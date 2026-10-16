"""Portable entrypoint; no model downloads during normal processing."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import subtitle_core as core


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams',
                             '-show_format', '-of', 'json', str(path)],
                            check=True, capture_output=True, text=True, encoding='utf-8')
    return json.loads(result.stdout)


def transcribe(video, output, model_name, language):
    from faster_whisper import WhisperModel
    from opencc import OpenCC
    convert = OpenCC('t2s').convert if language == 'zh' else lambda x: x
    model = WhisperModel(model_name, device='cpu', compute_type='int8', local_files_only=True)
    with tempfile.TemporaryDirectory(prefix='subtitle-asr-') as directory:
        wav = Path(directory) / 'audio.wav'
        core.extract_audio(video, wav)
        segments, _ = model.transcribe(str(wav), language=None if language == 'auto' else language,
                                      vad_filter=True, beam_size=5, condition_on_previous_text=False)
        cues = [core.SubtitleCue(i, convert(s.text.strip()), max(0, s.start), s.end)
                for i, s in enumerate(segments, 1) if s.text.strip() and s.end > s.start]
        if not cues:
            raise RuntimeError('No speech detected; no subtitles or video were produced.')
        core.write_srt(cues, output)


def main():
    parser = argparse.ArgumentParser(description='Burn SRT, align Chinese TXT, or transcribe video. CPU/int8.')
    parser.add_argument('--video', required=True, type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--srt', type=Path)
    modes.add_argument('--text-file', type=Path)
    modes.add_argument('--auto', action='store_true')
    parser.add_argument('--output-dir', required=True, type=Path, help='New or empty job directory')
    parser.add_argument('--model', default='base', help='Cached Whisper size or local CTranslate2 model directory')
    parser.add_argument('--language', default='zh', help='Whisper language code or auto; TXT alignment requires zh')
    parser.add_argument('--font-size', type=int, default=13)
    parser.add_argument('--margin-v', type=int, default=18)
    parser.add_argument('--crf', type=int, default=16)
    parser.add_argument('--preset', default='slow', choices=['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow'])
    args = parser.parse_args()
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool):
            parser.error(f'{tool} not found in PATH; see references/installation.md')
    inputs = [args.video] + [p for p in (args.srt, args.text_file) if p]
    for path in inputs:
        if not path.is_file():
            parser.error(f'Input does not exist: {path}')
    if args.text_file and args.language != 'zh':
        parser.error('TXT alignment currently supports Chinese (--language zh).')
    if not 0 <= args.crf <= 51 or args.font_size <= 0 or args.margin_v < 0:
        parser.error('Invalid subtitle style or CRF value.')
    if args.output_dir.exists() and (not args.output_dir.is_dir() or any(args.output_dir.iterdir())):
        parser.error('Output directory must be new or empty; use a separate directory for each job.')
    source = probe(args.video)
    streams = source['streams']
    video = next((s for s in streams if s['codec_type'] == 'video'), None)
    if not video:
        parser.error('Input has no video stream.')
    if video['width'] % 2 or video['height'] % 2:
        parser.error('H.264/yuv420p requires even dimensions; resize or pad the source first.')
    if not args.srt and not any(s['codec_type'] == 'audio' for s in streams):
        parser.error('Speech recognition requires an audio stream.')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Stage all results and publish only after successful encoding and verification.
    with tempfile.TemporaryDirectory(prefix='subtitle-job-', dir=args.output_dir) as directory:
        job = Path(directory)
        srt = job / 'video.subtitles.srt'
        if args.srt:
            text = core.read_text_file(args.srt)
            if '-->' not in text:
                parser.error('SRT has no timed cues.')
            srt.write_text(text, encoding='utf-8')
        elif args.text_file:
            core.build_srt_from_txt(args.video, args.text_file, srt, args.model)
        else:
            transcribe(args.video, srt, args.model, args.language)
        output = job / 'video.mp4'
        core.run_ffmpeg(args.video, srt, output, args.font_size, args.margin_v,
                        args.crf, args.preset, '&H00FFFF&')
        info = probe(output)
        v = next(s for s in info['streams'] if s['codec_type'] == 'video')
        if v['codec_name'] != 'h264' or v['pix_fmt'] != 'yuv420p':
            raise RuntimeError('Output codec verification failed.')
        if (v['width'], v['height']) != (video['width'], video['height']):
            raise RuntimeError('Output dimensions changed unexpectedly.')
        if any(s['codec_type'] == 'audio' for s in streams) and not any(s['codec_type'] == 'audio' for s in info['streams']):
            raise RuntimeError('Output audio missing.')
        (job / 'verification.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
        for name in ('video.mp4', 'video.subtitles.srt', 'verification.json'):
            shutil.move(str(job / name), args.output_dir / name)
    print(f'Completed: {args.output_dir.resolve()}')


if __name__ == '__main__':
    main()
