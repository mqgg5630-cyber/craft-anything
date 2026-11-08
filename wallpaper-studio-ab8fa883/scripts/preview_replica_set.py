#!/usr/bin/env python3
"""Lock-screen previews for the replica set, kept at the original 9:16-ish canvas
(1440x2560) so nothing gets cropped. Reuses the reference repo's phone geometry,
scaled from 1440x3200, with an ink-toned clock that stays legible on pale paper.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

import phone_mockup as pm

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "examples/law-of-attraction-6a30e185/05-同款复刻10张"
ART = WORK / "art"
OUT = WORK / "预览"
OUT.mkdir(parents=True, exist_ok=True)

S = 2560 / 3200
pm.W, pm.H = 1440, 2560
DATE_CY, DATE_SIZE = round(pm.DATE_CY * S), round(pm.DATE_SIZE * S)
TIME_CY, TIME_SIZE = round(pm.TIME_CY * S), round(pm.TIME_SIZE * S)
BTN_R, BTN_CY = round(pm.BTN_R * S), round(pm.BTN_CY * S)
BTN_CX = tuple(round(c * S) for c in pm.BTN_CX)
BAR = tuple(round(v * S) for v in pm.BAR)
INK = (74, 64, 58, 242)

CLOCK = pm.find_font(None, "CLOCK_FONT", pm.CLOCK_CANDS)
CJK = pm.find_font(None, "CJK_FONT", pm.CJK_CANDS)


def lock(base: Image.Image, date: str, time: str) -> Image.Image:
    img = base.convert("RGBA")
    for cx in BTN_CX:
        box = (cx - BTN_R, BTN_CY - BTN_R, cx + BTN_R, BTN_CY + BTN_R)
        patch = pm.glass_patch(img.convert("RGB"), box, blur=22, white_alpha=0.0, dark=0.80)
        m = Image.new("L", patch.size, 0)
        ImageDraw.Draw(m).ellipse((0, 0, patch.size[0] - 1, patch.size[1] - 1), fill=255)
        img.paste(patch, box[:2], m)
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    pm.flashlight_glyph(d, BTN_CX[0], BTN_CY, s=0.88 * S)
    pm.camera_glyph(d, BTN_CX[1], BTN_CY, s=0.88 * S)
    img.alpha_composite(g)
    pm.draw_text_centered(img, date, pm.font(CLOCK, DATE_SIZE, 600), pm.W / 2, DATE_CY, fill=INK)
    pm.draw_text_centered(img, time, pm.font(CLOCK, TIME_SIZE, 620), pm.W / 2, TIME_CY, fill=INK)
    bar = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(bar).rounded_rectangle(BAR, radius=7, fill=(74, 64, 58, 200))
    img.alpha_composite(bar)
    return img.convert("RGB")


def main():
    names = json.loads((WORK / "deliverables.json").read_text(encoding="utf-8"))
    files = []
    for n in range(1, 11):
        base = Image.open(ART / f"{n:02d}.png").convert("RGB")
        p = OUT / f"锁屏{n:02d}.jpg"
        lock(base, "Saturday, November 7", "05:20").save(p, "JPEG", quality=92, subsampling=0)
        files.append(p)
    spec = {"title": "同款复刻 10 张｜锁屏效果预览",
            "subtitle": "1440×2560 · 与原片同比例 · 时钟仅为示意，壁纸本身无任何 UI"}
    pm.contact_sheet(spec, files, WORK / "预览-锁屏总图.jpg", CJK, bezel=True)
    pm.cover(spec, files[0], files[3], WORK / "封面-双机预览.jpg", bezel=True)
    print("[preview]", len(files), "files +", WORK / "预览-锁屏总图.jpg")


if __name__ == "__main__":
    main()
