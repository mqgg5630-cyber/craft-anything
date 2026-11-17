"""Biophysical descriptors of plan §3.3 (V3, with the P0 formula fixes).

Feature blocks
--------------
    1. AAC                 20 dims  amino-acid composition, percent (sums to 100)
    2. global               7 dims  MW, net charge @pH 7.4, pI/14, GRAVY,
                                    instability/100, aromaticity, Boman index
    3. amphipathicity       5 dims  hydrophobic moment (100 deg), KRH, DE,
                                    hydrophobic, helix-forming fractions
    4. supplementary        3 dims  length, (KRH - DE) count difference,
                                    instability>40 flag
                          ----
                           35 dims

Why 35 and not the "32" of the V3 table: that table lists 20 + 6 + 5 + 3 = 34
(the "32" is an arithmetic slip in the source document), and the plan separately
requires the Boman index to be *defined with a fixed free-energy source*. Adding
that descriptor gives 35. Per the plan's own P1 rule ("do not force a 32-dim
vector"), the code reports the real dimensionality in
``features/feature_meta.json`` and lets the redundancy analysis drop features.

Formula fixes required by the V3 review (P0):
    * Aliphatic index uses the ExPASy ProtParam definition, which is *not* part of
      the 35-dim vector above; it is provided by :func:`aliphatic_index` and a unit
      test pins the value for a known peptide. (It is highly collinear with AAC and
      therefore folded into the redundancy analysis instead of being duplicated.)
    * Boman index uses one fixed table (Radzicka & Wolfenden 1988, water ->
      cyclohexane side-chain transfer free energies, kcal/mol), summed over
      residues and divided by peptide length. Hydrophobic residues are positive,
      charged/polar residues negative; this matches the convention used by APD.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

from .config import STANDARD_AA

# --------------------------------------------------------------------------- #
# residue tables
# --------------------------------------------------------------------------- #

#: average residue masses (Da), monoisotopic-free averages used for MW estimate
RESIDUE_MASS = {
    "A": 71.0788, "R": 156.1875, "N": 114.1038, "D": 115.0886, "C": 103.1388,
    "E": 129.1155, "Q": 128.1307, "G": 57.0519, "H": 137.1411, "I": 113.1594,
    "L": 113.1594, "K": 128.1741, "M": 131.1926, "F": 147.1766, "P": 97.1167,
    "S": 87.0782, "T": 101.1051, "W": 186.2132, "Y": 163.1760, "V": 99.1326,
}
WATER_MASS = 18.01524

#: Kyte & Doolittle (1982) hydropathy
KD_HYDROPATHY = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

#: Eisenberg et al. (1984) consensus hydrophobicity, used for the hydrophobic moment
EISENBERG = {
    "A": 0.25, "R": -1.80, "N": -0.64, "D": -0.72, "C": 0.04, "Q": -0.69,
    "E": -0.62, "G": 0.16, "H": -0.40, "I": 0.73, "L": 0.53, "K": -1.10,
    "M": 0.26, "F": 0.61, "P": -0.07, "S": -0.26, "T": -0.18, "W": 0.37,
    "Y": 0.02, "V": 0.54,
}

#: Radzicka & Wolfenden (1988) water -> cyclohexane side-chain transfer free energy
#: (kcal/mol). Fixed source for the Boman index, as demanded by the V3 review.
BOMAN_FREE_ENERGY = {
    "A": 1.81, "R": -14.92, "N": -6.64, "D": -8.72, "C": 1.28, "Q": -5.54,
    "E": -6.81, "G": 0.94, "H": -4.66, "I": 2.95, "L": 2.35, "K": -5.55,
    "M": 2.35, "F": 2.98, "P": 0.95, "S": -3.07, "T": -2.57, "W": 2.33,
    "Y": 2.16, "V": 1.99,
}

#: side-chain pKa values used for the charge / pI calculation
PKA_SIDECHAIN = {"D": 3.65, "E": 4.25, "C": 8.18, "Y": 10.07, "H": 6.00, "K": 10.53, "R": 12.48}
PKA_NTERM = 9.69
PKA_CTERM = 2.34
POSITIVE_RESIDUES = "KRH"
NEGATIVE_RESIDUES = "DE"
HYDROPHOBIC_RESIDUES = "AILMFWVY"
HELIX_RESIDUES = "AEMQLW"

AAC_FEATURES = [f"aac_{aa}" for aa in STANDARD_AA]
GLOBAL_FEATURES = [
    "mw_kda",
    "net_charge_ph74",
    "pi_norm",
    "gravy",
    "instability_norm",
    "aromaticity",
    "boman_index",
]
AMPHIPATHIC_FEATURES = [
    "hydrophobic_moment_100deg",
    "frac_krh",
    "frac_de",
    "frac_hydrophobic",
    "frac_helix_forming",
]
SUPPLEMENTARY_FEATURES = ["length", "charge_count_diff", "unstable_flag"]

FEATURE_NAMES: tuple[str, ...] = tuple(
    AAC_FEATURES + GLOBAL_FEATURES + AMPHIPATHIC_FEATURES + SUPPLEMENTARY_FEATURES
)
N_FEATURES = len(FEATURE_NAMES)
FEATURE_GROUPS = {
    "aac": AAC_FEATURES,
    "global": GLOBAL_FEATURES,
    "amphipathicity": AMPHIPATHIC_FEATURES,
    "supplementary": SUPPLEMENTARY_FEATURES,
}


# --------------------------------------------------------------------------- #
# individual descriptors
# --------------------------------------------------------------------------- #


def molecular_weight(seq: str) -> float:
    return sum(RESIDUE_MASS[aa] for aa in seq) + WATER_MASS


def gravy(seq: str) -> float:
    return sum(KD_HYDROPATHY[aa] for aa in seq) / len(seq)


def net_charge(seq: str, ph: float = 7.4) -> float:
    """Henderson-Hasselbalch net charge at ``ph`` (N-term + all ionizable groups)."""

    charge = 1.0 / (1.0 + 10 ** (ph - PKA_NTERM))
    charge -= 1.0 / (1.0 + 10 ** (PKA_CTERM - ph))
    for aa in seq:
        pka = PKA_SIDECHAIN.get(aa)
        if pka is None:
            continue
        frac_protonated = 1.0 / (1.0 + 10 ** (ph - pka))
        if aa in ("H", "K", "R"):
            charge += frac_protonated
        else:  # D, E, C, Y are negative when deprotonated
            charge -= 1.0 - frac_protonated
    return charge


def isoelectric_point(seq: str, tol: float = 1e-3) -> float:
    """Bisection on the charge function over pH 0-14."""

    lo, hi = 0.0, 14.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if net_charge(seq, mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def aromaticity(seq: str) -> float:
    return sum(seq.count(aa) for aa in "FWY") / len(seq)


def hydrophobic_moment(seq: str, angle_deg: float = 100.0, window: int = 11) -> float:
    """Maximum Eisenberg hydrophobic moment per residue over sliding windows."""

    angle = math.radians(angle_deg)
    if len(seq) <= window:
        windows = [seq]
    else:
        windows = [seq[i : i + window] for i in range(len(seq) - window + 1)]
    best = 0.0
    for win in windows:
        sin_sum = sum(EISENBERG[aa] * math.sin((i + 1) * angle) for i, aa in enumerate(win))
        cos_sum = sum(EISENBERG[aa] * math.cos((i + 1) * angle) for i, aa in enumerate(win))
        best = max(best, math.hypot(sin_sum, cos_sum) / len(win))
    return best


def boman_index(seq: str) -> float:
    """Sum of side-chain transfer free energies / length (kcal/mol)."""

    return sum(BOMAN_FREE_ENERGY[aa] for aa in seq) / len(seq)


def aliphatic_index(seq: str) -> float:
    """ExPASy ProtParam aliphatic index (V3 P0 fix, not part of the 35-dim vector).

    AI = X(Ala) + 2.9 * X(Val) + 3.9 * [X(Ile) + X(Leu)], X in mole percent.
    """

    n = len(seq)
    pct = {aa: 100.0 * seq.count(aa) / n for aa in STANDARD_AA}
    return pct["A"] + 2.9 * pct["V"] + 3.9 * (pct["I"] + pct["L"])


def instability_index(seq: str) -> float:
    """Biopython's ProtParam instability index (Guruprasad et al. 1990).

    Biopython is a hard requirement of this package; the import error is explicit
    because silently substituting a different formula would break comparability.
    """

    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
    except ImportError as exc:  # pragma: no cover - requirements pin biopython
        raise ImportError(
            "biopython is required for the instability index: pip install biopython"
        ) from exc
    return float(ProteinAnalysis(seq).instability_index())


# --------------------------------------------------------------------------- #
# vector computation
# --------------------------------------------------------------------------- #


def feature_dict(seq: str) -> dict[str, float]:
    n = len(seq)
    counts = {aa: seq.count(aa) for aa in STANDARD_AA}
    out: dict[str, float] = {f"aac_{aa}": 100.0 * counts[aa] / n for aa in STANDARD_AA}
    instab = instability_index(seq)
    out.update(
        {
            "mw_kda": molecular_weight(seq) / 1000.0,
            "net_charge_ph74": net_charge(seq, 7.4),
            "pi_norm": isoelectric_point(seq) / 14.0,
            "gravy": gravy(seq),
            "instability_norm": instab / 100.0,
            "aromaticity": aromaticity(seq),
            "boman_index": boman_index(seq),
            "hydrophobic_moment_100deg": hydrophobic_moment(seq),
            "frac_krh": sum(counts[aa] for aa in POSITIVE_RESIDUES) / n,
            "frac_de": sum(counts[aa] for aa in NEGATIVE_RESIDUES) / n,
            "frac_hydrophobic": sum(counts[aa] for aa in HYDROPHOBIC_RESIDUES) / n,
            "frac_helix_forming": sum(counts[aa] for aa in HELIX_RESIDUES) / n,
            "length": float(n),
            "charge_count_diff": float(
                sum(counts[aa] for aa in POSITIVE_RESIDUES)
                - sum(counts[aa] for aa in NEGATIVE_RESIDUES)
            ),
            "unstable_flag": float(instab > 40.0),
        }
    )
    return out


def compute_features(seqs: Sequence[str], progress_every: int = 5000, logger=None) -> np.ndarray:
    """Return a ``(n_sequences, N_FEATURES)`` float32 array."""

    out = np.zeros((len(seqs), N_FEATURES), dtype=np.float32)
    for i, seq in enumerate(seqs):
        values = feature_dict(seq)
        out[i] = [values[name] for name in FEATURE_NAMES]
        if logger is not None and progress_every and (i + 1) % progress_every == 0:
            logger.info("  biophys %d/%d", i + 1, len(seqs))
    return out


def redundancy_report(
    X: np.ndarray, names: Sequence[str] = FEATURE_NAMES, threshold: float = 0.85
) -> list[dict]:
    """Highly correlated feature pairs (|r| >= threshold) on the training split.

    Mirrors the P1 rule of the plan: report, group, then compare model performance
    with and without the redundant member - do not silently drop dimensions.
    """

    X = np.asarray(X, dtype=np.float64)
    if X.shape[0] < 3:
        return []
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(X, rowvar=False)
    pairs: list[dict] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            r = corr[i, j]
            if np.isfinite(r) and abs(r) >= threshold:
                pairs.append({"feature_a": names[i], "feature_b": names[j], "pearson_r": float(r)})
    pairs.sort(key=lambda d: -abs(d["pearson_r"]))
    return pairs


def correlation_matrix(X: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.corrcoef(np.asarray(X, dtype=np.float64), rowvar=False)


def feature_documentation() -> dict:
    """Provenance block written into ``features/feature_meta.json``."""

    return {
        "n_features": N_FEATURES,
        "names": list(FEATURE_NAMES),
        "groups": {k: list(v) for k, v in FEATURE_GROUPS.items()},
        "notes": {
            "aac": "mole percent, the 20 values sum to 100 (linear constraint)",
            "net_charge_ph74": "Henderson-Hasselbalch, N-term 9.69 / C-term 2.34, side-chain pKa fixed in code",
            "pi_norm": "isoelectric point / 14 (bisection over pH 0-14)",
            "instability_norm": "Biopython ProtParam instability index / 100",
            "boman_index": "Radzicka & Wolfenden 1988 transfer free energies, kcal/mol, sum / length",
            "hydrophobic_moment_100deg": "Eisenberg 1984 scale, 100 deg, 11-residue windows, per residue",
            "aliphatic_index": "ExPASy ProtParam: A + 2.9 V + 3.9 (I + L) in mole percent; computed but not in the vector because it is collinear with AAC",
            "dimensionality": "the V3 table sums to 34; +1 Boman index = 35 reported features",
        },
    }


def aliphatic_index_many(seqs: Iterable[str]) -> np.ndarray:
    return np.array([aliphatic_index(s) for s in seqs], dtype=np.float32)
