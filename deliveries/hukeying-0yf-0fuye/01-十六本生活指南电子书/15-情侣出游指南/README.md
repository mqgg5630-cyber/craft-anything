# 情侣出游指南

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本关于约会安排、行程节奏、拍照沟通、发布边界、吃饭与应变的离线指南。

配套 7 个 agent skills：trip-adviser、plan-day、photo-coach、post-check、eat-plan、lean-trip，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是出行参考，不是旅游攻略，也不推荐具体店铺与路线。所有案例都是编写情境，不是真人记录。景区规定、天气预警与禁飞要求以当地最新公告为准。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/date-trip.epub) | 手机与电纸书阅读 |
| [PDF](downloads/date-trip.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/date-trip-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 不知道该怎么约 | 第 1 章 |
| 约出来了不知道去哪 | 第 2 章 |
| 拍照总被说拍得丑 | 第 3 章 |
| 照片发不发、怎么发 | 第 4 章 |
| 吃饭总踩雷 | 第 5 章 |
| 突然下雨、她不方便 | 第 6 章 |
| 住宿、机位、花销的边界 | 第 7 章 |

## 章节

- [1. 约与定：怎么开口约一次出门](book/01-约与定.md)
- [2. 行程：不要把她当行李](book/02-行程.md)
- [3. 拍照：她要的不是技术，是被看见](book/03-拍照.md)
- [4. 记录：照片、视频与发不发](book/04-记录.md)
- [5. 吃饭：一顿饭决定半天心情](book/05-吃饭.md)
- [6. 应变：下雨、生理期、走散与吵架](book/06-应变.md)
- [7. 边界、安全与花销](book/07-边界与安全.md)

## 结构

```
date-trip/
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
cd guides/date-trip
python3 tools/build.py            # 校验并生成 index.html / selfcheck.html / GUIDE.md / EPUB
python3 tools/build_pdf.py        # 生成 downloads/date-trip.pdf
./tools/install-skills.sh         # 把 7 个 skills 软链到 ~/.claude/skills
```

## 许可

正文 CC BY 4.0，代码 MIT。字体为霞鹜文楷（SIL OFL 1.1）。
