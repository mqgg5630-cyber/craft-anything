# 福州租房指南

**一本可以离线读、可以检索、可以照着念的租房手册。**

7 章，42 个具体处境。每条都写清：怎么判断、原话怎么说、对方两种反应怎么接、接下来做什么、怎么算过关、哪条红线不能碰、依据有几成。

按顺序走一遍就是完整的租房流程：算预算与选址、认渠道、看房、签合同、算费用、应对福州的气候（回南天与台风）、入住与维权。

配套 7 个 agent skills：查条目、看房清单、合同核对、租金议价、入住与退租留证、极简版，以及把这个结构复刻到其他主题上的 `guide-forge`。

> **免责声明：** 本书是租房参考，不是法律意见。涉及押金、定金、转租、人身损害的具体纠纷，请咨询当地住建部门、12345 或律师。所有案例都是编写情境，不是真人记录。租金水平与政策以官方最新公告为准。

## 入口

| 入口 | 内容 |
| --- | --- |
| [离线检索页](index.html) | 42 条全文搜索、按章/依据筛选、复制原话、复制给 AI 的提问 |
| [24 题自查](selfcheck.html) | 六个维度打分，三道红线题，给出先读哪几条 |
| [对话模式库](PATTERNS.md) | 18 个可以照着演的瞬间，含两轮对话与失败改法 |
| [完整正文](GUIDE.md) | 一次读完，适合打印或导入阅读器 |
| [EPUB](downloads/fuzhou-rent.epub) | 手机与电纸书阅读 |
| [PDF](downloads/fuzhou-rent.pdf) | A4 打印版，带目录、页码、书眉与证据徽章 |
| [单文件离线版](downloads/fuzhou-rent-offline.html) | 一个 HTML，双击就开，无需联网 |
| [来源与核实记录](SOURCES.md) | 18 个来源，标了读到什么程度、哪些说法被删掉 |
| [编写规范](docs/编写规范.md) | 字段规范、证据分级、写作纪律 |
| [验收报告](docs/验收报告.md) | 结构验收与行为验收协议 |
| [站点首页](../../index.html) | 全部指南与部署说明 |

## 这本书想回答的问题

| 问题 | 去哪看 |
| --- | --- |
| 一个月到底能付多少房租？ | [1.1](book/01-预算与选址.md) |
| 住哪个片区，通勤多久？ | [1.2](book/01-预算与选址.md)、[1.3](book/01-预算与选址.md) |
| 中介费谁出、能不能谈？ | [2.2](book/02-找房渠道.md) |
| 二房东的房子能不能租？ | [2.3](book/02-找房渠道.md) |
| 看房半小时要看什么？ | [3.1](book/03-看房清单.md) |
| 墙上的霉斑要紧吗？ | [3.3](book/03-看房清单.md) |
| 怎么核对房东身份？ | [4.1](book/04-合同与押金.md) |
| 押金怎么才能退得回来？ | [4.4](book/04-合同与押金.md)、[7.3](book/07-入住与维权.md) |
| 定金交了不租，能退吗？ | [4.5](book/04-合同与押金.md) |
| 电费为什么这么贵？ | [5.2](book/05-费用与隐形成本.md) |
| 回南天、台风季怎么办？ | [6.1](book/06-福州的气候与房子.md)、[6.2](book/06-福州的气候与房子.md) |
| 押金被扣、房东失联找谁？ | [7.4](book/07-入住与维权.md) |

## 结构

```
fuzhou-rent/
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

## 构建

```bash
python3 tools/build.py --check      # 校验字段、条数、来源、模式、自查题
python3 tools/build.py              # 生成 entries.json / GUIDE.md / index.html / selfcheck.html / EPUB
python3 tools/build_pdf.py --out "$PWD/downloads/fuzhou-rent.pdf"
python3 skills/guide-forge/scripts/audit.py .
```

字体是霞鹜文楷的子集，只打包本书用到的字。换正文后重新切一次：

```bash
python3 ../tools/make_fonts.py .
```

## skills

```bash
./tools/install-skills.sh          # 软链到 ~/.claude/skills 与 ~/.agents/skills
./tools/install-skills.sh --copy   # 复制
```

| Skill | 干什么 |
| --- | --- |
| `rent-adviser` | 查条目后回答一个具体处境 |
| `viewing-checklist` | 生成看房清单并按红线给判断 |
| `lease-check` | 合同逐条过一遍，标出六类高风险 |
| `rent-negotiate` | 先算总成本，再谈条件，最后谈价 |
| `move-in-kit` | 入住与退租的留证清单 |
| `lean-rent` | 极简版：四行答案 |
| `guide-forge` | 拆解、复刻、验收别的指南 |

## 许可

正文 CC BY 4.0，代码 MIT。字体为霞鹜文楷（SIL OFL 1.1）。
