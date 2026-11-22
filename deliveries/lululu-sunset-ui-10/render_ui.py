"""Build the UI (lock-screen mock-up) versions, previews and manifest for this delivery.

Reads the clean images in 复刻结果/无UI, never modifies them, and writes
复刻结果/有UI (same file names), 00-总览-*.jpg previews and output-manifest.json.
The UI is a generic illustrative lock screen, not a real device screenshot.
Run from the repository root:  .venv/bin/python deliveries/lululu-sunset-ui-10/render_ui.py
"""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CLEAN = ROOT / '复刻结果' / '无UI'
UI = ROOT / '复刻结果' / '有UI'
SOURCE = ROOT / '原片'
CJK = REPO / 'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
DIGITS = REPO / 'assets/fonts/DMSans-Medium.ttf'
DIGITS_BOLD = REPO / 'assets/fonts/DMSans-Bold.ttf'

# Output -> reference mapping and the change made relative to that reference.
PLAN = {
    '01-湖畔依偎.png': ('01.png', '码头背影依偎，取景更近，太阳更低'),
    '02-追着你跑.png': ('02.png', '草坡小路追逐，男孩回头挥手'),
    '03-草地看云.png': ('03.png', '草地并排躺下牵手对望'),
    '04-牵手过溪.png': ('04.png', '踩石过溪，牵手扶她跳过'),
    '05-山路同行.png': ('05.png', '山路牵手同行，侧后方视角'),
    '06-晚霞飞鸟.png': ('01.png', '码头对坐递橘子，远处飞鸟'),
    '07-回头等你.png': ('02.png', '蒲公英草坡，回头伸手等她'),
    '08-山顶看日落.png': ('03.png', '山顶背影搂肩远眺河谷'),
    '09-背你回家.png': ('04.png', '溪石上背着她过河'),
    '10-奔向夕阳.png': ('05.png', '正后方牵手奔向夕阳'),
}
# Visual review result (2026-11-22): identity drift found in these two outputs.
KNOWN_DEFECTS = {
    '03-草地看云.png': '妹妹脸部被画成人类娃娃脸并带黑发，与原片黄色毛绒猪脸不符，待返工',
    '06-晚霞飞鸟.png': '妹妹脸部偏人类娃娃脸带棕发，与原片黄色毛绒猪脸不符，待返工',
}
TIME, DATE = '18:30', '11月22日 星期日'


def font(path, size):
    return ImageFont.truetype(str(path), size)


def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def overlay(image):
    base = image.convert('RGBA')
    w, h = base.size
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    shadow = Image.new('RGBA', base.size, (0, 0, 0, 0))
    d, s = ImageDraw.Draw(layer), ImageDraw.Draw(shadow)
    ink, soft = (255, 255, 255, 245), (90, 45, 20, 110)

    def text(xy, value, fnt, anchor):
        s.text(xy, value, font=fnt, fill=soft, anchor=anchor)
        d.text(xy, value, font=fnt, fill=ink, anchor=anchor)

    # Status bar
    small = font(DIGITS, round(w * .036))
    text((w * .085, h * .028), TIME, small, 'lm')
    bx, by = w * .86, h * .028
    for i in range(4):  # signal bars
        bh = w * (.010 + i * .005)
        d.rounded_rectangle((w * .72 + i * w * .014, by + w * .012 - bh, w * .72 + i * w * .014 + w * .008, by + w * .012), 2, fill=ink)
    d.rounded_rectangle((bx, by - w * .013, bx + w * .06, by + w * .013), round(w * .008), outline=ink, width=2)
    d.rounded_rectangle((bx + 4, by - w * .013 + 4, bx + w * .045, by + w * .013 - 4), round(w * .005), fill=ink)
    d.rounded_rectangle((bx + w * .063, by - w * .005, bx + w * .068, by + w * .005), 2, fill=ink)
    # Lock icon, date and clock in the clear sky area
    lx, ly = w / 2, h * .075
    d.rounded_rectangle((lx - w * .018, ly, lx + w * .018, ly + w * .03), 4, fill=ink)
    d.arc((lx - w * .012, ly - w * .02, lx + w * .012, ly + w * .012), 180, 360, fill=ink, width=3)
    text((w / 2, h * .125), DATE, font(CJK, round(w * .042)), 'mm')
    text((w / 2, h * .215), TIME, font(DIGITS_BOLD, round(w * .23)), 'mm')
    # Bottom quick actions and home indicator
    r = w * .062
    for cx in (w * .16, w * .84):
        cy = h * .905
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(40, 25, 15, 95))
    fx, fy = w * .16, h * .905  # flashlight glyph
    d.rounded_rectangle((fx - w * .012, fy - w * .005, fx + w * .012, fy + w * .03), 3, fill=ink)
    d.polygon([(fx - w * .02, fy - w * .03), (fx + w * .02, fy - w * .03), (fx + w * .012, fy - w * .005), (fx - w * .012, fy - w * .005)], fill=ink)
    cx, cy = w * .84, h * .905  # camera glyph
    d.rounded_rectangle((cx - w * .03, cy - w * .018, cx + w * .03, cy + w * .022), 5, outline=ink, width=3)
    d.ellipse((cx - w * .011, cy - w * .009, cx + w * .011, cy + w * .013), outline=ink, width=3)
    d.rounded_rectangle((w * .34, h * .975, w * .66, h * .975 + max(4, w * .008)), 4, fill=ink)
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, w // 220)))
    return Image.alpha_composite(Image.alpha_composite(base, shadow), layer).convert('RGB')


def sheet(paths, target, cols, cell):
    rows = -(-len(paths) // cols)
    cw, ch = cell
    out = Image.new('RGB', (cols * cw + (cols + 1) * 12, rows * ch + (rows + 1) * 12), (255, 248, 240))
    for i, path in enumerate(paths):
        with Image.open(path) as im:
            out.paste(im.convert('RGB').resize(cell, Image.LANCZOS), (12 + (i % cols) * (cw + 12), 12 + (i // cols) * (ch + 12)))
    out.save(target, quality=90)


def main():
    clean = sorted(CLEAN.glob('*.png'))
    if [p.name for p in clean] != sorted(PLAN):
        raise SystemExit(f'Expected exactly the 10 planned clean images, found {[p.name for p in clean]}')
    UI.mkdir(parents=True, exist_ok=True)
    before = {p.name: md5(p) for p in clean}
    files = []
    for path in clean:
        with Image.open(path) as im:
            im.load()
            size = list(im.size)
            ui_image = overlay(im)
        ui_path = UI / path.name
        ui_image.save(ui_path, optimize=True)
        ref, change = PLAN[path.name]
        for kind, p in (('无UI', path), ('有UI', ui_path)):
            files.append({'file': str(p.relative_to(ROOT)), 'kind': kind, 'reference': f'原片/{ref}',
                          'change': change, 'size': size, 'bytes': p.stat().st_size, 'md5': md5(p),
                          'known_defect': KNOWN_DEFECTS.get(path.name)})
    if before != {p.name: md5(p) for p in clean}:
        raise SystemExit('Clean images changed during rendering')
    sheet(clean, ROOT / '00-总览-无UI.jpg', 5, (300, 537))
    sheet(sorted(UI.glob('*.png')), ROOT / '00-总览-有UI.jpg', 5, (300, 537))
    sheet(sorted(SOURCE.glob('*.png')), ROOT / '00-总览-原片.jpg', 5, (300, 533))
    manifest = {'route': 'xhs-link-recreate-10 + user-requested UI versions',
                'generated_count': 10, 'ui_count': 10,
                'native_size_note': '768x1376 model-native output; not upscaled',
                'ui_note': 'Generic illustrative lock screen overlay; not a real device screenshot or theme.',
                'known_defects': KNOWN_DEFECTS, 'files': files}
    (ROOT / 'output-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'rendered {len(clean)} UI images; {len(files)} records')


if __name__ == '__main__':
    main()
