from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path



PUNCTUATION_CODEPOINTS = {
    ord(","),
    ord("."),
    ord("!"),
    ord("?"),
    ord(";"),
    ord(":"),
    ord("，"),
    ord("。"),
    ord("！"),
    ord("？"),
    ord("；"),
    ord("："),
    ord("\n"),
    ord("\r"),
}
MIN_SUBTITLE_DURATION_SECONDS = 0.9
READING_CHARS_PER_SECOND = 7.0
SUBTITLE_GAP_SECONDS = 0.02
@lru_cache(maxsize=1)
def get_converter():
    from opencc import OpenCC
    return OpenCC("t2s").convert

def traditional_to_simplified(text: str) -> str:
    return get_converter()(text)



@dataclass
class CharStamp:
    char: str
    start: float
    end: float


@dataclass
class SubtitleCue:
    index: int
    text: str
    start: float
    end: float


def read_text_file(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    buffer: list[str] = []
    for char in text:
        if ord(char) in PUNCTUATION_CODEPOINTS:
            sentence = "".join(buffer).strip(" \t,，")
            if sentence:
                sentences.append(sentence)
            buffer = []
            continue
        buffer.append(char)

    sentence = "".join(buffer).strip(" \t,，")
    if sentence:
        sentences.append(sentence)
    return sentences


def normalize_text(text: str) -> str:
    normalized: list[str] = []
    for char in traditional_to_simplified(text.lower()):
        if ord(char) in PUNCTUATION_CODEPOINTS or char.isspace():
            continue
        normalized.append(char)
    return "".join(normalized)


def minimum_subtitle_duration(text: str) -> float:
    visible_chars = len(normalize_text(text))
    if visible_chars == 0:
        return MIN_SUBTITLE_DURATION_SECONDS
    return max(MIN_SUBTITLE_DURATION_SECONDS, visible_chars / READING_CHARS_PER_SECOND)


def format_srt_timestamp(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def extract_audio(video_path: Path, wav_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path.resolve()),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(wav_path),
        ],
        check=True,
    )


def detect_silences(audio_path: Path, noise: str = "-30dB", duration: str = "0.25") -> list[tuple[float, float]]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(audio_path),
            "-af",
            f"silencedetect=noise={noise}:d={duration}",
            "-f",
            "null",
            "-",
        ],
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    starts: list[float] = []
    silences: list[tuple[float, float]] = []
    for line in result.stderr.splitlines():
        if "silence_start:" in line:
            starts.append(float(line.split("silence_start:", 1)[1].strip()))
        if "silence_end:" in line and starts:
            end_text = line.split("silence_end:", 1)[1].split("|", 1)[0].strip()
            silences.append((starts.pop(0), float(end_text)))
    return silences


def transcribe_char_stamps(audio_path: Path, model_size: str) -> list[CharStamp]:
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8", local_files_only=True)
    segments, _ = model.transcribe(
        str(audio_path),
        language="zh",
        beam_size=5,
        best_of=5,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
    )

    char_stamps: list[CharStamp] = []
    for segment in segments:
        words = getattr(segment, "words", None) or []
        if words:
            for word in words:
                token = normalize_text(word.word)
                if not token:
                    continue
                duration = max((word.end or segment.end) - (word.start or segment.start), 0.001)
                step = duration / len(token)
                for index, char in enumerate(token):
                    start = (word.start or segment.start) + step * index
                    end = (word.start or segment.start) + step * (index + 1)
                    char_stamps.append(CharStamp(char=char, start=start, end=end))
            continue

        token = normalize_text(segment.text)
        if not token:
            continue
        duration = max(segment.end - segment.start, 0.001)
        step = duration / len(token)
        for index, char in enumerate(token):
            start = segment.start + step * index
            end = segment.start + step * (index + 1)
            char_stamps.append(CharStamp(char=char, start=start, end=end))
    return char_stamps


def align_sentence(sentence: str, transcript: str, stamps: list[CharStamp], cursor: int) -> tuple[int, int]:
    target = normalize_text(sentence)
    if not target:
        return cursor, min(cursor, len(stamps) - 1)

    exact = transcript.find(target, cursor)
    if exact != -1:
        return exact, exact + len(target) - 1

    search_start = max(0, cursor - 2)
    search_end = min(len(transcript), search_start + max(len(target) * 8, 120))
    best_score = -1.0
    best_span = (cursor, min(len(stamps) - 1, cursor + max(len(target) - 1, 0)))
    min_len = max(1, int(len(target) * 0.55))
    max_len = min(search_end - search_start, int(len(target) * 1.8) + 12)
    probe = target[: max(1, min(8, len(target)))]

    for start in range(search_start, max(search_start + 1, search_end - min_len + 1)):
        if probe and transcript[start : start + len(probe)] != probe and start > cursor + 10:
            continue
        for size in range(min_len, max_len + 1):
            end = start + size
            if end > search_end:
                break
            candidate = transcript[start:end]
            score = SequenceMatcher(None, candidate, target).ratio()
            if score > best_score:
                best_score = score
                best_span = (start, end - 1)
    return best_span


def snap_to_silence(time_point: float, silences: list[tuple[float, float]], use_end: bool, tolerance: float = 0.35) -> float:
    choices = [end if use_end else start for start, end in silences if abs((end if use_end else start) - time_point) <= tolerance]
    if not choices:
        return time_point
    return min(choices, key=lambda value: abs(value - time_point))


def build_cues(sentences: list[str], stamps: list[CharStamp], silences: list[tuple[float, float]]) -> list[SubtitleCue]:
    transcript = "".join(stamp.char for stamp in stamps)
    cues: list[SubtitleCue] = []
    cursor = 0

    for index, sentence in enumerate(sentences, start=1):
        start_index, end_index = align_sentence(sentence, transcript, stamps, cursor)
        start_index = max(0, min(start_index, len(stamps) - 1))
        end_index = max(start_index, min(end_index, len(stamps) - 1))
        cursor = end_index + 1

        start = max(0.0, stamps[start_index].start - 0.03)
        end = stamps[end_index].end + 0.03
        minimum_end = start + minimum_subtitle_duration(sentence)
        if index > 1:
            start = snap_to_silence(start, silences, use_end=True)
        if index < len(sentences):
            end = snap_to_silence(end, silences, use_end=False)
        end = max(end, minimum_end)
        cues.append(SubtitleCue(index=index, text=sentence, start=start, end=end))

    if cues:
        cues[0].start = 0.0

    for idx in range(len(cues)):
        cue = cues[idx]
        if idx > 0 and cue.start <= cues[idx - 1].end:
            cue.start = cues[idx - 1].end + SUBTITLE_GAP_SECONDS
        if cue.end <= cue.start:
            cue.end = cue.start + MIN_SUBTITLE_DURATION_SECONDS

    return cues


def write_srt(cues: list[SubtitleCue], path: Path) -> None:
    lines: list[str] = []
    for cue in cues:
        text = cue.text
        if len(text) > 24:
            midpoint = math.ceil(len(text) / 2)
            text = f"{text[:midpoint]}\n{text[midpoint:]}"
        lines.extend(
            [
                str(cue.index),
                f"{format_srt_timestamp(cue.start)} --> {format_srt_timestamp(cue.end)}",
                text,
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_srt_from_txt(video_path: Path, text_path: Path, output_srt_path: Path, model_size: str) -> Path:
    wav_path = output_srt_path.with_suffix(".audio.wav")
    try:
        text = read_text_file(text_path)
        sentences = split_sentences(text)
        if not sentences:
            raise RuntimeError(f"No subtitle sentences found in {text_path}")
        extract_audio(video_path, wav_path)
        silences = detect_silences(wav_path)
        stamps = transcribe_char_stamps(wav_path, model_size)
        if not stamps:
            raise RuntimeError("Speech transcription produced no timestamps.")
        cues = build_cues(sentences, stamps, silences)
        write_srt(cues, output_srt_path)
    finally:
        if wav_path.exists():
            wav_path.unlink()
    return output_srt_path


def probe_audio_codec(video_path: Path) -> str | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path.resolve()),
        ],
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    codec = result.stdout.strip()
    return codec or None


def run_ffmpeg(video_path: Path, srt_path: Path, output_path: Path, font_size: int, margin_v: int, crf: int, preset: str, primary_colour: str) -> None:
    style = (
        "FontName=Microsoft YaHei,"
        f"FontSize={font_size},"
        f"PrimaryColour={primary_colour},"
        "OutlineColour=&H101010&,"
        "BorderStyle=1,"
        "Outline=1.2,"
        "Shadow=0.3,"
        "Alignment=2,"
        f"MarginV={margin_v}"
    )
    import tempfile
    with tempfile.TemporaryDirectory(prefix="subtitle-burn-") as directory:
        local_srt = Path(directory) / "subtitles.srt"
        local_srt.write_text(read_text_file(srt_path), encoding="utf-8")
        _render_in_directory(video_path, output_path, style, crf, preset, directory)


def _render_in_directory(video_path, output_path, style, crf, preset, directory):
    vf = f"subtitles=subtitles.srt:charenc=UTF-8:force_style='{style}'"
    audio_codec = probe_audio_codec(video_path)
    audio_args = ["-c:a", "copy"] if audio_codec == "aac" else ["-c:a", "aac", "-b:a", "192k"]

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path.resolve()),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        preset,
        "-crf",
        str(crf),
        *audio_args,
        "-movflags",
        "+faststart",
        str(output_path.resolve()),
    ]
    subprocess.run(command, check=True, cwd=directory)
