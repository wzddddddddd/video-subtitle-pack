"""Generate synthetic media in a temporary directory; never use personal videos."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if p.returncode:
        raise RuntimeError(f'Command failed ({p.returncode}): {args}\n{p.stderr[-5000:]}')
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', help='Also test ASR and TXT using cached model and Windows speech')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="字幕 smoke ' ") as directory:
        work = Path(directory)
        video = work / "input's video.mp4"
        run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=navy:s=640x360:r=25',
             '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000', '-t', '4',
             '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', video])
        entry = [sys.executable, ROOT / 'scripts/video_subtitles.py', '--video', video,
                 '--preset', 'ultrafast']
        out = work / 'srt output'
        run(entry + ['--srt', ROOT / 'examples/example.srt', '--output-dir', out])
        info = json.loads((out / 'verification.json').read_text())
        v = next(s for s in info['streams'] if s['codec_type'] == 'video')
        assert (v['codec_name'], v['pix_fmt'], v['width'], v['height']) == ('h264','yuv420p',640,360)
        assert any(s['codec_type'] == 'audio' for s in info['streams'])
        # Ensure subtitles changed actual rendered pixels, not just container metadata.
        def frame(path):
            return run(['ffmpeg', '-v', 'error', '-ss', '1', '-i', path, '-frames:v', '1',
                        '-an', '-f', 'framemd5', '-']).stdout.splitlines()[-1]
        assert frame(video) != frame(out / 'video.mp4'), 'Subtitle render did not change frame'
        print('PASS: SRT, Chinese/spaces/apostrophe paths, codec, dimensions, audio, rendered pixels')
        before = (out / 'video.mp4').read_bytes()
        p = subprocess.run([str(a) for a in entry + ['--srt', ROOT / 'examples/example.srt', '--output-dir', out]], capture_output=True)
        assert p.returncode and (out / 'video.mp4').read_bytes() == before
        print('PASS: existing outputs protected')
        if args.model:
            if os.name != 'nt':
                raise RuntimeError('Synthetic speech test requires Windows System.Speech')
            speech = work / 'speech.wav'
            # Pass path as an argument, never interpolate it into shell code.
            ps = work / 'speak.ps1'
            ps.write_text('''param([string]$OutputPath)
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $speaker.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'zh-CN' } | Select-Object -First 1
if (-not $voice) { throw 'No zh-CN system voice installed' }
$speaker.SelectVoice($voice.VoiceInfo.Name)
$speaker.SetOutputToWaveFile($OutputPath)
$speaker.Speak('你好，这是字幕合成测试。今天我们学习如何制作视频字幕。')
$speaker.Dispose()
''', encoding='utf-8-sig')
            run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps, str(speech)])
            spoken = work / 'spoken.mp4'
            run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=navy:s=640x360:r=25',
                 '-i', speech, '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', spoken])
            entry = [sys.executable, ROOT / 'scripts/video_subtitles.py', '--video', spoken,
                     '--model', args.model, '--preset', 'ultrafast']
            auto = work / 'auto'
            run(entry + ['--auto', '--output-dir', auto])
            text = (auto / 'video.subtitles.srt').read_text(encoding='utf-8')
            assert '-->' in text and '字幕' in text, text
            print('PASS: real local ASR on synthetic Chinese speech; recognized subtitle keyword')
            copy = work / 'copy.txt'
            copy.write_text('你好，这是字幕合成测试。今天我们学习如何制作视频字幕。', encoding='utf-8')
            aligned = work / 'txt'
            run(entry + ['--text-file', copy, '--output-dir', aligned])
            text = (aligned / 'video.subtitles.srt').read_text(encoding='utf-8')
            assert '你好' in text and '制作视频字幕' in text and '-->' in text
            print('PASS: TXT alignment and rendered MP4')
        print('All requested smoke tests passed; temporary generated media removed.')


if __name__ == '__main__':
    main()
