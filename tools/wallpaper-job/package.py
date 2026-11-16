"""Deterministic phone overlays and a validated folder archive for this delivery."""
import hashlib
import json
from pathlib import Path
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path('deliveries/blue-kitty')
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')


def font(size):
    return ImageFont.truetype(str(FONT), size)


def overlay(image):
    """Return a new image; never draw into the clean wallpaper."""
    image = image.convert('RGBA')
    w, h = image.size
    layer = Image.new('RGBA', image.size)
    d = ImageDraw.Draw(layer)
    ink = (68, 88, 111, 240)
    def box(values):
        return tuple(round(v * w) for v in values)
    # Lock icon and date, followed by an intentionally legible dark blue clock.
    cx, y = w // 2, round(h * .063)
    d.rounded_rectangle((cx-9, y, cx+9, y+16), radius=4, fill=ink)
    d.arc((cx-6, y-11, cx+6, y+5), 180, 360, fill=ink, width=3)
    d.text((w / 2, h * .093), 'Monday, November 16', font=font(round(w * .039)), fill=ink, anchor='mt')
    d.text((w / 2, h * .123), '09:41', font=font(round(w * .19)), fill=ink, anchor='mt', stroke_width=0)
    # Top-right battery and reception: vector shapes, no external image assets.
    sx, sy = round(w * .83), round(h * .031)
    for i in range(4):
        d.rounded_rectangle((sx+i*6, sy+10-i*3, sx+i*6+3, sy+13), radius=1, fill=ink)
    d.rounded_rectangle((sx+33, sy, sx+62, sy+14), radius=3, outline=ink, width=2)
    d.rectangle((sx+36, sy+3, sx+56, sy+11), fill=ink)
    d.rectangle((sx+63, sy+5, sx+65, sy+9), fill=ink)
    # Flashlight and camera quick actions over translucent circular buttons.
    for x, kind in [(w*.15, 'light'), (w*.85, 'camera')]:
        x, y, r = round(x), round(h*.933), round(w*.042)
        d.ellipse((x-r,y-r,x+r,y+r), fill=(193,209,227,170), outline=(255,255,255,145), width=1)
        if kind == 'camera':
            d.rounded_rectangle((x-13,y-8,x+13,y+10), radius=4, outline=ink, width=2)
            d.ellipse((x-5,y-4,x+5,y+6), outline=ink, width=2)
            d.rectangle((x-7,y-12,x+5,y-8), fill=ink)
        else:
            d.polygon([(x-10,y-11),(x+10,y-11),(x+6,y-2),(x+4,y+12),(x-4,y+12),(x-6,y-2)], fill=ink)
            d.line((x-7,y-4,x+7,y-4), fill=(222,231,242,255), width=2)
    d.rounded_rectangle((w*.34,h*.977,w*.66,h*.981), radius=3, fill=ink)
    return Image.alpha_composite(image, layer).convert('RGB')


def record(path):
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        size = list(im.size)
    return {'file': str(path.relative_to(ROOT)), 'dimensions': size,
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def sheet(files, target):
    cols = 5
    rows = (len(files) + cols - 1) // cols
    result = Image.new('RGB', (cols*230+20, rows*540+20), '#e9edf3')
    d = ImageDraw.Draw(result)
    for i, path in enumerate(files):
        x, y = 20 + (i % cols)*230, 20 + (i // cols)*540
        with Image.open(path) as im:
            thumb = ImageOps.contain(im.convert('RGB'), (210, 490))
        d.text((x, y), path.name[:2], font=font(16), fill='#435367')
        result.paste(thumb, (x, y+26))
    result.save(target, quality=92)


def main():
    clean = sorted((ROOT / '02-复刻无手机UI').glob('*.png'))
    source = sorted((ROOT / '01-下载原图').glob('*.png'))
    if len(clean) != 10 or len(source) != 7:
        raise ValueError('Require exactly seven sources and ten clean results before packaging')
    source_log = json.loads((ROOT / '01-下载原图' / '下载记录.json').read_text())
    for entry in source_log['images']:
        p = ROOT / '01-下载原图' / entry['file']
        if hashlib.sha256(p.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Source hash mismatch')
    ui = ROOT / '03-复刻有手机UI'
    report = ROOT / '04-说明与验收'
    ui.mkdir(exist_ok=True)
    report.mkdir(exist_ok=True)
    pairs = []
    for i, p in enumerate(clean, 1):
        before = hashlib.sha256(p.read_bytes()).hexdigest()
        dest = ui / p.name
        with Image.open(p) as im:
            overlay(im).save(dest, optimize=True)
        if before != hashlib.sha256(p.read_bytes()).hexdigest():
            raise ValueError('Clean source unexpectedly changed')
        pairs.append({'number': i, 'mode': 'reference_redraw' if i <= 7 else 'new_scene_same_series',
                      'reference_numbers': [i] if i <= 7 else {8:[1,6],9:[2,4],10:[3,7]}[i],
                      'clean': record(p), 'phone_preview': record(dest)})
    ui_files = sorted(ui.glob('*.png'))
    if len(ui_files) != 10:
        raise ValueError('Unexpected overlay count')
    manifest = {'schema_version': 1, 'status': 'complete', 'source_count': 7,
                'clean_count': 10, 'phone_preview_count': 10,
                'generation': 'Ten independent image-conditioned AI generations; native 688x1536, not upscaled.',
                'ui': 'Deterministic illustrative lock-screen overlay, not a device screenshot.',
                'sources': [record(p) for p in source], 'pairs': pairs}
    (report/'验收记录.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    sheet(clean, report/'无UI总览.jpg')
    sheet(ui_files, report/'手机UI总览.jpg')
    sheet(source, report/'下载原图总览.jpg')
    archive = ROOT.parent / '奶fufu淡蓝壁纸-完整交付.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file():
                z.write(p, Path('奶fufu淡蓝壁纸') / p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Archive integrity check failed')
    print(json.dumps({'sources':len(source),'clean':len(clean),'ui':len(ui_files),
                      'zip_bytes':archive.stat().st_size,'zip':str(archive)},ensure_ascii=False))


if __name__ == '__main__':
    main()
