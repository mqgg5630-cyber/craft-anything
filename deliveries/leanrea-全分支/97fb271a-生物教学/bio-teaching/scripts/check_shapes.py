#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图形元素相撞检查：文字之外那些「看起来没事、投影出来很脏」的地方。

`check_overflow.py` 只管文字与文字。但真正难看的往往是**图形与文字之间**的问题，
在没有渲染环境的沙箱里，肉眼看不见，只能靠几何算：

    · 元素越界         图片/图形跨出画布（裁掉一半）
    · 图压字           图片绘制顺序在文字之后，把字盖住了
    · 色块压字         不透明色块盖住文字（标题压进导航条这种）
    · 图碰图           两张图重叠一大块（通常是坐标写错，不是刻意拼贴）
    · 线穿字           分隔线/箭头从字中间穿过去

判定用**绘制顺序 = 文档顺序**（SVG 后画的在上面），所以只有"后画的"压"先画的"才算压。

用法：python3 scripts/check_shapes.py <目录>...（构建根或 svg 目录）
退出码 0 = 没有硬伤（WARN 不阻塞）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from check_overflow import attrs, lines_of, tw

W, H = 1280, 720
EDGE = 1.5          # 容差：贴边不算越界
TEXT_COVER = 0.20   # 图片盖住文字面积的多少算"压"
BLOCK_COVER = 0.50  # 不透明色块盖住多少算"压"
IMG_IMG = 0.12      # 两张图重叠占小图面积的比例

TAG = re.compile(r"<(image|rect|circle|polygon|polyline|line|path|text)\b([^>]*?)/?>(?:(.*?)</\1>)?", re.S)
ATTR = re.compile(r'([\w:-]+)="([^"]*)"')

NUM = r"[-+]?[\d.]+(?:[eE][-+]?\d+)?"


def f(a: dict, k: str, d: float = 0.0) -> float:
    try:
        return float(a.get(k, d))
    except (TypeError, ValueError):
        return d


def path_bbox(d: str) -> tuple[float, float, float, float] | None:
    """粗略 path 包围盒：把各命令的控制点都算进去（偏大一点，够用来查相撞）。"""
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|" + NUM, d)
    xs: list[float] = []
    ys: list[float] = []
    cx = cy = sx = sy = 0.0
    i, cmd = 0, "M"
    while i < len(toks):
        tk = toks[i]
        if re.match(r"[A-Za-z]", tk):
            cmd = tk
            i += 1
            if cmd in "Zz":
                cx, cy = sx, sy
            continue
        rel = cmd.islower()
        c = cmd.upper()
        need = {"M": 2, "L": 2, "T": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "A": 7}.get(c, 0)
        nums = toks[i:i + need]
        if len(nums) < need:
            break
        v = [float(x) for x in nums]
        i += need
        if c in ("M", "L", "T"):
            x, y = v[0] + (cx if rel else 0), v[1] + (cy if rel else 0)
            if c == "M":
                sx, sy = x, y
            xs.append(x), ys.append(y)
            cx, cy = x, y
            if c == "M":
                cmd = "l" if rel else "L"
        elif c == "H":
            cx = v[0] + (cx if rel else 0)
            xs.append(cx), ys.append(cy)
        elif c == "V":
            cy = v[0] + (cy if rel else 0)
            xs.append(cx), ys.append(cy)
        elif c in ("C", "S", "Q"):
            pts = [(v[k], v[k + 1]) for k in range(0, len(v), 2)]
            for px, py in pts:
                xs.append(px + (cx if rel else 0)), ys.append(py + (cy if rel else 0))
            cx, cy = xs[-1], ys[-1]
        elif c == "A":
            x, y = v[5] + (cx if rel else 0), v[6] + (cy if rel else 0)
            xs.append(x), ys.append(y)
            cx, cy = x, y
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def elements(svg: str):
    """按文档顺序产出 (kind, bbox, attr)。bbox = (x0, y0, x1, y1)。"""
    for m in TAG.finditer(svg):
        kind, a, body = m.group(1), dict(ATTR.findall(m.group(2))), m.group(3) or ""
        if kind == "image":
            x, y = f(a, "x"), f(a, "y")
            yield "image", (x, y, x + f(a, "width"), y + f(a, "height")), a
        elif kind == "rect":
            x, y = f(a, "x"), f(a, "y")
            yield "rect", (x, y, x + f(a, "width"), y + f(a, "height")), a
        elif kind == "circle":
            cx, cy, r = f(a, "cx"), f(a, "cy"), f(a, "r")
            yield "circle", (cx - r, cy - r, cx + r, cy + r), a
        elif kind in ("polygon", "polyline"):
            nums = [float(v) for v in re.findall(NUM, a.get("points", ""))]
            xs, ys = nums[0::2], nums[1::2]
            if xs:
                yield kind, (min(xs), min(ys), max(xs), max(ys)), a
        elif kind == "line":
            x1, y1, x2, y2 = f(a, "x1"), f(a, "y1"), f(a, "x2"), f(a, "y2")
            pad = max(1.2, f(a, "stroke-width", 1.0) / 2)   # 水平线没有高度，得按线宽给厚度
            yield "line", (min(x1, x2), min(y1, y2) - pad, max(x1, x2), max(y1, y2) + pad), a
        elif kind == "path":
            b = path_bbox(a.get("d", ""))
            if b:
                pad = max(1.2, f(a, "stroke-width", 1.0) / 2)
                yield "path", (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad), a
        else:  # text
            box = None
            for (x, y, txt, fs, ls, anchor) in lines_of(m.group(2), body):
                if not txt.strip():
                    continue
                w = tw(txt, fs, ls)
                left = x if anchor == "start" else x - w / 2 if anchor == "middle" else x - w
                b = (left, y - fs * 0.86, left + w, y + fs * 0.18)
                box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                             max(box[2], b[2]), max(box[3], b[3]))
            if box:
                yield "text", box, a


def overlap(a, b) -> tuple[float, float, float]:
    ox = min(a[2], b[2]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[1], b[1])
    if ox <= 0 or oy <= 0:
        return 0.0, 0.0, 0.0
    return ox, oy, ox * oy


def area(b) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def opaque(kind: str, a: dict) -> bool:
    if kind in ("image", "circle", "polygon"):
        return True
    if kind == "rect":
        fill = a.get("fill", "")
        op = f(a, "fill-opacity", 1.0)
        return fill.startswith("#") and op >= 0.55
    return False


def check(path: Path) -> list[str]:
    svg = path.read_text(encoding="utf-8")
    out: list[str] = []
    els = list(elements(svg))
    for z, (kind, b, a) in enumerate(els):
        if b[2] - b[0] <= 0 or b[3] - b[1] <= 0:
            continue
        full = b[2] - b[0] >= 0.92 * W and b[3] - b[1] >= 0.88 * H
        if full:
            continue
        if b[0] < -EDGE or b[1] < -EDGE or b[2] > W + EDGE or b[3] > H + EDGE:
            tag = {"image": "图片", "text": "文字", "rect": "色块", "line": "线"}.get(kind, kind)
            out.append(f"{path.name}: 越界 {tag} ({b[0]:.0f},{b[1]:.0f})-({b[2]:.0f},{b[3]:.0f})")

    texts = [(z, b, a) for z, (k, b, a) in enumerate(els) if k == "text"]
    solids = [(z, k, b, a) for z, (k, b, a) in enumerate(els) if k in ("image", "rect", "circle", "polygon")]
    images = [(z, b) for z, k, b, a in solids if k == "image"]
    thin = [(z, k, b) for z, (k, b, a) in enumerate(els) if k in ("line", "path")
            and (b[3] - b[1] <= 8 or b[2] - b[0] <= 8)]

    for tz, tb, ta in texts:
        # 文字被覆盖面积要累计判断，单看某一元素容易误报
        for sz, kind, sb, sa in solids:
            if sz < tz or not opaque(kind, sa):
                continue
            _ox, _oy, ov = overlap(sb, tb)
            if not ov:
                continue
            need = TEXT_COVER if kind == "image" else BLOCK_COVER
            if ov / max(area(tb), 1.0) > need:
                out.append(f"{path.name}: {'图' if kind == 'image' else '色块'}压字 "
                           f"{ov / max(area(tb), 1.0) * 100:.0f}% @ ({tb[0]:.0f},{tb[1]:.0f})")

    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            _ox, _oy, ov = overlap(images[i][1], images[j][1])
            if ov and ov / max(min(area(images[i][1]), area(images[j][1])), 1.0) > IMG_IMG:
                out.append(f"{path.name}: 图碰图 {ov / min(area(images[i][1]), area(images[j][1])) * 100:.0f}% "
                           f"@ ({images[i][1][0]:.0f},{images[i][1][1]:.0f})")

    for lz, kind, lb in thin:
        for tz, tb, ta in texts:
            ox, oy, _ = overlap(lb, tb)
            if ox <= 0 or oy <= 0:
                continue
            # 线在字的"实心区"里穿行（不含字上下各 15% 的呼吸空间）
            h = tb[3] - tb[1]
            inner = (tb[0] + 2, tb[1] + h * 0.28, tb[2] - 2, tb[3] - h * 0.10)
            iox, ioy, _ = overlap(lb, inner)
            if iox >= 6 and ioy > 0:
                out.append(f"{path.name}: 线穿字 @ ({tb[0]:.0f},{tb[1]:.0f})")
                break
    return out


def self_test() -> None:
    """证明这道门不是摆设：三个合成用例必须被抓到，一个干净用例必须放过。"""
    good = ('<svg><rect x="0" y="0" width="1280" height="720" fill="#FFF"/>'
            '<text x="100" y="200" font-size="30" fill="#111">干净的一行</text>'
            '<line x1="100" y1="240" x2="600" y2="240" stroke="#CCC" stroke-width="1"/></svg>')
    img_on_text = ('<svg><text x="100" y="200" font-size="30" fill="#111">被图片盖住</text>'
                   '<image x="60" y="150" width="600" height="120" href="a.jpg"/></svg>')
    block_on_text = ('<svg><text x="100" y="200" font-size="30" fill="#111">被色块盖住</text>'
                     '<rect x="80" y="160" width="500" height="80" fill="#20302C"/></svg>')
    line_through = ('<svg><text x="100" y="200" font-size="30" fill="#111">线从中间穿过</text>'
                    '<line x1="80" y1="192" x2="500" y2="192" stroke="#111" stroke-width="2"/></svg>')
    over = ('<svg><image x="1100" y="600" width="400" height="300" href="a.jpg"/></svg>')
    for name, svg, want in [("干净", good, False), ("图压字", img_on_text, True),
                            ("色块压字", block_on_text, True), ("线穿字", line_through, True),
                            ("越界", over, True)]:
        got = bool(check_text(svg, "t.svg"))
        print(f"  {'✓' if got == want else '✗'} {name}: {'报警' if got else '放过'}")
        if got != want:
            sys.exit(1)
    print("自测通过")


def check_text(svg: str, label: str) -> list[str]:
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as fp:
        fp.write(svg)
        tmp = Path(fp.name)
    try:
        return [s.replace("t.svg", label) for s in check(tmp)]
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    if "--self-test" in sys.argv:
        self_test()
        return 0
    roots = [Path(a) for a in sys.argv[1:]] or [Path(".")]
    bad: list[str] = []
    n = 0
    for r in roots:
        d = r / "svg_output" if (r / "svg_output").is_dir() else r
        for p in sorted(d.glob("*.svg")):
            n += 1
            bad += check(p)
    print(f"图形检查 {n} 页，问题 {len(bad)} 处")
    for b in bad[:80]:
        print("  " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
