"""Deterministic phone overlays, contact sheets and validation for the
Lululu sunset delivery. Runs after the 10 replica wallpapers exist in
``02-复刻无手机UI``. Never modifies the clean wallpapers; the overlay is rendered
onto a copy. Produces:
  - 03-复刻有手机UI/<NN>.png  (illustrative lock-screen overlay, not a screenshot)
  - 04-说明与验收/验收记录.json (source hash check + per-image records)
  - 04-说明与验收/下载原图总览.jpg
  - 04-说明与验收/无UI总览.jpg
  - 04-说明与验收/手机UI总览.jpg
  - 00-10张复刻总览.jpg  (replica-only preview)
  - 总预览图.jpg         (originals + replicas + UI, the master total preview)
"""
import hashlib
import json
from pathlib import Path
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path('deliveries/lululu-sunset')
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
CLEAN_COUNT = 10


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

    cx, y = w // 2, round(h * .063)
    d.rounded_rectangle((cx - 9, y, cx + 9, y + 16), radius=4, fill=ink)
    d.arc((cx - 6, y - 11, cx + 6, y + 5), 180, 360, fill=ink, width=3)
    d.text((w / 2, h * .093), 'Monday, November 16', font=font(round(w * .039)), fill=ink, anchor='mt')
    d.text((w / 2, h * .123), '09:41', font=font(round(w * .19)), fill=ink, anchor='mt')
    sx, sy = round(w * .83), round(h * .031)
    for i in range(4):
        d.rounded_rectangle((sx + i * 6, sy + 10 - i * 3, sx + i * 6 + 3, sy + 13), radius=1, fill=ink)
    d.rounded_rectangle((sx + 33, sy, sx + 62, sy + 14), radius=3, outline=ink, width=2)
    d.rectangle((sx + 36, sy + 3, sx + 56, sy + 11), fill=ink)
    d.rectangle((sx + 63, sy + 5, sx + 65, sy + 9), fill=ink)
    for x, kind in [(w * .15, 'light'), (w * .85, 'camera')]:
        x, y, r = round(x), round(h * .933), round(w * .042)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(193, 209, 227, 170), outline=(255, 255, 255, 145), width=1)
        if kind == 'camera':
            d.rounded_rectangle((x - 13, y - 8, x + 13, y + 10), radius=4, outline=ink, width=2)
            d.ellipse((x - 5, y - 4, x + 5, y + 6), outline=ink, width=2)
            d.rectangle((x - 7, y - 12, x + 5, y - 8), fill=ink)
        else:
            d.polygon([(x - 10, y - 11), (x + 10, y - 11), (x + 6, y - 2), (x + 4, y + 12),
                       (x - 4, y + 12), (x - 6, y - 2)], fill=ink)
            d.line((x - 7, y - 4, x + 7, y - 4), fill=(222, 231, 242, 255), width=2)
    d.rounded_rectangle((w * .34, h * .977, w * .66, h * .981), radius=3, fill=ink)
    return Image.alpha_composite(image, layer).convert('RGB')


def record(path):
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        size = list(im.size)
    return {'file': str(path.relative_to(ROOT)), 'dimensions': size,
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def sheet(files, target, label_width=210, label_height=490, pad=20, bg='#e9edf3'):
    cols = 5
    rows = (len(files) + cols - 1) // cols
    result = Image.new('RGB', (cols * (label_width + pad) + pad, rows * (label_height + pad + 20) + pad), bg)
    d = ImageDraw.Draw(result)
    for i, path in enumerate(files):
        x, y = pad + (i % cols) * (label_width + pad), pad + (i // cols) * (label_height + pad + 20)
        with Image.open(path) as im:
            thumb = ImageOps.contain(im.convert('RGB'), (label_width, label_height))
        d.text((x, y), path.name[:2], font=font(16), fill='#435367')
        result.paste(thumb, (x, y + 20))
    result.save(target, quality=92)


def main():
    source_folder = ROOT / '01-下载原片'
    clean = sorted((ROOT / '02-复刻无手机UI').glob('*.png'))
    if len(clean) != CLEAN_COUNT:
        raise ValueError(f'Require exactly {CLEAN_COUNT} clean replicas before packaging, found {len(clean)}')

    source_log = json.loads((source_folder / '下载记录.json').read_text()) if (source_folder / '下载记录.json').exists() else {}
    source_images = source_log.get('images') or []
    source_files = sorted(p for p in source_folder.glob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'))
    if source_images:
        for entry in source_images:
            p = source_folder / entry['file']
            if not p.exists():
                continue
            actual = hashlib.sha256(p.read_bytes()).hexdigest()
            if actual != entry.get('sha256', ''):
                raise ValueError(f'Source hash mismatch for {entry["file"]}')
    source_records = [record(p) for p in source_files]

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
        pairs.append({'number': i, 'clean': record(p), 'phone_preview': record(dest)})
    ui_files = sorted(ui.glob('*.png'))
    if len(ui_files) != CLEAN_COUNT:
        raise ValueError('Unexpected overlay count')

    manifest = {
        'schema_version': 1,
        'status': 'complete',
        'source_count': len(source_records),
        'clean_count': CLEAN_COUNT,
        'phone_preview_count': CLEAN_COUNT,
        'generation': 'Ten independent image-conditioned AI generations; native output, not upscaled.',
        'ui': 'Deterministic illustrative lock-screen overlay, not a device screenshot.',
        'sources': source_records,
        'pairs': pairs,
    }
    (report / '验收记录.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    sheet(clean, report / '无UI总览.jpg')
    sheet(ui_files, report / '手机UI总览.jpg')
    if source_files:
        sheet(source_files, report / '下载原图总览.jpg')
    sheet(clean, ROOT / '00-10张复刻总览.jpg')
    # Master total preview: originals (if any), then no-UI replicas, then UI replicas.
    sheet((source_files + clean + ui_files) if source_files else (clean + ui_files), ROOT / '总预览图.jpg')

    archive = ROOT.parent / '噜噜噜妹夕阳壁纸-完整交付.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file():
                z.write(p, Path('噜噜噜妹夕阳壁纸') / p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Archive integrity check failed')
    print(json.dumps({'sources': len(source_records), 'clean': len(clean), 'ui': len(ui_files),
                      'zip_bytes': archive.stat().st_size, 'zip': str(archive)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
