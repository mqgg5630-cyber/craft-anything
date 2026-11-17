#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本模块的 Markdown 编译成"能直接上传成 Google Doc / Word"的干净 HTML。

用法:
    python3 scripts/md2html.py in.md -o out.html --title "教学指南 · 脱水缩合"

为什么需要这一步：Drive 的 upload_file 支持把 text/html 直接转成 Google 文档，
标题、表格、列表都会变成真结构（而不是把 `##` 和 `|` 原样塞进文档）。
这就是"知识库 → 编译 → 发布"里的编译环节。
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

CSS = """
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.75;color:#222;max-width:820px}
h1{font-size:26px;line-height:1.3;margin:0 0 .6em;border-bottom:3px solid #1b6b4c;padding-bottom:.3em}
h2{font-size:19px;margin:1.6em 0 .5em;color:#1b6b4c}
h3{font-size:16px;margin:1.2em 0 .4em}
table{border-collapse:collapse;width:100%;margin:.8em 0;font-size:14px}
th,td{border:1px solid #d8ded9;padding:6px 9px;text-align:left;vertical-align:top}
th{background:#f2f5f3}
blockquote{margin:.8em 0;padding:.5em .9em;border-left:4px solid #cfe0d4;background:#f8faf8;color:#444}
code{background:#f2f4f2;padding:1px 4px;border-radius:3px;font-size:.92em}
pre{background:#f6f8f6;border:1px solid #e3e8e4;padding:10px 12px;overflow-x:auto;font-size:13px;line-height:1.5}
ul{margin:.5em 0 .8em 1.2em;padding:0}
li{margin:.25em 0}
hr{border:0;border-top:1px solid #e3e8e4;margin:1.6em 0}
.meta{color:#666;font-size:13px}
"""


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`([^`]+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def convert(md: str) -> str:
    out: list[str] = []
    lines = md.splitlines()
    i, n = 0, len(lines)
    in_list = in_table = in_code = in_quote = False

    def close():
        nonlocal in_list, in_table, in_quote
        if in_list:
            out.append("</ul>"); in_list = False
        if in_table:
            out.append("</table>"); in_table = False
        if in_quote:
            out.append("</blockquote>"); in_quote = False

    while i < n:
        line = lines[i].rstrip()

        if line.startswith("```"):
            close()
            if in_code:
                out.append("</pre>"); in_code = False
            else:
                out.append("<pre>"); in_code = True
            i += 1
            continue
        if in_code:
            out.append(html.escape(line))
            i += 1
            continue

        if not line.strip():
            close()
            i += 1
            continue

        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                i += 1
                continue
            if not in_table:
                close()
                out.append("<table>")
                in_table = True
                out.append("<tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells) + "</tr>")
            else:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
            i += 1
            continue
        elif in_table:
            out.append("</table>")
            in_table = False

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close()
            lvl = min(len(m.group(1)), 4)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        if line.startswith(">"):
            if not in_quote:
                close()
                out.append("<blockquote>")
                in_quote = True
            out.append(f"<p>{inline(line.lstrip('> ').strip())}</p>")
            i += 1
            continue
        elif in_quote:
            out.append("</blockquote>")
            in_quote = False

        if line.strip() in ("---", "***", "___"):
            close()
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^[-*]\s+(.*)$", line)
        if m:
            if in_list:
                out.append(f"<li>{inline(m.group(1))}</li>")
            else:
                close()
                out.append("<ul>")
                in_list = True
                out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue
        elif in_list:
            out.append("</ul>")
            in_list = False

        m = re.match(r"^(\d+)[.)]\s+(.*)$", line)
        if m:
            out.append(f"<p>{inline(line)}</p>")
            i += 1
            continue

        out.append(f"<p>{inline(line)}</p>")
        i += 1

    close()
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--title", default=None)
    a = ap.parse_args()
    src = Path(a.md)
    if not src.exists():
        sys.exit(f"找不到 {src}")
    body = convert(src.read_text(encoding="utf-8"))
    title = a.title or src.stem
    doc = (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
           f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
           f"<body>{body}</body></html>")
    out = Path(a.out) if a.out else src.with_suffix(".html")
    out.write_text(doc, encoding="utf-8")
    print(f"[ok] {out}  ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
