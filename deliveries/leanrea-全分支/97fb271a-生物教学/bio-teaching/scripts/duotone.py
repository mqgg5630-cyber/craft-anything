#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把配图统一成「单墨双色版画」（duotone）。

为什么要有这一步：
    一套课件里同时出现写实照片、3D 渲染、水彩插画、风景照，视觉上是「四种材料拼起来」。
    生物学教材真正统一的视觉语言是**单色版画 / 铜版画**：一张纸，一种墨。
    把所有配图压到「墨 + 纸」两个色阶，混合媒介立刻读成同一套图版。

第三代（v3）改了三点：
    1. 墨色与纸色跟着版式主题走——学术冷版、课堂暖版、教材版各自一套色，
       图和页面纸色**完全同色**，于是图片可以「meet」放进版面而看不见边框（纸底自然过渡）。
    2. 抽出 `tone()` 供 build_deck.py 直接调用，构建时按主题上色，源图只留一份原图。
    3. 曲线仍保留 gamma，避免中间调压成死黑。

用法：
    python3 scripts/duotone.py <原图目录> <输出目录> [--width 1500] [--theme textbook]
    python3 scripts/duotone.py <原图目录> <输出目录> --paper F7F4EA --ink 16282A

输出两个版本：
    <name>-light.jpg   浅版：纸底、墨色，用于浅色页的嵌版图 / 满版图
    <name>-ink.jpg     深版：墨底、亮部收窄，用于深色页压白字
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

# 主题 → (纸色, 墨色)；与 build_deck.py 的 THEMES 保持一致
THEME_TONE = {
    "plate": ("F4EFE4", "14302F"),
    "academic": ("F1F0EB", "111E20"),
    "classroom": ("F8F1E2", "1D2E29"),
    "textbook": ("F7F4EA", "16282A"),
}


def hex_rgb(s: str) -> tuple[int, int, int]:
    s = s.strip().lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def mix(a, b, t: float):
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def tone(img: Image.Image, low, high, contrast=1.15, gamma=0.58) -> Image.Image:
    """单墨上色：灰度 → 自动对比 → 对比度 → gamma → 双色映射。"""
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(contrast)
    if gamma != 1.0:
        g = g.point(lambda v: int(255 * (v / 255.0) ** gamma))
    return ImageOps.colorize(g, black=low, white=high)


def make_pair(img: Image.Image, paper_hex: str, ink_hex: str, light_contrast=1.15,
              light_gamma=0.58, ink_contrast=1.10):
    """一张原图 → (浅版, 深版)。深版压高光，保证白字压得住。"""
    paper, ink = hex_rgb(paper_hex), hex_rgb(ink_hex)
    light = tone(img, ink, paper, contrast=light_contrast, gamma=light_gamma)
    deep = mix(ink, (0, 0, 0), 0.45)
    soft = mix(ink, paper, 0.44)
    dark = tone(img, deep, soft, contrast=ink_contrast)
    return light, dark


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--width", type=int, default=1500)
    ap.add_argument("--theme", default="", choices=["", *THEME_TONE])
    ap.add_argument("--paper", default="F4EFE4")
    ap.add_argument("--ink", default="14302F")
    a = ap.parse_args()

    paper, ink = (THEME_TONE[a.theme] if a.theme else (a.paper, a.ink))
    src, dst = Path(a.src), Path(a.dst)
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(src.glob("*.jpg")) + sorted(src.glob("*.png")):
        if f.name.startswith("_"):
            continue
        img = Image.open(f).convert("RGB")
        if img.width > a.width:
            img = img.resize((a.width, round(img.height * a.width / img.width)), Image.LANCZOS)
        light, dark = make_pair(img, paper, ink)
        light.save(dst / f"{f.stem}-light.jpg", quality=86, optimize=True)
        dark.save(dst / f"{f.stem}-ink.jpg", quality=86, optimize=True)
        n += 2
    print(f"[ok] {n} 张（{n // 2} 组 light/ink，纸 #{paper} 墨 #{ink}）→ {dst}")


if __name__ == "__main__":
    main()
