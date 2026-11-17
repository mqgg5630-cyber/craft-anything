"""Stage 5 - frozen 32-dim physicochemical matrix and ESM-2 embeddings.

Two blocks are produced, both keyed by ``sequence_id``:

``features/physchem.npz``      raw (unscaled) 32-dim matrix + ids + sequences
``features/esm/<split>.npz``   residue embeddings (L, 480), mean vector (480), mask

Scaling is *not* done here: V4 requires a StandardScaler fitted on the training
part of each fold (final models: fitted on all of Development, then applied once
to the internal test). Storing raw values is what makes that possible.

Backends
--------
``fair-esm``     official weights, ``esm2_t12_35M_UR50D``, layer 12
``transformers`` HuggingFace mirror of the same checkpoint
``mock``         deterministic hash-based stand-in; plumbing only, never quotable

The mock backend exists because this sandbox cannot download the 140 MB ESM-2
checkpoint. Its output shape is identical, so every downstream code path is
exercised, but the resulting numbers must never be reported as ESM-2 results.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..utils import sha256_file
from . import schema
from .config import FeatureConfig, Paths
from .data import read_master
from .qc import assert_all_pass, check_features

SPLITS = ("development", "internal_test", "hard_negative_test", "external_test", "external_homolog", "scrambled_test", "review")


# --------------------------------------------------------------------------- #
# encoders
# --------------------------------------------------------------------------- #


def _aa_base_matrix(embed_dim: int) -> np.ndarray:
    rng = np.random.default_rng(20261109)
    return rng.normal(0.0, 0.35, size=(len(schema.AA_ORDER), embed_dim)).astype(np.float32)


class MockEncoder:
    """Deterministic, composition-aware stand-in for ESM-2 (NOT a real model)."""

    name = "mock"
    is_mock = True

    def __init__(self, embed_dim: int = 480, max_len: int = 50):
        self.embed_dim = embed_dim
        self.max_len = max_len
        self._base = _aa_base_matrix(embed_dim)
        self._index = {aa: i for i, aa in enumerate(schema.AA_ORDER)}

    def encode(self, sequences: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        n = len(sequences)
        L = min(self.max_len, max(len(s) for s in sequences)) if sequences else 1
        residue = np.zeros((n, L, self.embed_dim), dtype=np.float32)
        mask = np.zeros((n, L), dtype=bool)
        for i, seq in enumerate(sequences):
            seed = int.from_bytes(hashlib.sha256(seq.encode()).digest()[:8], "little")
            rng = np.random.default_rng(seed)
            length = min(len(seq), L)
            noise = rng.normal(0.0, 0.25, size=(length, self.embed_dim)).astype(np.float32)
            base = np.stack([self._base[self._index[aa]] for aa in seq[:length]])
            residue[i, :length] = base + noise
            mask[i, :length] = True
        mean = (residue * mask[..., None]).sum(axis=1) / np.maximum(mask.sum(axis=1, keepdims=True), 1)
        return residue.astype(np.float16), mean.astype(np.float32), mask


class FairESMEncoder:
    name = "fair-esm"
    is_mock = False

    def __init__(self, cfg: FeatureConfig, device: str = "cpu"):
        import esm  # noqa: F401 - explicit ImportError is the point

        self.cfg = cfg
        self.device = device
        loader = getattr(esm.pretrained, cfg.esm_model, None)
        if loader is None:
            raise RuntimeError(f"fair-esm has no pretrained loader {cfg.esm_model!r}")
        model, alphabet = loader()
        self.model = model.eval().to(device)
        self.alphabet = alphabet
        self.batch_converter = alphabet.get_batch_converter()
        self.embed_dim = cfg.embed_dim

    def encode(self, sequences: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        import torch

        L = min(self.cfg.max_residues, max(len(s) for s in sequences))
        n = len(sequences)
        residue = np.zeros((n, L, self.embed_dim), dtype=np.float16)
        mean = np.zeros((n, self.embed_dim), dtype=np.float32)
        mask = np.zeros((n, L), dtype=bool)
        bs = max(1, self.cfg.batch_size)
        for start in range(0, n, bs):
            chunk = sequences[start : start + bs]
            labels = [(f"seq{i}", s) for i, s in enumerate(chunk)]
            _, _, tokens = self.batch_converter(labels)
            tokens = tokens[:, : L + 2].to(self.device)
            with torch.no_grad():
                out = self.model(tokens, repr_layers=[self.cfg.repr_layer], return_contacts=False)
            reps = out["representations"][self.cfg.repr_layer][:, 1 : tokens.shape[1] - 1]
            for i, seq in enumerate(chunk):
                length = min(len(seq), L)
                vec = reps[i, :length].float().cpu().numpy()
                residue[start + i, :length] = vec.astype(np.float16)
                mean[start + i] = vec.mean(axis=0)
                mask[start + i, :length] = True
        return residue, mean, mask


class HFEncoder:
    name = "transformers"
    is_mock = False

    def __init__(self, cfg: FeatureConfig, device: str = "cpu"):
        from transformers import AutoModel, AutoTokenizer

        self.cfg = cfg
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(
            cfg.hf_model_id, local_files_only=cfg.local_files_only
        )
        self.model = AutoModel.from_pretrained(cfg.hf_model_id, local_files_only=cfg.local_files_only).eval().to(device)
        self.embed_dim = int(self.model.config.hidden_size)

    def encode(self, sequences: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        import torch

        L = min(self.cfg.max_residues, max(len(s) for s in sequences))
        n = len(sequences)
        residue = np.zeros((n, L, self.embed_dim), dtype=np.float16)
        mean = np.zeros((n, self.embed_dim), dtype=np.float32)
        mask = np.zeros((n, L), dtype=bool)
        bs = max(1, self.cfg.batch_size)
        for start in range(0, n, bs):
            chunk = sequences[start : start + bs]
            enc = self.tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=L + 2)
            enc = {k: v.to(self.device) for k, v in enc.items()}
            with torch.no_grad():
                hidden = self.model(**enc).last_hidden_state[:, 1 : L + 1]
            for i, seq in enumerate(chunk):
                length = min(len(seq), L)
                vec = hidden[i, :length].float().cpu().numpy()
                residue[start + i, :length] = vec.astype(np.float16)
                mean[start + i] = vec.mean(axis=0)
                mask[start + i, :length] = True
        return residue, mean, mask


def build_encoder(cfg: FeatureConfig, device: str = "cpu", logger=None):
    backend = cfg.backend
    if backend == "auto":
        if cfg.weights_dir and Path(cfg.weights_dir).exists() and any(Path(cfg.weights_dir).glob("*.pt")):
            backend = "fair-esm"
        elif cfg.local_files_only:
            backend = "mock"
        else:
            backend = "mock"
        if logger and backend == "mock":
            logger.warning(
                "  no ESM-2 weights available - using the MOCK encoder. "
                "Numbers from this run are plumbing-only and must never be reported."
            )
    if backend == "mock":
        return MockEncoder(cfg.embed_dim, cfg.max_residues)
    if backend == "fair-esm":
        return FairESMEncoder(cfg, device=device)
    if backend == "transformers":
        return HFEncoder(cfg, device=device)
    raise ValueError(f"unknown feature backend {backend!r}")


# --------------------------------------------------------------------------- #
# stage
# --------------------------------------------------------------------------- #


def run_features(cfg, paths: Paths, logger=None, device: str = "cpu") -> dict:
    master = read_master(paths)
    seqs = master["seq"].tolist()
    ids = master["sequence_id"].tolist()

    # --- 32-dim block ------------------------------------------------------
    X = schema.compute_matrix(seqs, logger=logger).astype(np.float32)
    np.savez_compressed(
        paths.physchem,
        X=X,
        ids=np.asarray(ids, dtype=str),
        seq=np.asarray(seqs, dtype=str),
    )
    _, schema_digest = schema.write_schema(paths.feature_schema)
    pd.Series(schema.FEATURE_NAMES).to_csv(paths.physchem_names, index=False, header=["feature"])
    pd.DataFrame(schema.moments_table(X)).T.to_csv(paths.physchem_moments)
    pairs = schema.redundancy_pairs(X, cfg.features.redundancy_threshold)
    pd.DataFrame(pairs, columns=["feature_a", "feature_b", "pearson_r"]).to_csv(paths.redundancy, index=False)

    checks = check_features(X, ids=ids)
    zero_var = schema.zero_variance_columns(X)
    checks.append(
        {
            "check": "no_zero_variance_columns",
            # a real dataset missing an amino acid is a data problem (P0); the
            # synthetic demo only proves the plumbing, so it is reported only.
            "level": "INFO" if cfg.demo_mode else "P0",
            "passed": not zero_var,
            "detail": f"zero-variance columns: {zero_var}",
        }
    )
    assert_all_pass(checks, "features")

    # --- ESM block ---------------------------------------------------------
    paths.esm.mkdir(parents=True, exist_ok=True)
    encoder = build_encoder(cfg.features, device=device, logger=logger)
    index_rows = []
    split_of = dict(zip(master["sequence_id"], _split_lookup(paths, master)))
    for split in SPLITS:
        part = master[master["sequence_id"].isin([i for i, s in split_of.items() if s == split])]
        if part.empty:
            continue
        residue, mean, mask = encoder.encode(part["seq"].tolist())
        np.savez_compressed(
            paths.esm_split(split),
            ids=np.asarray(part["sequence_id"].tolist(), dtype=str),
            residue=residue,
            mean=mean,
            mask=mask,
            seq=np.asarray(part["seq"].tolist(), dtype=str),
        )
        for row, sid in enumerate(part["sequence_id"]):
            index_rows.append({"sequence_id": sid, "split": split, "row": row})
        if logger:
            logger.info("  ESM %-22s %5d x %3d x %d", split, len(part), residue.shape[1], residue.shape[2])

    pd.DataFrame(index_rows).to_csv(paths.esm_index, sep="\t", index=False)

    # weight provenance: the checkpoint files that produced these vectors
    weight_rows = []
    if cfg.features.weights_dir and Path(cfg.features.weights_dir).exists():
        for weight in sorted(Path(cfg.features.weights_dir).glob("*")):
            if weight.is_file():
                weight_rows.append({"path": str(weight), "sha256": sha256_file(weight), "size_bytes": weight.stat().st_size})
    weights_path = paths.features / "esm_weights_sha256.tsv"
    pd.DataFrame(weight_rows, columns=["path", "sha256", "size_bytes"]).to_csv(weights_path, sep="\t", index=False)
    meta = {
        "backend": encoder.name,
        "is_mock": bool(getattr(encoder, "is_mock", False)),
        "embed_dim": int(getattr(encoder, "embed_dim", cfg.features.embed_dim)),
        "repr_layer": cfg.features.repr_layer if not getattr(encoder, "is_mock", False) else None,
        "model": cfg.features.esm_model,
        "storage_dtype": "float16 (residue), float32 (mean)",
        "max_residues": cfg.features.max_residues,
        "schema_version": schema.SCHEMA_VERSION,
        "schema_sha256": schema_digest,
        "feature_names": list(schema.FEATURE_NAMES),
        "qc": checks,
        "redundant_pairs": len(pairs),
        "physchem_sha256": sha256_file(paths.physchem),
        "n_records": int(len(master)),
    }
    (paths.features / "feature_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def _split_lookup(paths: Paths, master: pd.DataFrame) -> list[str]:
    """Map every master record to the split file it was written to."""

    lookup = pd.Series("", index=master["sequence_id"])
    for split in SPLITS:
        path = paths.split_csv(split)
        if path.exists():
            ids = pd.read_csv(path, usecols=["sequence_id"])["sequence_id"]
            lookup.loc[lookup.index.intersection(ids)] = split
    if (lookup == "").any():
        missing = int((lookup == "").sum())
        raise RuntimeError(f"{missing} master records are not present in any split file")
    return lookup.reindex(master["sequence_id"]).tolist()


def load_split_features(paths: Paths, split: str) -> dict:
    blob = np.load(paths.esm_split(split), allow_pickle=False)
    return {
        "ids": blob["ids"].tolist(),
        "residue": blob["residue"],
        "mean": blob["mean"],
        "mask": blob["mask"],
        "seq": blob["seq"].tolist(),
    }


def load_physchem(paths: Paths) -> dict:
    blob = np.load(paths.physchem, allow_pickle=False)
    return {"X": blob["X"], "ids": blob["ids"].tolist(), "seq": blob["seq"].tolist()}
