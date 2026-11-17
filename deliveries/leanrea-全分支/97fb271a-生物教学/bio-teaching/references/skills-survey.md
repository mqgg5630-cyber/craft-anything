# 相关 Skills 调研（19 个）

> 2026-11-03 做过一次 GitHub 实检的全量盘点（53 个候选 → 14 个评审 → 6 个可用），
> 见 [`skills-survey-v3.md`](skills-survey-v3.md)。本文件是早期人工调研，保留作对照。

调研时间 2026-11。判断标准只有一条：**它解决的环节，我们要不要自己重写？**
星数取自 GitHub API（`gh api repos/...`），只作活跃度参考，不代表质量。

## 一、把书变成技能（原料层）

| Skill | 星 | 它做什么 | 我们借鉴什么 | 为什么不直接用 |
|---|---|---|---|---|
| [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 36.8k | 文档 → 结构化 skill：框架 / 决策规则 / 反模式 / 反例，按章出文件、按需加载；>50k token 用 REPL 式 grep+sed 探针而不是整本读 | **分章切片 + 按需加载**；大书用切片探测控制 token；`chapters/` 与索引表 | 它的目标是"蒸馏成可执行框架"。教材的价值是**知识结构保真**与课标对齐，蒸馏会丢掉事实层级、栏目、迷思 |
| [jiaxinmmhh/book-to-skill](https://github.com/jiaxinmmhh/book-to-skill) | 0 | 中文版：先解析脚手架（`sections/` + `structure.md`），再按 `distill-guide.md` 蒸馏，最后组装 | **两段式**（先切分建骨架、再改写）正好是本模块的路线 | 同上；且面向技术书/白皮书 |
| [zhouwei713/book2skill](https://github.com/zhouwei713/book2skill) | 9 | 生成有来源依据的 skill 包：`source-pack.json` 记录来源与可信度，稳定 source id 供引用 | **来源 id + 可校验引用**（我们用「册-章-节-栏目」当 id） | 产物是 skill 包，不是教学资产 |

## 二、教学设计与教案

| Skill | 星 | 它做什么 | 借鉴 | 不直接用 |
|---|---|---|---|---|
| [jiangfire/lesson-plan-skills](https://github.com/jiangfire/lesson-plan-skills) | 0 | 一次产出教案 `.md` + 单文件 HTML 幻灯片；6 条教育学原则写进产出物本身 | **时间预算守恒**（新增环节必须显性扣减）、**答案页时序**（收敛型紧跟练习、发散型放分享后）、**弹药分层投放**、HTML 放映壳 | 面向企业内训/成人培训，无课标、无学情、无迷思概念 |
| [huapg/teacher-workflow-skills](https://github.com/huapg/teacher-workflow-skills) | 0 | 教前/教中/教后 10 环节（A1–A10）+ **总协调器** + 学生画像 schema + 错题归因五分类 | **总协调器**的结构（路由、画像读写、跨环节衔接）→ 我们的「总控对话」；错题归因分类法 | 环节偏"教师事务"（家长反馈、学习规划），课堂设计深度不足 |
| [tanghua-git/skill-instructional-design](https://github.com/tanghua-git/skill-instructional-design) | 2 | v5.0 问题驱动：主问题 + 问题链（五何/良构劣构）、布鲁姆 6×4 ABCD、ICAP、GRASPS/SOLO 评分、8 维质检、`ai-era-framework.md` | **问题链设计**、ABCD 可观察动词、**AI 评估三分类**（无 AI / AI 辅助 / AI 整合）、AI 时代七问自检 | 9 个 agent 的多智能体流程成本高；术语密度大，需转成教师能直接用的表格 |
| [quietseek/teacher-prep-skill](https://github.com/quietseek/teacher-prep-skill) | 1 | 高中化学备课：教案、实验探究、错题变式、学考选考讲评；**教师版 / 课堂作答版 / 自学反馈版三版本输出** | **三版本输出**（同一份题，教师版带答案、学生版只留题面、自学版带提示） | 化学专属；浙江学考口径 |

## 三、课件与 PPT

| Skill | 星 | 它做什么 | 借鉴 | 不直接用 |
|---|---|---|---|---|
| [Gabberflast/academic-pptx-skill](https://github.com/Gabberflast/academic-pptx-skill) | — | 学术报告规范：action title（标题即结论）、幽灵牌组测试、一页一个 exhibit、极简设计 | **标题写成结论句**；"只读标题能否讲完故事"的自检 | 学术会议场景，不管教学节奏 |
| [PHY041/claude-skill-academic-ppt](https://github.com/PHY041/claude-skill-academic-ppt) | — | LaTeX/PDF → pptx，双引擎配图、**speaker notes**、Q&A 预测 | **备注页写讲稿**（课件与逐字稿天然衔接）、预判学生问题 | 面向答辩，无教学活动 |
| [Noi1r/powerpoint-skill](https://github.com/Noi1r/powerpoint-skill) | — | PptxGenJS + OMML + 图管线；**29 条硬规则**、内容密度上下限、10 秒测试、溢出防护 | 密度硬上限（每页 ≤45 字）、"10 秒测试"（一页能否 10 秒读出主张）、溢出校验 | 依赖 Node 与 Graphviz/LaTeX 环境 |
| [tristan-mcinnis/pptx-from-layouts-skill](https://github.com/tristan-mcinnis/pptx-from-layouts-skill) | — | 读母版布局 → 语义匹配占位符 → 渲染，保留学校模板设计 | 需要套用学校/教研室模板时，改用它的"母版占位符"思路 | 需先有模板与 python-pptx pydantic 依赖 |

## 四、习题与检验

| Skill | 星 | 它做什么 | 借鉴 | 不直接用 |
|---|---|---|---|---|
| [weishao2/tizhuang-agent-skills](https://github.com/weishao2/tizhuang-agent-skills) | 34 | 2000 万 K12 真题库：按教材版本/章节/知识点/题型抽题、智能组卷 | **按章节 + 知识点 + 难度抽真题**，可作"真实考题对照" | 需注册；题目版权与答案口径不由我们控制 |
| [YU-403/quiz-complete](https://github.com/YU-403/quiz-complete) | 1 | 出题 → 标准 Markdown 题库 → `build.py` → 单页刷题站（六种模式、错题本、进度持久化） | **Markdown 题库契约** + 学生端刷题站；稳定题 ID（内容哈希） | 只管选择题/判断题，无实验分析与迷思诊断 |
| [ggb6070/exam-kit](https://github.com/ggb6070/exam-kit) | 0 | 课件 → 复习提纲 + 题库 + **知识图谱**三份离线 HTML；错题本导出 | 知识图谱渲染、错题本导出、按章分组 | 面向学生自学复习，不管教学目标 |
| [questioner](https://skills.lc/HYW2023-s/questioner-skill) | — | LangGraph 多 agent 出题：7 题型 5 管线（教材解析/知识点/题库改写/驳回改造/思辨） | **题型矩阵**与"驳回改造"流程 | 依赖 LLM API key 与自建管线 |

## 五、逐字稿与视频演示

| Skill | 星 | 它做什么 | 借鉴 | 不直接用 |
|---|---|---|---|---|
| [shuyicc/MathLens](https://github.com/shuyicc/MathLens) | 361 | 一道题 → 分析 → SVG 讲解 → 分镜 → TTS → **Manim** 动画，`wait_for_narration(keyword)` 帧级同步、几何自校验 | **旁白关键词同步**（说到哪个词触发哪个动画）→ 生物改成"概念词同步"；自校验思想 | 数学几何专用 |
| [adao-max/agent-skills](https://github.com/adao-max/agent-skills) | 2 | `explainer-video`：提纲 → 旁白 → 配音与逐字时间戳 → Manim → 自动核对字幕对齐 | **默认视频路线**：旁白先定、动画后配、字幕逐字对齐核对 | 需 MiniMax TTS 账号 |
| [kuaizengji/courseware-video-skill](https://github.com/kuaizengji/courseware-video-skill) | 1 | 课件 → 电影感教学片：Manim + 代码生成配乐 + 本地 TTS + 双语字幕 + QA 脚本 | QA 清单（字幕、响度、80px 安全边距） | 工程量大，适合精品课 |
| [macromogic/myanim](https://github.com/macromogic/myanim) | 0 | Manim CLI：new/check/render/review，两次人工确认（**受众契约**、**分镜**） | **两处人工确认点** → 我们的 07 模块也要求先确认"给谁看、要讲清什么" | 需 uv/MacTeX 环境 |

## 结论：本模块的组合

我们不重写别人已经做对的部分，只补两块空缺：**教材到课堂的桥**（拆解、迷思、课标对齐）和**产物之间的 gate**。

| 环节 | 借谁的 | 我们补什么 |
|---|---|---|
| 00 教材拆解 | book-to-skill 的切片 + book2skill 的来源 id | 概念层级挂课标、迷思概念带证据、栏目与命题点 |
| 01–02 教学设计与教案 | skill-instructional-design 的问题链/ABCD + lesson-plan 的时间预算 | 生物学科的活动原型（观察、建模、论证、实验） |
| 03 课件 | academic-pptx 的行动标题 + powerpoint-skill 的密度上限 | 与逐字稿同源的备注页；`build_pptx.py` 一条命令出 pptx + HTML |
| 04 习题 | quiz-complete 的题库契约 + tizhuang 的真题对照 + teacher-prep 的三版本 | **按迷思编号出题**、错因归类、变式链 |
| 05 AI 时代教学 | skill-instructional-design 的 AI 评估三分类 | 生物特有的 AI 场景（显微图像识别、序列比对、生态数据）与幻觉检测 |
| 06 逐字稿 | academic-ppt 的 speaker notes | 口语化规则、停顿与追问标记、时长核算 |
| 07 视频演示 | MathLens / explainer-video / myanim | 生物概念的分镜原型（过程动画、尺度缩放、显微视野） |
| 总控 | teacher-workflow 的总协调器 | 章节状态机 + 一章一回合 + 交接单 |

## 课件类（本轮补检，2026-11-03）

| 仓库 | 能做什么 | 本模块怎么用 |
|---|---|---|
| [`hugohe3/ppt-master`](https://github.com/hugohe3/ppt-master)（MIT，v6.8.0） | 1280×720 SVG → **原生** PPTX：文字可编辑、图片原生、曲线/表格原生；带质量门（svg_quality_checker）、讲稿备注分页、动画/过渡、模板复用 | **已安装并接入**：`scripts/install_ppt_master.sh` + `scripts/build_deck.py`。只用它的 SVG→PPTX 导出与质量门，不用它的 Strategist 多轮确认流程（我们要的是"按课时出片"，不是"聊出一版设计"） |
| `gnuhpc/ppt-master-plus` | PPT Master 的增强分支：美化、备注、实时预览 | 暂不接；`--quick-generate` 已够 |
| `M1n-n9/academic-ppt-master` | 论文→学术 PPTX | 场景不符（我们是课时课件，不是论文汇报） |

**结论**：之前没有用任何 PPT 设计 skill——`scripts/build_pptx.py` 是自写的"文本框 + 圆点"生成器，能保证结构（页数、备注覆盖率）但保证不了好看。现在把"好看"这件事交给专门的 skill，自己只保留"内容层（md）+ 版式决策层（plan.json）"。
