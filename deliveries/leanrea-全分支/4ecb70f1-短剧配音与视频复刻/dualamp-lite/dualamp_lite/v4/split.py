"""Stage 4 - homology clustering, fixed Development/Test split and the 5 folds.

Rules fixed by V4 section 6:

* cluster at 80 % identity (CD-HIT ``-c 0.80 -aL 0.80`` when the binary exists,
  MMseqs2 next, the built-in k-mer fallback last - the method actually used is
  recorded and reported);
* Development 80 % / internal test 20 %, grouped by ``identity_cluster`` and
  seeded with ``split_seed = 20261109``; a cluster is never split across the two;
* hard negatives and scrambled peptides are challenge sets, not training data
  (unless ``hard_negative_in_training`` is set explicitly);
* the five folds are generated per training seed with ``StratifiedGroupKFold``;
  stratification is approximate by construction (documented limitation).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from ..dataset import cluster_sequences, load_precomputed_clusters
from ..utils import sha256_file
from .config import DatasetConfig, Paths
from .data import read_master

HARD_SPLIT = "hard_negative_test"


def _cluster_master(df: pd.DataFrame, cfg: DatasetConfig, paths: Paths, logger=None) -> tuple[pd.DataFrame, str]:
    pool = df[df["layer"] != "scrambled"].copy()
    seqs = pool["seq"].tolist()
    if cfg.cluster_method == "precomputed":
        if not cfg.cluster_table:
            raise ValueError("cluster_method=precomputed needs cluster_table")
        mapping = load_precomputed_clusters(cfg.cluster_table, seqs)
        method = "precomputed"
    else:
        mapping, method = cluster_sequences(
            seqs, cfg.cluster_method, cfg.cluster_identity, cfg.cluster_coverage, paths.cache, logger=logger
        )
    df = df.copy()
    df["identity_cluster"] = [
        f"c{int(mapping[s])}" if (s in mapping) else "scrambled" for s in df["seq"]
    ]
    if logger:
        n = df.loc[df["layer"] != "scrambled", "identity_cluster"].nunique()
        logger.info("  clustering: %d sequences -> %d clusters (%s)", len(seqs), n, method)
    return df, method


def _assign_dev_test(df: pd.DataFrame, cfg: DatasetConfig, logger=None) -> pd.DataFrame:
    trainable_layers = ["general_amp", "bacterial_amp", "negative_background"]
    if cfg.hard_negative_in_training:
        trainable_layers.append("hard_negative")
    pool = df[df["layer"].isin(trainable_layers)].copy()
    if pool.empty:
        raise RuntimeError("no trainable records - check the dataset layers")

    # a cluster that mixes labels is a homology/label conflict: review only
    labels_per_cluster = pool.groupby("identity_cluster")["label"].nunique()
    clash = set(labels_per_cluster[labels_per_cluster > 1].index)
    df = df.copy()
    df["split"] = ""
    df.loc[df["layer"].isin(trainable_layers) & df["identity_cluster"].isin(clash), "split"] = "review"
    pool = pool[~pool["identity_cluster"].isin(clash)]

    rng = np.random.default_rng(cfg.split_seed)
    cluster_stats = (
        pool.groupby(["identity_cluster", "label"]).size().reset_index(name="n").sort_values("n", ascending=False)
    )
    per_label_target = {
        int(label): int(round((1.0 - cfg.dev_fraction) * total))
        for label, total in cluster_stats.groupby("label")["n"].sum().items()
    }
    assigned = {label: 0 for label in per_label_target}

    for label in sorted(per_label_target):
        subset = cluster_stats[cluster_stats["label"] == label].copy()
        order = rng.permutation(len(subset))
        subset = subset.iloc[order].sort_values("n", ascending=False, kind="stable")
        target = per_label_target[label]
        for _, row in subset.iterrows():
            cluster = row["identity_cluster"]
            if assigned[label] < target:
                df.loc[df["identity_cluster"] == cluster, "split"] = "internal_test"
                assigned[label] += int(row["n"])
            else:
                df.loc[df["identity_cluster"] == cluster, "split"] = "development"

    used = df["identity_cluster"].isin(set(pool["identity_cluster"]))
    df.loc[used & (df["split"] == ""), "split"] = "development"

    if cfg.hard_negative_in_training:
        df.loc[(df["layer"] == "hard_negative") & (df["split"] == ""), "split"] = "development"
    else:
        df.loc[df["layer"] == "hard_negative", "split"] = HARD_SPLIT
    df.loc[df["layer"] == "scrambled", "split"] = "scrambled_test"
    df.loc[df["layer"] == "external", "split"] = "external_test"

    if logger:
        counts = df["split"].value_counts().to_dict()
        logger.info("  split sizes: %s", counts)
        for split in ("development", "internal_test"):
            part = df[df["split"] == split]
            if part["label"].nunique() < 2:
                raise RuntimeError(f"{split} contains a single class - cannot train/evaluate")
    return df


def _external_homologs(df: pd.DataFrame, logger=None) -> pd.DataFrame:
    dev_clusters = set(df.loc[df["split"].isin(["development", "internal_test", "review"]), "identity_cluster"])
    mask = (df["split"] == "external_test") & df["identity_cluster"].isin(dev_clusters)
    df.loc[mask, "split"] = "external_homolog"
    if logger and int(mask.sum()):
        logger.warning(
            "  %d/%d external peptides share an 80%% cluster with Development/Test -> split 'external_homolog'",
            int(mask.sum()), int((df["layer"] == "external").sum()),
        )
    return df


def assign_folds(df: pd.DataFrame, seeds: tuple[int, ...], folds: int, logger=None) -> pd.DataFrame:
    dev = df[df["split"] == "development"]
    if dev.empty:
        raise RuntimeError("development split is empty")
    X = np.zeros((len(dev), 1))
    y = dev["label"].to_numpy()
    groups = dev["identity_cluster"].to_numpy()
    df = df.copy()
    for seed in seeds:
        column = f"fold_seed_{seed}"
        df[column] = -1
        splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=int(seed))
        assignment = np.full(len(dev), -1, dtype=int)
        for fold, (_, valid_idx) in enumerate(splitter.split(X, y, groups)):
            assignment[valid_idx] = fold
        if (assignment < 0).any():
            raise RuntimeError(f"fold assignment incomplete for seed {seed}")
        df.loc[dev.index, column] = assignment
        if logger:
            sizes = pd.Series(assignment).value_counts().sort_index().to_dict()
            pos = pd.Series(y).groupby(assignment).mean().round(3).to_dict()
            logger.info("  folds seed=%s sizes=%s positive_rate=%s", seed, sizes, pos)
    return df


def run_split(cfg, paths: Paths, logger=None, seeds: tuple[int, ...] | None = None) -> dict:
    df = read_master(paths)
    df, cluster_method = _cluster_master(df, cfg.dataset, paths, logger=logger)
    df = _assign_dev_test(df, cfg.dataset, logger=logger)
    df = _external_homologs(df, logger=logger)
    seeds = tuple(seeds if seeds is not None else cfg.train.seeds)
    df = assign_folds(df, seeds, cfg.train.folds, logger=logger)

    paths.splits.mkdir(parents=True, exist_ok=True)
    for split in ("development", "internal_test", HARD_SPLIT, "external_test", "external_homolog", "scrambled_test", "review"):
        part = df[df["split"] == split]
        part.to_csv(paths.split_csv(split), index=False)
    for seed in seeds:
        dev = df[df["split"] == "development"][["sequence_id", "label", "identity_cluster", f"fold_seed_{seed}"]]
        dev = dev.rename(columns={f"fold_seed_{seed}": "fold"})
        dev.to_csv(paths.fold_csv(seed), index=False)
    clusters = (
        df.groupby("identity_cluster")
        .agg(n=("sequence_id", "size"), n_positive=("label", "sum"), split=("split", lambda s: ",".join(sorted(set(s)))))
        .reset_index()
    )
    clusters.to_csv(paths.clusters, sep="\t", index=False)

    from .qc import check_split

    checks = check_split(df, paths, seeds=seeds, folds=cfg.train.folds, logger=logger)
    meta = {
        "cluster_method": cluster_method,
        "cluster_identity": cfg.dataset.cluster_identity,
        "cluster_coverage": cfg.dataset.cluster_coverage,
        "split_seed": cfg.dataset.split_seed,
        "dev_fraction": cfg.dataset.dev_fraction,
        "folds": cfg.train.folds,
        "seeds": list(seeds),
        "hard_negative_in_training": cfg.dataset.hard_negative_in_training,
        "counts": df["split"].value_counts().to_dict(),
        "n_clusters": int(df.loc[df["layer"] != "scrambled", "identity_cluster"].nunique()),
        "max_cluster_size": int(df.loc[df["layer"] != "scrambled", "identity_cluster"].value_counts().max()),
        "qc": checks,
        "files": {
            split: {"path": str(paths.split_csv(split)), "sha256": sha256_file(paths.split_csv(split))}
            for split in ("development", "internal_test", HARD_SPLIT, "external_test", "scrambled_test")
            if paths.split_csv(split).exists()
        },
    }
    paths.manifests.mkdir(parents=True, exist_ok=True)
    (paths.manifests / "split_manifest.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    failed = [c for c in checks if not c.get("passed")]
    if failed:
        raise RuntimeError(f"split QC failed: {failed}")
    return meta
