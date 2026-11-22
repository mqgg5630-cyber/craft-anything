"""Typeset ten short Chinese romantic quotes on the existing text-free artworks.
Run from repository root with .venv/bin/python; no new AI generation.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE = ROOT.parent / 'little-prince-no-text-r5'
FONT = REPO / 'assets/fonts/cjk/NotoSansCJKsc-Regular.otf'
QUOTES = ['星河予你', '月色为你', '此心向你', '与你朝夕', '余生是你',
          '黄昏有你', '心动不息', '温柔予你', '岁岁相依', '此生与你']
# Normalized center position chosen from the inspected R5 compositions; avoid faces/moons.
POSITIONS = [(.62,.36), (.57,.38), (.53,.34), (.65,.39), (.50,.34),
             (.61,.36), (.65,.35), (.58,.39), (.52,.39), (.55,.39)]


def spaced_text(draw, center, text, font, fill, spacing=8, stroke_width=0, stroke_fill=None):
    widths = [draw.textlength(c, font=font) for c in text]
    x = center[0] - (sum(widths) + spacing*(len(text)-1))/2
    for c, width in zip(text, widths):
        draw.text((round(x), center[1]), c, font=font, fill=fill,
                  stroke_width=stroke_width, stroke_fill=stroke_fill)
        x += width + spacing


def main():
    out = ROOT / 'images'
    out.mkdir(parents=True, exist_ok=True)
    files = sorted((SOURCE / 'images').glob('*.png'))
    assert len(files) == len(QUOTES) == 10
    records = []
    for i, (path, quote, pos) in enumerate(zip(files, QUOTES, POSITIONS)):
        image = Image.open(path).convert('RGB')
        w,h = image.size
        font = ImageFont.truetype(str(FONT), 30)
        xy = (int(w*pos[0]), int(h*pos[1]))
        shadow = Image.new('RGBA', image.size)
        spaced_text(ImageDraw.Draw(shadow), (xy[0],xy[1]+2), quote, font,
                    (21,24,26,220), stroke_width=2, stroke_fill=(21,24,26,180))
        image = Image.alpha_composite(image.convert('RGBA'), shadow.filter(ImageFilter.GaussianBlur(3)))
        spaced_text(ImageDraw.Draw(image), xy, quote, font, '#ffe4ad')
        p = out / f'{i+1:02d}-{quote}.png'
        image.convert('RGB').save(p)
        records.append({'file':str(p.relative_to(ROOT)), 'quote':quote,
                        'source':str(path.relative_to(REPO)), 'size':[w,h],
                        'text_top_center':list(pos), 'font_size':30, 'letter_spacing':8,
                        'bytes':p.stat().st_size, 'md5':hashlib.md5(p.read_bytes()).hexdigest()})
    board = Image.new('RGB', (1700,1370), '#17252b')
    draw = ImageDraw.Draw(board)
    draw.text((30,20),'小王子 · 浪漫短句版｜一张一句 · 原画不变',
              font=ImageFont.truetype(str(FONT),27), fill='#f9df9a')
    for i,record in enumerate(records):
        im = Image.open(ROOT / record['file'])
        im.thumbnail((310,565))
        x=25+i%5*335; y=80+i//5*640
        board.paste(im,(x+(310-im.width)//2,y))
        draw.text((x,y+575),f'{i+1:02d} · {record["quote"]}',
                  font=ImageFont.truetype(str(FONT),22), fill='#efdab3')
    board.save(ROOT/'00-浪漫短句十张总览.jpg', quality=95)
    (ROOT/'manifest.json').write_text(json.dumps({'count':10,'new_generation_calls':0,
        'process':'Deterministic Chinese typography over R5 text-free artwork; no new AI painting.',
        'files':records},ensure_ascii=False,indent=2))
    for record in records:
        with Image.open(ROOT / record['file']) as im:
            im.load()
            assert list(im.size) == record['size']
    assert len({r['md5'] for r in records})==10
    print('PASS ten independent PNGs; accurate quote strings; dimensions/decode/unique hashes')

if __name__ == '__main__':
    main()
