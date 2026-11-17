# 教学类 skills 盘点（2026-11 实检）

> 问题："有哪些具体的 skills？找全了吗？教学设计的、生物的、其他学科也可以，重点是讲清楚知识点。"
> 结论先说：**教学法层没有成熟的公共 skill**——不是没找全，是这块确实空。
> 有实质内容的一只手数得过来（4 个）；其余是 0–2★ 的一次性产物。
> 真正能"讲清楚知识点"的，是**教学法本身**（第 3 节 12 条），那部分得自己写进协议里。

## 0 检索面（找了多少）

| 角度 | 检索式（节选） | 结果 |
|---|---|---|
| 中文教学 | `备课 教案`、`说课 微课`、`知识点讲解`、`教师 agent 教学`、`科学 teaching agent 生物` | 3 个有内容，均 ≤1★ |
| 英文教学 | `lesson plan skill claude`、`instructional design agent`、`socratic tutor skill`、`curriculum lesson generator`、`quiz generator`、`flashcard` | 苏格拉底系列 5 个，均 ≤2★ |
| 通用合集 | 扫了 3 个 awesome 列表（78.6k / 15.7k / 10.3k★）逐条 grep `teach/educat/tutor/lesson/learn` | 教育类条目 **共 3 条**，其中 1 条有用 |
| 官方 | `anthropics/skills` 全部 skill（docx / pptx / xlsx / pdf / canvas-design / artifacts-builder / mcp-builder …） | **零个教学法 skill** |
| 分发渠道 | skills.sh、中文市集 claudeskill.me（只读目录，未装） | 上面的仓库都已覆盖 |

**为什么这块空**：① 教材有版权（人教版不开放语料）；② 教学效果没有自动评测（写个 skill 也没法证明"讲得更懂"）；③ 大厂优先做通用能力（Office 三件套），教学法被视为"提示词"而不是"工程"。

**所以**：指望"装一个教学 skill 就完事"是行不通的。可以参考的只有 4 个骨架，其余必须自研——这条我们在第四轮就验证过，这次把检索面扩到 28 条检索式后依然成立。

## 1 有实质内容的 4 个（值得读，不必装）

| 名称 | 仓库 | ★ | 许可 | 它到底做了什么 | 我们借了什么 |
|---|---|---|---|---|---|
| **私教.skill** | `swaylq/sijiao-skill` | 20 | MIT | 输入"想学什么"→ **8 路调研**（知识地图/正典教材/高手路径/刻意练习/常见卡点/能力评估/反馈社区/动机节奏）→ 先修 DAG（拓扑校验）→ Dreyfus 分段 → 每模块 Bloom 目标 + 可评估练习 → `learner-state.json` 记进度、错题、间隔重复 | **8 路调研清单**（我们原来只有"教材 + skills"两路）；**"顺序按真实先修，不按目录页"** |
| **ADDIE 工具包** | `hoadh/instructional-design-agentic-kit` | 1 | MIT | 覆盖 ADDIE 全生命周期（Analysis/Design/Development/Implementation/Evaluation）的 skill 集合 | ADDIE 的 **E**：我们原来只有"交付验收"，缺"课后评价" |
| **职教备课智能体** | `hongmayi2651/mayi-course-prep` | 1 | MIT | 检索资料 → 教学设计 → 教案 → PPT → 实验/作业/量规/题库/知识点，一条管线 | 与我们架构**最像**的一份对照物（它没有几何质量门） |
| **苏格拉底系列** | `UderMoreiraDeAssis/socrates`、`Sharan0516/socratic-tutor`、`noVaSon/teachme-chat`、`whzp015258712145-hub/mentor-mode` | 0–2 | MIT/GPL | 提问而不给答案；按学生回答调整追问深度 | **"不直接给答案"的追问模板**：三问一停（你怎么知道 → 如果反过来呢 → 哪一步你不确定） |

## 2 只差一步的工具类（能装 / 值得抄）

| 名称 | 仓库 | ★ | 许可 | 用途 | 状态 |
|---|---|---|---|---|---|
| ppt-master | `hugohe3/ppt-master` | — | MIT | SVG → 原生 PPTX（我们在用） | **已装** |
| pptx 官方 skill | `anthropics/skills` → `skills/pptx` | 187k | 专有 | 坑表：hex 不带 `#`、`LAYOUT_WIDE` 是 13.3″、`charSpacing` 不是 `letterSpacing`、图表要原生 | **抄坑表** |
| pptx-animation-skill | `BramAlkema/pptx-animation-skill` | 1 | — | 唯一逐条**视觉验证**过的动画 XML 词表（`oracle/`）＋死路径名单 | **抄词表**（preset 9/22 就从这来的） |
| drawio-skill | `Agents365-ai/drawio-skill` | 10.5k | MIT | 导出后自动截图自检、修重叠压字 | **抄自检思路**（我们做成 `check_shapes.py`） |
| huashu-design | `alchaincyf/huashu-design` | 28.5k | MIT | 先出 6 张缩略图 → 挑 3 版做真稿；92 种风格库 | 挑版流程 |
| Kami | `tw93/Kami` | 12.2k | MIT | 排版规则 + 8 套文档模板 | 排版细则 |
| dashi-ppt-skill | `chuspeeism/dashi-ppt-skill` | 10.3k | AGPL | 12 主题 / 1020 版式 / 浏览器改稿 | 只作参照（AGPL 传染） |
| guomics-ppt | `LAZARUSj/guomics-ppt` | 2 | — | SVG→PPTX + 自动 QC | 架构与我们同构，可对照 |
| PPTAgent / Paper2Slides / Paper2Any | `icip-cas/PPTAgent` 等 | 5.2k / 3.9k / 2.8k | — | 论文 → 幻灯片流水线 | 思路可借，工程不可用（绑模型） |

## 3 教学法 skill：真正"讲清楚知识点"的 12 条

这些不是仓库，是**可执行的教学动作**，每一条都对应到课件的一页。它们才是"讲得好"的来源。

| # | 方法 | 出处 | 怎么做 | 落到课件哪一页 | 失败信号 |
|---|---|---|---|---|---|
| 1 | **认知冲突** | 反驳式文本（refutation text） | 先让学生说出错的答案，再推翻 | `statement` 页："本课唯一的问题" | 直接给正确答案 |
| 2 | **类比映射** | 类比迁移研究 | 目标物 ↔ 源物逐项对应，并写明**哪里不成立** | `diagram`（桥/隧道/闸门） | 类比说完不划边界 |
| 3 | **具体—图示—抽象** | CRA 序列 | 先具体情境，再图示，再符号/定义 | 三页连排 | 一上来就给定义 |
| 4 | **变式** | 中国数学教学（一题多变/多变归一） | 换一个条件，结论怎么变；哪些不变 | `compare` / `chart` 变式页 | 只讲一个例子 |
| 5 | **正例 + 反例** | 概念教学（关键属性） | 给出"像但不是"的例子 | `checklist`（错→对） | 只给正例 |
| 6 | **双重编码** | 双通道加工 | 同一页：图 + 词同时出现，互相对指 | 每个 `diagram` 页 | 图上无标注、正文无指路 |
| 7 | **工作记忆管理** | 认知负荷理论 | 一页一个意思；块 ≤6；字 ≥24px | 全篇 | 一页三个要点 |
| 8 | **样例渐隐** | worked example → fading | 第一题全解，第二题留一步，第三题全留 | 习题页 | 一道例题后直接上难题 |
| 9 | **检索练习 + 间隔** | retrieval practice | 讲完立刻问、下课前再问、隔天再问 | 收尾页 + 作业 | 只有"听懂了没" |
| 10 | **自我解释** | self-explanation | "这一步为什么成立？"写在图上 | 关键推导页 | 只写结论 |
| 11 | **干扰项诊断** | 迷思概念研究 | 把学生最可能的错答做成选项 | 习题 | 选项都是凑数 |
| 12 | **教别人** | learning by teaching | "讲给同桌听，他卡在哪" | 活动页 | 全程老师讲 |

我们的 **七步协议**（`references/explain-protocol.md`）就是把这 12 条排成一个顺序：
现象(3) → 冲突(1) → 模型(2,6) → 命名(3) → 边界(2) → 迁移(4,5,8) → 反测(9,10,11)。

## 4 我们自研、外面拿不到的

| 资产 | 为什么没有现成的 |
|---|---|
| 七步讲解协议 + **49 项**判据（`check_kp.py`） | 教学效果好坏的自动评测不存在，只能把人评审的判据写死 |
| 章级成组 14 项（`check_group.py`） | 没人做"主线贯穿 / 钩子闭环 / 重复自查"这种章级一致性 |
| 课件工程管线（SVG→PPTX→polish→chart→animate） | 通用 PPT skill 只管"生成"，不管"字体槽 / 原生图表 / 动画兼容" |
| 三道几何门（文字 / 图形 / 动画） | 需要在无渲染环境里判版面，属于工程脏活 |

## 5 怎么装配

```text
装（2 个）：ppt-master（SVG→PPTX）+ pptx-animation-skill 的词表（抄进 animate_pptx.py）
借（3 个）：sijiao 的 8 路调研 · ADDIE 的 E（课后评价） · socratic 的三问一停
自研（4 个）：七步协议 + 三套判据 + 几何门 + 动画兼容层
不装（N 个）：所有 0–2★ 的一次性 skill，读 README 就够
```

## 6 复测用的检索式

```sh
gh search repos "lesson plan skill claude" --limit 20
gh search repos "instructional design agent" --limit 20
gh search repos "socratic tutor skill" --limit 20
gh search repos "备课 教案" --limit 20
gh search repos "知识点讲解" --limit 20
gh search repos "education skills claude" --limit 20
gh api repos/<owner>/<repo>/readme -H "Accept: application/vnd.github.raw"   # 看它到底写了什么
```

判据：**有没有"判据/质检/可评估练习"**。只有提示词罗列、没有验收的，一律当 0★ 处理。
