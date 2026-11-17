# Skills 全量盘点（v3 · 2026-11-03 用 GitHub 实检）

> 这一轮把"能用的 skill"重新扫了一遍：**53 个候选 → 14 个进入评审 → 6 个值得动**。
> 结论先放前面：**教学法部分没有现成 skill 可用，必须自研；能借的是三样——动画 XML、版式/风格库、原生图表的做法。**

## 0 怎么找的（可复现）

```bash
gh search repos "pptx" --sort stars --limit 12
gh search repos "claude skills" --sort stars
gh search repos "pptx animation" / "svg to pptx" / "PPTAgent" / "paper2slides"
gh search repos "教学设计" / "生物 教学 高中" / "k12 education" / "flashcard llm"
gh api repos/<owner>/<repo> --jq '{stars,license,pushed_at}'
gh api repos/<owner>/<repo>/readme -H "Accept: application/vnd.github.raw"
```

筛选口径：① 能落地到"一章一份课件"这条流水线；② 许可证允许**借用方法**（代码另说）；
③ 最近 6 个月有提交；④ 不依赖本机没有的东西（Chrome / LibreOffice / 中文字体）。

**一个明确的事实：中文教学法方向几乎没有像样的 skill。** `教学设计` 搜出来的是八竿子打不着的书单和面试题；
`教案生成` 只有 1 个 0 星仓库。也就是说——**我们的 `explain-protocol.md`（七步协议）和 `typography.md` 是真资产，
不是重复造轮子。**

## 1 候选清单（按流水线位）

### 1.1 版式与生成

| 仓库 | ★ | 许可 | 能力 | 结论 |
|---|---|---|---|---|
| `hugohe3/ppt-master` | 72.7k | MIT | SVG → **原生** pptx（文字/图片/曲线都是对象），有质量门 | **在用**。当前 12 版式的底座 |
| `alchaincyf/huashu-design` | 28.5k | MIT | 设计方向顾问：先出 6 张缩略图 → 挑 3 版做成真稿；92 种风格库；可编辑 PPTX、动画、信息图 | **借流程**：正是我们"三版"缺的那一步 |
| `tw93/Kami` | 12.2k | MIT | 排版规则 + 8 套文档模板，PDF/PNG/PPTX | **借规则**：中文版式细节参考 |
| `chuspeeism/dashi-ppt-skill` | 10.3k | **AGPL-3.0** | 12 主题 / 1020 版式 / 浏览器内改稿 → 导出 pptx；要 Chrome | **不用**：AGPL + 办公风，与教材气质冲突 |
| `anthropics/skills`（pptx） | 186.9k | 专有 | pptxgenjs 路线、`validate.py` 校验、`thumbnail.py` 出九宫格、模板改稿 | **借清单**：hex 不带 `#`、`LAYOUT_WIDE`、`charSpacing`、图表必须原生 等坑表 |
| `LAZARUSj/guomics-ppt` | 2 | 未标 | SVG→PPTX + 自动质量检查，**架构和我们一模一样** | 参考：看看别人怎么组织 QC（星太少，不引入） |
| `ningzimu/codex-ppt-skill` | 7.6k | — | 整页**图片**式 deck（GPT-Image 出图当页） | **不用**：不可编辑，改一个字要重画 |

### 1.2 动画

| 仓库 | ★ | 关键信息 | 结论 |
|---|---|---|---|
| `BramAlkema/pptx-animation-skill` | 1 | **唯一公开的"实测过播不播"的动画 XML 库**：入场 filter 词表、dead-path 反例库（`fill.opacity`、`stroke.weight` 等解析通过但**播不出**） | **立刻借**：已据此修正我们的 presetID——`fade` 是 **preset 9**，写 10 是 dissolve（动画窗格会标错） |
| `anmism/pptxgenjs-animation` | 5 | pptxgenjs 侧的动画 | 不适用（我们不走 pptxgenjs） |

**已修正**：`animate_pptx.py` 里 `presetID="10"` → `"9"`。同时确认我们的结构（`p:set style.visibility` + `p:animEffect filter="fade"`）**不在 dead-path 名单里**——这正是该库记载的唯一可靠入场组合。

### 1.3 图形与示意

| 仓库 | ★ | 能力 | 结论 |
|---|---|---|---|
| `Agents365-ai/drawio-skill` | 10.5k | 文本 → 可编辑 `.drawio`，**导出后自检 PNG，自动修重叠/压字/箭头堆叠（2 轮）** | **借自检思路**：我们的 `check_overflow.py` 只能算命中的包围盒，画不出图 |

### 1.4 研究型（论文 → 幻灯片）

`icip-cas/PPTAgent`（5.2k，反思式生成）、`HKUDS/Paper2Slides`（3.9k）、`OpenDCAI/Paper2Any`（2.8k，可编辑科研图示）。
**思路可借、工程不可用**：它们的输入是论文结构与图表，不是"一个知识点怎么讲懂"。

### 1.5 教学法

`excellence-wh/parcoach`（0 星，PBL 教案生成 skills）——体量与质量都撑不起一章。
**结论：教学法层继续自研。** 现有 `explain-protocol.md`（七步协议）+ `check_kp.py`（49 项验收）覆盖了这块，外面没有替代品。

## 2 我们与"最好的"差在哪（6 条）

| # | 差距 | 现况 | 影响 |
|---|---|---|---|
| 1 | 选版靠手写 | 三版是我手工定义三套色 + 三个机件 | 方向靠猜；huashu 的"先 6 张缩略图再挑 3 版"更科学 |
| 2 | 图表不是原生 | 曲线是 freeform 路径，表格是文本框 | 老师改不了数据；换一版教材要重画 |
| 3 | 动画只有 fade | 单一淡入 | 缺 wipe/zoom/按行出，节奏单调 |
| 4 | 自检只见坐标 | 包围盒 + 质量门 | 看不见"视觉上撞了但坐标没撞"（阴影、图框、色块） |
| 5 | 配图靠一次次生成 | 每张单独提示词 | 风格靠 duotone 兜底，不是从生成端锁定 |
| 6 | 版式 12 种 | 覆盖 90% 场景 | 缺"目录页 / 对比表 + 图 / 时间轴" |

## 3 优化路线（按性价比排序）

### P0 · 今天做完（改动小、收益确定）

| 动作 | 干什么 | 收益 | 成本 |
|---|---|---|---|
| ✅ 动画 preset 修正 | `presetID 10 → 9` | 动画窗格标对；避免"看起来有动画其实被丢" | 已完成 |
| 动画加两档 | 给 `wipe(up)`（表格行）和 `zoom`（大数字）两个入口，按 layout 自动选 | 节奏有变化，不再全是淡入 | 1 小时 |
| 图形页加"元素相撞"检查 | 把圆点/线条/色块的 bbox 也纳入 `check_overflow`（现在只查文字） | 投影上少一次"图压字" | 1 小时 |

### P1 · 本周（要写代码，但收益大）

| 动作 | 干什么 | 收益 | 成本 |
|---|---|---|---|
| **原生图表** | 用 python-pptx 后处理，把 `chart` 版式的 freeform 换成原生 `add_chart`（只换 3 张核心图：活化能、两条曲线、判据表） | 老师能改数据、能换教材；文件更小 | 半天 |
| **风格扩容** | 把 `--theme` 从 4 套扩到 6 套（加"黑板粉笔""旧教材双色""极简灰"），并生成 6 张封面缩略图给用户挑 | 选版不再靠猜 | 半天 |
| **动画按行** | 判据表、检查表支持"一行一次点击"，正文段落支持"一句一次" | 讲解节奏可控 | 2 小时 |

### P2 · 可选（有明确代价）

| 动作 | 代价 |
|---|---|
| 试装 `dashi-ppt-skill` 做对照 | AGPL + 要 Chrome；只作参照，不引入代码 |
| `drawio-skill` 出结构图（细胞器关系、运输路径） | 多一条工具链，`.drawio` 与 pptx 两套源 |
| 视频（manim / remotion） | 这是最后一步，现在做会拖垮主线 |

## 4 不建议做的

1. **整页图片式 deck**（`codex-ppt-skill` 一类）：等于把 pptx 变成 PDF，失去"改一个字"的能力。
2. **论文流水线**（PPTAgent / Paper2Slides）：解决的是"把论文压成 10 页"，不是"让学生懂活化能"。
3. **vendor 别人的 AGPL/专有代码**：只借方法，不拷代码。
4. **再加一套生成器**：我们已经有 md（内容）+ plan（版式）+ theme（风格）三层，再加会打架。

## 5 复测清单（每次改完必跑）

```sh
python3 scripts/check_overflow.py <构建目录>          # 0 越界 / 0 相撞 / 0 行距过挤
python3 .../svg_quality_checker.py <构建目录> --quick-generate --canonical-authoring --stage final   # 0 advisory
python3 scripts/animate_pptx.py a.pptx b.pptx          # 打印每页块数与点击数
python3 scripts/check_kp.py <kp 目录>                  # 49 项
python3 scripts/check_chapter.py <章目录>              # 36 项
python3 scripts/check_group.py <章目录>                # 14 项
```

"够不够高级"这一步脚本判不了——**每次改版都必须给人看一遍预览页**，这一条不改。
