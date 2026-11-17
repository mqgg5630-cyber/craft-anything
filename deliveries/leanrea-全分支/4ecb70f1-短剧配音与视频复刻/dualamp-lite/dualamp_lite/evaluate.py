"""Metrics and statistics of plan §5 (P2 fixes).

Implements exactly what the review demanded:

* AUROC  -> DeLong paired test + DeLong confidence interval
* MCC    -> paired bootstrap (50 CV folds are *not* 50 independent observations)
* AUPRC  -> paired bootstrap
* all point estimates get cluster-aware bootstrap CIs, i.e. homology clusters -
  not individual peptides - are the resampling unit
* Benjamini-Hochberg FDR across the model comparisons
* an explicit equivalence margin, because p > 0.05 does not mean "equivalent"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
from scipy import stats
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

METRIC_NAMES = ("auroc", "auprc", "mcc", "f1", "sensitivity", "specificity", "accuracy", "precision")


# --------------------------------------------------------------------------- #
# point estimates
# --------------------------------------------------------------------------- #


def binary_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float = 0.5) -> dict:
    y_true = np.asarray(y_true).astype(int).ravel()
    scores = np.asarray(scores, dtype=float).ravel()
    pred = (scores >= threshold).astype(int)
    out = {
        "threshold": float(threshold),
        "n": int(len(y_true)),
        "n_pos": int(y_true.sum()),
    }
    if len(np.unique(y_true)) > 1:
        out["auroc"] = float(roc_auc_score(y_true, scores))
        out["auprc"] = float(average_precision_score(y_true, scores))
    else:
        out["auroc"] = float("nan")
        out["auprc"] = float("nan")
    out["mcc"] = float(matthews_corrcoef(y_true, pred)) if len(np.unique(pred)) > 1 or len(np.unique(y_true)) > 1 else 0.0
    out["f1"] = float(f1_score(y_true, pred, zero_division=0))
    out["precision"] = float(precision_score(y_true, pred, zero_division=0))
    out["sensitivity"] = float(recall_score(y_true, pred, zero_division=0))
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    out["specificity"] = float(tn / (tn + fp)) if (tn + fp) else float("nan")
    out["accuracy"] = float(accuracy_score(y_true, pred))
    out["tp"], out["fp"], out["tn"], out["fn"] = int(tp), int(fp), int(tn), int(fn)
    out["mean_score"] = float(scores.mean()) if len(scores) else float("nan")
    out["frac_predicted_positive"] = float(pred.mean()) if len(pred) else float("nan")
    return out


def best_threshold(y_true: np.ndarray, scores: np.ndarray, rule: str = "mcc") -> float:
    """Threshold chosen on out-of-fold dev predictions only (never on test)."""

    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    candidates = np.unique(np.round(np.concatenate([scores, [0.0, 0.5, 1.0]]), 6))
    best_t, best_score = 0.5, -np.inf
    for t in candidates:
        pred = (scores >= t).astype(int)
        if rule == "youden":
            tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
            sens = tp / (tp + fn) if (tp + fn) else 0.0
            spec = tn / (tn + fp) if (tn + fp) else 0.0
            score = sens + spec - 1
        else:
            score = matthews_corrcoef(y_true, pred) if len(np.unique(pred)) > 1 else -1.0
        if score > best_score:
            best_t, best_score = float(t), float(score)
    return best_t


# --------------------------------------------------------------------------- #
# DeLong (AUROC only - the review forbids using it for MCC)
# --------------------------------------------------------------------------- #


def _midrank(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    x_sorted = x[order]
    n = len(x)
    ranks_sorted = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and x_sorted[j + 1] == x_sorted[i]:
            j += 1
        rank = 0.5 * (i + j) + 1.0
        ranks_sorted[i : j + 1] = rank
        i = j + 1
    ranks = np.empty(n, dtype=float)
    ranks[order] = ranks_sorted
    return ranks


def _fast_delong(predictions: np.ndarray, n_pos: int) -> tuple[np.ndarray, np.ndarray]:
    """predictions: (k models, n samples) with positives first."""

    k, n = predictions.shape
    n_neg = n - n_pos
    pos, neg = predictions[:, :n_pos], predictions[:, n_pos:]
    tx = np.array([_midrank(row) for row in pos])
    ty = np.array([_midrank(row) for row in neg])
    tz = np.array([_midrank(row) for row in predictions])
    aucs = tz[:, :n_pos].sum(axis=1) / (n_pos * n_neg) - (n_pos + 1.0) / (2.0 * n_neg)
    v01 = (tz[:, :n_pos] - tx) / n_neg          # (k, n_pos)
    v10 = 1.0 - (tz[:, n_pos:] - ty) / n_pos    # (k, n_neg)
    sx = np.atleast_2d(np.cov(v01))
    sy = np.atleast_2d(np.cov(v10))
    covariance = sx / n_pos + sy / n_neg
    return aucs, covariance


def delong_test(y_true: np.ndarray, scores_a: np.ndarray, scores_b: np.ndarray) -> dict:
    """Paired DeLong test for two AUROCs on the *same* samples."""

    y_true = np.asarray(y_true).astype(int)
    n_pos = int(y_true.sum())
    if n_pos == 0 or n_pos == len(y_true):
        return {"auc_a": float("nan"), "auc_b": float("nan"), "z": float("nan"), "p_value": float("nan")}
    order = np.argsort(-y_true, kind="mergesort")  # positives first, stable
    predictions = np.vstack([np.asarray(scores_a, float), np.asarray(scores_b, float)])[:, order]
    aucs, covariance = _fast_delong(predictions, n_pos)
    contrast = np.array([[1.0, -1.0]])
    variance = float((contrast @ covariance @ contrast.T).squeeze())
    if variance <= 0:
        return {
            "auc_a": float(aucs[0]), "auc_b": float(aucs[1]), "auc_diff": 0.0,
            "z": 0.0, "p_value": 1.0, "se_diff": 0.0,
        }
    z = float(abs(aucs[0] - aucs[1]) / np.sqrt(max(variance, 1e-12)))
    p = float(2.0 * stats.norm.sf(z))
    return {
        "auc_a": float(aucs[0]),
        "auc_b": float(aucs[1]),
        "auc_diff": float(aucs[0] - aucs[1]),
        "z": z,
        "p_value": p,
        "se_diff": float(np.sqrt(variance)),
    }


def delong_ci(y_true: np.ndarray, scores: np.ndarray, alpha: float = 0.05) -> tuple[float, float, float]:
    y_true = np.asarray(y_true).astype(int)
    n_pos = int(y_true.sum())
    if n_pos in (0, len(y_true)):
        return float("nan"), float("nan"), float("nan")
    order = np.argsort(-y_true, kind="mergesort")
    predictions = np.asarray(scores, float)[order][None, :]
    aucs, covariance = _fast_delong(predictions, n_pos)
    se = float(np.sqrt(max(covariance[0, 0], 0.0)))
    z = float(stats.norm.ppf(1 - alpha / 2))
    return float(aucs[0]), float(max(0.0, aucs[0] - z * se)), float(min(1.0, aucs[0] + z * se))


# --------------------------------------------------------------------------- #
# cluster bootstrap
# --------------------------------------------------------------------------- #


def _metric_value(metric: str, y: np.ndarray, s: np.ndarray, threshold: float) -> float:
    if metric == "auroc":
        return float(roc_auc_score(y, s)) if len(np.unique(y)) > 1 else np.nan
    if metric == "auprc":
        return float(average_precision_score(y, s)) if len(np.unique(y)) > 1 else np.nan
    point = binary_metrics(y, s, threshold)
    return float(point[metric])


def cluster_bootstrap(
    y_true: np.ndarray,
    scores: np.ndarray,
    clusters: np.ndarray,
    threshold: float = 0.5,
    metrics: Sequence[str] = METRIC_NAMES,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict[str, dict]:
    """Percentile CIs resampling homology clusters (not individual peptides)."""

    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    clusters = np.asarray(clusters)
    unique = np.unique(clusters)
    rng = np.random.default_rng(seed)
    index_by_cluster = [np.where(clusters == c)[0] for c in unique]
    draws: dict[str, list[float]] = {m: [] for m in metrics}
    for _ in range(n_boot):
        pick = rng.integers(0, len(unique), size=len(unique))
        idx = np.concatenate([index_by_cluster[i] for i in pick])
        y_b, s_b = y_true[idx], scores[idx]
        if len(np.unique(y_b)) < 2:
            continue
        for metric in metrics:
            value = _metric_value(metric, y_b, s_b, threshold)
            if np.isfinite(value):
                draws[metric].append(value)
    point = binary_metrics(y_true, scores, threshold)
    out = {}
    for metric in metrics:
        values = np.asarray(draws[metric])
        if values.size < max(20, n_boot // 10):
            lo = hi = float("nan")
        else:
            lo, hi = np.percentile(values, [100 * alpha / 2, 100 * (1 - alpha / 2)])
        out[metric] = {
            "point": float(point.get(metric, np.nan)),
            "ci_low": float(lo),
            "ci_high": float(hi),
            "n_boot_effective": int(values.size),
        }
    return out


def paired_bootstrap(
    y_true: np.ndarray,
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    clusters: np.ndarray,
    metric: str = "mcc",
    threshold_a: float = 0.5,
    threshold_b: float = 0.5,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict:
    """Paired cluster bootstrap of the difference metric(A-model) - metric(B-model)."""

    y_true = np.asarray(y_true).astype(int)
    scores_a = np.asarray(scores_a, float)
    scores_b = np.asarray(scores_b, float)
    clusters = np.asarray(clusters)
    unique = np.unique(clusters)
    index_by_cluster = [np.where(clusters == c)[0] for c in unique]
    rng = np.random.default_rng(seed)

    point_a = _metric_value(metric, y_true, scores_a, threshold_a)
    point_b = _metric_value(metric, y_true, scores_b, threshold_b)
    deltas = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(unique), size=len(unique))
        idx = np.concatenate([index_by_cluster[i] for i in pick])
        y_b = y_true[idx]
        if len(np.unique(y_b)) < 2:
            continue
        a = _metric_value(metric, y_b, scores_a[idx], threshold_a)
        b = _metric_value(metric, y_b, scores_b[idx], threshold_b)
        if np.isfinite(a) and np.isfinite(b):
            deltas.append(a - b)
    deltas = np.asarray(deltas)
    if deltas.size == 0:
        return {"metric": metric, "delta": float(point_a - point_b), "p_value": float("nan")}
    # two-sided bootstrap p-value around zero
    p = 2.0 * min((deltas <= 0).mean(), (deltas >= 0).mean())
    return {
        "metric": metric,
        "model_a_point": float(point_a),
        "model_b_point": float(point_b),
        "delta": float(point_a - point_b),
        "ci_low": float(np.percentile(deltas, 100 * alpha / 2)),
        "ci_high": float(np.percentile(deltas, 100 * (1 - alpha / 2))),
        "p_value": float(min(1.0, p)),
        "n_boot_effective": int(deltas.size),
    }


def bh_fdr(p_values: Iterable[float], alpha: float = 0.05) -> list[dict]:
    """Benjamini-Hochberg adjustment; returns per-test q values and decisions."""

    p = np.asarray([1.0 if not np.isfinite(v) else float(v) for v in p_values])
    n = len(p)
    if n == 0:
        return []
    order = np.argsort(p)
    ranked = p[order]
    q_sorted = ranked * n / (np.arange(n) + 1)
    q_sorted = np.minimum.accumulate(q_sorted[::-1])[::-1]
    q_sorted = np.clip(q_sorted, 0.0, 1.0)
    q = np.empty(n)
    q[order] = q_sorted
    return [{"p_value": float(p[i]), "q_value": float(q[i]), "significant": bool(q[i] <= alpha)} for i in range(n)]


@dataclass
class Comparison:
    model_a: str
    model_b: str
    metric: str
    delta: float
    ci_low: float
    ci_high: float
    p_value: float
    equivalence_margin: float | None = None
    q_value: float | None = None
    significant: bool | None = None

    def to_row(self) -> dict:
        row = {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "metric": self.metric,
            "delta": self.delta,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "p_value": self.p_value,
            "q_value": self.q_value,
            "significant_fdr": self.significant,
        }
        if self.equivalence_margin is not None:
            row["equivalence_margin"] = self.equivalence_margin
            row["within_margin"] = bool(abs(self.delta) < self.equivalence_margin)
            ci_excludes_zero = (
                np.isfinite(self.ci_low) and np.isfinite(self.ci_high)
                and (self.ci_low > 0 or self.ci_high < 0)
            )
            if abs(self.delta) < self.equivalence_margin:
                row["conclusion"] = "no meaningful difference (pre-set margin)"
            elif self.q_value is not None and self.q_value <= 0.05:
                row["conclusion"] = "a > b (FDR-adjusted)" if self.delta > 0 else "b > a (FDR-adjusted)"
            elif ci_excludes_zero:
                row["conclusion"] = (
                    "nominal 95% CI excludes 0 but the FDR-adjusted q does not survive "
                    "- do not claim a difference"
                )
            else:
                row["conclusion"] = (
                    "no significant difference; the interval is too wide to claim equivalence"
                )
        return row
