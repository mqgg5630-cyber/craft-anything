# DualAMP-Lite V1.0 — 第三次审查（V4）落地说明

本文件逐条对应 `抗菌肽深度学习AMP模型全流程可行性审查_第三次审查_V4_2026-11-09_2355.docx`，
说明冻结项在代码中的确切位置、一键管线怎么跑、以及哪些地方是有意偏离或仍待真实数据。

> 代码入口：`run_pipeline.py`（V4 主线）
> 旧入口 `python -m dualamp_lite ...` 与 `dualamp_lite/{biophys,features,train,report}.py`
> 属于 V3 草稿，仅为历史单元测试保留，**不再参与 V4 结果**。

---

## 1. 六项冻结门槛的落地位置

| 冻结项 | 代码 | 产物 |
| --- | --- | --- |
| ① 32 维特征冻结 | `dualamp_lite/v4/schema.py` | `features/feature_schema.json`（v1.0）、`features/physchem.npz` |
| ② M1/M2/M3 统一 | `dualamp_lite/v4/models.py` | 每个 run 的 `config.yaml` + `metrics.json`（`n_params`） |
| ③ 标签/聚类/切分 | `v4/data.py`, `v4/split.py`, `v4/qc.py` | `data/dataset_master.tsv`, `data/splits/*.csv`, `data/manifests/split_manifest.json` |
| ④ ESM 提取 + 单元测试 | `v4/features.py`, `tests/test_esm_shape.py` 等 | `features/esm/*.npz`, `features/feature_meta.json` |
| ⑤ 环境与种子归档 | `v4/runs.py`, `run_pipeline.py` | `environment/*`, 每个 run 的 `rng_state.pt` |
| ⑥ 小规模复现测试 | `run_pipeline.py --stage reproducibility` | `results/<run_id>/reproducibility_report.json` |

## 2. 32 维冻结表（与 V4 §7 完全一致）

```
0-19  aac_A ... aac_Y        分数 [0,1]（不是百分数），手工实现，禁用 get_amino_acids_percent()
20    molecular_weight       Da（平均残基质量 + 18.01524）
21    net_charge_ph7_4       固定 pKa 表 + N/C 端
22    isoelectric_point      pH 单
23    gravy                  Kyte-Doolittle 均值
24    instability_index      Guruprasad（Bio.SeqUtils.ProtParam，逐条调用）
25    aromaticity            (F+W+Y)/L
26    hydrophobic_moment_alpha  100°，Eisenberg，窗口 11
27    hydrophobic_moment_beta   160°，Eisenberg，窗口 11
28    cationic_residue_ratio (K+R+H)/L
29    boman_index            平均 Radzicka-Wolfenden 转移自由能（kcal/mol）
30    aliphatic_index        X(A)+2.9X(V)+3.9[X(I)+X(L)]，摩尔百分数
31    sequence_length        L
```

- `feature_version: v1.0`；`scaling: StandardScaler`；`missing_value_policy: error`。
- **标准化只在折内训练集拟合**：`train.py` 每次 `train_fold` 新建 `StandardScaler().fit(train_pool.phys)`，
  随 checkpoint 一起保存（`scaler.joblib` + checkpoint 内的 `scaler_mean/scale`）；
  最终模型在**全部 Development** 上拟合一次，内部测试只 transform 一次。
- 已删除 V3 的 `unstable_flag / charge_count_diff / frac_de / frac_hydrophobic / frac_helix_forming`；
  共线性（AAC 和为 1、MW↔Length、净电荷↔阳离子比）写入 `feature_schema.json` 的
  `collinearity_notes`，并在 `features/physchem_redundancy.csv` 输出实际 |r|。

## 3. 模型（不可改名、不可改通道数）

```
M1: mean(480) -> Linear 128 + GELU ; phys(32) -> Linear 64 + GELU ; concat 192 -> Linear 64 -> GELU -> Dropout -> Linear 1
M2: residue(L,480) -> Linear 480->128 -> [Conv1d k=3,5,7 × 64, GELU] -> masked global max -> concat 192
      -> Linear 192->128 -> GELU -> Dropout -> Linear 128->64 -> GELU -> Dropout -> Linear 1
M3: M2 的 CNN 分支(128) + phys(32)->64 -> concat 192 -> Linear 192->64 -> GELU -> Dropout -> Linear 1
```

- M3 **没有任何额外全局池化**；`tests/test_model_forward.py::test_m3_has_no_extra_pooling_module` 会失败即报警。
- 残基支路在卷积前用 mask 把 padding 置零（`ResidueBranch.forward`），因此 padding 内容不会污染边界卷积；
  `tests/test_mask_pooling.py` 用「把 padding 改成 1e3，logits 必须逐位相同」验证。
- Cross-Attention / Gated Fusion / LoRA 未实现（V4 §9 明确移出范围）。

## 4. 数据与切分

- 四类数据：`general_amp + bacterial_amp`（阳性，细菌来源只作为亚组报告，不单独建支路）、
  `negative_background`（弱负样本，进入主训练）、`hard_negative`（默认**只做挑战集**，
  由 `dataset.hard_negative_in_training: false` 控制）、`scrambled`（只做挑战集，永不作为生物负样本）。
- 标签来源：由清单里的 `layer` 决定（`_enforce_layer_labels`），**不从 FASTA header 猜**，
  避免 V3 的“记录号含 1 被判为阳性”这类错误；`external` 用清单 `label`/`label_column`。
- 切分：80/20，按 `identity_cluster` 分组，`split_seed: 20261109`；
  聚类优先 CD-HIT（`-c 0.80 -aL 0.80`）→ MMseqs2 → 内置 k-mer 回退，实际方法写入 manifest。
- 5 折：`StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)`，每个种子一份
  `data/splits/folds_seed_<seed>.csv`；**分层是近似的**（已在报告“限制”里写明）。
- 自动断言（`v4/qc.py`，P0 失败即中止）：无重复序列、无簇泄漏、无 `parent_id` 泄漏、
  无 scrambled 父序列泄漏、每折两类都有、长度窗口、特征有限且维度 = 32。

## 5. 25 次 CV + 5 次终测

```
runs/<run_id>/<MODEL>/seed_<s>/fold_<f>/
    config.yaml  best_model.pt  last_model.pt  train_log.csv
    predictions.csv  metrics.json  environment.txt  rng_state.pt  scaler.joblib
runs/<run_id>/<MODEL>/seed_<s>/oof_predictions.csv  oof_metrics.json
final_models/<run_id>/<MODEL>/seed_<s>/model.pt  predictions_<split>.csv
final_models/<run_id>/ensemble_<split>.csv
```

- 5 种子 `[11,23,37,53,71]` × 5 折 = 25 次/模型；M1/M2/M3 用**同一套折**（折只由 seed 决定）。
- 训练参数冻结：AdamW、lr 3e-4、wd 1e-4、batch 32、dropout 0.3、grad clip 1.0、
  最多 100 epoch、patience 10、主指标 AUPRC、阈值取自 Development OOF（MCC 规则）。
- 最终阶段：在**全部 Development** 上按每个 (模型, 种子) 重训（epoch 取该模型该种子 CV 的
  best_epoch 中位数），5 个权重全部保存，测试集只评分一次，输出 5 个种子指标 +
  Mean/SD + **均值概率集成**；不挑最优种子。
- 25 次与 5 次用途不同：CV 汇总以**每种子 OOF 向量**为单位（`cv_summary.csv`，n=5），
  不把 25 次当独立样本。

## 6. 统计与校准

- AUROC 差异：DeLong（仅 AUROC）；MCC/AUPRC 差异：**同源簇配对 bootstrap**；
  多比较 BH-FDR（`comparisons.csv` 的 `q_value`）。
- CI：按 `identity_cluster` 重采样的 percentile bootstrap（`ensemble_ci.csv`）。
- 校准：Platt（logistic）**只在 Development OOF 上拟合**，再应用到内部测试
  （`calibration_metrics.csv`、`calibration_bins.csv`），校准不改变排序指标。
- AUPRC 必须与测试集阳性率一起读（报告表格里给出 `n_pos`）。

## 7. 一键管线

```bash
# 全流程（真实数据 + 官方 ESM-2）
python run_pipeline.py --stage all \
    --manifest configs/sources.yaml \
    --backend fair-esm --weights-dir cache/weights \
    --workdir 2026-11-09_DualAMP-Lite

# 只跑某个阶段（每次调用都会新建 run_id，绝不覆盖历史）
python run_pipeline.py --stage split   --workdir ...
python run_pipeline.py --stage cross_validation --run-id 20261110_012214

# 合成数据 + mock 编码器的通流程自检（数值不可引用）
python run_pipeline.py --stage all --demo --epochs 20 --workdir demo_run
```

阶段：`env, audit, dataset, split, features, baseline, cross_validation,
final_train, evaluation, reproducibility, export, hash, all`。

失败时保留日志与半成品（`logs/pipeline_<run_id>.log`），不会写 `complete: true`。

## 8. 交付物 D1–D20

见 `dualamp_lite/v4/report.py::DELIVERABLES`；报告第 1 节自动列出每项 `ok/partial/missing`。
`D19` 的 `SHA256/manifest_<run_id>.tsv` 覆盖 raw/data/features/environment/runs/results/
final_models 以及 `dualamp_lite/v4/*.py` 与 `configs/*.yaml`。

## 9. 复现性

- 进程启动前设置 `PYTHONHASHSEED`、`CUBLAS_WORKSPACE_CONFIG=:4096:8`
  （`run_pipeline.py` 顶部，早于 torch 导入）；`torch.use_deterministic_algorithms(True)`、
  cudnn deterministic、DataLoader `generator` + `worker_init_fn`。
- 每次 run 保存 `rng_state.pt`（python/numpy/torch/cuda）。
- Test A（同种子两次逐位一致）：`--stage reproducibility`，阈值 1e-6。
- Test B（5 种子稳定性）：从 `cv_oof_metrics.csv` 汇总 AUROC 的 Mean/SD。
- 结论边界：**同环境同种子可复现**；跨 PyTorch 版本/跨设备不保证逐位一致（官方声明）。

## 10. 与 V4 的有意偏离（必须在论文中如实写明）

1. **特征缓存格式**：V4 附录建议每条序列一个 `.pt`；这里按 split 存一个 `.npz`
   （`ids/residue/mean/mask/seq`）。数值与形状完全一致，只是 IO 更快，且由 SHA256 清单保证完整性。
2. **mock 编码器**：本沙箱无法下载 ESM-2 权重，`--backend auto` 在无权重时退化为
   `MockEncoder`（确定性哈希向量）。所有 mock 结果都带 `is_mock: true` 与醒目的不可引用声明，
   **不得进入论文**。真实结果必须在 Kaggle/Colab 上以 `--backend fair-esm` 重跑。
3. **XGBoost**：`requirements.txt` 未强制安装；未安装时基线只有 RF 与 HistGradientBoosting
   （`M0_HGB`），报告中会写明。需要严格 XGBoost 时安装 `xgboost` 并把
   `train.baselines` 改为 `[M0_RF, M0_XGB]`。
4. **CD-HIT/MMseqs2**：镜像里通常没有二进制；回退到 k-mer 聚类时，
   `cluster_method` 会写成 `kmer_fallback(k=4)`，同源阈值只是操作性近似。
5. **最终重训轮数**：无验证集，取该 (模型, 种子) 的 CV `best_epoch` 中位数；
   V4 未规定具体轮数，此处是一个明确、可复现的约定。
