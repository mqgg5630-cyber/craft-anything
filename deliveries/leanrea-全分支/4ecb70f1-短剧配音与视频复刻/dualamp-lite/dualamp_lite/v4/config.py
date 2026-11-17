"""Paths, defaults and the YAML experiment configuration for the V4 pipeline.

Every artefact lives under one working directory so that the whole deliverable
can be zipped, re-hashed and re-run:

    <workdir>/
        raw/            source exports exactly as downloaded (never modified)
        data/           dataset_master.tsv, excluded_records.tsv, splits/, manifests/
        features/       frozen 32-dim matrix, ESM-2 tensors, feature_schema.json
        runs/<run_id>/  one directory per (model, seed, fold) - never overwritten
        results/<run_id>/ metrics, comparisons, figures, evaluation report
        final_models/<run_id>/ 5 full-development checkpoints + ensemble recipe
        environment/    environment.yml, requirements.lock, environment_info.txt
        SHA256/         per-file hashes of inputs, features, weights, configs, code
        cache/          downloaded ESM weights and cluster scratch files
        logs/           pipeline logs
"""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# --------------------------------------------------------------------------- #
# frozen vocabulary
# --------------------------------------------------------------------------- #

STANDARD_AA = "ACDEFGHIKLMNPQRSTVWY"
SCHEMA_VERSION = "v1.0"

#: data layers (V4 section 6)
LAYERS = (
    "general_amp",
    "bacterial_amp",
    "negative_background",
    "hard_negative",
    "scrambled",
    "external",
)
POSITIVE_LAYERS = ("general_amp", "bacterial_amp")
NEGATIVE_LAYERS = ("negative_background", "hard_negative")
CHALLENGE_ONLY_LAYERS = ("hard_negative", "scrambled")

#: evaluation splits written by the split stage
SPLITS = ("development", "internal_test", "hard_negative_test", "external_test", "scrambled_test")

MODELS = ("M1", "M2", "M3")
BASELINES = ("M0_RF", "M0_HGB")

SUBDIRS = (
    "raw",
    "data",
    "data/splits",
    "data/manifests",
    "features",
    "runs",
    "results",
    "final_models",
    "environment",
    "SHA256",
    "cache",
    "logs",
)

DEFAULT_WORKDIR_NAME = "2026-11-09_DualAMP-Lite"


def default_workdir() -> Path:
    env = os.environ.get("DUALAMP_WORKDIR")
    return Path(env) if env else Path.cwd() / DEFAULT_WORKDIR_NAME


# --------------------------------------------------------------------------- #
# filesystem layout
# --------------------------------------------------------------------------- #


@dataclass
class Paths:
    """Resolve every artefact location from a single working directory."""

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root).expanduser().resolve()
        for sub in SUBDIRS:
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    # anchors -------------------------------------------------------------- #
    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def splits(self) -> Path:
        return self.data / "splits"

    @property
    def manifests(self) -> Path:
        return self.data / "manifests"

    @property
    def features(self) -> Path:
        return self.root / "features"

    @property
    def esm(self) -> Path:
        return self.features / "esm"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def final_models(self) -> Path:
        return self.root / "final_models"

    @property
    def environment(self) -> Path:
        return self.root / "environment"

    @property
    def sha(self) -> Path:
        return self.root / "SHA256"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    # concrete artefacts --------------------------------------------------- #
    @property
    def dataset_master(self) -> Path:
        return self.data / "dataset_master.tsv"

    @property
    def excluded_records(self) -> Path:
        return self.data / "excluded_records.tsv"

    @property
    def label_audit(self) -> Path:
        return self.data / "label_audit.csv"

    @property
    def clusters(self) -> Path:
        return self.data / "clusters.tsv"

    @property
    def feature_schema(self) -> Path:
        return self.features / "feature_schema.json"

    @property
    def physchem(self) -> Path:
        return self.features / "physchem.npz"

    @property
    def physchem_names(self) -> Path:
        return self.features / "physchem_feature_names.tsv"

    @property
    def physchem_moments(self) -> Path:
        return self.features / "physchem_moments.csv"

    @property
    def redundancy(self) -> Path:
        return self.features / "physchem_redundancy.csv"

    def split_csv(self, split: str) -> Path:
        return self.splits / f"{split}.csv"

    def fold_csv(self, seed: int) -> Path:
        return self.splits / f"folds_seed_{seed}.csv"

    def esm_split(self, split: str) -> Path:
        return self.esm / f"{split}.npz"

    @property
    def esm_index(self) -> Path:
        return self.esm / "index.tsv"


# --------------------------------------------------------------------------- #
# experiment configuration
# --------------------------------------------------------------------------- #


@dataclass
class DatasetConfig:
    min_len: int = 10
    max_len: int = 50
    #: cluster identity for the group split (V4 section 6: CD-HIT 0.80)
    cluster_identity: float = 0.80
    cluster_coverage: float = 0.80
    cluster_method: str = "auto"  # auto | cdhit | mmseqs | kmer | precomputed
    cluster_table: str | None = None
    dev_fraction: float = 0.80
    split_seed: int = 20261109
    #: hard negatives are a *challenge* set by default (V4 section 6 table)
    hard_negative_in_training: bool = False
    add_scrambled: bool = True
    max_scrambled: int = 500
    drop_label_conflicts: bool = True


@dataclass
class FeatureConfig:
    #: mock = deterministic stand-in used for plumbing runs only (never quotable)
    backend: str = "auto"  # auto | fair-esm | transformers | mock
    esm_model: str = "esm2_t12_35M_UR50D"
    hf_model_id: str = "facebook/esm2_t12_35M_UR50D"
    repr_layer: int = 12
    embed_dim: int = 480
    batch_size: int = 16
    device: str = "auto"
    storage_dtype: str = "float16"
    max_residues: int = 64
    weights_dir: str | None = None
    local_files_only: bool = False
    #: |r| above which a pair is listed as collinear in physchem_redundancy.csv
    redundancy_threshold: float = 0.85


@dataclass
class TrainConfig:
    models: tuple[str, ...] = MODELS
    baselines: tuple[str, ...] = BASELINES
    seeds: tuple[int, ...] = (11, 23, 37, 53, 71)
    folds: int = 5
    epochs: int = 100
    batch_size: int = 32
    lr: float = 3e-4
    weight_decay: float = 1e-4
    dropout: float = 0.3
    grad_clip: float = 1.0
    patience: int = 10
    #: model selection metric on the inner validation fold (V4 section 11)
    primary_metric: str = "auprc"
    loss: str = "bce"  # bce | focal
    focal_alpha: float = 0.75
    focal_gamma: float = 2.0
    scheduler: str = "plateau"
    threshold_rule: str = "mcc"  # mcc | youden
    n_boot: int = 2000
    boot_alpha: float = 0.05
    equivalence_margin_mcc: float = 0.02
    num_workers: int = 0
    threads: int = 2
    amp: bool = True
    n_final_seeds: int = 5


@dataclass
class DemoConfig:
    n_positive: int = 200
    n_negative: int = 200
    n_hard_negative: int = 40
    n_bacterial: int = 60
    n_external: int = 40
    seed: int = 7


@dataclass
class Config:
    paths: Paths = field(default_factory=lambda: Paths(default_workdir()))
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    demo: DemoConfig = field(default_factory=DemoConfig)
    demo_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "paths": {"root": str(self.paths.root)},
            "dataset": dataclasses.asdict(self.dataset),
            "features": dataclasses.asdict(self.features),
            "train": dataclasses.asdict(self.train),
            "demo": dataclasses.asdict(self.demo),
            "demo_mode": self.demo_mode,
        }

    def write_yaml(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True), encoding="utf-8")
        return path


_SECTION_MAP = {
    "dataset": DatasetConfig,
    "features": FeatureConfig,
    "train": TrainConfig,
    "demo": DemoConfig,
}


def load_config(path: str | Path | None, workdir: str | Path | None = None) -> Config:
    """Load an experiment YAML, rejecting unknown keys (typos must not be silent)."""

    cfg = Config()
    if path is not None:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        unknown = set(payload) - {"dataset", "features", "train", "demo", "demo_mode", "paths"}
        if unknown:
            raise ValueError(f"{path}: unknown top-level keys {sorted(unknown)}")
        for section, klass in _SECTION_MAP.items():
            values = payload.get(section) or {}
            valid = {f.name for f in dataclasses.fields(klass)}
            bad = set(values) - valid
            if bad:
                raise ValueError(f"{path}: unknown {section} keys {sorted(bad)}")
            setattr(cfg, section, klass(**values))
        cfg.demo_mode = bool(payload.get("demo_mode", cfg.demo_mode))
    if workdir is not None:
        cfg.paths = Paths(Path(workdir))
    # YAML gives lists; the dataclasses use tuples for hashability
    cfg.train.models = tuple(cfg.train.models)
    cfg.train.baselines = tuple(cfg.train.baselines)
    cfg.train.seeds = tuple(int(s) for s in cfg.train.seeds)
    if cfg.train.folds < 2:
        raise ValueError("folds must be >= 2")
    if not (0.05 < cfg.dataset.dev_fraction < 0.95):
        raise ValueError("dev_fraction must be in (0.05, 0.95)")
    return cfg
