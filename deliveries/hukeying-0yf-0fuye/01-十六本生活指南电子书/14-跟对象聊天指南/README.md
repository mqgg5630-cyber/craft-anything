# 跟对象聊天指南

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本关于开场、接话、情绪回应、敏感题与节奏的离线指南。

配套 7 个 agent skills：chat-adviser、open-line、keep-talk、mood-reply、ex-answer、lean-chat，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是沟通参考，不是心理咨询。所有案例都是编写情境，不是真人记录。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/smalltalk.epub) | 手机与电纸书阅读 |
| [PDF](downloads/smalltalk.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/smalltalk-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 不知道发什么 | 第 1 章、第 2 章 |
| 聊两句就断 | 第 3 章 |
| 她情绪不好 | 第 4 章 |
| 被问前任、工资 | 第 5 章 |
| 异地、消息量不对等 | 第 6 章 |
| 越聊越累 | 第 7 章 |

## 章节

- [1. 聊天不是找话题](book/01-聊天不是找话题.md)
- [2. 每天怎么开场](book/02-每天怎么开场.md)
- [3. 让话继续下去](book/03-让话继续.md)
- [4. 对方情绪低的时候](book/04-对方情绪低.md)
- [5. 敏感话题怎么答](book/05-敏感话题.md)
- [6. 异地与高频聊天](book/06-异地与高频聊天.md)
- [7. 聊不下去与及时止损](book/07-聊不下去与止损.md)

## 结构

```
smalltalk/
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
cd guides/smalltalk
python3 tools/build.py            # 校验并生成 index.html / selfcheck.html / GUIDE.md / EPUB
python3 tools/build_pdf.py        # 生成 downloads/smalltalk.pdf
./tools/install-skills.sh         # 把 7 个 skills 软链到 ~/.claude/skills
```

`build.py --check` 只校验不写文件；`audit.py` 在 `skills/guide-forge/scripts/audit.py`。

## 许可

正文 CC BY 4.0，代码 MIT。字体为霞鹜文楷（SIL OFL 1.1）。
