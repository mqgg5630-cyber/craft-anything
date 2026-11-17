#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dialogue.py —— 在成品图上合成「很简单的对话」

规则和 finish.py 一样铁：**图片模型一个字都不写**。
出图时只留空位，对话在这里用脚本画上去，
所以中文不会错字、不会糊、不会被模型画成伪字。

画面版式（每张都照这个来）
  顶部 16%   留白 → 上方气泡（布布说）
  中部       角色
  底部 22%   留白 → 下方气泡（一二答）+ 一行小英文

用法
    python3 dialogue.py spec.json

spec.json
    {
      "outdir": "out",
      "sheet":  "out/总图.jpg",
      "grain":  0.010,
      "items": [
        {"src": "k01.png", "name": "对话图01", "top": "今天的蛋煎糊了",
         "bottom": "糊了也好吃", "word": "BREAKFAST"}
      ]
    }
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import json, sys, os, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finish  # 复用裁切 / USM / 胶片分级 / 字体选择

TW, TH = 1080, 2280

INK = (58, 42, 34)          # 气泡里字的颜色：暖墨色，不用纯黑
PAPER = (252, 248, 241)     # 气泡纸色
OUTLINE = 5                 # 描边粗细
TOP_CY = 0.105              # 上气泡中心 y（比例）
BOT_CY = 0.855              # 下气泡中心 y
WORD_Y = 0.945              # 底部小英文 y


def bubble(draw, text, cy, font, tail_down=True, max_w=920):
    """画一个白底墨边对话气泡，尾巴指向角色。返回 (x0,y0,x1,y1)。"""
    tw, th = draw.textbbox((0, 0), text, font=font)[2:]
    padx, pady = 52, 36
    w = min(max_w, tw + padx * 2)
    h = th + pady * 2
    cx = TW // 2
    x0, y0 = cx - w // 2, int(cy - h // 2)
    x1, y1 = x0 + w, y0 + h

    # 尾巴先画，再压气泡本体，接缝就被盖住了
    t = 46
    if tail_down:
        tri = [(cx - t // 2, y1 - 6), (cx + t // 2, y1 - 6), (cx - 8, y1 + 38)]
    else:
        tri = [(cx - t // 2, y0 + 6), (cx + t // 2, y0 + 6), (cx + 8, y0 - 38)]
    draw.polygon(tri, fill=PAPER, outline=INK)
    draw.line([tri[0], tri[2]], fill=INK, width=OUTLINE)
    draw.line([tri[1], tri[2]], fill=INK, width=OUTLINE)

    draw.rounded_rectangle([x0, y0, x1, y1], radius=42, fill=PAPER,
                           outline=INK, width=OUTLINE)
    draw.text((cx - tw // 2, y0 + pady - 6), text, font=font, fill=INK)
    return x0, y0, x1, y1


def frost_panel(im, box, radius=46, blur=34, tint=0.34):
    """从画面自己身上取材质：把该区域模糊后当文字底。

    之前用的是外来白纸（#FCF8F1 + 墨描边），跟画面的暖调对不上，
    用户一句「字的背景和图片的背景不一样」——
    所以改成：底 = 这块画面本身（模糊 + 轻微提亮/压暗），
    字色 = 从这块底的明暗推出来。底和画面是同一种材质，就一致了。
    """
    x0, y0, x1, y1 = box
    pad = 60                                  # 模糊会吃边缘，多取一圈
    sx0, sy0 = max(0, x0 - pad), max(0, y0 - pad)
    sx1, sy1 = min(TW, x1 + pad), min(TH, y1 + pad)
    region = im.crop((sx0, sy0, sx1, sy1)).filter(ImageFilter.GaussianBlur(blur))

    # 这块画面本身是亮还是暗 → 决定压暗还是提亮
    base = np.asarray(im.crop((x0, y0, x1, y1)).convert("L")).astype(np.float32)
    m = float(base.mean())
    overlay = Image.new("RGB", region.size, (28, 20, 16) if m > 138 else (255, 250, 242))
    region = Image.blend(region, overlay, tint)

    mask = Image.new("L", region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [x0 - sx0, y0 - sy0, x1 - sx0, y1 - sy0], radius=radius, fill=255)
    im.paste(region, (sx0, sy0), mask)
    return m


def panel(draw, im, text, cy, font, word=None, wfont=None):
    """毛玻璃文字牌：底来自画面，字色由底的明暗决定。"""
    tw, th = draw.textbbox((0, 0), text, font=font)[2:]
    ww, wh = (draw.textbbox((0, 0), word, font=wfont)[2:] if word else (0, 0))
    padx, pady = 60, 40
    w = min(940, max(tw, ww) + padx * 2)
    h = th + pady * 2 + (wh + 22 if word else 0)
    cx = TW // 2
    x0, y0, x1, y1 = cx - w // 2, int(cy - h / 2), cx + w // 2, int(cy + h / 2)

    m = frost_panel(im, (x0, y0, x1, y1))
    col = (74, 56, 46) if m > 138 else (252, 246, 238)   # 亮底用暖墨，暗底用奶油白

    ty = y0 + pady - 6
    draw.text((cx - tw // 2, ty), text, font=font, fill=col)
    if word:
        wy = ty + th + 22
        ln = max(ww, 120)
        draw.line([cx - ln // 2, wy - 12, cx + ln // 2, wy - 12],
                  fill=col + (None,), width=0) if False else None
        draw.text((cx - ww // 2, wy), word, font=wfont, fill=col)
    return x0, y0, x1, y1


def small_word(draw, word, font, im=None, y=None):
    """底部一行小英文——保持「每张都有英文元素」这条老规矩。

    颜色必须跟着背景走：亮底用暖墨，暗底用奶油白。
    第一版写死奶油白，结果早餐那张（亮场景）整行字糊在亮底里看不见。
    """
    tw = draw.textbbox((0, 0), word, font=font)[2]
    cx = TW // 2
    y = int(TH * WORD_Y) if y is None else int(y)
    # 取这一行的背景亮度，决定用深字还是浅字
    ink_bg = 0.5
    if im is not None:
        band = np.asarray(im.convert("RGB"))[y - 20:y + 60, cx - 260:cx + 260]
        ink_bg = float(band.mean()) / 255.0 if band.size else 0.5
    col = (250, 244, 234) if ink_bg < 0.55 else (96, 74, 60)
    draw.line([cx - tw // 2 - 30, y - 26, cx + tw // 2 + 30, y - 26],
              fill=col, width=3)
    draw.text((cx - tw // 2, y), word, font=font, fill=col)


def find_free_band(im, top=0.62, bot=0.99, need=96):
    """对话烤进画面之后，字在哪儿不由我们控制。

    所以先在下半幅找一条「最空」的横带放小英文——
    行间差分越小 = 细节越少 = 越干净。找不到足够空的地方就返回 None，
    宁可不放，也不压在烤进去的中文上。
    """
    g = np.asarray(im.convert("L")).astype(np.float32)
    y0, y1 = int(TH * top), int(TH * bot)
    rows = g[y0:y1]
    dens = np.abs(np.diff(rows, axis=0)).mean(axis=1)
    if len(dens) < need:
        return None
    win = np.convolve(dens, np.ones(need) / need, mode="valid")
    i = int(np.argmin(win))
    if win[i] > np.median(dens) * 0.75:      # 不够空 → 放弃
        return None
    return y0 + i + 12


def bare_text(im, draw, text, cy, font, word=None, wfont=None):
    """无底排版：字直接坐在画面上，没有牌子、没有外来底色。

    毛玻璃那版仍然是一块「板」（实测 Δ 60~97），用户要的是**根本没有底**。
    所以：底 = 画面本身，一个像素都不加。
    可读性靠一层很淡的柔光描边（描边色是字色的反色，半透明），
    这样在任何底色上都读得清，又不会像贴纸。
    """
    tw, th = draw.textbbox((0, 0), text, font=font)[2:]
    ww, wh = (draw.textbbox((0, 0), word, font=wfont)[2:] if word else (0, 0))
    cx = TW // 2
    ty = int(cy - (th + (wh + 26 if word else 0)) / 2) - 6

    # 这块留白带本身是亮还是暗 → 决定字用暖墨还是奶油白
    band = np.asarray(im.convert("L"))[max(0, ty - 20):min(TH, ty + th + 40)].astype(np.float32)
    m = float(band.mean())
    # 别用固定阈值切明暗——底色正好卡在临界点时字色会选错（03/07 下句就栽在这）。
    # 改成：墨色和奶油白谁离底色更远就选谁，永远选对比更大的那一个。
    INK_LUM, CREAM_LUM = 52.0, 247.0
    light = abs(m - INK_LUM) > abs(m - CREAM_LUM)
    ink = (66, 50, 40) if light else (252, 247, 240)
    contrast = abs((INK_LUM if light else CREAM_LUM) - m)
    # 对比不够就把柔光描边加厚加重（而不是去动画面底色）
    alpha = 200 if contrast < 80 else (150 if contrast < 120 else 120)
    halo = (255, 250, 243, alpha) if light else (24, 16, 12, alpha)

    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((cx - tw // 2, ty), text, font=font, fill=ink + (255,),
           stroke_width=9, stroke_fill=halo)
    if word:
        d.text((cx - ww // 2, ty + th + 26), word, font=wfont, fill=ink + (255,),
               stroke_width=6, stroke_fill=halo)
    im.paste(Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB"), (0, 0))
    return light


def make_sheet(paths, out, cols=5, tile_w=300):
    """把成品拼成一张总图，方便选首图。"""
    tw = TH * tile_w // TW
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (tile_w * cols, tw * rows), (246, 241, 234))
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB").resize((tile_w, tw), Image.LANCZOS)
        sheet.paste(im, ((i % cols) * tile_w, (i // cols) * tw))
    sheet.save(out, quality=90)
    return sheet.size


def main(spec_path):
    spec = json.load(open(spec_path, encoding="utf-8"))
    outdir = spec["outdir"]
    grain = spec.get("grain", 0.010)
    os.makedirs(outdir, exist_ok=True)

    f_text = finish.pick_font(62, lang="zh")
    f_word = finish.pick_font(40, lang="en")

    made = []
    for i, it in enumerate(spec["items"]):
        im = Image.open(it["src"]).convert("RGB")
        # 1 裁到 9:19  2 放大到 1080x2280  3 USM  4 胶片分级
        w, h = im.size
        tr = TW / TH
        if w / h > tr:
            nw = int(h * tr); im = im.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
        else:
            nh = int(w / tr); top = int((h - nh) * 0.42)
            im = im.crop((0, top, w, top + nh))
        im = im.resize((TW, TH), Image.LANCZOS)
        im = im.filter(__import__("PIL.ImageFilter", fromlist=["x"]).UnsharpMask(2, 60, 3))
        im = finish.film_grade(im, grain=grain,
                               rng=np.random.default_rng(7 + i))

        d = ImageDraw.Draw(im)
        style = spec.get("style", "bare")           # bare（默认，无底） / frost（毛玻璃） / paper（老白纸）
        if it.get("top"):
            if style == "frost":
                panel(d, im, it["top"], TH * TOP_CY, f_text)
            elif style == "paper":
                bubble(d, it["top"], TH * TOP_CY, f_text, tail_down=True)
            else:                       # bare（默认）：字直接坐在画面上
                bare_text(im, d, it["top"], TH * TOP_CY, f_text)
        if it.get("bottom"):
            if style == "frost":
                panel(d, im, it["bottom"], TH * BOT_CY, f_text,
                      word=it.get("word"), wfont=f_word)
            elif style == "paper":
                bubble(d, it["bottom"], TH * BOT_CY, f_text, tail_down=False)
                if it.get("word"):
                    small_word(d, it["word"], f_word, im=im)
            else:
                bare_text(im, d, it["bottom"], TH * BOT_CY, f_text,
                          word=it.get("word"), wfont=f_word)

        out = os.path.join(outdir, it["name"] + ".png")
        im.save(out)
        made.append(out)
        print(f"{it['name']}: 上「{it.get('top','')}」 下「{it.get('bottom','')}」 "
              f"word={it.get('word','')} -> {im.size}")

    if spec.get("sheet"):
        s = make_sheet(sorted(made), spec["sheet"])
        print(f"sheet -> {spec['sheet']} {s}")


if __name__ == "__main__":
    main(sys.argv[1])
