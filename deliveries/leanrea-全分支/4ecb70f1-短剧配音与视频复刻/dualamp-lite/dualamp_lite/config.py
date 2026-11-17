"""Central configuration: paths, label vocabulary and training defaults.

All output goes to one self-contained working directory (plan §8 requires the
30-day deliverables to live in an isolated ``2026-11-09_DualAMP-Lite/`` tree):

    <workdir>/
        dataset/      D1 metadata tables, D2 clean FASTA/CSV, D3 split CSVs
        features/     D4 feature tensors + biophys scaler + feature meta
        baseline/     D5 RF / HGB / CNN-BiGRU results
        model/        D6-D8 baselines & main model weights
        ablation/     D9 ablation table
        figures/      plots (optional, matplotlib only)
        manuscript/   D10/D11/D12 reports, D15 file manifest
        logs/         run logs
        cache/        downloaded ESM-2 weights, cluster scratch files

The working directory defaults to ``$DUALAMP_WORKDIR`` or ``./2026-11-09_DualAMP-Lite``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# vocabulary
# --------------------------------------------------------------------------- #

STANDARD_AA = "ACDEFGHIKLMNPQRSTVWY"
STANDARD_AA_SET = frozenset(STANDARD_AA)

#: Data layers of plan §4.1. `scrambled` is a challenge set, never a biological
#: negative; `external` is never used for training or model selection.
LAYERS = (
    "general_amp",
    "bacterial_amp",
    "negative_background",
    "hard_negative",
    "scrambled",
    "external",
)
TRAINABLE_LAYERS = ("general_amp", "bacterial_amp", "negative_background", "hard_negative")
POSITIVE_LAYERS = ("general_amp", "bacterial_amp")

SUBDIRS = (
    "dataset",
    "features",
    "baseline",
    "model",
    "ablation",
    "figures",
    "manuscript",
    "logs",
    "cache",
)

DEFAULT_WORKDIR_NAME = "2026-11-09_DualAMP-Lite"


@dataclass
class Paths:
    """Resolve every artefact location from a single working directory."""

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root).expanduser().resolve()
        for sub in SUBDIRS:
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    # convenient anchors --------------------------------------------------- #
    @property
    def dataset(self) -> Path:
        return self.root / "dataset"

    @property
    def features(self) -> Path:
        return self.root / "features"

    @property
    def baseline(self) -> Path:
        return self.root / "baseline"

    @property
    def model(self) -> Path:
        return self.root / "model"

    @property
    def ablation(self) -> Path:
        return self.root / "ablation"

    @property
    def figures(self) -> Path:
        return self.root / "figures"

    @property
    def manuscript(self) -> Path:
        return self.root / "manuscript"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    # concrete artefacts --------------------------------------------------- #
    @property
    def dataset_all(self) -> Path:
        return self.dataset / "dataset_all.csv"

    @property
    def dataset_fasta(self) -> Path:
        return self.dataset / "dataset_all.fasta"

    @property
    def split_dir(self) -> Path:
        return self.dataset / "splits"

    @property
    def metadata_table(self) -> Path:
        return self.dataset / "D1_sample_metadata.csv"

    @property
    def label_audit(self) -> Path:
        return self.dataset / "label_audit.csv"

    @property
    def cluster_table(self) -> Path:
        return self.dataset / "clusters.tsv"

    @property
    def feature_meta(self) -> Path:
        return self.features / "feature_meta.json"

    @property
    def scaler(self) -> Path:
        return self.features / "biophys_scaler.joblib"

    @property
    def correlation_table(self) -> Path:
        return self.features / "biophys_correlation.csv"

    def split_features(self, split: str) -> Path:
        return self.features / f"{split}_feat.npz"

    def split_csv(self, split: str) -> Path:
        return self.split_dir / f"{split}.csv"

    @property
    def metrics_table(self) -> Path:
        return self.manuscript / "D10_test_metrics.csv"

    @property
    def ablation_table(self) -> Path:
        return self.ablation / "D9_ablation.csv"

    @property
    def report(self) -> Path:
        return self.manuscript / "D10_evaluation_report.md"

    @property
    def file_manifest(self) -> Path:
        return self.manuscript / "D15_input_sha256.tsv"


def default_workdir() -> Path:
    env = os.environ.get("DUALAMP_WORKDIR")
    return Path(env) if env else Path.cwd() / DEFAULT_WORKDIR_NAME


# --------------------------------------------------------------------------- #
# step 1 defaults
# --------------------------------------------------------------------------- #


@dataclass
class DatasetConfig:
    min_len: int = 5
    max_len: int = 50
    #: sequences outside the canonical alphabet are dropped and audited
    allow_ambiguous: bool = False
    #: cluster identity used for the group-based split (plan §5)
    cluster_identity: float = 0.4
    cluster_coverage: float = 0.8
    cluster_method: str = "auto"  # auto | cdhit | mmseqs | kmer | precomputed
    cluster_table: str | None = None  # for method="precomputed"
    test_frac: float = 0.15
    val_frac: float = 0.15
    seed: int = 20261109
    #: generate a composition-preserving scrambled copy of every positive
    add_scrambled: bool = True
    #: a sequence appearing in more than one layer with conflicting labels is
    #: written to label_audit.csv and excluded from training (manual review).
    drop_conflicts: bool = True
    #: cap on positives used to build the scrambled challenge set (runtime guard)
    max_scrambled: int = 500


# --------------------------------------------------------------------------- #
# step 2 defaults
# --------------------------------------------------------------------------- #


@dataclass
class FeatureConfig:
    backend: str = "auto"  # auto | fair-esm | transformers | mock
    model_name: str = "esm2_t12_35M_UR50D"
    hf_model_id: str = "facebook/esm2_t12_35M_UR50D"
    repr_layer: int = 12
    embed_dim: int = 480
    batch_size: int = 32
    device: str = "auto"
    #: float16 halves the D4 tensor size (~4x headroom on T4 / Kaggle 20 GB)
    storage_dtype: str = "float16"
    max_residues: int = 512
    weights_dir: str | None = None
    local_files_only: bool = False
    #: |r| above which biophysical features are reported as a redundant group
    redundancy_threshold: float = 0.85


# --------------------------------------------------------------------------- #
# step 3 defaults
# --------------------------------------------------------------------------- #


@dataclass
class TrainConfig:
    models: tuple[str, ...] = ("M0_RF", "M0_HGB", "M0_CNN_BiGRU", "M1", "M2", "M3")
    seeds: tuple[int, ...] = (1, 2, 3, 4, 5)
    folds: int = 5
    epochs: int = 60
    batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 1e-4
    dropout: float = 0.3
    patience: int = 12
    #: loss: bce | focal (focal alpha/gamma are searched on the dev folds only)
    loss: str = "bce"
    focal_alpha: float = 0.75
    focal_gamma: float = 2.0
    #: "mcc" | "youden" - threshold is tuned on out-of-fold dev predictions
    threshold_rule: str = "mcc"
    n_boot: int = 2000
    boot_alpha: float = 0.05
    #: equivalence margin for "no meaningful difference" statements (plan §5)
    equivalence_margin_mcc: float = 0.02
    num_workers: int = 2
    amp: bool = True
    seed_everything: bool = True
    tune_threshold_models: bool = True


# --------------------------------------------------------------------------- #
# demo mode (plumbing smoke test - never a scientific result)
# --------------------------------------------------------------------------- #


@dataclass
class DemoConfig:
    n_positive: int = 240
    n_negative: int = 240
    n_hard_negative: int = 60
    n_bacterial: int = 80
    n_external: int = 60
    seed: int = 7


@dataclass
class Config:
    paths: Paths = field(default_factory=lambda: Paths(default_workdir()))
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    demo: DemoConfig = field(default_factory=DemoConfig)
    demo_mode: bool = False

    def to_dict(self) -> dict:
        import dataclasses

        return {
            "paths": {"root": str(self.paths.root)},
            "dataset": dataclasses.asdict(self.dataset),
            "features": dataclasses.asdict(self.features),
            "train": {
                **dataclasses.asdict(self.train),
                "models": list(self.train.models),
                "seeds": list(self.train.seeds),
            },
            "demo": dataclasses.asdict(self.demo),
            "demo_mode": self.demo_mode,
        }
