"""Shared helper: build a tiny end-to-end workspace for the V4 unit tests.

The fixture deliberately runs the real stages (audit -> dataset -> split ->
features) on synthetic peptides, so every test exercises production code rather
than mocks of it. It is small (~130 sequences, 2 seeds, 3 folds) and finishes in
a few seconds.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from dualamp_lite.synth import write_demo_sources
from dualamp_lite.v4.config import DemoConfig, Paths, load_config
from dualamp_lite.v4.pipeline import (
    Context,
    stage_audit,
    stage_dataset,
    stage_env,
    stage_features,
    stage_split,
)


def build_workspace(
    root: Path | None = None,
    *,
    seeds: tuple[int, ...] = (11, 23),
    folds: int = 3,
    backend: str = "mock",
    n_positive: int = 60,
    n_negative: int = 60,
    n_hard_negative: int = 12,
    n_bacterial: int = 16,
    n_external: int = 12,
) -> tuple[object, Paths, Path, Context]:
    root = Path(root) if root else Path(tempfile.mkdtemp(prefix="dualamp_v4_"))
    cfg = load_config(None, workdir=root)
    cfg.demo_mode = True
    cfg.demo = DemoConfig(
        n_positive=n_positive,
        n_negative=n_negative,
        n_hard_negative=n_hard_negative,
        n_bacterial=n_bacterial,
        n_external=n_external,
    )
    cfg.features.backend = backend
    cfg.train.seeds = tuple(seeds)
    cfg.train.folds = folds
    cfg.train.epochs = 2
    cfg.train.patience = 1
    cfg.train.batch_size = 16
    cfg.train.n_boot = 100
    paths = Paths(root)
    manifest = write_demo_sources(paths.raw / "demo", cfg.demo)
    logger = logging.getLogger("dualamp_v4_test")
    ctx = Context(cfg=cfg, paths=paths, run_id="test", logger=logger, manifest=manifest)
    stage_env(ctx)
    stage_audit(ctx)
    stage_dataset(ctx)
    stage_split(ctx)
    stage_features(ctx)
    return cfg, paths, manifest, ctx


def cleanup(paths: Paths) -> None:
    shutil.rmtree(paths.root, ignore_errors=True)
