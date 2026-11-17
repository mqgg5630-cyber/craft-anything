# 高情商指南

**一本可以离线读、可以检索、可以照着念的沟通手册。**

12 章，72 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算说对了、哪条红线不能碰、依据有几成。

顺序是一条完整的能力线：情商的四个分支、倾听、情绪识别、共情表达、赞美与感谢、批评与反馈、拒绝、冲突、道歉与修复、安慰与陪伴、文字沟通、自我情绪管理与求助。

配套 7 个 agent skills：查条目、冲突改写、倾听复盘、道歉草稿、危机识别、极简版，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是沟通参考，不是心理诊断或治疗。持续两周以上的情绪低落、失眠、自伤念头，请找精神科或心理治疗专业人员。危机时刻：急救 120，报警 110，心理援助热线 12356，妇女维权 12338，法律援助 12348。所有案例都是编写情境，不是真人记录。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 72 条全文搜索、按章/能力/依据筛选、复制原话、复制给 AI 的提问 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 20 个可以照着演的瞬间，含两轮对话与失败改法 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/gaoqingshang.epub) | 手机与电纸书阅读 |
| [PDF](downloads/gaoqingshang.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/gaoqingshang-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 情商到底指什么？ | [1.1](book/01-情商到底指什么.md) |
| 怎么听才算听懂？ | [2.1](book/02-先听懂.md)、[2.3](book/02-先听懂.md) |
| 对方说「没事」到底是不是没事？ | [2.6](book/02-先听懂.md) |
| 安慰人总越安慰越糟？ | [10.1](book/10-安慰与陪伴.md)、[10.2](book/10-安慰与陪伴.md) |
| 怎么批评人不伤人？ | [6.1](book/06-批评与反馈.md) |
| 不会拒绝、拒绝完就内疚？ | [7.1](book/07-拒绝.md)、[7.6](book/07-拒绝.md) |
| 吵架总是升级？ | [8.1](book/08-冲突.md)、[8.5](book/08-冲突.md) |
| 道歉怎么说才不假？ | [9.1](book/09-道歉与修复.md)、[9.2](book/09-道歉与修复.md) |
| 微信上老被误解？ | [11.1](book/11-文字沟通.md)、[11.4](book/11-文字沟通.md) |
| 朋友说「活着没意思」怎么办？ | [10.5](book/10-安慰与陪伴.md)、[12.4](book/12-自我情绪管理与求助.md) |
| 什么时候该去找专业帮助？ | [12.4](book/12-自我情绪管理与求助.md) |

## 结构

```
gaoqingshang/
├── book/                 正文，一章一个文件，条目用 ### 编号
├── data/                 selfcheck.json 与构建产物 entries.json
├── docs/                 编写规范与验收报告
├── downloads/            PDF / EPUB / 单文件 HTML / 纯文本
├── skills/               7 个 agent skills
├── tools/                build.py（校验+渲染）、build_pdf.py、模板、字体
├── SOURCES.md            来源与核实记录
├── PATTERNS.md           20 个沟通模式
├── GUIDE.md              构建生成的全文
├── index.html            检索页（构建生成）
└── selfcheck.html        自查页（构建生成）
```

## 重新构建

```bash
cd guides/gaoqingshang
python3 tools/build.py --check      # 只校验：字段、条数、来源编号
python3 tools/build.py              # 生成 index.html、selfcheck.html、GUIDE.md、EPUB
python3 tools/build_pdf.py          # 生成 downloads/gaoqingshang.pdf（需要 fpdf2）
python3 tools/audit.py              # 链接、词表、占位符检查
./tools/install-skills.sh           # 装 7 个 skills
```

字体是霞鹜文楷（SIL OFL 1.1）的两个子集，放在 `tools/fonts/`。PDF 不联网。

## 许可

正文 CC BY 4.0，代码 MIT。转载与改作请署名「高情商指南」并保留本条。
