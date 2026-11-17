#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""03-课件.md -> 03-课件.pptx + preview.html

用法:
    python3 scripts/build_pptx.py "chapters/.../03-课件.md" --outdir out
    python3 scripts/build_pptx.py deck.md --outdir out --title "第1章 走近细胞" --no-warn

Markdown 约定（见 prompts/03-教学课件.md）:
    # 课件标题
    > 副标题
    ## 01 页标题（写成结论句）
    - 要点
    | 列 | 列 |          <- 表格页
    <!-- note: 备注，进 pptx 备注页 -->
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
except ImportError:  # pragma: no cover
    sys.exit("缺少 python-pptx：python3 -m pip install python-pptx")

ACCENT = RGBColor(0x1B, 0x6B, 0x4C)
INK = RGBColor(0x22, 0x22, 0x22)
GREY = RGBColor(0x77, 0x77, 0x77)
LIGHT = RGBColor(0xF2, 0xF5, 0xF3)
FONT = "微软雅黑"

MAX_BULLETS = 5
MAX_BODY_CHARS = 45


# ---------------------------------------------------------------- parsing
def parse_md(path: Path) -> dict:
    deck = {"title": path.stem, "subtitle": "", "slides": []}
    cur = None
    in_note = False
    note_buf: list[str] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()

        if in_note:
            if "-->" in line:
                in_note = False
                cur["note"] = "\n".join(note_buf).strip() if cur else ""
                note_buf = []
            else:
                note_buf.append(line)
            continue

        m = re.match(r"^<!--\s*note:\s*(.*)$", line)
        if m:
            rest = m.group(1)
            if "-->" in rest:  # 单行备注
                cur["note"] = rest.split("-->")[0].strip() if cur else ""
                continue
            in_note = True
            note_buf = [rest]
            continue

        if line.startswith("# ") and not deck.get("_h1"):
            deck["_h1"] = True
            deck["title"] = line[2:].strip()
            continue
        if line.startswith("> ") and not deck["subtitle"]:
            deck["subtitle"] = line[2:].strip()
            continue  # 只取第一行
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            cur = {"title": re.sub(r"^\d+[\s.、]*", "", m.group(1)).strip(),
                   "bullets": [], "table": [], "note": ""}
            deck["slides"].append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") and c for c in cells):
                continue
            cur["table"].append(cells)
            continue
        m = re.match(r"^[-*]\s+(.*)$", line)
        if m:
            cur["bullets"].append(m.group(1).strip())
    return deck


# ---------------------------------------------------------------- pptx
def _set_font(run, size, bold=False, color=INK):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = FONT
    # 中文字体需要写入 a:ea
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ea")
    if ea is None:
        from lxml import etree
        ea = etree.SubElement(rPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}ea")
    ea.set("typeface", FONT)


def _textbox(slide, l, t, w, h):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def _accent_bar(slide, l=0.9, t=1.05, w=0.9):
    shp = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(0.06))
    shp.fill.solid()
    shp.fill.fore_color.rgb = ACCENT
    shp.line.fill.background()
    return shp


def _footer(slide, idx, total, title):
    tf = _textbox(slide, 0.9, 6.85, 11.5, 0.35)
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = f"{title}    {idx:02d}/{total:02d}"
    _set_font(r, 10, color=GREY)


def build_pptx(deck: dict, out: Path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    total = len(deck["slides"])

    # 封面
    s = prs.slides.add_slide(blank)
    tf = _textbox(s, 0.9, 2.2, 11.5, 1.8)
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = deck["h1"] if deck.get("h1") else deck["title"]
    _set_font(r, 40, bold=True)
    if deck["subtitle"]:
        tf2 = _textbox(s, 0.9, 4.15, 11.5, 0.8)
        r2 = tf2.paragraphs[0].add_run(); r2.text = deck["subtitle"]
        _set_font(r2, 18, color=GREY)
    bar = s.shapes.add_shape(1, Inches(0.9), Inches(1.85), Inches(1.2), Inches(0.08))
    bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background()

    for i, sl in enumerate(deck["slides"], start=1):
        s = prs.slides.add_slide(blank)
        # 标题
        tf = _textbox(s, 0.9, 0.55, 11.5, 1.25)
        p = tf.paragraphs[0]
        r = p.add_run(); r.text = sl["title"]
        _set_font(r, 26, bold=True)
        _accent_bar(s)

        y = 1.55
        if sl["bullets"]:
            tf = _textbox(s, 0.9, y, 11.5, 4.9)
            tf.word_wrap = True
            for j, b in enumerate(sl["bullets"]):
                para = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                para.space_after = Pt(14)
                para.line_spacing = 1.25
                r = para.add_run(); r.text = "· " + b
                _set_font(r, 20)
            y += 0.35 * len(sl["bullets"]) + 0.2

        if sl["table"]:
            rows, cols = len(sl["table"]), max(len(r) for r in sl["table"])
            top = Inches(y + 0.1)
            height = Inches(min(4.2, 0.55 * rows + 0.2))
            tbl_shape = s.shapes.add_table(rows, cols, Inches(0.9), top,
                                           Inches(11.5), height)
            tbl = tbl_shape.table
            for ri, row in enumerate(sl["table"]):
                for ci in range(cols):
                    cell = tbl.cell(ri, ci)
                    cell.text = row[ci] if ci < len(row) else ""
                    cell.margin_left = Inches(0.12)
                    cell.margin_top = Inches(0.06)
                    cell.margin_bottom = Inches(0.06)
                    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                    if ri == 0:
                        cell.fill.solid(); cell.fill.fore_color.rgb = LIGHT
                    for para in cell.text_frame.paragraphs:
                        para.alignment = PP_ALIGN.LEFT
                        for run in para.runs:
                            _set_font(run, 15, bold=(ri == 0))

        if sl["note"]:
            s.notes_slide.notes_text_frame.text = sl["note"]
        _footer(s, i, total, deck["title"])

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)


# ---------------------------------------------------------------- html
HTML_SHELL = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--accent:#1b6b4c;--ink:#222;--grey:#777;}}
*{{box-sizing:border-box}}
body{{margin:0;background:#111;font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;color:var(--ink)}}
.slide{{display:none;width:min(96vw,1280px);aspect-ratio:16/9;margin:2vh auto;background:#fff;
  padding:5.5% 6%;position:relative;border-radius:6px;overflow:hidden}}
.slide.on{{display:block}}
h1{{font-size:clamp(22px,3.4vw,46px);line-height:1.25;margin:0 0 1.2em}}
h2{{font-size:clamp(18px,2.4vw,31px);line-height:1.3;margin:0 0 .5em}}
h2::after{{content:"";display:block;width:70px;height:5px;background:var(--accent);margin-top:14px}}
ul{{list-style:none;padding:0;margin:1.6em 0 0}}
li{{font-size:clamp(13px,1.55vw,21px);line-height:1.6;margin:.75em 0;padding-left:1.1em;position:relative}}
li::before{{content:"·";position:absolute;left:.1em;color:var(--accent);font-weight:700}}
table{{border-collapse:collapse;margin-top:1.2em;width:100%;font-size:clamp(12px,1.35vw,18px)}}
th,td{{text-align:left;padding:.55em .7em;border-bottom:1px solid #e3e6e4}}
th{{background:#f2f5f3;font-weight:600}}
.sub{{color:var(--grey);font-size:clamp(13px,1.6vw,21px)}}
.bar{{width:100px;height:7px;background:var(--accent);margin:0 0 2.2em}}
.foot{{position:absolute;left:6%;bottom:4%;color:#aaa;font-size:12px}}
.note{{display:none}}
.hint{{position:fixed;right:12px;bottom:10px;color:#666;font-size:12px}}
@media print{{body{{background:#fff}}.slide{{display:block!important;page-break-after:always;margin:0;width:100%;border-radius:0}}}}
</style></head><body>
{slides}
<div class="hint">← → 翻页 · S 显示备注 · P 打印</div>
<script>
const S=[...document.querySelectorAll('.slide')];let i=0;
function show(n){{i=Math.max(0,Math.min(S.length-1,n));S.forEach((s,k)=>s.classList.toggle('on',k===i));}}
document.addEventListener('keydown',e=>{{
  if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){{show(i+1);e.preventDefault();}}
  if(e.key==='ArrowLeft'||e.key==='PageUp'){{show(i-1);e.preventDefault();}}
  if(e.key==='Home')show(0); if(e.key==='End')show(S.length-1);
  if(e.key==='s'||e.key==='S'){{const n=S[i].querySelector('.note');if(n)alert(n.textContent);}}
}});
show(0);
</script></body></html>
"""


def build_html(deck: dict, out: Path):
    parts = []
    cover = (f'<div class="slide on"><h1>{html.escape(deck["h1"] if deck.get("h1") else deck["title"])}</h1>'
             f'<div class="bar"></div><div class="sub">{html.escape(deck["subtitle"])}</div></div>')
    parts.append(cover)
    total = len(deck["slides"])
    for i, sl in enumerate(deck["slides"], start=1):
        body = [f"<h2>{html.escape(sl['title'])}</h2>"]
        if sl["bullets"]:
            body.append("<ul>" + "".join(f"<li>{html.escape(b)}</li>" for b in sl["bullets"]) + "</ul>")
        if sl["table"]:
            rows = sl["table"]
            head = "".join(f"<th>{html.escape(c)}</th>" for c in rows[0])
            trs = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
            body.append(f"<table><thead><tr>{head}</tr></thead><tbody>{trs}</tbody></table>")
        if sl["note"]:
            body.append(f'<div class="note">{html.escape(sl["note"])}</div>')
        body.append(f'<div class="foot">{html.escape(deck["title"])} · {i:02d}/{total:02d}</div>')
        parts.append('<div class="slide">' + "".join(body) + "</div>")
    out.write_text(HTML_SHELL.format(title=html.escape(deck["title"]), slides="\n".join(parts)),
                   encoding="utf-8")


# ---------------------------------------------------------------- gate
def gate(deck: dict, per_slide: int, lessons: float) -> int:
    warns = 0
    n = len(deck["slides"])
    target = round(per_slide * lessons)
    lo, hi = target - 4, target + 4
    print(f"[gate] 页数 {n}（目标 {lessons:g} 课时 × {per_slide} = {target}，允许 {lo}–{hi}）")
    if not (lo <= n <= hi):
        print(f"  WARN 页数 {n} 超出 {lo}–{hi}：课时数 × 8–10 为目标"); warns += 1
    if not deck["slides"] or not deck["slides"][0]["title"]:
        print("  WARN 首页无标题"); warns += 1
    notes = sum(1 for s in deck["slides"] if s["note"])
    if notes < n * 0.9:
        print(f"  WARN 备注覆盖 {notes}/{n}（要求 ≥90%）"); warns += 1
    for i, s in enumerate(deck["slides"], 1):
        chars = sum(len(b) for b in s["bullets"]) + sum(len(c) for r in s["table"] for c in r)
        if len(s["bullets"]) > MAX_BULLETS:
            print(f"  WARN P{i:02d} 要点 {len(s['bullets'])} 条 > {MAX_BULLETS}"); warns += 1
        if chars > MAX_BODY_CHARS * 2:
            print(f"  WARN P{i:02d} 正文 {chars} 字偏多（含表格；非表格页应 ≤{MAX_BODY_CHARS}）"); warns += 1
        if s["title"].endswith(("学说", "细胞", "结构", "种类")) and len(s["title"]) < 8:
            print(f"  WARN P{i:02d} 标题疑似名词短语，建议写成结论句：{s['title']}"); warns += 1
    print("  备注覆盖率 %.0f%%，WARN %d 条" % (100 * notes / max(n, 1), warns))
    return warns


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--outdir", default=None, help="默认写到 md 所在目录")
    ap.add_argument("--title", default=None)
    ap.add_argument("--per-slide", type=int, default=9, help="每课时页数目标，用于页数 gate")
    ap.add_argument("--lessons", type=float, default=2.0, help="本章课时数（含实验课，0.5 计半课时）")
    ap.add_argument("--no-html", action="store_true")
    ap.add_argument("--no-warn", action="store_true")
    a = ap.parse_args()

    md = Path(a.md)
    if not md.exists():
        sys.exit(f"找不到 {md}")
    deck = parse_md(md)
    if a.title:
        deck["title"] = a.title
        deck["h1"] = a.title
    if not deck["slides"]:
        sys.exit("没有解析到任何 `## 页标题`，检查 Markdown 结构")
    if not deck.get("h1"):
        deck["h1"] = deck["title"]

    outdir = Path(a.outdir) if a.outdir else md.parent
    outdir.mkdir(parents=True, exist_ok=True)
    stem = md.stem  # 03-课件.md -> 03-课件.pptx；06-课件.md -> 06-课件.pptx
    pptx_path = outdir / f"{stem}.pptx"
    build_pptx(deck, pptx_path)
    print(f"[ok] {pptx_path}")
    if not a.no_html:
        html_path = outdir / f"{stem}-preview.html"
        build_html(deck, html_path)
        print(f"[ok] {html_path}  （服务端预览用；改名 preview.html 也可）")
    if not a.no_warn:
        gate(deck, a.per_slide, a.lessons)


if __name__ == "__main__":
    main()
