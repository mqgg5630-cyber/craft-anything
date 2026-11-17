#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把课件 md 排版成 PPT Master 可转换的 SVG 页，并导出原生 PPTX。

两层分工：
    md        = 讲什么（要点 + 备注）
    plan.json = 长什么样（每页 layout / 配图 / kicker / 说明）
    --theme   = 用哪一套版式语言（下面四套，几何相同、字体与页面机件不同）

四套版式（v3）：
    plate      单墨版画（v2 基准）：暖纸 + 松墨 + 赤陶一点
    academic   A 学术冷版：冷灰纸、只有墨与一条细红线，标题字距放大、正文字号收紧
    classroom  B 课堂暖版：纸更暖、整体字号 +15%、手写感圈画与标注线
    textbook   C 教材版：条目编号「一、二、」、图注统一为「图 5-1」、页脚固定页码框

排版约定（四套都遵守，见 references/typography.md）：
    · 中文禁则：行首不出现 。，、；：？！」』；行尾不出现 （「『
    · 孤字控制：末行只剩一个字时，从上一行借一个字下来
    · 标题字距按 em 给（0.005–0.04），正文 0；行距 1.5–1.75，图注斜体衬线
    · 号数（01 / 15）用半宽，kicker 用大字距小字号——这一层负责「冷静感」

用法：
    python3 scripts/build_deck.py --md <课件.md> --plan <plan.json> --out <目录> \\
        --images <原图目录> --theme textbook --tag -C教材
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from duotone import make_pair  # noqa: E402
from polish_pptx import polish as polish_pptx
import native_chart  # noqa: E402

W, H = 1280, 720
M = 76                      # 版心边距
SERIF = "Songti SC, STSong, SimSun, serif"
SANS = "PingFang SC, Microsoft YaHei, Noto Sans SC, sans-serif"

THEMES = {
    "plate": dict(
        name="plate", label="单墨版画",
        paper="#F4EFE4", ink="#14302F", ink2="#4E625F", rule="#D5CCBA",
        rust="#B8452A", teal="#2C6157", dark="#0C1A1B",
        ochre="#A9761F", panel="#EDE6D6",
        scale=1.0, title_track=0.015, body_track=0.0,
        kicker="dot", caption="plate", head="none", foot="rule",
        cover_image="bleed", num_titles=False, body=20),
    "academic": dict(
        name="academic", label="A 学术冷版",
        paper="#F1F0EB", ink="#111E20", ink2="#4A585B", rule="#CFD2CE",
        rust="#9E2B1B", teal="#22464C", dark="#0B1416",
        ochre="#8A6A2A", panel="#E9E8E2",
        scale=0.97, title_track=0.045, body_track=0.012,
        kicker="rule", caption="pl", head="academic", foot="academic",
        cover_image="bleed", num_titles=False, body=19),
    "classroom": dict(
        name="classroom", label="B 课堂暖版",
        paper="#FAF3E3", ink="#1A2A26", ink2="#5B6B5F", rule="#E3D6BD",
        rust="#B94E2A", teal="#2D6A54", dark="#10201D",
        ochre="#B5852B", panel="#F2E6CB",
        scale=1.15, title_track=0.0, body_track=0.0,
        kicker="hand", caption="plain", head="none", foot="hand",
        cover_image="bleed", num_titles=False, body=22),
    "textbook": dict(
        name="textbook", label="C 教材版",
        paper="#F7F4EA", ink="#16282A", ink2="#4F625F", rule="#D8D2C2",
        rust="#A8432B", teal="#2A5F55", dark="#0E1B1C",
        ochre="#9C7A2E", panel="#F1ECDC",
        scale=1.03, title_track=0.02, body_track=0.004,
        kicker="textbook", caption="figure", head="textbook", foot="textbook",
        cover_image="figure", num_titles=True, body=20),
}

TH: dict = dict(THEMES["plate"])
SC = 1.0
PAPER = INK = INK2 = RULE = RUST = TEAL = DARK = ""
OCHRE = PANEL = ""

# plan.json 里写的是单墨版的色值；换主题时按语义映射，曲线/大数字才不会跟配色打架
CMAP = {"#14302F": "ink", "#1D2E29": "ink", "#111E20": "ink", "#16282A": "ink",
        "#B8452A": "rust", "#C0542F": "rust", "#9E2B1B": "rust", "#A8432B": "rust",
        "#2C6157": "teal", "#2F6B57": "teal", "#22464C": "teal", "#2A5F55": "teal",
        "#4E625F": "ink2", "#5A6B60": "ink2", "#D5CCBA": "rule", "#0C1A1B": "dark"}


def use_theme(name: str) -> None:
    global TH, SC, PAPER, INK, INK2, RULE, RUST, TEAL, DARK, OCHRE, PANEL
    TH = dict(THEMES[name])
    SC = TH["scale"]
    PAPER, INK, INK2 = TH["paper"], TH["ink"], TH["ink2"]
    RULE, RUST, TEAL, DARK = TH["rule"], TH["rust"], TH["teal"], TH["dark"]
    OCHRE, PANEL = TH["ochre"], TH["panel"]


def _lum(hexcolor: str) -> float:
    h = (hexcolor or "").lstrip("#")
    if len(h) != 6:
        return 0.5
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def on_dark(c: str, bg: str = "", need: float = 3.2) -> str:
    """深色页上的强调色：对比度不够就往纸色方向提亮。"""
    bg = bg or DARK
    def ratio(a, b):
        la, lb = _lum(a), _lum(b)
        hi, lo = max(la, lb), min(la, lb)
        return (hi + 0.05) / (lo + 0.05)
    out = c
    for k in (0.18, 0.32, 0.46, 0.6):
        if ratio(out, bg) >= need:
            return out
        out = "#%02X%02X%02X" % tuple(round(int(c[i:i + 2], 16) * (1 - k) + int(PAPER[i:i + 2], 16) * k)
                                      for i in (1, 3, 5))
    return out


def cmap(c: str) -> str:
    """把 plan 里写死的单墨色值映射到当前主题。"""
    return TH[CMAP[c.upper()]] if c and c.upper() in CMAP else (c or INK)


# ---------------------------------------------------------------- 基础图元
def S(v: float) -> float:
    """字号与竖向节奏统一乘主题缩放（课堂版 +15%）。"""
    return v * SC


def N(v: float) -> str:
    """坐标输出：整数不带小数点，其余保留两位——同时保证背景矩形能被识别为 1280 宽。"""
    return f"{round(float(v), 2):g}"


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def text_w(s: str, size: float, track: float = 0.0) -> float:
    raw = sum((0.52 if ord(c) < 128 else 1.0) for c in s) * size
    return (raw + len(s) * size * track) * SC


NO_START = "，。、；：？！）》」』”’,.;:?!)]%"
NO_END = "（《「『“‘(["


def wrap(s: str, size: float, max_w: float, track: float = 0.0) -> list[str]:
    """中文排版换行：带禁则（行首不排收尾标点、行尾不留起首标点）与孤字控制。"""
    lines: list[str] = []
    cur = ""
    for ch in s:
        if not cur:
            cur = ch
            continue
        if text_w(cur + ch, size, track) > max_w:
            if ch in NO_START:                 # 标点悬挂：收尾标点不另起一行
                cur += ch
                continue
            if cur[-1] in NO_END:              # 起首标点不留在行尾
                lines.append(cur[:-1])
                cur = cur[-1] + ch
                continue
            lines.append(cur)
            cur = ch.lstrip()
        else:
            cur += ch
    if cur:
        lines.append(cur)
    if len(lines) > 1 and len(lines[-1]) == 1 and len(lines[-2]) >= 2:
        lines[-1] = lines[-2][-1] + lines[-1]   # 孤字回借
        lines[-2] = lines[-2][:-1]
    return lines


def fit(s: str, size: float, max_w: float, max_h: float, max_lines: int = 99,
        floor: float = 13, track: float = 0.0) -> tuple[float, list[str]]:
    """在宽、高、行数三重约束下求最大字号（高度已含主题缩放）。"""
    while size > floor:
        ls = wrap(s, size, max_w, track)
        if len(ls) <= max_lines and len(ls) * size * 1.28 * SC <= max_h:
            return size, ls
        size -= 2
    return size, wrap(s, size, max_w, track)


def T(x, y, s, size=20, fill=None, font=SANS, weight=400, anchor="start",
      spacing=None, opacity=None, italic=False) -> str:
    fill = INK if fill is None else fill
    size = S(size)
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    sp = f' letter-spacing="{N(S(spacing))}"' if spacing else ""
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{N(x)}" y="{N(y)}" font-family="{font}" font-size="{N(size)}" '
            f'font-weight="{weight}" fill="{fill}"{a}{sp}{op}{it}>{esc(s)}</text>')


def R(x, y, w, h, fill, opacity=None, stroke=None, sw=1) -> str:
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{N(x)}" y="{N(y)}" width="{N(w)}" height="{N(h)}" fill="{fill}"{op}{st}/>'


def L(x1, y1, x2, y2, color=None, sw=1, opacity=None, dash=None) -> str:
    color = RULE if color is None else color
    op = f' stroke-opacity="{opacity}"' if opacity is not None else ""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{N(x1)}" y1="{N(y1)}" x2="{N(x2)}" y2="{N(y2)}" stroke="{color}" '
            f'stroke-width="{sw}"{op}{da}/>')


def IMG(name: str, x, y, w, h, variant="light", mode="slice") -> str:
    par = "xMidYMid slice" if mode == "slice" else "xMidYMid meet"
    return (f'<image href="../images/{name}-{variant}.jpg" x="{x:.1f}" y="{y:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="{par}"/>')


def hand_rule(x, y, w, color=None, sw=2.2) -> str:
    """手写感横线：略有起伏，不齐不抖。"""
    color = RUST if color is None else color
    q = w / 3
    d = (f"M{x:.1f},{y:.1f} C{x + q * .45:.1f},{y - 2.4:.1f} {x + q * .75:.1f},{y + 2.6:.1f} "
         f"{x + q:.1f},{y + .6:.1f} C{x + q * 1.5:.1f},{y - 1.8:.1f} {x + q * 1.8:.1f},{y + 2.4:.1f} "
         f"{x + 2 * q:.1f},{y + .2:.1f} C{x + 2 * q + 16:.1f},{y - 2.2:.1f} "
         f"{x + w - 22:.1f},{y + 2.2:.1f} {x + w:.1f},{y - .6:.1f}")
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round"/>')


def hand_circle(cx, cy, rx, ry, color=None, sw=2.2) -> str:
    """手圈重点：四段贝塞尔，半径微有出入。"""
    color = RUST if color is None else color
    k = 0.5523
    rx2, ry2 = rx * 1.02, ry * 0.97
    d = (f"M{cx - rx2:.1f},{cy:.1f} C{cx - rx2:.1f},{cy - ry2 * k:.1f} {cx - rx * k:.1f},{cy - ry2:.1f} "
         f"{cx:.1f},{cy - ry2:.1f} C{cx + rx2 * k:.1f},{cy - ry2 * 1.04:.1f} {cx + rx2:.1f},{cy - ry2 * k:.1f} "
         f"{cx + rx2:.1f},{cy:.1f} C{cx + rx2:.1f},{cy + ry * k:.1f} {cx + rx2 * k:.1f},{cy + ry:.1f} "
         f"{cx:.1f},{cy + ry:.1f} C{cx - rx * k:.1f},{cy + ry * 1.02:.1f} {cx - rx2:.1f},{cy + ry * k:.1f} "
         f"{cx - rx2:.1f},{cy:.1f}")
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round"/>')


def plate_img(e: list, name: str, x, y, w, h, page: int, cap: str = "",
              variant="light", mode="meet") -> None:
    """嵌版图：meet 不裁切（纸色与页面同色，看不出边界）；边框按主题给。"""
    e.append(IMG(name, x, y, w, h, variant, mode))
    ih = min(h, w * 720 / 1280) if mode == "meet" else h
    iy = y + (h - ih) / 2
    if TH["name"] in ("plate", "academic"):
        e.append(R(x, iy, w, ih, "none", stroke=INK2, sw=0.9))
    elif TH["name"] == "textbook":
        e.append(R(x, iy, w, ih, "none", stroke=INK, sw=1.1))
    else:
        e.append(hand_rule(x - 6, y + h + 4, w + 12))
    if cap:
        cy = y + h + 26 if TH["name"] != "classroom" else y + h + 34
        e.append(caption(cap, x, cy, page))


CN_NUM = "零一二三四五六七八九十"


def cn_num(n: int) -> str:
    if n <= 10:
        return CN_NUM[n]
    if n < 20:
        return "十" + CN_NUM[n - 10]
    return CN_NUM[n // 10] + "十" + (CN_NUM[n % 10] if n % 10 else "")


def caption(text: str, x, y, page: int, color=None, anchor="start") -> str:
    """图注三套写法：PLATE 01 / PL. 01 — / 图 5-1。"""
    c = color or INK2
    t = (text or "").strip()
    if not t:
        return ""
    m = re.match(r"^(?:PLATE|PL\.?)\s*(\d+)\s*[·\-—]\s*(.*)$", t)
    n = f"{int(m.group(1)):02d}" if m else f"{page:02d}"
    body = m.group(2) if m else t
    fmt = TH["caption"]
    if fmt == "plate":
        s = t or f"PLATE {n}"
    elif fmt == "pl":
        s = f"PL. {n} — {body}" if body else f"PL. {n}"
    elif fmt == "plain":
        s = f"{body}" if body else ""
    else:
        pre = TH.get("figures", "")
        s = f"图 {pre}-{int(n)}　{body}" if body else f"图 {pre}-{int(n)}"
    if not s:
        return ""
    size = 12.5 if fmt != "plain" else 13.5
    return T(x, y, s, size, c, SERIF, 400, anchor=anchor, spacing=1.0, opacity=0.9,
             italic=(fmt != "plain"))


def kicker(s: str, x=M, y=96, color=None, dark=False) -> str:
    if not s:
        return ""
    c = color or (PAPER if dark else RUST)
    st = TH["kicker"]
    if st == "dot":
        return "".join([R(x, y - 9, 7, 7, c), T(x + 16, y, s, 13, c, SANS, 500, spacing=3.2)])
    if st == "rule":
        return "".join([L(x, y - 4, x + 26, y - 4, c, 2),
                        T(x + 38, y, s, 11.5, INK if not dark else PAPER, SANS, 500, spacing=4.4)])
    if st == "hand":
        return "".join([hand_rule(x - 2, y + 8, 30, OCHRE, 2.6),
                        T(x + 40, y, s, 14.5, INK if not dark else PAPER, SANS, 600, spacing=1.6)])
    return "".join([R(x, y - 9, 6, 6, INK if not dark else PAPER),
                    T(x + 16, y, s, 12.5, INK if not dark else PAPER, SANS, 500, spacing=2.2)])


# ---------------------------------------------------------------- 页面机件
def furniture(i: int, total: int, meta: dict) -> list[str]:
    e: list[str] = []
    head = TH["head"]
    if head == "academic":
        e.append(L(M, 60, W - M, 60, RULE, 0.9))
        e.append(L(M, 60, M + 44, 60, RUST, 1.6))
        e.append(T(W - M, 46, meta["kicker"], 10.5, INK2, SANS, 400,
                   anchor="end", spacing=2.8, opacity=0.85))
    elif head == "textbook":
        e.append(R(0, 0, 12, H, INK, 0.06))
        e.append(T(M, 52, meta["kicker"], 12.5, INK, SERIF, 700, spacing=0.8))
        e.append(L(M, 64, W - M, 64, INK, 1.1))
        e.append(L(M, 67.5, W - M, 67.5, RULE, 0.8))

    foot = TH["foot"]
    if foot == "rule":
        e.append(L(M, 654, W - M, 654, RULE, 1))
        e.append(T(M, 682, meta["title"], 12, INK2, SANS, 400, spacing=1.6, opacity=0.8))
        e.append(T(W - M, 682, f"{i:02d} — {total:02d}", 12, INK2, SANS, 400,
                   anchor="end", spacing=1.2, opacity=0.8))
    elif foot == "academic":
        e.append(L(M, 654, W - M, 654, RULE, 0.8))
        e.append(T(M, 680, f"{i:02d}", 11, INK, SANS, 500, spacing=2.2))
        e.append(T(M + 30, 680, f"/ {total:02d}", 11, INK2, SANS, 400, spacing=2.2, opacity=0.8))
        e.append(T(W - M, 680, "单墨 · 教学图版", 10, INK2, SANS, 400,
                   anchor="end", spacing=3.4, opacity=0.6))
    elif foot == "hand":
        e.append(hand_rule(M, 650, 112, RULE, 1.6))
        e.append(T(M, 686, f"{i:02d}", 21, RUST, SERIF, 700))
        e.append(T(M + 34, 686, f"/{total}", 12, INK2, SANS, 400, opacity=0.8))
        e.append(T(W - M, 686, meta["kicker"], 11, INK2, SANS, 400,
                   anchor="end", spacing=1.4, opacity=0.75))
    else:  # textbook
        e.append(L(M, 658, W - M, 658, INK, 0.9))
        e.append(T(M, 686, meta["meta"], 10.5, INK2, SERIF, 400, spacing=0.8, opacity=0.85))
        e.append(R(W - M - 56, 666, 56, 28, "none", stroke=INK, sw=0.9))
        e.append(T(W - M - 28, 687, f"{i:02d}", 15, INK, SERIF, 700, anchor="middle"))
    return e


# ---------------------------------------------------------------- 版式
def lay_cover(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    t = p.get("title") or meta["title"]
    iw = 500 if TH["name"] in ("academic", "textbook") else 540
    ix = W - iw
    if TH["cover_image"] == "bleed":
        e.append(IMG(p["image"], ix, 0, iw, H, "light", "slice"))
        e.append(R(ix, 0, iw, H, PAPER, 0.04))
        e.append(R(ix - 1, 0, 1, H, RULE))
    else:
        ih = (iw - 56) * 720 / 1280
        e.append(IMG(p["image"], ix + 28, 150, iw - 56, ih, "light", "meet"))
        e.append(R(ix + 28, 150, iw - 56, ih, "none", stroke=INK, sw=1.1))
        e.append(caption(p.get("caption", ""), ix + 28 + (iw - 56) / 2, 150 + ih + 26,
                         ctx["i"], anchor="middle"))

    if TH["name"] == "textbook":
        e.append(R(0, 0, 12, H, INK, 0.06))
        e.append(T(M, 84, meta["kicker"], 13, INK, SERIF, 700, spacing=1.2))
        e.append(L(M, 98, W - M, 98, INK, 1.1))
        e.append(L(M, 101.5, W - M, 101.5, RULE, 0.8))
        kx, ky = M, 156
    else:
        e.append(kicker(p.get("kicker") or meta["kicker"], M, 150))
        kx, ky = M, 150

    size, lines = fit(t, 56, 560, 240, 3, track=TH["title_track"])
    y = (300 if TH["name"] != "academic" else 310) - (len(lines) - 1) * size * 0.55 * SC
    for ln in lines:
        e.append(T(M, y, ln, size, INK, SERIF, 700, spacing=size * TH["title_track"]))
        y += size * 1.16 * SC
    if TH["name"] == "academic":
        e.append(L(M, y + 6, M + 128, y + 6, RUST, 1.2))
    elif TH["name"] == "classroom":
        e.append(hand_rule(M - 4, y + 8, 118, RUST, 3.2))
    elif TH["name"] == "textbook":
        e.append(L(M, y + 8, W - M, y + 8, RULE, 0.9))
    else:
        e.append(L(M, y + 8, M + 96, y + 8, RUST, 3))

    if p.get("subtitle"):
        sy = y + 56
        for k, ln in enumerate(wrap(p["subtitle"], 20, 520, TH["body_track"])):
            e.append(T(M, sy + k * 32 * SC, ln, 20, INK2, SANS, 400, spacing=TH["body_track"] * 20))
    if TH["name"] == "textbook":
        e.append(T(M, 620, "人教版（2019）· 高中生物学", 11.5, INK2, SERIF, 400, spacing=1.2))
    else:
        e.append(T(M, 640, meta["meta"], 12.5, INK2, SANS, 400, spacing=1.4, opacity=0.85))
    return e


def lay_plate_full(p, meta, ctx):
    e = [R(0, 0, W, H, DARK), IMG(p["image"], 0, 0, W, H, "ink", "slice")]
    e.append(R(0, 250, W, H - 250, DARK, 0.6))
    e.append(kicker(p.get("kicker", ""), M, 412, PAPER, dark=True))
    size, lines = fit(p.get("title") or "", 50, 960, 150, 2, track=TH["title_track"])
    y = 500
    for ln in lines:
        e.append(T(M, y, ln, size, PAPER, SERIF, 700, spacing=size * TH["title_track"]))
        y += size * 1.16 * SC
    if TH["name"] == "classroom":
        e.append(hand_rule(M - 4, y + 4, 150, PAPER, 2.6))
    elif TH["name"] == "textbook":
        e.append(L(M, y + 6, M + 260, y + 6, PAPER, 0.8))
    if p.get("caption"):
        e.append(caption(p["caption"], M, 646, ctx["i"], color=PAPER))
    return e


def lay_plate_side(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    e.append(kicker(p.get("kicker") or meta["kicker"]))
    tw = 548
    size, tl = fit(p["title"], 38, tw, 190, 3, track=TH["title_track"])
    y = 190
    for ln in tl:
        e.append(T(M, y, ln, size, INK, SERIF, 700, spacing=size * TH["title_track"]))
        y += size * 1.12 * SC
    y += 30 * SC
    if TH["name"] == "classroom":
        e.append(hand_rule(M - 4, y - 32, 96, RUST, 2.4))   # 抬高：压到条目首行会切到字顶
    for i, b in enumerate(p["bullets"], 1):
        e.append(T(M, y, f"{i:02d}", 15, RUST, SANS, 500, spacing=1))
        bs, bl = fit(b, TH["body"] - 1, tw - 54, 200, 3)
        yy = y
        for ln in bl:
            e.append(T(M + 46, yy, ln, bs, INK, SANS, 400))
            yy += bs * 1.5 * SC
        y = yy + 22 * SC
        if i < len(p["bullets"]):
            e.append(L(M + 46, y - 16 * SC, M + tw, y - 16 * SC, RULE, 0.9))
    plate_img(e, p["image"], 700, 150, 504, 396, ctx["i"], p.get("caption", ""))
    return e


def lay_hero(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    e.append(kicker(p.get("kicker") or meta["kicker"]))
    size, lines = fit(p.get("title") or "", 30, 900, 90, 2, track=TH["body_track"])
    y = 178
    for ln in lines:
        e.append(T(M, y, ln, size, INK2, SANS, 400, spacing=TH["body_track"] * 30))
        y += size * 1.3 * SC
    big = p.get("big") or []
    x = M
    base = 470
    for it in big:
        s = it["text"]
        fs = it.get("size", 108)
        e.append(T(x, base, s, fs, cmap(it.get("color", INK)), SERIF, 700, spacing=fs * 0.01))
        x += text_w(s, fs, 0.01) + it.get("gap", 40)
    trail = 820 if p.get("image") else W - M
    e.append(L(M, base + 46 * SC, trail, base + 46 * SC, RULE, 1.2))
    if p.get("note"):
        for k, ln in enumerate(wrap(p["note"], 22, 700 if p.get("image") else 980, TH["body_track"])):
            e.append(T(M, base + 100 * SC + k * 34 * SC, ln, 22, INK, SANS, 400,
                       spacing=TH["body_track"] * 22))
    if p.get("image"):
        plate_img(e, p["image"], 900, 300, 304, 240, ctx["i"], p.get("caption", ""))
    return e


def lay_diagram(p, meta, ctx):
    """原生矢量能量图：两端谷、一个垭口、一条隧道。/ 不用风景照当隐喻。"""
    e = [R(0, 0, W, H, PAPER)]
    e.append(kicker(p.get("kicker") or meta["kicker"]))
    size, tl = fit(p.get("title") or "", 34, 1040, 60, 1, track=TH["title_track"])
    e.append(T(M, 170, tl[0], size, INK, SERIF, 700, spacing=size * TH["title_track"]))

    x0, x1 = 190, 1110
    yb, yt = 542, 250
    # 图版底色：像一张贴在纸上的挂图，而不是浮在空白里
    e.append(R(x0 - 58, yt - 46, (x1 + 44) - (x0 - 58), (yb + 60) - (yt - 46), PANEL))
    # 淡网格：教材图版的手感
    for k in range(1, 4):
        gy = yb - (yb - yt) * k / 4
        e.append(L(x0 - 20, gy, x1 + 16, gy, RULE, 0.6, 0.7))
    e.append(L(x0 - 30, yb, x1 + 10, yb, INK, 1.4))
    e.append(L(x0 - 30, yb, x0 - 30, yt - 10, INK, 1.4))
    e.append(T(x1 + 12, yb + 30, p.get("xlabel", "反应进程"), 14, INK2, SANS, 400, anchor="end"))
    e.append(T(x0 - 40, yt - 26, p.get("ylabel", "能量"), 14, INK2, SANS, 400, anchor="end"))

    peak = p.get("peak", 0.9)
    py = yb - (yb - yt) * peak
    hill = (f"M{x0},{yb} C{x0 + 90},{yb} {x0 + 150},{py} {x0 + 300},{py} "
            f"C{x0 + 430},{py} {x0 + 470},{yb} {x0 + 560},{yb} "
            f"C{x0 + 640},{yb} {x0 + 700},{yb - 30} {x0 + 760},{yb - 30} "
            f"L{x1},{yb - 30}")
    e.append(f'<path d="{hill}" fill="none" stroke="{INK}" stroke-width="3.2" stroke-linecap="round"/>')

    ax = x0 + 170
    e.append(L(ax, yb, ax, py, RUST, 1.4, dash="5 5"))
    e.append(f'<path d="M{ax - 5},{py + 12} L{ax},{py} L{ax + 5},{py + 12}" fill="none" stroke="{RUST}" stroke-width="1.4"/>')
    e.append(f'<path d="M{ax - 5},{yb - 12} L{ax},{yb} L{ax + 5},{yb - 12}" fill="none" stroke="{RUST}" stroke-width="1.4"/>')
    e.append(T(ax + 14, (yb + py) / 2, p.get("ann", "活化能"), 17, RUST, SANS, 500))

    if p.get("catalyst", True):
        cpy = py + 78
        e.append(f'<path d="M{x0 + 110},{yb - 40} C{x0 + 170},{cpy} {x0 + 250},{cpy} {x0 + 300},{cpy} '
                 f'C{x0 + 350},{cpy} {x0 + 430},{yb - 40} {x0 + 470},{yb - 40}" fill="none" '
                 f'stroke="{TEAL}" stroke-width="1.6" stroke-dasharray="7 6" stroke-linecap="round"/>')
        e.append(T(x0 + 320, cpy - 20, p.get("catalyst_label", "无机催化剂：降一点"), 15, TEAL, SANS, 400))
    if p.get("tunnel", True):
        ty = yb - 96
        e.append(L(x0 + 60, ty, x0 + 720, ty, RUST, 2.6, 0.95))
        e.append(T(x0 + 60, ty - 16, p.get("tunnel_label", "酶：打一条隧道"), 15, RUST, SANS, 500))
    for cap, cx in ((p.get("left", "反应物"), x0 + 62), (p.get("right", "产物"), x1 - 90)):
        e.append(T(cx, yb + 34, cap, 14, INK2, SANS, 400, spacing=1.2))
    return e


def lay_chart(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    e.append(kicker(p.get("kicker") or meta["kicker"]))
    size, tl = fit(p["title"], 32, 620, 120, 2, track=TH["title_track"])
    y = 174
    for ln in tl:
        e.append(T(M, y, ln, size, INK, SERIF, 700, spacing=size * TH["title_track"]))
        y += size * 1.15 * SC
    X0, Y0, X1, Y1 = 190, 560, 740, 260
    e.append(R(X0 - 52, Y1 - 44, (X1 + 46) - (X0 - 52), (Y0 + 36) - (Y1 - 44), PANEL))
    for k in range(1, 5):
        gy = Y0 - (Y0 - Y1) * k / 5
        e.append(L(X0, gy, X1 + 16, gy, RULE, 0.6, 0.7))
    e.append(L(X0, Y1 - 40, X0, Y0, INK, 1.2))
    e.append(L(X0, Y0, X1 + 20, Y0, INK, 1.2))
    e.append(T(X0 - 14, Y1 - 46, p.get("ylabel", ""), 14, INK2, SANS, 400, anchor="end"))
    e.append(T(X1 + 20, Y0 + 30, p.get("xlabel", ""), 14, INK2, SANS, 400, anchor="end"))

    def curve(peak, baseline=0.12, cutoff=None):
        """返回 [(t, v)]：t/v 都是 0–1 的归一化值。SVG 用它画线，原生图表用同一份数据。"""
        pts = []
        for i in range(81):
            t = i / 80
            if cutoff is not None and t > cutoff:
                v = 0.03
            else:
                u = min(t / 0.55, 1.0)
                v = baseline + (peak - baseline) * (u ** 1.8)
                if t > 0.55:
                    v = baseline + (peak - baseline) * (1 - (t - 0.55) * 0.12)
            pts.append((round(t, 4), round(v, 4)))
        return pts

    def path_for(peak, baseline=0.12, cutoff=None):
        pts = curve(peak, baseline, cutoff)
        xy = [(X0 + 10 + t * (X1 - X0 - 10), Y0 - 16 - (v - 0.03) * (Y0 - Y1 - 16)) for t, v in pts]
        return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in xy)

    for s in p["series"]:
        dash = ' stroke-dasharray="9 7"' if s.get("dash") else ""
        e.append(f'<path d="{path_for(s["peak"], s.get("baseline", 0.12), s.get("cutoff"))}" '
                 f'fill="none" stroke="{cmap(s["color"])}" stroke-width="2.6"{dash} stroke-linecap="round"/>')

    # 同一份数据交给原生图表（PowerPoint 里右键「编辑数据」就能改）
    ctx.setdefault("charts", []).append({
        "slide": ctx["i"],
        "region": [100, 196, 1110, 408],
        "xlabel": p.get("xlabel", ""), "ylabel": p.get("ylabel", ""),
        "ink": cmap(INK).lstrip("#"), "ink2": cmap(INK2).lstrip("#"),
        "rule": cmap(RULE).lstrip("#"), "panel": cmap(PANEL).lstrip("#"),
        "series": [{"name": s["name"], "color": cmap(s["color"]).lstrip("#"),
                    "dash": bool(s.get("dash")),
                    "pts": curve(s["peak"], s.get("baseline", 0.12), s.get("cutoff"))}
                   for s in p["series"]],
    })
    ly = 300
    for s in p["series"]:
        dash = ' stroke-dasharray="9 7"' if s.get("dash") else ""
        e.append(f'<line x1="800" y1="{ly}" x2="852" y2="{ly}" stroke="{cmap(s["color"])}" stroke-width="2.6"{dash}/>')
        e.append(T(866, ly + 6, s["name"], 18, INK, SANS, 400))
        ly += 40 * SC
    if p.get("note"):
        e.append(L(800, ly + 4, 1204, ly + 4, RULE, 1))
        yy = ly + 38
        for raw in p["note"].split("\n"):
            for ln in wrap(raw, 17, 396, TH["body_track"]):
                e.append(T(800, yy, ln, 17, INK2, SANS, 400))
                yy += 27 * SC
    return e


def lay_table(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    e.append(kicker(p.get("kicker") or meta["kicker"]))
    size, tl = fit(p["title"], 33, 1020, 80, 2, track=TH["title_track"])
    y = 172
    for ln in tl:
        e.append(T(M, y, ln, size, INK, SERIF, 700, spacing=size * TH["title_track"]))
        y += size * 1.12 * SC
    rows = p["table"]
    ncol = max(len(r) for r in rows)
    cw = (W - 2 * M) / ncol
    y += 30 * SC
    e.append(L(M, y, W - M, y, INK, 2))
    y += 36 * SC
    e.append(R(M, y - 26 * SC, W - 2 * M, 34 * SC, PANEL))
    body_size = TH["body"] * (1.0 if ncol <= 4 else 0.88)
    for ri, row in enumerate(rows):
        for ci in range(ncol):
            val = row[ci] if ci < len(row) else ""
            if ri == 0:
                e.append(T(M + ci * cw + 10, y, val, 13, RUST, SANS, 500, spacing=2.4))
            else:
                e.append(T(M + ci * cw + 10, y, val, body_size, INK,
                           SERIF if ci == 0 else SANS, 700 if ci == 0 else 400))
        y += 54 * SC
        e.append(L(M, y - 22 * SC, W - M, y - 22 * SC, RULE, 0.9))
    if p.get("caption"):
        e.append(caption(p["caption"], M, y + 4, ctx["i"]))
    return e


def lay_compare(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    e.append(kicker(p.get("kicker") or meta["kicker"]))
    size, tl = fit(p["title"], 33, 1020, 80, 2, track=TH["title_track"])
    y = 170
    for ln in tl:
        e.append(T(M, y, ln, size, INK, SERIF, 700, spacing=size * TH["title_track"]))
        y += size * 1.12 * SC
    y += 44 * SC
    cols = p["cols"]
    cw = (W - 2 * M) / len(cols)
    for ci, c in enumerate(cols):
        x = M + ci * cw + (0 if ci == 0 else 40)
        e.append(T(x, y, c["label"], 13, RUST if ci == 0 else TEAL, SANS, 500, spacing=2.4))
        e.append(T(x, y + 56 * SC, c["head"], 32, INK, SERIF, 700))
        yy = y + 106 * SC
        for b in c.get("bullets", []):
            for ln in wrap(b, 18, cw - 74, TH["body_track"])[:2]:
                e.append(T(x, yy, ln, 18, INK2, SANS, 400))
                yy += 28 * SC
            yy += 8 * SC
    if len(cols) == 2:                     # 细分隔：不贯穿整页，只在中段
        e.append(L(W / 2, y + 40 * SC, W / 2, y + 232 * SC, RULE, 0.9, 0.75))
    return e


def lay_checklist(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    e.append(kicker(p.get("kicker") or meta["kicker"]))
    size, tl = fit(p["title"], 33, 1020, 80, 2, track=TH["title_track"])
    y = 170
    for ln in tl:
        e.append(T(M, y, ln, size, INK, SERIF, 700, spacing=size * TH["title_track"]))
        y += size * 1.12 * SC
    y += 46 * SC
    for item in p["pairs"]:
        e.append(T(M, y, "✗", 24, RUST, SANS, 700))
        top = y
        for ln in wrap(item["wrong"], 21, 420, TH["body_track"])[:2]:
            e.append(T(M + 44, y, ln, 21, INK2, SANS, 400))
            y += 30 * SC
        e.append(T(600, top, "→", 22, TEAL, SANS, 700))
        yy = top
        for ln in wrap(item["right"], 21, 520, TH["body_track"])[:2]:
            e.append(T(646, yy, ln, 21, INK, SANS, 500))
            yy += 30 * SC
        y = max(y, yy) + 24 * SC
        e.append(L(M, y - 16 * SC, W - M, y - 16 * SC, RULE, 0.9))
    return e


def lay_quote(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    has_img = bool(p.get("image"))
    if has_img:
        iw = 470
        e.append(IMG(p["image"], W - iw, 0, iw, H, "light", "slice"))
        e.append(R(W - iw, 0, iw, H, PAPER, 0.06))
        e.append(R(W - iw - 1, 0, 1, H, RULE))
    e.append(kicker(p.get("kicker") or meta["kicker"], M, 150))
    lines_in = p.get("lines") or [p.get("title") or ""]
    y = 322
    for ln in lines_in:
        size, ls = fit(ln, 46, 560 if has_img else 980, 130, 2, track=TH["title_track"])
        for s in ls:
            e.append(T(M, y, s, size, INK, SERIF, 700, spacing=size * TH["title_track"]))
            y += size * 1.2 * SC
        y += 14 * SC
    if TH["name"] == "classroom":
        e.append(hand_rule(M - 4, y + 18, 104, RUST, 3))
    elif TH["name"] == "academic":
        e.append(L(M, y + 18, M + 132, y + 18, RUST, 1.2))
    else:
        e.append(L(M, y + 18, M + 88, y + 18, RUST, 3))
    if p.get("note"):
        for k, ln in enumerate(wrap(p["note"], 18, 500 if has_img else 880, TH["body_track"])):
            e.append(T(M, y + 70 * SC + k * 28 * SC, ln, 18, INK2, SANS, 400))
    return e


def lay_section(p, meta, ctx):
    e = [R(0, 0, W, H, DARK)]
    if p.get("image"):
        e.append(IMG(p["image"], 0, 0, W, H, "ink", "slice"))
        e.append(R(0, 0, W, H, DARK, 0.55))
    num = p.get("num", "")
    if TH["name"] == "textbook":
        e.append(T(M, 268, num, 108, PAPER, SERIF, 700, spacing=6))
        e.append(L(M, 300, M + 120, 300, PAPER, 2))
    else:
        e.append(T(M, 258, num, 118, on_dark(RUST), SERIF, 700))
    size, lines = fit(p["title"], 46, 900, 180, 2, track=TH["title_track"])
    y = 392
    for ln in lines:
        e.append(T(M, y, ln, size, PAPER, SERIF, 700, spacing=size * TH["title_track"]))
        y += size * 1.2 * SC
    e.append(L(M, y + 4, M + 96, y + 4, PAPER, 2.4))
    if p.get("subtitle"):
        e.append(T(M, y + 62, p["subtitle"], 19, PAPER, SANS, 400, opacity=0.82))
    return e


def lay_statement(p, meta, ctx):
    e = [R(0, 0, W, H, PAPER)]
    e.append(kicker(p.get("kicker") or meta["kicker"]))
    lines_in = p.get("lines") or [p.get("title") or ""]
    y = 300
    for ln in lines_in:
        size, ls = fit(ln, 48, 960, 140, 2, track=TH["title_track"])
        for s in ls:
            e.append(T(M, y, s, size, INK, SERIF, 700, spacing=size * TH["title_track"]))
            y += size * 1.2 * SC
        y += 12 * SC
    if TH["name"] == "classroom":
        e.append(hand_rule(M - 4, y + 12, 220, RULE, 2.2))
    else:
        e.append(L(M, y + 12, M + 300, y + 12, RULE, 2))
    if p.get("note"):
        for k, ln in enumerate(wrap(p["note"], 20, 880, TH["body_track"])):
            e.append(T(M, y + 64 * SC + k * 30 * SC, ln, 20, INK2, SANS, 400))
    if p.get("image"):
        plate_img(e, p["image"], 900, 420, 304, 200, ctx["i"], "")
    return e



TEXT_EL = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')


def merge_text_runs(svg: str) -> str:
    """把「同一段落的连续单行 <text>」合并成 一个 <text> + <tspan dy>。

    为什么要做：一行一个 <text>，在 PPTX 里就是一行一个文本框——改一个字要重排整页，
    而且换行是死坐标。合并成 tspan 段落之后，一段话是一个可编辑的文本段。
    （这也是 ppt-master 质量门唯一在提的那类 advisory 警告。）
    """
    items = [(m, dict(ATTR_RE.findall(m.group(1)))) for m in TEXT_EL.finditer(svg)]

    def key(a):
        return tuple(sorted((k, v) for k, v in a.items() if k not in ("x", "y")))

    SENT_END = ("。", "！", "？", "；")

    def plain(s: str) -> str:
        return re.sub(r"<[^>]+>", "", s).strip()

    groups: list[list[int]] = []
    cur: list[int] | None = None
    for idx, (m, a) in enumerate(items):
        # **句子边界不合并**：一句一个文本框，才能一句一次点击地讲。
        # （长句折行时前几行不以句号结尾，仍然并进同一段。）
        if cur and plain(items[cur[-1]][0].group(2)).endswith(SENT_END):
            cur = None
        if cur and "<tspan" not in m.group(2):
            pa = items[cur[-1]][1]
            same = (key(pa) == key(a)
                    and abs(float(pa.get("x", 0)) - float(a.get("x", 0))) < 0.6
                    and 0 < float(a.get("y", 0)) - float(pa.get("y", 0))
                    <= float(a.get("font-size", 20)) * 2.05)
            if same:
                cur.append(idx)
                continue
        cur = [idx]
        groups.append(cur)

    repl: dict[int, str] = {}
    for g in groups:
        if len(g) < 2:
            continue
        m0, a0 = items[g[0]]
        x = a0.get("x", "0")
        body = [m0.group(2)]
        prev = float(a0.get("y", 0))
        for k in g[1:]:
            m, a = items[k]
            y = float(a.get("y", 0))
            body.append(f'<tspan x="{x}" dy="{N(y - prev)}">{m.group(2)}</tspan>')
            prev = y
        repl[g[0]] = f"<text{m0.group(1)}>{''.join(body)}</text>"
        for k in g[1:]:
            repl[k] = ""

    out, last = [], 0
    for idx, (m, _a) in enumerate(items):
        out.append(svg[last:m.start()])
        out.append(repl.get(idx, m.group(0)))
        last = m.end()
    out.append(svg[last:])
    return "".join(out)


LAYOUTS = {
    "cover": lay_cover, "plate": lay_plate_full, "plate_side": lay_plate_side,
    "hero": lay_hero, "diagram": lay_diagram, "chart": lay_chart,
    "table": lay_table, "compare": lay_compare, "checklist": lay_checklist,
    "quote": lay_quote, "section": lay_section, "statement": lay_statement,
}
NO_FOLIO = {"cover", "plate", "section", "quote"}


# ---------------------------------------------------------------- 解析 md
def parse_md(path: Path):
    t = path.read_text(encoding="utf-8")
    meta = {"title": "", "subtitle": "", "kicker": "", "meta": ""}
    slides, cur = [], None
    for ln in t.splitlines():
        if ln.startswith("# ") and not meta["title"]:
            meta["title"] = ln[2:].strip()
            continue
        if ln.startswith(">") and not meta["subtitle"]:
            meta["subtitle"] = ln.lstrip("> ").strip()
            continue
        m = re.match(r"^##\s+(\d+)\s+(.*)$", ln)
        if m:
            if cur:
                slides.append(cur)
            cur = {"num": m.group(1), "title": m.group(2).strip(),
                   "bullets": [], "table": [], "note": ""}
            continue
        if cur is None:
            continue
        if ln.startswith("<!--"):
            n = re.search(r"note:\s*(.*?)\s*-->", ln)
            if n:
                cur["note"] = n.group(1)
            continue
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c or "---") for c in cells):
                continue
            cur["table"].append(cells)
            continue
        if ln.startswith("- "):
            cur["bullets"].append(ln[2:].strip())
            continue
        if ln.strip():
            cur["bullets"].append(ln.strip())
    if cur:
        slides.append(cur)
    return meta, slides


def choose_layout(s, spec):
    if spec.get("layout"):
        return spec["layout"]
    if s["table"]:
        return "table"
    if len(s["bullets"]) <= 2:
        return "statement"
    return "plate_side"


# ---------------------------------------------------------------- 构建
def prep_images(src: Path, dst: Path) -> int:
    """按当前主题把原图重新上色成 light/ink 两版（纸色与页面完全一致）。"""
    from PIL import Image
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(list(src.glob("*.jpg")) + list(src.glob("*.png"))):
        if f.name.startswith("_"):
            continue
        img = Image.open(f).convert("RGB")
        if img.width > 1400:
            img = img.resize((1400, round(img.height * 1400 / img.width)), Image.LANCZOS)
        light, dark = make_pair(img, TH["paper"], TH["ink"])
        light.save(dst / f"{f.stem}-light.jpg", quality=86, optimize=True)
        dark.save(dst / f"{f.stem}-ink.jpg", quality=86, optimize=True)
        n += 2
    return n


def build(md: Path, plan: Path, out: Path, images: Path, skill: Path, tag: str = "") -> Path:
    meta, slides = parse_md(md)
    p = json.loads(plan.read_text(encoding="utf-8")) if plan.exists() else {"pages": []}
    specs = p.get("pages", [])
    meta["kicker"] = p.get("kicker", meta["kicker"] or meta["title"])
    meta["meta"] = p.get("meta", "")
    TH["figures"] = str(p.get("figures", "")) or "1"

    svgdir = out / "svg_output"
    if svgdir.exists():
        shutil.rmtree(svgdir)
    svgdir.mkdir(parents=True)
    imgdir = out / "images"
    if imgdir.exists():
        shutil.rmtree(imgdir)
    n_img = prep_images(images, imgdir)

    total = len(slides)
    charts: list[dict] = []
    for i, s in enumerate(slides, start=1):
        spec = specs[i - 1] if i - 1 < len(specs) else {}
        page = dict(s)
        page.update({k: v for k, v in spec.items() if k != "layout"})
        if not page.get("table") and s["table"]:
            page["table"] = s["table"]
        lay = choose_layout(s, spec)
        title = page.get("title") or ""
        if TH["num_titles"] and title and i > 1:
            page["title"] = f"{cn_num(i - 1)}、{title}"
        ctx = {"i": i, "total": total}
        body = LAYOUTS[lay](page, meta, ctx)
        charts.extend(ctx.get("charts", []))
        if lay not in NO_FOLIO:
            body.append("".join(furniture(i, total, meta)))

        bg, rest = None, body
        if body and 'width="1280"' in body[0]:
            bg, rest = body[0], body[1:]
        if bg:
            bg = bg.replace("/>", ' id="bg" data-pptx-role="background"/>', 1)
        role = ("cover" if i == 1 else "section" if lay == "section"
                else "ending" if i == total else "content")
        parts = ([bg] if bg else []) + [
            f'<g id="content" data-pptx-bounds="0 0 {W} {H}">'] + rest + ["</g>"]
        svg = merge_text_runs('<svg xmlns="http://www.w3.org/2000/svg" '
               'xmlns:xlink="http://www.w3.org/1999/xlink" lang="zh-CN" '
               f'viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
               f'font-family="{SANS}" data-pptx-page-role="{role}">\n'
               + "\n".join(parts) + "\n</svg>\n")
        stem = re.sub(r"[^0-9A-Za-z一-龥]+", "", page["title"])[:12]
        (svgdir / f"{i:02d}-{stem}.svg").write_text(svg, encoding="utf-8")

    notes_dir = out / "notes"
    notes_dir.mkdir(exist_ok=True)
    blocks = [f"# {i:02d}_{s['title']}\n\n{(s.get('note') or '')}" for i, s in enumerate(slides, 1)]
    (notes_dir / "total.md").write_text("\n\n---\n\n".join(blocks) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(skill / "scripts/total_md_split.py"), str(out)],
                   check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run([sys.executable, str(skill / "scripts/compact_svg_styles.py"),
                    str(svgdir), "--inplace"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(skill / "scripts/svg_quality_checker.py"),
                    str(out), "--quick-generate", "--canonical-authoring",
                    "--stage", "final", "--json"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    pptx = out / (md.stem + tag + ".pptx")
    r = subprocess.run([sys.executable, str(skill / "scripts/svg_to_pptx.py"),
                        str(out), "--quick-generate", "--primary-language", "zh-CN",
                        "--with-notes", "-o", str(pptx)], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-1600:])
        print(r.stderr[-1600:], file=sys.stderr)
        sys.exit(r.returncode)
    for line in r.stdout.splitlines():
        if "POSTFLIGHT" in line or "[Done]" in line or "Slides:" in line:
            print(line.strip())
    n_font, n_alt = polish_pptx(pptx)      # 字体槽位（标题宋体 / 正文雅黑）+ 图片替代文字
    print(f"[polish] 字体槽位 {n_font} 处，图片替代文字 {n_alt} 条")
    if charts:                             # 画出来的曲线 → 原生图表（可编辑数据）
        spec = out / (pptx.stem + "-charts.json")
        spec.write_text(json.dumps(charts, ensure_ascii=False, indent=1), encoding="utf-8")
        n_del, n_add = native_chart.apply(pptx, charts)
        print(f"[chart] 原生图表 {n_add} 张（清掉 {n_del} 个画图元素）")
    else:
        (out / (pptx.stem + "-charts.json")).unlink(missing_ok=True)
    write_preview(out, meta, total, tag)
    print(f"[img] {n_img} 张（主题 {TH['name']}）")
    return pptx


PREVIEW = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>{title} · {label}</title>
<style>
:root{{--paper:{paper};--ink:{ink};--rust:{rust}}}
body{{margin:0;background:#0d1415;color:#e9e3d7;font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif}}
header{{padding:28px 40px 4px}} h1{{font-size:20px;margin:0 0 6px;font-weight:600;letter-spacing:.5px}}
p.meta{{margin:0;color:#8b9a94;font-size:12.5px;letter-spacing:1px}}
.chip{{display:inline-block;margin-left:10px;padding:2px 9px;border:1px solid #38484a;border-radius:99px;font-size:11px;letter-spacing:1.5px;color:{rust}}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(470px,1fr));gap:20px;padding:24px 40px 64px}}
figure{{margin:0;background:var(--paper);border-radius:2px;overflow:hidden}}
img{{width:100%;display:block}}
figcaption{{font-size:11.5px;color:{ink};opacity:.6;padding:7px 10px;letter-spacing:.6px;background:var(--paper)}}
</style></head><body>
<header><h1>{title}<span class="chip">{label}</span></h1>
<p class="meta">{meta} · 共 {total} 页 · 字体 {typo}</p></header>
<div class="grid">
{items}
</div></body></html>"""


def write_preview(out: Path, meta: dict, total: int, tag: str = "") -> None:
    files = sorted((out / "svg_output").glob("*.svg"))
    items = "\n".join(
        f'<figure><img src="svg_output/{f.name}" alt="{esc(f.stem)}">'
        f'<figcaption>{esc(f.stem)}</figcaption></figure>' for f in files)
    typo = f"{TH['body']}px 正文 / 缩放 {int(SC * 100)}%"
    (out / "preview.html").write_text(
        PREVIEW.format(title=esc(meta["title"]), meta=esc(meta["meta"]), total=total,
                       items=items, label=TH["label"], paper=TH["paper"], ink=TH["ink"],
                       rust=TH["rust"], typo=typo), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--plan", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--theme", default="plate", choices=list(THEMES))
    ap.add_argument("--tag", default="")
    ap.add_argument("--skill", default="/home/user/ppt-master/skills/ppt-master")
    a = ap.parse_args()
    use_theme(a.theme)
    pptx = build(Path(a.md), Path(a.plan) if a.plan else Path(a.md).with_suffix(".plan.json"),
                 Path(a.out), Path(a.images), Path(a.skill), a.tag)
    print(f"[ok] {pptx}")


if __name__ == "__main__":
    main()
