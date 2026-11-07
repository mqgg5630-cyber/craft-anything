#!/usr/bin/env python3
"""
phone_mockup.py — 把生图模型吐出的「无字底图」变成可交付的手机壁纸（默认：干净版，没有任何手机 UI）。

默认 --ui none：壁纸就是壁纸——不加时间/日期/手电筒/相机/Home 条/图标，这些都是手机自带的。
可选 --ui ios：额外输出一份带 iOS 锁屏/主屏覆盖层的「效果预览图」（仿壁纸博主的预览帖），仅作展示。

用法（spec.json 见 examples/*/02-复刻/spec.json）：
  python3 scripts/phone_mockup.py build  SPEC --art-dir ART --out OUT [--format png|jpg] [--ui none|ios] [--date ...] [--time ...]
      ART/01.png … → OUT/复刻图01-xxx.png (1440×3200 干净壁纸)
                   → OUT/预览-iOS/复刻图01-xxx.png（仅 --ui ios）
  python3 scripts/phone_mockup.py sheet  SPEC --out OUT          → OUT/总图.jpg（2×5 拼版）
  python3 scripts/phone_mockup.py cover  SPEC --out OUT          → OUT/封面-双机预览.jpg（米色底两张竖图）
  python3 scripts/phone_mockup.py all    SPEC --art-dir ART --out OUT

依赖：Pillow。字体：中文标题用霞鹜文楷（--cjk-font / CJK_FONT）；--ui ios 时时钟用 Inter（--clock-font / CLOCK_FONT）。
锁屏几何常量来自对参考帖原图（1440×3200）的逐像素测量，见 SKILL.md。
"""
import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ------------------------------------------------------------------ 几何（1440×3200 实测）
W, H = 1440, 3200
DATE_CY, DATE_SIZE, DATE_WGHT = 319, 78, 600        # 日期：带 y/逗号下伸的字框高 71，中心 y 319
TIME_CY, TIME_SIZE, TIME_WGHT = 553, 336, 700       # 时钟：数字高 244，中心 y 553
BTN_R, BTN_CY, BTN_CX = 92, 2940, (231, 1209)       # 手电筒 / 相机 圆钮
BAR = (468, 3129, 971, 3147)                        # Home 条
ICON = 244                                          # 主屏毛玻璃图标边长
ICON_R = 54
ICON_CX = (212, 548, 892, 1228)
ICON_ROWS_CY = (300, 602)
DOCK_CY = 2960


def find_font(explicit, env, candidates):
    for p in [explicit, os.environ.get(env)] + candidates:
        if p and Path(p).expanduser().exists():
            return str(Path(p).expanduser())
    return None


CLOCK_CANDS = ["~/.fonts/Inter-Variable.ttf", "~/.fonts/Inter.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
CJK_CANDS = ["~/.fonts/LXGWWenKai-Medium.ttf", "~/.fonts/LXGWWenKai-Regular.ttf",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]


def font(path, size, wght=None):
    f = ImageFont.truetype(path, size)
    if wght is not None:
        try:
            axes = f.get_variation_axes()
            vals = []
            for ax in axes:
                name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
                if "eight" in name:
                    vals.append(wght)
                elif "ptical" in name:
                    vals.append(ax["maximum"])
                else:
                    vals.append(ax["default"])
            f.set_variation_by_axes(vals)
        except Exception:  # 静态字体
            pass
    return f


# ------------------------------------------------------------------ 底图
def fit_canvas(art: Image.Image, size=(W, H), ax=0.5, ay=0.5) -> Image.Image:
    """等比放大/裁切到 1440×3200，再轻微锐化（688×1536 → ×2.09）。

    ax / ay = 裁切锚点（0=左/上，0.5=居中，1=右/下）。生图偶尔吐出偏宽的 848×1264，
    按 9:20 要裁掉三成宽度时，用 spec 里每页的 "ax" 把主体留在画面里（见第 11 轮）。
    """
    is_mask = art.mode == "L"
    art = art if is_mask else art.convert("RGB")
    aw, ah = art.size
    s = max(size[0] / aw, size[1] / ah)
    big = art.resize((round(aw * s), round(ah * s)), Image.LANCZOS)
    x0 = round((big.width - size[0]) * min(max(ax, 0.0), 1.0))
    y0 = round((big.height - size[1]) * min(max(ay, 0.0), 1.0))
    big = big.crop((x0, y0, x0 + size[0], y0 + size[1]))
    if is_mask:
        return big
    return big.filter(ImageFilter.UnsharpMask(radius=1.6, percent=55, threshold=2))


# ------------------------------------------------------------------ 覆盖层
def rounded_mask(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255)
    return m


def glass_patch(base, box, blur, white_alpha, dark=1.0):
    """取 box 区域 → 高斯模糊 → 调亮/调暗 → 返回贴片。"""
    patch = base.crop(box).filter(ImageFilter.GaussianBlur(blur))
    if dark != 1.0:
        patch = Image.eval(patch, lambda v: int(v * dark))
    if white_alpha:
        patch = Image.blend(patch, Image.new("RGB", patch.size, (255, 255, 255)), white_alpha)
    return patch


def draw_text_centered(img, text, f, cx, cy, fill=(255, 255, 255, 248)):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    d.text((cx - (l + r) / 2, cy - (t + b) / 2), text, font=f, fill=fill)
    img.alpha_composite(layer)


def flashlight_glyph(d, cx, cy, s=1.0, fill=(255, 255, 255, 255)):
    """iOS 风格手电筒：上宽头 + 细身 + 小灯珠。s 为缩放。"""
    def P(x, y):
        return (cx + x * s, cy + y * s)
    d.polygon([P(-30, -52), P(30, -52), P(17, -14), P(-17, -14)], fill=fill)      # 头
    d.rounded_rectangle([P(-17, -8), P(17, 54)], radius=12 * s, fill=fill)         # 身
    d.rectangle([P(-30, -62), P(30, -52)], fill=fill)                               # 顶沿
    d.ellipse([P(-7, -46), P(7, -32)], fill=(0, 0, 0, 0))                           # 灯珠挖孔（透明）


def camera_glyph(d, cx, cy, s=1.0, fill=(255, 255, 255, 255)):
    def P(x, y):
        return (cx + x * s, cy + y * s)
    d.rounded_rectangle([P(-52, -30), P(52, 42)], radius=14 * s, fill=fill)         # 机身
    d.rounded_rectangle([P(-24, -46), P(24, -24)], radius=8 * s, fill=fill)         # 取景凸起
    d.ellipse([P(-24, -18), P(24, 30)], fill=(0, 0, 0, 0))                          # 镜头外圈挖空
    d.ellipse([P(-15, -9), P(15, 21)], fill=fill)                                   # 镜头


def lock_overlay(base: Image.Image, date, time, clock_font, subject_mask: Image.Image = None):
    """iOS 锁屏叠层。subject_mask（L，同尺寸）不为空时模拟「景深效果」：把前景主体再贴回时钟上面。"""
    img = base.convert("RGBA")
    # 圆钮：模糊 + 压暗 的毛玻璃
    for cx in BTN_CX:
        box = (cx - BTN_R, BTN_CY - BTN_R, cx + BTN_R, BTN_CY + BTN_R)
        patch = glass_patch(img.convert("RGB"), box, blur=28, white_alpha=0.0, dark=0.74)
        m = Image.new("L", patch.size, 0)
        ImageDraw.Draw(m).ellipse((0, 0, patch.size[0] - 1, patch.size[1] - 1), fill=255)
        img.paste(patch, box[:2], m)
    # 圆钮上的白色图标（用透明挖孔，所以单独一层 alpha 合成）
    glyphs = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(glyphs)
    flashlight_glyph(d, BTN_CX[0], BTN_CY, s=0.88)
    camera_glyph(d, BTN_CX[1], BTN_CY, s=0.88)
    # 挖孔要真正透出底图：把 glyph 层里 alpha=0 的「孔」保留为透明即可（alpha_composite 自然处理）
    img.alpha_composite(glyphs)
    # 日期 + 时钟
    draw_text_centered(img, date, font(clock_font, DATE_SIZE, DATE_WGHT), W / 2, DATE_CY)
    draw_text_centered(img, time, font(clock_font, TIME_SIZE, TIME_WGHT), W / 2, TIME_CY)
    # 景深效果：主体压在时钟前面（iOS 16+ 锁屏「景深效果」的样子；只遮时钟，不遮按钮和 Home 条）
    if subject_mask is not None:
        fg = base.convert("RGBA")
        fg.putalpha(subject_mask.convert("L"))
        img.alpha_composite(fg)
    # Home 条
    bar = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(bar).rounded_rectangle(BAR, radius=9, fill=(255, 255, 255, 235))
    img.alpha_composite(bar)
    return img.convert("RGB")


def home_overlay(base: Image.Image):
    img = base.convert("RGB")
    cells = [(cx, cy) for cy in ICON_ROWS_CY for cx in ICON_CX] + [(cx, DOCK_CY) for cx in ICON_CX]
    mask = rounded_mask((ICON, ICON), ICON_R)
    edge = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle((1, 1, ICON - 2, ICON - 2), ICON_R, outline=(255, 255, 255, 140), width=3)
    for cx, cy in cells:
        box = (cx - ICON // 2, cy - ICON // 2, cx + ICON // 2, cy + ICON // 2)
        patch = glass_patch(img, box, blur=40, white_alpha=0.42).convert("RGBA")
        patch.alpha_composite(edge)
        img.paste(patch.convert("RGB"), box[:2], mask)
    return img


# ------------------------------------------------------------------ 拼版
def phone_frame(im, size, r, border=4, shadow=True, bg=None):
    """缩到 size，切圆角，加深色细边 + 柔影；返回带透明的 RGBA 贴片（含阴影边距）。"""
    pad = 40 if shadow else 0
    w, h = size
    tile = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", tile.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 14, pad + w, pad + h + 14), r, fill=(60, 40, 30, 70))
        tile.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22)))
    body = im.convert("RGB").resize(size, Image.LANCZOS)
    m = rounded_mask(size, r)
    frame = Image.new("RGBA", size, (0, 0, 0, 0))
    frame.paste(body, (0, 0), m)
    if border:
        ImageDraw.Draw(frame).rounded_rectangle((0, 0, w - 1, h - 1), r, outline=(52, 44, 40, 255), width=border)
    tile.alpha_composite(frame, (pad, pad))
    return tile


def contact_sheet(spec, previews, out, cjk_font, bezel=False):
    cols, tw = 5, 300
    th = round(tw * H / W)
    gap, margin, header = 36, 60, 120
    rows = (len(previews) + cols - 1) // cols
    sw = margin * 2 + cols * tw + (cols - 1) * gap
    sh = margin + header + rows * th + (rows - 1) * gap + margin
    sheet = Image.new("RGBA", (sw, sh), (241, 222, 203, 255))
    d = ImageDraw.Draw(sheet)
    d.text((margin, margin - 6), spec["title"], font=font(cjk_font, 46), fill=(58, 46, 42))
    d.text((margin, margin + 60), spec["subtitle"], font=font(cjk_font, 24), fill=(120, 100, 92))
    for i, p in enumerate(previews):
        tile = phone_frame(Image.open(p), (tw, th), r=28, border=3 if bezel else 0)
        x = margin + (i % cols) * (tw + gap) - 40
        y = margin + header + (i // cols) * (th + gap) - 40
        sheet.alpha_composite(tile, (x, y))
    sheet.convert("RGB").save(out, "JPEG", quality=92)
    return out


def cover(spec, left_img, right_img, out, bezel=False):
    S = 1600
    bg = Image.new("RGBA", (S, S), (241, 222, 203, 255))
    pw = 560
    ph = round(pw * H / W)
    y = (S - ph) // 2
    for im, x in ((left_img, 170), (right_img, 870)):
        bg.alpha_composite(phone_frame(Image.open(im), (pw, ph), r=72 if bezel else 48, border=5 if bezel else 0), (x - 40, y - 40))
    bg.convert("RGB").save(out, "JPEG", quality=93)
    return out


# ------------------------------------------------------------------ 主流程
def page_name(spec, pg):
    return f"{spec.get('prefix', '复刻图')}{pg['n']:02d}-{pg['name']}"


def cmd_build(a, spec):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    clock = None
    if a.ui == "ios":
        clock = find_font(a.clock_font, "CLOCK_FONT", CLOCK_CANDS)
        if not clock:
            sys.exit("--ui ios 需要时钟字体：--clock-font 或 CLOCK_FONT（推荐 Inter）")
        (out / "预览-iOS").mkdir(parents=True, exist_ok=True)
    date, time = a.date or spec.get("date"), a.time or spec.get("time", "05:20")
    for pg in spec["pages"]:
        src = Path(a.art_dir) / f"{pg['n']:02d}.png"
        if not src.exists():
            print(f"[skip] {src} 不存在")
            continue
        ax, ay = float(pg.get("ax", 0.5)), float(pg.get("ay", 0.5))
        base = fit_canvas(Image.open(src), ax=ax, ay=ay)
        name = page_name(spec, pg)
        save(base, out / f"{name}.{a.format}")                      # 干净壁纸 = 交付物
        depth = ""
        if a.ui == "ios":
            mask = None
            if a.mask_dir and pg.get("overlay") == "lock" and pg.get("depth", True):
                mp = Path(a.mask_dir) / f"{pg['n']:02d}.png"
                if mp.exists():
                    mask = fit_canvas(Image.open(mp).convert("L"), ax=ax, ay=ay)
                    depth = " depth=on"
            prev = lock_overlay(base, date, time, clock, mask) if pg.get("overlay") == "lock" else home_overlay(base)
            save(prev, out / "预览-iOS" / f"{name}.{a.format}")
        print(f"[build] {name}" + (f"  ios-overlay={pg.get('overlay')}{depth}" if a.ui == "ios" else ""))


def save(im, path):
    path = Path(path)
    if path.suffix.lower() in (".jpg", ".jpeg"):
        im.convert("RGB").save(path, "JPEG", quality=92, subsampling=0)
    else:
        im.save(path, "PNG", compress_level=6)


def page_file(spec, out, pg, ui="none"):
    base = Path(out) / "预览-iOS" if ui == "ios" else Path(out)
    for ext in ("png", "jpg"):
        p = base / f"{page_name(spec, pg)}.{ext}"
        if p.exists():
            return p
    return None


def previews_of(spec, out, ui="none"):
    return [p for p in (page_file(spec, out, pg, ui) for pg in spec["pages"]) if p]


def cmd_sheet(a, spec):
    cjk = find_font(a.cjk_font, "CJK_FONT", CJK_CANDS)
    if not cjk:
        sys.exit("找不到中文字体：--cjk-font 或 CJK_FONT（霞鹜文楷：healing-comic/scripts/fetch_font.sh）")
    files = previews_of(spec, a.out, a.ui)
    if not files:
        sys.exit("sheet: 没找到壁纸文件，先跑 build")
    print("[sheet]", contact_sheet(spec, files, Path(a.out) / "总图.jpg", cjk, bezel=(a.ui == "ios")))


def cmd_cover(a, spec):
    byn = {pg["n"]: pg for pg in spec["pages"]}
    c = spec.get("cover", {"left": 1, "right": 2})
    def pick(n):
        p = page_file(spec, a.out, byn[n], a.ui)
        if not p:
            sys.exit(f"cover: 找不到第 {n} 页")
        return p
    l, r = pick(c["left"]), pick(c["right"])
    print("[cover]", cover(spec, l, r, Path(a.out) / "封面-双机预览.jpg", bezel=(a.ui == "ios")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "sheet", "cover", "all"])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--art-dir", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--date", default=None)
    ap.add_argument("--time", default=None)
    ap.add_argument("--clock-font", default=None)
    ap.add_argument("--cjk-font", default=None)
    ap.add_argument("--format", choices=["png", "jpg"], default="png", help="输出格式（交付用 png，仓库留档用 jpg）")
    ap.add_argument("--ui", choices=["none", "ios"], default="none", help="none=干净壁纸（默认）；ios=额外输出带锁屏/主屏覆盖层的效果预览")
    ap.add_argument("--mask-dir", default=None, help="景深效果：depth_mask.py 输出的主体蒙版目录（NN.png），锁屏页会把主体贴回时钟前面；spec 每页可写 \"depth\": false 关掉")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    if a.cmd in ("build", "all"):
        if not a.art_dir:
            sys.exit("build 需要 --art-dir")
        cmd_build(a, spec)
    if a.cmd in ("sheet", "all"):
        cmd_sheet(a, spec)
    if a.cmd in ("cover", "all"):
        cmd_cover(a, spec)


if __name__ == "__main__":
    main()
