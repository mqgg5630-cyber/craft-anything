"""Run from repository root: .venv/bin/python deliveries/sakura-image-suite-v2/skills/test_delivery.py"""
from pathlib import Path
from PIL import Image
import json,hashlib,subprocess,imageio_ffmpeg
R=Path(__file__).resolve().parents[1]
manifest=json.loads((R/'清单.json').read_text())
assert len(manifest)==10
n=0
for folder,entry in zip(sorted((R/'sets').iterdir()),manifest):
 assert len(entry['files'])==33
 for item in entry['files']:
  p=folder/item['file']
  assert p.stat().st_size==item['bytes']
  assert hashlib.md5(p.read_bytes()).hexdigest()==item['md5'],p
  if p.suffix=='.mp4':
   subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(p),'-f','null','-'],check=True)
  else:
   with Image.open(p) as im:
    assert list(im.size)==item['size'],p
    im.load()
  n+=1
assert n==330
assert not list(R.rglob('*.html'))
print('PASS: 330 hashes, sizes and decodes; 10 videos; no HTML')
