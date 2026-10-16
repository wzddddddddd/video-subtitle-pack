"""Explicit, opt-in model download to an external Hugging Face cache."""
import argparse
from faster_whisper.utils import download_model

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model', default='base')
parser.add_argument('--cache-dir', help='Optional external cache path; avoid the repository')
args = parser.parse_args()
print(download_model(args.model, cache_dir=args.cache_dir))
