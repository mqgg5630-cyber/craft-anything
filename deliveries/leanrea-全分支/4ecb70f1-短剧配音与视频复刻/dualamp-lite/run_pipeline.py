#!/usr/bin/env python3
"""DualAMP-Lite V1.0 - one-command, staged, reproducible pipeline.

Examples
--------
    # plumbing smoke test on synthetic peptides with the mock encoder
    python run_pipeline.py --stage all --demo --epochs 8 --workdir demo_run

    # real run (Kaggle / Colab): point --manifest at your sources.yaml
    python run_pipeline.py --stage all --manifest configs/sources.yaml \
        --backend fair-esm --weights-dir cache/weights --workdir 2026-11-09_DualAMP-Lite

    # rebuild only the report from existing artefacts
    python run_pipeline.py --stage evaluation --run-id 20261109_235500
"""

from __future__ import annotations

import argparse
import os

# Determinism switches must be set before torch/CUDA are initialised (V4 §12).
os.environ.setdefault("PYTHONHASHSEED", "0")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dualamp_lite.v4.config import Paths, default_workdir, load_config  # noqa: E402
from dualamp_lite.v4.pipeline import build_context, run_stage  # noqa: E402

STAGES = (
    "all",
    "env",
    "audit",
    "dataset",
    "split",
    "features",
    "baseline",
    "cross_validation",
    "final_train",
    "evaluation",
    "reproducibility",
    "export",
    "hash",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DualAMP-Lite V1.0 pipeline")
    parser.add_argument("--stage", default="all", choices=STAGES)
    parser.add_argument("--workdir", default=None, help="output directory (default ./2026-11-09_DualAMP-Lite)")
    parser.add_argument("--config", default=None, help="experiment YAML (see configs/experiment.yaml)")
    parser.add_argument("--manifest", default=None, help="source manifest YAML")
    parser.add_argument("--run-id", default=None, help="reuse an existing run id (default: new timestamp)")
    parser.add_argument("--demo", action="store_true", help="generate synthetic peptides and a source manifest")
    parser.add_argument("--backend", default=None, choices=["auto", "fair-esm", "transformers", "mock"])
    parser.add_argument("--weights-dir", default=None)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--epochs", type=int, default=None, help="override the maximum epochs")
    parser.add_argument("--seeds", default=None, help="comma separated, e.g. 11,23,37,53,71")
    parser.add_argument("--folds", type=int, default=None)
    parser.add_argument("--models", default=None, help="comma separated torch models (default M1,M2,M3)")
    parser.add_argument("--baselines", default=None, help="comma separated baselines (default M0_RF,M0_HGB)")
    parser.add_argument("--device", default=None)
    parser.add_argument("--n-boot", type=int, default=None)
    parser.add_argument("--threads", type=int, default=None)
    return parser.parse_args(argv)


def apply_overrides(cfg, args: argparse.Namespace) -> None:
    if args.demo:
        cfg.demo_mode = True
    if args.backend:
        cfg.features.backend = args.backend
    if args.weights_dir:
        cfg.features.weights_dir = args.weights_dir
    if args.local_files_only:
        cfg.features.local_files_only = True
    if args.device:
        cfg.features.device = args.device
    if args.seeds:
        cfg.train.seeds = tuple(int(x) for x in args.seeds.split(",") if x.strip())
    if args.folds:
        cfg.train.folds = int(args.folds)
    if args.models:
        cfg.train.models = tuple(x.strip() for x in args.models.split(",") if x.strip())
    if args.baselines:
        cfg.train.baselines = tuple(x.strip() for x in args.baselines.split(",") if x.strip())
    if args.n_boot:
        cfg.train.n_boot = int(args.n_boot)
    if args.threads:
        cfg.train.threads = int(args.threads)


def configure_torch(cfg, logger=None) -> None:
    import torch

    torch.set_num_threads(max(1, cfg.train.threads))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    try:
        torch.use_deterministic_algorithms(True)
        mode = "strict"
    except Exception as exc:  # pragma: no cover - platform dependent
        torch.use_deterministic_algorithms(True, warn_only=True)
        mode = f"warn_only ({exc})"
    if logger:
        logger.info("torch determinism: %s | threads=%d", mode, torch.get_num_threads())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    workdir = Path(args.workdir).expanduser() if args.workdir else default_workdir()
    cfg = load_config(args.config, workdir=workdir)
    apply_overrides(cfg, args)
    paths = Paths(workdir)
    ctx = build_context(cfg, paths, run_id=args.run_id, manifest=args.manifest, max_epochs=args.epochs)
    configure_torch(cfg, ctx.logger)
    try:
        result = run_stage(ctx, args.stage)
    except Exception:
        ctx.logger.exception("stage %s failed - partial artefacts kept in %s", args.stage, paths.root)
        raise
    ctx.logger.info("done: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
