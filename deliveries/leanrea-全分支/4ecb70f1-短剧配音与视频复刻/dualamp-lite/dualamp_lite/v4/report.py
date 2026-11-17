"""Stage 10 - regenerate the Chinese evaluation report from raw result files.

Nothing in the report is typed by hand: every number is read from
``results/<run_id>/*.csv`` or ``runs/<run_id>`` so that a re-run of the
evaluation stage reproduces the document byte-for-byte (apart from timestamps).
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Paths


DELIVERABLES = (
    ("D1", "环境与配置冻结", ["environment/environment.yml", "environment/requirements.lock", "environment/environment_info.txt"]),
    ("D2", "原始数据来源登记（含 SHA256）", ["data/manifests/sources_manifest.json"]),
    ("D3", "清洗后主表 dataset_master.tsv", ["data/dataset_master.tsv"]),
    ("D4", "排除记录与标签审计", ["data/excluded_records.tsv", "data/label_audit.csv"]),
    ("D5", "Development / 内部测试固定划分", ["data/splits/development.csv", "data/splits/internal_test.csv"]),
    ("D6", "5 个种子 × 5 折划分表", ["data/splits/folds_seed_11.csv"]),
    ("D7", "32 维理化特征矩阵", ["features/physchem.npz"]),
    ("D8", "feature_schema.json v1.0", ["features/feature_schema.json"]),
    ("D9", "ESM-2 残基/均值特征缓存", ["features/esm/development.npz", "features/feature_meta.json"]),
    ("D10", "基线模型结果（RF / HGB）", ["results/{run_id}/cv_runs.csv"]),
    ("D11", "25 次交叉验证逐次归档", ["runs/{run_id}"]),
    ("D12", "交叉验证 Mean±SD 汇总", ["results/{run_id}/cv_summary.csv"]),
    ("D13", "最终 5 种子权重与集成配方", ["final_models/{run_id}/manifest.json"]),
    ("D14", "内部测试指标（5 种子 + 集成）", ["results/{run_id}/internal_test_metrics.csv", "results/{run_id}/internal_test_summary.csv"]),
    ("D15", "统计比较（DeLong / 配对 bootstrap / BH-FDR）", ["results/{run_id}/comparisons.csv", "results/{run_id}/ensemble_ci.csv"]),
    ("D16", "挑战集与细菌亚组", ["results/{run_id}/challenge_sets.csv", "results/{run_id}/subgroup_metrics.csv"]),
    ("D17", "概率校准（Dev 拟合，Test 应用）", ["results/{run_id}/calibration_metrics.csv", "results/{run_id}/calibration_bins.csv"]),
    ("D18", "复现性测试报告", ["results/{run_id}/reproducibility_report.json"]),
    ("D19", "全量输入/权重/配置 SHA256 清单", ["SHA256"]),
    ("D20", "推理程序 + 示例 FASTA + 模型卡", ["export/inference.py", "export/example.fasta", "export/MODEL_CARD.md"]),
)


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "—"
    try:
        value = float(value)
    except Exception:
        return str(value)
    if not np.isfinite(value):
        return "—"
    return f"{value:.{digits}f}"


def _table(df: pd.DataFrame, columns: list[str] | None = None, digits: int = 3) -> str:
    if df is None or df.empty:
        return "_（无数据）_\n"
    df = df.copy()
    if columns:
        df = df[[c for c in columns if c in df.columns]]
    header = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join(["---"] * len(df.columns)) + "|"
    rows = []
    for _, row in df.iterrows():
        cells = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                cells.append(_fmt(value, digits))
            else:
                cells.append(str(value))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *rows]) + "\n"


def _read(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def create_figures(paths: Paths, run_id: str) -> list[Path]:
    """ROC and PR curves of the ensembles on the internal test."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import precision_recall_curve, roc_curve

    out_dir = paths.results / run_id / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    created = []
    path = paths.final_models / run_id / "ensemble_internal_test.csv"
    if not path.exists():
        return created
    df = pd.read_csv(path)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    for model, grp in df.groupby("model"):
        fpr, tpr, _ = roc_curve(grp["y_true"], grp["prob"])
        ax.plot(fpr, tpr, label=model)
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("Internal test ROC (ensemble)")
    ax.legend(frameon=False)
    fig.tight_layout()
    roc_path = out_dir / "D14_roc_ensemble.png"
    fig.savefig(roc_path, dpi=150)
    plt.close(fig)
    created.append(roc_path)

    fig, ax = plt.subplots(figsize=(4.5, 4))
    for model, grp in df.groupby("model"):
        precision, recall, _ = precision_recall_curve(grp["y_true"], grp["prob"])
        ax.plot(recall, precision, label=model)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Internal test PR (ensemble)")
    ax.legend(frameon=False)
    fig.tight_layout()
    pr_path = out_dir / "D14_pr_ensemble.png"
    fig.savefig(pr_path, dpi=150)
    plt.close(fig)
    created.append(pr_path)
    return created


def build_report(cfg, paths: Paths, run_id: str, logger=None) -> Path:
    results = paths.results / run_id
    meta = json.loads((paths.features / "feature_meta.json").read_text()) if (paths.features / "feature_meta.json").exists() else {}
    split_manifest = json.loads((paths.data / "manifests" / "split_manifest.json").read_text()) if (paths.data / "manifests" / "split_manifest.json").exists() else {}
    test_metrics = _read(results / "internal_test_metrics.csv")
    test_summary = _read(results / "internal_test_summary.csv")
    cv_summary = _read(results / "cv_summary.csv")
    comparisons = _read(results / "comparisons.csv")
    ci = _read(results / "ensemble_ci.csv")
    challenge = _read(results / "challenge_sets.csv")
    subgroup = _read(results / "subgroup_metrics.csv")
    calibration = _read(results / "calibration_metrics.csv")
    repr_report = results / "reproducibility_report.json"
    repro = json.loads(repr_report.read_text()) if repr_report.exists() else None
    env_info = json.loads((paths.environment / "environment_info.json").read_text()) if (paths.environment / "environment_info.json").exists() else {}

    lag = meta.get("backend") == "mock"
    demo = bool(cfg.demo_mode)

    lines: list[str] = []
    lines.append("# DualAMP-Lite 可复现模型全流程 V1.0 — 评估报告\n")
    lines.append(f"- run_id：`{run_id}`")
    lines.append(f"- 生成时间：{_dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- 特征版本：`{meta.get('schema_version', 'v1.0')}`（32 维，SHA256 `{(meta.get('schema_sha256') or '')[:16]}…`）")
    lines.append(f"- ESM 后端：`{meta.get('backend', 'unknown')}`" + ("（**mock 占位编码器**）" if lag else f"（{meta.get('model', '')}，第 {meta.get('repr_layer')} 层）"))
    lines.append(f"- 划分：dev {split_manifest.get('dev_fraction', 0.8):.0%} / 内部测试 {1 - split_manifest.get('dev_fraction', 0.8):.0%}，聚类方法 `{split_manifest.get('cluster_method', 'unknown')}`，split_seed {split_manifest.get('split_seed')}")
    lines.append(f"- 训练：{len(cfg.train.models)} 个模型 × {len(cfg.train.seeds)} 个种子 × {cfg.train.folds} 折 = {len(cfg.train.models) * len(cfg.train.seeds) * cfg.train.folds} 次交叉验证；最终 {len(cfg.train.models)} × {len(cfg.train.seeds)} 次全 Development 重训 + 均值概率集成")
    lines.append("")

    if lag or demo:
        lines.append("> **结果不可引用声明**")
        lines.append("> ")
        if lag:
            lines.append("> 本次运行使用 **mock 编码器**（确定性哈希占位向量），不具备 ESM-2 语义；")
        if demo:
            lines.append("> 训练数据为 **合成演示数据**（`--demo`），不是任何真实 AMP 数据库。")
        lines.append("> 因此下表的 AUROC/AUPRC 等数值仅用于验证“流程是否跑通”，**不得写入论文、不得对外汇报**。真实数值必须在 Kaggle/Colab 上以 `--backend fair-esm` 与真实数据重跑后生成。")
        lines.append("")

    lines.append("## 1. 流程与交付物状态（D1–D20）\n")
    status_rows = []
    for code, name, files in DELIVERABLES:
        resolved = [f.format(run_id=run_id) for f in files]
        present = [f for f in resolved if (paths.root / f).exists()]
        status = "ok" if len(present) == len(resolved) else ("partial" if present else "missing")
        status_rows.append({"交付物": f"{code} {name}", "状态": status, "路径": "<br>".join(resolved)})
    lines.append(_table(pd.DataFrame(status_rows)))
    lines.append("")

    lines.append("## 2. 数据与划分\n")
    counts = split_manifest.get("counts", {})
    count_rows = pd.DataFrame([{"split": k, "n": v} for k, v in counts.items()])
    lines.append(_table(count_rows))
    qc_rows = pd.DataFrame(split_manifest.get("qc", []))
    if not qc_rows.empty:
        lines.append("\n**划分质量检查（P0 全过才允许训练）**\n")
        lines.append(_table(qc_rows[["check", "level", "passed", "detail"]]))
    lines.append("")

    lines.append("## 3. 32 维特征与共线性\n")
    lines.append(f"- 特征数：{len(meta.get('feature_names', []))}，缺失值策略：`error`，标准化：`StandardScaler`（每折仅用训练部分拟合）")
    lines.append(f"- 相关系数 |r| ≥ {cfg.features.redundancy_threshold} 的特征对：{meta.get('redundant_pairs', '—')} 对（明细 `features/physchem_redundancy.csv`）")
    lines.append("- 已记录的共线性：AAC 20 列和为 1；instability 与其 >40 阈值标志同一变量（标志已删除）；MW 与 Length 仿射相关；阳离子比例与净电荷强相关。")
    lines.append("")

    lines.append("## 4. 25 次交叉验证（Development OOF）\n")
    if cv_summary is not None:
        pivot = cv_summary.pivot_table(index="model", columns="metric", values="mean")
        sd = cv_summary.pivot_table(index="model", columns="metric", values="sd")
        display = pd.DataFrame(index=pivot.index)
        for metric in ("auroc", "auprc", "mcc", "balanced_accuracy"):
            if metric in pivot:
                display[metric] = [f"{_fmt(pivot.loc[i, metric])} ± {_fmt(sd.loc[i, metric])}" for i in pivot.index]
        display = display.reset_index()
        lines.append(_table(display))
    lines.append("\n阈值与集成规则：每个种子的阈值来自其 Development OOF（MCC 规则）；集成阈值 = 各种子 OOF 概率按序列取均值后再按 MCC 规则确定，内部测试只做一次 transform 与打分。\n")
    lines.append("\n说明：25 次运行**不是 25 个独立样本**。汇总是“每种子 OOF 向量”的 Mean ± SD（n = 5），逐次原始值见 `results/<run_id>/cv_runs.csv`。\n")

    lines.append("## 5. 内部测试集（只触碰一次）\n")
    if test_metrics is not None:
        ens = test_metrics[test_metrics["seed"].astype(str) == "mean"]
        lines.append("**集成模型（5 种子均值概率）**\n")
        lines.append(_table(ens, ["model", "n", "n_pos", "threshold", "auroc", "auprc", "mcc", "balanced_accuracy", "sensitivity", "specificity", "f1", "brier", "ece"]))
        per_seed = test_metrics[test_metrics["seed"].astype(str) != "mean"]
        lines.append("\n**5 个种子逐一结果（不允许只报最优种子）**\n")
        lines.append(_table(per_seed, ["model", "seed", "threshold", "auroc", "auprc", "mcc", "balanced_accuracy", "sensitivity", "specificity"]))
    if test_summary is not None:
        lines.append("\n**跨种子 Mean ± SD**\n")
        pivot = test_summary.pivot_table(index="model", columns="metric", values="mean")
        sd = test_summary.pivot_table(index="model", columns="metric", values="sd")
        display = pd.DataFrame(index=pivot.index)
        for metric in ("auroc", "auprc", "mcc", "balanced_accuracy"):
            if metric in pivot:
                display[metric] = [f"{_fmt(pivot.loc[i, metric])} ± {_fmt(sd.loc[i, metric])}" for i in pivot.index]
        lines.append(_table(display.reset_index()))
    if ci is not None:
        lines[-1] = lines[-1] + "\n"
        lines.append("**集成模型 95% 置信区间（按同源簇重采样 bootstrap）**\n")
        lines.append(_table(ci, ["model", "metric", "point", "ci_low", "ci_high", "n_boot_effective"]))
    lines.append("")

    lines.append("## 6. 统计比较\n")
    if comparisons is not None:
        lines.append(_table(comparisons, ["comparison", "metric", "delta", "ci_low", "ci_high", "p_value", "q_value", "significant", "test"], digits=4))
        lines.append("\nAUROC 差异用 DeLong（仅 AUROC）；MCC/AUPRC 差异用同源簇配对 bootstrap；p 值经 BH-FDR 校正。等价边界：MCC 差异 0.02。\n")
    else:
        lines.append("_（无比较结果）_\n")

    lines.append("## 7. 挑战集与细菌亚组\n")
    if challenge is not None:
        lines.append(_table(challenge, ["split", "model", "n", "threshold", "mean_prob", "frac_predicted_positive", "auroc", "auprc"]))
    lines.append("")
    if subgroup is not None:
        lines.append("**细菌来源阳性亚组（不单独建支路，仅分报告）**\n")
        lines.append(_table(subgroup, ["model", "subgroup", "n_pos", "n_neg", "auroc", "auprc", "mcc", "sensitivity", "specificity"]))
    lines.append("")

    lines.append("## 8. 概率校准（Dev 拟合，Test 应用）\n")
    if calibration is not None:
        lines.append(_table(calibration, ["model", "seed", "calibration", "auroc", "auprc", "mcc", "brier", "ece"], digits=4))
    lines.append("")

    lines.append("## 9. 复现性\n")
    if repro:
        lines.append(f"- 同种子两次运行一致（Test A）：{'通过' if repro.get('same_seed_identical') else '未通过'}")
        lines.append(f"- 5 个种子稳定性（Test B）：AUROC 均值 {_fmt(repro.get('seed_auroc_mean'))}，SD {_fmt(repro.get('seed_auroc_sd'))}")
        lines.append(f"- 说明：{repro.get('note', '')}")
    else:
        lines.append("_（尚未运行复现性测试：`run_pipeline.py --stage reproducibility`）_")
    lines.append("")

    lines.append("## 10. 环境\n")
    lines.append(f"- OS：{env_info.get('os')}")
    lines.append(f"- Python {env_info.get('python')}，torch {env_info.get('torch')}，CUDA {env_info.get('cuda_version')}，cuDNN {env_info.get('cudnn_version')}，GPU {env_info.get('gpu')}")
    lines.append(f"- numpy {env_info.get('numpy')}，pandas {env_info.get('pandas')}，scikit-learn {env_info.get('sklearn')}，Biopython {env_info.get('biopython')}，fair-esm {env_info.get('fair_esm')}")
    lines.append(f"- CD-HIT：{env_info.get('cd_hit')}；MMseqs2：{env_info.get('mmseqs')}")
    lines.append(f"- git：{env_info.get('git_branch')} @ {str(env_info.get('git_commit'))[:12]}（dirty={env_info.get('git_dirty')}）")
    lines.append("")

    lines.append("## 11. 限制与声明\n")
    lines.append("1. 25 次 CV 与 5 次最终训练用途不同，不得混谈，也不得把 25 次当作独立样本做显著性检验。")
    lines.append("2. 内部测试集只评分一次；阈值、校准、模型选择全部来自 Development。")
    lines.append("3. PyTorch 官方声明：跨版本、跨设备、不同 CPU/GPU 不保证逐位一致；本仓库只保证同环境同种子可复现。")
    lines.append("4. `StratifiedGroupKFold` 的分层是近似的（按簇分组优先于精确分层）。")
    lines.append("5. 若聚类回退到 k-mer，40%/80% 同源阈值只是“操作性”近似，须在方法学中写明。")
    lines.append("6. 外部验证（AMPSphere 100 条）与 AD 队列分析不在本阶段范围。")
    lines.append("")

    out = results / "D14_evaluation_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    if logger:
        logger.info("  report written: %s", out)
    return out
