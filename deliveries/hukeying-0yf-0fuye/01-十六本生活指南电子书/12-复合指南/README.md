# 复合指南

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本关于分开之后怎么判断、怎么联系、怎么重建的离线指南。

配套 7 个 agent skills：reunion-adviser、split-check、first-message、meet-plan、trust-plan、lean-reunion，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是关系参考，不是情感咨询，也不承诺任何结果。所有案例都是编写情境，不是真人记录。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/reunion.epub) | 手机与电纸书阅读 |
| [PDF](downloads/reunion.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/reunion-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 想复合但说不清为什么 | 第 1 章 |
| 不知道值不值得 | 第 2 章 |
| 想联系又不敢发 | 第 3 章 |
| 被问前任、怕说错 | 第 4 章 |
| 已经约了见面 | 第 5 章 |
| 复合了但没底 | 第 6 章 |
| 被拒绝、想放手 | 第 7 章 |

## 章节

- [1. 先分清「想复合」是什么](book/01-先分清想复合.md)
- [2. 这段关系值不值得重来](book/02-值不值得重来.md)
- [3. 断联、复联与第一条消息](book/03-断联与复联.md)
- [4. 前任话题怎么谈](book/04-前任话题.md)
- [5. 复联后的第一次见面](book/05-第一次见面.md)
- [6. 重建信任：从保证到可验证](book/06-重建信任.md)
- [7. 复合失败与放手](book/07-失败与放手.md)

## 结构

```
reunion/
├── book/                 正文，一章一个文件，条目用 ### 编号
├── data/                 selfcheck.json 与构建产物 entries.json
├── docs/                 编写规范与验收报告
├── downloads/            PDF / EPUB / 单文件 HTML / 纯文本
├── skills/               7 个 agent skills
├── tools/                build.py（校验+渲染）、build_pdf.py、模板、字体
├── SOURCES.md            来源与核实记录
├── PATTERNS.md           18 个对话模式
├── README.md             本文件
├── GUIDE.md              完整正文（构建产物）
├── index.html            离线检索页（构建产物）
└── selfcheck.html        24 题自查（构建产物）
```

## 构建

```bash
cd guides/reunion
python3 tools/build.py            # 校验并生成 index.html / selfcheck.html / GUIDE.md / EPUB
python3 tools/build_pdf.py        # 生成 downloads/reunion.pdf
./tools/install-skills.sh         # 把 7 个 skills 软链到 ~/.claude/skills
```

`build.py --check` 只校验不写文件；`audit.py` 在 `skills/guide-forge/scripts/audit.py`。

## 许可

正文 CC BY 4.0，代码 MIT。字体为霞鹜文楷（SIL OFL 1.1）。
