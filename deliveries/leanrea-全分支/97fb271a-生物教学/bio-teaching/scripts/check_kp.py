#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识点验收：python3 scripts/check_kp.py <kp 目录>

检查 02b 讲解设计 + 知识库卡 + 指南 + 学案 + 诊断题 + 板画/动画（+ 可选课件/逐字稿/AI/交接单）。
最小集 6 份；完整集 10 份。退出码：0 = 无 FAIL。
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


def cjk(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def files(d: Path) -> None:
    core = ["00-讲解设计.md", "01-知识库卡片.md", "02-教学指南.md",
            "03-学生一页学案.md", "04-诊断题.md", "05-板画与动画.md"]
    extra = ["06-课件.md", "07-逐字稿.md", "08-AI时代教学.md", "index.md"]
    for f in core:
        add("OK" if (d / f).exists() else "FAIL", f"文件 {f}")
    for f in extra:
        add("OK" if (d / f).exists() else "WARN", f"可选 {f}")
    decks = sorted(d.glob("06-课件*.pptx"))
    add("OK" if decks else "WARN", f"可选课件 {len(decks)} 版",
        "、".join(x.stem.replace("06-课件", "") or "单墨" for x in decks))


def design(d: Path) -> None:
    t = read(d / "00-讲解设计.md")
    if not t:
        return
    # 一句定义 ≤25 字
    lines = t.splitlines()
    idx = next((i for i, l in enumerate(lines) if "一句定义" in l or "一句记住" in l), None)
    if idx is None:
        add("FAIL", "缺「一句定义」")
    else:
        window = "\n".join(lines[idx:idx + 3])
        m = re.search(r"`([^`]{6,})`", window)
        if not m:
            add("WARN", "一句定义未用反引号标出，无法计数")
        else:
            n = len(m.group(1).replace(" ", ""))
            add("OK" if n <= 26 else "FAIL", f"一句定义 {n} 字（≤26）", m.group(1)[:30])
    has_conflict = bool(re.search(r"##\s*\d+\.\s*冲突", t)) or "造冲突" in t
    add("OK" if has_conflict else "FAIL", "含冲突环节")
    for key, label in [("哪里不像", "类比失效处"),
                       ("变式", "变式"), ("回收", "回收复述"), ("时间预算", "时间预算")]:
        add("OK" if key in t else "FAIL", f"含{label}")
    vs = len(re.findall(r"^\|\s*V\d", t, re.M))
    add("OK" if vs >= 3 else "FAIL", f"变式 {vs} 个（要求 ≥3，各只变一维）")
    # 时间预算求和
    totals = re.findall(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", t)
    add("OK" if re.search(r"讲\s*[:：]", t) else "WARN", "标注讲/练/收比例")


def kb(d: Path) -> None:
    t = read(d / "01-知识库卡片.md")
    if not t:
        return
    ps = len(set(re.findall(r"\bP\d+\b", t)))
    ms = len(set(re.findall(r"\bM\d+\b", t)))
    add("OK" if ps >= 8 else "FAIL", f"核心命题 {ps} 条（≥8）")
    add("OK" if ms >= 6 else "FAIL", f"迷思 {ms} 条（≥6）")
    for key in ["诊断信号", "表征", "边界", "关联", "sources"]:
        add("OK" if key in t else "WARN", f"字段：{key}")


def guide(d: Path) -> None:
    t = read(d / "02-教学指南.md")
    if not t:
        return
    add("OK" if "一句话讲法" in t else "FAIL", "含一句话讲法")
    add("OK" if "板书" in t else "FAIL", "含板书设计")
    q = len(re.findall(r"\*\*\d+\.\*\*", t))
    add("OK" if q >= 3 else "WARN", f"当堂诊断题 {q} 道（≥3）")
    up = len(re.findall(r"→\s*\*\*[A-D]\*\*", t))
    add("OK" if up >= 3 else "WARN", f"带答案 {up} 道")
    # 时间表
    ts = re.findall(r"^\|\s*(\d+)\s*[–-]\s*(\d+)\s*\|", t, re.M)
    if ts:
        end = max(int(b) for _, b in ts)
        add("OK" if 38 <= end <= 45 else "WARN", f"流程覆盖到第 {end} 分钟")
    else:
        add("WARN", "未找到时间表")


def quiz(d: Path) -> None:
    t = read(d / "04-诊断题.md")
    if not t:
        return
    qs = re.findall(r"^###\s*\d+\.", t, re.M)
    add("OK" if len(qs) >= 8 else "WARN", f"题量 {len(qs)}（建议 8–10）")
    diag = len(re.findall(r"\[[PM]\d", t))
    add("OK" if diag >= len(qs) else "FAIL", f"诊断标注 {diag} 处")
    add("OK" if "变式" in t else "WARN", "含变式")


def board(d: Path) -> None:
    t = read(d / "05-板画与动画.md")
    if not t:
        return
    rows_n = len(re.findall(r"^\|\s*\d+:\d\d", t, re.M))
    add("OK" if rows_n >= 3 else "WARN", f"分镜 {rows_n} 行")
    add("OK" if "```sh" in t else "FAIL", "含可跑命令")
    add("OK" if "哪里不像" in t or "一致性" in t else "WARN", "含一致性检查")


def slides(d: Path) -> None:
    t = read(d / "06-课件.md")
    if not t:
        return
    pages = len(re.findall(r"^##\s+\d+\s", t, re.M))
    add("OK" if 10 <= pages <= 22 else "WARN", f"课件 {pages} 页（10–22）")
    notes = len(re.findall(r"<!--\s*note:", t))
    add("OK" if pages and notes / pages >= 0.9 else "WARN", f"备注覆盖 {notes}/{pages}")


def script(d: Path) -> None:
    t = read(d / "07-逐字稿.md")
    if not t:
        return
    body = re.sub(r"^>.*$", "", t, flags=re.M)
    n = cjk(body)
    add("OK" if n >= 2000 else "WARN", f"逐字稿 {n} 汉字")
    marks = len(re.findall(r"\[(停|板书|看第|追问|走动|举手统计|低声)", body))
    add("OK" if marks >= 15 else "WARN", f"标记 {marks} 处")
    banned = [w for w in ["综上所述", "鉴于此", "众所周知", "毋庸置疑", "显而易见"] if w in t]
    add("FAIL" if banned else "OK", "无书面语禁用词", str(banned) if banned else "")
    long_sent = [s for s in re.findall(r"[^。！？\n]{26,}", body) if cjk(s) > 25]
    add("OK" if len(long_sent) <= 3 else "WARN", f"超 25 字的句子 {len(long_sent)} 处（口语宜短）")


def ai(d: Path) -> None:
    t = read(d / "08-AI时代教学.md")
    if not t:
        return
    pts = len(re.findall(r"###\s*融合点", t))
    add("OK" if pts >= 2 else "FAIL", f"AI 融合点 {pts} 个")
    for key in ["AI 做什么", "学生判断什么", "没有 AI", "需要什么工具"]:
        add("OK" if key in t else "WARN", f"要素：{key}")
    three = [k for k in ["无 AI", "AI 辅助", "AI 整合"] if k in t]
    add("OK" if len(three) == 3 else "WARN", f"评价三分类 {three}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法：python3 scripts/check_kp.py <kp 目录>")
    d = Path(sys.argv[1])
    if not d.is_dir():
        sys.exit(f"不是目录：{d}")
    files(d)
    design(d)
    kb(d)
    guide(d)
    quiz(d)
    board(d)
    slides(d)
    script(d)
    ai(d)

    order = {"FAIL": 0, "WARN": 1, "OK": 2}
    rows.sort(key=lambda r: order[r[0]])
    w = max(len(r[1]) for r in rows)
    print(f"\n知识点验收：{d}\n" + "-" * (w + 32))
    for lv, item, detail in rows:
        mark = {"FAIL": "✗", "WARN": "!", "OK": "✓"}[lv]
        print(f" {mark} {item.ljust(w)}  {detail}")
    f = sum(1 for r in rows if r[0] == "FAIL")
    warn = sum(1 for r in rows if r[0] == "WARN")
    ok = sum(1 for r in rows if r[0] == "OK")
    print("-" * (w + 32))
    print(f" PASS {ok} / WARN {warn} / FAIL {f}")
    sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
