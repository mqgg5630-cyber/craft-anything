#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单章验收：python3 scripts/check_chapter.py <章目录>

检查 references/asset-spec.md 里能用正则判定的项。查不到的（事实核验、课堂可行性）由 08 对话人工过。
退出码：0 = 无 FAIL（可能有 WARN）；1 = 有 FAIL。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

FAIL, WARN = "FAIL", "WARN"
rows: list[tuple[str, str, str]] = []


def add(level: str, item: str, detail: str = "") -> None:
    rows.append((level, item, detail))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def check_files(d: Path) -> None:
    required = ["01-教材拆解.md", "02-教学设计.md", "03-课件.md",
                "04-习题检验.md", "04-习题-学生版.md", "05-AI时代教学.md",
                "06-逐字稿.md", "07-视频演示.md"]
    for f in required:
        if (d / f).exists():
            add("OK", f"文件 {f}")
        else:
            add(FAIL, f"缺文件 {f}")
    for f in ["index.md"]:
        if (d / f).exists():
            add("OK", f"文件 {f}")
        else:
            add(WARN, f"缺生成物 {f}（交接单在 08 生成）")
    decks = sorted(d.glob("03-课件*.pptx"))
    add("OK" if decks else "WARN", f"课件 {len(decks)} 版",
        "、".join(x.stem.replace("03-课件", "") or "单墨" for x in decks))


def check_extract(d: Path) -> None:
    t = read(d / "01-教材拆解.md")
    if not t:
        return
    ids = re.findall(r"C\d+\.\d+-\d+", t)
    uniq = sorted(set(ids), key=lambda s: (s.split("-")[0], int(s.split("-")[1])))
    if len(uniq) < 5:
        add(FAIL, "次位概念不足 5 条", f"找到 {len(uniq)} 条")
    else:
        add("OK", f"次位概念 {len(uniq)} 条")
    groups: dict[str, list[int]] = {}
    for s in uniq:
        head, n = s.rsplit("-", 1)
        groups.setdefault(head, []).append(int(n))
    for head, nums in groups.items():
        if sorted(nums) != list(range(1, len(nums) + 1)):
            add(WARN, "概念编号不连续", f"{head}: {sorted(nums)}")
    myths = sorted(set(re.findall(r"M\d+", t)))
    if len(myths) < 5:
        add(WARN, f"迷思概念 {len(myths)} 条（建议 ≥5）")
    else:
        add("OK", f"迷思概念 {len(myths)} 条")
    cols = ["思考·讨论", "探究·实践", "练习与应用"]
    hit = [c for c in cols if c in t]
    if len(hit) < 2:
        add(WARN, "教材栏目盘点偏少", f"命中 {hit}")
    else:
        add("OK", f"栏目盘点命中 {hit}")


def check_design(d: Path) -> None:
    t = read(d / "02-教学设计.md")
    if not t:
        return
    if "目标—活动—评价" not in t and "目标-活动-评价" not in t:
        add(FAIL, "缺目标—活动—评价对照表")
    else:
        add("OK", "目标—活动—评价对照表")
    goals = sorted(set(re.findall(r"^\|\s*(G\d+)\s*\|", t, re.M)))
    add("OK" if len(goals) >= 2 else FAIL, f"可观察目标 {len(goals)} 条")
    # 时间预算求和
    sums = []
    for line in t.splitlines():
        if line.startswith("|") and "|" in line[1:]:
            cells = [re.sub(r"[（(].*?[)）]", "", c.strip()) for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6 and re.match(r"^\d+$", cells[1] or "x"):
                nums = [int(c) for c in cells[1:] if re.match(r"^\d+$", c)]
                if len(nums) >= 5:
                    body, total = nums[:-1], nums[-1]
                    sums.append((sum(body), total))
    if not sums:
        add(WARN, "未找到时间预算表（导入/任务/评价/合计）")
    else:
        bad = [(s, tt) for s, tt in sums if s != tt or not (43 <= tt <= 47)]
        if bad:
            add(FAIL, "时间预算不守恒", f"{bad}")
        else:
            add("OK", f"时间预算 {len(sums)} 课时，均合计 45±2 且分项之和一致")
    if "认知冲突" not in t:
        add(WARN, "未明确写出认知冲突")


def check_slides(d: Path) -> None:
    t = read(d / "03-课件.md")
    if not t:
        return
    pages = re.findall(r"^##\s+\d+\s", t, re.M)
    if len(pages) < 8:
        add(WARN, f"课件只有 {len(pages)} 页（课时数 × 8–10）")
    else:
        add("OK", f"课件 {len(pages)} 页")
    notes = len(re.findall(r"<!--\s*note:", t))
    if pages and notes / len(pages) < 0.9:
        add(WARN, f"备注覆盖 {notes}/{len(pages)}（要求 ≥90%）")
    else:
        add("OK", f"备注覆盖 {notes}/{len(pages)}")
    if "反例" not in t and "≠" not in t and "错的" not in t:
        add(WARN, "未见迷思反例页")
    else:
        add("OK", "含迷思反例")


def check_quiz(d: Path) -> None:
    t = read(d / "04-习题检验.md")
    if not t:
        return
    qs = re.findall(r"^###\s*\d+\.", t, re.M)
    if len(qs) < 10:
        add(WARN, f"题量 {len(qs)}（建议 10–14）")
    else:
        add("OK", f"题量 {len(qs)}")
    tiers = {k: len(re.findall(rf"\[{k}\]", t)) for k in ["基础", "应用", "迁移"]}
    if all(v > 0 for v in tiers.values()):
        add("OK", f"三层齐 {tiers}")
    else:
        add(FAIL, "三层不全", f"{tiers}")
    diag = len(re.findall(r"\[[CM]\d", t))
    add("OK" if diag >= len(qs) else FAIL, f"诊断标注 {diag} 处（题数 {len(qs)}）")
    if "变式" not in t:
        add(WARN, "缺变式")
    s = read(d / "04-习题-学生版.md")
    leak = [w for w in ["答案", "解析", "错因"] if w in s]
    add(FAIL if leak else "OK", "学生版无答案痕迹", f"泄漏 {leak}" if leak else "")


def check_ai(d: Path) -> None:
    t = read(d / "05-AI时代教学.md")
    if not t:
        return
    points = len(re.findall(r"###\s*融合点", t))
    add("OK" if points >= 2 else FAIL, f"AI 融合点 {points} 个（要求 ≥2）")
    for k, label in [("AI 做什么", "AI 做什么"), ("学生判断什么", "学生判断什么"),
                     ("没有 AI", "没有 AI 的替代"), ("工具", "工具说明")]:
        add("OK" if k in t else WARN, f"融合点要素：{label}")
    three = [k for k in ["无 AI", "AI 辅助", "AI 整合"] if k in t]
    add("OK" if len(three) == 3 else WARN, f"AI 评价三分类 {three}")
    if "幻觉" in t or "错" in t:
        add("OK", "含幻觉检测/错误辨析")


def check_script(d: Path) -> None:
    t = read(d / "06-逐字稿.md")
    if not t:
        return
    body = re.sub(r"^>.*$", "", t, flags=re.M)
    chars = len(re.findall(r"[\u4e00-\u9fff]", body))
    add("OK" if chars >= 2000 else WARN, f"逐字稿 {chars} 汉字（1 课时约 3000–5400）")
    marks = len(re.findall(r"\[(停|板书|看第|追问|走动|举手统计|低声)", body))
    add("OK" if marks >= 15 else WARN, f"标记 {marks} 处（建议 ≥15/课时）")
    banned = [w for w in ["综上所述", "鉴于此", "众所周知", "毋庸置疑", "显而易见"] if w in t]
    add(FAIL if banned else "OK", "无书面语禁用词", f"{banned}" if banned else "")


def check_video(d: Path) -> None:
    t = read(d / "07-视频演示.md")
    if not t:
        return
    if "受众契约" not in t and "给谁看" not in t:
        add(FAIL, "缺受众契约")
    else:
        add("OK", "受众契约")
    rows_n = len(re.findall(r"^\|\s*\d+\s*\|", t, re.M))
    add("OK" if rows_n >= 5 else WARN, f"分镜 {rows_n} 行")
    cmds = len(re.findall(r"```sh", t))
    add("OK" if cmds >= 1 else FAIL, "含可跑命令")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法：python3 scripts/check_chapter.py <章目录>")
    d = Path(sys.argv[1])
    if not d.is_dir():
        sys.exit(f"不是目录：{d}")
    check_files(d)
    check_extract(d)
    check_design(d)
    check_slides(d)
    check_quiz(d)
    check_ai(d)
    check_script(d)
    check_video(d)

    order = {"FAIL": 0, "WARN": 1, "OK": 2}
    rows.sort(key=lambda r: order[r[0]])
    width = max(len(r[1]) for r in rows)
    print(f"\n验收：{d}\n" + "-" * (width + 30))
    for lv, item, detail in rows:
        mark = {"FAIL": "✗", "WARN": "!", "OK": "✓"}[lv]
        print(f" {mark} {item.ljust(width)}  {detail}")
    f = sum(1 for r in rows if r[0] == FAIL)
    w = sum(1 for r in rows if r[0] == WARN)
    o = sum(1 for r in rows if r[0] == "OK")
    print("-" * (width + 30))
    print(f" PASS {o} / WARN {w} / FAIL {f}")
    sys.exit(1 if f else 0)


if __name__ == "__main__":
    main()
