# 依恋人格指南

**一本可以离线读、可以检索、可以照着念的指南。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

一本关于依恋模式、追逃循环与修复的离线指南。

配套 7 个 agent skills：attach-adviser、trigger-map、pause-script、space-script、repair-plan、lean-attach，以及把这套结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是关系参考，不是心理诊断或治疗。依恋类型描述的是倾向，不是临床分类。所有案例都是编写情境，不是真人记录。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/场景/依据筛选、复制原话 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/attachment.epub) | 手机与电纸书阅读 |
| [PDF](downloads/attachment.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/attachment-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 15 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 不知道怎么判断自己是哪一型 | [第 1 章](book/01-依恋是什么.md)、[第 2 章](book/02-认出自己的模式.md) |
| 一谈恋爱就焦虑、反复确认 | [第 3 章](book/03-焦虑型.md) |
| 一亲密就想跑 | [第 4 章](book/04-回避型.md) |
| 想变稳一点 | [第 5 章](book/05-安全型怎么练.md) |
| 总遇到同一类人 | [第 6 章](book/06-两个人的组合.md) |
| 关系里有暴力或控制 | [第 7 章](book/07-边界与求助.md) |

## 章节

- [1. 依恋是什么：四类模式的基本盘](book/01-依恋是什么.md)
- [2. 认出自己的模式](book/02-认出自己的模式.md)
- [3. 焦虑型：追逐、确认与被丢下的恐惧](book/03-焦虑型.md)
- [4. 回避型：撤退、需要空间与亲密过载](book/04-回避型.md)
- [5. 安全型怎么练](book/05-安全型怎么练.md)
- [6. 两个人的组合](book/06-两个人的组合.md)
- [7. 边界、标签与求助](book/07-边界与求助.md)

## 结构

```
attachment/
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
cd guides/attachment
python3 tools/build.py --check      # 只校验：字段、条数、来源编号
python3 tools/build.py              # 生成 index.html、selfcheck.html、GUIDE.md、EPUB
python3 tools/build_pdf.py          # 生成 downloads/attachment.pdf（需要 fpdf2）
python3 tools/audit.py              # 链接、词表、占位符检查（在 skills/guide-forge/scripts 下）
./tools/install-skills.sh           # 装 7 个 skills
```

## 许可

正文 CC BY 4.0，代码 MIT。转载与改作请署名「依恋人格指南」并保留本条。
