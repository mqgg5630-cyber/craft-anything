"""Stage 9 - statistics on the frozen internal test and the challenge sets.

Everything here is recomputed from files written by the training stages
(``runs/<run_id>`` and ``final_models/<run_id>``), so the report can be rebuilt
without touching a model. V4 rules honoured:

* the test is read once, after the five final seeds are trained;
* all five seeds are reported (mean + SD), plus the mean-probability ensemble;
* 25 CV runs are never treated as independent samples: the per-seed OOF vectors
  are the unit of the cross-validated summary;
* AUROC differences use DeLong; MCC / AUPRC differences use a paired bootstrap
  over homology clusters; p-values are BH-FDR adjusted;
* thresholds come from Development out-of-fold predictions only;
* calibration (Platt) is fitted on Development OOF only.
"""

from __future__ import annotations

import json
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from scipy.special import logit
from sklearn.metrics import average_precision_score, roc_auc_score

from ..evaluate import bh_fdr, binary_metrics, delong_test
from .config import Paths

METRICS = ("auroc", "auprc", "mcc", "balanced_accuracy", "sensitivity", "specificity", "f1", "precision", "accuracy")


# --------------------------------------------------------------------------- #
# metric helpers
# --------------------------------------------------------------------------- #


def metric_value(name: str, y: np.ndarray, scores: np.ndarray, threshold: float) -> float:
    """Fast metric evaluation used inside the bootstrap loops.

    Plain numpy counts: a 2000-iteration cluster bootstrap over several metrics
    must stay seconds, not minutes.
    """

    y = np.asarray(y).astype(bool)
    scores = np.asarray(scores, dtype=float)
    if name == "auroc":
        return float(roc_auc_score(y, scores)) if y.any() and (~y).any() else float("nan")
    if name == "auprc":
        return float(average_precision_score(y, scores)) if y.any() else float("nan")
    pred = scores >= threshold
    tp = int(np.count_nonzero(pred & y))
    fp = int(np.count_nonzero(pred & ~y))
    tn = int(np.count_nonzero(~pred & ~y))
    fn = int(np.count_nonzero(~pred & y))
    sens = tp / (tp + fn) if (tp + fn) else float("nan")
    spec = tn / (tn + fp) if (tn + fp) else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = 2 * precision * sens / (precision + sens) if (precision + sens) else 0.0
    accuracy = (tp + tn) / max(1, tp + tn + fp + fn)
    denom = np.sqrt(float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)))
    mcc = ((tp * tn - fp * fn) / denom) if denom > 0 else 0.0
    return {
        "mcc": float(mcc),
        "balanced_accuracy": 0.5 * (sens + spec) if np.isfinite(sens) and np.isfinite(spec) else float("nan"),
        "sensitivity": float(sens),
        "specificity": float(spec),
        "f1": float(f1),
        "precision": float(precision),
        "accuracy": float(accuracy),
    }.get(name, float("nan"))


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        if not mask.any():
            continue
        total += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    return float(total)


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def calibration_bins(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        rows.append(
            {
                "bin_low": round(float(lo), 3),
                "bin_high": round(float(hi), 3),
                "n": int(mask.sum()),
                "mean_prob": float(p[mask].mean()) if mask.any() else np.nan,
                "observed_rate": float(y[mask].mean()) if mask.any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def fit_platt(p_oof: np.ndarray, y_oof: np.ndarray) -> LogisticRegression:
    model = LogisticRegression(C=1e6, solver="lbfgs")
    model.fit(logit(np.clip(p_oof, 1e-6, 1 - 1e-6)).reshape(-1, 1), y_oof)
    return model


def apply_platt(model: LogisticRegression, p: np.ndarray) -> np.ndarray:
    return model.predict_proba(logit(np.clip(p, 1e-6, 1 - 1e-6)).reshape(-1, 1))[:, 1]


def cluster_bootstrap(
    y: np.ndarray,
    scores: np.ndarray,
    clusters: np.ndarray,
    threshold: float,
    metrics: Sequence[str] = METRICS,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 20261109,
) -> pd.DataFrame:
    unique = np.unique(clusters)
    index_by_cluster = [np.where(clusters == c)[0] for c in unique]
    rng = np.random.default_rng(seed)
    draws: dict[str, list[float]] = {m: [] for m in metrics}
    for _ in range(n_boot):
        pick = rng.integers(0, len(unique), size=len(unique))
        idx = np.concatenate([index_by_cluster[i] for i in pick])
        y_b = y[idx]
        if len(np.unique(y_b)) < 2:
            continue
        for metric in metrics:
            value = metric_value(metric, y_b, scores[idx], threshold)
            if np.isfinite(value):
                draws[metric].append(value)
    rows = []
    for metric in metrics:
        values = np.asarray(draws[metric])
        point = metric_value(metric, y, scores, threshold)
        if values.size < 50:
            lo = hi = float("nan")
        else:
            lo, hi = np.percentile(values, [100 * alpha / 2, 100 * (1 - alpha / 2)])
        rows.append(
            {
                "metric": metric,
                "point": point,
                "ci_low": float(lo),
                "ci_high": float(hi),
                "n_boot_effective": int(values.size),
            }
        )
    return pd.DataFrame(rows)


def paired_cluster_bootstrap(
    y: np.ndarray,
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    clusters: np.ndarray,
    metric: str,
    threshold_a: float,
    threshold_b: float,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict:
    unique = np.unique(clusters)
    index_by_cluster = [np.where(clusters == c)[0] for c in unique]
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(unique), size=len(unique))
        idx = np.concatenate([index_by_cluster[i] for i in pick])
        y_b = y[idx]
        if len(np.unique(y_b)) < 2:
            continue
        a = metric_value(metric, y_b, scores_a[idx], threshold_a)
        b = metric_value(metric, y_b, scores_b[idx], threshold_b)
        if np.isfinite(a) and np.isfinite(b):
            deltas.append(a - b)
    deltas = np.asarray(deltas)
    delta = metric_value(metric, y, scores_a, threshold_a) - metric_value(metric, y, scores_b, threshold_b)
    if deltas.size == 0:
        return {"metric": metric, "delta": float(delta), "ci_low": np.nan, "ci_high": np.nan, "p_value": np.nan}
    p = 2.0 * min(float((deltas <= 0).mean()), float((deltas >= 0).mean()))
    return {
        "metric": metric,
        "delta": float(delta),
        "ci_low": float(np.percentile(deltas, 100 * alpha / 2)),
        "ci_high": float(np.percentile(deltas, 100 * (1 - alpha / 2))),
        "p_value": float(min(1.0, p)),
        "n_boot_effective": int(deltas.size),
    }


# --------------------------------------------------------------------------- #
# stage
# --------------------------------------------------------------------------- #


def _load_predictions(paths: Paths, run_id: str, split: str) -> pd.DataFrame:
    rows = []
    root = paths.final_models / run_id
    for path in sorted(root.glob(f"*/seed_*/predictions_{split}.csv")):
        rows.append(pd.read_csv(path))
    if not rows:
        raise FileNotFoundError(f"no final predictions for split {split} under {root}")
    return pd.concat(rows, ignore_index=True)


def _load_ensemble(paths: Paths, run_id: str, split: str) -> pd.DataFrame | None:
    path = paths.final_models / run_id / f"ensemble_{split}.csv"
    return pd.read_csv(path) if path.exists() else None


def _split_meta(paths: Paths, split: str) -> pd.DataFrame:
    return pd.read_csv(paths.split_csv(split), keep_default_na=False)


def _oof_table(paths: Paths, run_id: str, model: str) -> pd.DataFrame | None:
    rows = []
    for path in sorted((paths.runs / run_id / model).glob("seed_*/oof_predictions.csv")):
        rows.append(pd.read_csv(path))
    return pd.concat(rows, ignore_index=True) if rows else None


def run_evaluation(cfg, paths: Paths, run_id: str, logger=None) -> dict:
    out_dir = paths.results / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    test = _load_predictions(paths, run_id, "internal_test")
    test_meta = _split_meta(paths, "internal_test")[["sequence_id", "identity_cluster", "has_bacterial_origin"]]
    test = test.merge(test_meta, on="sequence_id", how="left")
    y = test["y_true"].to_numpy()

    # ---- per-seed and ensemble test metrics -------------------------------
    rows = []
    calibrated_rows = []
    platt_store = {}
    for model in sorted(test["model"].unique()):
        model_df = test[test["model"] == model]
        oof = _oof_table(paths, run_id, model)
        ens = _load_ensemble(paths, run_id, "internal_test")
        ens = ens[ens["model"] == model]
        platt = None
        if oof is not None:
            oof_ens = oof.groupby("sequence_id", as_index=False).agg(y_true=("y_true", "first"), prob=("prob", "mean"))
            platt = fit_platt(oof_ens["prob"].to_numpy(), oof_ens["y_true"].to_numpy().astype(int))
            platt_store[model] = platt
        for seed, grp in model_df.groupby("seed"):
            threshold = float(grp["threshold"].iloc[0])
            row = {"model": model, "seed": seed, "split": "internal_test", "n": len(grp), "n_pos": int(grp["y_true"].sum()), "threshold": threshold}
            row.update(binary_metrics(grp["y_true"].to_numpy(), grp["prob"].to_numpy(), threshold))
            row["balanced_accuracy"] = 0.5 * (row["sensitivity"] + row["specificity"])
            row["brier"] = brier(grp["y_true"].to_numpy(), grp["prob"].to_numpy())
            row["ece"] = ece(grp["y_true"].to_numpy(), grp["prob"].to_numpy())
            rows.append(row)
            if platt is not None:
                calibrated = apply_platt(platt, grp["prob"].to_numpy())
                crow = {"model": model, "seed": seed, "calibration": "platt(dev OOF)"}
                cm = binary_metrics(grp["y_true"].to_numpy(), calibrated, threshold)
                crow.update({k: cm[k] for k in ("auroc", "auprc", "mcc", "sensitivity", "specificity", "f1")})
                crow["balanced_accuracy"] = 0.5 * (cm["sensitivity"] + cm["specificity"])
                crow["brier"] = brier(grp["y_true"].to_numpy(), calibrated)
                crow["ece"] = ece(grp["y_true"].to_numpy(), calibrated)
                calibrated_rows.append(crow)
        if ens is not None and len(ens):
            threshold = _ensemble_threshold(paths, run_id, model, cfg)
            row = {"model": f"{model}+ENSEMBLE", "seed": "mean", "split": "internal_test", "n": len(ens), "n_pos": int(ens["y_true"].sum()), "threshold": threshold}
            row.update(binary_metrics(ens["y_true"].to_numpy(), ens["prob"].to_numpy(), threshold))
            row["balanced_accuracy"] = 0.5 * (row["sensitivity"] + row["specificity"])
            row["brier"] = brier(ens["y_true"].to_numpy(), ens["prob"].to_numpy())
            row["ece"] = ece(ens["y_true"].to_numpy(), ens["prob"].to_numpy())
            rows.append(row)
    metrics_table = pd.DataFrame(rows)
    metrics_table.to_csv(out_dir / "internal_test_metrics.csv", index=False)
    if calibrated_rows:
        pd.DataFrame(calibrated_rows).to_csv(out_dir / "calibration_metrics.csv", index=False)

    # ---- mean / SD across seeds -------------------------------------------
    summary = []
    for model, grp in metrics_table[metrics_table["seed"] != "mean"].groupby("model"):
        for metric in ("auroc", "auprc", "mcc", "balanced_accuracy", "sensitivity", "specificity", "f1", "brier", "ece"):
            values = grp[metric].astype(float)
            summary.append(
                {
                    "model": model,
                    "metric": metric,
                    "n_seeds": len(values),
                    "mean": float(values.mean()),
                    "sd": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                    "min": float(values.min()),
                    "max": float(values.max()),
                    "values": ";".join(f"{v:.4f}" for v in values),
                }
            )
    pd.DataFrame(summary).to_csv(out_dir / "internal_test_summary.csv", index=False)

    # ---- CV summary (per-seed OOF is the unit) ----------------------------
    cv_rows = []
    for path in sorted((paths.runs / run_id).glob("*/seed_*/oof_metrics.json")):
        payload = json.loads(path.read_text())
        payload["model"] = path.parent.parent.name
        payload["seed"] = int(path.parent.name.split("_")[1])
        cv_rows.append(payload)
    cv = pd.DataFrame(cv_rows)
    if not cv.empty:
        cv.to_csv(out_dir / "cv_oof_metrics.csv", index=False)
        agg = []
        for model, grp in cv.groupby("model"):
            for metric in ("auroc", "auprc", "mcc", "balanced_accuracy", "sensitivity", "specificity"):
                values = grp[metric].astype(float)
                agg.append(
                    {
                        "model": model, "metric": metric, "n_seeds": len(values),
                        "mean": float(values.mean()),
                        "sd": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                        "min": float(values.min()), "max": float(values.max()),
                    }
                )
        pd.DataFrame(agg).to_csv(out_dir / "cv_summary.csv", index=False)

    # ---- calibration curve -------------------------------------------------
    ens_all = _load_ensemble(paths, run_id, "internal_test")
    calib_frames = []
    if ens_all is not None:
        for model, grp in ens_all.groupby("model"):
            frame = calibration_bins(grp["y_true"].to_numpy(), grp["prob"].to_numpy())
            frame["model"] = model
            calib_frames.append(frame)
        if calib_frames:
            pd.concat(calib_frames, ignore_index=True).to_csv(out_dir / "calibration_bins.csv", index=False)

    # ---- comparisons (ensemble vs baselines) ------------------------------
    comp_rows = []
    models = sorted(test["model"].unique())
    best = "M3" if "M3" in models else models[-1]
    comparisons = []
    for other in models:
        if other == best:
            continue
        comparisons += [(f"{best}+ENSEMBLE", f"{other}+ENSEMBLE"), (best, other)]
    clusters = test_meta.set_index("sequence_id")["identity_cluster"]
    for a, b in comparisons:
        a_name, b_name = a.replace("+ENSEMBLE", ""), b.replace("+ENSEMBLE", "")
        a_df = _load_ensemble(paths, run_id, "internal_test") if a.endswith("+ENSEMBLE") else test[test["model"] == a]
        b_df = _load_ensemble(paths, run_id, "internal_test") if b.endswith("+ENSEMBLE") else test[test["model"] == b]
        if a_df is None or b_df is None:
            continue
        a_df = a_df[a_df["model"] == a_name].sort_values("sequence_id")
        b_df = b_df[b_df["model"] == b_name].sort_values("sequence_id")
        if len(a_df) != len(b_df):
            continue
        y_common = a_df["y_true"].to_numpy()
        pa = a_df["prob"].to_numpy()
        pb = b_df["prob"].to_numpy()
        cl = clusters.reindex(a_df["sequence_id"]).to_numpy()
        ta = _ensemble_threshold(paths, run_id, a_name, cfg)
        tb = _ensemble_threshold(paths, run_id, b_name, cfg)
        dm = delong_test(y_common, pa, pb)
        comp_rows.append({"comparison": f"{a} vs {b}", "metric": "auroc", "delta": dm["auc_diff"], "ci_low": np.nan, "ci_high": np.nan, "p_value": dm["p_value"], "test": "DeLong"})
        for metric in ("mcc", "auprc"):
            boot = paired_cluster_bootstrap(y_common, pa, pb, cl, metric, ta, tb, n_boot=cfg.train.n_boot)
            comp_rows.append({"comparison": f"{a} vs {b}", "metric": metric, "delta": boot["delta"], "ci_low": boot["ci_low"], "ci_high": boot["ci_high"], "p_value": boot["p_value"], "test": "paired cluster bootstrap"})
    if comp_rows:
        comp = pd.DataFrame(comp_rows)
        adjusted = bh_fdr(comp["p_value"].tolist(), cfg.train.boot_alpha)
        comp["q_value"] = [a["q_value"] for a in adjusted]
        comp["significant"] = [a["significant"] for a in adjusted]
        comp["equivalence_margin_mcc"] = cfg.train.equivalence_margin_mcc
        comp.to_csv(out_dir / "comparisons.csv", index=False)

    # ---- bootstrap CI of the ensemble -------------------------------------
    ci_frames = []
    for model in models:
        ens = _load_ensemble(paths, run_id, "internal_test")
        if ens is None:
            continue
        ens = ens[ens["model"] == model]
        if not len(ens):
            continue
        cl = clusters.reindex(ens["sequence_id"]).to_numpy()
        th = _ensemble_threshold(paths, run_id, model, cfg)
        ci = cluster_bootstrap(ens["y_true"].to_numpy(), ens["prob"].to_numpy(), cl, th, n_boot=cfg.train.n_boot)
        ci["model"] = model
        ci_frames.append(ci)
    if ci_frames:
        pd.concat(ci_frames, ignore_index=True).to_csv(out_dir / "ensemble_ci.csv", index=False)

    # ---- subgroup: bacterial-origin positives ------------------------------
    sub_rows = []
    ens_all = _load_ensemble(paths, run_id, "internal_test")
    if ens_all is not None:
        for model, grp in ens_all.groupby("model"):
            merged = grp.merge(test_meta, on="sequence_id", how="left")
            pos_bact = merged[(merged["y_true"] == 1) & (merged["has_bacterial_origin"] == 1)]
            neg = merged[merged["y_true"] == 0]
            if len(pos_bact) and len(neg):
                subset = pd.concat([pos_bact, neg])
                th = _ensemble_threshold(paths, run_id, model, cfg)
                row = {"model": model, "subgroup": "bacterial_origin_positive_vs_all_negative", "n_pos": len(pos_bact), "n_neg": len(neg)}
                row.update(binary_metrics(subset["y_true"].to_numpy(), subset["prob"].to_numpy(), th))
                sub_rows.append(row)
            pos_other = merged[(merged["y_true"] == 1) & (merged["has_bacterial_origin"] == 0)]
            if len(pos_other) and len(neg):
                subset = pd.concat([pos_other, neg])
                th = _ensemble_threshold(paths, run_id, model, cfg)
                row = {"model": model, "subgroup": "general_positive_vs_all_negative", "n_pos": len(pos_other), "n_neg": len(neg)}
                row.update(binary_metrics(subset["y_true"].to_numpy(), subset["prob"].to_numpy(), th))
                sub_rows.append(row)
    if sub_rows:
        pd.DataFrame(sub_rows).to_csv(out_dir / "subgroup_metrics.csv", index=False)

    # ---- challenge sets ----------------------------------------------------
    challenge_rows = []
    for split in ("hard_negative_test", "scrambled_test", "external_test", "external_homolog"):
        if not paths.split_csv(split).exists():
            continue
        try:
            preds = _load_predictions(paths, run_id, split)
            ens = _load_ensemble(paths, run_id, split)
        except FileNotFoundError:
            continue
        for model in sorted(preds["model"].unique()):
            grp = preds[preds["model"] == model]
            th = _ensemble_threshold(paths, run_id, model, cfg)
            row = {
                "split": split,
                "model": f"{model}+ENSEMBLE",
                "n": len(grp),
                "threshold": th,
                "mean_prob": float(grp["prob"].mean()),
                "frac_predicted_positive": float((grp["prob"] >= th).mean()),
                "n_pos": int(grp["y_true"].sum()) if grp["y_true"].nunique() > 1 else int(grp["y_true"].sum()),
            }
            if grp["y_true"].nunique() > 1:
                row["auroc"] = float(roc_auc_score(grp["y_true"], grp["prob"]))
                row["auprc"] = float(average_precision_score(grp["y_true"], grp["prob"]))
            challenge_rows.append(row)
    if challenge_rows:
        pd.DataFrame(challenge_rows).to_csv(out_dir / "challenge_sets.csv", index=False)

    payload = {
        "run_id": run_id,
        "models": models,
        "n_test": int(test.loc[test["model"] == models[0], "sequence_id"].nunique()),
        "test_positive_rate": float(y.mean()),
        "files": sorted(p.name for p in out_dir.glob("*.csv")),
    }
    (out_dir / "evaluation_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if logger:
        ens_metrics = metrics_table[metrics_table["seed"] == "mean"]
        for _, row in ens_metrics.iterrows():
            logger.info(
                "  TEST %-14s AUROC=%.3f AUPRC=%.3f MCC=%.3f (n=%d, pos=%d)",
                row["model"], row["auroc"], row["auprc"], row["mcc"], row["n"], row["n_pos"],
            )
    return payload


def _ensemble_threshold(paths: Paths, run_id: str, model: str, cfg) -> float:
    """Threshold from Development OOF (mean of per-seed OOF probabilities)."""

    rows = []
    for path in sorted((paths.runs / run_id / model).glob("seed_*/oof_predictions.csv")):
        rows.append(pd.read_csv(path))
    if not rows:
        return 0.5
    oof = pd.concat(rows, ignore_index=True)
    per_seq = oof.groupby("sequence_id", as_index=False).agg(y_true=("y_true", "first"), prob=("prob", "mean"))
    from ..evaluate import best_threshold

    return float(best_threshold(per_seq["y_true"].to_numpy(), per_seq["prob"].to_numpy(), cfg.train.threshold_rule))
