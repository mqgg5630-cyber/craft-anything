#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给原生 pptx 加"按块出现"的进场动画（淡入 0.5s）。

为什么单独做一个后处理：
    PPT Master 的 SVG→PPTX 只出静态页，python-pptx 也不支持动画。
    但动画在 OOXML 里就是 `ppt/slides/slideN.xml` 末尾的一段 `<p:timing>`，
    引用形状 id（spTgt spid）即可——所以可以直接改包。

做法（不改变任何排版坐标）：
    1. 读出每页 content 组里的形状，按纵向区间做"行带"合并（重叠即同带）；
    2. 每个行带包成一个新的子组（子组的 xfrm/chOff 与原组完全一致，
       所以坐标不变，只是多了一层可被动画引用的对象）；
    3. 第一带（通常是满版底图 + 标题）随页面自动出现，其余每带一次点击淡入；
    4. 页脚带并进最后一带，避免"点一下才出现页码"。

用法：
    python3 scripts/animate_pptx.py in.pptx out.pptx [--dry-run] [--simple] [--group]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"p": P, "a": A}
EMU = 9525.0          # 1px @96dpi
W_PX, H_PX = 1280, 720


def q(tag: str) -> str:
    pre, name = tag.split(":")
    return f"{{{P if pre == 'p' else A}}}{name}"


def shape_box(el):
    off = el.find(".//a:xfrm/a:off", NS)
    ext = el.find(".//a:xfrm/a:ext", NS)
    if off is None or ext is None:
        return None
    x = int(off.get("x", 0)) / EMU
    y = int(off.get("y", 0)) / EMU
    w = int(ext.get("cx", 0)) / EMU
    h = int(ext.get("cy", 0)) / EMU
    return x, y, w, h


def clusters(shapes, gap=24.0, min_h=22.0):
    """按**文档顺序**分块（SVG 的绘制顺序 = 阅读顺序）。

    · 满版底图/底色（≈整页）单独作为第一块，随页面自动出现；
    · 之后的形状依次归并：只有比当前块底部低出一截（> gap）才另起一块；
    · 后出现的图形若位置更靠上（如图文对开页的插图），归回当前块。
    """
    bg, out, cur = [], [], None
    for el in shapes:
        box = shape_box(el)
        if not box:
            continue
        _x, y, w, h = box
        if w >= 0.92 * W_PX and h >= 0.88 * H_PX:
            bg.append(el)
            continue
        if cur is not None and y <= cur["bottom"] + gap:
            cur["els"].append(el)
            cur["bottom"] = max(cur["bottom"], y + h)
        else:
            cur = {"top": y, "bottom": y + h, "els": [el]}
            out.append(cur)
    # 太薄的一块（kicker、分隔线、单条网格线）并进邻块，避免"点一下才出一个小点"
    thin = []
    for b in out:
        if thin and (thin[-1]["bottom"] - thin[-1]["top"]) < min_h:
            thin[-1]["els"] += b["els"]
            thin[-1]["bottom"] = max(thin[-1]["bottom"], b["bottom"])
        else:
            thin.append(b)
    if len(thin) > 1 and (thin[-1]["bottom"] - thin[-1]["top"]) < min_h:
        thin[-2]["els"] += thin[-1]["els"]
        thin[-2]["bottom"] = max(thin[-2]["bottom"], thin[-1]["bottom"])
        thin.pop()
    if bg:
        thin.insert(0, {"top": 0, "bottom": H_PX, "els": bg, "bg": True})
    return thin


def max_id(root) -> int:
    ids = [int(e.get("id")) for e in root.iter(q("p:cNvPr")) if e.get("id", "").isdigit()]
    return max(ids) if ids else 1


def make_group(nid: int, name: str, children) -> etree._Element:
    g = etree.Element(q("p:grpSp"))
    nv = etree.SubElement(g, q("p:nvGrpSpPr"))
    cnv = etree.SubElement(nv, q("p:cNvPr"))
    cnv.set("id", str(nid))
    cnv.set("name", name)
    etree.SubElement(nv, q("p:cNvGrpSpPr"))
    etree.SubElement(nv, q("p:nvPr"))
    pr = etree.SubElement(g, q("p:grpSpPr"))
    xfrm = etree.SubElement(pr, q("a:xfrm"))
    for tag, x, y, cx, cy in (("a:off", 0, 0, None, None), ("a:ext", None, None, W_PX * EMU, H_PX * EMU),
                              ("a:chOff", 0, 0, None, None), ("a:chExt", None, None, W_PX * EMU, H_PX * EMU)):
        e = etree.SubElement(xfrm, q(tag))
        if x is not None:
            e.set("x", str(int(x)))
            e.set("y", str(int(y)))
        else:
            e.set("cx", str(int(cx)))
            e.set("cy", str(int(cy)))
    for ch in children:
        g.append(ch)          # move（lxml 会自动从父节点摘除）
    return g


def is_text(el) -> bool:
    return el.tag == q("p:sp") and el.find("p:txBody", NS) is not None


def list_rows(block, min_items=3):
    """块内"逐条/逐行"拆分：只在**列表或表格**上动手。

    判据是"同一列、等距堆叠的短文本"：≥3 条文本框左边缘对齐（±5px）、
    单个高度 ≤ 80（一行字），且纵向依次下落。这种结构十有八九是
    列表/表格行，一条一次点击是对的。
    图（坐标轴、曲线、标注散落各处）拿不到这样的列，自动放弃——
    否则一张能量图会被拆成十几步，讲不成一句完整的话。
    """
    boxes = [(e, shape_box(e)) for e in block["els"]]
    boxes = [(e, b) for e, b in boxes if b]
    texts = [(e, b) for e, b in boxes if is_text(e) and b[3] <= 80 and b[2] >= 30]
    if len(texts) < min_items:
        return None
    # 按左边缘分列，取成员最多的那一列
    cols: dict[int, list] = {}
    for e, (x, y, w, h) in texts:
        key = int(round(x / 5))
        cols.setdefault(key, []).append((y, x, e, (x, y, w, h)))
    col = max(cols.values(), key=len)
    if len(col) < min_items:
        return None
    col.sort()
    ys = [c[0] for c in col]
    if any(ys[i + 1] - ys[i] < 12 for i in range(len(ys) - 1)):
        return None
    # 每条 = 该行文本 + 落在它这一带里的其它元素（底色、序号、分隔线）
    items = []
    for i, (y, x, e, b) in enumerate(col):
        top = y - 10
        bottom = (col[i + 1][0] - 10) if i + 1 < len(col) else block["bottom"] + 2
        items.append({"top": top, "bottom": bottom, "els": []})
    for e, (x, y, w, h) in boxes:
        cy = y + h / 2
        k = 0
        for i, it in enumerate(items):
            if cy >= it["top"]:
                k = i
        items[k]["els"].append(e)
    items = [it for it in items if it["els"]]
    return items if len(items) >= min_items else None


FILTERS = {          # 只用在 pptx-animation-skill 词表里实测过的三个
    "fade": ("fade", "9", 500),
    "wipe": ("wipe(up)", "22", 420),
    "reveal": ("wipe(left)", "22", 460),
}


def pick_effect(box, max_sz):
    """宽扁的一块（表行、通栏标题）用擦除；其余淡入。"""
    x, y, w, h = box
    if h <= 150 and w >= 620:
        return "wipe"
    return "fade"


def timing_xml(steps) -> etree._Element:
    """steps: [([spid, ...], mode, effect)]，mode = auto / click。

    **一步 = 一次点击 = 一组形状**。同一个块里的多个形状各写一条效果，
    第一条 clickEffect、其余 withEffect（PowerPoint 自己"多个对象一起"就是这么写的）。
    这样就不必先把形状包成组合——组合是 WPS 最不擅长播放的动画目标。
    """
    nid = [1]

    def nxt():
        nid[0] += 1
        return nid[0]

    timing = etree.Element(q("p:timing"), nsmap={"p": P, "a": A})
    tnLst = etree.SubElement(timing, q("p:tnLst"))
    root_par = etree.SubElement(tnLst, q("p:par"))
    ctn = etree.SubElement(root_par, q("p:cTn"))
    ctn.set("id", str(nxt()))
    ctn.set("dur", "indefinite")
    ctn.set("restart", "never")
    ctn.set("nodeType", "tmRoot")
    child = etree.SubElement(ctn, q("p:childTnLst"))

    seq = etree.SubElement(child, q("p:seq"))
    seq.set("concurrent", "1")
    seq.set("nextAc", "seek")
    sctn = etree.SubElement(seq, q("p:cTn"))
    sctn.set("id", str(nxt()))
    sctn.set("dur", "indefinite")
    sctn.set("nodeType", "mainSeq")
    scl = etree.SubElement(sctn, q("p:childTnLst"))

    for spids, mode, effect in steps:
        par = etree.SubElement(scl, q("p:par"))
        c1 = etree.SubElement(par, q("p:cTn"))
        c1.set("id", str(nxt()))
        c1.set("fill", "hold")
        st = etree.SubElement(c1, q("p:stCondLst"))
        etree.SubElement(st, q("p:cond")).set(
            "delay", "0" if mode == "auto" else "indefinite")
        c1l = etree.SubElement(c1, q("p:childTnLst"))

        p2 = etree.SubElement(c1l, q("p:par"))
        c2 = etree.SubElement(p2, q("p:cTn"))
        c2.set("id", str(nxt()))
        c2.set("fill", "hold")
        st2 = etree.SubElement(c2, q("p:stCondLst"))
        etree.SubElement(st2, q("p:cond")).set("delay", "0")
        c2l = etree.SubElement(c2, q("p:childTnLst"))

        filt, preset, dur = FILTERS[effect]
        for k, spid in enumerate(spids):
            p3 = etree.SubElement(c2l, q("p:par"))
            c3 = etree.SubElement(p3, q("p:cTn"))
            c3.set("id", str(nxt()))
            c3.set("presetID", preset)
            c3.set("presetClass", "entr")
            c3.set("presetSubtype", "0")
            c3.set("fill", "hold")
            if k == 0:
                c3.set("nodeType", "afterEffect" if mode == "auto" else "clickEffect")
            else:
                c3.set("nodeType", "withEffect")
            st3 = etree.SubElement(c3, q("p:stCondLst"))
            etree.SubElement(st3, q("p:cond")).set("delay", "0")
            c3l = etree.SubElement(c3, q("p:childTnLst"))

            setEl = etree.SubElement(c3l, q("p:set"))
            bhvr = etree.SubElement(setEl, q("p:cBhvr"))
            tc = etree.SubElement(bhvr, q("p:cTn"))
            tc.set("id", str(nxt()))
            tc.set("dur", "1")
            tc.set("fill", "hold")
            stc = etree.SubElement(tc, q("p:stCondLst"))
            etree.SubElement(stc, q("p:cond")).set("delay", "0")
            tgt = etree.SubElement(bhvr, q("p:tgtEl"))
            etree.SubElement(tgt, q("p:spTgt")).set("spid", str(spid))
            names = etree.SubElement(bhvr, q("p:attrNameLst"))
            etree.SubElement(names, q("p:attrName")).text = "style.visibility"
            to = etree.SubElement(setEl, q("p:to"))
            etree.SubElement(to, q("p:strVal")).set("val", "visible")

            eff = etree.SubElement(c3l, q("p:animEffect"))
            eff.set("transition", "in")
            eff.set("filter", filt)
            eb = etree.SubElement(eff, q("p:cBhvr"))
            et = etree.SubElement(eb, q("p:cTn"))
            et.set("id", str(nxt()))
            et.set("dur", str(dur))
            etg = etree.SubElement(eb, q("p:tgtEl"))
            etree.SubElement(etg, q("p:spTgt")).set("spid", str(spid))

    prev = etree.SubElement(seq, q("p:prevCondLst"))
    pc = etree.SubElement(prev, q("p:cond"))
    pc.set("evt", "onPrev")
    pc.set("delay", "0")
    etree.SubElement(etree.SubElement(pc, q("p:tgtEl")), q("p:sldTgt"))
    nxtc = etree.SubElement(seq, q("p:nextCondLst"))
    nc = etree.SubElement(nxtc, q("p:cond"))
    nc.set("evt", "onNext")
    nc.set("delay", "0")
    etree.SubElement(etree.SubElement(nc, q("p:tgtEl")), q("p:sldTgt"))
    return timing


def shape_id(el):
    nv = el.find(".//p:cNvPr", NS)
    return int(nv.get("id")) if nv is not None else 0


def process_slide(xml_bytes: bytes, idx=0, total=0, verbose=False, group=False, simple=False):
    root = etree.fromstring(xml_bytes)
    tree = root.find(".//p:spTree", NS)
    if tree is None:
        return xml_bytes, []

    # content 组（导出器把整页内容包在一个 <p:grpSp name="content"> 里）
    grp = None
    for g in tree.findall("p:grpSp", NS):
        nv = g.find("p:nvGrpSpPr/p:cNvPr", NS)
        if nv is not None and nv.get("name") in ("content", None, ""):
            grp = g
            break
    container = grp if grp is not None else tree
    shapes = [el for el in container if el.tag in (q("p:sp"), q("p:pic"), q("p:grpSp"))]
    if len(shapes) < 2:
        return xml_bytes, []

    bs = clusters(shapes)
    # 页脚并进上一块（不要"点一下才出现页码"）
    if len(bs) >= 2 and bs[-1]["top"] > 640:
        bs[-2]["els"] += bs[-1]["els"]
        bs.pop()
    # 逐行/逐句：块内再按行带切一刀（表格一行一步、列表一句一步）
    cap = 6
    sub = []
    for b in bs:
        sub.extend(list_rows(b) or [b])
    if 6 < len(sub) <= 9:                 # 拆得值才拆：步数上限放宽到 9
        bs, cap = sub, 9
    while len(bs) > cap:                  # 多了合并最短的相邻块
        i = min(range(len(bs) - 1), key=lambda k: (bs[k]["bottom"] - bs[k]["top"], k))
        bs[i]["els"] += bs[i + 1]["els"]
        bs[i]["bottom"] = max(bs[i]["bottom"], bs[i + 1]["bottom"])
        bs.pop(i + 1)

    if group:                              # 老做法：包成组合再对组合加动画（PowerPoint 友好，WPS 不友好）
        nid = max_id(root)
        groups = []
        for i, b in enumerate(bs):
            nid += 1
            groups.append(make_group(nid, f"step{i + 1}", b["els"]))
        for g in groups:
            container.append(g)
    else:                                  # 默认：不动树，直接给每个形状各写一条效果
        groups = bs
    # 首块（标题/底图）自动出现；封面与收尾页全部自动
    auto_n = 1
    if bs and bs[0].get("bg"):
        auto_n = 2
    if idx in (1, total):                 # 封面与收尾页整体淡入，不需要点
        auto_n = len(bs)
    def bbox(els):
        bs = [shape_box(e) for e in els]
        bs = [b for b in bs if b]
        return (min(b[0] for b in bs), min(b[1] for b in bs),
                max(b[0] + b[2] for b in bs) - min(b[0] for b in bs),
                max(b[1] + b[3] for b in bs) - min(b[1] for b in bs)) if bs else (0, 0, 0, 0)

    def max_sz(els):
        vals = [int(v) for e in els for v in re.findall(r'\bsz="(\d+)"', etree.tostring(e).decode())]
        return max(vals) if vals else 0

    steps = []
    for i, b in enumerate(bs):
        eff = "fade" if (i < auto_n and b.get("bg")) else pick_effect(bbox(b["els"]), max_sz(b["els"]))
        if simple:
            eff = "fade"
        if group:
            ids = [shape_id(groups[i])]
        else:
            ids = [i2 for i2 in (shape_id(e) for e in b["els"]) if i2]
        if ids:
            steps.append((ids, "auto" if i < auto_n else "click", eff))

    old = root.find("p:timing", NS)
    if old is not None:
        root.remove(old)
    root.append(timing_xml(steps))
    if verbose:
        n_click = sum(1 for _s, m, _e in steps if m == "click")
        n_obj = sum(len(s) for s, _m, _e in steps)
        print(f"    {len(bs)} 块 / {n_obj} 对象 → {len(bs) - n_click} 自动 + {n_click} 次点击")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True), steps


def _mk_sp(sid: int, x, y, w, h, text=None) -> etree._Element:
    body = f'<a:p><a:r><a:t>{text}</a:t></a:r></a:p>' if text is not None else ""
    return etree.fromstring(
        f'<p:sp xmlns:p="{P}" xmlns:a="{A}"><p:nvSpPr><p:cNvPr id="{sid}" name="s{sid}"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{int(x * EMU)}" y="{int(y * EMU)}"/>'
        f'<a:ext cx="{int(w * EMU)}" cy="{int(h * EMU)}"/></a:xfrm></p:spPr>'
        f'{("<p:txBody>" + body + "</p:txBody>") if text is not None else ""}</p:sp>')


def self_test() -> None:
    """按行/按句拆分的自测：列表要拆，图不能拆。"""
    # 一份"列表"：四条同左边缘、等距下落的短文本
    lst = {"els": [_mk_sp(i, 120, 200 + i * 46, 300, 30, f"第{i}条") for i in range(4)],
           "top": 190, "bottom": 420}
    got = list_rows(lst)
    ok1 = got is not None and len(got) == 4
    # 一张"能量图"：标注散落各处，没有可用的列
    dia = {"els": [_mk_sp(1, 180, 380, 60, 24, "反应物"), _mk_sp(2, 640, 380, 60, 24, "产物"),
                   _mk_sp(3, 380, 250, 70, 30, "活化能"), _mk_sp(4, 100, 200, 40, 20, "能量"),
                   _mk_sp(5, 700, 560, 70, 24, "反应进程")],
           "top": 200, "bottom": 590}
    ok2 = list_rows(dia) is None
    for name, ok in (("列表逐条拆 4 步", ok1), ("能量图不拆", ok2)):
        print(f"  {'✓' if ok else '✗'} {name}")
    if not (ok1 and ok2):
        sys.exit(1)
    print("自测通过")


def main() -> None:
    if "--self-test" in sys.argv:
        self_test()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--simple", action="store_true",
                    help="全部退化成 fade（老版本 WPS 不认 wipe(up) 时用）")
    ap.add_argument("--group", action="store_true",
                    help="把每块包成组合再动画（PowerPoint 友好；WPS 对组合动画支持差，默认关）")
    a = ap.parse_args()

    src, dst = Path(a.src), Path(a.dst)
    if a.dry_run:
        dst = Path("/tmp/_anim_dry.pptx")
    with zipfile.ZipFile(src) as zin:
        items = [(i, zin.read(i.filename)) for i in zin.infolist()]

    import re as _re
    slides = [i.filename for i, _ in items
              if i.filename.startswith("ppt/slides/slide") and i.filename.endswith(".xml")]
    total_slides = len(slides)
    total = 0
    out = []
    for info, data in items:
        if info.filename.startswith("ppt/slides/slide") and info.filename.endswith(".xml"):
            idx = int(_re.search(r"slide(\d+)\.xml$", info.filename).group(1))
            new, steps = process_slide(data, idx, total_slides, verbose=True,
                                       group=a.group, simple=a.simple)
            total += len(steps)
            data = new
        out.append((info, data))

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in out:
            zout.writestr(info, data)
    print(f"[ok] {dst}  共 {total} 个动画步（含首带自动）")


if __name__ == "__main__":
    main()
