# GitHub Skills 调研与逐项适配（本次实际安装 + 映射到你的盘）

> 任务要求："安装 github 上相关的 skills 帮我分析一下，各个方面"。
> 本次不是"引用"，是**真装了**：3 个公开仓库已 clone 到 `~/skills/`，56 个 skill 已软链到 `~/.claude/skills` 与 `~/.agents/skills`，并用它们的方法论逐条对照你的 25 个顶层目录。

---

## 一、安装记录（可复现）

```bash
mkdir -p ~/skills && cd ~/skills
git clone --depth 1 https://github.com/zLanqing/codex-claude-academic-skills.git
git clone --depth 1 https://github.com/coreyhaines31/marketingskills.git
# 安装（软链进两个 Agent 标准目录）
for s in ~/skills/codex-claude-academic-skills/*/ ~/skills/marketingskills/skills/*/; do
  n=$(basename "$s"); ln -sfn "$s" ~/.claude/skills/$n; ln -sfn "$s" ~/.agents/skills/$n
done
```

结果：`~/.claude/skills` 下 **56 个** skill 生效（3 学术 + 53 营销）。

---

## 二、已装 skill 清单与能力边界

### A. `zLanqing/codex-claude-academic-skills`（中文优先，3 个）

| skill | 能做什么 | 对你的价值 |
|---|---|---|
| `office-academic-skill` | 论文 → Word 阅读报告；开题/中期/答辩 PPT；DOCX/PPTX 可编辑生成；模板匹配；演讲备注；版式质检；中英混排保留英文标题/公式/变量/参考文献 | 直接解决你 16 号的 docx 谱系与 07–12 的 PPT/PDF 复用 |
| `research-writing-skill` | 论文正文/摘要/引言/方法/结果/讨论、回复审稿人、LaTeX/Overleaf、论文润色 | 对应 02 号 `06_R183-R185_修复与论文总表` |
| `scientific-toolkit-skill` | MATLAB/Octave、科学 Python、信号/图像处理、统计、仿真、优化、出版级图表、引用检索、可复现流程 | 对应 16 号 ESM-2 / DualAMP 脚本与 DualAMP 数据工程 |

### B. `coreyhaines31/marketingskills`（53 个，按对你的用处分组）

- **文案与内容**：`copywriting` `copy-editing` `content-strategy` `marketing-psychology` `marketing-ideas` `offers` `pricing` `lead-magnets` `marketing-plan` `marketing-loops` `marketing-council`
- **渠道与增长**：`social` `video` `image` `influencer-marketing` `community-marketing` `public-relations` `co-marketing` `events` `emails` `sms` `cold-email` `prospecting` `referrals` `affiliates` `directories`/`directory-submissions` `link-building`
- **转化与站点**：`cro` `ab-testing` `conversion-tracking` `analytics` `attribution` `site-architecture` `schema` `seo-audit` `ai-seo` `programmatic-seo` `popups` `paywalls` `onboarding` `signup` `churn-prevention`
- **竞品与调研**：`competitors` `competitor-profiling` `customer-research` `reverse-engineer-marketing`
- **投放与其他**：`ads` `ad-creative` `aso` `revops` `sales-enablement` `product-marketing` `free-tools` `launch`

### C. 只读核对（未安装，作为对照与备选）

| 仓库 | 规模 | 定位 | 对你的用法 |
|---|---|---|---|
| `K-Dense-AI/scientific-agent-skills` | 177 skills / 100+ 数据库 | 把任意 Agent 变成 AI Scientist（arXiv 2609.00065，v2.72.0） | 16 号抗菌肽的文献-蛋白-数据全链，需要时按需装单 skill |
| `ComposioHQ/awesome-claude-skills` | 索引总表（79k★） | 全生态目录 | 找细分 skill 的入口 |
| `thedotmack/claude-mem` | 单 skill（115k★） | 跨会话持久上下文 | 对应你 14 号"待机实验/跨对话复用"的痛点 |
| `paperclipai/paperclip` | 应用（112k★） | 团队级 Agent 管理 | 未来多人协作时用 |
| `tt-a1i/archify` | 单 skill（95k★） | 把想法/代码库变成交互式架构图 | 给本审计的目录关系出图 |
| `ayghri/i-have-adhd` | 单 skill | 让 Agent 别把答案埋起来（结论先行） | 全盘"索引/说明"文档的文风标准 |

> 检索方式：`GET api.github.com/search/repositories?q=…&sort=stars`（两个维度：`claude skills in:name`、`topic:claude-skills`）。

---

## 三、逐项适配表（skill → 你的文件夹 → 怎么用 → 产出）

| 你的资产 | 推荐 skill | 具体用法 | 可交付产出 |
|---|---|---|---|
| 16 号 docx 谱系（V1→V4、开题、总结） | `office-academic-skill` | 把 V4 作为唯一母版，其余降为附录；统一 中文正文字体 + 英文术语保留 | 一份版式统一的《抗菌肽课题总报告》DOCX + 答辩 PPT |
| 02 号 `R183–R185 修复与论文总表` | `research-writing-skill` | 逐条 response-to-reviewer 起草，保留公式/编号/实测值 | 审稿回复信 + 修订说明 |
| 16 号 `colab_t4_esm2_feature_extraction*.py`、`kaggle_2x_t4_dualamp_lite_train*.py` | `scientific-toolkit-skill` | 代码复盘（复现性、随机种子、指标口径）+ 出版级图表 | 训练曲线/混淆矩阵/特征可视化一组图 |
| DualAMP 原始数据（07/manifests/raw） | `scientific-toolkit-skill` | raw 只读 + manifest 校验 + 数据字典 | `data_card.md`（数据卡） |
| 15 号云端算力 Skill | `scientific-toolkit-skill` + 自建 `gpu_ctl` | 把"训练→导出→Drive 直传→释放实例"固化为一条命令 | 一键跑通脚本 + 实测 JSON 归档 |
| 07–12 十五本指南（PDF/EPUB/HTML） | `office-academic-skill` | 每本生成统一 开题式 PPT（10 页）用于引流/讲课 | 15 份引流 PPT |
| 06 号「引导型恋人指南」多形态 | `copywriting` + `copy-editing` | 提炼 3 条钩子文案（痛点/反常识/身份），做小红书 A/B 两版 | 6 条文案 + 2 套封面 |
| 社交库 9 个跑通项目 | `launch` + `analytics` + `conversion-tracking` | 建立发布台账；每条打 UTM 式标记（项目/轮次/封面） | 发布台账表 + 单条复盘 |
| 素材库 8 平台 | `social` + `programmatic-seo` | 平台化改写（同内容不同平台语气/长度/话题） | 一稿 8 平台矩阵表 |
| 13 号画风复刻 | `image` + `ad-creative` | 把 v7 口径写成"提示词三段式"模板，稳定出图 | 画风提示词卡（对外可售） |
| 05 号电商长图 v1–v3 | `cro` + `copy-editing` | 按"首屏 3 秒/卖点排序/信任元素"重排 | 长图改版方案 + v4 |
| 09 号星座/MBTI 指南 | `marketing-psychology` | 把"不做运势预测"的立场做成差异化卖点（反伪科学） | 立场页文案 |
| 03 号私密区 | 不适用任何 skill | 保持本地化 + 脱敏 | — |
| 全盘索引（00 号） | `i-have-adhd` 文风 + `archify` | 结论先行重写索引；生成目录关系图 | 一页目录地图 PNG/SVG |
| 跨对话复用（14/15） | `claude-mem`（备选） | 把"唤醒口令"升级成结构化记忆 | 记忆条目规范 |

---

## 四、你自建 skill 的"公开生态定位"（重要结论）

| 你的 skill | 公开生态对应物 | 结论 |
|---|---|---|
| `guide-forge`（指南工厂） | **无** | 公开生态没有"把生活经验做成 6 章×6 条 + 证据分级 + 红线"的方法论。**可首发开源** |
| `healing-comic`（v1.3 → v7 口径） | `yang0/handraw-style`（6.9k★，367 种手绘风格）、`wzj52501/aesthetic-atelier`（1★） | 你的"原画=target、原片只抠轮廓"是实测结论，比公开库更可执行 |
| `scribble-couple`（红笔情侣头像） | 无（仅 `aesthetic-atelier` 含 couple avatars 子技能） | 独占，可占位 |
| `lean-attach/mbti/zodiac/…`（105 个） | 无 | 体量上已是"一个人的 skill 生态" |
| `jiamama-bedtime-story-skill` 等睡前故事库 | 4–6★ 不等 | 你的睡前故事产物（10 篇长故事）可反哺成 skill |
| 15 号 GPU skill | `K-Dense-AI` 有科学栈但无"个人 GPU 持久化"方案 | 你的 PKCE + 双平台路由是稀缺实践 |

**一句话**：你缺的不是 skill，是**把 skill 变成仓库 + 文档站 + 定价**的那一步。

---

## 五、缺口与建议（按性价比）

1. **建一个总仓库 `hukeying85-ux/skills-hub`**（或复用 `0yf` 站）：把 15 本书的 105 个 skill + healing-comic + gpu skill 收进去，统一 `install-skills.sh`。（你已有安装脚本，只是散在各书里。）
2. **给每个 skill 补 frontmatter `description`**（公开生态的硬门槛：Agent 靠 description 决定是否加载）。你现有的 SKILL.md 多为中文正文，缺标准化字段。
3. **装 1–2 个"元 skill"**：`i-have-adhd`（结论先行文风）用于所有说明文档；`archify` 用于目录/流水线图。
4. **科研侧按需装单 skill**，不要整包 177 个（体积与冲突风险）。
5. **凭据永不进 skill**：skill 里只写"如何从 vault 取"，不写 token（你 15 号已这么做，保持）。

---

## 六、本次审计实际使用了哪些 skill 方法

- `i-have-adhd` 的"结论先行"→ 00 号文档第一节即结论。
- `office-academic-skill` 的"母版唯一 + 版式质检"→ 06 号/16 号的母版建议。
- `research-writing-skill` 的"保留公式与实测值"→ 02/16 的修改纪律。
- `scientific-toolkit-skill` 的"可复现流程 + 数据卡"→ DualAMP 数据层建议。
- `marketing-psychology` / `offers` / `pricing`→ 第 4 节的商业化判断。
- `analytics` / `conversion-tracking` → 社交库升级为"发布台账"的方案。
