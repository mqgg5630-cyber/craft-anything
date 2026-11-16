"""Deterministic phone previews, contact sheets and a verified archive for the Budapest delivery.

The wallpapers themselves are AI generated; this script only composites illustrative
lock-screen and home-screen previews on top of copies, and validates the result.
"""
import hashlib
import json
import random
import zipfile
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path('deliveries/budapest-autumn-563')
FONT_DIR = Path('.cache/wheels/mpl/mplfonts/fonts')
LATIN = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
SERIF = FONT_DIR / 'NotoSerifCJKsc-Regular.otf'
SANS = FONT_DIR / 'NotoSansCJKsc-Regular.otf'

TEAL = (58, 166, 181)
TEAL_SOFT = (150, 199, 205)
CREAM = (246, 239, 226)
INK = (34, 48, 56)

CLEAN = ROOT / '02-复刻无手机UI'
LOCK = ROOT / '03-锁屏预览'
HOME = ROOT / '04-桌面组件预览'
REPORT = ROOT / '05-说明与验收'


def font(size, path=LATIN):
    return ImageFont.truetype(str(path), size)


def lock_overlay(image, number):
    """Return a new illustrative lock-screen image; the clean wallpaper is never touched."""
    image = image.convert('RGBA')
    w, h = image.size
    layer = Image.new('RGBA', image.size)
    d = ImageDraw.Draw(layer)
    white = (255, 255, 255, 238)
    soft = (255, 255, 255, 150)

    # Status bar: clock on the left, reception, wifi and battery on the right.
    d.text((w * .085, h * .028), '23:55', font=font(round(w * .032)), fill=white, anchor='lt')
    bx, by = round(w * .80), round(h * .033)
    for i in range(4):
        d.rounded_rectangle((bx + i * 7, by + 11 - i * 3, bx + i * 7 + 4, by + 14), radius=1, fill=white)
    wx = bx + 34
    for radius in (5, 11, 17):
        d.arc((wx - radius, by + 12 - radius, wx + radius, by + 12 + radius), 220, 320, fill=white, width=2)
    d.rounded_rectangle((wx + 26, by, wx + 60, by + 15), radius=4, outline=white, width=2)
    d.rounded_rectangle((wx + 29, by + 3, wx + 52, by + 12), radius=2, fill=white)
    d.rectangle((wx + 61, by + 5, wx + 63, by + 10), fill=white)

    # Date and the large thin clock, using the note's own layering.
    d.text((w / 2, h * .062), '11月16日 星期一', font=font(round(w * .031), SANS), fill=soft, anchor='mt')
    d.text((w / 2, h * .084), '23:55', font=font(round(w * .165), LATIN), fill=white, anchor='mt')

    # Battery pill with a place label, then a ring and a quick-toggle circle.
    y = h * .295
    d.rounded_rectangle((w * .085, y, w * .095, y + h * .011), radius=3, fill=white)
    d.text((w * .105, y - h * .004), '68%', font=font(round(w * .026), LATIN), fill=white, anchor='lt')
    d.text((w * .085, y + h * .019), '布达佩斯 · 秋', font=font(round(w * .028), SANS), fill=soft, anchor='lt')
    d.rounded_rectangle((w * .085, y + h * .052, w * .355, y + h * .058), radius=4, fill=(255, 255, 255, 90))
    d.rounded_rectangle((w * .085, y + h * .052, w * .085 + w * .19, y + h * .058), radius=4, fill=white)

    rx, ry, r = w * .545, y + h * .008, w * .045
    d.arc((rx - r, ry - r, rx + r, ry + r), 0, 360, fill=(255, 255, 255, 110), width=round(w * .009))
    d.arc((rx - r, ry - r, rx + r, ry + r), -90, 150, fill=white, width=round(w * .009))
    d.text((rx, ry), f'{number * 620}', font=font(round(w * .030), LATIN), fill=white, anchor='mm')
    d.text((rx, ry + r + h * .012), '步', font=font(round(w * .022), SANS), fill=soft, anchor='mt')

    cx, cy, cr = w * .70, ry, w * .043
    d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), outline=(255, 255, 255, 130), width=round(w * .008))
    d.rounded_rectangle((cx - w * .012, cy - w * .021, cx + w * .012, cy + w * .019),
                        radius=round(w * .006), outline=white, width=round(w * .004))

    # Bottom quick actions over translucent circles, plus the home indicator.
    for x, kind in ((w * .145, 'light'), (w * .855, 'camera')):
        cy2 = h * .925
        rad = w * .045
        # A dark halo keeps the white glyph readable over both water and pale boats.
        d.ellipse((x - rad - 3, cy2 - rad - 3, x + rad + 3, cy2 + rad + 3), fill=(18, 44, 52, 90))
        d.ellipse((x - rad, cy2 - rad, x + rad, cy2 + rad), fill=(40, 70, 80, 120),
                  outline=(255, 255, 255, 130), width=2)
        if kind == 'camera':
            d.rounded_rectangle((x - w * .019, cy2 - w * .012, x + w * .019, cy2 + w * .015),
                                radius=round(w * .006), outline=white, width=3)
            d.ellipse((x - w * .008, cy2 - w * .006, x + w * .008, cy2 + w * .010), outline=white, width=3)
            d.rectangle((x - w * .011, cy2 - w * .018, x + w * .008, cy2 - w * .012), fill=white)
        else:
            d.polygon([(x - w * .014, cy2 - w * .017), (x + w * .014, cy2 - w * .017),
                       (x + w * .009, cy2 - w * .004), (x + w * .007, cy2 + w * .017),
                       (x - w * .007, cy2 + w * .017), (x - w * .009, cy2 - w * .004)], fill=white)
            d.line((x - w * .010, cy2 - w * .007, x + w * .010, cy2 - w * .007),
                   fill=(58, 166, 181, 255), width=3)
    d.rounded_rectangle((w * .35, h * .975, w * .65, h * .981), radius=3, fill=(255, 255, 255, 220))
    return Image.alpha_composite(image, layer).convert('RGB')


def torn_mask(size, seed):
    """Irregular screen-print torn edge, deterministic per image."""
    w, h = size
    rng = random.Random(seed)
    mask = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(mask)
    points = []
    steps = 14
    for i in range(steps + 1):
        x = -4 + (w + 8) * i / steps
        points.append((x, 4 + rng.uniform(0, 9)))
    for i in range(steps + 1):
        x = w + 4 - (w + 8) * i / steps
        points.append((x, h - 4 - rng.uniform(0, 10)))
    d.polygon(points, fill=255)
    return mask


def home_overlay(image, number):
    """Illustrative widget-screen preview with a torn artwork inset; the wallpaper is copied, never drawn on."""
    src = image.convert('RGB')
    w, h = src.size
    card = Image.new('RGB', (w, h), CREAM)
    d = ImageDraw.Draw(card)
    radius = round(w * .045)

    def block(x0, y0, x1, y1, fill=TEAL):
        d.rounded_rectangle((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)),
                            radius=radius, fill=fill)

    # Status line, then the widget grid from the reference layout.
    d.text((w * .115, h * .030), '23:55', font=font(round(w * .030), LATIN), fill=(40, 52, 58), anchor='lt')
    bx = w * .72
    for i in range(4):
        d.rounded_rectangle((bx + i * 7, h * .034 + 11 - i * 3, bx + i * 7 + 4, h * .034 + 14),
                            radius=1, fill=(40, 52, 58))
    d.rounded_rectangle((bx + 34, h * .034, bx + 68, h * .034 + 15), radius=4, outline=(40, 52, 58), width=2)
    d.rounded_rectangle((bx + 37, h * .034 + 3, bx + 60, h * .034 + 12), radius=2, fill=(40, 52, 58))

    block(.10, .075, .52, .245)
    block(.565, .075, .675, .145)
    block(.71, .075, .82, .145)
    block(.565, .165, .675, .235)
    block(.71, .165, .82, .235)
    block(.10, .275, .21, .345)
    block(.245, .275, .355, .345)
    block(.40, .275, .82, .445)
    block(.10, .375, .21, .445)
    block(.245, .375, .355, .445)

    # Artwork inset with a torn paper edge, cut from the wallpaper's scene area.
    art_w = round(w * .74)
    art_h = round(h * .20)
    crop = src.crop((round(w * .12), round(h * .42), round(w * .88), round(h * .62)))
    crop = crop.resize((art_w, art_h), Image.LANCZOS)
    mask = torn_mask((art_w, art_h), number)
    at = (round(w * .13), round(h * .485))
    card.paste(crop, at, mask)

    d.text((w / 2, h * .705), '布达佩斯的秋天', font=font(round(w * .040), SERIF), fill=(30, 62, 66), anchor='mt')
    d.text((w / 2, h * .742), 'Duna  ·  563', font=font(round(w * .024), LATIN), fill=(120, 110, 96), anchor='mt')

    d.rounded_rectangle((round(w * .075), round(h * .805), round(w * .925), round(h * .900)),
                        radius=round(w * .050), fill=TEAL_SOFT)
    for i in range(4):
        x0 = w * .098 + i * w * .205
        d.rounded_rectangle((round(x0), round(h * .818), round(x0 + w * .155), round(h * .887)),
                            radius=round(w * .035), fill=TEAL)
    return card


def record(path):
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        size = list(im.size)
    return {'file': str(path.relative_to(ROOT)), 'dimensions': size,
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def sheet(files, target, label, cols=5, thumb=(210, 470)):
    rows = (len(files) + cols - 1) // cols
    cell_w, cell_h = thumb[0] + 20, thumb[1] + 46
    result = Image.new('RGB', (cols * cell_w + 20, rows * cell_h + 60), '#eceff3')
    d = ImageDraw.Draw(result)
    d.text((20, 18), label, font=font(26, SANS), fill='#3a4652')
    for i, path in enumerate(files):
        x, y = 20 + (i % cols) * cell_w, 60 + (i // cols) * cell_h
        with Image.open(path) as im:
            piece = ImageOps.contain(im.convert('RGB'), thumb, Image.LANCZOS)
        d.text((x, y), path.name[:2], font=font(18, LATIN), fill='#44525f')
        result.paste(piece, (x, y + 24))
    result.save(target, quality=93)


def main():
    clean = sorted(CLEAN.glob('*.png'))
    sources = sorted((ROOT / '01-下载原图').glob('*.jpeg'))
    if len(clean) != 10:
        raise SystemExit(f'Need ten clean wallpapers, found {len(clean)}')
    if len(sources) != 4:
        raise SystemExit(f'Need four source images, found {len(sources)}')

    source_log = json.loads((ROOT / '01-下载原图' / '下载记录.json').read_text(encoding='utf-8'))
    for entry in source_log['images']:
        path = ROOT / '01-下载原图' / entry['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise SystemExit('Source hash mismatch: downloaded originals changed')

    LOCK.mkdir(exist_ok=True)
    HOME.mkdir(exist_ok=True)
    REPORT.mkdir(exist_ok=True)

    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in clean}
    for i, path in enumerate(clean, 1):
        with Image.open(path) as im:
            lock_overlay(im, i).save(LOCK / path.name, optimize=True)
        with Image.open(path) as im:
            home_overlay(im, i).save(HOME / path.name, optimize=True)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in clean}
    if before != after:
        raise SystemExit('Clean wallpapers were modified while rendering previews')

    locks = sorted(LOCK.glob('*.png'))
    homes = sorted(HOME.glob('*.png'))
    if len(locks) != 10 or len(homes) != 10:
        raise SystemExit('Preview counts are wrong')
    if [p.name for p in locks] != [p.name for p in clean] or [p.name for p in homes] != [p.name for p in clean]:
        raise SystemExit('Preview filenames do not match clean wallpapers')

    sheet(sources, REPORT / '下载原图总览.jpg', '参考原图 · 4 张（公开 CDN）')
    sheet(clean, REPORT / '无UI总览.jpg', '复刻壁纸 · 10 张（无手机 UI）')
    sheet(locks, REPORT / '锁屏预览总览.jpg', '锁屏预览 · 10 张（示意叠层）')
    sheet(homes, REPORT / '桌面组件总览.jpg', '桌面组件预览 · 10 张（示意叠层）')

    manifest = {
        'schema_version': 1,
        'status': 'complete',
        'note_id': source_log['note_id'],
        'source_count': len(sources),
        'clean_count': len(clean),
        'lock_preview_count': len(locks),
        'home_preview_count': len(homes),
        'style_reference': 'Only source image 01 was treated as the style anchor (retro screen-print Budapest map, teal sky).',
        'generation': 'Ten independent image-conditioned AI generations; native 704x1520, not upscaled.',
        'ui': 'Deterministic illustrative lock-screen and widget-screen overlays; not device screenshots.',
        'sources': [record(p) for p in sources],
        'clean': [record(p) for p in clean],
        'lock_previews': [record(p) for p in locks],
        'home_previews': [record(p) for p in homes],
        'sheets': [record(p) for p in sorted(REPORT.glob('*.jpg'))],
    }
    (REPORT / '验收记录.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    archive = ROOT.parent / '布达佩斯秋日壁纸-完整交付.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(ROOT.rglob('*')):
            if path.is_file():
                zf.write(path, path.relative_to(ROOT.parent))
    with zipfile.ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f'Archive CRC failure at {bad}')
    print(f'Packaged {len(clean)} wallpapers, {len(locks)} lock previews, {len(homes)} widget previews')
    print(f'Archive: {archive} ({archive.stat().st_size} bytes)')


if __name__ == '__main__':
    sys.exit(main())
