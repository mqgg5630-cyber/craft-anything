#!/usr/bin/env python3
"""Compose healing affirmation text onto textless watercolor backgrounds.

The image model only draws paper/doodles. All Chinese characters are typeset here
with deterministic fonts so the final wallpaper has crisp, correct text and no watermark.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HOME = Path.home()
FONTS = {
    "MaShanZheng": HOME / ".fonts/MaShanZheng-Regular.ttf",
    "LongCang": HOME / ".fonts/LongCang-Regular.ttf",
    "LXGWWenKai": HOME / ".fonts/LXGWWenKai-Medium.ttf",
    "ZCOOLKuaiLe": HOME / ".fonts/ZCOOLKuaiLe-Regular.ttf",
}


def hex_rgb(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


def fit_cover(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = (im.width - w) // 2
    y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def apply_variant(im: Image.Image, variant: dict | None) -> Image.Image:
    if not variant:
        return im
    if variant.get("flip"):
        im = ImageOps.mirror(im)
    hue = float(variant.get("hue", 0))
    sat = float(variant.get("sat", 1))
    bright = float(variant.get("bright", 1))
    if hue or sat != 1 or bright != 1:
        a = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
        # vectorized RGB->HSV
        mx = a.max(axis=2)
        mn = a.min(axis=2)
        df = mx - mn
        h = np.zeros_like(mx)
        mask = df > 1e-6
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        idx = mask & (mx == r)
        h[idx] = ((g[idx] - b[idx]) / df[idx]) % 6
        idx = mask & (mx == g)
        h[idx] = (b[idx] - r[idx]) / df[idx] + 2
        idx = mask & (mx == b)
        h[idx] = (r[idx] - g[idx]) / df[idx] + 4
        h = (h / 6.0 + hue / 360.0) % 1.0
        s = np.where(mx > 1e-6, df / np.maximum(mx, 1e-6), 0) * sat
        v = np.clip(mx * bright, 0, 1)
        s = np.clip(s, 0, 1)
        i = np.floor(h * 6).astype(int)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        i = i % 6
        out = np.zeros_like(a)
        conds = [i == 0, i == 1, i == 2, i == 3, i == 4, i == 5]
        vals = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
        for c, (rr, gg, bb) in zip(conds, vals):
            out[..., 0][c] = rr[c]
            out[..., 1][c] = gg[c]
            out[..., 2][c] = bb[c]
        im = Image.fromarray((out * 255).astype(np.uint8), "RGB")
    return im


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    p = FONTS.get(name) or FONTS["LXGWWenKai"]
    return ImageFont.truetype(str(p), size)


def text_layer(text: str, f: ImageFont.FreeTypeFont, fill, stroke=0, rotate=0.0):
    pad = 80
    tmp = Image.new("RGBA", (4000, 600), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((pad, pad), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=fill)
    bbox = d.textbbox((pad, pad), text, font=f, stroke_width=stroke)
    layer = tmp.crop((max(0, bbox[0] - 20), max(0, bbox[1] - 20), bbox[2] + 20, bbox[3] + 20))
    if rotate:
        layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
    return layer


def paste_center(base: Image.Image, layer: Image.Image, cx: float, cy: float):
    base.alpha_composite(layer, (round(cx - layer.width / 2), round(cy - layer.height / 2)))


def underline(base: Image.Image, cx: float, cy: float, width: float, color, seed=0):
    rnd = random.Random(seed)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0 = cx - width / 2
    x1 = cx + width / 2
    y = cy
    pts = []
    n = 24
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        yy = y + math.sin(t * math.pi * 2 + rnd.random()) * 3 + rnd.uniform(-1.5, 1.5)
        pts.append((x, yy))
    d.line(pts, fill=color, width=4, joint="curve")
    # little loop at end
    d.arc((x1 - 18, y - 10, x1 + 18, y + 18), start=20, end=300, fill=color, width=3)
    base.alpha_composite(layer)


def sparkle(base: Image.Image, cx: float, cy: float, size: float, color):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    s = size
    d.polygon([(cx, cy - s), (cx + s * 0.28, cy - s * 0.28), (cx + s, cy), (cx + s * 0.28, cy + s * 0.28), (cx, cy + s), (cx - s * 0.28, cy + s * 0.28), (cx - s, cy), (cx - s * 0.28, cy - s * 0.28)], fill=color)
    base.alpha_composite(layer)


def compose_page(bg: Image.Image, pg: dict, canvas: tuple[int, int]) -> Image.Image:
    W, H = canvas
    im = fit_cover(bg.convert("RGB"), canvas)
    im = apply_variant(im, pg.get("variant"))
    base = im.convert("RGBA")
    main_color = hex_rgb(pg.get("main_color", "#2F2A26")) + (255,)
    main_font_name = pg.get("main_font", "MaShanZheng")
    main_y = float(pg.get("main_y", 0.31)) * H
    lines = pg.get("main_lines") or [pg["line"]]
    # fit main text
    max_w = W * 0.82
    size = 250 if len(lines) > 1 else 230
    while size > 90:
        f = font(main_font_name, size)
        widths = [ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(line, font=f) for line in lines]
        if max(widths) <= max_w:
            break
        size -= 4
    f = font(main_font_name, size)
    line_h = size * 1.12
    total_h = line_h * len(lines)
    y0 = main_y - total_h / 2 + line_h / 2
    for i, line in enumerate(lines):
        rot = -2 if i % 2 == 0 else 1.5
        layer = text_layer(line, f, main_color, stroke=1 if main_font_name == "LongCang" else 0, rotate=rot)
        paste_center(base, layer, W / 2 + (i % 2) * 8, y0 + i * line_h)
    # small sparkles near main
    sparkle(base, W * 0.84, main_y - size * 0.45, 16, main_color[:3] + (160,))
    sparkle(base, W * 0.16, main_y + size * 0.35, 12, main_color[:3] + (130,))

    sub_font = font("LongCang", 70)
    for idx, sub in enumerate(pg.get("subs", [])):
        text, x, y, color, rot = sub
        fill = hex_rgb(color) + (235,)
        layer = text_layer(text, sub_font, fill, stroke=1, rotate=float(rot))
        cx, cy = float(x) * W, float(y) * H
        paste_center(base, layer, cx, cy)
        # underline a bit below text
        w = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(text, font=sub_font) * 0.92
        underline(base, cx, cy + 48, w, hex_rgb(color) + (170,), seed=pg["n"] * 100 + idx)
        if idx % 3 == 0:
            sparkle(base, cx + w / 2 + 28, cy - 28, 10, hex_rgb(color) + (150,))
    return base.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("--bg-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    canvas = tuple(spec.get("canvas", [1440, 2560]))
    a.out.mkdir(parents=True, exist_ok=True)
    thumbs = []
    for pg in spec["pages"]:
        bg_path = a.bg_dir / f"{pg['bg']}.png"
        bg = Image.open(bg_path)
        im = compose_page(bg, pg, canvas)
        out = a.out / f"{pg['n']:02d}.png"
        im.save(out, "PNG", compress_level=6)
        print("[compose]", out.name, im.size, pg["line"])
        t = im.copy()
        t.thumbnail((288, 512))
        thumbs.append((pg, t))
    # contact sheet
    cols = 5
    rows = math.ceil(len(thumbs) / cols)
    tw = max(t.width for _, t in thumbs)
    th = max(t.height for _, t in thumbs)
    gap, margin, cap = 24, 40, 44
    S = Image.new("RGB", (margin * 2 + cols * tw + (cols - 1) * gap, margin * 2 + rows * (th + cap) + (rows - 1) * gap + 60), (245, 240, 232))
    d = ImageDraw.Draw(S)
    cf = font("LXGWWenKai", 34)
    d.text((margin, 14), spec.get("title", ""), font=cf, fill=(58, 46, 42))
    for i, (pg, t) in enumerate(thumbs):
        x = margin + (i % cols) * (tw + gap)
        y = margin + 60 + (i // cols) * (th + cap + gap)
        S.paste(t, (x, y))
        label = f"{pg['n']:02d} {pg['name']}"
        d.text((x, y + th + 8), label, font=font("LXGWWenKai", 24), fill=(78, 62, 56))
    sheet = a.out.parent / "compose-contact.jpg"
    S.save(sheet, "JPEG", quality=92)
    print("[contact]", sheet)


if __name__ == "__main__":
    main()
