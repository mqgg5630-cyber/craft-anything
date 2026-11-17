"""Frozen 32-dimensional biophysical feature schema (V4 section 7).

The list below is the single source of truth. ``feature_schema.json`` is written
from it and every model run records the schema SHA256, so a run can never be
compared against a different feature definition.

    0-19   AAC of ACDEFGHIKLMNPQRSTVWY, fraction in [0, 1] (not percent)
    20     molecular weight, Da (average residue masses, + H2O)
    21     net charge at pH 7.4 (fixed pKa table + N/C termini)
    22     isoelectric point, pH units
    23     GRAVY (Kyte & Doolittle mean hydropathy)
    24     instability index (Guruprasad 1990, via Bio.SeqUtils.ProtParam)
    25     aromaticity = (F + W + Y) / L
    26     alpha hydrophobic moment, 100 deg, Eisenberg scale, window 11
    27     beta hydrophobic moment, 160 deg, Eisenberg scale, window 11
    28     cationic residue ratio = (K + R + H) / L
    29     Boman index, mean Radzicka-Wolfenden transfer free energy (kcal/mol)
    30     aliphatic index = X(Ala) + 2.9 X(Val) + 3.9 [X(Ile) + X(Leu)], mol %
    31     sequence length, residues

Deliberately *not* in the vector (the V3 draft had 34-36 columns because these
were mixed in): ``unstable_flag`` (a thresholded copy of the instability index),
``charge_count_diff`` (a rescaling of the net charge), ``frac_de`` /
``frac_hydrophobic`` / ``frac_helix_forming`` (linear combinations of the AAC
block). The collinearity notes are recorded in the schema file.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from ..biophys import (
    BOMAN_FREE_ENERGY,
    EISENBERG,
    KD_HYDROPATHY,
    PKA_CTERM,
    PKA_NTERM,
    PKA_SIDECHAIN,
    RESIDUE_MASS,
    WATER_MASS,
    aliphatic_index,
    aromaticity,
    boman_index,
    gravy,
    hydrophobic_moment,
    instability_index,
    isoelectric_point,
    molecular_weight,
    net_charge,
)
from ..config import STANDARD_AA

SCHEMA_VERSION = "v1.0"
AA_ORDER = STANDARD_AA
N_AAC = 20
N_FEATURES = 32


@dataclass(frozen=True)
class FeatureSpec:
    index: int
    name: str
    group: str
    unit: str
    formula: str
    source: str
    notes: str = ""


def _aac_specs() -> list[FeatureSpec]:
    out = []
    for i, aa in enumerate(AA_ORDER):
        out.append(
            FeatureSpec(
                index=i,
                name=f"aac_{aa}",
                group="aac",
                unit="fraction (0-1)",
                formula=f"count({aa}) / L",
                source="hand-coded (Biopython get_amino_acids_percent() is deprecated in 1.85 and removed in 1.87)",
                notes="the 20 AAC values sum to 1 exactly - one linear dependency inside the block",
            )
        )
    return out


def _rest_specs() -> list[FeatureSpec]:
    specs = [
        ("molecular_weight", "global", "Da", "sum(residue average masses) + 18.01524", "average residue mass table", "linear in length for a fixed composition"),
        ("net_charge_ph7_4", "global", "elementary charge", "Henderson-Hasselbalch sum over D,E,C,Y,H,K,R + termini", "fixed pKa table (D 3.65, E 4.25, C 8.18, Y 10.07, H 6.00, K 10.53, R 12.48; N 9.69, C-term 2.34)", "sign: acidic residues contribute negative charge"),
        ("isoelectric_point", "global", "pH units", "bisection on net_charge(pH) = 0 over [0, 14], tol 1e-3", "derived from the same pKa table", "monotone transform of the charge composition"),
        ("gravy", "global", "kcal/mol (mean)", "mean Kyte-Doolittle hydropathy", "Kyte & Doolittle 1982", ""),
        ("instability_index", "global", "dimensionless", "Guruprasad 1990 dipeptide instability weights", "Bio.SeqUtils.ProtParam.ProteinAnalysis.instability_index()", "the >40 'unstable' flag is intentionally NOT a separate column"),
        ("aromaticity", "global", "fraction (0-1)", "(count(F)+count(W)+count(Y)) / L", "ProtParam definition", ""),
        ("hydrophobic_moment_alpha", "amphipathicity", "mean Eisenberg hydrophobicity", "max over 11-residue windows of |sum h_i exp(i*100deg*i)| / window", "Eisenberg 1984 consensus scale", "alpha-helical periodicity"),
        ("hydrophobic_moment_beta", "amphipathicity", "mean Eisenberg hydrophobicity", "same with 160deg (beta-strand periodicity)", "Eisenberg 1984 consensus scale", ""),
        ("cationic_residue_ratio", "amphipathicity", "fraction (0-1)", "(count(K)+count(R)+count(H)) / L", "AMP literature convention", "collinear with net charge at pH 7.4 (r > 0.9 on AMP data)"),
        ("boman_index", "supplementary", "kcal/mol (mean)", "mean Radzicka-Wolfenden water->cyclohexane side-chain transfer free energy", "Radzicka & Wolfenden 1988", "sign convention: negative = hydrophilic/poor membrane binding"),
        ("aliphatic_index", "supplementary", "dimensionless (mol %)", "X(Ala) + 2.9 X(Val) + 3.9 [X(Ile) + X(Leu)]", "ExPASy ProtParam", "X in mole percent"),
        ("sequence_length", "supplementary", "residues", "L", "direct", "collinear with molecular weight for a fixed composition"),
    ]
    out = []
    for offset, (name, group, unit, formula, source, notes) in enumerate(specs, start=N_AAC):
        out.append(FeatureSpec(offset, name, group, unit, formula, source, notes))
    return out


FEATURES: tuple[FeatureSpec, ...] = tuple(_aac_specs() + _rest_specs())
FEATURE_NAMES: tuple[str, ...] = tuple(f.name for f in FEATURES)
assert len(FEATURES) == N_FEATURES, len(FEATURES)

COLLINEARITY_NOTES = (
    "AAC block sums to 1 (rank 19): standardise and keep all 20 only for interpretability; "
    "regularised linear baselines must not be interpreted coefficient-wise.",
    "instability_index and the >40 'unstable' flag are the same variable (flag removed).",
    "molecular_weight is an affine function of length for a fixed composition (both kept, documented).",
    "cationic_residue_ratio and net_charge_ph7_4 are strongly correlated (r > 0.9 on AMP data).",
    "alpha/beta hydrophobic moments share the Eisenberg scale but differ in periodicity, so they are kept separately.",
)


def assert_valid(seq: str, min_len: int = 10, max_len: int = 50) -> None:
    """missing_value_policy = error: never silently impute a bad input."""

    if not seq:
        raise ValueError("empty sequence")
    if not (min_len <= len(seq) <= max_len):
        raise ValueError(f"length {len(seq)} outside [{min_len}, {max_len}]")
    bad = sorted(set(seq) - set(AA_ORDER))
    if bad:
        raise ValueError(f"non-standard residues {''.join(bad)}")


def feature_dict(seq: str) -> dict[str, float]:
    """Return the 32 values in frozen order; raises on invalid input."""

    n = len(seq)
    counts = {aa: seq.count(aa) for aa in AA_ORDER}
    values: dict[str, float] = {f"aac_{aa}": counts[aa] / n for aa in AA_ORDER}
    values.update(
        {
            "molecular_weight": float(molecular_weight(seq)),
            "net_charge_ph7_4": float(net_charge(seq, 7.4)),
            "isoelectric_point": float(isoelectric_point(seq)),
            "gravy": float(gravy(seq)),
            "instability_index": float(instability_index(seq)),
            "aromaticity": float(aromaticity(seq)),
            "hydrophobic_moment_alpha": float(hydrophobic_moment(seq, 100.0, 11)),
            "hydrophobic_moment_beta": float(hydrophobic_moment(seq, 160.0, 11)),
            "cationic_residue_ratio": (counts["K"] + counts["R"] + counts["H"]) / n,
            "boman_index": float(boman_index(seq)),
            "aliphatic_index": float(aliphatic_index(seq)),
            "sequence_length": float(n),
        }
    )
    return values


def compute_matrix(seqs: Sequence[str], progress_every: int = 5000, logger=None) -> np.ndarray:
    out = np.zeros((len(seqs), N_FEATURES), dtype=np.float64)
    for i, seq in enumerate(seqs):
        bad = sorted(set(seq) - set(AA_ORDER))
        if not seq or bad:
            raise ValueError(
                f"record {i}: missing_value_policy=error - "
                f"{'empty sequence' if not seq else 'non-standard residues ' + ''.join(bad)}"
            )
        values = feature_dict(seq)
        row = np.array([values[name] for name in FEATURE_NAMES], dtype=np.float64)
        if not np.all(np.isfinite(row)):
            raise ValueError(f"non-finite feature values for sequence {i}: {row}")
        out[i] = row
        if logger is not None and progress_every and (i + 1) % progress_every == 0:
            logger.info("  physchem %d/%d", i + 1, len(seqs))
    return out


def schema_payload() -> dict:
    return {
        "feature_version": SCHEMA_VERSION,
        "n_features": N_FEATURES,
        "aa_order": AA_ORDER,
        "scaling": "StandardScaler",
        "scaling_fit": "per fold on the training part only; final models fit on all Development; the internal test is transformed with the Development scaler",
        "missing_value_policy": "error",
        "aac_scale": "fraction in [0, 1]",
        "hydrophobic_moment_window": 11,
        "hydrophobic_moment_angles_deg": {"alpha": 100.0, "beta": 160.0},
        "pka_table": {**PKA_SIDECHAIN, "N_term": PKA_NTERM, "C_term": PKA_CTERM},
        "tables": {
            "residue_mass_Da": RESIDUE_MASS,
            "water_mass_Da": WATER_MASS,
            "kyte_doolittle": KD_HYDROPATHY,
            "eisenberg": EISENBERG,
            "boman_free_energy_kcal_per_mol": BOMAN_FREE_ENERGY,
        },
        "collinearity_notes": list(COLLINEARITY_NOTES),
        "features": [vars(f) for f in FEATURES],
    }


def write_schema(path: Path) -> tuple[Path, str]:
    payload = schema_payload()
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return path, digest


def schema_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def redundancy_pairs(X: np.ndarray, threshold: float = 0.85) -> list[tuple[str, str, float]]:
    """|Pearson r| above ``threshold`` for every pair of the 32 columns."""

    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2 or X.shape[1] != N_FEATURES:
        raise ValueError(f"expected (n, {N_FEATURES}) matrix, got {X.shape}")
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(X, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0)
    pairs = []
    for i in range(N_FEATURES):
        for j in range(i + 1, N_FEATURES):
            r = float(corr[i, j])
            if abs(r) >= threshold:
                pairs.append((FEATURE_NAMES[i], FEATURE_NAMES[j], r))
    return sorted(pairs, key=lambda t: -abs(t[2]))


def moments_table(X: np.ndarray) -> dict[str, dict[str, float]]:
    out = {}
    for i, name in enumerate(FEATURE_NAMES):
        col = np.asarray(X[:, i], dtype=np.float64)
        out[name] = {
            "mean": float(np.mean(col)),
            "std": float(np.std(col, ddof=0)),
            "min": float(np.min(col)),
            "max": float(np.max(col)),
            "n_unique": int(len(np.unique(col))),
        }
    return out


def finite_columns(X: np.ndarray) -> list[int]:
    X = np.asarray(X)
    return [i for i in range(X.shape[1]) if not np.all(np.isfinite(X[:, i]))]


def zero_variance_columns(X: np.ndarray) -> list[int]:
    X = np.asarray(X)
    return [i for i in range(X.shape[1]) if float(np.var(X[:, i])) == 0.0]


def summarise(seqs: Iterable[str]) -> dict[str, float]:
    values = [feature_dict(s) for s in seqs]
    if not values:
        return {}
    return {k: float(np.mean([v[k] for v in values])) for k in values[0]}


def beta_moment(seq: str) -> float:
    return float(hydrophobic_moment(seq, 160.0, 11))
