"""Offline acceptance check: python deliveries/lululu-sunset-ui-10/test_delivery.py"""
import hashlib
import json
from pathlib import Path

from PIL import Image

root = Path(__file__).resolve().parent
src = json.loads((root / 'source-manifest.json').read_text())['images']
out = json.loads((root / 'output-manifest.json').read_text())['files']
assert len(src) == 5 and len(out) == 20
for rec in src:
    data = (root / rec['file']).read_bytes()
    assert len(data) == rec['bytes'] and hashlib.md5(data).hexdigest() == rec['md5']
for rec in out:
    path = root / rec['file']
    assert path.stat().st_size == rec['bytes'] and hashlib.md5(path.read_bytes()).hexdigest() == rec['md5']
    with Image.open(path) as image:
        image.load()
        assert list(image.size) == rec['size']
for kind in ('无UI', '有UI'):
    names = sorted(p.name for p in (root / '复刻结果' / kind).glob('*.png'))
    assert len(names) == 10 and names[0].startswith('01-') and names[-1].startswith('10-')
assert len({r['md5'] for r in out}) == 20
cloud = json.loads((root / 'cloud-verification.json').read_text())
assert cloud['all_match'] and cloud['cloud_count'] == 25
assert not list(root.rglob('*.html'))
print('PASS: 5 sources + 10 no-UI + 10 UI; hash/decode/size/unique; Drive 25/25 MD5 match')
