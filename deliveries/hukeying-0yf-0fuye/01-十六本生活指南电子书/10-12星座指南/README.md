# 12 星座指南

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本关于星座的天文常识、社交用法与风险的离线指南。

配套 7 个 agent skills：zodiac-adviser、zodiac-fact-check、sign-script、forecast-scam-check、sign-at-work、lean-zodiac，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书不做运势预测，也不提供占卜服务。占星对性格的预测未获实证支持，书里只当作文化与沟通话题。所有案例都是编写情境。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/zodiac.epub) | 手机与电纸书阅读 |
| [PDF](downloads/zodiac.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/zodiac-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 想知道星座到底靠不靠谱 | [第 1 章](book/01-星座是什么.md)、[第 2 章](book/02-为什么觉得准.md) |
| 总被问「你什么星座」 | [第 4 章](book/04-被问星座怎么答.md) |
| 伴侣很信星座 | [第 5 章](book/05-星座与感情.md) |
| 团队里有人拿星座说事 | [第 6 章](book/06-星座与职场.md) |
| 有人推销付费占卜 | [第 7 章](book/07-运势与红线.md) |
| 想把它当社交话题 | [第 3 章](book/03-社交里的用途.md) |

## 章节

- [1. 星座是什么：天文的时间表与占星的来历](book/01-星座是什么.md)
- [2. 为什么觉得「特别准」](book/02-为什么觉得准.md)
- [3. 星座在社交里的真实用途](book/03-社交里的用途.md)
- [4. 被问「你什么星座」怎么答](book/04-被问星座怎么答.md)
- [5. 星座与感情](book/05-星座与感情.md)
- [6. 星座与职场](book/06-星座与职场.md)
- [7. 运势、水逆与付费占卜](book/07-运势与红线.md)

## 结构

```
zodiac/
├── book/                 正文，一章一个文件，条目用 ### 编号
├── data/                 selfcheck.json 与构建产物 entries.json
├── docs/                 编写规范与验收报告
├── downloads/            PDF / EPUB / 单文件 HTML / 纯文本
├── skills/               7 个 agent skills
├── tools/                build.py（校验+渲染）、build_pdf.py、模板、字体
├── SOURCES.md            来源与核实记录
├── PATTERNS.md           18 个对话模式
├── GUIDE.md              构建生成的全文
├── index.html            检索页（构建生成）
└── selfcheck.html        自查页（构建生成）
```

## 重新构建

```bash
cd guides/zodiac
python3 tools/build.py --check      # 只校验：字段、条数、来源编号
python3 tools/build.py              # 生成 index.html、selfcheck.html、GUIDE.md、EPUB
python3 tools/build_pdf.py          # 生成 downloads/zodiac.pdf（需要 fpdf2）
python3 tools/audit.py              # 链接、词表、占位符检查（在 skills/guide-forge/scripts 下）
./tools/install-skills.sh           # 装 7 个 skills
```

## 许可

正文 CC BY 4.0，代码 MIT。转载与改作请署名「12 星座指南」并保留本条。
