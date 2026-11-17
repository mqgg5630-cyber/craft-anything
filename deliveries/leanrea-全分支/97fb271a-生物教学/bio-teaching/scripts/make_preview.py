#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一套 SVG 页打包成**单文件自包含**预览 HTML（页面内联，不依赖相对路径 / 服务器）。

为什么要这个：
    `<stem>-preview.html` 引用 `svg_output/*.svg`，换个地方打开就是一片白框；
    发给别人、或用文件查看器直接看，都会断。自包含版把每页 SVG 直接内联进 HTML，
    图片路径改成相对本文件的 `../assets/deck-images/`，一个文件就是一套课件。

用法：
    python3 scripts/make_preview.py --svg <svg 目录> --out <输出 html> \\
        --title "酶降低活化能" --theme "A 学术冷版" --paper "#F1F0EB" --ink "#111E20" \\
        --accent "#9E2B1B" --meta "必修 1 · 第 5 章第 1 节 · 15 页" \\
        --nav "A 学术|酶-A学术.html" --nav "B 课堂|酶-B课堂.html" --nav "C 教材|酶-C教材.html"
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

IMG_PREFIX = "../assets/deck-images/"

PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · {theme}</title>
<style>
  :root{{--paper:{paper};--ink:{ink};--accent:{accent};--rule:#2a393b}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:#0d1415;color:#e6e1d6;
        font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif}}
  header{{padding:34px 42px 6px;display:flex;flex-wrap:wrap;gap:18px;align-items:flex-end;
          justify-content:space-between}}
  h1{{font-size:21px;margin:0 0 8px;font-weight:600;letter-spacing:.4px}}
  h1 span{{color:var(--accent);margin-left:10px;font-size:13px;letter-spacing:1.2px}}
  p.meta{{margin:0;color:#8b9a94;font-size:12.5px;letter-spacing:.6px}}
  nav{{display:flex;gap:8px}}
  nav a{{text-decoration:none;color:#a9b8b2;font-size:12px;letter-spacing:.6px;
         border:1px solid #2c3a3c;border-radius:99px;padding:5px 12px}}
  nav a:hover{{color:#fff;border-color:var(--accent)}}
  nav a.on{{color:var(--accent);border-color:var(--accent)}}
  main{{padding:22px 42px 72px;display:grid;gap:22px;
        grid-template-columns:repeat(auto-fill,minmax(520px,1fr))}}
  figure{{margin:0}}
  .page{{background:var(--paper);border-radius:2px;overflow:hidden;
         box-shadow:0 1px 0 rgba(255,255,255,.04)}}
  .page svg{{width:100%;height:auto;display:block}}
  figcaption{{font-size:11px;color:#7d8f89;padding:7px 2px;letter-spacing:.5px}}
</style></head>
<body>
<header>
  <div>
    <h1>{title}<span>{theme}</span></h1>
    <p class="meta">{meta} · 共 {total} 页 · 页面内联，离线可看</p>
  </div>
  <nav>{nav}</nav>
</header>
<main>
{pages}
</main>
</body></html>
"""


def inline(svg: str) -> str:
    svg = svg.replace('href="../../assets/deck-images/', f'href="{IMG_PREFIX}')
    svg = re.sub(r"<svg\b([^>]*)>", r"<svg\1>", svg, count=1)
    return svg.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--meta", default="")
    ap.add_argument("--paper", default="#F4EFE4")
    ap.add_argument("--ink", default="#14302F")
    ap.add_argument("--accent", default="#B8452A")
    ap.add_argument("--nav", action="append", default=[])
    ap.add_argument("--md", default="", help="课件 md，用来取每页标题做图注")
    ap.add_argument("--self", dest="self_name", default="")
    a = ap.parse_args()

    titles = []
    if a.md and Path(a.md).exists():
        titles = re.findall(r"^##\s+(\d+)\s+(.*)$", Path(a.md).read_text(encoding="utf-8"), re.M)
    files = sorted(Path(a.svg).glob("*.svg"))
    figs = []
    for i, f in enumerate(files):
        s = inline(f.read_text(encoding="utf-8"))
        cap = titles[i][1] if i < len(titles) else f.stem
        figs.append(f'<figure><div class="page">{s}</div>'
                    f'<figcaption>{i + 1:02d} · {cap}</figcaption></figure>')

    nav = "".join(
        f'<a class="{"on" if a.self_name and href == a.self_name else ""}" href="{href}">{label}</a>'
        for item in a.nav for label, href in [item.split("|", 1)])

    Path(a.out).write_text(PAGE.format(
        title=a.title, theme=a.theme, meta=a.meta, total=len(files),
        pages="\n".join(figs), nav=nav, paper=a.paper, ink=a.ink, accent=a.accent),
        encoding="utf-8")
    print(f"[ok] {a.out}  {len(files)} 页  {Path(a.out).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
