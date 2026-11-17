#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动画自检 / WPS 兼容性体检：`python3 scripts/check_animation.py <pptx>`。

为什么需要：动画写错**不会报错**——PowerPoint 多半还能播，WPS 直接静默跳过，
你看到的只是"点了没反应"。这个脚本把"能播"拆成七条可判定的结构，
其中第 4 条（动画目标不能是组合）就是 WPS 最常见的翻车点。

检查项：
    1 p:sld 子元素顺序       cSld → clrMapOvr → transition → timing → extLst
    2 cTn id 唯一            同一页里 id 重复 = 播放器按 id 索引时错乱
    3 spTgt 目标存在         指向不存在的形状 = 该步静默丢失
    4 目标不是组合           **WPS 对"组合"动画支持差，常表现为整页没动画**
    5 animEffect 有 transition="in"
    6 clickEffect 外层条件   delay 必须是 indefinite（否则一进页就全播完）
    7 filter 在兼容白名单     fade / wipe(...) / fly(...) / circle(in) / zoom

用法：python3 scripts/check_animation.py a-含动画.pptx [b.pptx ...]
退出码 0 = 没有 FAIL（WARN 不阻塞）。
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"p": P, "a": A}

OK_FILTERS = ("fade", "wipe", "fly", "circle", "zoom", "dissolve", "barn", "checkerboard")
ORDER = ["cSld", "clrMapOvr", "transition", "timing", "extLst"]


def q(tag: str) -> str:
    pre, name = tag.split(":")
    return f"{{{P if pre == 'p' else A}}}{name}"


def shapes_by_id(root) -> dict[int, str]:
    """spid → 元素标签（sp / pic / grpSp / graphicFrame）。"""
    out = {}
    for el in root.iter():
        if el.tag in (q("p:sp"), q("p:pic"), q("p:grpSp"), q("p:graphicFrame")):
            nv = el.find(".//p:cNvPr", NS)
            if nv is not None and nv.get("id", "").isdigit():
                out[int(nv.get("id"))] = etree.QName(el).localname
    return out


def check_slide(xml: bytes, name: str) -> tuple[list[str], list[str], dict]:
    root = etree.fromstring(xml)
    fails: list[str] = []
    warns: list[str] = []
    stat = {"clicks": 0, "effects": 0}

    # 1 子元素顺序
    tags = [etree.QName(c).localname for c in root]
    idx = [ORDER.index(t) for t in tags if t in ORDER]
    if idx != sorted(idx):
        fails.append(f"{name}: p:sld 子元素顺序不对 {tags}")

    ids = shapes_by_id(root)
    timing = root.find("p:timing", NS)
    if timing is None:
        return fails, warns, stat

    # 2 id 唯一
    ctns = [e.get("id") for e in timing.iter(q("p:cTn")) if e.get("id")]
    dup = {i for i in ctns if ctns.count(i) > 1}
    if dup:
        fails.append(f"{name}: cTn id 重复 {sorted(dup)[:6]}")

    # 3/4 目标
    for tgt in timing.iter(q("p:spTgt")):
        sid = tgt.get("spid")
        if not sid or not sid.isdigit():
            fails.append(f"{name}: spTgt 缺 spid")
            continue
        kind = ids.get(int(sid))
        if kind is None:
            fails.append(f"{name}: spTgt 指向不存在的形状 #{sid}")
        elif kind == "grpSp":
            fails.append(f"{name}: 动画目标 # {sid} 是**组合**（WPS 常不播）")

    # 5 animEffect
    for eff in timing.iter(q("p:animEffect")):
        if eff.get("transition") not in ("in", "out"):
            warns.append(f"{name}: animEffect 缺 transition 属性")
            break
        filt = (eff.get("filter") or "").split("(")[0]
        if filt not in OK_FILTERS:
            warns.append(f"{name}: filter「{eff.get('filter')}」不在兼容白名单")
            break

    # 6 clickEffect 的外层 delay 必须是 indefinite
    for node in timing.iter(q("p:cTn")):
        if node.get("nodeType") != "clickEffect":
            continue
        stat["clicks"] += 1
        # 从效果节点往上爬，直到"mainSeq 的直接子 par"——那一层才是"等一次点击"
        cur = node
        group_par = None
        while cur is not None:
            par = cur.getparent()
            if par is None:
                break
            holder = par.getparent()                     # childTnLst
            up = holder.getparent() if holder is not None else None
            if up is not None and up.tag == q("p:cTn") and up.get("nodeType") == "mainSeq":
                group_par = par
                break
            cur = up
        if group_par is None:
            fails.append(f"{name}: clickEffect 结构不完整（找不到所属点击组）")
            break
        cond = group_par.find("p:cTn/p:stCondLst/p:cond", NS)
        if cond is None or cond.get("delay") != "indefinite":
            fails.append(f"{name}: clickEffect 外层 delay 不是 indefinite"
                         f"（{cond.get('delay') if cond is not None else '缺'}）→ 一进页就全播完")
            break

    stat["effects"] = len(list(timing.iter(q("p:animEffect"))))
    return fails, warns, stat


def main() -> int:
    paths = [Path(a) for a in sys.argv[1:]]
    if not paths:
        print(__doc__)
        return 2
    bad = 0
    for pptx in paths:
        fails: list[str] = []
        warns: list[str] = []
        clicks = effects = pages = 0
        with zipfile.ZipFile(pptx) as z:
            names = sorted((n for n in z.namelist()
                            if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                           key=lambda s: int(re.findall(r"\d+", s)[0]))
            for n in names:
                pages += 1
                f, w, st = check_slide(z.read(n), f"{pptx.name}:{n.split('/')[-1]}")
                fails += f
                warns += w
                clicks += st["clicks"]
                effects += st["effects"]
        flag = "PASS" if not fails else "FAIL"
        print(f"[{flag}] {pptx.name}  {pages} 页 / {clicks} 次点击 / {effects} 条效果"
              f"  FAIL {len(fails)} WARN {len(warns)}")
        for m in (fails + warns)[:10]:
            print("   " + m)
        if not clicks:
            print("   WARN 没有任何点击动画——这份文件可能是静态版")
        bad += len(fails)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
