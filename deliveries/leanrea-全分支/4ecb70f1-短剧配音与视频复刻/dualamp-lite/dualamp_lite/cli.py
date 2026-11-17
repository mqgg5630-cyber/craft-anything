"""Command line interface - one entry point for Kaggle, Colab and local runs.

    python -m dualamp_lite check                     # environment / GPU / tools
    python -m dualamp_lite demo                      # 2-minute plumbing test
    python -m dualamp_lite build   --manifest configs/sources.yaml
    python -m dualamp_lite features --backend fair-esm --weights-dir /kaggle/input/esm2
    python -m dualamp_lite train   --models M0_RF,M0_HGB,M1,M2,M3 --seeds 1,2,3,4,5
    python -m dualamp_lite report
    python -m dualamp_lite all --manifest configs/sources.yaml --backend fair-esm
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .config import (
    DatasetConfig,
    DemoConfig,
    FeatureConfig,
    Paths,
    TrainConfig,
    default_workdir,
)
from .utils import Timer, describe_environment, get_logger, human_bytes, write_file_manifest


def _paths(args) -> Paths:
    return Paths(Path(args.workdir).expanduser() if args.workdir else default_workdir())


def _dataset_cfg(args) -> DatasetConfig:
    cfg = DatasetConfig()
    for attr in ("min_len", "max_len", "cluster_identity", "cluster_coverage", "test_frac",
                 "val_frac", "seed", "max_scrambled"):
        value = getattr(args, attr, None)
        if value is not None:
            setattr(cfg, attr, value)
    if getattr(args, "cluster_method", None):
        cfg.cluster_method = args.cluster_method
    if getattr(args, "cluster_table", None):
        cfg.cluster_table = args.cluster_table
        cfg.cluster_method = "precomputed"
    if getattr(args, "no_scrambled", False):
        cfg.add_scrambled = False
        cfg.max_scrambled = 0
    if getattr(args, "keep_conflicts", False):
        cfg.drop_conflicts = False
    return cfg


def _feature_cfg(args) -> FeatureConfig:
    cfg = FeatureConfig()
    for attr in ("backend", "model_name", "hf_model_id", "repr_layer", "batch_size", "device",
                 "storage_dtype", "max_residues", "weights_dir", "redundancy_threshold"):
        value = getattr(args, attr, None)
        if value is not None:
            setattr(cfg, attr, value)
    if getattr(args, "local_files_only", False):
        cfg.local_files_only = True
    return cfg


def _train_cfg(args) -> TrainConfig:
    cfg = TrainConfig()
    if getattr(args, "models", None):
        cfg.models = tuple(m.strip() for m in args.models.split(",") if m.strip())
    if getattr(args, "seeds", None):
        cfg.seeds = tuple(int(s) for s in str(args.seeds).split(",") if s.strip())
    for attr in ("folds", "epochs", "batch_size", "lr", "weight_decay", "dropout", "patience",
                 "loss", "focal_alpha", "focal_gamma", "threshold_rule", "n_boot",
                 "equivalence_margin_mcc", "num_workers"):
        value = getattr(args, attr, None)
        if value is not None:
            setattr(cfg, attr, value)
    if getattr(args, "no_amp", False):
        cfg.amp = False
    return cfg


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def cmd_check(args) -> int:
    paths = _paths(args)
    env = describe_environment()
    print("DualAMP-Lite environment check")
    print("=" * 60)
    print(f"workdir         : {paths.root}")
    print(f"python          : {env['python']}")
    print(f"platform        : {env['platform']}")
    print(f"CUDA available  : {env['cuda']}")
    print(f"GPU             : {env['gpu']}")
    packages = {k: v for k, v in env["packages"].items() if v}
    print(f"packages        : {packages}")
    for tool in ("cd-hit", "mmseqs", "cd-hit-est"):
        found = shutil.which(tool)
        print(f"{tool:<16}: {found or 'not found (k-mer fallback will be used)'}")
    for label, path in (("data dir", paths.dataset), ("features dir", paths.features)):
        n = len(list(path.glob("*"))) if path.exists() else 0
        print(f"{label:<16}: {n} files")
    try:
        usage = shutil.disk_usage(paths.root)
        print(f"free disk       : {human_bytes(usage.free)}")
    except OSError:
        pass
    try:
        import torch

        if torch.cuda.is_available():
            print(f"GPU memory      : {human_bytes(torch.cuda.get_device_properties(0).total_memory)}")
            print(f"GPU count       : {torch.cuda.device_count()}")
    except Exception:
        pass
    print("=" * 60)
    print("ready" if env["packages"].get("numpy") else "numpy missing - pip install -r requirements.txt")
    return 0


def cmd_build(args) -> int:
    from .dataset import build_dataset

    paths = _paths(args)
    logger = get_logger(paths.logs / "build_dataset.log")
    manifest = args.manifest
    if args.demo:
        from .synth import write_demo_sources

        manifest = write_demo_sources(paths.dataset / "raw_demo", DemoConfig(seed=args.seed or 7))
        logger.info("demo sources written to %s", manifest)
    if not manifest:
        raise SystemExit("--manifest is required (or pass --demo)")
    with Timer(logger, "step1 build_dataset"):
        summary = build_dataset(_dataset_cfg(args), paths, manifest=manifest, logger=logger)
    print(f"sequences={summary['n_sequences']} clusters={summary['n_clusters']} "
          f"test={summary['split_counts'].get('test', 0)}")
    return 0


def cmd_features(args) -> int:
    from .features import extract_all

    paths = _paths(args)
    logger = get_logger(paths.logs / "extract_features.log")
    with Timer(logger, "step2 extract_features"):
        meta = extract_all(_feature_cfg(args), paths, force=args.force, logger=logger)
    print(f"backend={meta['backend']} embed_dim={meta['embed_dim']} demo={meta['demo_mode']}")
    return 0


def cmd_train(args) -> int:
    from .train import run_training

    paths = _paths(args)
    logger = get_logger(paths.logs / "train.log")
    with Timer(logger, "step3 train_and_eval"):
        payload = run_training(_train_cfg(args), paths, logger=logger,
                               external=not args.no_external, force=args.force)
    print(f"models={[m['model'] for m in payload['models']]}")
    for model in payload["models"]:
        m = model["test_metrics"]
        print(f"  {model['model']:<12} AUROC={m['auroc']:.3f} MCC={m['mcc']:.3f} "
              f"AUPRC={m['auprc']:.3f}")
    return 0


def cmd_report(args) -> int:
    from .report import build_report

    paths = _paths(args)
    logger = get_logger(paths.logs / "report.log")
    # manifest first so the report can honestly show D15 as present, then refresh
    # it so the report/figure files themselves are covered too
    write_file_manifest(paths.root, paths.file_manifest)
    report = build_report(paths, logger=logger, with_figures=not args.no_figures)
    count = write_file_manifest(paths.root, paths.file_manifest)
    print(f"report: {report}")
    print(f"manifest: {paths.file_manifest} ({count} files)")
    return 0


def cmd_all(args) -> int:
    rc = cmd_build(args)
    if rc:
        return rc
    rc = cmd_features(args)
    if rc:
        return rc
    rc = cmd_train(args)
    if rc:
        return rc
    return cmd_report(args)


def cmd_demo(args) -> int:
    """Full pipeline on synthetic data with the mock encoder (plumbing test)."""

    paths = _paths(args)
    logger = get_logger(paths.logs / "demo.log")
    logger.warning("=" * 72)
    logger.warning("DEMO MODE: synthetic peptides + mock embeddings.")
    logger.warning("The metrics below only prove the code runs. They are NOT results.")
    logger.warning("=" * 72)

    from .dataset import build_dataset
    from .features import extract_all
    from .report import build_report
    from .synth import write_demo_sources
    from .train import run_training

    demo_root = paths.dataset / "raw_demo"
    manifest = write_demo_sources(demo_root, DemoConfig(seed=args.seed or 7))
    dataset_cfg = _dataset_cfg(args)
    dataset_cfg.cluster_method = args.cluster_method or "kmer"
    dataset_cfg.max_scrambled = min(dataset_cfg.max_scrambled, 200)
    feature_cfg = _feature_cfg(args)
    feature_cfg.backend = args.backend or "mock"
    feature_cfg.batch_size = min(feature_cfg.batch_size, 64)
    train_cfg = _train_cfg(args)
    train_cfg.models = train_cfg.models if args.models else (
        "M0_RF", "M0_HGB", "M0_CNN_BiGRU", "M1", "M2", "M3", "M3_NOPHYS",
    )
    train_cfg.seeds = train_cfg.seeds if args.seeds else (1, 2)
    train_cfg.folds = args.folds or 3
    train_cfg.epochs = args.epochs or 8
    train_cfg.n_boot = args.n_boot or 300
    train_cfg.num_workers = 0
    train_cfg.patience = 4

    with Timer(logger, "demo step1"):
        build_dataset(dataset_cfg, paths, manifest=manifest, logger=logger)
    with Timer(logger, "demo step2"):
        extract_all(feature_cfg, paths, force=True, logger=logger)
    with Timer(logger, "demo step3"):
        payload = run_training(train_cfg, paths, logger=logger, external=True)
    write_file_manifest(paths.root, paths.file_manifest)
    report = build_report(paths, logger=logger, with_figures=not args.no_figures)
    write_file_manifest(paths.root, paths.file_manifest)

    print("\nDemo complete (numbers are meaningless by construction):")
    for model in payload["models"]:
        m = model["test_metrics"]
        print(f"  {model['model']:<12} AUROC={m['auroc']:.3f} MCC={m['mcc']:.3f}")
    print(f"report: {report}")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dualamp_lite",
        description="DualAMP-Lite: ESM-2 + multi-scale CNN + biophysical priors (plan V3 code companion)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--workdir", default=None,
                        help="output root (default: $DUALAMP_WORKDIR or ./2026-11-09_DualAMP-Lite)")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p, with_manifest=True, with_cluster=True):
        # SUPPRESS keeps a value given *before* the subcommand from being reset
        p.add_argument("--workdir", default=argparse.SUPPRESS,
                       help="output root (default: $DUALAMP_WORKDIR or ./2026-11-09_DualAMP-Lite)")
        if with_manifest:
            p.add_argument("--manifest", default=None, help="YAML source manifest (step 1)")
        if with_cluster:
            p.add_argument("--cluster-method", default=None,
                           choices=["auto", "cdhit", "mmseqs", "kmer", "precomputed"])
            p.add_argument("--cluster-table", default=None, help="precomputed seq/cluster TSV")
            p.add_argument("--cluster-identity", type=float, default=None)
            p.add_argument("--cluster-coverage", type=float, default=None)
            p.add_argument("--test-frac", type=float, default=None)
            p.add_argument("--val-frac", type=float, default=None)
            p.add_argument("--min-len", type=int, default=None)
            p.add_argument("--max-len", type=int, default=None)
            p.add_argument("--no-scrambled", action="store_true")
            p.add_argument("--keep-conflicts", action="store_true")
            p.add_argument("--seed", type=int, default=None)
        p.add_argument("--backend", default=None, choices=["auto", "fair-esm", "transformers", "mock"])
        p.add_argument("--weights-dir", default=None, help="directory with esm2_t12_35M_UR50D.pt")
        p.add_argument("--local-files-only", action="store_true")
        p.add_argument("--model-name", default=None)
        p.add_argument("--hf-model-id", default=None)
        p.add_argument("--repr-layer", type=int, default=None)
        p.add_argument("--batch-size", type=int, default=None)
        p.add_argument("--device", default=None, help="auto | cpu | cuda")
        p.add_argument("--storage-dtype", default=None, choices=["float16", "float32"])
        p.add_argument("--max-residues", type=int, default=None)
        p.add_argument("--redundancy-threshold", type=float, default=None)
        p.add_argument("--force", action="store_true",
                       help="recompute cached features / retrain models (default: resume)")
        p.add_argument("--models", default=None, help="comma list, e.g. M0_RF,M1,M2,M3")
        p.add_argument("--seeds", default=None, help="comma list, e.g. 1,2,3,4,5")
        p.add_argument("--folds", type=int, default=None)
        p.add_argument("--epochs", type=int, default=None)
        p.add_argument("--lr", type=float, default=None)
        p.add_argument("--weight-decay", type=float, default=None)
        p.add_argument("--dropout", type=float, default=None)
        p.add_argument("--patience", type=int, default=None)
        p.add_argument("--loss", default=None, choices=["bce", "focal"])
        p.add_argument("--focal-alpha", type=float, default=None)
        p.add_argument("--focal-gamma", type=float, default=None)
        p.add_argument("--threshold-rule", default=None, choices=["mcc", "youden"])
        p.add_argument("--n-boot", type=int, default=None)
        p.add_argument("--equivalence-margin-mcc", type=float, default=None)
        p.add_argument("--num-workers", type=int, default=None)
        p.add_argument("--no-amp", action="store_true")
        p.add_argument("--no-external", action="store_true")
        p.add_argument("--no-figures", action="store_true")
        p.add_argument("--demo", action="store_true", help="use the synthetic demo sources")

    p_check = sub.add_parser("check", help="environment / GPU / bio-tool check")
    p_check.add_argument("--workdir", default=argparse.SUPPRESS,
                         help="output root (default: $DUALAMP_WORKDIR or ./2026-11-09_DualAMP-Lite)")
    p_check.set_defaults(func=cmd_check)

    p_build = sub.add_parser("build", help="step 1: clean, deduplicate, cluster, split")
    add_common(p_build)
    p_build.set_defaults(func=cmd_build)

    p_features = sub.add_parser("features", help="step 2: ESM-2 + biophysical features")
    add_common(p_features)
    p_features.set_defaults(func=cmd_features)

    p_train = sub.add_parser("train", help="step 3: train, ablate and evaluate")
    add_common(p_train)
    p_train.set_defaults(func=cmd_train)

    p_report = sub.add_parser("report", help="write the markdown report + file manifest")
    add_common(p_report)
    p_report.set_defaults(func=cmd_report)

    p_all = sub.add_parser("all", help="build -> features -> train -> report")
    add_common(p_all)
    p_all.set_defaults(func=cmd_all)

    p_demo = sub.add_parser("demo", help="synthetic end-to-end plumbing test (no GPU needed)")
    add_common(p_demo)
    p_demo.set_defaults(func=cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
