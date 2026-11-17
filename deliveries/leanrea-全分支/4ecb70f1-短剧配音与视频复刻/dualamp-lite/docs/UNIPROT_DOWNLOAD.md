# UniProt 快照的获取与校验（2026-11-10）

DualAMP-Lite 的负样本背景来自 Swiss-Prot 细菌胞质蛋白。本文件记录**怎么取**和**怎么校验**，
不含任何凭据。

## 查询式（快照锁定）

```
(reviewed:true) AND (taxonomy_id:2) AND (cc_scl_term:SL-0086)
AND (length:[100 TO 5000]) AND (NOT ft_signal:*) AND (NOT ft_transmem:*)
```

- 端点 `https://rest.uniprot.org/uniprotkb/stream`
- FASTA：`format=fasta&compressed=true`
- TSV：`format=tsv&compressed=true&fields=accession,id,protein_name,organism_name,length,cc_subcellular_location`
- 预期：FASTA 117,172 条 / TSV 117,172 行（表头 1 行），两侧必须一致

## 两条获取路径

1. **本机 / 任意可直连 UniProt 的机器**：`data/raw/UniProt/download_uniprot.sh`（curl + gzip 校验 + 条数比对）。
2. **受限环境（本项目的 Agent 沙箱）**：沙箱只放行 GitHub / PyPI，`rest.uniprot.org` 被阻断，
   因此把下载放进 Kaggle 内核执行，产物经预授权 resumable URI 回传私有 Google Drive。
   下载脚本 `uniprot_download.py` 与上面 shell 脚本等价（同一查询式、同样校验），
   额外输出 sha256 / md5 / 记录数。

## 2026-11-10 实测结果

| 文件 | 字节 | md5 | 条数 |
|---|---|---|---|
| `uniprot_bacteria_cytoplasm_reviewed.fasta.gz` | 27,721,477 | `4f0bd8c8…2ed6` | 117,172 |
| `uniprot_bacteria_cytoplasm_reviewed.tsv.gz` | 3,704,283 | `7830d540…4f75` | 117,172 |

sha256 见 Drive 清单（`uniprot_download_manifest.json`）：

- FASTA `53edcd309eb1855b1c982ebf661216c8ca6fce287ae37045b0577e50e6cefb1a`
- TSV `0f9b6bb2c818b36f6c2f697bac5b9d7edb06a178c5da619f34321dbdb92ec88b`

两次独立获取（06:44Z 本机路径 / 07:03Z Kaggle 路径）**逐字节一致**，Release 2026_04。

## 复现要求

- 训练前把上述 md5 写进实验日志；文件变了说明 UniProt 发了新版本，需要重新登记快照时间。
- 严禁把 `*.gz` 原始数据提交进 Git（见 `.gitignore`），只提交本说明与清单。
