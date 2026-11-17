# SKILL：科技资讯图卡复刻（素材07 · Round01）

> 本技能用于把一条科技类 YouTube Short 复刻为 10 张 9:16 资讯图卡系列 + 1 张总预览图，可直接做成图片轮播 Short 或作为视频分镜底稿。

## 一、本轮信息

| 项目 | 内容 |
|---|---|
| 轮次 | Round01 |
| 参考视频 | https://www.youtube.com/shorts/bkGhmZLOAwI |
| 视频标题 | Claude Code is now free forever: use 1.3 billion tokens per month without limits |
| 频道 | qingqing wang（2026-10-12 发布，44K 观看 / 365 赞） |
| 主题 | 用 GitHub 开源项目把 DeepSeek / Kimi 等免费模型接入 Claude Code，实现零成本 AI 编程，支持失败自动切换备用模型 |
| 核心工具 | musistudio/claude-code-router（★38k+） |
| 产出 | card_01 ~ card_10（1080×1920 PNG）+ preview_总预览图.png |

## 二、相关 GitHub 工具

| 用途 | 仓库 | Stars |
|---|---|---|
| 下载 YouTube 视频 | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | 205k+ |
| 免费模型接入 Claude Code（视频主角） | [musistudio/claude-code-router](https://github.com/musistudio/claude-code-router) | 38k+ |
| 同类备选 | quangdang46/openproxy、dmitry-lavrik/claude-code-free | — |

本地下载视频命令（需科学上网环境）：
```bash
pip install -U yt-dlp
yt-dlp -f "bv*+ba/b" -o "素材07_%(title)s.%(ext)s" "https://www.youtube.com/shorts/bkGhmZLOAwI"
```

## 三、图卡设计规范（复用即可保持系列一致）

- **画布**：1080 × 1920（9:16），PNG，quality 95
- **背景**：深海军蓝渐变 `#0B1020 → #161B36` + 高斯模糊光斑（右上橙 / 左下青）+ 72px 间距点阵
- **配色**：
  - 强调橙 `#FF7A45`（序号徽章 / 关键词）
  - 青色 `#36CFC9`（系列标签 / 次强调）
  - 紫色 `#9580FF`、绿色 `#52C47E`、红 `#FF5F5F`、黄 `#FFC850`
  - 正文白 `#F5F7FF`，灰 `#969EBA`
- **字体**：
  - 中文：Noto Sans SC（400/500/700/900，npm `@fontsource/noto-sans-sc` woff2 → fonttools 转 ttf）
  - 代码：JetBrains Mono（400/700/800，npm `@fontsource/jetbrains-mono`）
- **版式骨架**（每张统一）：
  1. 顶部左：橙色圆角徽章「第 N / 10 张」；顶部右：青色描边标签「白嫖 AI 编程系列」
  2. 大标题：Noto SC Black 92–128px，两三行，其中一行用强调色
  3. 中部：内容区（面板 / 代码窗口 / 流程图 / 列表卡）
  4. 底部：分隔线 + 「一二和布布 · AI 工具分享」+ 话题标签
- **组件库**（make_cards.py 内置）：
  - `code_window`：mac 风格三色圆点 + 标题栏 + 中英文混排代码（英文 JBMono / 中文 NotoSC 分段渲染）
  - `bullet_panel`：半透明圆角面板 + 圆点列表（自动换行、自动高度）
  - `chip`：描边胶囊标签
  - 矢量图标：`icon_x / icon_check / icon_star / icon_refresh / icon_arrow_down`（⚠️ 字体子集缺 ✓★●→ 等字形，必须用 PIL 画，不要用字符）

## 四、10 张卡叙事结构（Shorts 万能模板）

| # | 角色 | 本轮内容 |
|---|---|---|
| 01 | 封面钩子 | 大数字冲击：每月 13 亿免费 Token |
| 02 | 痛点 | AI 编程订阅贵、额度焦虑 |
| 03 | 核心思路 | 公式卡：免费模型 + Claude Code = 零成本 |
| 04 | 工具登场 | GitHub repo 卡片：claude-code-router |
| 05 | 资源盘点 | 4 大免费模型平台 |
| 06 | 步骤 1 | 安装命令（终端窗口） |
| 07 | 步骤 2 | config.json 配置（代码窗口） |
| 08 | 亮点功能 | 失败自动切换流程图 |
| 09 | 实测 | 会话演示 + 体验结论 |
| 10 | 总结 CTA | 三步回顾 + 关注引导 |

## 五、复刻流程（下一轮照做）

1. `fetch_page` 抓取目标 Short 的标题 / 简介 / 频道元数据
2. GitHub API 核实视频里提到的开源项目（名称、stars、功能）
3. 按「四」的叙事结构把内容拆成 10 张卡的文案（原创改写，不照抄原视频字幕）
4. 复用 `make_cards.py`：改每张卡的文案与组件组合，跑 `python3 make_cards.py`
5. 自检预览图：重点看 ① 特殊符号是否豆腐块 ② 代码窗口是否溢出 ③ 中英混排
6. 新建 Drive 子文件夹 `素材 07/RoundNN_主题_日期`，上传 10 卡 + 预览图 + SKILL + 文案

## 六、已知坑

- fontsource 的 chinese-simplified 子集**不含** `✓ ★ ● → ≈ √ ①` 等符号 → 一律矢量绘制或换 `× ↓ · —`
- JetBrains Mono 无中文 → 代码行必须走 `draw_mixed` 混排
- 沙盒出站仅允许 GitHub / npm / PyPI → 视频本体需在本地用 yt-dlp 下载后手动放入 Drive
