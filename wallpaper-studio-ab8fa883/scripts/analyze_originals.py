#!/usr/bin/env python3
"""Find every ink element (handwriting + doodle) in the downloaded originals.

Outputs an annotated preview per page plus a JSON list of bounding boxes, so the
phrase sprites can be lifted from the original artwork pixel-for-pixel.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples/law-of-attraction-6a30e185"
SRC = EX / "01-原图"
OUT = ROOT / "tmp-analysis"
OUT.mkdir(parents=True, exist_ok=True)


def ink_mask(img: np.ndarray, ksize: int = 21, thresh: int = 10):
    """Paper estimate via median (kills thin strokes), then difference."""
    bg = cv2.medianBlur(img, ksize)
    d = bg.astype(np.int16) - img.astype(np.int16)
    dark = d.max(axis=2)                      # coloured / dark ink
    bright = (-d).max(axis=2)                 # white watermark ink
    m = ((dark > thresh) | (bright > thresh + 8)).astype(np.uint8) * 255
    return m, bg


def components(mask: np.ndarray, dx: int = 14, dy: int = 8, min_area: int = 90):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dx, dy))
    merged = cv2.dilate(mask, kernel)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(merged, 8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < min_area or w < 8 or h < 8:
            continue
        sub = mask[y : y + h, x : x + w]
        if sub.sum() / 255 < 40:
            continue
        boxes.append([int(x), int(y), int(x + w), int(y + h)])
    boxes.sort(key=lambda b: (b[1] // 40, b[0]))
    return boxes


def main():
    inventory = {}
    for n in range(1, 5):
        img = np.asarray(Image.open(SRC / f"{n:02d}.png").convert("RGB"))
        m, _ = ink_mask(img)
        boxes = components(m)
        inventory[f"{n:02d}"] = boxes
        vis = Image.fromarray(img).convert("RGB")
        d = ImageDraw.Draw(vis)
        try:
            f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except Exception:
            f = ImageFont.load_default()
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            d.rectangle((x0, y0, x1, y1), outline=(255, 0, 0), width=2)
            d.text((x0 + 2, max(0, y0 - 22)), str(i), font=f, fill=(200, 0, 0))
        vis.save(OUT / f"boxes-{n:02d}.png")
        print(f"page {n:02d}: {len(boxes)} components")
        for i, b in enumerate(boxes):
            print("   ", i, b)
    (OUT / "boxes.json").write_text(json.dumps(inventory, indent=2))


if __name__ == "__main__":
    main()
