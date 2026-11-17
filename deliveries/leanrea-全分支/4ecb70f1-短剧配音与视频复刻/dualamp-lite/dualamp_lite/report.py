"""D10/D11/D12 - turn the run artefacts into a report a reviewer can audit.

The report refuses to over-claim:

* every metric is printed with its CI and the caveat that it is descriptive;
* if the mock encoder or a k-mer cluster fallback was used, a banner says so;
* the M3-vs-M2/M3-nophys comparison is reported as "no measurable gain" whenever
  the paired interval straddles zero, instead of spinning it as a win;
* the deliverables checklist mirrors plan §6 (D1...D15).
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd

from .utils import describe_environment, read_json


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def _ci(row: dict, metric: str) -> str:
    lo, hi = row.get(f"{metric}_ci_low"), row.get(f"{metric}_ci_high")
    if lo is None or hi is None or not np.isfinite(lo) or not np.isfinite(hi):
        return ""
    return f" [{_fmt(lo, 2)}, {_fmt(hi, 2)}]"


def make_figures(paths, logger=None) -> list[str]:
    """ROC / PR curves for every model that saved scores (optional, matplotlib)."""

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import precision_recall_curve, roc_curve
    except Exception as exc:  # pragma: no cover - matplotlib is optional
        if logger:
            logger.info("figures skipped (%s)", exc)
        return []

    score_files = sorted(paths.model.glob("*_scores.npz"))
    if not score_files:
        return []
    produced: list[str] = []
    for kind in ("roc", "pr"):
        fig, ax = plt.subplots(figsize=(5.2, 4.4))
        for path in score_files:
            data = np.load(path)
            if "test_labels" not in data:
                continue
            y, s = data["test_labels"], data["test_ensemble"]
            if len(np.unique(y)) < 2:
                continue
            if kind == "roc":
                fpr, tpr, _ = roc_curve(y, s)
                ax.plot(fpr, tpr, lw=1.4, label=path.stem.replace("_scores", ""))
            else:
                precision, recall, _ = precision_recall_curve(y, s)
                ax.plot(recall, precision, lw=1.4, label=path.stem.replace("_scores", ""))
        ax.set_xlabel("False positive rate" if kind == "roc" else "Recall")
        ax.set_ylabel("True positive rate" if kind == "roc" else "Precision")
        ax.set_title("Independent test set" if kind == "roc" else "Independent test set")
        if kind == "roc":
            ax.plot([0, 1], [0, 1], ls=":", c="grey", lw=1)
        ax.legend(fontsize=7, frameon=False)
        fig.tight_layout()
        out = paths.figures / f"D10_{kind}_curve.png"
        fig.savefig(out, dpi=300)
        plt.close(fig)
        produced.append(out.name)
    return produced


def _dataset_section(paths) -> list[str]:
    summary_path = paths.dataset / "dataset_summary.json"
    if not summary_path.exists():
        return ["_dataset summary missing - run step 1_", ""]
    summary = read_json(summary_path)
    lines = [
        "## 1. Dataset (D2/D3)",
        "",
        f"- unique sequences: **{summary['n_sequences']}**",
        f"- homology clusters: **{summary['n_clusters']}** "
        f"(tool: `{summary['cluster_method']}`, identity {summary['cluster_identity']}, coverage {summary['cluster_coverage']})",
        f"- length window: {summary['min_len']}-{summary['max_len']} aa",
        "",
        "| layer | sequences |",
        "|---|---|",
    ]
    for layer, count in sorted(summary["layer_counts"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {layer} | {count} |")
    lines += ["", "| split | sequences | positives | negatives |", "|---|---|---|---|"]
    for split in ("train", "val", "dev", "test", "external", "external_homolog", "scrambled", "review"):
        n = summary["split_counts"].get(split, 0)
        pos = summary["split_positives"].get(split, 0)
        neg = summary["split_negatives"].get(split, 0)
        lines.append(f"| {split} | {n} | {pos} | {neg} |")
    dropped = summary.get("dropped_records", 0)
    if dropped:
        lines += ["", f"Dropped/flagged records: {dropped} - see `dataset/label_audit.csv` "
                      f"({summary.get('drop_reasons', {})})."]
    lines.append("")
    return lines


def _feature_section(paths) -> list[str]:
    if not paths.feature_meta.exists():
        return ["_feature metadata missing - run step 2_", ""]
    meta = read_json(paths.feature_meta)
    bio = meta["biophys"]
    lines = [
        "## 2. Features (D4)",
        "",
        f"- encoder: **{meta['backend']}** (`{meta['model_name']}`, layer {meta['repr_layer']}, "
        f"{meta['embed_dim']}-d)",
        f"- pooling: {meta['pooling']}",
        f"- biophysical block: {bio['n_features']} features "
        f"(scaler fitted on train only; {bio['redundant_pairs']} feature pairs with "
        f"|r| >= {bio['redundancy_threshold']})",
    ]
    for split, info in meta["splits"].items():
        if info.get("cached"):
            continue
        lines.append(
            f"- {split}: {info['n']} peptides x {info['max_len']} residues "
            f"({info['dtype']}, {info['seconds']} s)"
        )
    lines += ["", "See `features/biophys_correlation.csv` for the redundancy audit.", ""]
    return lines


def _metric_section(paths) -> list[str]:
    if not paths.metrics_table.exists():
        return ["_metrics missing - run step 3_", ""]
    df = pd.read_csv(paths.metrics_table)
    lines = [
        "## 3. Independent test set (D10)",
        "",
        "Point estimates on the frozen test split; thresholds were tuned on dev OOF "
        "predictions only. 95% CIs resample **homology clusters**, not peptides.",
        "",
        "| model | AUROC | AUROC 95% CI | AUPRC | MCC | sensitivity | specificity | F1 | AUROC across seeds |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for _, row in df.sort_values("auroc", ascending=False).iterrows():
        seed_sd = row.get("test_auroc_seed_sd")
        seed_txt = f"{_fmt(row.get('test_auroc_seed_mean'), 3)} ± {_fmt(seed_sd, 3)}" if pd.notna(seed_sd) else ""
        lines.append(
            f"| {row['model']} | {_fmt(row['auroc'])}{_ci(row, 'auroc')} | "
            f"{_fmt(row.get('auroc_delong_ci_low'), 2)}-{_fmt(row.get('auroc_delong_ci_high'), 2)} | "
            f"{_fmt(row['auprc'])} | {_fmt(row['mcc'])} | {_fmt(row['sensitivity'])} | "
            f"{_fmt(row['specificity'])} | {_fmt(row['f1'])} | {seed_txt} |"
        )
    lines += ["", "AUROC CIs in the dedicated column use the DeLong variance (plan §5: "
                  "DeLong is used for AUROC only).", ""]
    return lines


def _comparison_section(paths) -> list[str]:
    if not paths.ablation_table.exists():
        return []
    df = pd.read_csv(paths.ablation_table)
    if df.empty:
        return []
    lines = [
        "## 4. Ablation / paired comparisons (D9)",
        "",
        "AUROC: DeLong paired test. MCC/AUPRC: paired cluster bootstrap. "
        "q-values: Benjamini-Hochberg across all rows. `within_margin` uses the "
        "pre-set MCC equivalence margin - a non-significant p-value is **not** "
        "evidence of equivalence.",
        "",
        "| pair | metric | delta (A-B) | 95% CI | p | q | FDR-significant | within margin | conclusion |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for _, row in df.iterrows():
        ci = ""
        if pd.notna(row.get("ci_low")) and pd.notna(row.get("ci_high")):
            ci = f"[{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}]"
        lines.append(
            f"| {row['model_a']} vs {row['model_b']} | {row['metric']} | {_fmt(row['delta'])} | {ci} | "
            f"{_fmt(row.get('p_value'))} | {_fmt(row.get('q_value'))} | "
            f"{row.get('significant_fdr')} | {row.get('within_margin', '')} | "
            f"{row.get('conclusion') if isinstance(row.get('conclusion'), str) else ''} |"
        )
    lines.append("")
    return lines


def _external_section(paths) -> list[str]:
    path = paths.manuscript / "D11_external_validation.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    if df.empty:
        return []
    lines = [
        "## 5. External / challenge sets (D11)",
        "",
        "External data never participated in model selection or threshold tuning. "
        "The `scrambled` split is composition-matched noise: a model that calls it "
        "positive is fitting composition only, not sequence order.",
        "",
        "| split | model | n | mean score | fraction predicted positive | AUROC | MCC |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"| {row['split']} | {row['model']} | {int(row.get('n', 0))} | "
            f"{_fmt(row.get('mean_score'))} | {_fmt(row.get('frac_predicted_positive'))} | "
            f"{_fmt(row.get('auroc'))} | {_fmt(row.get('mcc'))} |"
        )
    lines.append("")
    return lines


def _honesty_section(paths, results: dict | None) -> list[str]:
    """Automatic, pre-registered interpretations - including the uncomfortable ones."""

    caveats: list[str] = []
    if paths.feature_meta.exists():
        meta = read_json(paths.feature_meta)
        if meta.get("backend") == "mock":
            caveats.append(
                "**MOCK encoder.** These numbers only prove that the pipeline runs. "
                "They are not evidence about antimicrobial peptides and must not be quoted."
            )
    if paths.dataset.joinpath("dataset_summary.json").exists():
        summary = read_json(paths.dataset / "dataset_summary.json")
        if str(summary.get("cluster_method", "")).startswith("kmer"):
            caveats.append(
                "Clustering fell back to k-mer containment because CD-HIT/MMseqs2 were not "
                "available. The homology blocking is approximate - re-run step 1 with CD-HIT "
                "before the manuscript is finalised."
            )
        if summary.get("split_positives", {}).get("test", 0) < 100:
            caveats.append(
                f"The test split has only {summary['split_positives'].get('test', 0)} positives; "
                "bootstrap intervals will be wide. Report them as they are - do not drop them."
            )
    if results and results.get("comparisons"):
        comps = results["comparisons"]
        gain = [
            c for c in comps
            if c["model_a"] == "M3" and c["model_b"] in ("M3_NOPHYS", "M2") and c["metric"] in ("mcc", "auroc")
        ]
        for c in gain:
            if c.get("within_margin"):
                caveats.append(
                    f"M3 vs {c['model_b']} ({c['metric']}): |delta| = {_fmt(abs(c['delta']))} is inside the "
                    f"pre-set margin {_fmt(c.get('equivalence_margin'))}. **Do not claim** the "
                    "biophysical branch or the residue-level CNN provides a meaningful gain."
                )
            elif c.get("ci_low") is not None and c.get("ci_high") is not None and \
                    float(c["ci_low"]) <= 0 <= float(c["ci_high"]):
                caveats.append(
                    f"M3 vs {c['model_b']} ({c['metric']}): the paired 95% CI includes zero - report as "
                    "'no measurable difference on this test set'."
                )
    caveats.append(
        "All metrics here concern peptide-level AMP classification. They do not "
        "demonstrate abundance differences between AD patients and controls; that "
        "requires the read-mapping and DESeq2 chain of plan §4.3 (D13/D14)."
    )
    caveats.append(
        "The AMPSphere external check must use the 100 experimentally tested peptides "
        "(79 active + 21 inactive); the 863,498 computationally discovered candidates are "
        "candidates, not labels."
    )
    lines = ["## 6. Mandatory caveats", ""]
    lines += [f"- {c}" for c in caveats]
    lines.append("")
    return lines


def _deliverable_checklist(paths) -> list[str]:
    checks = [
        ("D1 sample metadata table", paths.metadata_table, "template only - manual curation required"),
        ("D2 clean dataset", paths.dataset_all, ""),
        ("D3 train/val/test splits", paths.split_csv("test"), ""),
        ("D4 features", paths.split_features("train"), ""),
        ("D5 baselines", paths.model / "M0_RF_results.json", "RF / HGB / CNN-BiGRU"),
        ("D6 M1 weights", paths.model / "M1_seed1.pt", ""),
        ("D8 M3 weights", paths.model / "M3_seed1.pt", ""),
        ("D9 ablation", paths.ablation_table, ""),
        ("D10 test metrics", paths.metrics_table, ""),
        ("D11 external validation", paths.manuscript / "D11_external_validation.csv", ""),
        ("D15 file manifest", paths.file_manifest, ""),
    ]
    lines = ["## 7. Deliverable checklist (plan §6)", "", "| id | artifact | status | note |", "|---|---|---|---|"]
    for name, path, note in checks:
        lines.append(f"| {name} | `{path.relative_to(paths.root)}` | {'ok' if Path(path).exists() else 'missing'} | {note} |")
    lines.append("")
    return lines


def build_report(paths, logger=None, with_figures: bool = True) -> Path:
    results_path = paths.model / "train_summary.json"
    results = read_json(results_path) if results_path.exists() else None
    env = describe_environment()

    lines = [
        "# DualAMP-Lite: independent-test evaluation report",
        "",
        f"Generated {_dt.datetime.now().isoformat(timespec='seconds')} · "
        f"workdir `{paths.root}`",
        "",
        "Methodology follows the V3 plan: ESM-2 (layer 12) frozen features, masked mean "
        "pooling, multi-scale 1D-CNN, biophysical priors, Concat fusion (M3), cluster-based "
        "group split, DeLong/bootstrap statistics.",
        "",
        "## 0. Environment",
        "",
        f"- python {env['python']} · {env['platform']}",
        f"- CUDA: {env['cuda']} · GPU: {env['gpu']}",
        f"- packages: { {k: v for k, v in env['packages'].items() if v} }",
        "",
    ]
    lines += _dataset_section(paths)
    lines += _feature_section(paths)
    lines += _metric_section(paths)
    lines += _comparison_section(paths)
    lines += _external_section(paths)
    lines += _honesty_section(paths, results)
    lines += _deliverable_checklist(paths)

    if with_figures:
        figures = make_figures(paths, logger=logger)
        if figures:
            lines += ["## 8. Figures", ""] + [f"- `figures/{f}`" for f in figures] + [""]

    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if logger:
        logger.info("report written: %s", paths.report)
    return paths.report
