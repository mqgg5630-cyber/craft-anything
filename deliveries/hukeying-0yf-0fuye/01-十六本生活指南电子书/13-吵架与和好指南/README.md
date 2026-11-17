# 吵架与和好指南

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本关于冲突升级、哄人、道歉与复盘、以及什么时候必须停的离线指南。

配套 7 个 agent skills：quarrel-adviser、escalate-map、pause-script、soothe-three、repair-review、lean-quarrel，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是关系沟通参考，不是心理咨询。所有案例都是编写情境，不是真人记录。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/quarrel.epub) | 手机与电纸书阅读 |
| [PDF](downloads/quarrel.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/quarrel-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 正在吵，想停 | 第 2 章第 4 条 |
| 刚吵完她不理我 | 第 4 章、第 6 章 |
| 她说我太理性 | 第 3 章 |
| 道歉没被接受 | 第 5 章 |
| 想从根上改 | 第 5 章 |
| 出现摔东西、推搡 | 第 7 章 |

## 章节

- [1. 吵架是怎么升级的](book/01-吵架怎么升级.md)
- [2. 吵的时候说什么](book/02-吵的时候说什么.md)
- [3. 当她说你太理性](book/03-太理性.md)
- [4. 哄人的正确姿势](book/04-哄人.md)
- [5. 道歉与复盘](book/05-道歉与复盘.md)
- [6. 冷战、撤退与追](book/06-冷战与撤退.md)
- [7. 高危时刻与求助](book/07-高危时刻.md)

## 结构

```
quarrel/
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
cd guides/quarrel
python3 tools/build.py            # 校验并生成 index.html / selfcheck.html / GUIDE.md / EPUB
python3 tools/build_pdf.py        # 生成 downloads/quarrel.pdf
./tools/install-skills.sh         # 把 7 个 skills 软链到 ~/.claude/skills
```

`build.py --check` 只校验不写文件；`audit.py` 在 `skills/guide-forge/scripts/audit.py`。

## 许可

正文 CC BY 4.0，代码 MIT。字体为霞鹜文楷（SIL OFL 1.1）。
