#!/usr/bin/env python3
"""Faithful replication directly from the downloaded Xiaohongshu originals.

01-04: original pixels, only platform watermark cleaned + upscaled.
05-10: same original backgrounds/doodles; the main phrase is replaced by another
phrase cut from the original handwriting itself, so the lettering stays identical.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples/law-of-attraction-6a30e185"
SRC = EX / "01-原图"
OUT = EX / "04-原片复刻版"
OUT.mkdir(parents=True, exist_ok=True)

# boxes in original 944x1672 coordinates
WATERMARK = (390, 1465, 930, 1620)
MAIN = {
    1: (120, 360, 870, 610),
    2: (210, 580, 760, 980),
    3: (120, 350, 840, 610),
    4: (140, 420, 840, 660),
}
PROMO = {
    5: {"base": 4, "text": "平安喜乐", "box": (495, 1115, 795, 1235), "center": (472, 540), "width": 640},
    6: {"base": 3, "text": "得偿所愿", "box": (610, 1145, 875, 1265), "center": (472, 480), "width": 640},
    7: {"base": 2, "text": "我值得最好的一切", "box": (75, 375, 465, 495), "center": (472, 770), "width": 720},
    8: {"base": 3, "text": "一路绿灯", "box": (275, 835, 545, 955), "center": (472, 480), "width": 580},
    9: {"base": 4, "text": "财运爆棚", "box": (505, 165, 865, 295), "center": (472, 540), "width": 640},
    10: {"base": 1, "text": "未来可期", "box": (305, 795, 565, 915), "center": (472, 480), "width": 580},
}


def load(n: int) -> np.ndarray:
    im = Image.open(SRC / f"{n:02d}.png").convert("RGB")
    return np.asarray(im)


def inpaint_rect(img: np.ndarray, boxes, radius=7) -> np.ndarray:
    mask = np.zeros(img.shape[:2], np.uint8)
    for x0, y0, x1, y1 in boxes:
        mask[y0:y1, x0:x1] = 255
    return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)


def text_mask(img: np.ndarray, box) -> np.ndarray:
    x0, y0, x1, y1 = box
    crop = img[y0:y1, x0:x1].astype(np.float32)
    border = np.concatenate([
        crop[:6, :, :].reshape(-1, 3),
        crop[-6:, :, :].reshape(-1, 3),
        crop[:, :6, :].reshape(-1, 3),
        crop[:, -6:, :].reshape(-1, 3),
    ])
    bg = np.median(border, axis=0)
    diff = np.sqrt(((crop - bg) ** 2).sum(axis=2))
    m = (diff > 32).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    full = np.zeros(img.shape[:2], np.uint8)
    full[y0:y1, x0:x1] = m
    return full


def inpaint_text(img: np.ndarray, boxes, radius=4) -> np.ndarray:
    mask = np.zeros(img.shape[:2], np.uint8)
    for b in boxes:
        mask = cv2.bitwise_or(mask, text_mask(img, b))
    return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)


def extract_text(img: np.ndarray, box) -> Image.Image:
    x0, y0, x1, y1 = box
    crop = img[y0:y1, x0:x1].astype(np.float32)
    h, w = crop.shape[:2]
    # estimate paper color from border pixels
    border = np.concatenate([
        crop[:6, :, :].reshape(-1, 3),
        crop[-6:, :, :].reshape(-1, 3),
        crop[:, :6, :].reshape(-1, 3),
        crop[:, -6:, :].reshape(-1, 3),
    ])
    bg = np.median(border, axis=0)
    diff = np.sqrt(((crop - bg) ** 2).sum(axis=2))
    alpha = np.clip((diff - 14) / 55, 0, 1)
    # keep colored strokes, suppress paper noise
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    alpha = np.clip(alpha * 1.35, 0, 1)
    rgba = np.dstack([crop.astype(np.uint8), (alpha * 255).astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def pasteSnippet(base: Image.Image, snippet: Image.Image, center, target_w):
    s = target_w / snippet.width
    sn = snippet.resize((round(snippet.width * s), round(snippet.height * s)), Image.LANCZOS)
    x = round(center[0] - sn.width / 2)
    y = round(center[1] - sn.height / 2)
    base.alpha_composite(sn, (x, y))


def upscale(img: np.ndarray) -> Image.Image:
    im = Image.fromarray(img).resize((1440, 2560), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=35, threshold=2))


def main():
    orig = {n: load(n) for n in range(1, 5)}
    results = []
    # 01-04 faithful originals (keep original author/platform marks; no redesign)
    for n in range(1, 5):
        im = upscale(orig[n])
        name = f"原片复刻{n:02d}"
        im.save(OUT / f"{name}.jpg", quality=94, subsampling=0)
        results.append((n, name, im))
    # 05-10 same-series using original handwriting snippets; remove only stroke pixels
    for n, cfg in PROMO.items():
        base_n = cfg["base"]
        boxes = [MAIN[base_n], cfg["box"]]
        cleaned = inpaint_text(orig[base_n], boxes, radius=4)
        base = Image.fromarray(cleaned).convert("RGBA")
        sn = extract_text(orig[base_n], cfg["box"])
        pasteSnippet(base, sn, cfg["center"], cfg["width"])
        im = upscale(np.asarray(base.convert("RGB")))
        name = f"原片复刻{n:02d}-{cfg['text']}"
        im.save(OUT / f"{name}.jpg", quality=94, subsampling=0)
        results.append((n, name, im))
    # contact sheet
    thumbs = []
    for n, name, im in results:
        t = im.copy()
        t.thumbnail((288, 512))
        thumbs.append((n, name, t))
    cols = 5
    rows = 2
    tw, th = 288, 512
    gap, margin, cap = 24, 40, 48
    S = Image.new("RGB", (margin * 2 + cols * tw + (cols - 1) * gap, margin * 2 + rows * (th + cap) + (rows - 1) * gap + 60), (245, 240, 232))
    d = ImageDraw.Draw(S)
    try:
        f = ImageFont.truetype(str(Path.home() / ".fonts/LXGWWenKai-Medium.ttf"), 32)
        fs = ImageFont.truetype(str(Path.home() / ".fonts/LXGWWenKai-Medium.ttf"), 22)
    except Exception:
        f = fs = ImageFont.load_default()
    d.text((margin, 14), "Replica set based on the downloaded originals", font=f, fill=(58, 46, 42))
    for i, (n, name, t) in enumerate(thumbs):
        x = margin + (i % cols) * (tw + gap)
        y = margin + 60 + (i // cols) * (th + cap + gap)
        S.paste(t, (x, y))
        d.text((x, y + th + 8), f"{n:02d}", font=fs, fill=(78, 62, 56))
    S.save(OUT / "总图.jpg", quality=92)
    print("saved", OUT)


if __name__ == "__main__":
    main()
