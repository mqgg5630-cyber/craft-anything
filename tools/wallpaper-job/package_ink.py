"""Deterministic lock-screen / home-screen previews, contact sheets and archive for the ink note.

Wallpapers are AI generated. This script only composites illustrative previews onto copies and
validates the delivery; it never draws on a clean wallpaper.
"""
import hashlib
import json
import random
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path('deliveries/ink-bunny-fox-127')
FONT_DIR = Path('.cache/wheels/mpl/mplfonts/fonts')
LATIN = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
SANS = FONT_DIR / 'NotoSansCJKsc-Regular.otf'

INK = (40, 40, 42)
WARM = (255, 176, 88)
CLEAN = ROOT / '02-复刻无手机UI'
LOCK = ROOT / '03-锁屏预览'
HOME = ROOT / '04-桌面预览'
REPORT = ROOT / '05-说明与验收'


def font(size, path=LATIN):
    return ImageFont.truetype(str(path), size)


def lock_overlay(image, number):
    """Illustrative lock screen: date above a thin large clock, as in the note's own layout."""
    image = image.convert('RGBA')
    w, h = image.size
    layer = Image.new('RGBA', image.size)
    d = ImageDraw.Draw(layer)
    d.text((w / 2, h * .088), '8月12日 星期二', font=font(round(w * .034), SANS), fill=INK + (215,), anchor='mt')
    d.text((w / 2, h * .112), '13:14', font=font(round(w * .155), LATIN), fill=INK + (225,), anchor='mt')
    d.text((w * .5, h * .028), '23:55', font=font(round(w * .026), LATIN), fill=INK + (200,), anchor='mt')
    bx, by = round(w * .74), round(h * .028)
    for i in range(4):
        d.rounded_rectangle((bx + i * 6, by + 10 - i * 3, bx + i * 6 + 4, by + 13), radius=1, fill=INK + (200,))
    d.rounded_rectangle((bx + 30, by, bx + 60, by + 14), radius=4, outline=INK + (200,), width=2)
    d.rounded_rectangle((bx + 33, by + 3, bx + 54, by + 11), radius=2, fill=INK + (200,))
    # Two small round lock-screen shortcuts, as drawn in the note's mockups.
    for x, kind in ((w * .14, 'light'), (w * .86, 'camera')):
        cy, r = h * .915, w * .052
        d.ellipse((x - r, cy - r, x + r, cy + r), fill=(28, 28, 30, 130), outline=(255, 255, 255, 120), width=2)
        if kind == 'camera':
            d.rounded_rectangle((x - w * .022, cy - w * .014, x + w * .022, cy + w * .016),
                                radius=round(w * .007), outline=(255, 255, 255, 230), width=3)
            d.ellipse((x - w * .009, cy - w * .007, x + w * .009, cy + w * .011),
                      outline=(255, 255, 255, 230), width=3)
        else:
            d.polygon([(x - w * .016, cy - w * .019), (x + w * .016, cy - w * .019),
                       (x + w * .010, cy - w * .004), (x + w * .008, cy + w * .019),
                       (x - w * .008, cy + w * .019), (x - w * .010, cy - w * .004)],
                      fill=(255, 255, 255, 230))
    d.rounded_rectangle((w * .35, h * .972, w * .65, h * .978), radius=3, fill=(255, 255, 255, 210))
    return Image.alpha_composite(image, layer).convert('RGB')


ICONS = ['相机', '照片', '邮件', '备忘录', '时钟', '地图', '天气', '音乐',
         '相册', '日历', '文件', '设置', '商店', '播客', '健康', '钱包']


def home_overlay(image, number):
    """Illustrative home screen: blurred wallpaper, a frosted widget card and an icon grid."""
    src = image.convert('RGB')
    w, h = src.size
    base = src.resize((max(1, w // 6), max(1, h // 6)), Image.LANCZOS)
    base = base.filter(ImageFilter.GaussianBlur(6)).resize((w, h), Image.LANCZOS)
    base = Image.blend(base, Image.new('RGB', (w, h), (92, 88, 86)), .10)
    layer = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(layer)

    d.text((w * .5, h * .030), '23:55', font=font(round(w * .028), LATIN), fill=(255, 255, 255, 235), anchor='mt')

    card = (round(w * .055), round(h * .075), round(w * .945), round(h * .965))
    d.rounded_rectangle(card, radius=round(w * .075), fill=(240, 238, 236, 58))
    cols, rows = 4, 4
    left, right = w * .115, w * .885
    top = h * .135
    step_x = (right - left) / (cols - 1)
    step_y = h * .165
    labels = [font(round(w * .021), SANS) for _ in range(cols)]
    for i, name in enumerate(ICONS[:cols * rows]):
        cx = left + (i % cols) * step_x
        cy = top + (i // cols) * step_y
        rad = w * .058
        d.rounded_rectangle((cx - rad, cy - rad, cx + rad, cy + rad), radius=round(w * .026),
                            fill=(252, 250, 248, 120), outline=(255, 255, 255, 120), width=2)
        warm = (WARM[0], WARM[1], WARM[2], 210)
        k = i % 4
        if k == 0:
            d.ellipse((cx - rad * .42, cy - rad * .42, cx + rad * .42, cy + rad * .42), outline=warm, width=3)
            d.ellipse((cx - rad * .16, cy - rad * .16, cx + rad * .16, cy + rad * .16), fill=warm)
        elif k == 1:
            d.line((cx, cy - rad * .55, cx + rad * .55, cy + rad * .30), fill=warm, width=4)
            d.line((cx, cy + rad * .55, cx + rad * .55, cy + rad * .30), fill=warm, width=4)
        elif k == 2:
            for j in range(3):
                d.line((cx - rad * .5, cy - rad * .3 + j * rad * .30, cx + rad * .5, cy - rad * .3 + j * rad * .30),
                       fill=warm, width=3)
        else:
            d.arc((cx - rad * .55, cy - rad * .55, cx + rad * .55, cy + rad * .55), 0, 300, fill=warm, width=4)
        d.text((cx, cy + rad + h * .012), name, font=labels[0], fill=(255, 255, 255, 240), anchor='mt')

    dock_top = h * .845
    d.rounded_rectangle((round(w * .115), round(dock_top), round(w * .885), round(h * .945)),
                        radius=round(w * .085), fill=(238, 236, 234, 110))
    for i in range(4):
        cx = w * .19 + i * w * .207
        cy = dock_top + h * .04
        rad = w * .056
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=(255, 255, 255, 120))
    d.rounded_rectangle((w * .35, h * .972, w * .65, h * .978), radius=3, fill=(255, 255, 255, 220))
    return Image.alpha_composite(base.convert('RGBA'), layer).convert('RGB')


def record(path):
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        size = list(im.size)
    return {'file': str(path.relative_to(ROOT)), 'dimensions': size,
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def sheet(files, target, label, thumb=(210, 400), cols=5):
    if not files:
        return
    rows = (len(files) + cols - 1) // cols
    cell_w, cell_h = thumb[0] + 20, thumb[1] + 46
    result = Image.new('RGB', (cols * cell_w + 20, rows * cell_h + 60), '#e9e9ea')
    d = ImageDraw.Draw(result)
    d.text((20, 18), label, font=font(26, SANS), fill='#3a3a3c')
    for i, path in enumerate(files):
        x, y = 20 + (i % cols) * cell_w, 60 + (i // cols) * cell_h
        with Image.open(path) as im:
            piece = ImageOps.contain(im.convert('RGB'), thumb, Image.LANCZOS)
        d.text((x, y), path.name[:2], font=font(18, LATIN), fill='#4a4a4c')
        result.paste(piece, (x, y + 24))
    result.save(target, quality=92)


def main():
    clean = sorted(CLEAN.glob('*.png'))
    sources = sorted((ROOT / '01-下载原图').glob('*.png')) + sorted((ROOT / '01-下载原图').glob('*.jpeg'))
    sources = sorted(sources, key=lambda p: p.name)
    if len(clean) < 6:
        raise SystemExit('Not enough clean wallpapers to package')
    log = json.loads((ROOT / '01-下载原图' / '下载记录.json').read_text(encoding='utf-8'))
    for entry in log['images']:
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
    sheet(sources, REPORT / '下载原图总览.jpg', '参考原图（公开 CDN）', thumb=(300, 400), cols=3)
    sheet(clean, REPORT / '无UI总览.jpg', f'复刻壁纸 · {len(clean)} 张（无手机 UI）')
    sheet(locks, REPORT / '锁屏预览总览.jpg', f'锁屏预览 · {len(locks)} 张（示意叠层）')
    sheet(homes, REPORT / '桌面预览总览.jpg', f'桌面预览 · {len(homes)} 张（示意叠层）')

    manifest = {
        'schema_version': 1,
        'status': 'complete' if len(clean) == 10 else 'partial',
        'note_id': log['note_id'],
        'source_count': len(sources),
        'clean_count': len(clean),
        'lock_preview_count': len(locks),
        'home_preview_count': len(homes),
        'style_anchor': 'Source 02 (portrait art, 1080x1440) is the only clean art reference; 01/03/04/05/06 are device mockups of the same art.',
        'lively_note': 'Two LIVE items (02, 03) are animated in the app; only their cover frames are downloadable.',
        'ui': 'Deterministic illustrative lock and home previews; not device screenshots.',
        'sources': [record(p) for p in sources],
        'clean': [record(p) for p in clean],
        'lock_previews': [record(p) for p in locks],
        'home_previews': [record(p) for p in homes],
        'sheets': [record(p) for p in sorted(REPORT.glob('*.jpg'))],
    }
    (REPORT / '验收记录.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(clean)} clean, {len(locks)} lock, {len(homes)} home, {len(sources)} sources')


if __name__ == '__main__':
    sys.exit(main())
