"""Stage 3 - cleaning, label audit, ``dataset_master.tsv`` / ``excluded_records.tsv``.

The ingestion itself (source manifest, FASTA/CSV/TSV readers, fragmenting UniProt
negatives, deduplication, composition-preserving scramble) is shared with the
legacy module so that the two pipelines cannot disagree about what a sequence is.
What this module adds for V4:

* ``sequence_id`` (stable hash), ``parent_id`` (UniProt accession or the sequence
  itself) and ``record_index`` - the parent id is what blocks precursor-family
  leakage between Development and the internal test;
* ``excluded_records.tsv`` with one row per dropped input (never a silent drop);
* ``label_audit.csv`` with the per-layer label audit required by V4 section 6;
* hard-typed dtypes and a hard failure on anything that would make the frozen
  feature schema invalid (missing values, non-standard residues, wrong length).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import STANDARD_AA
from ..dataset import add_scrambled, deduplicate, load_manifest, read_sources, seq_id
from .config import DatasetConfig, NEGATIVE_LAYERS, POSITIVE_LAYERS, Paths

MASTER_COLUMNS = (
    "record_index",
    "sequence_id",
    "seq",
    "length",
    "label",
    "layer",
    "sources",
    "parent_id",
    "n_source_records",
    "has_bacterial_origin",
    "organism",
    "activity",
    "mic",
    "mic_unit",
    "strain",
    "assay",
    "uniprot_id",
    "notes",
    "activity_label_source",
)

EXCLUDED_COLUMNS = ("sequence_id", "seq", "reason", "detail", "source", "layer")


def _parent_id(uniprot_id: str, sequence_id: str) -> str:
    text = str(uniprot_id or "").strip()
    if not text:
        return sequence_id
    # UniProt headers are aggregated as "P12345 | Q99999"; the first accession is
    # the precursor family key.
    first = text.replace(",", "|").split("|")[0].strip()
    return first or sequence_id


def _enforce_layer_labels(df: pd.DataFrame, manifest: str | Path) -> pd.DataFrame:
    """Labels come from the declared layer, never from a substring of the header.

    The legacy reader guesses a label from ``positive_values`` substrings, which
    misfires on record ids that contain a digit ("demo_external_13" contains
    "1"). V4 therefore re-derives the label from the source manifest:

    * ``general_amp`` / ``bacterial_amp`` -> 1 (experimentally validated AMP)
    * ``negative_background`` / ``hard_negative`` / ``scrambled`` -> 0
    * ``external`` -> the manifest's ``label`` / ``label_column`` value

    This keeps "antiviral/antifungal is not automatically positive" explicit.
    """

    specs, _ = load_manifest(manifest)
    by_source = {spec.id: spec for spec in specs}
    labels = []
    for _, row in df.iterrows():
        layer = str(row["layer"])
        if layer in POSITIVE_LAYERS:
            labels.append(1)
        elif layer in NEGATIVE_LAYERS or layer == "scrambled":
            labels.append(0)
        else:
            spec = by_source.get(str(row["source"]))
            if spec is not None and spec.label is not None:
                labels.append(int(spec.label))
            else:
                labels.append(int(row["label"]))
    out = df.copy()
    out["label"] = labels
    return out


def build_master(manifest: str | Path, cfg: DatasetConfig, paths: Paths, logger=None) -> pd.DataFrame:
    """Read the source manifest and write the frozen master table."""

    df, audit = read_sources(manifest, cfg.min_len, cfg.max_len, logger=logger)
    df = _enforce_layer_labels(df, manifest)
    df = deduplicate(df, cfg.drop_label_conflicts, audit, logger=logger).reset_index(drop=True)
    df["parent_id"] = [
        _parent_id(u, s) for u, s in zip(df.get("uniprot_id", ""), df["seq_id"])
    ]
    df["activity_label_source"] = "source annotation (experimentally validated AMP / curated negative)"

    if cfg.add_scrambled:
        df = add_scrambled(df, cfg.max_scrambled, cfg.split_seed, logger=logger).reset_index(drop=True)
        scrambled = df["layer"] == "scrambled"
        parents = df.loc[scrambled, "sources"].astype(str).str.split(":", n=1).str[1].fillna("")
        df.loc[scrambled, "parent_id"] = parents.to_numpy()
        df.loc[scrambled, "activity_label_source"] = (
            "composition-preserving scramble of a positive (challenge only)"
        )

    df = df.rename(columns={"seq_id": "sequence_id"}).reset_index(drop=True)

    df["record_index"] = np.arange(len(df), dtype=int)
    missing = [c for c in MASTER_COLUMNS if c not in df.columns]
    for column in missing:
        df[column] = ""
    df = df[list(MASTER_COLUMNS)].copy()
    df["label"] = df["label"].astype(int)
    df["length"] = df["length"].astype(int)
    df["n_source_records"] = df["n_source_records"].astype(int)
    df["has_bacterial_origin"] = df["has_bacterial_origin"].astype(int)

    validate_master(df, cfg)

    paths.data.mkdir(parents=True, exist_ok=True)
    df.to_csv(paths.dataset_master, sep="\t", index=False)

    excluded = pd.DataFrame(audit)
    if excluded.empty:
        excluded = pd.DataFrame(columns=list(EXCLUDED_COLUMNS))
    else:
        excluded = excluded.rename(columns={"seq": "seq"})
        for column in EXCLUDED_COLUMNS:
            if column not in excluded.columns:
                excluded[column] = ""
        excluded["sequence_id"] = [seq_id(str(s)) if s else "" for s in excluded["seq"]]
        excluded = excluded[list(EXCLUDED_COLUMNS)]
    excluded.to_csv(paths.excluded_records, sep="\t", index=False)

    write_label_audit(df, excluded, paths, logger=logger)
    if logger:
        logger.info(
            "  master: %d records (%d pos / %d neg), excluded rows: %d",
            len(df),
            int((df["label"] == 1).sum()),
            int((df["label"] == 0).sum()),
            len(excluded),
        )
    return df


def validate_master(df: pd.DataFrame, cfg: DatasetConfig) -> None:
    if df.empty:
        raise RuntimeError("dataset_master is empty")
    if df["seq"].duplicated().any():
        dup = df.loc[df["seq"].duplicated(), "seq"].head(3).tolist()
        raise ValueError(f"duplicate sequences survived deduplication: {dup}")
    if not set(df["label"].unique()) <= {0, 1}:
        raise ValueError(f"labels must be 0/1, got {sorted(df['label'].unique())}")
    bad_len = df[(df["length"] < cfg.min_len) | (df["length"] > cfg.max_len)]
    if len(bad_len):
        raise ValueError(f"{len(bad_len)} sequences outside [{cfg.min_len}, {cfg.max_len}] aa")
    bad_aa = [s for s in df["seq"] if set(s) - set(STANDARD_AA)]
    if bad_aa:
        raise ValueError(f"{len(bad_aa)} sequences contain non-standard residues")
    if df["sequence_id"].duplicated().any():
        raise ValueError("sequence_id collision - widen the hash prefix")


def write_label_audit(df: pd.DataFrame, excluded: pd.DataFrame, paths: Paths, logger=None) -> pd.DataFrame:
    rows = []
    for layer, grp in df.groupby("layer", sort=True):
        rows.append(
            {
                "layer": layer,
                "n_records": len(grp),
                "n_positive": int((grp["label"] == 1).sum()),
                "n_negative": int((grp["label"] == 0).sum()),
                "median_length": float(grp["length"].median()),
                "n_unique_parents": int(grp["parent_id"].nunique()),
                "use": {
                    "general_amp": "training positive",
                    "bacterial_amp": "training positive (subgroup reported separately)",
                    "negative_background": "training negative",
                    "hard_negative": "challenge set (excluded from training by default)",
                    "scrambled": "challenge set only - never a biological negative",
                    "external": "external validation only - never trained or selected on",
                }.get(layer, "review"),
            }
        )
    audit = pd.DataFrame(rows)
    reasons = (
        excluded.groupby(["reason", "detail"]).size().reset_index(name="n")
        if not excluded.empty
        else pd.DataFrame(columns=["reason", "detail", "n"])
    )
    reasons.to_csv(paths.data / "exclusion_reasons.csv", index=False)
    audit.to_csv(paths.label_audit, index=False)
    if logger:
        for _, row in audit.iterrows():
            logger.info(
                "  layer %-20s n=%4d pos=%3d neg=%3d",
                row["layer"], row["n_records"], row["n_positive"], row["n_negative"],
            )
    return audit


def read_master(paths: Paths) -> pd.DataFrame:
    df = pd.read_csv(paths.dataset_master, sep="\t", keep_default_na=False)
    df["label"] = df["label"].astype(int)
    return df


def master_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
