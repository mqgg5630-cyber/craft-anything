# 07 职场与生活指南（2026-10-31）

四本中文指南，同一套骨架：13（或 7）章、每章 6 条、每条十个字段（情况 / 判断 / 原话 / 回应两种 / 接着做 / 做对了 / 红线 / 依据 / 来源 / 相关）、A 到 D 证据分级、来源表、24 题自查、模式库、配套 agent skills。

| 指南 | 规模 | 章 | 条 | 来源 | 模式 | 自查 | PDF | skills |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 求职面试 | 13 章 | 13 | 82 | 27 | 20 | 24 题 | 51 页 | 7 |
| 福州租房 | 7 章 | 7 | 42 | 18 | 18 | 24 题 | 26 页 | 7 |
| 健康饮食 | 13 章 | 13 | 78 | 18 | 18 | 24 题 | 43 页 | 7 |
| 旅行 | 13 章 | 13 | 78 | 18 | 18 | 24 题 | 44 页 | 7 |

每个子文件夹里有三种文件：

- `*.pdf`：A4 打印版，带目录、页码、书眉、证据徽章。
- `*.epub`：手机与电纸书。
- `*_离线单文件.html`：一个 HTML 包含全部条目，可搜索、可复制原话，双击就开，不需要联网。

## 内容边界

- 所有案例与对话都是编写情境（D 级材料），不指向任何真实的人。
- 求职：法律条款按《劳动合同法》口径；不给具体薪资数据。
- 租房：押金、定金、转租、维修按《民法典》与部门规章；租金水平不给具体数字，以当地最新公告为准。
- 饮食：不作诊断、不给个体化处方；有确诊疾病、用药、孕期、术后，以医生与注册营养师为准。急救 120，心理援助 12356。
- 旅行：签证与入境以使领馆最新公告为准；境外遇险先打当地报警与急救，再联系中国驻当地使领馆或 12308。

## 在线版本与源码

- 站点：https://github.com/hukeying85-ux/0yf （根目录 `index.html` 是五本指南的入口，含《引导型恋人指南》）
- 每本指南自带 `index.html`（全文检索）、`selfcheck.html`（24 题自查）、`GUIDE.md`（全文）、`SOURCES.md`（来源与核实记录）、`PATTERNS.md`（模式库）。
- 安装 skills：进入任意指南目录，执行 `./tools/install-skills.sh`，会软链到 `~/.claude/skills` 与 `~/.agents/skills`。

## 复刻方法

`guide-forge` 可以拆解任意指南的结构，再按同一骨架生成一本新的：

```bash
python3 guides/job-interview/skills/guide-forge/scripts/deconstruct.py guides/job-interview --json /tmp/profile.json
python3 guides/job-interview/skills/guide-forge/scripts/scaffold.py --profile /tmp/profile.json \
    --out guides/my-guide --title "我的指南" --chapters "第一章,第二章,第三章" \
    --per-chapter 6 --tools-from guides/job-interview
python3 guides/job-interview/skills/guide-forge/scripts/audit.py guides/my-guide
```
