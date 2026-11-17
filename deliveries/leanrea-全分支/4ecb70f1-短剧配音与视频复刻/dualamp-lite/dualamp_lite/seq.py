"""Sequence IO and cleaning.

Amino-acid sequences only: peptide records are normalised, validated against the
canonical alphabet, deduplicated and (optionally) scrambled while preserving the
amino-acid composition (plan §4.1 challenge set).
"""

from __future__ import annotations

import random
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator

from .config import STANDARD_AA_SET

_WHITESPACE = re.compile(r"\s+")
_DIGITS = re.compile(r"[0-9]+")


def clean_sequence(raw: str) -> str:
    """Uppercase, strip whitespace/digits, drop terminal ``*`` and common tags."""

    seq = _WHITESPACE.sub("", str(raw or ""))
    seq = _DIGITS.sub("", seq).upper()
    seq = seq.rstrip("*")
    return seq


def sequence_problems(seq: str, min_len: int = 5, max_len: int = 50) -> str | None:
    """Return a short reason string when a sequence is unusable, else ``None``."""

    if not seq:
        return "empty"
    if len(seq) < min_len:
        return f"too_short(<{min_len})"
    if len(seq) > max_len:
        return f"too_long(>{max_len})"
    if not set(seq) <= STANDARD_AA_SET:
        bad = "".join(sorted(set(seq) - STANDARD_AA_SET))[:10]
        return f"non_standard_residues({bad})"
    return None


def is_valid_sequence(seq: str, min_len: int = 5, max_len: int = 50) -> bool:
    return sequence_problems(seq, min_len, max_len) is None


def read_fasta(path: str | Path) -> Iterator[tuple[str, str]]:
    """Yield ``(header, sequence)`` pairs. Tolerates CRLF and blank lines."""

    header: str | None = None
    chunks: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks)
                header = line[1:].strip()
                chunks = []
            else:
                chunks.append(line)
    if header is not None:
        yield header, "".join(chunks)


def write_fasta(records: Iterable[tuple[str, str]], path: str | Path, width: int = 60) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for header, seq in records:
            fh.write(f">{header}\n")
            for i in range(0, len(seq), width):
                fh.write(seq[i : i + width] + "\n")
            n += 1
    return n


def write_fasta_record(seq: str, header: str) -> str:
    return f">{header}\n{seq}\n"


def aa_composition(seq: str) -> Counter:
    return Counter(seq)


def scramble(seq: str, rng: random.Random | None = None) -> str:
    """Shuffle residues, preserving the amino-acid composition exactly.

    The result is guaranteed to differ from the input for len(seq) > 1 unless
    every residue is identical.
    """

    rng = rng or random.Random()
    residues = list(seq)
    for _ in range(20):
        rng.shuffle(residues)
        candidate = "".join(residues)
        if candidate != seq:
            return candidate
    return "".join(residues)


def gc_content(seq: str) -> float:
    seq = seq.upper()
    return (seq.count("G") + seq.count("C")) / len(seq) if seq else 0.0


def kmer_set(seq: str, k: int) -> set[str]:
    if len(seq) < k:
        return {seq}
    return {seq[i : i + k] for i in range(len(seq) - k + 1)}


def kmer_containment(a: str, b: str, k: int) -> float:
    """Shared k-mers / smaller k-mer set size (0..1), a cheap identity surrogate."""

    ka, kb = kmer_set(a, k), kmer_set(b, k)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / min(len(ka), len(kb))
