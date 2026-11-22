"""Overlay short romantic Chinese captions onto the 10 Little Prince replicas.

Runs on the GitHub Actions runner (which has Pillow + an installed CJK font).
Reads deliveries/little-prince-xhs-10/images/*.png and writes captioned copies to
deliveries/little-prince-xhs-10/images-captioned/.
"""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

SRC = Path('deliveries/little-prince-xhs-10/images')
OUT = Path('deliveries/little-prince-xhs-10/images-captioned')
OUT.mkdir(parents=True, exist_ok=True)

# One short romantic line per replica, matched to its mood.
PHRASES = {
    '01-深蓝星河.png': '宇宙温柔，星光不落',
    '02-深蓝流星.png': '愿流星替我说晚安',
    '03-深蓝月光.png': '月光很慢，刚好够想你',
    '04-深蓝玫瑰.png': '你是我用心浇灌的玫瑰',
    '05-粉橙黄昏.png': '落日橘粉，等你同行的风',
    '06-黄昏晚风.png': '晚风很轻，喜欢很满',
    '07-黄昏星愿.png': '对星星许的愿，都关于你',
    '08-暖调晨光.png': '晨光落满，万物可期',
    '09-晨光花语.png': '花开了，春天也向你走来',
    '10-晨光远行.png': '远方很远，我慢慢去见你',
}

FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]


def load_font(size):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    raise RuntimeError('No usable CJK font found for caption overlay')


def add_caption(src: Path, phrase: str) -> Image.Image:
    im = Image.open(src).convert('RGBA')
    w, h = im.size
    font_size = max(28, int(w * 0.058))
    font = load_font(font_size)
    cx = w // 2
    y = int(h * 0.06)  # upper sky area, safe from the subject
    draw = ImageDraw.Draw(im)
    # soft shadow first, then the cream text on top for legibility
    draw.text((cx + 2, y + 2), phrase, font=font, fill=(16, 24, 42, 190), anchor='mt')
    draw.text((cx, y), phrase, font=font, fill=(245, 238, 214, 255), anchor='mt')
    return im.convert('RGB')


def main():
    done = 0
    for name, phrase in PHRASES.items():
        src = SRC / name
        if not src.exists():
            print('MISSING', src, flush=True)
            continue
        add_caption(src, phrase).save(OUT / name, optimize=True)
        print(f'captioned {name}: {phrase}', flush=True)
        done += 1
    print(f'Done: {done} captions', flush=True)
    if done != 10:
        sys.exit(1)


if __name__ == '__main__':
    main()
