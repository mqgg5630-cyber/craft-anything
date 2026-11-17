# DualAMP-Lite · 可复现模型全流程 V1.0（V4 冻结版）

> **本仓库当前主线 = 第三次审查（V4, 2026-11-09 23:55）冻结版。**
> 一键入口：`python run_pipeline.py --stage all --manifest configs/sources.yaml --backend fair-esm`。
> 32 维特征、M1/M2/M3 结构、5 种子 × 5 折 × 3 模型 = 25 次/模型 CV、5 次最终重训 + 均值概率集成、
> 环境锁 + SHA256 清单 + D1–D20 交付物，全部由管线自动产出。
>
> - 设计落地说明（逐条对应 V4 文档）：[`docs/V4_IMPLEMENTATION.md`](docs/V4_IMPLEMENTATION.md)
> - 通流程自检（合成数据 + mock 编码器，**数值不可引用**）：
>   `python run_pipeline.py --stage all --demo --epochs 20 --workdir demo_run`
> - 单元测试：`python -m unittest discover -s tests -t .`（共 87 个：V4 新增 11 个文件 + V3 历史 5 个文件）
>
> 以下几点必须如实写进论文：mock 编码器结果不可引用；CD-HIT 缺失时聚类回退为 k-mer；
> 25 次 CV 与 5 次终测用途不同、不可混谈；内部测试集只触碰一次；
> PyTorch 不保证跨版本/跨设备逐位一致。

---

## 附录：V3 计划的 Kaggle / Colab 可执行骨架（历史，仅用于对照）

把 `抗菌肽深度学习方案_三次审查修订与最终执行版_V3_20261109_2245.docx`（放在本仓库根目录）里的三个骨架脚本
（`step1_build_dataset.py` / `step2_extract_features.py` / `step3_train_and_eval.py`）落成**一条能跑通的流水线**，
并针对 Kaggle 免费 GPU（2×T4，30 h/周）与 Colab 免费 T4（16 GB，会话易断）做了适配：

| 计划要求 | 代码实现 | 是否可验证 |
|---|---|---|
| §4.1 五层数据（General/Bacterial/Negative/Hard-negative/Scrambled） | `dualamp_lite/dataset.py` | ✅ 单元测试 |
| §5 全部序列统一去重 + 同源聚类 + 分组切分 | `dataset.py`（CD-HIT / MMseqs2 / k-mer 回退） | ✅ 单元测试 |
| §3.3 生物物理特征（Aliphatic Index / Boman Index 已修正） | `dualamp_lite/biophys.py` | ✅ 单元测试（含公式核对） |
| §3.2 ESM-2 残基级 + Masked Mean Pooling | `dualamp_lite/features.py` | ✅ 单元测试（含掩码均值核对） |
| §3.2 M1 / M2 / M3 Concat（M4/M5 选做） | `dualamp_lite/models.py` | ✅ 单元测试（形状/参数量/检查点重载） |
| §5 DeLong + 按簇 Bootstrap + FDR + 等价界值 | `dualamp_lite/evaluate.py` | ✅ 单元测试 |
| §6 D1–D15 交付物 | `dualamp_lite/report.py` 自动生成 | ✅ 报告含交付物核对表 |

> 说明：本仓库不包含任何抗菌肽序列数据（授权/体积问题），也不替代计划里的 AD 宏基因组分析链（D13/D14，需你自己完成元数据核对与 reads 回贴）。这里提供的是**建模主线的可执行骨架 + 审计产物**。

---

## 1. 目录结构

```
dualamp-lite/
├── dualamp_lite/            # Python 包（无安装也可用，python -m 直接跑）
│   ├── dataset.py           # step1 清洗/去重/聚类/切分      -> D2 D3
│   ├── biophys.py           # 35 维生物物理特征（P0 公式已修正）
│   ├── features.py          # step2 ESM-2 特征 + 标准化        -> D4
│   ├── models.py            # M0-CNN-BiGRU / M1 / M2 / M3 / M4 / M5
│   ├── train.py             # step3 训练、消融、外部验证       -> D5–D11
│   ├── evaluate.py          # DeLong / Bootstrap / FDR / 等价界值
│   ├── report.py            # 报告 + 交付物核对表              -> D10 D15
│   ├── synth.py             # 合成 demo 数据（仅用于冒烟测试）
│   └── cli.py               # 统一入口
├── configs/sources_example.yaml  # 真实数据源清单模板（APD6/DRAMP/DBAASP/CAMPR4/UniProt/AMPSphere）
├── notebooks/               # Kaggle / Colab 一键笔记本
├── kaggle/                  # kernel-metadata.json + push 脚本
├── scripts/                 # 环境检查、跑全套的 shell 封装
├── tests/                   # 48 个单元测试（numpy/sklearn 即可跑，torch 可选）
└── docs/PLAN_MAPPING.md     # 计划章节 ↔ 代码/产物 对照，含所有已知偏差
```

输出统一落在 `--workdir`（默认 `./2026-11-09_DualAMP-Lite/`，符合计划 §8 的目录隔离要求）：

```
2026-11-09_DualAMP-Lite/
├── dataset/    dataset_all.csv/.fasta, splits/{train,val,dev,test,external,scrambled}.csv,
│               clusters.tsv, label_audit.csv, dataset_summary.json, D1_sample_metadata.csv
├── features/   train/val/test/external/scrambled_feat.npz, biophys_scaler.joblib,
│               biophys_correlation.csv, feature_meta.json
├── model/      <MODEL>_seed<k>.pt, <MODEL>_scores.npz, <MODEL>_results.json, train_summary.json
├── ablation/   D9_ablation.csv
├── manuscript/ D10_test_metrics.csv, D10_evaluation_report.md,
│               D11_external_validation.csv, D15_input_sha256.tsv
├── figures/    D10_roc_curve.png, D10_pr_curve.png（有 matplotlib 时）
└── logs/       每一步的日志
```

---

## 2. 三分钟冒烟测试（无需 GPU / 无需下载权重）

```bash
cd dualamp-lite
python3 -m venv .venv && . .venv/bin/activate        # 可选
pip install numpy pandas scipy scikit-learn biopython pyyaml joblib matplotlib
pip install torch --index-url https://download.pytorch.org/whl/cpu   # 或让镜像自带

python -m dualamp_lite check                          # 环境/GPU/CD-HIT 自检
python -m dualamp_lite demo  --workdir ./demo_run      # 合成数据全流程，约 3–6 分钟（CPU）
python -m unittest discover -s tests                   # 48 个单测，约 1 分钟
```

`demo` 用**合成序列 + mock 编码器**，只为验证代码路径：报告里会打上 `MOCK encoder` 横幅，
那些 AUC 一律不可引用。它的价值是：能在你排队等 GPU 之前，先在 CPU 上把整条链路跑通。

---

## 3. Kaggle 流程（推荐，2×T4，30 GPU h/周）

### 3.1 一次性准备

1. **上传数据**：把原始文件（含 `sources.yaml`）打包成一个 Kaggle Dataset（私有即可），
   例如 `yourname/dualamp-raw`。文件放在 Dataset 根目录或 `raw/` 子目录都行：

   ```bash
   cp kaggle/dataset-metadata.json dataset/   # 改 id / title
   kaggle datasets create -p dataset/ --dir-mode zip
   ```
2. **（可选）离线 ESM-2 权重**：如果不想开 Notebook 的 Internet，把 `esm2_t12_35M_UR50D.pt`
   也放进 Dataset（约 140 MB）；否则 Notebook 里 `pip install fair-esm` + 首次加载会自动下载。
3. **新建 Notebook** 并挂载上面的 Dataset。工作目录：

   | 用途 | 路径 |
   |---|---|
   | 只读输入（数据 / 权重） | `/kaggle/input/dualamp-raw/` |
   | 可写工作区（20 GB，随版本保存） | `/kaggle/working/DualAMP-Lite/` |
   | 会话时长上限 | 12 h（9 h 空闲会断） |
   | GPU 配额 | 30 h/周（2×T4 或 P100，按实际占用计；本流水线只用单卡，DDP 未实现） |

### 3.2 直接跑 Notebook

打开 `notebooks/DualAMP_Lite_Kaggle.ipynb`，改顶部两个变量（数据路径、是否离线权重），
**Run All**。它做四件事：装依赖 → `check` → 真实数据 `build/features/train/report` → 打印指标与产物清单。

### 3.3 或者用命令行（可在 Notebook 的 cell 里逐条跑）

```bash
export DUALAMP_WORKDIR=/kaggle/working/DualAMP-Lite
cd /kaggle/working/dualamp-lite          # 把本目录 clone/上传到这里

# 0) 依赖（--no-deps 保住镜像自带的 CUDA torch）
pip install fair-esm --no-deps
pip install biopython pyyaml -q

# 1) 数据：五层样本 -> 去重 -> 同源聚类 -> 分组切分
python -m dualamp_lite build \
  --manifest /kaggle/input/dualamp-raw/sources.yaml \
  --cluster-method auto            # 有 cd-hit 用 CD-HIT，没有自动回退 k-mer

# 2) 特征：ESM-2(t12_35M) 残基级 + Masked Mean Pooling + 35 维理化
python -m dualamp_lite features --backend fair-esm --batch-size 64
#   离线权重：--weights-dir /kaggle/input/dualamp-raw/esm2 --local-files-only

# 3) 训练 + 消融 + 独立测试 + Bootstrap
python -m dualamp_lite train \
  --models M0_RF,M0_HGB,M0_CNN_BiGRU,M1,M2,M3,M3_NOPHYS \
  --seeds 1,2,3,4,5 --folds 5 --epochs 60 --loss bce

# 4) 报告 + 文件指纹
python -m dualamp_lite report
```

时间预算（8 k 条肽、单卡 T4、上表的 7 个模型 × 5 seeds × 5 folds）：

| 步骤 | 预计 |
|---|---|
| `build`（CD-HIT 0.4/0.8） | 3–10 min |
| `features`（ESM-2 t12，8 k × ≤50 aa） | 2–5 min |
| `train`（6–7 个模型，含 5 seeds × 5 folds） | **60–120 min** |
| `report` | < 1 min |

一个 12 h 会话跑完绰绰有余；周配额 30 h 足够做 10 次以上的完整重跑。
加 `M4,M5` 或做 focal loss 网格搜索会到 3–4 h。

### 3.4 用 `kaggle kernels push` 无人值守跑

```bash
# kaggle/kernel-metadata.json 里把 dataset_sources 换成你的 dataset slug
python kaggle/push.py --id yourname/dualamp-lite-run          # 生成并推送
kaggle kernels status yourname/dualamp-lite-run
kaggle kernels output yourname/dualamp-lite-run -p ./kaggle_out   # 拉回产物
```

---

## 4. Colab 流程（T4 16 GB，会话随时会断 → 必须支持续跑）

核心差异是**持久化**：Colab 的 `/content` 会消失，产物必须放 Google Drive，且每步都要能续跑。

```python
from google.colab import drive
drive.mount('/content/drive')

WORK = '/content/drive/MyDrive/16_抗菌肽深度学习建模学习总结_2026-11-08/DualAMP-Lite'
DATA = '/content/drive/MyDrive/16_抗菌肽深度学习建模学习总结_2026-11-08/raw'
```

```bash
pip install -q fair-esm --no-deps && pip install -q biopython pyyaml
git clone --depth 1 -b arena/4ecb70f1-leanrea https://github.com/hukeying85-ux/leanrea /content/leanrea
cd /content/leanrea/dualamp-lite

python -m dualamp_lite build    --workdir "$WORK" --manifest "$DATA/sources.yaml" --cluster-method kmer
python -m dualamp_lite features --workdir "$WORK" --backend fair-esm --batch-size 64
python -m dualamp_lite train    --workdir "$WORK" --seeds 1,2,3
python -m dualamp_lite train    --workdir "$WORK" --seeds 4,5      # 断了就重跑这行
python -m dualamp_lite report   --workdir "$WORK"
```

续跑机制（默认开启）：

* `features`：`*_feat.npz` 已存在则跳过（`--force` 强制重算）；
* `train`：`<MODEL>_results.json` + `<MODEL>_scores.npz` 都在、且 `--seeds` 一致时，整个模型直接复用；
* 所以把模型拆成几批（先 M0/M1，再 M2/M3）最省时间，符合免费的 GPU 时段碎片化。

Colab 上 ESM-2 权重建议缓存到 Drive（`~/.cache/torch` 在会话结束后丢失）：

```bash
export TORCH_HOME="$WORK/cache/torch"
python -m dualamp_lite features --backend fair-esm --batch-size 64
```

完整可执行版本见 `notebooks/DualAMP_Lite_Colab.ipynb`（含 Drive 挂载、断线提示、单步重跑）。

---

## 5. 真实数据怎么放（`configs/sources_example.yaml`）

流水线**不自动下载**数据库（都要注册、且 URL 会变）。你下载一次，然后在 manifest 里声明列名：

| 层 | 来源 | 关键提醒（计划 §4.1） |
|---|---|---|
| General AMP | APD6、DRAMP 4.0、CAMPR4、DBAASP | 只保留**实验验证**记录；DRAMP 30 260 条含专利，不等于阳性数 |
| Bacterial AMP | BAGEL4 / antiSMASH / DRAMP 细菌来源 | V3 新增层，缓解“动物来源训练 → 肠道细菌筛选”的领域偏移 |
| Hard negative | DBAASP 实验无活性肽 | 记录 MIC/菌株/方法（自动写入 `label_audit.csv` 的元数据列） |
| Negative background | UniProt Swiss-Prot（非 AMP 注释）+ `fragment` 切片段 | 默认排除关键词 antimicrobial/bacteriocin/defensin |
| External | AMPSphere **100 条体外测试肽**（79 阳 + 21 阴） | 863 498 条计算候选**不能**当实验标签 |

```bash
python -m dualamp_lite build --manifest configs/sources.yaml --cluster-method cdhit
```

跑完先看三个文件，再决定要不要进 GPU：

1. `dataset/dataset_summary.json` —— 每层多少条、聚类工具、切分大小；
2. `dataset/label_audit.csv` —— 被丢弃/标签冲突/同源簇冲突的每一条理由；
3. `dataset/splits/test.csv` —— 冻结的独立测试集（阳性数 <100 时报告会自动加警告）。

**同源不泄漏的保证**：聚类在**全部序列**上做（含 external），`train/val/test` 按簇整体分配；
跨簇污染会直接把测试集变得过于乐观。外部集里与 dev/test 同簇的肽会被单独放进
`split=external_homolog`，不计入 D11 主指标（但仍保留，报告里写明数量）。

---

## 6. 模型与消融（对应计划 §3.2）

| 名字 | 结构 | 说明 |
|---|---|---|
| `M0_RF` / `M0_HGB` | 35 维理化 + 随机森林 / 直方图梯度提升 | 基准下限；装了 xgboost 可用 `M0_XGB` |
| `M0_LOGREG` | 理化 + 逻辑回归 | 最便宜的线性基线 |
| `M0_CNN_BiGRU` | 从零训练：Embedding → 多尺度 CNN → BiGRU → attention pool | 验证 ESM-2 先验是否必要 |
| `M1` | ESM-2 Masked Mean Pooling → MLP | 全局表征基线 |
| `M2` | ESM-2 残基级 → 多尺度 1D-CNN(k=3,5,7) → 128 | 验证残基级卷积的增益 |
| **`M3`** | M2 的 128 维 **Concat** 理化 MLP 的 64 维 = 192 → MLP | **主模型**（不使用有缺陷的单 Token Cross-Attention） |
| `M3_NOPHYS` | M3 去掉理化分支 | 与 M3 配对比较，检验理化先验是否真有贡献 |
| `M4` | 35 个特征 Token 对残基做**真**交叉注意力 | 选做；只在 M3 有增益后再上 |
| `M5` | Gated / FiLM 融合 | 选做 |

**评估协议（计划 §5 的三层结构）**

1. 开发集 = train + val：`StratifiedGroupKFold`（按同源簇分组）× 5 seeds，早停、选阈值、选超参都只在这里；
2. 独立测试集：每个模型在开发集重训后**只评估一次**，不调任何东西；
3. 外部集/打乱集：阈值冻结后直接套用，只报告，不参与选择。

统计口径与审查意见逐条对应：

* AUROC：**DeLong** 配对检验 + DeLong 置信区间；
* MCC / AUPRC：**按同源簇**的配对 Bootstrap（簇是重采样单位，不是单条肽、更不是 50 个折）；
* 所有点估计都给 95% CI；跨模型比较做 **Benjamini–Hochberg FDR**；
* 预设 **MCC 等价界值**（默认 0.02，`--equivalence-margin-mcc`），报告里直接写“无实质差异”，
  不会把 `p > 0.05` 说成“等效”。

报告 `manuscript/D10_evaluation_report.md` 的“Mandatory caveats”是**自动生成**的：mock 编码器、
k-mer 回退、测试集阳性不足、M3 相比 M2 的区间跨 0/落在等价界值内……这些都会自己写出来，
防止结果页被过度解读。

---

## 7. 交付物对照（计划 §6）

| ID | 产物 | 由谁生成 |
|---|---|---|
| D1 | `dataset/D1_sample_metadata.csv`（模板） | `build`（AD 三队列的元数据仍需你手工核对） |
| D2 | `dataset/dataset_all.csv/.fasta` + `label_audit.csv` | `build` |
| D3 | `dataset/splits/{train,val,dev,test}.csv` | `build` |
| D4 | `features/*_feat.npz`、`biophys_scaler.joblib`、`biophys_correlation.csv` | `features` |
| D5 | `model/M0_*_results.json` + `_scores.npz` | `train` |
| D6–D8 | `model/M1_seed*.pt`、`M2_seed*.pt`、`M3_seed*.pt` | `train` |
| D9 | `ablation/D9_ablation.csv` | `train` |
| D10 | `manuscript/D10_test_metrics.csv` + 报告 + `figures/` | `train` / `report` |
| D11 | `manuscript/D11_external_validation.csv` | `train` |
| D15 | `manuscript/D15_input_sha256.tsv` | `report` |
| D12–D14 | AD 队列元数据核对、reads 回贴、DESeq2 差异分析 | **不在本流水线**（见计划 §4.2/§4.3） |

---

## 8. 与计划的已知偏差（都在 `docs/PLAN_MAPPING.md` 里逐条说明）

1. **“32 维”理化特征实际是 35 维**：V3 表格自身 20+6+5+3=34，加上计划要求固定来源的 Boman Index（+1）= 35。
   按计划自己的 P1 原则（“不为凑 32 维而硬凑”），代码报告真实维度，并输出 `|r| ≥ 0.85` 的冗余对清单。
2. **Aliphatic Index 单独实现但未放进特征向量**：它与 AAC 高度共线，放进向量会重复计权；作为函数 + 单测保留，供正文引用。
3. **CD-HIT 不一定可用**：Kaggle 镜像没有 sudo、也不保证装 CD-HIT。默认 `auto` → CD-HIT → MMseqs2 → 内置 k-mer 回退。
   报告会自动标注“k-mer 回退”，提醒你换机器或本地跑 CD-HIT 后重跑 step1（可 `--cluster-method precomputed` 直接喂结果）。
4. **ESM-2 用 t12_35M**（计划指定），不是 650M——T4 显存与 30 h 周配额下这是正确取舍；换大模型改 `--model-name` 即可。
5. **AMPSphere 100 条体外测试集**只是流水线的“外部集”位；文件需你自己按原论文核对（79 阳 + 21 阴）。
6. **AD 差异分析（D12–D14）未实现**：那是元数据核对 + reads 回贴 + DESeq2 的独立工作，代码骨架里只留了 D1 模板与报告位置。

---

## 9. 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| `CUDA out of memory` | 降 `--batch-size`（64→32）；残基张量已存 float16，训练时按 batch 转 float32 |
| `fair-esm` 装完 torch 变了 / 冲突 | `pip install fair-esm --no-deps`，不要让它重装 CUDA torch |
| 第一次 `features` 卡在下载 | Kaggle 未开 Internet；改用 `--weights-dir /kaggle/input/...`，HF 后端可加 `--local-files-only` |
| `cd-hit: command not found` | 正常，自动回退 k-mer；要严格同源阻断就在有 cd-hit 的机器上跑 step1，或 `--cluster-method precomputed --cluster-table clusters.tsv` |
| Colab 断线后重跑很久 | 默认续跑；确认 `--seeds` 与上次一致，否则会重训（提示信息会写 “reusing”） |
| 测试集阳性太少（<100） | 报告会警告；不要为了“好看”去合并 train/test，宁可报告更宽的 CI |
| Drive 上训练极慢 | 先把 `features/*.npz` 拷到 `/content/work` 再训练，最后把产物同步回 Drive |
| 指标异常高（AUC>0.98） | 先查 `dataset_summary.json` 的聚类工具和 `label_audit.csv`：多半是同源泄漏或重复记录 |

---

## 10. 与 30 天计划的排期对应

| 计划阶段 | 用本流水线做什么 |
|---|---|
| 第 1 周 | 把 4 大库 + UniProt + AMPSphere 下载好 → 写 `sources.yaml` → `build` → 逐条看 `label_audit.csv` |
| 第 2 周 | `features`（ESM-2 + 理化）→ 先跑 `M0_RF/M0_HGB/M1` 建立基线，把 `D10_test_metrics.csv` 填起来 |
| 第 3 周 | 上 `M2/M3/M3_NOPHYS`，做消融；必要时试 `M4/M5`、focal loss（都在 dev 上选） |
| 第 4 周 | `report` 出稿 → 写第 3 章方法/结果 → 同步开始 D12 的 AD 元数据核对（与本流水线并行，不抢 GPU） |

---

## 11. 引用与致谢

方法学依据见计划 §3.5（ESM-2 + AMP 文献清单）。数据来源：APD6、DRAMP 4.0、DBAASP v3、CAMPR4、UniProt、AMPSphere。
代码按计划 §8 的命名/目录隔离规则组织；模型权重统一命名 `M*_seed*.pt`，不与 HierMetaAMP 系列混用。
