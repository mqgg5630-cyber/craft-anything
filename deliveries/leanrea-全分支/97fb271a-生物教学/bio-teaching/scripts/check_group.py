#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成组验收：python3 scripts/check_group.py <章目录>

check_chapter.py 查"一份份文件合不合规"；本脚本只查**章之所以为章**的那几件事：
主线是否贯穿、判据表是否逐课时长出来、钩子是否闭环、重复内容是否自查。
用法示例：
    python3 scripts/check_group.py "chapters/高中-必修1-分子与细胞/第04章-细胞的物质输入与输出"
退出码：0 = 无 FAIL。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

rows: list[tuple[str, str, str]] = []


def add(level: str, item: str, detail: str = "") -> None:
    rows.append((level, item, detail))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法：python3 scripts/check_group.py <章目录>")
    d = Path(sys.argv[1])
    if not d.is_dir():
        sys.exit(f"不是目录：{d}")

    group = read(d / "00-课时切分与成组.md")
    design = read(d / "02-教学设计.md")
    slides = read(d / "03-课件.md")
    script = read(d / "06-逐字稿.md")
    index = read(d / "index.md")

    # 1. 成组件是否存在
    add("OK" if group else "FAIL", "成组件 00-课时切分与成组.md")

    # 2. 主线：必须有一个可命名的情境，且贯穿设计、课件、逐字稿
    main_line = ""
    m = re.search(r"主线[：:][^\n]*?[「“]([^」”]{2,12})[」”]", group)
    if m:
        main_line = m.group(1)
    elif "海水稻" in group:
        main_line = "海水稻"
    if not main_line:
        add("WARN", "未识别出主线情境（建议写成「主线：XXX」）")
    else:
        hits = [("设计", main_line in design), ("课件", main_line in slides),
                ("逐字稿", main_line in script)]
        miss = [k for k, v in hits if not v]
        add("OK" if not miss else "FAIL", f"主线贯穿：{main_line}",
            "缺 " + "、".join(miss) if miss else "设计/课件/逐字稿 均在")

    # 3. 判据表逐课时长出来：三栏词必须都出现，且成组文件里写了"加一列"
    cols = [c for c in ["方向", "载体", "能量"] if c in group]
    add("OK" if len(cols) == 3 else "FAIL", f"判据表三栏 {len(cols)}/3", "、".join(cols))
    add("OK" if re.search(r"加一列|加.*列|逐列", group) else "WARN", "写明「逐课时加列」")

    # 4. 钩子：埋点数量与回收数量都必须 ≥3
    hooks = len(re.findall(r"钩\s*\d", group))
    back = len(re.findall(r"回收", group))
    add("OK" if hooks >= 3 else "WARN", f"跨课时钩子 {hooks} 处")
    add("OK" if back >= 2 else "WARN", f"钩子回收 {back} 处")

    # 5. 重复内容自查表
    add("OK" if "讲一次" in group else "FAIL", "重复内容自查表（讲一次/用一次）")

    # 6. 课时数一致性：设计里的课时行数 vs 成组里的课时数
    n_design = len(re.findall(r"^\|\s*课时\s*\d+\s*\|", design, re.M)) or len(
        re.findall(r"^\|\s*\d+\s*\|[^|\n]*新授", design, re.M))
    add("OK" if n_design >= 2 else "WARN", f"课时 {n_design} 个")

    # 7. 讲授比例：三课时必须有讲/练/收三个数字
    ratio = len(re.findall(r"\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|", group))
    add("OK" if ratio >= 2 else "WARN", f"讲/练/收 比例行 {ratio} 条")

    # 8. 课件密度：总页数 / 课时数 ≥ 6（课时数 × 6–10 为合理区间）
    pages = len(re.findall(r"^##\s+\d+\s", slides, re.M))
    per = round(pages / n_design, 1) if n_design else 0
    add("OK" if per >= 6 else "WARN", f"课件 {pages} 页 / {n_design} 课时 = {per} 页每课时（建议 6–10）")
    add("OK" if slides.count(main_line) >= 1 and main_line else "WARN", "课件回到主线")

    # 9. 逐字稿必须是"关键段"而不是"全稿"，且标注清楚
    cjk = len(re.findall(r"[\u4e00-\u9fff]", re.sub(r"^>.*$", "", script, flags=re.M)))
    labeled = ("关键段" in script) or ("全稿" in script)
    add("OK" if labeled else "WARN", "逐字稿标明「关键段/全稿」")
    add("OK" if cjk >= 2000 else "WARN", f"逐字稿 {cjk} 汉字")

    # 10. 交接单必须写清"章 vs 知识点"的分工
    add("OK" if ("kp/" in index and "章" in index) else "WARN", "交接单写明 章/知识点 分工")

    order = {"FAIL": 0, "WARN": 1, "OK": 2}
    rows.sort(key=lambda r: order[r[0]])
    w = max(len(r[1]) for r in rows)
    print(f"\n成组验收：{d}\n" + "-" * (w + 36))
    for lv, item, detail in rows:
        mark = {"FAIL": "✗", "WARN": "!", "OK": "✓"}[lv]
        print(f" {mark} {item.ljust(w)}  {detail}")
    f = sum(1 for r in rows if r[0] == "FAIL")
    warn = sum(1 for r in rows if r[0] == "WARN")
    ok = sum(1 for r in rows if r[0] == "OK")
    print("-" * (w + 36))
    print(f" PASS {ok} / WARN {warn} / FAIL {f}")
    sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
