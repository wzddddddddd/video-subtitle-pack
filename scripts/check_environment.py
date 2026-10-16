import importlib.metadata
import importlib.util
import shutil
import subprocess
import sys

print('Python:', sys.version.split()[0])
failed = sys.version_info < (3, 10)
for tool in ('ffmpeg', 'ffprobe'):
    path = shutil.which(tool)
    print(tool + ':', path or 'MISSING')
    failed |= path is None
if shutil.which('ffmpeg'):
    for option, feature in [('-filters', 'subtitles'), ('-encoders', 'libx264')]:
        p = subprocess.run(['ffmpeg', '-hide_banner', option], capture_output=True, text=True, encoding='utf-8', errors='replace')
        ok = p.returncode == 0 and feature in p.stdout
        print(feature + ':', 'OK' if ok else 'MISSING')
        failed |= not ok
for module, package in [('faster_whisper', 'faster-whisper'), ('opencc', 'opencc-python-reimplemented')]:
    present = importlib.util.find_spec(module) is not None
    print(package + ':', importlib.metadata.version(package) if present else 'MISSING (needed for ASR/TXT only)')
raise SystemExit(1 if failed else 0)
