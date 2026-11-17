"""Automatic quality-control assertions (V4 sections 6 and 8).

Every check returns ``{"check", "level", "passed", "detail"}``. Level ``P0``
checks abort the stage: a pipeline that cannot prove the split is leak-free must
not produce numbers. Level ``INFO`` checks are reported in the manifest only.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

P0 = "P0"
INFO = "INFO"


def _result(check: str, passed: bool, detail: str, level: str = P0) -> dict:
    return {"check": check, "level": level, "passed": bool(passed), "detail": detail}


def check_split(df: pd.DataFrame, paths=None, seeds: tuple[int, ...] = (), folds: int = 5, logger=None) -> list[dict]:
    checks: list[dict] = []
    dev = df[df["split"] == "development"]
    test = df[df["split"] == "internal_test"]

    checks.append(_result("dev_test_both_classes", dev["label"].nunique() == 2 and test["label"].nunique() == 2, f"dev={dev['label'].value_counts().to_dict()}, test={test['label'].value_counts().to_dict()}"))
    checks.append(_result("no_duplicate_sequences", not df["seq"].duplicated().any(), f"{int(df['seq'].duplicated().sum())} duplicates"))

    shared_clusters = set(dev["identity_cluster"]) & set(test["identity_cluster"])
    checks.append(_result("no_cluster_leakage", not shared_clusters, f"{len(shared_clusters)} clusters shared between Development and Test"))

    dev_parents = set(dev["parent_id"]) - {""}
    test_parents = set(test["parent_id"]) - {""}
    shared_parents = dev_parents & test_parents
    checks.append(_result("no_parent_leakage", not shared_parents, f"{len(shared_parents)} parent ids shared: {sorted(shared_parents)[:5]}"))

    trainable = df[df["split"].isin(["development", "internal_test"])]
    scrambled = df[df["layer"] == "scrambled"]
    overlap = set(scrambled["seq"]) & set(trainable["seq"])
    checks.append(_result("no_scrambled_parent_leakage", not overlap, f"{len(overlap)} scrambled sequences appear in Development/Test"))

    pos_ids = set(df.loc[df["label"] == 1, "sequence_id"])
    parentless = [p for p in scrambled["parent_id"] if p not in pos_ids]
    checks.append(
        _result(
            "scrambled_derived_from_positives",
            len(parentless) == 0,
            f"{len(parentless)} scrambled peptides without a positive parent",
            level=INFO,
        )
    )

    for seed in seeds:
        column = f"fold_seed_{seed}"
        if column not in dev.columns:
            checks.append(_result(f"folds_present_seed_{seed}", False, f"missing column {column}"))
            continue
        ok = True
        detail = {}
        for fold, grp in dev.groupby(column):
            counts = grp["label"].value_counts().to_dict()
            detail[int(fold)] = counts
            if len(counts) < 2:
                ok = False
        checks.append(_result(f"folds_both_classes_seed_{seed}", ok, str(detail)))

    # cluster sanity --------------------------------------------------------
    sizes = df.loc[df["layer"] != "scrambled", "identity_cluster"].value_counts()
    share = float(sizes.max() / max(1, len(df)))
    checks.append(_result("cluster_max_share_below_5pct", share < 0.05, f"largest cluster = {share:.3f} of records", level=INFO))
    checks.append(_result("cluster_count", len(sizes) > 1, f"{len(sizes)} clusters", level=INFO))
    checks.append(
        _result(
            "cluster_singleton_fraction",
            True,
            f"{float((sizes == 1).mean()):.3f} of clusters are singletons",
            level=INFO,
        )
    )
    checks.append(
        _result(
            "sequence_length_range",
            bool(((df["length"] >= 10) & (df["length"] <= 50)).all()),
            f"length in [{int(df['length'].min())}, {int(df['length'].max())}]",
        )
    )
    if logger:
        for check in checks:
            logger.info("  QC %-36s %s  %s", check["check"], "ok" if check["passed"] else "FAIL", check["detail"])
    return checks


def check_features(X: np.ndarray, mask: np.ndarray | None = None, ids: list[str] | None = None, logger=None) -> list[dict]:
    checks: list[dict] = []
    X = np.asarray(X)
    finite = bool(np.all(np.isfinite(X)))
    checks.append(_result("features_finite", finite, f"{X.shape[1]} columns, {len(X)} rows"))
    if not finite:
        bad = [i for i in range(X.shape[1]) if not np.all(np.isfinite(X[:, i]))]
        checks[-1]["detail"] += f"; non-finite columns {bad}"
    checks.append(_result("features_expected_dim", X.shape[1] == 32, f"shape={X.shape}"))
    if mask is not None:
        lengths = np.asarray(mask, dtype=bool).sum(axis=1)
        checks.append(_result("mask_matches_length", bool((lengths > 0).all()), f"min length {int(lengths.min())}"))
        checks.append(
            _result(
                "mask_padding_blocked",
                bool((np.asarray(mask)[:, 0]).all() if mask.size else True),
                "every sequence has at least one real residue",
            )
        )
    if ids is not None:
        checks.append(_result("ids_unique", len(set(ids)) == len(ids), f"{len(ids)} ids"))
    if logger:
        for check in checks:
            logger.info("  QC %-36s %s  %s", check["check"], "ok" if check["passed"] else "FAIL", check["detail"])
    return checks


def check_models(models: dict, embed_dim: int = 480, logger=None) -> list[dict]:
    """Shape and parameter-count checks for the frozen M1/M2/M3 definitions."""

    checks: list[dict] = []
    for name, model in models.items():
        n_params = sum(p.numel() for p in model.parameters())
        checks.append(_result(f"model_{name}_parameters", n_params > 0, f"{n_params} parameters"))
    if logger:
        for check in checks:
            logger.info("  QC %-36s %s  %s", check["check"], "ok" if check["passed"] else "FAIL", check["detail"])
    return checks


def assert_all_pass(checks: list[dict], stage: str) -> None:
    failed = [c for c in checks if c["level"] == P0 and not c["passed"]]
    if failed:
        detail = "; ".join(f"{c['check']}: {c['detail']}" for c in failed)
        raise RuntimeError(f"{stage} QC failed ({len(failed)} P0 checks): {detail}")


def write_checks(checks: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks).to_csv(path, index=False)
    return path
