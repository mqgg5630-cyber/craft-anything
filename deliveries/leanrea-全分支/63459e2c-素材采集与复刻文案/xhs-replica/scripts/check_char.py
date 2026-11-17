#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_char.py —— 角色跑偏自查（代理人看不到图，只能靠量）

第 14 轮整轮翻车：一二被画成了一只奶油棕熊，10 张全是「两个布布」。
肉眼一眼能看出来，但代理人没有视觉，所以写一个能测的代理指标。

原理
  一二 = 纯白圆身 + 实心黑耳 + 黑眼罩 + 黑领结 → 画面里必须有一片**低饱和亮面**。
  布布 = 奶茶棕 → 画面里有一片**中饱和暖棕**。
  两个都在 → 亮面占比不会太低。

指标
  w_warm  = min(R,G,B) > 160 且 sat < 0.30 的像素占比   ← 一二的白色身体
  brown   = 中饱和暖棕像素占比                          ← 布布

基线（实测，256×256 采样）
  第12轮 ✅  均值 10.7%  最小  4.4%
  第13轮 ✅  均值  6.8%  最小  2.9%
  第14轮 ❌  均值  2.6%  最小  0.0%   ← 整轮没有一二

判定
  w_warm < 2.5%  →  ⚠️ 疑似缺一二（白团子没画出来）
  brown  < 1.0%  →  ⚠️ 疑似缺布布
  只是预警，不是判决——最终还是得让用户看。

用法
  python3 scripts/check_char.py 目录/*.png
"""
import sys, glob, os
import numpy as np
from PIL import Image

W_WARN = 2.5
B_WARN = 1.0


def feat(path):
    a = np.asarray(Image.open(path).convert("RGB").resize((256, 256))).astype(int)
    mx, mn = a.max(2), a.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    w = ((mn > 160) & (sat < 0.30)).mean() * 100
    brown = ((r > 110) & (r < 200) & (g > 80) & (g < 160) & (b > 55) & (b < 130)
             & (r > g) & (g > b) & (sat > 0.18)).mean() * 100
    return w, brown


def main(paths):
    bad = 0
    print(f"{'file':40}{'white(一二)':>12}{'brown(布布)':>12}   判定")
    print("-" * 78)
    for p in paths:
        w, br = feat(p)
        flags = []
        if w < W_WARN:
            flags.append("⚠️疑似缺一二")
        if br < B_WARN:
            flags.append("⚠️疑似缺布布")
        if flags:
            bad += 1
        verdict = " ".join(flags) or "ok"
        print(f"{os.path.basename(p):40}{w:11.1f}%{br:11.1f}%   {verdict}")
    print("-" * 78)
    if bad:
        print(f"⚠️ {bad}/{len(paths)} 张疑似角色跑偏。别上传，先让用户看。")
        return 1
    print(f"✅ {len(paths)} 张都在基线内。仍然要让用户确认——这个脚本只能量颜色，看不了脸。")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    files = []
    for a in args:
        if os.path.isdir(a):
            files += sorted(glob.glob(os.path.join(a, "*.png")))
        else:
            files.append(a)
    if not files:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(files))
