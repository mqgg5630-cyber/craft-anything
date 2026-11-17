# 计划 ↔ 代码 对照表（含审查意见落实证据）

对应文档：`../抗菌肽深度学习方案_三次审查修订与最终执行版_V3_20261109_2245.docx`（本仓库根目录）
代码根目录：`dualamp-lite/`

---

## 1. 章节级对照

| 计划章节 | 计划内容 | 代码位置 | 产物 | 验证方式 |
|---|---|---|---|---|
| §3.2 支路 A | ESM-2 残基级 (N,L,480) 不池化，供多尺度 CNN | `features.py::FairESMEncoder.encode`、`models.py::MultiScaleCNN` | `features/*_feat.npz: residue/mask` | `tests/test_pipeline.py::test_feature_shapes` |
| §3.2 支路 B | Masked Mean Pooling，不含 BOS/EOS/Padding | `features.py`（`bias` = `mask`）、`models.py::masked_mean` | `*_feat.npz: mean` | `test_pipeline` 用 mask 手工复算均值并 `allclose` |
| §3.2 主模型 | M3 = CNN 128 + 理化 64 = 192 → MLP，**Concat** | `models.py::ConcatDual` | `model/M3_seed*.pt` | `test_pipeline::test_checkpoint_reloads` |
| §3.2 P0 修正 | 单 Token Cross-Attention 降级为选做，改真多 Token 交叉注意力 | `models.py::CrossAttentionDual`（query 长度 = 特征数 35） | 选做 `M4` | 代码注释 + 结构（`n_physio > 1`） |
| §3.2 实验顺序 | M0-RF/XGB → M0-CNN-BiGRU → M1 → M2 → M3 → M4/M5 | `config.TrainConfig.models`、`cli` | `ablation/D9_ablation.csv` | 报告第 4 节配对比较 |
| §3.3 理化 35 维 | AAC 20 + 全局 7（含 Boman）+ 两亲性 5 + 补充 3 | `biophys.py::FEATURE_NAMES` | `features/feature_meta.json` | `test_biophys::test_feature_vector_contract` |
| §3.3 P0 Aliphatic Index | `AI = A + 2.9V + 3.9(I+L)`（ExPASy） | `biophys.py::aliphatic_index` | `feature_meta.json.notes` | `test_biophys::test_expasy_definition` |
| §3.3 P0 Boman Index | 固定自由能来源/单位/正负号 | `biophys.py::BOMAN_FREE_ENERGY`（Radzicka & Wolfenden 1988, kcal/mol） | 同上 | `test_biophys::test_boman_fixed_source` |
| §3.3 P1 冗余处理 | 训练集相关性矩阵、\|r\|>0.85 分组、不硬凑维数 | `biophys.py::redundancy_report`、`features.extract_all` | `features/biophys_correlation.csv` | 报告第 2 节 |
| §4.1 五层数据 | General / Bacterial / Negative / Hard negative / Scrambled | `dataset.py`（layer 词汇 + scrambled 生成） | `dataset/dataset_all.csv` | `tests/test_seq_dataset.py` |
| §4.1 标签审核 | 跨库去重、冲突标记、MIC 元数据保留 | `dataset.py::deduplicate`（`label_audit.csv`） | `dataset/label_audit.csv` | `test_seq_dataset::test_trainable_clusters_are_label_pure` |
| §4.1 P0 细菌 AMP 层 | 单独数据层 + 单独报告 | `layer=bacterial_amp` + `feature_meta`/报告分层统计 | `dataset_summary.json` | 汇总表按 layer 计数 |
| §5 同源聚类 | 全部序列统一聚类（CD-HIT `-c 0.4 -aL 0.8 -n 2`） | `dataset.py::_run_cd_hit` / `_run_mmseqs` / `_kmer_cluster` | `dataset/clusters.tsv` | `test_no_cluster_straddles_dev_or_test` |
| §5 三层结构 | 开发集 CV（5 seeds×5 folds）/ 独立测试一次 / 外部集不参与选择 | `train.py`（`make_folds`、`train_torch_model`、`evaluate_external`） | `model/*_scores.npz` | 报告第 3/5 节 |
| §5 统计 | AUROC DeLong、MCC/AUPRC 按簇 Bootstrap、FDR、等价界值 | `evaluate.py` | `D9_ablation.csv`（含 q 值/within_margin） | `tests/test_metrics.py`（9 个用例） |
| §5 P1 AMPSphere | 100 条体外测试肽作外部集，不用 863k 候选 | manifest `layer: external` + `external_homolog` 拆分 | `D11_external_validation.csv` | 报告第 5 节 |
| §6 交付物 | D1–D15 | `report.py::_deliverable_checklist` | 报告第 7 节自动核对 | `report` 命令 |
| §8 目录/命名隔离 | 独立 workdir、`M*_seed*.pt` | `config.Paths`、`paths.model` | `2026-11-09_DualAMP-Lite/` | `python -m dualamp_lite check` |
| §9 三个脚本 | step1/2/3 | `build` / `features` / `train` 子命令 | 同上 | `--help` |

---

## 2. 审查意见 ↔ 实现证据

| 审查项（§1.3） | 结论/严重度 | 本代码的落实 | 可复核的地方 |
|---|---|---|---|
| ESM-2 + 多尺度 CNN + 理化架构 | 中 | 阶梯式 M1→M2→M3，M4/M5 选做；M3 用 Concat | `models.py`、报告第 4 节 |
| 正负样本构建 / 标签质量 | 高 | 跨库去重、冲突入 `label_audit.csv`、只保留实验验证（manifest `positive_values`）、MIC 元数据、bacterial 层、scrambled 仅挑战集 | `dataset.py`、`label_audit.csv` |
| CD-HIT 0.4 低同源测试 | 高 | 全部序列联合聚类 + Group Split；覆盖率参数可配；k-mer 回退自动记录 | `dataset.py::cluster_sequences`，`dataset_summary.json.cluster_method` |
| 5 Seeds × 10-Fold 统计 | 中高 | 折不再当独立观测；同一独立测试集上配对比较；簇级 Bootstrap | `train.py::compare_models`、`evaluate.py::paired_bootstrap` |
| AD 队列分组错误 | 很高 | 代码**不**输出任何 AD 分组结论；只生成 D1 元数据模板 | `dataset/D1_sample_metadata.csv`，报告第 6 节 |
| 30 天全交付过高 | 很高 | 只承诺 D2–D11；D12–D14 明确标注为流水线之外 | `README.md` §7、报告第 7 节 |

### P0 技术修正的“可执行证据”

| P0 项 | 原问题 | 修正实现 | 对应测试 |
|---|---|---|---|
| Aliphatic Index | 公式缺 Ala、系数错 | `biophys.aliphatic_index`（ExPASy 摩尔百分比口径） | `test_expasy_definition` / `test_poly_alanine` / `test_old_broken_formula_is_not_used` |
| Cross-Attention | Key/Value 长度 1，softmax 恒 1 | 主模型改 Concat；M4 改成 35 个 query token | `models.py` 类注释 + `ConcatDual.fusion_dim == 192` |
| ESM-2 BOS/CLS | 用 BOS 当全局向量 | `mask` 仅真实残基，BOS/EOS 被切掉 | `test_feature_shapes`（mask 复算均值） |
| PRJNA798058 164 vs 93 | 未经证实当日重 | 代码不涉及；D1 模板要求 Subject-BioSample-Experiment-Run 关系 | `D1_sample_metadata.csv` 列定义 |
| PRJNA679346 43 vs 106 | 同上 | 同上（`include` / `exclusion_reason` 列） | 同上 |
| 细菌 AMP 专项层 | 领域偏移 | `bacterial_amp` 层 + 报告分层计数 | `dataset_summary.json.layer_counts` |
| cAMP 双重索引 | 氨基酸不能给 Bowtie2 | **不在本流水线**（D13 工作，需另写脚本） | README §7 明示 |
| DESeq2 integer counts | 不能喂 CPM/TPM | **不在本流水线**（D13/D14） | 同上 |

---

## 3. 与计划的偏差（必须写进论文方法/限制）

1. **理化维数 35 ≠ 计划里的“32”**
   V3 表格逐项相加为 20+6+5+3 = 34，其中并没有 Boman Index；而 §3.3 的 P0 又要求固定 Boman 的来源。
   代码实现 34 + 1 = **35** 维，并把真实维数写进 `feature_meta.json`。
   这与计划自身 P1 原则一致（“不为凑 32 维硬凑”），但**论文里必须写 35 维并说明**。

2. **Aliphatic Index 计算了但不进特征向量**
   它与 AAC 高度共线（A/V/I/L 的频数线性组合）。保留函数 + 单测供正文引用，避免与 AAC 重复计权。

3. **ESM-2 只有 t12_35M**
   计划也写的是 `esm2_t12_35M`，与 T4 / 30 GPU h 的约束匹配。用 `--model-name esm2_t33_650M_UR50D`
   可以换大模型，但残基级张量宽 1280、显存与时间都会上去，Colab 免费档不建议。

4. **聚类工具回退**
   默认 `auto`：CD-HIT → MMseqs2 → 内置 k-mer。Kaggle 官方镜像无 sudo，不一定有 CD-HIT；
   k-mer 回退在 40% 一致性下只是近似（代码里 k=3、containment≥0.10）。
   **论文里必须写明实际用的工具与参数**，`dataset_summary.json.cluster_method` 会记录。
   严谨做法：本地跑 CD-HIT 生成 `clusters.tsv`，再 `--cluster-method precomputed --cluster-table ...`。

5. **外部集与 dev/test 同源的肽**
   不删除，单独放进 `split=external_homolog`，不计入 D11 主指标。`dataset_summary.json.external_homolog_overlap`
   给出数量，报告第 1 节会显示。这比“悄悄丢掉”更可审计。

6. **scrambled 与正样本同簇**
   打乱序列保持组成不变，必然与母序列落在同一同源簇。这是**特性不是 bug**：它检验模型是否只学到了组成。
   因此 `train/val/test` 的簇完整性检查只在可训练层 + 三切分之间做（见 `test_no_cluster_straddles_dev_or_test`）。

7. **D12–D14 未实现**
   AD 元数据核对、reads 回贴（cAMP_nt）、DESeq2 差异分析是独立工作量，依赖你下载的 SRA 数据。
   本流水线只提供 `D1` 模板与报告占位，避免“模型分数 = 表达量”的误读。

---

## 4. 复现一次“可引用”的结果需要做的事

1. 下载 4 大 AMP 库 + UniProt 阴性背景 + AMPSphere 100 条体外测试肽，写好 `sources.yaml`；
2. 在**有 CD-HIT 的机器**上跑 step1（或提供 `clusters.tsv`）；
3. GPU 上跑 step2（`fair-esm`）、step3（`M0_RF,M0_HGB,M0_CNN_BiGRU,M1,M2,M3,M3_NOPHYS`，5 seeds × 5 folds）；
4. 检查 `manuscript/D10_evaluation_report.md` 的 **Mandatory caveats**：
   - 有没有出现 `MOCK encoder`？（有 → 结果作废）
   - `cluster_method` 是不是 `kmer_fallback`？（是 → 换机器重跑 step1）
   - 测试集阳性是否 ≥100？（不足 → CI 会宽，如实报告）
   - M3 vs M3_NOPHYS/M2 的 MCC 区间是否跨 0 / 落在等价界值内？（是 → **不要**宣称理化分支有增益）
5. 用 `D15_input_sha256.tsv` 校验交付一致性，再把 D10/D11 的数字搬进论文表格。

---

## 5. 代码质量自检

```bash
python -m unittest discover -s tests -v     # 48 个用例：公式、切分、统计、端到端
python -m dualamp_lite demo --workdir /tmp/x  # 全链路（产物 + 报告 + 指纹）
python -m dualamp_lite check                  # 环境/GPU/工具自检
```

单测覆盖的关键不变量：

* Aliphatic Index / Boman Index 的固定来源与符号约定；
* 电荷–pH 曲线在 pI 处过零、Asp/Glu 在 pH 7.4 为负；
* AAC 每行和为 100（线性约束存在）；
* 同源簇不跨 train/val/test；
* 掩码均值只统计真实残基；
* DeLong 在完全相同预测上 p=1；
* Bootstrap CI 覆盖点估计；
* 端到端产出的指标都在 [0,1]、检查点可重载、报告一定包含“MOCK encoder”警示。
