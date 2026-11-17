#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 SVG 里"画"出来的曲线换成 **PowerPoint 原生图表**。

为什么要换：
    SVG 描出来的曲线到 PPT 里是一条路径（Freeform），能看不能改——
    改一个数据点要重画整张图，教务检查也会问"这是不是图片"。
    原生图表是真正的数据对象：右键 → 编辑数据，改数值、加系列、换样式都在 PPT 里完成。

做法：
    build_deck.py 画图时把曲线数据（x/y 采样点、颜色、虚线）写进 `<stem>-charts.json`；
    本脚本读出该文件，在对应页**删掉那块画出来的图**，在同一位置插一个原生图表。
    位置、配色、字号都跟原来一致，所以换完看着像同一张，但已经是数据了。

用法：
    python3 scripts/native_chart.py <deck.pptx> [charts.json]
    （不给 charts.json 时按 <同名>-charts.json 找）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.chart.data import XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import (XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE,
                             XL_TICK_LABEL_POSITION, XL_TICK_MARK)
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.util import Emu, Pt

PX = 9525  # 1px @96dpi 的 EMU

FONT = "微软雅黑"


def _rgb(hexcolor: str) -> RGBColor:
    return RGBColor.from_string(hexcolor.lstrip("#").upper())


def _px_box(shape):
    return (int(shape.left) / PX, int(shape.top) / PX,
            int(shape.width) / PX, int(shape.height) / PX)


def _inside(box, region, slack=1.0) -> bool:
    x, y, w, h = box
    rx, ry, rw, rh = region
    return (x >= rx - slack and y >= ry - slack
            and x + w <= rx + rw + slack and y + h <= ry + rh + slack)


def _walk(shapes):
    for sh in shapes:
        yield sh
        if sh.shape_type == 6 or hasattr(sh, "shapes"):       # group
            try:
                yield from _walk(sh.shapes)
            except (AttributeError, TypeError):
                pass


def _area_fill(chart, panel_hex: str) -> None:
    """图表区底色 + 无边框（python-pptx 没有 chart.format，只能改 ChartSpace 的 spPr）。"""
    C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    cs = chart._chartSpace
    sp = cs.find(f"{{{C}}}spPr")
    if sp is None:
        sp = etree.SubElement(cs, f"{{{C}}}spPr")
    for ch in list(sp):
        sp.remove(ch)
    fill = etree.SubElement(sp, f"{{{A}}}solidFill")
    clr = etree.SubElement(fill, f"{{{A}}}srgbClr")
    clr.set("val", panel_hex.lstrip("#").upper())
    ln = etree.SubElement(sp, f"{{{A}}}ln")
    etree.SubElement(ln, f"{{{A}}}noFill")


def build_chart(slide, spec) -> None:
    region = spec["region"]
    data = XyChartData()
    for s in spec["series"]:
        pts = s["pts"]
        ser = data.add_series(s["name"], number_format="0.0")
        for xv, yv in pts:
            ser.add_data_point(xv, yv)

    x, y, w, h = [v * PX for v in region]
    gf = slide.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_SMOOTH_NO_MARKERS,
                                Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)), data)
    chart = gf.chart

    chart.font.name = FONT
    chart.font.size = Pt(spec.get("font_pt", 13))
    chart.font.color.rgb = _rgb(spec.get("ink2", "5B6B5F"))
    _area_fill(chart, spec.get("panel", "F2E6CB"))

    chart.has_title = False
    chart.has_legend = bool(spec.get("legend", True))
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.RIGHT
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(spec.get("legend_pt", 14))
        chart.legend.font.color.rgb = _rgb(spec.get("ink", "1A2A26"))

    for i, s in enumerate(spec["series"]):
        ser = chart.series[i]
        ser.marker.style = XL_MARKER_STYLE.NONE
        line = ser.format.line
        line.color.rgb = _rgb(s["color"])
        line.width = Pt(s.get("width_pt", 2.4))
        if s.get("dash"):
            line.dash_style = MSO_LINE_DASH_STYLE.DASH
        ser.smooth = True

    ca = chart.category_axis           # XY 散点：x 轴叫 category_axis
    ca.has_major_gridlines = False
    ca.has_minor_gridlines = False
    ca.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    ca.major_tick_mark = XL_TICK_MARK.OUTSIDE
    ca.minimum_scale, ca.maximum_scale = spec.get("x_range", [0, 1])
    ca.format.line.color.rgb = _rgb(spec.get("ink", "1A2A26"))
    if spec.get("xlabel"):
        ca.has_title = True
        ca.axis_title.text_frame.text = spec["xlabel"]
        for p in ca.axis_title.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(12)
                r.font.name = FONT
                r.font.color.rgb = _rgb(spec.get("ink2", "5B6B5F"))

    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = _rgb(spec.get("rule", "E3D6BD"))
    va.major_gridlines.format.line.width = Pt(0.6)
    va.tick_label_position = XL_TICK_LABEL_POSITION.NONE
    va.minimum_scale, va.maximum_scale = spec.get("y_range", [0, 1])
    va.format.line.color.rgb = _rgb(spec.get("ink", "1A2A26"))
    if spec.get("ylabel"):
        va.has_title = True
        va.axis_title.text_frame.text = spec["ylabel"]
        for p in va.axis_title.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(12)
                r.font.name = FONT
                r.font.color.rgb = _rgb(spec.get("ink2", "5B6B5F"))
    return gf


def apply(pptx: Path, specs: list[dict]) -> tuple[int, int]:
    prs = Presentation(str(pptx))
    n_del = n_add = 0
    for spec in specs:
        idx = int(spec["slide"]) - 1
        if idx < 0 or idx >= len(prs.slides):
            continue
        slide = prs.slides[idx]
        region = spec["region"]
        # 1) 删掉这块"画"出来的图（整块落在区域内的才删，标题/页脚不在此区域）
        doomed = [sh for sh in _walk(slide.shapes)
                  if sh.has_text_frame is False or True]
        doomed = []
        for sh in _walk(slide.shapes):
            try:
                box = _px_box(sh)
            except (TypeError, ValueError):
                continue
            if box[2] <= 0 or box[3] <= 0:
                continue
            if _inside(box, region):
                doomed.append(sh)
        for sh in doomed:
            el = sh._element
            el.getparent().remove(el)
            n_del += 1

        # 2) 插原生图表，并把它挪进 content 组（这样动画按块引用得到它）
        gf = build_chart(slide, spec)
        grp = None
        for sh in slide.shapes:
            if sh.shape_type == 6 and sh.name in ("content", "", None):
                grp = sh._element
                break
        if grp is None:
            for sh in slide.shapes:
                if sh.shape_type == 6:
                    grp = sh._element
                    break
        if grp is not None:
            grp.append(gf._element)
        n_add += 1
    prs.save(str(pptx))
    return n_del, n_add


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pptx = Path(sys.argv[1])
    spec_path = Path(sys.argv[2]) if len(sys.argv) > 2 else pptx.with_name(pptx.stem + "-charts.json")
    if not spec_path.exists():
        print(f"[chart] 没有 {spec_path.name}，跳过（这页没有需要换成原生图表的曲线）")
        return 0
    specs = json.loads(spec_path.read_text(encoding="utf-8"))
    n_del, n_add = apply(pptx, specs)
    print(f"[chart] 原生图表 {n_add} 张（清掉 {n_del} 个画图元素）→ {pptx.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
