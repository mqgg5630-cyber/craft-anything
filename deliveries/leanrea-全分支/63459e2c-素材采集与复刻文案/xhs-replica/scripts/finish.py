#!/usr/bin/env python3
"""
finish.py — turn raw model output into a 一二和布布 replica frame.

Fixes, in order, for every image:
  1. centre-crop to 9:19 and resample to exactly 1080 x 2280
  2. unsharp mask (model output is smaller than target, always upscale)
  3. film grade: desaturate -> warm/cool split tone -> S-curve -> vignette -> grain
  4. composite one English word into the flattest patch it can find,
     so every frame carries the "word printed on a prop" detail the
     originals have. The image model cannot be trusted to render text,
     so we do it deterministically here.

Usage:
    python3 finish.py spec.json

spec.json:
    {
      "outdir": "out",
      "sheet":  "out/preview.jpg",          # optional
      "grain":  0.010,                      # optional
      "items": [
        {"src": "c01.png", "name": "跨年倒计时", "word": "COUNTDOWN"},
        ...
      ]
    }
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import json, sys, os, glob

# ---------------------------------------------------------------- constants
TW, TH = 1080, 2280          # hard target: 9:19 phone wallpaper
TR = TW / TH
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
# only used when lang="zh" — the originals carry English, so this is the fallback
CJK_FONT_PATHS = [
    "/usr/local/lib/python3.11/dist-packages/mplfonts/fonts/NotoSansCJKsc-Regular.otf",
    "/usr/local/lib/python3.11/dist-packages/mplfonts/fonts/SourceHanSerifSC-Regular.otf",
    "/usr/local/lib/python3.11/dist-packages/mplfonts/fonts/SimHei.ttf",
]
SHADOW_TINT = np.array([1.045, 1.005, 0.960], dtype=np.float32)  # warm cocoa
HIGH_TINT   = np.array([0.960, 0.985, 1.040], dtype=np.float32)  # cool slate


def pick_font(size, lang="en"):
    paths = (CJK_FONT_PATHS + FONT_PATHS) if lang == "zh" else (FONT_PATHS + CJK_FONT_PATHS)
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ---------------------------------------------------------------- grade
def film_grade(im, grain=0.010, rng=None):
    rng = rng or np.random.default_rng(7)
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

    a = np.clip(lum[..., None] * 0.20 + a * 0.80, 0, 1)          # desaturate
    w = lum[..., None]
    a = np.clip(a * (SHADOW_TINT * (1 - w) + HIGH_TINT * w), 0, 1)  # split tone
    a = a * a * (3 - 2 * a) * 0.18 + a * 0.82                    # S-curve

    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (xx / W - 0.5) * 2.0, (yy / H - 0.5) * 2.0
    r = np.sqrt(nx ** 2 + (ny * 0.92) ** 2) / np.sqrt(2.0)
    a = a * np.clip(1.0 - 0.42 * (r ** 2.4), 0, 1)[..., None]    # vignette

    a = np.clip(a + rng.normal(0, grain, a.shape).astype(np.float32), 0, 1)
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8))


def tone(im, sat=1.0, warm=0.0, bright=1.0):
    """整轮色调微调：sat>1 加饱和，warm>0 往暖褐推，bright>1 提亮。
    用来把新画的一轮拉回某一版老配色（比如第2轮那种低饱和胶片暖调）；
    film_grade 的暗角和 S 曲线会把明度压掉一截，bright 就是用来补回来的。"""
    if sat == 1.0 and warm == 0.0 and bright == 1.0:
        return im
    a = np.asarray(im).astype(np.float32) / 255.0
    if bright != 1.0:
        a = np.clip(a * bright, 0, 1)
    if sat != 1.0:
        lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        a = np.clip(lum[..., None] + (a - lum[..., None]) * sat, 0, 1)
    if warm:
        a[..., 0] = np.clip(a[..., 0] * (1 + warm), 0, 1)
        a[..., 2] = np.clip(a[..., 2] * (1 - warm * 0.8), 0, 1)
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8))


# ---------------------------------------------------------------- lettering
def flattest_patch(im, bw, bh):
    """Find the lowest-detail bw x bh block in the lower band of the frame."""
    W, H = im.size
    g = np.asarray(im.convert("L")).astype(np.float32) / 255.0
    gy, gx = np.gradient(g)
    mag = np.sqrt(gx ** 2 + gy ** 2)

    # cheap box blur
    k = 9
    c = np.cumsum(np.cumsum(np.pad(mag, ((1, 0), (1, 0))), 0), 1)
    box = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    box = np.pad(box, ((k, 0), (k, 0)), mode="edge")[:H, :W]

    y0, y1 = int(0.58 * H), int(0.93 * H) - bh
    x0, x1 = int(0.05 * W), int(0.95 * W) - bw
    best, score = None, 1e9
    for y in range(y0, max(y0 + 1, y1), 24):
        for x in range(x0, max(x0 + 1, x1), 24):
            s = box[y:y + bh, x:x + bw].mean()
            # mild bias away from the exact horizontal centre (characters)
            cx = (x + bw / 2) / W
            s *= 1.0 + 0.18 * max(0.0, 1.0 - abs(cx - 0.5) * 3.0)
            if s < score:
                score, best = s, (x, y)
    return best or (x0, y0)


def stamp_word(im, word, idx=0, scale=1.35, rule=True, lang="en", anchor=None):
    """Composite one word, letter-spaced, into the flattest patch.

    scale=1.35 makes it read as a designed text element rather than a stray
    prop label; rule=True adds the thin rule underneath, poster-style.
    """
    W, H = im.size
    bw, bh = int(W * 0.34 * scale), int(H * 0.055 * scale)
    if anchor:  # 整轮统一位置：anchor=[x%, y%]，不再各自找最平色块
        x, y = int(W * anchor[0]), int(H * anchor[1])
    else:
        x, y = flattest_patch(im, bw, bh)

    patch = np.asarray(im.crop((x, y, x + bw, y + bh)).convert("RGB")).astype(np.float32) / 255.0
    mean = patch.reshape(-1, 3).mean(0)
    lum = float(mean @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32))
    # read as ink on the surface under it: dark on light, light on dark
    col = mean * 0.40 if lum > 0.45 else mean * 0.45 + np.array([0.55, 0.55, 0.55], dtype=np.float32)
    col = tuple(int(max(0, min(255, c * 255))) for c in col)

    # fit the word to the patch, letter-spaced
    size = 10
    spacing = 0.16
    while True:
        f = pick_font(size, lang)
        widths = [f.getlength(ch) for ch in word]
        total = sum(widths) + spacing * size * (len(word) - 1)
        if total > bw * 0.92 or size > 160:
            size -= 2
            f = pick_font(max(6, size), lang)
            widths = [f.getlength(ch) for ch in word]
            total = sum(widths) + spacing * max(6, size) * (len(word) - 1)
            break
        size += 2

    f = pick_font(max(6, size), lang)
    ascent, descent = f.getmetrics()
    lh = ascent + descent
    pad = 20
    lw, lhgt = int(total) + pad * 2, lh + pad + (28 if rule else 16)
    layer = Image.new("RGBA", (lw, lhgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pen = pad
    for ch, wch in zip(word, widths):
        d.text((pen, pad // 2), ch, font=f, fill=col + (255,))
        pen += wch + spacing * max(6, size)

    if rule:  # thin rule under the word — reads as printed type, not a sticker
        rw = int(total)
        ry = pad // 2 + lh + 6
        d.rectangle([pad, ry, pad + rw, ry + max(3, size // 12)], fill=col + (255,))

    rot = ((idx * 7) % 5) - 2            # -2..+2 deg, deterministic
    layer = layer.rotate(rot, expand=True, resample=Image.BICUBIC)
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * 0.72)))

    px = x + (bw - layer.width) // 2
    py = y + (bh - layer.height) // 2
    out = im.convert("RGBA")
    out.alpha_composite(layer, (px, py))
    return out.convert("RGB"), (px, py, layer.width, layer.height)


# ---------------------------------------------------------------- main
def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = spec["outdir"]
    os.makedirs(outdir, exist_ok=True)
    grain = float(spec.get("grain", 0.010))

    for i, it in enumerate(spec["items"]):
        im = Image.open(it["src"]).convert("RGB")
        w, h = im.size
        if w / h > TR:
            nw, nh = int(round(h * TR)), h
        else:
            nw, nh = w, int(round(w / TR))
        l, t = (w - nw) // 2, (h - nh) // 2
        im = im.crop((l, t, l + nw, t + nh)).resize((TW, TH), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
        im = film_grade(im, grain=grain, rng=np.random.default_rng(7 + i))
        im = tone(im, float(spec.get("sat", 1.0)), float(spec.get("warm", 0.0)),
                  float(spec.get("bright", 1.0)))
        if it.get("word"):
            im, box = stamp_word(im, it["word"], i,
                                 scale=float(it.get("scale", 1.35)),
                                 rule=bool(it.get("rule", True)),
                                 lang=it.get("lang", "en"),
                                 anchor=it.get("anchor"))
        else:
            box = None
        dst = os.path.join(outdir, it["name"] + ".png")
        im.save(dst, "PNG", optimize=True)
        print(f"{it['name']}: {w}x{h} -> {im.size}  word={it.get('word')} box={box}  {os.path.getsize(dst)}")

    if spec.get("sheet"):
        files = sorted(glob.glob(os.path.join(outdir, "*.png")))
        cols = min(5, max(1, len(files)))
        rows = (len(files) + cols - 1) // cols
        tw, th = 300, 633
        sheet = Image.new("RGB", (cols * tw, rows * th), "#f6f1ea")
        for k, f in enumerate(files):
            sheet.paste(Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS),
                        ((k % cols) * tw, (k // cols) * th))
        sheet.save(spec["sheet"], quality=90)
        print("sheet ->", spec["sheet"], sheet.size)


if __name__ == "__main__":
    main()
