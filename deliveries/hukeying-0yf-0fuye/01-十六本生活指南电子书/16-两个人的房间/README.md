# 两个人的房间

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本关于「两个人在酒店房间里怎么过一天」的离线指南：能一起玩什么、怎么把房间用起来、吃什么、怎么定规则、哪些线不能越。

配套 7 个 agent skills：room-adviser、play-book、room-setup、night-plan、safe-check、lean-room，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是住店相处参考，不是情色指南，也不推荐具体酒店。所有案例都是编写情境，不是真人记录。亲密行为须明确同意；实名登记、消防与访客规定以酒店与当地要求为准。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/in-room.epub) | 手机与电纸书阅读 |
| [PDF](downloads/in-room.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/in-room-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 不知道两个人在房间干什么 | 第 1 章、第 2 章 |
| 想找点新鲜玩法 | 第 2 章、第 3 章、第 4 章 |
| 泳池健身房没去过 | 第 3 章 |
| 晚上怎么过 | 第 4 章 |
| 在房间吃饭 | 第 5 章 |
| 亲密与拒绝 | 第 6 章 |
| 偷拍、敲门、退房 | 第 7 章 |

## 章节

- [1. 把房间当成目的地](book/01-把房间当地.md)
- [2. 白天能一起做的六件事](book/02-白天一起做.md)
- [3. 把酒店用起来](book/03-把酒店用起来.md)
- [4. 晚上能一起做的六件事](book/04-晚上一起做.md)
- [5. 吃在房间里](book/05-吃在房间.md)
- [6. 亲密、边界与拒绝](book/06-亲密与边界.md)
- [7. 安全、合规与退房](book/07-安全与退房.md)

## 结构

```
in-room/
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
cd guides/in-room
python3 tools/build.py            # 校验并生成 index.html / selfcheck.html / GUIDE.md / EPUB
python3 tools/build_pdf.py        # 生成 downloads/in-room.pdf
./tools/install-skills.sh         # 把 7 个 skills 软链到 ~/.claude/skills
```

## 许可

正文 CC BY 4.0，代码 MIT。字体为霞鹜文楷（SIL OFL 1.1）。
