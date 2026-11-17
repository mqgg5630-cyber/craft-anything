#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 SVG→PPTX 之后的"最后一公里"补上：字体槽位与图片替代文字。

为什么必须做这一步（实测发现的坑）：
    转换器把每一段文字都写成 `typeface="+mj-lt"` / `+mn-lt"`（引用主题字体），
    而它生成的主题里 **major 和 minor 都被写成了 SimSun**。
    结果：屏幕上看到的"宋体标题 + 黑体正文"，到了 PowerPoint 里**正文也变宋体**——
    整套课件变成单一衬线，这就是"预览挺好看、打开很一般"的原因之一。

做法：
    major（标题）= Times New Roman + SimSun（拉丁走衬线，汉字走宋体）
    minor（正文）= Arial + Microsoft YaHei（汉字走微软雅黑，Mac 上 Office 自带）
    这两个字体在 Windows / macOS 的 Office 里都随装，不挑机器。

另外给图片补 `descr`（替代文字），读屏与"选择窗格"里能看到这是什么图。

用法：
    python3 scripts/polish_pptx.py deck.pptx            # 原地
    python3 scripts/polish_pptx.py deck.pptx out.pptx
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

MAJOR_LATIN, MAJOR_EA = "Times New Roman", "SimSun"
MINOR_LATIN, MINOR_EA = "Arial", "Microsoft YaHei"


def fix_theme(xml: str) -> str:
    for tag, latin, ea in (("majorFont", MAJOR_LATIN, MAJOR_EA),
                           ("minorFont", MINOR_LATIN, MINOR_EA)):
        m = re.search(rf"<a:{tag}>.*?</a:{tag}>", xml, re.S)
        if not m:
            continue
        block = m.group(0)
        block = re.sub(r'<a:latin typeface="[^"]*"', f'<a:latin typeface="{latin}"', block, count=1)
        block = re.sub(r'<a:ea typeface="[^"]*"', f'<a:ea typeface="{ea}"', block, count=1)
        block = re.sub(r'<a:cs typeface="[^"]*"', f'<a:cs typeface="{ea}"', block, count=1)
        # 各语言 script 槽位：汉字（Hans/Hant/Jpan/Hang）统一到同一套
        block = re.sub(r'(<a:font script="(?:Hans|Hant|Jpan|Hang)" typeface=")[^"]*"',
                       rf'\g<1>{ea}"', block)
        xml = xml.replace(m.group(0), block)
    return xml


def add_alt_text(xml: str) -> str:
    """只给 <p:pic> 里的图片补替代文字；形状与组合不动。"""
    def fix_pic(m):
        block = m.group(0)
        if "descr=" in block:
            return block
        return re.sub(r"<p:cNvPr\b([^>]*?)/>",
                      r'<p:cNvPr\1 descr="课程配图：单墨版画"/>', block, count=1)
    return re.sub(r"<p:pic>.*?</p:pic>", fix_pic, xml, flags=re.S)


def polish(src: Path, dst: Path | None = None) -> tuple[int, int]:
    dst = Path(dst or src)
    with zipfile.ZipFile(src) as zin:
        items = [(i, zin.read(i.filename)) for i in zin.infolist()]

    out, n_theme, n_img = [], 0, 0
    for info, data in items:
        name = info.filename
        if re.fullmatch(r"ppt/theme/theme\d+\.xml", name):
            data = fix_theme(data.decode("utf-8")).encode("utf-8")
            n_theme += 1
        elif re.fullmatch(r"ppt/slides/slide\d+\.xml", name):
            txt = data.decode("utf-8")
            before = txt.count("<p:cNvPr")
            txt = add_alt_text(txt)
            n_img += txt.count('descr="课程配图')
            data = txt.encode("utf-8")
        out.append((info, data))

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in out:
            zout.writestr(info, data)
    return n_theme, n_img


def main() -> None:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src
    n_theme, n_img = polish(src, dst)
    print(f"[ok] {dst}  主题 {n_theme} 处字体槽位已修，图片替代文字 {n_img} 条")


if __name__ == "__main__":
    main()
