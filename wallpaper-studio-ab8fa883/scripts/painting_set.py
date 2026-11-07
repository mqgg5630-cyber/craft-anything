#!/usr/bin/env python3
"""painting_set.py —— 把一组「名画风」底图统一成同一画幅，并拼一张带说明文字的总图。

和 phone_mockup.py 的区别：这里不是手机壁纸，不做任何覆盖层；画幅跟随原帖（默认 1532×2560），
每张可以指定裁切锚点（top/center/bottom，防止把主体裁掉），总图下方带「画家·作品」说明。

用法：
  python3 scripts/painting_set.py SPEC.json --art-dir ART --out OUT [--format png|jpg] [--cjk-font F]

SPEC：
  {"title": "...", "subtitle": "...", "canvas": [1532, 2560], "prefix": "名画",
   "pages": [{"n": 1, "name": "梵高·向日葵", "anchor": "top"}, ...]}
"""
import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CJK_CANDS = ["~/.fonts/LXGWWenKai-Medium.ttf", "~/.fonts/LXGWWenKai-Regular.ttf",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
             "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"]


def find_font(explicit, cands):
    for p in ([explicit] if explicit else []) + [os.path.expanduser(c) for c in cands]:
        if p and os.path.exists(p):
            return p
    return None


def font(path, size):
    try:
        return ImageFont.truetype(path, size) if path else ImageFont.load_default()
    except OSError:
        return ImageFont.load_default()


def fit_cover(art: Image.Image, size, anchor="center") -> Image.Image:
    """等比放大到盖满 size，再按锚点裁切。"""
    W, H = size
    s = max(W / art.width, H / art.height)
    im = art.resize((round(art.width * s), round(art.height * s)), Image.LANCZOS)
    dx, dy = im.width - W, im.height - H
    if anchor == "top":
        box = (dx // 2, 0, dx // 2 + W, H)
    elif anchor == "bottom":
        box = (dx // 2, dy, dx // 2 + W, dy + H)
    elif anchor == "left":
        box = (0, dy // 2, W, dy // 2 + H)
    elif anchor == "right":
        box = (dx, dy // 2, dx + W, dy // 2 + H)
    else:
        box = (dx // 2, dy // 2, dx // 2 + W, dy // 2 + H)
    return im.crop(box)


def rounded(im: Image.Image, r: int) -> Image.Image:
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    out = im.copy()
    out.putalpha(mask)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--art-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--format", choices=["png", "jpg"], default="png")
    ap.add_argument("--cjk-font", default=None)
    a = ap.parse_args()

    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    W, H = spec.get("canvas", [1532, 2560])
    prefix = spec.get("prefix", "名画")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cjk = find_font(a.cjk_font, CJK_CANDS)
    if not cjk:
        print("warn: 没找到中文字体，总图标题会是方块；放一个到 ~/.fonts 或 --cjk-font", file=sys.stderr)

    finals = []
    for pg in spec["pages"]:
        src = Path(a.art_dir) / f"{pg['n']:02d}.png"
        if not src.exists():
            sys.exit(f"missing {src}")
        im = fit_cover(Image.open(src).convert("RGB"), (W, H), pg.get("anchor", "center"))
        name = f"{prefix}{pg['n']:02d}-{pg['name']}"
        if a.format == "png":
            p = out / f"{name}.png"
            im.save(p, "PNG", compress_level=6)
        else:
            p = out / f"{name}.jpg"
            im.save(p, "JPEG", quality=92, subsampling=0)
        finals.append((pg, im))
        print("[build]", p.name, im.size)

    # ---- 总图：2 行 × 5 列，米色底，圆角卡片，卡片下方写「画家·作品」
    cols = 5
    rows = (len(finals) + cols - 1) // cols
    tw = 300
    th = round(tw * H / W)
    gap, margin, header, caption = 28, 70, 150, 64
    sw = margin * 2 + cols * tw + (cols - 1) * gap
    sh = margin + header + rows * (th + caption) + (rows - 1) * gap + margin
    S = Image.new("RGB", (sw, sh), (241, 230, 212))
    d = ImageDraw.Draw(S)
    d.text((margin, margin - 10), spec.get("title", ""), font=font(cjk, 48), fill=(58, 46, 42))
    d.text((margin, margin + 56), spec.get("subtitle", ""), font=font(cjk, 24), fill=(120, 100, 92))
    for i, (pg, im) in enumerate(finals):
        x = margin + (i % cols) * (tw + gap)
        y = margin + header + (i // cols) * (th + caption + gap)
        card = rounded(im.resize((tw, th), Image.LANCZOS), 22)
        shadow = Image.new("RGBA", (tw + 16, th + 16), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((8, 10, tw + 8, th + 10), 24, fill=(90, 70, 50, 70))
        S.paste(shadow, (x - 8, y - 6), shadow)
        S.paste(card, (x, y), card)
        label = f"{pg['n']:02d}  {pg['name']}"
        f = font(cjk, 24)
        lw = d.textlength(label, font=f)
        d.text((x + (tw - lw) / 2, y + th + 16), label, font=f, fill=(78, 62, 56))
    sheet = out / "总图.jpg"
    S.save(sheet, "JPEG", quality=90)
    print("[sheet]", sheet, S.size)


if __name__ == "__main__":
    main()
