#!/usr/bin/env python3
"""Rebuild 10 wallpapers from the original artwork elements.

01-04  every phrase back in its exact original place  -> same-style replicas
05-10  same paper / wash / doodles, original handwriting re-arranged into new pages

No font is substituted and no doodle is redrawn, so the whole set keeps the
original artist's line, colour and layout grammar.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples/law-of-attraction-6a30e185"
WORK = EX / "05-同款复刻10张"
PLATES = WORK / "plates"
SPRITES = WORK / "sprites"
OUT = WORK / "壁纸"
OUT.mkdir(parents=True, exist_ok=True)

SPEC = json.loads((ROOT / "scripts/original_elements.json").read_text(encoding="utf-8"))
SRC_W, SRC_H = SPEC["canvas_src"]
CANVAS = (1440, 2560)

NEW_PAGES = [
    {"n": 5, "base": "02", "mirror": False, "main": "04-平安喜乐",
     "subs": ["04-天生好命", "02-我会实现目标", "02-健康且富足", "04-福气满满",
              "02-如愿以偿", "02-万事皆有回甘", "01-日日向好"]},
    {"n": 6, "base": "03", "mirror": False, "main": "04-得偿所愿",
     "subs": ["03-诸事顺遂", "03-水逆退散", "03-一路绿灯", "03-步步高升",
              "03-万事顺意", "03-平安顺遂", "03-好运开挂", "01-未来可期"]},
    {"n": 7, "base": "01", "mirror": False, "main": "02-我值得最好的一切",
     "subs": ["01-过去不定义未来", "01-慢慢变好", "02-我会越来越好", "01-好事将至",
              "01-万事胜意", "01-日日向好", "01-稳步前进", "01-心有暖阳", "01-花路常开"]},
    {"n": 8, "base": "04", "mirror": False, "main": "03-一路绿灯",
     "subs": ["04-天生好命", "04-财运爆棚", "03-诸事顺遂", "04-万事顺意",
              "04-好运常伴", "04-平安喜乐", "04-得偿所愿", "03-步步高升"]},
    {"n": 9, "base": "01", "mirror": True, "main": "04-财运爆棚",
     "subs": ["04-天生好命", "01-慢慢变好", "01-未来可期", "01-好事将至",
              "01-万事胜意", "01-日日向好", "01-稳步前进", "01-心有暖阳", "04-命里带财"]},
    {"n": 10, "base": "04", "mirror": True, "main": "01-未来可期",
     "subs": ["04-天生好命", "04-财运爆棚", "04-福气满满", "04-万事顺意",
              "04-好运常伴", "04-平安喜乐", "02-如愿以偿", "02-我会越来越好"]},
]


def load_meta(key: str):
    return json.loads((PLATES / f"{key}.json").read_text(encoding="utf-8"))


def sprite(file: str) -> Image.Image:
    return Image.open(SPRITES / file).convert("RGBA")


def rescale(im: Image.Image, scale: float) -> Image.Image:
    if abs(scale - 1.0) < 0.01:
        return im
    w, h = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    out = im.resize((w, h), Image.LANCZOS)
    if scale > 1.08:  # keep the pen edge crisp after enlargement
        a = np.asarray(out.getchannel("A"), dtype=np.float32) / 255.0
        a = np.clip((a - 0.28) / 0.44, 0, 1)
        a = a * a * (3 - 2 * a)
        rgb = np.asarray(out.convert("RGB"))
        out = Image.fromarray(np.dstack([rgb, (a * 255).astype(np.uint8)]), "RGBA")
    return out


def place_centred(base: Image.Image, sp: Image.Image, cx: float, cy: float,
                  slot_w: float, slot_h: float, w_fit=0.96, h_fit=0.92, max_scale=2.6):
    scale = min(slot_w * w_fit / sp.width, slot_h * h_fit / sp.height, max_scale)
    sp = rescale(sp, scale)
    base.alpha_composite(sp, (round(cx - sp.width / 2), round(cy - sp.height / 2)))


def finish(im: Image.Image) -> Image.Image:
    s = max(CANVAS[0] / im.width, CANVAS[1] / im.height)
    big = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = (big.width - CANVAS[0]) // 2
    y = (big.height - CANVAS[1]) // 2
    big = big.crop((x, y, x + CANVAS[0], y + CANVAS[1]))
    return big.filter(ImageFilter.UnsharpMask(radius=1.1, percent=32, threshold=2))


def build_replica(key: str) -> Image.Image:
    base = Image.open(PLATES / f"{key}.png").convert("RGBA")
    for e in load_meta(key):
        base.alpha_composite(sprite(e["file"]), tuple(e["origin"]))
    return base.convert("RGB")


def build_new(cfg: dict) -> Image.Image:
    key = cfg["base"]
    plate = Image.open(PLATES / f"{key}.png").convert("RGB")
    if cfg["mirror"]:
        plate = ImageOps.mirror(plate)
    base = plate.convert("RGBA")
    meta = load_meta(key)
    main_slot = next(e for e in meta if e["role"] == "main")
    sub_slots = [e for e in meta if e["role"] == "sub"]

    def slot_geom(e):
        x0, y0, x1, y1 = e["box"]
        if cfg["mirror"]:
            x0, x1 = SRC_W - x1, SRC_W - x0
        return (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0

    cx, cy, w, h = slot_geom(main_slot)
    place_centred(base, sprite(cfg["main"] + ".png"), cx, cy, w, h, 0.94, 0.86)
    for slot, name in zip(sub_slots, cfg["subs"]):
        cx, cy, w, h = slot_geom(slot)
        place_centred(base, sprite(name + ".png"), cx, cy, w, h, 0.99, 0.95, max_scale=1.6)
    return base.convert("RGB")


def sheet(items, path: Path, title: str, subtitle: str):
    cols, tw = 5, 300
    th = round(tw * CANVAS[1] / CANVAS[0])
    gap, margin, head, cap = 30, 64, 150, 54
    rows = (len(items) + cols - 1) // cols
    W = margin * 2 + cols * tw + (cols - 1) * gap
    H = margin + head + rows * (th + cap) + (rows - 1) * gap + margin
    S = Image.new("RGB", (W, H), (243, 233, 219))
    d = ImageDraw.Draw(S)
    fp = Path.home() / ".fonts/LXGWWenKai-Medium.ttf"
    f1 = ImageFont.truetype(str(fp), 46)
    f2 = ImageFont.truetype(str(fp), 24)
    f3 = ImageFont.truetype(str(fp), 25)
    d.text((margin, margin - 8), title, font=f1, fill=(58, 46, 42))
    d.text((margin, margin + 54), subtitle, font=f2, fill=(122, 102, 94))
    for i, (label, im) in enumerate(items):
        x = margin + (i % cols) * (tw + gap)
        y = margin + head + (i // cols) * (th + cap + gap)
        card = im.resize((tw, th), Image.LANCZOS).convert("RGBA")
        mask = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw - 1, th - 1), 20, fill=255)
        sh = Image.new("RGBA", (tw + 20, th + 20), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((10, 12, tw + 10, th + 12), 22, fill=(90, 70, 50, 60))
        S.paste(sh.filter(ImageFilter.GaussianBlur(9)), (x - 10, y - 8), sh)
        S.paste(card, (x, y), mask)
        lw = d.textlength(label, font=f3)
        d.text((x + (tw - lw) / 2, y + th + 14), label, font=f3, fill=(78, 62, 56))
    S.save(path, "JPEG", quality=93)
    return path


def main():
    items = []
    names = {}
    for key in ("01", "02", "03", "04"):
        page = SPEC["pages"][key]
        im = finish(build_replica(key))
        n = int(key)
        name = f"复刻{n:02d}-{page['main']['text']}"
        im.save(OUT / f"{name}.jpg", "JPEG", quality=95, subsampling=0)
        items.append((f"{n:02d}  {page['main']['text']}", im))
        names[n] = name
        print("[replica]", name)
    for cfg in NEW_PAGES:
        im = finish(build_new(cfg))
        text = cfg["main"].split("-", 1)[1]
        name = f"复刻{cfg['n']:02d}-{text}"
        im.save(OUT / f"{name}.jpg", "JPEG", quality=95, subsampling=0)
        items.append((f"{cfg['n']:02d}  {text}", im))
        names[cfg["n"]] = name
        print("[new]    ", name)
    sheet(items, WORK / "总图.jpg", "吸引力法则治愈壁纸｜暴富顺遂万事向好",
          "10 张同款复刻 · 纸纹 / 晕染 / 涂鸦 / 手写笔迹全部取自小红书原片")
    (WORK / "deliverables.json").write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8")
    # numbered PNG copies for the phone-mockup script
    art = WORK / "art"
    art.mkdir(exist_ok=True)
    for n, name in names.items():
        Image.open(OUT / f"{name}.jpg").save(art / f"{int(n):02d}.png")
    print("[sheet]", WORK / "总图.jpg")


if __name__ == "__main__":
    main()
