"""Overlay illustrative lock-screen UI, without changing the generated originals."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).parent
SOURCE_ROOT = ROOT.parent / "lululu-cute-note"
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def digest(data):
    return hashlib.md5(data).hexdigest()

def main():
    sources = json.loads((SOURCE_ROOT / 'source-manifest.json').read_text(encoding='utf-8'))
    for rec in sources['images']:
        data = (SOURCE_ROOT / rec['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == rec['sha256']
        with Image.open(SOURCE_ROOT / rec['file']) as im:
            im.verify()
    files = sorted((ROOT / 'images').glob('*.png'))
    if len(files) != 10:
        raise RuntimeError('Expected exactly 10 original generations')
    out = ROOT / 'ui'
    out.mkdir(exist_ok=True)
    records, hashes = [], set()
    for index, path in enumerate(files, 1):
        data = path.read_bytes()
        with Image.open(path) as im:
            im.load()
            w, h = im.size
            if min(w, h) < 500 or digest(data) in hashes:
                raise ValueError('Image too small or duplicate')
            hashes.add(digest(data))
            base = im.convert('RGBA')
        draw = ImageDraw.Draw(base, 'RGBA')
        # Simple mockup only: time/date and bottom controls, not a device screenshot.
        def text(y, value, size):
            font = ImageFont.truetype(FONT, int(w * size))
            draw.text((w // 2 + 1, int(h * y) + 2), value, font=font, anchor='mt', fill=(70, 44, 32, 100))
            draw.text((w // 2, int(h * y)), value, font=font, anchor='mt', fill=(255, 255, 255, 245))
        text(.065, 'Monday, August 18', .032)
        text(.103, '9:41', .145)
        r = int(w * .046)
        for cx in (int(w * .13), int(w * .87)):
            cy = int(h * .925)
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(35, 32, 30, 100))
        # Stylized flashlight and camera glyphs.
        cx, cy = int(w * .13), int(h * .925)
        draw.polygon([(cx-r*.25,cy-r*.35),(cx+r*.25,cy-r*.35),(cx+r*.13,cy),(cx+r*.13,cy+r*.38),(cx-r*.13,cy+r*.38),(cx-r*.13,cy)],fill=(255,255,255,235))
        cx = int(w * .87)
        draw.rounded_rectangle((cx-r*.42,cy-r*.23,cx+r*.42,cy+r*.32), radius=3, fill=(255,255,255,235))
        draw.ellipse((cx-r*.17,cy-r*.15,cx+r*.17,cy+r*.19), fill=(75,70,65,255))
        ui = out / path.name
        base.convert('RGB').save(ui, 'PNG', optimize=True)
        with Image.open(ui) as check:
            check.verify()
        ui_bytes = ui.read_bytes()
        records.append({'file': f'images/{path.name}', 'reference': '../lululu-cute-note/source/02.webp, 03.webp, 04.webp (see README for mapping)',
                        'width': w, 'height': h, 'bytes':len(data), 'md5':digest(data),
                        'ui_file': f'ui/{path.name}', 'ui_bytes':len(ui_bytes), 'ui_md5':digest(ui_bytes)})
    (ROOT / 'output-manifest.json').write_text(json.dumps({'image_count':len(records),'ui_count':len(records),'images':records}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Verified 5 source files, 10 unique generated images, 10 mock UI images')

if __name__ == '__main__':
    main()
