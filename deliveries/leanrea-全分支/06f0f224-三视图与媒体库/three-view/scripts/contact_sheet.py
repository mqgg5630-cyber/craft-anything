#!/usr/bin/env python3
"""contact_sheet.py — 把一轮的图拼成「总预览图」和「六视图汇总图」。

两个模式：
  preview    带编号 + 标题 + 来源脚注的总预览（发布/交付用）
  turnaround 2×3 六视图汇总（正/侧/背 × 两人），无字，喂给下游 AI 当参考图

用法：
  python3 scripts/contact_sheet.py preview \
      --indir examples/round-01 --out examples/round-01/11_总预览.jpg \
      --title "一二布布 三视图复刻 · 10 张" --font /tmp/fonts/LXGWWenKaiLite-Regular.ttf

  python3 scripts/contact_sheet.py turnaround \
      --indir examples/round-01 --out examples/round-01/10_六视图汇总.png

只依赖 Pillow。中文字体建议霞鹜文楷（scripts/fetch_font.sh）；没有中文字体时
标题会自动降级成文件名，不会出现豆腐块。
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# ---------- 字体 ----------
FONT_CANDIDATES = [
    os.environ.get("SHEET_FONT", ""),
    os.path.expanduser("~/.fonts/LXGWWenKaiLite-Regular.ttf"),
    os.path.expanduser("~/.fonts/LXGWWenKai-Regular.ttf"),
    "/tmp/fonts/LXGWWenKaiLite-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def load_font(size: int):
    for p in FONT_CANDIDATES:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size), p
            except OSError:
                continue
    return ImageFont.load_default(), ""


def has_cjk(path: str) -> bool:
    """粗判字体是否含中文：文泉驿/文楷/Noto 都含，DejaVu 不含。"""
    low = os.path.basename(path).lower()
    return not ("dejavu" in low or "mono" in low and "wenkai" not in low)


# ---------- 通用 ----------
def collect(indir: str, skip_prefixes=("11_", "preview")):
    files = []
    for p in sorted(glob.glob(os.path.join(indir, "*.png")) + glob.glob(os.path.join(indir, "*.jpg"))):
        name = os.path.basename(p)
        if any(name.startswith(s) for s in skip_prefixes):
            continue
        files.append(p)
    files.sort(key=lambda p: os.path.basename(p))
    return files


def trim(im: Image.Image, bg_tol: int = 8) -> Image.Image:
    """按四角底色裁掉多余留白，让每格主体大小一致。"""
    rgb = im.convert("RGB")
    w, h = rgb.size
    corners = [rgb.getpixel((0, 0)), rgb.getpixel((w - 1, 0)),
               rgb.getpixel((0, h - 1)), rgb.getpixel((w - 1, h - 1))]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    px = rgb.load()
    step = max(1, min(w, h) // 400)

    def row_empty(y):
        return all(abs(px[x, y][0] - bg[0]) <= bg_tol and abs(px[x, y][1] - bg[1]) <= bg_tol
                   and abs(px[x, y][2] - bg[2]) <= bg_tol for x in range(0, w, step))

    def col_empty(x):
        return all(abs(px[x, y][0] - bg[0]) <= bg_tol and abs(px[x, y][1] - bg[1]) <= bg_tol
                   and abs(px[x, y][2] - bg[2]) <= bg_tol for y in range(0, h, step))

    top, bottom = 0, h - 1
    while top < bottom and row_empty(top):
        top += 1
    while bottom > top and row_empty(bottom):
        bottom -= 1
    left, right = 0, w - 1
    while left < right and col_empty(left):
        left += 1
    while right > left and col_empty(right):
        right -= 1
    if right <= left or bottom <= top:
        return im
    return im.crop((left, top, right + 1, bottom + 1))


def fit(im: Image.Image, box_w: int, box_h: int) -> Image.Image:
    im = im.copy()
    im.thumbnail((box_w, box_h), Image.LANCZOS)
    return im


# ---------- 模式一：总预览 ----------
def build_preview(indir, out, title, cols, cell, pad, bg, fg, note):
    files = collect(indir, skip_prefixes=("11_", "preview"))
    if not files:
        sys.exit(f"没找到图片：{indir}")
    font, font_path = load_font(int(cell * 0.085))
    cjk = has_cjk(font_path)
    small, _ = load_font(int(cell * 0.062))

    rows = (len(files) + cols - 1) // cols
    header = int(cell * 0.42) if (title and cjk) else int(cell * 0.10)
    footer = int(cell * 0.22) if (note and cjk) else int(cell * 0.05)
    W = pad + cols * (cell + pad)
    H = header + pad + rows * (cell + pad + int(cell * 0.16)) + footer
    canvas = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(canvas)

    if title:
        text = title if cjk else os.path.basename(os.path.abspath(indir))
        tw = d.textlength(text, font=font)
        d.text(((W - tw) / 2, header * 0.28), text, font=font, fill=fg)

    for i, p in enumerate(files):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = header + pad + r * (cell + pad + int(cell * 0.16))
        tile = Image.new("RGB", (cell, cell), "#FFFFFF")
        im = trim(Image.open(p).convert("RGB"))
        th = fit(im, int(cell * 0.92), int(cell * 0.92))
        tile.paste(th, ((cell - th.width) // 2, (cell - th.height) // 2))
        d.rectangle([x, y, x + cell, y + cell], outline="#E6E2DA", width=max(1, cell // 400))
        canvas.paste(tile, (x, y))
        label = os.path.splitext(os.path.basename(p))[0]
        if not cjk:
            label = f"{i + 1:02d}"
        d.text((x + cell * 0.04, y + cell + cell * 0.03), label, font=small, fill="#6B6259")

    if note:
        text = note if cjk else ""
        if text:
            tw = d.textlength(text, font=small)
            d.text(((W - tw) / 2, H - footer * 0.85), text, font=small, fill="#8A8177")

    canvas.save(out, quality=95, subsampling=0)
    print(f"{out}  {canvas.size[0]}×{canvas.size[1]}  {len(files)} 张")


# ---------- 模式二：2×3 六视图汇总 ----------
TURNAROUND_ORDER = ["01_", "02_", "03_", "04_", "05_", "06_"]


def build_turnaround(indir, out, cell, gap, bg):
    picks = []
    for pref in TURNAROUND_ORDER:
        hit = [p for p in collect(indir, skip_prefixes=("10_", "11_"))
               if os.path.basename(p).startswith(pref)]
        if not hit:
            sys.exit(f"缺少 {pref}*：{indir}")
        picks.append(hit[0])

    W = gap * 4 + cell * 3
    H = gap * 3 + cell * 2
    canvas = Image.new("RGB", (W, H), bg)
    for i, p in enumerate(picks):
        r, c = divmod(i, 3)
        x = gap + c * (cell + gap)
        y = gap + r * (cell + gap)
        tile = Image.new("RGB", (cell, cell), bg)
        im = trim(Image.open(p).convert("RGB"))
        th = fit(im, int(cell * 0.94), int(cell * 0.94))
        tile.paste(th, ((cell - th.width) // 2, (cell - th.height) // 2))
        canvas.paste(tile, (x, y))
    canvas.save(out)
    print(f"{out}  {W}×{H}  6 视图")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preview", "turnaround"])
    ap.add_argument("--indir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--cell", type=int, default=520)
    ap.add_argument("--pad", type=int, default=28)
    ap.add_argument("--gap", type=int, default=40)
    ap.add_argument("--bg", default="#F7F5F0")
    ap.add_argument("--fg", default="#3A1F12")
    a = ap.parse_args()
    if a.mode == "preview":
        build_preview(a.indir, a.out, a.title, a.cols, a.cell, a.pad, a.bg, a.fg, a.note)
    else:
        build_turnaround(a.indir, a.out, a.cell, a.gap, a.bg)


if __name__ == "__main__":
    main()
