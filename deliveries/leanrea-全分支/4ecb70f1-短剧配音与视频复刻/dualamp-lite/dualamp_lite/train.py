"""Step 3 - train M0-M5, select on the dev folds, then evaluate the frozen test set once.

Protocol (plan §5, P1/P2 fixes)
-------------------------------
1. **Development set** = train + val. Group 5-fold CV by homology cluster, repeated
   over 5 seeds. Everything that needs a decision (epochs, threshold, optional
   focal-loss grid) is decided here.
2. **Independent test set**: clusters were held out in step 1, touched exactly once
   per model after the dev refit. No architecture/threshold tuning on it.
3. **Statistics**: DeLong for AUROC, paired cluster bootstrap for MCC/AUPRC, CIs on
   every point estimate, BH-FDR across comparisons, pre-set equivalence margin.

Artifacts
---------
    model/<MODEL>_seed<k>.pt        final dev-refit weights (D6-D8)
    model/<MODEL>_scores.npz        test predictions per seed + labels/clusters
    manuscript/D10_test_metrics.csv
    ablation/D9_ablation.csv
    manuscript/D10_evaluation_report.md
    manuscript/D11_external_validation.csv
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from . import evaluate as ev
from .config import STANDARD_AA, Paths, TrainConfig
from .features import load_split
from .models import (
    BASELINE_MODELS,
    CNNBiGRU,
    TORCH_MODELS,
    build_model,
    count_parameters,
)
from .utils import get_logger, set_seed, write_json

AA_TO_INDEX = {aa: i + 1 for i, aa in enumerate(STANDARD_AA)}


# --------------------------------------------------------------------------- #
# data plumbing
# --------------------------------------------------------------------------- #


@dataclass
class Bundle:
    residue: np.ndarray
    mask: np.ndarray
    mean: np.ndarray
    physio: np.ndarray
    tokens: np.ndarray
    labels: np.ndarray
    clusters: np.ndarray
    seq_ids: np.ndarray
    seqs: np.ndarray

    def take(self, idx: np.ndarray) -> "Bundle":
        return Bundle(
            self.residue[idx], self.mask[idx], self.mean[idx], self.physio[idx],
            self.tokens[idx], self.labels[idx], self.clusters[idx],
            self.seq_ids[idx], self.seqs[idx],
        )

    def __len__(self) -> int:
        return len(self.labels)


def _tokens_from_seqs(seqs: np.ndarray) -> np.ndarray:
    max_len = max(len(s) for s in seqs)
    tokens = np.zeros((len(seqs), max_len), dtype=np.int64)
    for i, seq in enumerate(seqs):
        tokens[i, : len(seq)] = [AA_TO_INDEX.get(aa, 0) for aa in seq]
    return tokens


def load_bundle(paths: Paths, split: str) -> Bundle:
    data = load_split(paths, split)
    return Bundle(
        residue=data["residue"],
        mask=data["mask"],
        mean=data["mean"],
        physio=data["physio"],
        tokens=_tokens_from_seqs(data["seqs"]),
        labels=data["labels"].astype(np.int64),
        clusters=data["clusters"].astype(np.int64),
        seq_ids=data["seq_ids"],
        seqs=data["seqs"],
    )


def _pad_stack(arrays: Sequence[np.ndarray], pad_value=0) -> np.ndarray:
    """Concatenate (N_i, L_i, ...) arrays along N, right-padding L to the maximum."""

    width = max(arr.shape[1] for arr in arrays)
    padded = []
    for arr in arrays:
        if arr.shape[1] == width:
            padded.append(arr)
            continue
        shape = (arr.shape[0], width - arr.shape[1]) + arr.shape[2:]
        pad = np.full(shape, pad_value, dtype=arr.dtype)
        padded.append(np.concatenate([arr, pad], axis=1))
    return np.concatenate(padded, axis=0)


def concat_bundles(bundles: Sequence[Bundle]) -> Bundle:
    residue = _pad_stack([b.residue for b in bundles], 0)
    mask = _pad_stack([b.mask for b in bundles], False)
    tokens = _pad_stack([b.tokens for b in bundles], 0)
    return Bundle(
        residue=residue,
        mask=mask,
        mean=np.concatenate([b.mean for b in bundles]),
        physio=np.concatenate([b.physio for b in bundles]),
        tokens=tokens,
        labels=np.concatenate([b.labels for b in bundles]),
        clusters=np.concatenate([b.clusters for b in bundles]),
        seq_ids=np.concatenate([b.seq_ids for b in bundles]),
        seqs=np.concatenate([b.seqs for b in bundles]),
    )


class PeptideDataset:
    """Minimal dataset holding float16 arrays, emitting float32 batch items."""

    def __init__(self, bundle: Bundle) -> None:
        self.bundle = bundle

    def __len__(self) -> int:
        return len(self.bundle)

    def __getitem__(self, idx: int) -> dict:
        import torch

        b = self.bundle
        return {
            "residue": torch.from_numpy(b.residue[idx].astype(np.float32)),
            "mask": torch.from_numpy(b.mask[idx]),
            "mean": torch.from_numpy(b.mean[idx].astype(np.float32)),
            "physio": torch.from_numpy(b.physio[idx].astype(np.float32)),
            "tokens": torch.from_numpy(b.tokens[idx]),
            "label": torch.tensor(float(b.labels[idx]), dtype=torch.float32),
        }


def forward_batch(model, batch: dict, device):
    if isinstance(model, CNNBiGRU):
        return model.forward_tokens(batch["tokens"].to(device), batch["mask"].to(device))
    return model(
        batch["residue"].to(device),
        batch["mask"].to(device),
        batch["physio"].to(device),
        batch["mean"].to(device),
    )


# --------------------------------------------------------------------------- #
# losses
# --------------------------------------------------------------------------- #


class FocalLoss:
    """Binary focal loss (Lin et al. 2017). alpha/gamma are treated as hyper-
    parameters resolved on the dev folds, never fixed a priori (plan §3.2)."""

    def __init__(self, alpha: float = 0.75, gamma: float = 2.0, pos_weight: float | None = None) -> None:
        self.alpha = alpha
        self.gamma = gamma
        self.pos_weight = pos_weight

    def __call__(self, logits, targets):
        import torch.nn.functional as F

        bce = F.binary_cross_entropy_with_logits(
            logits, targets, reduction="none",
            pos_weight=None if self.pos_weight is None else logits.new_tensor(self.pos_weight),
        )
        p = logits.sigmoid()
        pt = p * targets + (1 - p) * (1 - targets)
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
        return (alpha_t * (1 - pt).pow(self.gamma) * bce).mean()


def make_loss(cfg: TrainConfig, n_pos: int, n_neg: int):
    import torch
    import torch.nn as nn

    pos_weight = n_neg / max(n_pos, 1)
    if cfg.loss == "focal":
        return FocalLoss(cfg.focal_alpha, cfg.focal_gamma, pos_weight=pos_weight)
    return nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight, dtype=torch.float32))


# --------------------------------------------------------------------------- #
# torch training
# --------------------------------------------------------------------------- #


def _run_epochs(
    model,
    train_bundle: Bundle,
    val_bundle: Bundle | None,
    cfg: TrainConfig,
    device,
    epochs: int,
    lr: float,
    seed: int,
    logger=None,
    tag: str = "",
):
    import torch
    from torch.utils.data import DataLoader

    set_seed(seed)
    n_pos = int(train_bundle.labels.sum())
    n_neg = int(len(train_bundle.labels) - n_pos)
    loss_fn = make_loss(cfg, n_pos, n_neg)

    train_loader = DataLoader(
        PeptideDataset(train_bundle), batch_size=cfg.batch_size, shuffle=True,
        num_workers=cfg.num_workers, drop_last=False, pin_memory=(device.type == "cuda"),
    )
    val_loader = (
        DataLoader(PeptideDataset(val_bundle), batch_size=max(cfg.batch_size, 128), shuffle=False,
                   num_workers=cfg.num_workers, pin_memory=(device.type == "cuda"))
        if val_bundle is not None and len(val_bundle) else None
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(epochs, 1))
    use_amp = cfg.amp and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_state, best_score, best_epoch, bad = None, -np.inf, 0, 0
    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        running, seen = 0.0, 0
        for batch in train_loader:
            labels = batch["label"].to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=use_amp):
                logits = forward_batch(model, batch, device)
                loss = loss_fn(logits, labels)
            if use_amp:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                optimizer.step()
            running += float(loss.detach()) * len(labels)
            seen += len(labels)
        scheduler.step()
        record = {"epoch": epoch, "train_loss": running / max(seen, 1)}
        if val_loader is not None:
            probs = predict_loader(model, val_loader, device)
            val_auc = float(ev.binary_metrics(val_bundle.labels, probs)["auroc"])
            record["val_auroc"] = val_auc
            val_loss = float(
                torch.nn.functional.binary_cross_entropy(
                    torch.tensor(np.clip(probs, 1e-6, 1 - 1e-6), dtype=torch.float32),
                    torch.tensor(val_bundle.labels, dtype=torch.float32),
                )
            )
            record["val_loss"] = val_loss
            score = val_auc if np.isfinite(val_auc) else -val_loss
            if score > best_score + 1e-4:
                best_score, best_epoch, bad = score, epoch, 0
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
        history.append(record)
        if val_loader is not None and bad >= cfg.patience:
            if logger:
                logger.info("    %s early stop at epoch %d (best %d, val AUROC %.3f)",
                            tag, epoch, best_epoch, best_score)
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return {"best_epoch": best_epoch or epochs, "best_score": None if best_state is None else best_score,
            "history": history, "epochs_run": len(history)}


def predict_loader(model, loader, device) -> np.ndarray:
    import torch

    model.eval()
    out = []
    with torch.no_grad():
        for batch in loader:
            logits = forward_batch(model, batch, device)
            out.append(torch.sigmoid(logits.float()).cpu().numpy())
    return np.concatenate(out) if out else np.array([])


def predict_bundle(model, bundle: Bundle, cfg: TrainConfig, device) -> np.ndarray:
    from torch.utils.data import DataLoader

    loader = DataLoader(
        PeptideDataset(bundle), batch_size=max(cfg.batch_size * 2, 128), shuffle=False, num_workers=0
    )
    return predict_loader(model, loader, device)


def make_folds(labels: np.ndarray, clusters: np.ndarray, folds: int, seed: int):
    n_splits = min(folds, len(np.unique(clusters)))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    dummy = np.zeros((len(labels), 1))
    return [(tr, va) for tr, va in splitter.split(dummy, labels, groups=clusters)]


def train_torch_model(
    name: str,
    dev: Bundle,
    test: Bundle,
    cfg: TrainConfig,
    paths: Paths,
    embed_dim: int,
    n_physio: int,
    logger,
) -> dict:
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    started = time.time()
    per_seed, epoch_picks, test_scores = [], [], []
    oof_by_seed = []

    for seed in cfg.seeds:
        folds = make_folds(dev.labels, dev.clusters, cfg.folds, seed)
        oof = np.full(len(dev), np.nan)
        fold_rows = []
        for fold_idx, (tr, va) in enumerate(folds):
            model = build_model(name, embed_dim=embed_dim, n_physio=n_physio, dropout=cfg.dropout).to(device)
            info = _run_epochs(
                model, dev.take(tr), dev.take(va), cfg, device, cfg.epochs, cfg.lr, seed * 1000 + fold_idx,
                logger=logger, tag=f"{name}/s{seed}/f{fold_idx}",
            )
            oof[va] = predict_bundle(model, dev.take(va), cfg, device)
            met = ev.binary_metrics(dev.labels[va], oof[va])
            fold_rows.append({"fold": fold_idx, "val_auroc": met["auroc"], "val_mcc_at_0.5": met["mcc"],
                              "best_epoch": info["best_epoch"], "epochs_run": info["epochs_run"]})
        epoch_final = int(np.clip(np.median([r["best_epoch"] for r in fold_rows]), 2, max(cfg.epochs, 2)))
        epoch_picks.append(epoch_final)

        threshold = ev.best_threshold(dev.labels, oof, cfg.threshold_rule) if cfg.tune_threshold_models else 0.5
        oof_metrics = ev.binary_metrics(dev.labels, oof, threshold)

        # final refit on the whole development set (train + val), fixed epoch count
        final = build_model(name, embed_dim=embed_dim, n_physio=n_physio, dropout=cfg.dropout).to(device)
        _run_epochs(final, dev, None, cfg, device, epoch_final, cfg.lr, seed, logger=None, tag=f"{name}/final")

        test_prob = predict_bundle(final, test, cfg, device)
        test_scores.append(test_prob)
        oof_by_seed.append(oof)
        checkpoint = paths.model / f"{name}_seed{seed}.pt"
        torch.save(
            {
                "state_dict": final.state_dict(),
                "model_name": name,
                "seed": seed,
                "threshold": threshold,
                "epochs": epoch_final,
                "embed_dim": embed_dim,
                "n_physio": n_physio,
                "config": {k: getattr(cfg, k) for k in ("dropout", "lr", "weight_decay", "loss")},
            },
            checkpoint,
        )
        row = {
            "seed": seed,
            "threshold": float(threshold),
            "epochs_final": epoch_final,
            "dev_oof_auroc": oof_metrics["auroc"],
            "dev_oof_mcc": oof_metrics["mcc"],
            "folds": fold_rows,
            **{f"test_{k}": v for k, v in ev.binary_metrics(test.labels, test_prob, threshold).items()},
        }
        per_seed.append(row)
        if logger:
            logger.info(
                "  %s seed %d: dev OOF AUROC %.3f, test AUROC %.3f MCC %.3f (epochs=%d)",
                name, seed, oof_metrics["auroc"], row["test_auroc"], row["test_mcc"], epoch_final,
            )

    ensemble = np.mean(np.vstack(test_scores), axis=0)
    thresholds = [r["threshold"] for r in per_seed]
    threshold = float(np.mean(thresholds))
    metrics = ev.binary_metrics(test.labels, ensemble, threshold)
    ci = ev.cluster_bootstrap(
        test.labels, ensemble, test.clusters, threshold=threshold,
        n_boot=cfg.n_boot, alpha=cfg.boot_alpha, seed=0,
    )
    auroc_point, auroc_lo, auroc_hi = ev.delong_ci(test.labels, ensemble, cfg.boot_alpha)

    scores_path = paths.model / f"{name}_scores.npz"
    np.savez(
        scores_path,
        test_scores=np.vstack(test_scores),
        test_ensemble=ensemble,
        test_labels=test.labels,
        test_clusters=test.clusters,
        test_seq_ids=test.seq_ids,
        dev_oof_seed0=oof_by_seed[0],
        dev_labels=dev.labels,
        dev_clusters=dev.clusters,
    )

    return {
        "model": name,
        "family": "torch",
        "n_params": int(count_parameters(build_model(name, embed_dim=embed_dim, n_physio=n_physio))),
        "seeds": list(cfg.seeds),
        "threshold": threshold,
        "epochs": epoch_picks,
        "per_seed": per_seed,
        "test_metrics": metrics,
        "test_ci": ci,
        "auroc_delong_ci": {"point": auroc_point, "ci_low": auroc_lo, "ci_high": auroc_hi},
        "seconds": round(time.time() - started, 1),
        "scores_file": scores_path.name,
        "n_test": int(len(test.labels)),
    }


# --------------------------------------------------------------------------- #
# sklearn baselines (M0-RF / M0-HGB / M0-LogReg / optional XGBoost)
# --------------------------------------------------------------------------- #


def _sklearn_estimator(name: str, seed: int):
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression

    if name == "M0_RF":
        return RandomForestClassifier(
            n_estimators=500, min_samples_leaf=2, class_weight="balanced_subsample",
            n_jobs=-1, random_state=seed,
        )
    if name == "M0_HGB":
        return HistGradientBoostingClassifier(
            max_iter=400, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1e-3,
            early_stopping=True, validation_fraction=0.15, random_state=seed,
        )
    if name == "M0_LOGREG":
        return LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5)
    if name == "M0_XGB":
        from xgboost import XGBClassifier  # type: ignore

        return XGBClassifier(
            n_estimators=600, learning_rate=0.05, max_depth=4, subsample=0.8,
            colsample_bytree=0.8, reg_lambda=1.0, n_jobs=-1, eval_metric="logloss",
            random_state=seed,
        )
    raise ValueError(f"unknown baseline {name}")


def run_baseline_model(
    name: str,
    dev: Bundle,
    test: Bundle,
    cfg: TrainConfig,
    paths: Paths,
    logger,
) -> dict:
    started = time.time()
    per_seed, test_scores = [], []
    for seed in cfg.seeds:
        try:
            _sklearn_estimator(name, seed)
        except Exception as exc:  # e.g. xgboost not installed
            if logger:
                logger.warning("  %s skipped: %s", name, exc)
            return {"model": name, "family": "sklearn", "skipped": str(exc)}

        folds = make_folds(dev.labels, dev.clusters, cfg.folds, seed)
        oof = np.full(len(dev), np.nan)
        for tr, va in folds:
            est = _sklearn_estimator(name, seed)
            est.fit(dev.physio[tr], dev.labels[tr])
            oof[va] = est.predict_proba(dev.physio[va])[:, 1]
        threshold = ev.best_threshold(dev.labels, oof, cfg.threshold_rule) if cfg.tune_threshold_models else 0.5
        oof_metrics = ev.binary_metrics(dev.labels, oof, threshold)
        final = _sklearn_estimator(name, seed)
        final.fit(dev.physio, dev.labels)
        prob = final.predict_proba(test.physio)[:, 1]
        test_scores.append(prob)
        per_seed.append(
            {
                "seed": seed,
                "threshold": float(threshold),
                "dev_oof_auroc": oof_metrics["auroc"],
                "dev_oof_mcc": oof_metrics["mcc"],
                **{f"test_{k}": v for k, v in ev.binary_metrics(test.labels, prob, threshold).items()},
            }
        )
        if logger:
            logger.info("  %s seed %d: dev OOF AUROC %.3f, test AUROC %.3f",
                        name, seed, oof_metrics["auroc"], per_seed[-1]["test_auroc"])

    ensemble = np.mean(np.vstack(test_scores), axis=0)
    threshold = float(np.mean([r["threshold"] for r in per_seed]))
    metrics = ev.binary_metrics(test.labels, ensemble, threshold)
    ci = ev.cluster_bootstrap(
        test.labels, ensemble, test.clusters, threshold=threshold,
        n_boot=cfg.n_boot, alpha=cfg.boot_alpha, seed=0,
    )
    auroc_point, auroc_lo, auroc_hi = ev.delong_ci(test.labels, ensemble, cfg.boot_alpha)
    scores_path = paths.model / f"{name}_scores.npz"
    np.savez(
        scores_path,
        test_scores=np.vstack(test_scores),
        test_ensemble=ensemble,
        test_labels=test.labels,
        test_clusters=test.clusters,
        test_seq_ids=test.seq_ids,
    )
    return {
        "model": name,
        "family": "sklearn",
        "seeds": list(cfg.seeds),
        "threshold": threshold,
        "per_seed": per_seed,
        "test_metrics": metrics,
        "test_ci": ci,
        "auroc_delong_ci": {"point": auroc_point, "ci_low": auroc_lo, "ci_high": auroc_hi},
        "seconds": round(time.time() - started, 1),
        "scores_file": scores_path.name,
        "n_test": int(len(test.labels)),
    }


# --------------------------------------------------------------------------- #
# top-level driver
# --------------------------------------------------------------------------- #


def run_training(cfg: TrainConfig, paths: Paths, logger=None, external: bool = True,
                 force: bool = False) -> dict:
    logger = logger or get_logger(paths.logs / "train.log")
    train, val, test = (load_bundle(paths, split) for split in ("train", "val", "test"))
    dev = concat_bundles([train, val])
    logger.info(
        "dev: %d peptides (%d pos) in %d clusters | test: %d peptides (%d pos) in %d clusters",
        len(dev), int(dev.labels.sum()), len(np.unique(dev.clusters)),
        len(test), int(test.labels.sum()), len(np.unique(test.clusters)),
    )
    if int(test.labels.sum()) < 20:
        logger.warning(
            "only %d positives in the independent test set - CIs will be wide; "
            "this is a data-scale warning, not a bug", int(test.labels.sum())
        )

    embed_dim = int(train.residue.shape[-1])
    n_physio = int(train.physio.shape[-1])
    results = []
    for raw_name in cfg.models:
        name = raw_name.strip()
        key = name.upper()
        if key not in TORCH_MODELS and key not in BASELINE_MODELS + ("M0_XGB",):
            logger.warning("unknown model %s - skipped", name)
            continue
        cached = paths.model / f"{name}_results.json"
        scores = paths.model / f"{name}_scores.npz"
        if cached.exists() and scores.exists() and not force:
            # session-resume hook (Colab disconnects, Kaggle 12 h limits): model
            # results are only reused when both the JSON and the scores are present
            try:
                import json as _json

                previous = _json.loads(cached.read_text(encoding="utf-8"))
                if previous.get("seeds") == list(cfg.seeds):
                    logger.info("  %s already trained with these seeds - reusing (use --force to retrain)", name)
                    results.append(previous)
                    continue
            except Exception:
                pass
        logger.info("training %s ...", name)
        if key in TORCH_MODELS:
            result = train_torch_model(name, dev, test, cfg, paths, embed_dim, n_physio, logger)
        else:
            result = run_baseline_model(name, dev, test, cfg, paths, logger)
        if "skipped" in result:
            continue
        results.append(result)
        write_json(paths.model / f"{name}_results.json", result)

    if not results:
        raise RuntimeError("no model finished - check the model names and the torch installation")

    # Batch runs are the norm on Colab (session limits) and Kaggle (quota): merge
    # every model that has artefacts on disk instead of overwriting the tables
    # with whatever this particular invocation trained.
    import json as _json

    merged: dict[str, dict] = {}
    for path in sorted(paths.model.glob("*_results.json")):
        try:
            payload_model = _json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not payload_model.get("scores_file"):
            continue
        if not (paths.model / payload_model["scores_file"]).exists():
            continue
        merged[payload_model["model"]] = payload_model
    for res in results:
        merged[res["model"]] = res
    if len(merged) > len(results):
        logger.info("  merged results from previous runs: %s", sorted(merged))
    results = [merged[name] for name in sorted(merged)]

    metrics_rows = []
    for res in results:
        row = {"model": res["model"], "family": res["family"], "n_test": res.get("n_test"),
               "threshold": res["threshold"], "seconds": res.get("seconds")}
        for metric, point in res["test_metrics"].items():
            if metric in ("tp", "fp", "tn", "fn", "n"):
                continue
            ci = res["test_ci"].get(metric, {})
            row[metric] = point
            if ci:
                row[f"{metric}_ci_low"] = ci.get("ci_low")
                row[f"{metric}_ci_high"] = ci.get("ci_high")
        row["auroc_delong_ci_low"] = res["auroc_delong_ci"]["ci_low"]
        row["auroc_delong_ci_high"] = res["auroc_delong_ci"]["ci_high"]
        per_seed_aurocs = [r["test_auroc"] for r in res["per_seed"]]
        row["test_auroc_seed_mean"] = float(np.mean(per_seed_aurocs))
        row["test_auroc_seed_sd"] = float(np.std(per_seed_aurocs, ddof=1)) if len(per_seed_aurocs) > 1 else 0.0
        metrics_rows.append(row)
    metrics_df = pd.DataFrame(metrics_rows).sort_values("auroc", ascending=False)
    metrics_df.to_csv(paths.metrics_table, index=False)

    if force or not all((paths.model / f"{r['model']}_scores.npz").exists() for r in results):
        raise RuntimeError("scores missing for a finished model - rerun without --resume")
    comparisons = compare_models(results, test, cfg, paths, logger)
    pd.DataFrame([c.to_row() for c in comparisons]).to_csv(paths.ablation_table, index=False)

    external_rows = []
    if external:
        external_rows = evaluate_external(cfg, paths, results, logger)
    payload = {
        "models": results,
        "comparisons": [c.to_row() for c in comparisons],
        "external": external_rows,
    }
    write_json(paths.model / "train_summary.json", payload)
    logger.info("wrote %s and %s", paths.metrics_table.name, paths.ablation_table.name)
    return payload


def compare_models(results: list[dict], test: Bundle, cfg: TrainConfig, paths: Paths,
                   logger) -> list[ev.Comparison]:
    """Pre-declared comparisons with FDR control and an explicit equivalence margin."""

    by_name = {r["model"]: r for r in results}
    out: list[ev.Comparison] = []
    reference = "M3" if "M3" in by_name else results[0]["model"]
    pairs = [(reference, name) for name in by_name if name != reference]
    for a, b in pairs:
        scores_a = np.load(paths.model / by_name[a]["scores_file"])["test_ensemble"]
        scores_b = np.load(paths.model / by_name[b]["scores_file"])["test_ensemble"]
        if len(scores_a) != len(scores_b):
            continue
        delta = ev.delong_test(test.labels, scores_a, scores_b)
        se = delta.get("se_diff", float("nan"))
        z = 1.959963984540054  # 95% normal interval
        out.append(
            ev.Comparison(
                model_a=a, model_b=b, metric="auroc", delta=delta["auc_diff"],
                ci_low=delta["auc_diff"] - z * se if np.isfinite(se) else float("nan"),
                ci_high=delta["auc_diff"] + z * se if np.isfinite(se) else float("nan"),
                p_value=delta["p_value"],
            )
        )
        boot = ev.paired_bootstrap(
            test.labels, scores_a, scores_b, test.clusters, metric="mcc",
            threshold_a=by_name[a]["threshold"], threshold_b=by_name[b]["threshold"],
            n_boot=cfg.n_boot, alpha=cfg.boot_alpha, seed=0,
        )
        out.append(
            ev.Comparison(
                model_a=a, model_b=b, metric="mcc", delta=boot["delta"],
                ci_low=boot.get("ci_low", float("nan")), ci_high=boot.get("ci_high", float("nan")),
                p_value=boot.get("p_value", float("nan")),
                equivalence_margin=cfg.equivalence_margin_mcc,
            )
        )
        boot_pr = ev.paired_bootstrap(
            test.labels, scores_a, scores_b, test.clusters, metric="auprc",
            threshold_a=by_name[a]["threshold"], threshold_b=by_name[b]["threshold"],
            n_boot=cfg.n_boot, alpha=cfg.boot_alpha, seed=0,
        )
        out.append(
            ev.Comparison(
                model_a=a, model_b=b, metric="auprc", delta=boot_pr["delta"],
                ci_low=boot_pr.get("ci_low", float("nan")), ci_high=boot_pr.get("ci_high", float("nan")),
                p_value=boot_pr.get("p_value", float("nan")),
            )
        )
    fdr = ev.bh_fdr([c.p_value for c in out], alpha=cfg.boot_alpha)
    for comparison, adjusted in zip(out, fdr):
        comparison.q_value = adjusted["q_value"]  # type: ignore[attr-defined]
        comparison.significant = adjusted["significant"]  # type: ignore[attr-defined]
    if logger:
        logger.info("  comparisons: %d (BH-FDR controlled at %.2f)", len(out), cfg.boot_alpha)
    return out


def evaluate_external(cfg: TrainConfig, paths: Paths, results: list[dict], logger) -> list[dict]:
    """D11: AMPSphere-style external set + the scrambled challenge set.

    Loads every saved per-seed checkpoint of each model, averages the scores and
    reports metrics *with the threshold frozen from the dev folds*. External data
    never takes part in any model or threshold decision (plan §5).
    """

    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows: list[dict] = []
    for split in ("external", "scrambled"):
        path = paths.split_features(split)
        if not path.exists():
            continue
        bundle = load_bundle(paths, split)
        if split == "scrambled":
            # challenge set: every peptide should ideally be predicted negative
            bundle.labels[:] = 0
        for res in results:
            name = res["model"]
            probs = []
            for seed in cfg.seeds:
                checkpoint = paths.model / f"{name}_seed{seed}.pt"
                if not checkpoint.exists():
                    continue
                blob = torch.load(checkpoint, map_location=device, weights_only=False)
                model = build_model(name, embed_dim=blob["embed_dim"], n_physio=blob["n_physio"]).to(device)
                model.load_state_dict(blob["state_dict"])
                probs.append(predict_bundle(model, bundle, cfg, device))
            if not probs:
                continue
            scores = np.mean(np.vstack(probs), axis=0)
            threshold = res["threshold"]
            metrics = ev.binary_metrics(bundle.labels, scores, threshold) if len(np.unique(bundle.labels)) > 1 else {
                "n": int(len(bundle.labels)), "n_pos": int(bundle.labels.sum()),
                "mean_score": float(scores.mean()),
                "frac_predicted_positive": float((scores >= threshold).mean()),
            }
            rows.append({"split": split, "model": name, "threshold": threshold, **metrics})
            if logger:
                logger.info("  external[%s] %s: %s", split, name, metrics)
    if rows:
        pd.DataFrame(rows).to_csv(paths.manuscript / "D11_external_validation.csv", index=False)
    return rows
