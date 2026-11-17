# MBTI 指南

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本关于 MBTI 四维度、用法与边界的离线指南。

配套 7 个 agent skills：mbti-adviser、type-check、team-agreement、feedback-script、type-redline、lean-mbti，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是人格讨论参考，不提供测评，也不做能力判断。MBTI 是 Myers & Briggs Foundation 的注册商标，本书与该机构无关。所有案例都是编写情境。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/mbti.epub) | 手机与电纸书阅读 |
| [PDF](downloads/mbti.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/mbti-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 刚测完，不知道准不准 | [第 2 章](book/02-测得准不准.md) |
| 想知道四个维度指什么 | [第 3 章](book/03-EI与SN.md)、[第 4 章](book/04-TF与JP.md) |
| 团队要做 MBTI 团建 | [第 6 章](book/06-职场与团队.md) |
| 被用人格类型评价过 | [第 7 章](book/07-与不同类型的人相处.md) |
| 想读十六型 | [第 5 章](book/05-十六型怎么读.md) |
| 能不能写进简历 | [第 6 章](book/06-职场与团队.md) |

## 章节

- [1. MBTI 是什么：四个维度与它的来历](book/01-MBTI是什么.md)
- [2. 测得准不准：类型、连续与巴纳姆效应](book/02-测得准不准.md)
- [3. E/I 与 S/N：能量与信息偏好](book/03-EI与SN.md)
- [4. T/F 与 J/P：决策与节奏](book/04-TF与JP.md)
- [5. 十六型怎么读](book/05-十六型怎么读.md)
- [6. 职场与团队：怎么用，怎么被滥用](book/06-职场与团队.md)
- [7. 与不同类型的人相处：分寸与红线](book/07-与不同类型的人相处.md)

## 结构

```
mbti/
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
cd guides/mbti
python3 tools/build.py --check      # 只校验：字段、条数、来源编号
python3 tools/build.py              # 生成 index.html、selfcheck.html、GUIDE.md、EPUB
python3 tools/build_pdf.py          # 生成 downloads/mbti.pdf（需要 fpdf2）
python3 tools/audit.py              # 链接、词表、占位符检查（在 skills/guide-forge/scripts 下）
./tools/install-skills.sh           # 装 7 个 skills
```

## 许可

正文 CC BY 4.0，代码 MIT。转载与改作请署名「MBTI 指南」并保留本条。
