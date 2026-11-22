from pathlib import Path
import hashlib
import json
from PIL import Image

root = Path(__file__).resolve().parent
sources = json.loads((root / 'source-manifest.json').read_text())['images']
outputs = json.loads((root / 'output-manifest.json').read_text())['files']
assert len(sources) == 3 and len(outputs) == 10
assert len(list((root / 'images').glob('*.png'))) == 10
for rec in sources + outputs:
    path = root / rec['file']
    assert path.stat().st_size == rec['bytes']
    assert hashlib.md5(path.read_bytes()).hexdigest() == rec['md5']
    with Image.open(path) as image:
        image.load()
        expected = rec.get('size', [rec.get('width'), rec.get('height')])
        assert list(image.size) == expected
assert len({rec['md5'] for rec in outputs}) == 10
assert not list(root.rglob('*.html'))
print('PASS: 3 downloaded references + 10 native independent images; size/hash/decode/unique/noHTML')
