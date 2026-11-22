"""Render simulated lock-screen overlays without changing clean AI outputs.
Overlay drawing reused from the successful 2d4fad4b delivery; all manifests rebuilt.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CLEAN, UI, SOURCE = ROOT / 'images', ROOT / 'ui', ROOT / 'source'
CJK = REPO / 'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
DIGITS = REPO / 'assets/fonts/DMSans-Medium.ttf'
DIGITS_BOLD = REPO / 'assets/fonts/DMSans-Bold.ttf'
TIME, DATE = '18:30', '11月22日 星期日'
PLAN = [
('湖畔依偎', ['01','04'], '码头依偎，双脚垂在木板边缘'),
('回头等你', ['02','04'], '草坡小路上回头伸手'),
('草地看云', ['03','04'], '草地并排躺下牵手看云'),
('牵手过溪', ['04'], '溪石间牵手扶她迈步'),
('山路同行', ['05','04'], '山路上指向河谷远景'),
('分你橘子', ['01','04'], '码头面对面分享橘子'),
('蒲公英之约', ['02','04'], '草坡一起吹蒲公英'),
('山顶日落', ['03','05'], '山顶搂肩背影看日落'),
('背你过河', ['04','03'], '背着她跨过溪石'),
('奔向夕阳', ['05','04'], '牵手跑向落日河谷'),
]
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
    if [p.name for p in clean] != [f'{i:02d}.png' for i in range(1,11)]:
        raise ValueError('Expected exactly 10 independent wallpapers')
    before = {p.name: md5(p) for p in clean}
    UI.mkdir(exist_ok=True)
    records = []
    for i, path in enumerate(clean):
        with Image.open(path) as im:
            im.load()
            size = list(im.size)
            overlay(im).save(UI/path.name, optimize=True)
        title, refs, change = PLAN[i]
        for kind, out in [('no_ui', path), ('simulated_ui', UI/path.name)]:
            data = out.read_bytes()
            records.append({'file': str(out.relative_to(ROOT)), 'kind': kind, 'title': title,
                'references': [f'source/{r}.png' for r in refs], 'change': change,
                'width': size[0], 'height': size[1], 'bytes': len(data),
                'md5': hashlib.md5(data).hexdigest(), 'sha256': hashlib.sha256(data).hexdigest()})
    assert before == {p.name: md5(p) for p in clean}
    sheet(clean, ROOT/'00-无UI总预览.jpg', 5, (270,484))
    sheet(sorted(UI.glob('*.png')), ROOT/'00-有UI总预览.jpg', 5, (270,484))
    sheet(sorted(SOURCE.glob('*.png')), ROOT/'00-原片总预览.jpg', 5, (270,480))
    # One overall review board: original row, ten clean outputs, ten UI previews.
    previews = [('原片 · 5张 · GitHub Actions下载核验', ROOT/'00-原片总预览.jpg'),
                ('独立复刻 · 10张 · 无UI', ROOT/'00-无UI总预览.jpg'),
                ('模拟锁屏 · 10张 · 有UI', ROOT/'00-有UI总预览.jpg')]
    width, pad, heading = 1482, 36, 70
    height = sum(Image.open(p).height + heading + pad for _,p in previews) + pad
    board = Image.new('RGB', (width,height), '#fff7ed'); d=ImageDraw.Draw(board)
    y=pad
    for title,path in previews:
        d.text((pad,y), title, font=font(CJK,30), fill='#79523d'); y+=heading
        with Image.open(path) as im: board.paste(im, ((width-im.width)//2,y)); y+=im.height+pad
    board.save(ROOT/'00-总预览.jpg',quality=91)
    (ROOT/'output-manifest.json').write_text(json.dumps({
        'generated_count':10,'ui_count':10, 'status':'pending_visual_review',
        'ui_note':'Generic simulated lock screen, not a real screenshot or installable theme',
        'native_size_note':'Model-native outputs; no interpolation or upscaling',
        'files':records},ensure_ascii=False,indent=2)+'\n')
    print('Rendered 10 UI images and four review boards')

if __name__ == '__main__':
    main()
