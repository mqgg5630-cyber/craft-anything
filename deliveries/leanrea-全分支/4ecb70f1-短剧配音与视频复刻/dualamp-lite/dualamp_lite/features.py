"""Step 2 - ESM-2 frozen features + biophysical priors (plan §3.2, §3.3, D4).

Two representation streams are produced, exactly as the V3 architecture requires:

* ``residue``  (N, L, 480) float16 - per-residue ESM-2 layer-12 states, BOS/EOS
  and padding stripped. Never mean-pooled before the CNN branch, otherwise the
  positional information needed by the multi-scale 1D-CNN would be destroyed.
* ``mean``     (N, 480) float32 - **masked** mean pooling over real residues only
  (no BOS/CLS/EOS/padding), the V3 P0 fix.

Plus the 35-dim biophysical block, standardised with a scaler fitted on the
training split only.

Backends
--------
``fair-esm``   ``esm2_t12_35M_UR50D`` via the official `fair-esm` package
``transformers`` HuggingFace ``facebook/esm2_t12_35M_UR50D``
``mock``       fixed random projection of one-hot residues - plumbing test only.

The mock backend lets the whole pipeline run on a machine with no GPU, no internet
and no ESM-2 weights (CI, Kaggle smoke test). It is *not* a scientific embedding
and every artifact it touches is tagged ``"backend": "mock"``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import time
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from . import biophys
from .config import STANDARD_AA, FeatureConfig, Paths
from .utils import get_logger, human_bytes, write_json

SPLITS = ("train", "val", "test", "external", "scrambled")


# --------------------------------------------------------------------------- #
# encoders
# --------------------------------------------------------------------------- #


class MockEncoder:
    """Deterministic fixed projection of one-hot residues + tiny noise.

    Purpose: exercise every code path (tensor shapes, masking, checkpointing,
    metrics) without downloading 140 MB of weights. Composition is preserved, so
    a model *can* fit the synthetic demo labels - which is what makes the smoke
    test useful - but the numbers carry no biological meaning.
    """

    name = "mock"

    def __init__(self, dim: int = 480, seed: int = 20261109) -> None:
        rng = np.random.default_rng(seed)
        self.projection = rng.normal(0.0, 1.0 / np.sqrt(len(STANDARD_AA)), size=(len(STANDARD_AA), dim))
        self.dim = dim
        self.noise_scale = 0.05

    def encode(self, seqs: Sequence[str], batch_size: int = 256):
        max_len = max(len(s) for s in seqs)
        n = len(seqs)
        residue = np.zeros((n, max_len, self.dim), dtype=np.float32)
        mask = np.zeros((n, max_len), dtype=bool)
        for i, seq in enumerate(seqs):
            idx = [STANDARD_AA.index(aa) for aa in seq]
            vec = self.projection[idx]
            rng = np.random.default_rng(int(hashlib.sha1(seq.encode()).hexdigest()[:8], 16))
            residue[i, : len(seq)] = vec + rng.normal(0, self.noise_scale, size=vec.shape)
            mask[i, : len(seq)] = True
        mean = (residue * mask[..., None]).sum(1) / mask.sum(1, keepdims=True)
        return residue, mask, mean.astype(np.float32)


class FairESMEncoder:
    name = "fair-esm"

    def __init__(self, cfg: FeatureConfig, device) -> None:
        import esm  # type: ignore
        import torch

        self.torch = torch
        weights = None
        if cfg.weights_dir:
            candidate = Path(cfg.weights_dir).expanduser() / f"{cfg.model_name}.pt"
            if candidate.exists():
                weights = str(candidate)
        if weights:
            self.model, self.alphabet = esm.pretrained.load_model_and_alphabet_local(weights)
        else:
            loader = getattr(esm.pretrained, cfg.model_name, None)
            if loader is None:
                raise ValueError(f"fair-esm has no loader {cfg.model_name!r}")
            self.model, self.alphabet = loader()
        self.model.eval().to(device)
        self.device = device
        self.cfg = cfg
        self.batch_converter = self.alphabet.get_batch_converter()
        self.dim = int(getattr(self.model, "embed_dim", cfg.embed_dim))
        self.pad_idx = self.alphabet.padding_idx
        self.special = {self.alphabet.cls_idx, self.alphabet.eos_idx, self.alphabet.padding_idx}

    def encode(self, seqs: Sequence[str], batch_size: int = 32):
        torch = self.torch
        max_len = min(self.cfg.max_residues, max(len(s) for s in seqs))
        n = len(seqs)
        residue = np.zeros((n, max_len, self.dim), dtype=np.float32)
        mask = np.zeros((n, max_len), dtype=bool)
        with torch.no_grad():
            for start in range(0, n, batch_size):
                chunk = seqs[start : start + batch_size]
                _, _, tokens = self.batch_converter([(str(i), s) for i, s in enumerate(chunk)])
                tokens = tokens[:, : max_len + 2].to(self.device)
                out = self.model(tokens, repr_layers=[self.cfg.repr_layer], return_contacts=False)
                rep = out["representations"][self.cfg.repr_layer]
                for i, seq in enumerate(chunk):
                    length = min(len(seq), max_len)
                    residue[start + i, :length] = rep[i, 1 : length + 1].float().cpu().numpy()
                    mask[start + i, :length] = True
        mean = (residue * mask[..., None]).sum(1) / mask.sum(1, keepdims=True)
        return residue, mask, mean.astype(np.float32)


class HFEncoder:
    name = "transformers"

    def __init__(self, cfg: FeatureConfig, device) -> None:
        from transformers import AutoModel, AutoTokenizer
        import torch

        self.torch = torch
        kwargs = {"local_files_only": cfg.local_files_only}
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.hf_model_id, **kwargs)
        self.model = AutoModel.from_pretrained(cfg.hf_model_id, **kwargs).eval().to(device)
        self.device = device
        self.cfg = cfg
        self.dim = int(self.model.config.hidden_size)

    def encode(self, seqs: Sequence[str], batch_size: int = 32):
        torch = self.torch
        max_len = min(self.cfg.max_residues, max(len(s) for s in seqs))
        n = len(seqs)
        residue = np.zeros((n, max_len, self.dim), dtype=np.float32)
        mask = np.zeros((n, max_len), dtype=bool)
        with torch.no_grad():
            for start in range(0, n, batch_size):
                chunk = seqs[start : start + batch_size]
                batch = self.tokenizer(
                    list(chunk), return_tensors="pt", padding=True, truncation=True,
                    max_length=max_len + 2,
                )
                batch = {k: v.to(self.device) for k, v in batch.items()}
                out = self.model(**batch, output_hidden_states=True)
                hidden = out.hidden_states[self.cfg.repr_layer]
                for i, seq in enumerate(chunk):
                    length = min(len(seq), max_len)
                    residue[start + i, :length] = hidden[i, 1 : length + 1].float().cpu().numpy()
                    mask[start + i, :length] = True
        mean = (residue * mask[..., None]).sum(1) / mask.sum(1, keepdims=True)
        return residue, mask, mean.astype(np.float32)


def build_encoder(cfg: FeatureConfig, device, logger=None):
    backend = cfg.backend
    if backend == "auto":
        if cfg.weights_dir and (Path(cfg.weights_dir).expanduser() / f"{cfg.model_name}.pt").exists():
            backend = "fair-esm"
        elif importlib.util.find_spec("esm") is not None:
            backend = "fair-esm"
        elif importlib.util.find_spec("transformers") is not None:
            backend = "transformers"
        else:
            backend = "mock"
    if logger:
        logger.info("feature backend: %s", backend)
    if backend == "fair-esm":
        return FairESMEncoder(cfg, device)
    if backend == "transformers":
        return HFEncoder(cfg, device)
    if backend == "mock":
        if logger:
            logger.warning(
                "MOCK encoder - deterministic random projection, no ESM-2 weights. "
                "Install fair-esm and pass --backend fair-esm for real features."
            )
        return MockEncoder(dim=cfg.embed_dim)
    raise ValueError(f"unknown backend {backend!r}")


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #


def _read_split(paths: Paths, split: str) -> pd.DataFrame:
    path = paths.split_csv(split)
    if not path.exists():
        return pd.DataFrame(columns=["seq_id", "seq", "label", "cluster", "layer"])
    df = pd.read_csv(path)
    return df[df["seq"].notna()].copy()


def _save_split(
    path: Path,
    residue: np.ndarray,
    mask: np.ndarray,
    mean: np.ndarray,
    physio: np.ndarray,
    df: pd.DataFrame,
    storage_dtype: str,
) -> None:
    dtype = np.float16 if storage_dtype == "float16" else np.float32
    np.savez(
        path,
        residue=residue.astype(dtype),
        mask=mask.astype(bool),
        mean=mean.astype(np.float32),
        physio=physio.astype(np.float32),
        physio_names=np.array(biophys.FEATURE_NAMES),
        labels=df["label"].to_numpy(dtype=np.int64),
        clusters=df["cluster"].to_numpy(dtype=np.int64),
        seq_ids=df["seq_id"].to_numpy(dtype=str),
        seqs=df["seq"].to_numpy(dtype=str),
        layers=df["layer"].to_numpy(dtype=str),
    )


def load_split(paths: Paths, split: str) -> dict:
    path = paths.split_features(split)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing - run `python -m dualamp_lite features` first (step 2)"
        )
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def extract_all(
    cfg: FeatureConfig,
    paths: Paths,
    splits: Iterable[str] = SPLITS,
    force: bool = False,
    logger=None,
) -> dict:
    from .utils import device_of

    logger = logger or get_logger(paths.logs / "extract_features.log")
    device = device_of(cfg.device)
    logger.info("device: %s", device)
    started = time.time()

    frames = {split: _read_split(paths, split) for split in splits}
    frames = {k: v for k, v in frames.items() if len(v)}
    if "train" not in frames:
        raise RuntimeError("no train split found - run step 1 (`python -m dualamp_lite build`) first")

    # biophys + scaler (fit on train only, plan §5)
    from sklearn.preprocessing import StandardScaler
    import joblib

    raw_physio = {
        split: biophys.compute_features(df["seq"].tolist(), logger=logger)
        for split, df in frames.items()
    }
    train_raw = raw_physio["train"]
    if not np.isfinite(train_raw).all():
        bad = int((~np.isfinite(train_raw)).sum())
        raise RuntimeError(f"{bad} non-finite biophysical values - check sequences for non-standard residues")
    scaler = StandardScaler().fit(train_raw)
    joblib.dump(scaler, paths.scaler)

    pairs = biophys.redundancy_report(train_raw, threshold=cfg.redundancy_threshold)
    pd.DataFrame(
        [
            {"feature_a": name, "feature_b": name, "pearson_r": 1.0}
            for name in biophys.FEATURE_NAMES
        ]
        + pairs
    ).to_csv(paths.correlation_table, index=False)
    logger.info(
        "biophys: %d features, %d pairs with |r| >= %.2f (see %s)",
        len(biophys.FEATURE_NAMES),
        len(pairs),
        cfg.redundancy_threshold,
        paths.correlation_table.name,
    )

    # memory guard: floating-point residue tensors are (N, L, D); a 50k-peptide
    # project needs >2 GB of RAM for the raw float32 buffer alone
    peak_bytes = int(len(frames["train"]) * cfg.max_residues * cfg.embed_dim * 4 * 1.2)
    if peak_bytes > 4 * 1024**3:
        logger.warning(
            "  estimated residue-tensor RAM ~%.1f GB for the train split; consider "
            "splitting the dataset or lowering --max-residues", peak_bytes / 1024**3
        )

    # ESM-2 features
    encoder = build_encoder(cfg, device, logger=logger)
    meta_splits: dict[str, dict] = {}
    for split, df in frames.items():
        out_path = paths.split_features(split)
        if out_path.exists() and not force:
            logger.info("  %s: cached %s, skipping", split, out_path.name)
            meta_splits[split] = {"cached": True, "n": int(len(df))}
            continue
        t0 = time.time()
        residue, mask, mean = encoder.encode(df["seq"].tolist(), batch_size=cfg.batch_size)
        physio = scaler.transform(raw_physio[split]).astype(np.float32)
        _save_split(out_path, residue, mask, mean, physio, df, cfg.storage_dtype)
        meta_splits[split] = {
            "n": int(len(df)),
            "max_len": int(residue.shape[1]),
            "dtype": cfg.storage_dtype,
            "seconds": round(time.time() - t0, 1),
            "bytes": out_path.stat().st_size,
        }
        logger.info(
            "  %s: %d x %d x %d (%s) in %.1fs -> %s",
            split,
            residue.shape[0],
            residue.shape[1],
            residue.shape[2],
            human_bytes(out_path.stat().st_size),
            time.time() - t0,
            out_path.name,
        )

    backend = getattr(encoder, "name", "unknown")
    if backend == "mock":
        model_name = "mock (deterministic one-hot projection - plumbing only)"
    elif backend == "fair-esm":
        model_name = cfg.model_name
    else:
        model_name = cfg.hf_model_id
    meta = {
        "backend": backend,
        "model_name": model_name,
        "repr_layer": cfg.repr_layer,
        "embed_dim": int(getattr(encoder, "dim", cfg.embed_dim)),
        "pooling": "masked mean over residues (no BOS/CLS/EOS/padding)",
        "splits": meta_splits,
        "biophys": {
            **biophys.feature_documentation(),
            "scaler": "StandardScaler fitted on train only",
            "redundant_pairs": len(pairs),
            "redundancy_threshold": cfg.redundancy_threshold,
        },
        "config": {
            "batch_size": cfg.batch_size,
            "max_residues": cfg.max_residues,
            "storage_dtype": cfg.storage_dtype,
            "device": str(device),
        },
        "elapsed_seconds": round(time.time() - started, 1),
        "demo_mode": backend == "mock",
    }
    write_json(paths.feature_meta, meta)
    if meta["backend"] == "mock":
        logger.warning("features were produced by the MOCK backend - not usable for the paper")
    return meta
