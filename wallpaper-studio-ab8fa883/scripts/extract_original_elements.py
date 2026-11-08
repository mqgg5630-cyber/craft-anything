#!/usr/bin/env python3
"""Lift the original artwork apart so replicas can be rebuilt in the SAME style.

Steps
  1. de-watermark  : the XHS mark is a white overlay -> estimate its alpha and un-blend it
  2. plate         : paper + watercolour wash + doodles, with every phrase erased
  3. sprites       : every handwritten phrase (with its underline flourish) as clean RGBA

Nothing is redrawn: paper, wash, doodles and handwriting all come from the
downloaded originals, so the replica set is stylistically identical.
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
WORK = EX / "05-同款复刻10张"
PLATES = WORK / "plates"
SPRITES = WORK / "sprites"
DEBUG = ROOT / "tmp-analysis"
for p in (PLATES, SPRITES, DEBUG):
    p.mkdir(parents=True, exist_ok=True)

SPEC = json.loads((ROOT / "scripts/original_elements.json").read_text(encoding="utf-8"))


def paper_estimate(img: np.ndarray, k: int = 21) -> np.ndarray:
    return cv2.medianBlur(img, k)


def boxes_of(page: dict) -> list[list[int]]:
    return [page["main"]["box"]] + [p["box"] for p in page["phrases"]]


def protect_mask(img: np.ndarray, box: list[int], phrase_boxes: list[list[int]]) -> np.ndarray:
    """Artwork (doodles) inside the watermark area must never be inpainted over."""
    bg = paper_estimate(img, 15).astype(np.int16)
    ink = ((bg - img.astype(np.int16)).max(axis=2) > 9).astype(np.uint8)
    for x0, y0, x1, y1 in phrase_boxes:
        ink[y0:y1, x0:x1] = 0
    ink = cv2.dilate(ink, np.ones((9, 9), np.uint8))
    return ink


def de_watermark(img: np.ndarray, box: list[int], phrase_boxes: list[list[int]],
                 inpaint: bool = True) -> np.ndarray:
    """The XHS mark mixes translucent and solid white: un-blend the translucent
    part, inpaint the solid part, leave every doodle pixel alone."""
    x0, y0, x1, y1 = box
    f = img.astype(np.float32)
    bg = paper_estimate(img, 41).astype(np.float32)
    bright = (f - bg).max(axis=2)
    dark = (bg - f).max(axis=2)
    m = (bright > 3).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    roi = np.zeros_like(m)
    roi[y0:y1, x0:x1] = m[y0:y1, x0:x1]
    roi = cv2.dilate(roi, np.ones((3, 3), np.uint8))
    if roi.sum() < 50:
        return img
    protect = protect_mask(img, box, phrase_boxes)
    roi = (roi & (1 - protect)).astype(np.uint8)
    plain = (roi > 0) & (dark < 3) & (bg.min(axis=2) > 200)
    ratio = ((f - bg) / np.maximum(255.0 - bg, 8.0)).max(axis=2)
    a = float(np.median(ratio[plain])) if plain.sum() > 100 else 0.5
    a = float(np.clip(a, 0.30, 0.90))
    soft = cv2.GaussianBlur(roi.astype(np.float32), (5, 5), 0)[..., None] * a
    out = np.clip((f - soft * 255.0) / np.maximum(1.0 - soft, 1e-3), 0, 255).astype(np.uint8)
    if not inpaint:
        return out
    opaque = ((roi > 0) & (out.min(axis=2) > 244)).astype(np.uint8) * 255
    if opaque.sum():
        out = cv2.inpaint(out, opaque, 4, cv2.INPAINT_TELEA)
    bg2 = paper_estimate(out, 41).astype(np.int16)
    d2 = (out.astype(np.int16) - bg2).max(axis=2)
    ink2 = (bg2 - out.astype(np.int16)).max(axis=2)
    resid = np.zeros_like(opaque)
    resid[y0:y1, x0:x1] = ((d2[y0:y1, x0:x1] > 2) & (ink2[y0:y1, x0:x1] < 5)).astype(np.uint8) * 255
    resid = cv2.dilate(resid, np.ones((3, 3), np.uint8))
    resid = (resid & (1 - protect_mask(out, box, phrase_boxes))).astype(np.uint8)
    if resid.sum():
        out = cv2.inpaint(out, resid, 3, cv2.INPAINT_TELEA)
    return out


def resynth_paper_region(img: np.ndarray, box: list[int], feather: int = 26) -> np.ndarray:
    """Rebuild the paper inside the watermark rectangle from the page's own
    gradient + grain, then put the doodles back as clean ink sprites.
    No inpainting smear, no leftover white logo."""
    pad = feather + 10
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.shape[1], x1), min(img.shape[0], y1)
    f = img.astype(np.float32)
    bg = paper_estimate(img, 21).astype(np.float32)
    ink = ((bg - f).max(axis=2) > 7).astype(np.float32)
    ink = cv2.dilate(ink, np.ones((7, 7), np.uint8)).astype(np.float32)
    w = 1.0 - ink
    sig = 45
    num = cv2.GaussianBlur(f * w[..., None], (0, 0), sig)
    den = cv2.GaussianBlur(w, (0, 0), sig)[..., None]
    smooth = num / np.maximum(den, 1e-4)
    # borrow real paper grain from the calmest window of the same page
    best, best_score = None, 1e18
    step = 80
    for gy in range(0, img.shape[0] - 128, step):
        for gx in range(0, img.shape[1] - 128, step):
            if gy > y0 - 160 and gy < y1 + 40:
                continue
            patch_ink = ink[gy : gy + 128, gx : gx + 128].mean()
            score = patch_ink * 1000 + float(f[gy : gy + 128, gx : gx + 128].std()) * 0.01
            if score < best_score:
                best_score, best = score, (gy, gx)
    gy, gx = best or (0, 0)
    patch = f[gy : gy + 128, gx : gx + 128]
    grain = patch - cv2.GaussianBlur(patch, (0, 0), 6)
    th = (y1 - y0 + 127) // 128
    tw = (x1 - x0 + 127) // 128
    tile = np.vstack([np.hstack([grain if (r + c) % 2 == 0 else grain[:, ::-1] for c in range(tw)])
                      for r in range(th)])
    tile = tile[: y1 - y0, : x1 - x0]
    fill = np.clip(smooth[y0:y1, x0:x1] + tile, 0, 255)
    # feathered rectangle mask
    mh, mw = y1 - y0, x1 - x0
    my = np.minimum(np.arange(mh), np.arange(mh)[::-1]) / float(feather)
    mx = np.minimum(np.arange(mw), np.arange(mw)[::-1]) / float(feather)
    mask = np.clip(np.minimum(my[:, None], mx[None, :]), 0, 1)[..., None]
    out = f.copy()
    out[y0:y1, x0:x1] = f[y0:y1, x0:x1] * (1 - mask) + fill * mask
    out = np.clip(out, 0, 255).astype(np.uint8)
    # doodles back on top, lifted as ink so the white logo never comes along
    colour, alpha = ink_alpha(img, [x0, y0, x1, y1], lo=8, hi=30, k=51)
    sp = Image.fromarray(np.dstack([colour, alpha * 255]).astype(np.uint8), "RGBA")
    base = Image.fromarray(out).convert("RGBA")
    base.alpha_composite(sp, (x0, y0))
    return np.asarray(base.convert("RGB"))


def ink_alpha(img: np.ndarray, box: list[int], lo: float = 5.0, hi: float = 42.0, k: int = 21,
              bg_img: np.ndarray | None = None):
    x0, y0, x1, y1 = box
    crop = img[y0:y1, x0:x1].astype(np.float32)
    bg = paper_estimate(img if bg_img is None else bg_img, k)[y0:y1, x0:x1].astype(np.float32)
    delta = bg - crop
    d = delta.max(axis=2)
    alpha = np.clip((d - lo) / (hi - lo), 0.0, 1.0)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    # un-premultiply the paper out of the stroke colour
    a = np.maximum(alpha[..., None], 0.12)
    colour = bg - delta / a
    colour = np.clip(colour, 0, 255)
    # solid centre keeps the ink colour stable
    solid = alpha > 0.75
    colour[solid] = crop[solid]
    return colour, alpha


def drop_strays(alpha: np.ndarray) -> np.ndarray:
    """Remove flecks picked up from a neighbouring doodle, keep the phrase's own
    hearts / sparkles (they sit close to the lettering)."""
    m = (alpha > 0.12).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 2:
        return alpha
    areas = stats[1:, 4]
    big = 1 + int(np.argmax(areas))
    bx, by, bw, bh = stats[big][:4]
    out = alpha.copy()
    for i in range(1, n):
        if i == big or stats[i, 4] >= 70:
            continue
        x, y, w, h = stats[i][:4]
        gap = max(bx - (x + w), x - (bx + bw), by - (y + h), y - (by + bh), 0)
        if gap > 26:
            out[lab == i] = 0
    return out


def mend_strokes(colour: np.ndarray, alpha: np.ndarray, box: list[int],
                 wm: list[int] | None) -> tuple[np.ndarray, np.ndarray]:
    """Where the solid-white logo erased a pen stroke, close the tiny gap by
    interpolating the stroke itself (never the paper around it)."""
    if wm is None:
        return colour, alpha
    x0, y0, x1, y1 = box
    ix0, iy0 = max(x0, wm[0]), max(y0, wm[1])
    ix1, iy1 = min(x1, wm[2]), min(y1, wm[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return colour, alpha
    a8 = (alpha * 255).astype(np.uint8)
    solid = (alpha > 0.45).astype(np.uint8)
    closed = cv2.morphologyEx(solid, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    hole = ((closed > 0) & (alpha < 0.35)).astype(np.uint8)
    zone = np.zeros_like(hole)
    zone[iy0 - y0 : iy1 - y0, ix0 - x0 : ix1 - x0] = 1
    hole *= zone
    if hole.sum() < 4:
        return colour, alpha
    hole = cv2.dilate(hole, np.ones((3, 3), np.uint8)) * zone
    fa = cv2.inpaint(a8, hole * 255, 3, cv2.INPAINT_TELEA).astype(np.float32) / 255.0
    fc = cv2.inpaint(colour.astype(np.uint8), hole * 255, 3, cv2.INPAINT_TELEA).astype(np.float32)
    m = (hole > 0) & (fa > alpha)
    alpha = np.where(m, fa, alpha)
    colour = np.where(m[..., None], fc, colour)
    return colour, alpha


def make_sprite(img: np.ndarray, box: list[int], pad: int = 3, bg_img: np.ndarray | None = None,
                wm: list[int] | None = None):
    colour, alpha = ink_alpha(img, box, bg_img=bg_img)
    colour, alpha = mend_strokes(colour, alpha, box, wm)
    alpha = drop_strays(alpha)
    rgba = np.dstack([colour, alpha * 255.0]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    bbox = im.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    ox, oy = box[0], box[1]
    if bbox:
        l, t, r, b = bbox
        left, top = max(0, l - pad), max(0, t - pad)
        im = im.crop((left, top, min(im.width, r + pad), min(im.height, b + pad)))
        ox, oy = box[0] + left, box[1] + top
    return im, (ox, oy)


def make_plate(img: np.ndarray, boxes: list[list[int]]) -> np.ndarray:
    mask = np.zeros(img.shape[:2], np.uint8)
    bg = paper_estimate(img, 21).astype(np.int16)
    d = (bg - img.astype(np.int16)).max(axis=2)
    for x0, y0, x1, y1 in boxes:
        sub = (d[y0:y1, x0:x1] > 4).astype(np.uint8) * 255
        sub = cv2.dilate(sub, np.ones((7, 7), np.uint8))
        mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], sub)
    plate = cv2.inpaint(img, mask, 4, cv2.INPAINT_TELEA)
    # second pass catches halos the first pass left behind
    bg2 = paper_estimate(plate, 21).astype(np.int16)
    d2 = (bg2 - plate.astype(np.int16)).max(axis=2)
    mask2 = np.zeros_like(mask)
    for x0, y0, x1, y1 in boxes:
        sub = (d2[y0:y1, x0:x1] > 3).astype(np.uint8) * 255
        sub = cv2.dilate(sub, np.ones((7, 7), np.uint8))
        mask2[y0:y1, x0:x1] = np.maximum(mask2[y0:y1, x0:x1], sub)
    if mask2.sum() > 0:
        plate = cv2.inpaint(plate, mask2, 4, cv2.INPAINT_TELEA)
    return plate


def crisp(im: Image.Image, scale: float) -> Image.Image:
    """Scale a handwriting sprite and re-sharpen its edge so it stays pen-like."""
    if abs(scale - 1.0) < 1e-3:
        return im
    w = max(1, round(im.width * scale))
    h = max(1, round(im.height * scale))
    big = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(big.getchannel("A"), dtype=np.float32) / 255.0
    if scale > 1.05:
        a = np.clip((a - 0.30) / 0.42, 0, 1)
        a = a * a * (3 - 2 * a)
        a = cv2.GaussianBlur(a, (3, 3), 0)
    rgb = np.asarray(big.convert("RGB"))
    return Image.fromarray(np.dstack([rgb, (a * 255).astype(np.uint8)]), "RGBA")


def main():
    lib = {}
    tiles = []
    for key, page in SPEC["pages"].items():
        img = np.asarray(Image.open(SRC / f"{key}.png").convert("RGB"))
        boxes = boxes_of(page)
        # sprites: only un-blend, never inpaint, so lettering stays intact
        clean = de_watermark(img, page["watermark"], boxes, inpaint=False)
        Image.fromarray(clean).save(DEBUG / f"clean-{key}.png")
        # plate: erase the lettering first, then lift the mark off bare paper
        plate = make_plate(img, boxes)
        plate = resynth_paper_region(plate, page["watermark"])
        Image.fromarray(plate).save(PLATES / f"{key}.png")
        entries = [{"role": "main", **page["main"]}] + [{"role": "sub", **p} for p in page["phrases"]]
        meta = []
        for e in entries:
            sp, origin = make_sprite(clean, e["box"], bg_img=plate, wm=page["watermark"])
            name = f"{key}-{e['text']}"
            sp.save(SPRITES / f"{name}.png")
            lib.setdefault(e["text"], []).append({"file": f"{name}.png", "page": key, "role": e["role"],
                                                 "w": sp.width, "h": sp.height})
            meta.append({"text": e["text"], "role": e["role"], "box": e["box"],
                         "file": f"{name}.png", "w": sp.width, "h": sp.height,
                         "origin": list(origin)})
            tiles.append((name, sp))
        (PLATES / f"{key}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[plate] {key}  phrases={len(entries)}")
    (WORK / "sprite-library.json").write_text(json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")

    # sprite QA sheet on a mid-tone background so halos are obvious
    try:
        f = ImageFont.truetype(str(Path.home() / ".fonts/LXGWWenKai-Medium.ttf"), 22)
    except Exception:
        f = ImageFont.load_default()
    cols, cw, ch = 5, 340, 150
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new("RGB", (cols * cw, rows * ch), (238, 234, 226))
    d = ImageDraw.Draw(S)
    for i, (name, sp) in enumerate(tiles):
        x, y = (i % cols) * cw, (i // cols) * ch
        t = sp.copy()
        t.thumbnail((cw - 24, ch - 48))
        S.paste(t, (x + (cw - t.width) // 2, y + 10), t)
        d.text((x + 10, y + ch - 32), name, font=f, fill=(90, 80, 74))
    S.save(DEBUG / "sprites.jpg", quality=93)
    print("[debug] sprites.jpg", S.size)


if __name__ == "__main__":
    main()
