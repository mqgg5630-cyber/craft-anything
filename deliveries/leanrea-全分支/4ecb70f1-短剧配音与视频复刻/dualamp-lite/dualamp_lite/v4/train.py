"""Stages 6-8 - 25-run cross-validation and the 5 final full-Development models.

Every run owns a directory and writes exactly the artefacts V4 section 10 asks
for::

    runs/<run_id>/<MODEL>/seed_<s>/fold_<f>/
        config.yaml  best_model.pt  last_model.pt  train_log.csv
        predictions.csv  metrics.json  environment.txt  rng_state.pt  scaler.joblib

The scaler is fitted on the training part of the fold only. The internal test is
never seen during cross-validation; the final stage retrains on all of
Development with the same five seeds, scores the frozen test once and keeps all
five checkpoints plus the mean-probability ensemble (never only the best seed).
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from ..evaluate import best_threshold, binary_metrics
from ..utils import get_logger, set_seed
from .config import Paths, TrainConfig
from .features import load_physchem, load_split_features
from .models import build_model, count_parameters
from .runs import run_dir, save_rng_state, short_environment, write_json

PRIMARY_METRICS = ("auprc", "auroc", "mcc")


# --------------------------------------------------------------------------- #
# feature store
# --------------------------------------------------------------------------- #


@dataclass
class Pool:
    ids: list[str]
    seqs: list[str]
    labels: np.ndarray
    phys: np.ndarray
    mean: np.ndarray
    residue: np.ndarray
    mask: np.ndarray
    clusters: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.ids)

    def take(self, index: np.ndarray) -> "Pool":
        index = np.asarray(index, dtype=int)
        return Pool(
            ids=[self.ids[i] for i in index],
            seqs=[self.seqs[i] for i in index],
            labels=self.labels[index],
            phys=self.phys[index],
            mean=self.mean[index],
            residue=self.residue[index],
            mask=self.mask[index],
            clusters=None if self.clusters is None else self.clusters[index],
        )

    def with_phys(self, phys: np.ndarray) -> "Pool":
        return replace(self, phys=phys)


class FeatureStore:
    """Lazily joins the split tables with the cached feature blocks."""

    def __init__(self, paths: Paths):
        blob = load_physchem(paths)
        self.phys = blob["X"]
        self.phys_index = {sid: i for i, sid in enumerate(blob["ids"])}
        self._esm: dict[str, dict] = {}

    def pool(self, paths: Paths, split: str) -> Pool:
        split_path = paths.split_csv(split)
        if not split_path.exists():
            raise FileNotFoundError(f"split file missing: {split_path}")
        table = pd.read_csv(split_path, keep_default_na=False)
        if not len(table):
            raise RuntimeError(f"split {split} is empty")
        esm = self._esm.get(split)
        if esm is None:
            esm = load_split_features(paths, split)
            esm_pos = {sid: i for i, sid in enumerate(esm["ids"])}
            order = []
            for sid in table["sequence_id"]:
                if sid not in esm_pos:
                    raise KeyError(f"sequence {sid} missing from the ESM cache of split {split}")
                order.append(esm_pos[sid])
            order = np.asarray(order, dtype=int)
            esm = {
                "ids": table["sequence_id"].tolist(),
                "mean": esm["mean"][order],
                "residue": esm["residue"][order],
                "mask": esm["mask"][order],
            }
            self._esm[split] = esm
        phys_rows = np.asarray([self.phys_index[sid] for sid in table["sequence_id"]], dtype=int)
        clusters = table["identity_cluster"].to_numpy() if "identity_cluster" in table else None
        return Pool(
            ids=table["sequence_id"].tolist(),
            seqs=table["seq"].tolist(),
            labels=table["label"].to_numpy(dtype=int),
            phys=self.phys[phys_rows].astype(np.float32),
            mean=esm["mean"].astype(np.float32),
            residue=esm["residue"],
            mask=esm["mask"].astype(bool),
            clusters=clusters,
        )


# --------------------------------------------------------------------------- #
# torch plumbing
# --------------------------------------------------------------------------- #


class PeptideDataset(torch.utils.data.Dataset):
    def __init__(self, pool: Pool):
        self.pool = pool

    def __len__(self) -> int:
        return len(self.pool)

    def __getitem__(self, i: int) -> dict:
        return {
            "index": i,
            "mean": torch.from_numpy(np.asarray(self.pool.mean[i], dtype=np.float32)),
            "residue": torch.from_numpy(np.asarray(self.pool.residue[i], dtype=np.float32)),
            "mask": torch.from_numpy(np.asarray(self.pool.mask[i], dtype=bool)),
            "phys": torch.from_numpy(np.asarray(self.pool.phys[i], dtype=np.float32)),
            "label": torch.tensor(float(self.pool.labels[i]), dtype=torch.float32),
        }


def _worker_init(worker_id: int) -> None:  # pragma: no cover - tested indirectly
    seed = torch.initial_seed() % 2**31
    np.random.seed(seed + worker_id)


def make_loader(pool: Pool, batch_size: int, seed: int, shuffle: bool, num_workers: int = 0):
    generator = torch.Generator()
    generator.manual_seed(int(seed))
    return torch.utils.data.DataLoader(
        PeptideDataset(pool),
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        generator=generator,
        worker_init_fn=_worker_init,
        drop_last=False,
    )


def _batch_forward(model: nn.Module, batch: dict, device) -> torch.Tensor:
    return model(
        mean=batch["mean"].to(device),
        phys=batch["phys"].to(device),
        residue=batch["residue"].to(device),
        mask=batch["mask"].to(device),
    )


def focal_loss(logits: torch.Tensor, targets: torch.Tensor, alpha: float = 0.75, gamma: float = 2.0) -> torch.Tensor:
    bce = nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
    pt = torch.exp(-bce)
    return (alpha * (1 - pt) ** gamma * bce).mean()


def _loss_fn(cfg: TrainConfig):
    if cfg.loss == "focal":
        return lambda logits, targets: focal_loss(logits, targets, cfg.focal_alpha, cfg.focal_gamma)
    return nn.BCEWithLogitsLoss()


def predict_pool(model: nn.Module, pool: Pool, cfg: TrainConfig, device) -> np.ndarray:
    model.eval()
    loader = make_loader(pool, cfg.batch_size, seed=0, shuffle=False, num_workers=cfg.num_workers)
    out = np.zeros(len(pool), dtype=np.float64)
    with torch.no_grad():
        for batch in loader:
            logits = _batch_forward(model, batch, device)
            out[batch["index"].numpy()] = torch.sigmoid(logits).cpu().numpy()
    return out


def _epoch_metrics(y: np.ndarray, probs: np.ndarray) -> dict:
    metrics = binary_metrics(y, probs, 0.5)
    metrics["balanced_accuracy"] = 0.5 * (metrics.get("sensitivity", np.nan) + metrics.get("specificity", np.nan))
    metrics["log_loss"] = float(
        -np.mean(y * np.log(np.clip(probs, 1e-7, 1)) + (1 - y) * np.log(np.clip(1 - probs, 1e-7, 1)))
    )
    return metrics


def _score(metrics: dict, primary: str) -> float:
    value = metrics.get(primary, float("nan"))
    return -np.inf if not np.isfinite(value) else float(value)


# --------------------------------------------------------------------------- #
# single fold
# --------------------------------------------------------------------------- #


def train_fold(
    cfg: TrainConfig,
    model_name: str,
    seed: int,
    fold: int,
    train_pool: Pool,
    val_pool: Pool,
    out_dir: Path,
    logger,
    embed_dim: int = 480,
    n_phys: int = 32,
    max_epochs: int | None = None,
    save: bool = True,
) -> dict:
    started = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    set_seed(seed)
    device = torch.device("cpu") if not torch.cuda.is_available() else torch.device("cuda")
    epochs = int(max_epochs or cfg.epochs)

    scaler = StandardScaler().fit(train_pool.phys)
    train_pool = train_pool.with_phys(scaler.transform(train_pool.phys).astype(np.float32))
    val_pool = val_pool.with_phys(scaler.transform(val_pool.phys).astype(np.float32))

    model = build_model(model_name, embed_dim=embed_dim, n_phys=n_phys, dropout=cfg.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=max(1, cfg.patience // 3)
    )
    loss_fn = _loss_fn(cfg)

    train_loader = make_loader(train_pool, cfg.batch_size, seed, shuffle=True, num_workers=cfg.num_workers)
    val_loader = make_loader(val_pool, cfg.batch_size, seed, shuffle=False, num_workers=cfg.num_workers)

    log_rows = []
    best_state = None
    best_epoch = 0
    best_score = -np.inf
    stale = 0
    history: list[dict] = []

    for epoch in range(1, epochs + 1):
        model.train()
        total, n_seen = 0.0, 0
        epoch_start = time.time()
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            logits = _batch_forward(model, batch, device)
            loss = loss_fn(logits, batch["label"].to(device))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
            optimizer.step()
            total += float(loss.item()) * len(batch["label"])
            n_seen += len(batch["label"])
        train_loss = total / max(1, n_seen)

        model.eval()
        val_probs = np.zeros(len(val_pool), dtype=np.float64)
        val_loss_total = 0.0
        with torch.no_grad():
            for batch in val_loader:
                logits = _batch_forward(model, batch, device)
                labels = batch["label"].to(device)
                val_loss_total += float(loss_fn(logits, labels).item()) * len(labels)
                val_probs[batch["index"].numpy()] = torch.sigmoid(logits).cpu().numpy()
        val_loss = val_loss_total / max(1, len(val_pool))
        metrics = _epoch_metrics(val_pool.labels, val_probs)
        score = _score(metrics, cfg.primary_metric)
        scheduler.step(score)

        row = {
            "epoch": epoch,
            "lr": float(optimizer.param_groups[0]["lr"]),
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_auroc": metrics.get("auroc"),
            "val_auprc": metrics.get("auprc"),
            "val_mcc": metrics.get("mcc"),
            "val_balanced_accuracy": metrics.get("balanced_accuracy"),
            "seconds": round(time.time() - epoch_start, 3),
        }
        log_rows.append(row)
        history.append(row)

        if score > best_score + 1e-6:
            best_score, best_epoch, stale = score, epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
        if stale >= cfg.patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    val_probs = predict_pool(model, val_pool, cfg, device)
    final_metrics = _epoch_metrics(val_pool.labels, val_probs)

    payload = {
        "model": model_name,
        "seed": int(seed),
        "fold": int(fold),
        "embed_dim": int(embed_dim),
        "n_phys": int(n_phys),
        "n_train": int(len(train_pool)),
        "n_val": int(len(val_pool)),
        "n_params": count_parameters(model),
        "epochs_ran": len(log_rows),
        "best_epoch": int(best_epoch),
        "primary_metric": cfg.primary_metric,
        "best_val_score": float(best_score) if np.isfinite(best_score) else None,
        "val_metrics": final_metrics,
        "thresholds": {
            "mcc": best_threshold(val_pool.labels, val_probs, "mcc"),
            "youden": best_threshold(val_pool.labels, val_probs, "youden"),
        },
        "loss": cfg.loss,
        "optimizer": "AdamW",
        "lr": cfg.lr,
        "weight_decay": cfg.weight_decay,
        "batch_size": cfg.batch_size,
        "dropout": cfg.dropout,
        "grad_clip": cfg.grad_clip,
        "scaler": "StandardScaler fitted on this fold's training part only",
        "deterministic": True,
        "seconds": round(time.time() - started, 2),
        "torch_threads": int(torch.get_num_threads()),
    }

    if save:
        pd.DataFrame(log_rows).to_csv(out_dir / "train_log.csv", index=False)
        pd.DataFrame(
            {
                "sequence_id": val_pool.ids,
                "y_true": val_pool.labels,
                "prob": val_probs,
                "threshold_mcc": payload["thresholds"]["mcc"],
                "model": model_name,
                "seed": seed,
                "fold": fold,
            }
        ).to_csv(out_dir / "predictions.csv", index=False)
        torch.save(
            {
                "state_dict": model.state_dict(),
                "model_name": model_name,
                "embed_dim": embed_dim,
                "n_phys": n_phys,
                "dropout": cfg.dropout,
                "seed": seed,
                "fold": fold,
                "best_epoch": best_epoch,
                "scaler_mean": scaler.mean_.tolist(),
                "scaler_scale": scaler.scale_.tolist(),
                "metrics": final_metrics,
                "config": {
                    "lr": cfg.lr,
                    "weight_decay": cfg.weight_decay,
                    "batch_size": cfg.batch_size,
                    "loss": cfg.loss,
                    "primary_metric": cfg.primary_metric,
                },
            },
            out_dir / "best_model.pt",
        )
        torch.save({"state_dict": model.state_dict(), "epoch": len(log_rows)}, out_dir / "last_model.pt")
        import joblib

        joblib.dump(scaler, out_dir / "scaler.joblib")
        save_rng_state(out_dir / "rng_state.pt")
        write_json(out_dir / "metrics.json", payload)
        (out_dir / "environment.txt").write_text(short_environment(), encoding="utf-8")
        _write_run_config(out_dir / "config.yaml", cfg, model_name, seed, fold, embed_dim, n_phys, epochs)

    payload["val_probs"] = val_probs
    payload["val_ids"] = val_pool.ids
    payload["history"] = history
    return payload


def _write_run_config(path: Path, cfg: TrainConfig, model: str, seed: int, fold: int, embed_dim: int, n_phys: int, epochs: int) -> None:
    import yaml

    payload = {
        "model": model,
        "seed": seed,
        "fold": fold,
        "epochs_max": epochs,
        "batch_size": cfg.batch_size,
        "lr": cfg.lr,
        "weight_decay": cfg.weight_decay,
        "dropout": cfg.dropout,
        "grad_clip": cfg.grad_clip,
        "patience": cfg.patience,
        "loss": cfg.loss,
        "primary_metric": cfg.primary_metric,
        "embed_dim": embed_dim,
        "n_phys": n_phys,
        "optimizer": "AdamW",
        "scheduler": "ReduceLROnPlateau(mode=max, factor=0.5)",
        "scaler": "StandardScaler(train fold only)",
        "threshold_rule": cfg.threshold_rule,
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


# --------------------------------------------------------------------------- #
# baselines (RF / HGB on the 32-dim block)
# --------------------------------------------------------------------------- #


def _baseline_estimator(name: str, seed: int):
    if name == "M0_RF":
        return RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2, max_features="sqrt", n_jobs=2, random_state=seed
        )
    if name == "M0_HGB":
        return HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, random_state=seed
        )
    if name == "M0_XGB":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=400, max_depth=3, learning_rate=0.05, subsample=0.9,
            colsample_bytree=0.9, reg_lambda=1.0, n_jobs=2, random_state=seed, eval_metric="logloss",
        )
    raise KeyError(f"unknown baseline {name!r}")


def train_baseline_fold(
    cfg: TrainConfig,
    name: str,
    seed: int,
    fold: int,
    train_pool: Pool,
    val_pool: Pool,
    out_dir: Path,
    logger=None,
) -> dict:
    started = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    scaler = StandardScaler().fit(train_pool.phys)
    X_train = scaler.transform(train_pool.phys)
    X_val = scaler.transform(val_pool.phys)
    model = _baseline_estimator(name, seed)
    model.fit(X_train, train_pool.labels)
    probs = np.asarray(model.predict_proba(X_val))[:, 1]
    metrics = _epoch_metrics(val_pool.labels, probs)
    payload = {
        "model": name,
        "seed": int(seed),
        "fold": int(fold),
        "n_train": int(len(train_pool)),
        "n_val": int(len(val_pool)),
        "val_metrics": metrics,
        "thresholds": {
            "mcc": best_threshold(val_pool.labels, probs, "mcc"),
            "youden": best_threshold(val_pool.labels, probs, "youden"),
        },
        "features": "frozen 32-dim schema only",
        "scaler": "StandardScaler fitted on this fold's training part only",
        "seconds": round(time.time() - started, 2),
    }
    pd.DataFrame({"epoch": [1], "train_loss": [np.nan], "val_loss": [np.nan], "val_auroc": [metrics["auroc"]], "val_auprc": [metrics["auprc"]], "val_mcc": [metrics["mcc"]], "seconds": [payload["seconds"]]}).to_csv(
        out_dir / "train_log.csv", index=False
    )
    pd.DataFrame(
        {
            "sequence_id": val_pool.ids,
            "y_true": val_pool.labels,
            "prob": probs,
            "threshold_mcc": payload["thresholds"]["mcc"],
            "model": name,
            "seed": seed,
            "fold": fold,
        }
    ).to_csv(out_dir / "predictions.csv", index=False)
    import joblib

    joblib.dump({"model": model, "scaler": scaler}, out_dir / "model.joblib")
    write_json(out_dir / "metrics.json", payload)
    (out_dir / "environment.txt").write_text(short_environment(), encoding="utf-8")
    payload["val_probs"] = probs
    payload["val_ids"] = val_pool.ids
    return payload


# --------------------------------------------------------------------------- #
# cross-validation driver
# --------------------------------------------------------------------------- #


def run_cross_validation(
    cfg,
    paths: Paths,
    run_id: str,
    store: FeatureStore,
    logger=None,
    max_epochs: int | None = None,
    models: Sequence[str] | None = None,
) -> pd.DataFrame:
    logger = logger or get_logger(paths.logs / f"cv_{run_id}.log")
    dev = store.pool(paths, "development")
    rows = []
    models = list(models) if models else list(cfg.train.models) + list(cfg.train.baselines)
    for model_name in models:
        for seed in cfg.train.seeds:
            fold_col = f"fold_seed_{seed}"
            if fold_col not in pd.read_csv(paths.split_csv("development"), nrows=1).columns:
                raise RuntimeError(f"split files do not contain {fold_col}; re-run the split stage with this seed")
            fold_table = pd.read_csv(paths.fold_csv(seed))
            fold_of = dict(zip(fold_table["sequence_id"], fold_table["fold"]))
            fold_ids = np.asarray([fold_of[sid] for sid in dev.ids], dtype=int)
            oof_prob = np.zeros(len(dev), dtype=np.float64)
            for fold in range(cfg.train.folds):
                train_idx = np.where(fold_ids != fold)[0]
                val_idx = np.where(fold_ids == fold)[0]
                if len(val_idx) == 0:
                    raise RuntimeError(f"empty validation fold {fold}")
                out_dir = run_dir(paths, run_id, model_name, seed, fold)
                if model_name.startswith("M0_"):
                    result = train_baseline_fold(cfg.train, model_name, seed, fold, dev.take(train_idx), dev.take(val_idx), out_dir, logger)
                else:
                    result = train_fold(
                        cfg.train, model_name, seed, fold, dev.take(train_idx), dev.take(val_idx),
                        out_dir, logger, embed_dim=cfg.features.embed_dim, max_epochs=max_epochs,
                    )
                oof_prob[val_idx] = result["val_probs"]
                rows.append(
                    {
                        "run_id": run_id,
                        "model": model_name,
                        "seed": seed,
                        "fold": fold,
                        "n_train": result["n_train"],
                        "n_val": result["n_val"],
                        "auroc": result["val_metrics"]["auroc"],
                        "auprc": result["val_metrics"]["auprc"],
                        "mcc": result["val_metrics"]["mcc"],
                        "best_epoch": result.get("best_epoch", 1),
                        "seconds": result["seconds"],
                    }
                )
                logger.info(
                    "  %-6s seed=%2d fold=%d  AUROC=%.3f AUPRC=%.3f MCC=%.3f (%.1fs)",
                    model_name, seed, fold,
                    result["val_metrics"]["auroc"], result["val_metrics"]["auprc"], result["val_metrics"]["mcc"],
                    result["seconds"],
                )
            threshold = best_threshold(dev.labels, oof_prob, cfg.train.threshold_rule)
            seed_dir = paths.runs / run_id / model_name / f"seed_{seed}"
            seed_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                {
                    "sequence_id": dev.ids,
                    "y_true": dev.labels,
                    "prob": oof_prob,
                    "threshold": threshold,
                    "model": model_name,
                    "seed": seed,
                    "fold": fold_ids,
                }
            ).to_csv(seed_dir / "oof_predictions.csv", index=False)
            oof_metrics = binary_metrics(dev.labels, oof_prob, threshold)
            oof_metrics["balanced_accuracy"] = 0.5 * (oof_metrics["sensitivity"] + oof_metrics["specificity"])
            oof_metrics["threshold_rule"] = cfg.train.threshold_rule
            write_json(seed_dir / "oof_metrics.json", oof_metrics)
            rows.append(
                {
                    "run_id": run_id, "model": model_name, "seed": seed, "fold": "oof",
                    "n_train": int((fold_ids >= 0).sum()), "n_val": len(dev),
                    "auroc": oof_metrics["auroc"], "auprc": oof_metrics["auprc"],
                    "mcc": oof_metrics["mcc"], "best_epoch": np.nan,
                    "seconds": np.nan, "threshold": threshold,
                }
            )
    table = pd.DataFrame(rows)
    results_dir = paths.results / run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    existing = results_dir / "cv_runs.csv"
    if existing.exists():
        previous = pd.read_csv(existing)
        previous = previous[~previous["model"].isin(table["model"].unique())]
        table = pd.concat([previous, table], ignore_index=True)
    table.to_csv(results_dir / "cv_runs.csv", index=False)
    table[table["fold"] == "oof"].to_csv(results_dir / "cv_oof.csv", index=False)
    return table


# --------------------------------------------------------------------------- #
# final models
# --------------------------------------------------------------------------- #


def _cv_best_epochs(paths: Paths, run_id: str, model: str, seed: int) -> int | None:
    folds = []
    for fold in range(100):
        path = paths.runs / run_id / model / f"seed_{seed}" / f"fold_{fold}" / "metrics.json"
        if not path.exists():
            break
        import json

        payload = json.loads(path.read_text())
        if "best_epoch" in payload:
            folds.append(int(payload["best_epoch"]))
    if not folds:
        return None
    return max(1, int(round(float(np.median(folds)))))


def run_final(cfg, paths: Paths, run_id: str, store: FeatureStore, logger=None, epochs: int | None = None) -> pd.DataFrame:
    logger = logger or get_logger(paths.logs / f"final_{run_id}.log")
    dev = store.pool(paths, "development")
    test = store.pool(paths, "internal_test")
    splits = {"internal_test": test}
    for extra in ("hard_negative_test", "external_test", "external_homolog", "scrambled_test"):
        if paths.split_csv(extra).exists():
            try:
                splits[extra] = store.pool(paths, extra)
            except RuntimeError:
                continue

    scaler = StandardScaler().fit(dev.phys)
    dev_scaled = dev.with_phys(scaler.transform(dev.phys).astype(np.float32))
    device = torch.device("cpu") if not torch.cuda.is_available() else torch.device("cuda")

    rows = []
    ensemble_probs: dict[str, dict[str, list[np.ndarray]]] = {
        name: {model: [] for model in cfg.train.models} for name in splits
    }
    for model_name in cfg.train.models:
        for seed in cfg.train.seeds:
            epochs_this = epochs or _cv_best_epochs(paths, run_id, model_name, seed) or cfg.train.epochs
            set_seed(seed)
            model = build_model(model_name, embed_dim=cfg.features.embed_dim, n_phys=32, dropout=cfg.train.dropout).to(device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.train.lr, weight_decay=cfg.train.weight_decay)
            loss_fn = _loss_fn(cfg.train)
            loader = make_loader(dev_scaled, cfg.train.batch_size, seed, shuffle=True, num_workers=cfg.train.num_workers)
            for epoch in range(1, epochs_this + 1):
                model.train()
                for batch in loader:
                    optimizer.zero_grad(set_to_none=True)
                    loss = loss_fn(_batch_forward(model, batch, device), batch["label"].to(device))
                    loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(), cfg.train.grad_clip)
                    optimizer.step()
            out_dir = paths.final_models / run_id / model_name / f"seed_{seed}"
            out_dir.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "model_name": model_name,
                    "embed_dim": cfg.features.embed_dim,
                    "n_phys": 32,
                    "dropout": cfg.train.dropout,
                    "seed": seed,
                    "epochs": epochs_this,
                    "scaler_mean": scaler.mean_.tolist(),
                    "scaler_scale": scaler.scale_.tolist(),
                },
                out_dir / "model.pt",
            )
            oof_path = paths.runs / run_id / model_name / f"seed_{seed}" / "oof_metrics.json"
            threshold = 0.5
            if oof_path.exists():
                import json

                threshold = float(json.loads(oof_path.read_text())["threshold"])
            for split_name, pool in splits.items():
                pool_scaled = pool.with_phys(scaler.transform(pool.phys).astype(np.float32))
                probs = predict_pool(model, pool_scaled, cfg.train, device)
                pd.DataFrame(
                    {"sequence_id": pool.ids, "y_true": pool.labels, "prob": probs, "model": model_name, "seed": seed, "split": split_name, "threshold": threshold}
                ).to_csv(out_dir / f"predictions_{split_name}.csv", index=False)
                ensemble_probs[split_name][model_name].append(probs)
                rows.append(
                    {
                        "run_id": run_id, "model": model_name, "seed": seed, "split": split_name,
                        "epochs": epochs_this, "n": len(pool), "mean_prob": float(np.mean(probs)),
                        "auroc": binary_metrics(pool.labels, probs, threshold)["auroc"] if pool.labels.min() != pool.labels.max() else np.nan,
                    }
                )
            logger.info("  final %-6s seed=%2d epochs=%d", model_name, seed, epochs_this)

    # mean-probability ensemble, one row set per architecture
    for split_name, pool in splits.items():
        frames = []
        for model_name, prob_list in ensemble_probs[split_name].items():
            if not prob_list:
                continue
            stack = np.vstack(prob_list)
            frames.append(
                pd.DataFrame(
                    {
                        "sequence_id": pool.ids,
                        "y_true": pool.labels,
                        "prob": stack.mean(axis=0),
                        "model": model_name,
                        "seed": "mean",
                        "split": split_name,
                        "n_seeds": stack.shape[0],
                    }
                )
            )
        if frames:
            pd.concat(frames, ignore_index=True).to_csv(
                paths.final_models / run_id / f"ensemble_{split_name}.csv", index=False
            )
    table = pd.DataFrame(rows)
    results_dir = paths.results / run_id
    results_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(results_dir / "final_test_predictions.csv", index=False)
    write_json(
        paths.final_models / run_id / "manifest.json",
        {
            "run_id": run_id,
            "models": list(cfg.train.models),
            "seeds": list(cfg.train.seeds),
            "ensemble": "mean predicted probability across seeds for the same architecture",
            "scaler": "StandardScaler fitted on all Development; applied to the internal test once",
            "test_touched": "once, after the five seeds were trained",
            "files": sorted(str(p.relative_to(paths.final_models / run_id)) for p in (paths.final_models / run_id).rglob("*") if p.is_file()),
        },
    )
    return table
