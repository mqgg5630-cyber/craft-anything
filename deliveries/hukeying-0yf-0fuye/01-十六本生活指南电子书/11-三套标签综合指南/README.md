# 三套标签综合指南

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本把 MBTI、星座与依恋类型放在一起用的离线指南。

配套 7 个 agent skills：label-adviser、label-map、decision-five、label-boundary、family-label-script、lean-label，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是标签使用参考，不是心理测评、诊断或占卜。三套框架的证据强度不同，书中已分别标注。所有案例都是编写情境。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/integrated.epub) | 手机与电纸书阅读 |
| [PDF](downloads/integrated.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/integrated-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 三套测试都做过，越看越乱 | [第 1 章](book/01-三套标签的分工.md)、[第 3 章](book/03-矛盾时听谁的.md) |
| 总用标签解释自己 | [第 2 章](book/02-描述自己.md) |
| 和伴侣各信一套 | [第 4 章](book/04-亲密关系.md) |
| 公司用 MBTI 或星座评价人 | [第 5 章](book/05-职场与团队.md) |
| 家里人天天转运势 | [第 6 章](book/06-家庭与朋友.md) |
| 想定一套使用规则 | [第 7 章](book/07-决策框架与停止.md) |

## 章节

- [1. 三套标签的分工与证据强度](book/01-三套标签的分工.md)
- [2. 用标签描述自己，而不被定义](book/02-描述自己.md)
- [3. 三套说法矛盾时听谁的](book/03-矛盾时听谁的.md)
- [4. 亲密关系：三套话术怎么合用](book/04-亲密关系.md)
- [5. 职场与团队：三重误用](book/05-职场与团队.md)
- [6. 家庭与朋友：跟信标签的人相处](book/06-家庭与朋友.md)
- [7. 决策框架与停止使用标签的时刻](book/07-决策框架与停止.md)

## 结构

```
integrated/
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
cd guides/integrated
python3 tools/build.py --check      # 只校验：字段、条数、来源编号
python3 tools/build.py              # 生成 index.html、selfcheck.html、GUIDE.md、EPUB
python3 tools/build_pdf.py          # 生成 downloads/integrated.pdf（需要 fpdf2）
python3 tools/audit.py              # 链接、词表、占位符检查（在 skills/guide-forge/scripts 下）
./tools/install-skills.sh           # 装 7 个 skills
```

## 许可

正文 CC BY 4.0，代码 MIT。转载与改作请署名「三套标签综合指南」并保留本条。
