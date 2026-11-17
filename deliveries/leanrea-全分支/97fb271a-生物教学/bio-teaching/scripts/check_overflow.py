#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文本包围盒与行距检查（无渲染环境下的替代品）。

沙箱里没有中文字体、没有 libreoffice、没有 libcairo，无法把 SVG 渲染成图来看。
这个脚本按「CJK 一字一 em、ASCII 半 em」估每一行文字的宽高，检查：
    · 左/右越出安全边（22px）
    · 上/下越出页面
    · 两段文字在页面上相撞（横纵区间同时相交）
    · 同一段落内 <tspan> 行距过挤（< 1.05 字号，汉字会顶在一起）

用法：python3 scripts/check_overflow.py <目录>...（目录可以是构建根或 svg 目录）
退出码 0 = 全部通过。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

W, H = 1280, 720
SAFE = 22

TEXT = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
TSPAN = re.compile(r"<tspan\b([^>]*)>(.*?)</tspan>", re.S)
ATTR = re.compile(r'([\w:-]+)="([^"]*)"')


def attrs(s: str) -> dict:
    return dict(ATTR.findall(s or ""))


def tw(s: str, fs: float, ls: float) -> float:
    raw = sum((0.52 if ord(c) < 128 else 1.0) for c in s) * fs
    return raw + len(s) * ls


def lines_of(at: str, body: str) -> list[tuple[float, float, str, float, float]]:
    """把一段（可能带 tspan）拆成若干行：(x, y, 文本, 字号, 字距)。"""
    a = attrs(at)
    fs = float(a.get("font-size", 20))
    ls = float(a.get("letter-spacing", 0) or 0)
    x = float(a.get("x", 0))
    y = float(a.get("y", 0))
    anchor = a.get("text-anchor", "start")
    out = []
    head = re.split(r"<tspan\b", body)[0]
    head = re.sub(r"<[^>]+>", "", head)
    if head.strip():
        out.append((x, y, head, fs, ls, anchor))
    cur_y = y
    for m in TSPAN.finditer(body):
        ta = attrs(m.group(1))
        cur_x = float(ta.get("x", x))
        cur_y += float(ta.get("dy", 0))
        txt = re.sub(r"<[^>]+>", "", m.group(2))
        out.append((cur_x, cur_y, txt, fs, ls, anchor))
    return out


def _lum(hexcolor: str) -> float:
    h = hexcolor.lstrip("#")
    if len(h) != 6:
        return 0.5
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def page_bg(t: str) -> str:
    """取覆盖面积最大的矩形当底色（深色整版页也能正确判定）。"""
    best, area = "#FFFFFF", 0.0
    for m in re.finditer(r'<rect[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"[^>]*fill="(#[0-9A-Fa-f]{6})"', t):
        a = float(m.group(1)) * float(m.group(2))
        if a > area:
            area, best = a, m.group(3)
    return best


def check(path: Path) -> list[str]:
    t = path.read_text(encoding="utf-8")
    out: list[str] = []
    bg = page_bg(t)
    boxes: list[tuple[float, float, float, float, str]] = []
    for m in TEXT.finditer(t):
        at, body = m.group(1), m.group(2)
        rows = lines_of(at, body)
        fs = float(attrs(at).get("font-size", 20))
        for k in range(1, len(rows)):
            gap = rows[k][1] - rows[k - 1][1]
            if gap < fs * 1.05 and rows[k][2].strip() and rows[k - 1][2].strip():
                out.append(f"{path.name}: 行距过挤 {gap:.0f}px / 字号 {fs:.0f}  「{rows[k][2][:14]}」")
        for (x, y, txt, f_s, ls, anchor) in rows:
            if not txt.strip():
                continue
            w = tw(txt, f_s, ls)
            left = x if anchor == "start" else x - w / 2 if anchor == "middle" else x - w
            right = left + w
            if right > W - SAFE:
                out.append(f"{path.name}: 右越界 {right - (W - SAFE):.0f}px  「{txt[:18]}」")
            if left < SAFE:
                out.append(f"{path.name}: 左越界 {SAFE - left:.0f}px  「{txt[:18]}」")
            if y > H - 18:
                out.append(f"{path.name}: 下越界 y={y:.0f}  「{txt[:18]}」")
            if y < 18:
                out.append(f"{path.name}: 上越界 y={y:.0f}  「{txt[:18]}」")
            boxes.append((left, y - f_s * 0.86, right, y + f_s * 0.18, txt))
            fill = re.search(r'fill="(#[0-9A-Fa-f]{6})"', at)
            if fill:
                ratio = _contrast(fill.group(1), bg)
                need = 3.0 if f_s >= 24 else 4.2
                if ratio < need:
                    out.append(f"{path.name}: 对比度低 {ratio:.1f}:1（需 ≥{need}）"
                               f"「{txt[:16]}」")

    for i in range(len(boxes)):
        a = boxes[i]
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > 6 and oy > 5 and oy > min(a[3] - a[1], b[3] - b[1]) * 0.34:
                out.append(f"{path.name}: 文字相撞 「{a[4][:12]}」×「{b[4][:12]}」")
    return out


def main() -> int:
    roots = [Path(a) for a in sys.argv[1:]] or [Path(".")]
    bad: list[str] = []
    n = 0
    for r in roots:
        d = r / "svg_output" if (r / "svg_output").is_dir() else r
        for f in sorted(d.glob("*.svg")):
            n += 1
            bad += check(f)
    print(f"检查 {n} 页，问题 {len(bad)} 处")
    for b in bad[:80]:
        print("  " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
