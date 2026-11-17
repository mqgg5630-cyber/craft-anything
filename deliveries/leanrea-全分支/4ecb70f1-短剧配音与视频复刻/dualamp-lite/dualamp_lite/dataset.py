"""Step 1 - build the five-layer AMP dataset, deduplicate it, cluster it and split it.

Implements plan §4.1 (data layers), §4.2 hooks (metadata table) and §5 (all
sequences clustered together, homology clusters never straddle train/val/test).

Usage
-----
    python -m dualamp_lite build --manifest configs/sources_example.yaml
    python -m dualamp_lite demo            # synthetic plumbing test
    python -m dualamp_lite build --cluster-method kmer   # no CD-HIT installed

Outputs (in ``<workdir>/dataset/``)
-----------------------------------
    dataset_all.csv / dataset_all.fasta   D2  cleaned, deduplicated records
    splits/{train,val,dev,test,external,scrambled}.csv   D3
    clusters.tsv                          homology cluster membership
    label_audit.csv                       dropped / conflicting / ambiguous rows
    dataset_summary.json                  counts for the report
    D1_sample_metadata.csv                template for the AD cohort metadata task
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

from .config import LAYERS, POSITIVE_LAYERS, TRAINABLE_LAYERS, DatasetConfig, Paths
from .seq import clean_sequence, is_valid_sequence, read_fasta, scramble, sequence_problems, write_fasta
from .utils import get_logger, sha256_file, write_json

META_COLUMNS = (
    "organism",
    "activity",
    "mic",
    "mic_unit",
    "strain",
    "assay",
    "uniprot_id",
    "notes",
)

LAYER_LABEL = {
    "general_amp": 1,
    "bacterial_amp": 1,
    "negative_background": 0,
    "hard_negative": 0,
    "scrambled": 0,  # never used for training; kept for the challenge evaluation
    "external": -1,  # label comes from the source file
}

LAYER_PRECEDENCE = {
    "general_amp": 0,
    "bacterial_amp": 1,
    "hard_negative": 2,
    "negative_background": 3,
    "external": 4,
    "scrambled": 5,
}


# --------------------------------------------------------------------------- #
# source manifest
# --------------------------------------------------------------------------- #


@dataclass
class SourceSpec:
    id: str
    path: str
    format: str = "fasta"
    layer: str = "general_amp"
    seq_column: str = "sequence"
    label_column: str | None = None
    label: int | None = None
    positive_values: list[str] = field(default_factory=lambda: ["1", "true", "yes", "active", "validated", "experimentally validated"])
    negative_values: list[str] = field(default_factory=lambda: ["0", "false", "no", "inactive", "not active"])
    metadata: dict[str, str] = field(default_factory=dict)
    filters: dict[str, Any] = field(default_factory=dict)
    delimiter: str | None = None
    min_len: int | None = None
    max_len: int | None = None
    limit: int | None = None
    #: cut random fragments out of long proteins (UniProt negative background):
    #: {min_len, max_len, per_protein, seed, exclude_keywords}
    fragment: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.layer not in LAYERS:
            raise ValueError(f"source {self.id}: unknown layer {self.layer!r}; expected one of {LAYERS}")
        if self.format not in ("fasta", "csv", "tsv"):
            raise ValueError(f"source {self.id}: unsupported format {self.format!r}")


def load_manifest(path: str | Path) -> tuple[list[SourceSpec], Path]:
    path = Path(path).expanduser().resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    specs = []
    for entry in payload.get("sources", []):
        unknown = set(entry) - {f for f in SourceSpec.__dataclass_fields__}
        if unknown:
            raise ValueError(f"{path.name}: source {entry.get('id')} has unknown keys {sorted(unknown)}")
        specs.append(SourceSpec(**entry))
    if not specs:
        raise ValueError(f"{path} defines no sources")
    return specs, path.parent


def _apply_filters(df: pd.DataFrame, spec: SourceSpec, audit: list[dict]) -> pd.DataFrame:
    """Column-level filters declared in the manifest (equals / notna / contains)."""

    filters = spec.filters or {}
    before = len(df)
    for column in filters.get("notna", []) or []:
        if column in df.columns:
            df = df[df[column].notna() & (df[column].astype(str).str.strip() != "")]
    for column, values in (filters.get("equals") or {}).items():
        if column not in df.columns:
            raise ValueError(f"source {spec.id}: filter column {column!r} not found")
        wanted = {str(v).strip().lower() for v in ([values] if isinstance(values, str) else values)}
        df = df[df[column].astype(str).str.strip().str.lower().isin(wanted)]
    for column, needles in (filters.get("contains") or {}).items():
        if column not in df.columns:
            raise ValueError(f"source {spec.id}: filter column {column!r} not found")
        pattern = "|".join(str(n) for n in ([needles] if isinstance(needles, str) else needles))
        df = df[df[column].astype(str).str.contains(pattern, case=False, na=False, regex=True)]
    if len(df) != before:
        audit.append(
            {
                "reason": "source_filter",
                "detail": f"{spec.id}: {before - len(df)} rows removed by manifest filters ({filters})",
                "source": spec.id,
            }
        )
    return df


def _read_table(path: Path, spec: SourceSpec) -> list[dict]:
    """Return raw records as dicts with at least ``sequence`` (and optional label)."""

    if spec.format == "fasta":
        records = []
        fragment_cfg = spec.fragment or None
        rng = __import__("random").Random(int((fragment_cfg or {}).get("seed", 0)))
        exclude = [k.lower() for k in (fragment_cfg or {}).get("exclude_keywords", []) if k]
        for header, raw in read_fasta(path):
            if fragment_cfg and raw:
                if any(key in header.lower() for key in exclude):
                    continue
                lo = int(fragment_cfg.get("min_len", 5))
                hi = int(fragment_cfg.get("max_len", 50))
                if len(raw) < lo:
                    continue
                for _ in range(int(fragment_cfg.get("per_protein", 1))):
                    length = rng.randint(lo, min(hi, len(raw)))
                    start = rng.randint(0, len(raw) - length)
                    records.append(
                        {
                            "sequence": raw[start : start + length],
                            "header": header,
                            "_label": LAYER_LABEL[spec.layer] if spec.label is None else spec.label,
                            "_uniprot_id": header.split("|")[1] if "|" in header else header.split()[0],
                            "_organism": _header_field(header, spec.metadata.get("organism", "")) if spec.metadata.get("organism") else "",
                        }
                    )
                continue
            meta = spec.metadata
            records.append(
                {
                    "sequence": raw,
                    "header": header,
                    "_label": _label_from_text(header, spec),
                    "_organism": _header_field(header, meta.get("organism", "")) if meta.get("organism") else "",
                    "_activity": _header_field(header, meta.get("activity", "")) if meta.get("activity") else "",
                }
            )
        return records

    sep = spec.delimiter or ("\t" if spec.format == "tsv" else ",")
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False, low_memory=False)
    if spec.seq_column not in df.columns:
        raise ValueError(
            f"source {spec.id}: sequence column {spec.seq_column!r} not in {list(df.columns)[:20]}"
        )
    df = _apply_filters(df, spec, [])
    if spec.limit:
        df = df.head(spec.limit)
    records = []
    for _, row in df.iterrows():
        rec = {"sequence": row[spec.seq_column], "header": f"{spec.id}:{_}", "_label": None}
        if spec.label_column:
            rec["_label"] = _label_from_text(str(row.get(spec.label_column, "")), spec)
        for target, column in (spec.metadata or {}).items():
            if column in df.columns:
                rec[f"_{target}"] = str(row.get(column, ""))
        records.append(rec)
    return records


def _label_from_text(text: str, spec: SourceSpec) -> int | None:
    value = str(text or "").strip().lower()
    if not value:
        return spec.label
    if any(v.lower() in value for v in spec.positive_values):
        return 1
    if any(v.lower() in value for v in spec.negative_values):
        return 0
    return spec.label


def _header_field(header: str, key: str) -> str:
    """Extract ``key=value`` / ``key:value`` from a FASTA header when requested."""

    if not key:
        return ""
    for sep in ("=", ":", "|"):
        for token in header.replace("|", " | ").split():
            if sep in token:
                k, _, v = token.partition(sep)
                if k.strip().lower() == key.lower():
                    return v.strip()
    return ""


def read_sources(manifest: str | Path, min_len: int, max_len: int, logger=None) -> tuple[pd.DataFrame, list[dict]]:
    specs, base = load_manifest(manifest)
    audit: list[dict] = []
    frames: list[pd.DataFrame] = []
    for spec in specs:
        path = (base / spec.path).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve() if not path.exists() else path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"source {spec.id}: {path} does not exist")
        records = _read_table(path, spec)
        rows = []
        for rec in records:
            seq = clean_sequence(rec.get("sequence", ""))
            label = rec.get("_label")
            if label is None:
                label = LAYER_LABEL[spec.layer]
            row = {
                "seq": seq,
                "label": label,
                "layer": spec.layer,
                "source": spec.id,
            }
            for meta in META_COLUMNS:
                row[meta] = rec.get(f"_{meta}", "")
            rows.append(row)
        df = pd.DataFrame(rows)
        if df.empty:
            audit.append({"reason": "empty_source", "detail": f"{spec.id}: no records parsed", "source": spec.id})
            continue
        # per-source length filter (falls back to the global one)
        lo = spec.min_len if spec.min_len is not None else min_len
        hi = spec.max_len if spec.max_len is not None else max_len
        problems = df["seq"].map(lambda s: sequence_problems(s, lo, hi))
        for seq, reason in zip(df.loc[problems.notna(), "seq"], problems.dropna()):
            audit.append(
                {
                    "seq": seq,
                    "reason": "invalid_sequence",
                    "detail": reason,
                    "source": spec.id,
                    "layer": spec.layer,
                }
            )
        df = df[problems.isna()].copy()
        frames.append(df)
        if logger:
            logger.info(
                "  source %-22s layer=%-20s kept=%5d (from %d rows)",
                spec.id,
                spec.layer,
                len(df),
                len(records),
            )
    if not frames:
        raise RuntimeError("no usable records in any source; check the manifest paths and columns")
    return pd.concat(frames, ignore_index=True), audit


# --------------------------------------------------------------------------- #
# cleaning / dedup
# --------------------------------------------------------------------------- #


def seq_id(seq: str) -> str:
    return "s_" + hashlib.sha1(seq.encode()).hexdigest()[:12]


def deduplicate(df: pd.DataFrame, drop_conflicts: bool, audit: list[dict], logger=None) -> pd.DataFrame:
    """Collapse identical sequences across databases and resolve label conflicts."""

    df = df.copy()
    df["seq_id"] = df["seq"].map(seq_id)
    df["_label_set"] = df["label"].astype(int)
    grouped = df.groupby("seq", sort=False)
    rows = []
    for seq, grp in grouped:
        labels = set(grp["label"].astype(int))
        # external / scrambled records do not vote on the training label
        trainable = grp[grp["layer"].isin(TRAINABLE_LAYERS)]
        train_labels = set(trainable["label"].astype(int)) if len(trainable) else set()
        if len(labels) > 1 and len(train_labels) > 1:
            audit.append(
                {
                    "seq": seq,
                    "reason": "label_conflict",
                    "detail": "same sequence is positive in one source and negative in another",
                    "source": ",".join(sorted(set(grp["source"]))),
                    "layer": ",".join(sorted(set(grp["layer"]))),
                }
            )
            if drop_conflicts:
                continue
        primary = min(grp["layer"], key=lambda lay: LAYER_PRECEDENCE.get(lay, 99))
        label = 1 if (grp["layer"].isin(POSITIVE_LAYERS)).any() else int(grp["label"].iloc[0])
        if primary in POSITIVE_LAYERS:
            label = 1
        elif primary in ("negative_background", "hard_negative"):
            label = 0
        row = {
            "seq_id": seq_id(seq),
            "seq": seq,
            "length": len(seq),
            "label": label,
            "layer": primary,
            "sources": ",".join(sorted(set(grp["source"]))),
            "n_source_records": int(len(grp)),
            "has_bacterial_origin": int((grp["layer"] == "bacterial_amp").any()),
        }
        for meta in META_COLUMNS:
            values = [str(v) for v in grp.get(meta, []) if str(v).strip()]
            row[meta] = " | ".join(dict.fromkeys(values))[:400]
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("deduplication removed every sequence; check labels and the conflict policy")
    # duplicated seq_id (hash prefix collision) cannot happen at this scale, but be explicit
    if out["seq_id"].duplicated().any():
        raise RuntimeError("seq_id collision detected - widen the hash prefix in dataset.seq_id()")
    if logger:
        logger.info("  dedup: %d records -> %d unique sequences", len(df), len(out))
    return out


def add_scrambled(df: pd.DataFrame, max_scrambled: int, seed: int, logger=None) -> pd.DataFrame:
    positives = df[(df["layer"].isin(POSITIVE_LAYERS)) & (df["label"] == 1)]
    if positives.empty or max_scrambled <= 0:
        return df
    rng = __import__("random").Random(seed)
    sample = positives.sample(n=min(max_scrambled, len(positives)), random_state=seed)
    rows = []
    seen = set(df["seq"])
    for _, rec in sample.iterrows():
        shuffled = scramble(rec["seq"], rng)
        if shuffled in seen:
            continue
        seen.add(shuffled)
        rows.append(
            {
                "seq_id": "sc_" + seq_id(shuffled)[2:],
                "seq": shuffled,
                "length": len(shuffled),
                "label": 0,
                "layer": "scrambled",
                "sources": f"scrambled:{rec['seq_id']}",
                "n_source_records": 1,
                "has_bacterial_origin": 0,
                **{m: "" for m in META_COLUMNS},
            }
        )
    if not rows:
        return df
    out = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    if logger:
        logger.info("  scrambled challenge set: +%d sequences", len(rows))
    return out


# --------------------------------------------------------------------------- #
# clustering
# --------------------------------------------------------------------------- #


def _run_cd_hit(seqs: list[str], workdir: Path, identity: float, coverage: float) -> dict[str, int] | None:
    import shutil
    import subprocess

    exe = shutil.which("cd-hit")
    if exe is None:
        return None
    word = 5 if identity >= 0.7 else 4 if identity >= 0.6 else 3 if identity >= 0.5 else 2
    workdir.mkdir(parents=True, exist_ok=True)
    fasta = workdir / "cdhit_in.fasta"
    out = workdir / "cdhit_out"
    write_fasta(((f"id{i}", s) for i, s in enumerate(seqs)), fasta)
    cmd = [
        exe, "-i", str(fasta), "-o", str(out), "-c", f"{identity:.2f}",
        "-aL", f"{coverage:.2f}", "-n", str(word), "-d", "0", "-T", "0", "-M", "0",
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    cluster_of: dict[int, int] = {}
    cluster_id = -1
    with open(str(out) + ".clstr", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">Cluster"):
                cluster_id += 1
            elif ">id" in line:
                token = line.split(">id")[1].split("...")[0].split()[0]
                cluster_of[int(token)] = cluster_id
    return {seqs[i]: c for i, c in cluster_of.items()}


def _run_mmseqs(seqs: list[str], workdir: Path, identity: float, coverage: float) -> dict[str, int] | None:
    import shutil
    import subprocess

    exe = shutil.which("mmseqs")
    if exe is None:
        return None
    workdir.mkdir(parents=True, exist_ok=True)
    fasta = workdir / "mmseqs_in.fasta"
    write_fasta(((f"id{i}", s) for i, s in enumerate(seqs)), fasta)
    prefix = workdir / "mmseqs"
    subprocess.run(
        [
            exe, "easy-cluster", str(fasta), str(prefix), str(workdir / "tmp"),
            "--min-seq-id", f"{identity:.2f}", "-c", f"{coverage:.2f}",
            "--cov-mode", "0", "-v", "0",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    mapping: dict[str, int] = {}
    for cluster_idx, cluster_file in enumerate(sorted(workdir.glob("mmseqs_cluster_*.fasta"))):
        for header, seq in read_fasta(cluster_file):
            mapping[seq] = cluster_idx
    return mapping or None


def _kmer_cluster(seqs: list[str], identity: float, k: int | None = None) -> dict[str, int]:
    """Greedy k-mer containment clustering - approximation of CD-HIT.

    Used when neither CD-HIT nor MMseqs2 is installed (e.g. a stock Kaggle image
    without internet). The report records which method was used and the plan's
    caveat that 40 % identity is only an *operational* low-homology test.
    """

    from .seq import kmer_containment

    # k=3 keeps chance k-mer overlap negligible for short peptides (the 3-mer space
    # is 8000 words wide, a 20-mer carries 18 of them), k=4 is used for near-identity
    # clustering. A 40 %-identical pair keeps roughly identity**k of its k-mers.
    k = k or (3 if identity < 0.6 else 4)
    threshold = max(0.10, identity**k)
    order = sorted(range(len(seqs)), key=lambda i: (-len(seqs[i]), i))
    reps: list[str] = []
    mapping: dict[str, int] = {}
    for idx in order:
        seq = seqs[idx]
        for cluster_idx, rep in enumerate(reps):
            # CD-HIT's -s/-aL spirit: never merge peptides with a large length gap
            if abs(len(rep) - len(seq)) > max(3, int(0.2 * max(len(rep), len(seq)))):
                continue
            if kmer_containment(seq, rep, k) >= threshold:
                mapping[seq] = cluster_idx
                break
        else:
            reps.append(seq)
            mapping[seq] = len(reps) - 1
    return mapping


def cluster_sequences(
    seqs: list[str],
    method: str,
    identity: float,
    coverage: float,
    cache_dir: Path,
    logger=None,
) -> tuple[dict[str, int], str]:
    """Return ``({sequence: cluster_id}, method_actually_used)``."""

    if method in ("cdhit", "auto"):
        mapping = _run_cd_hit(seqs, cache_dir, identity, coverage)
        if mapping is not None:
            return mapping, "cdhit"
        if method == "cdhit":
            raise RuntimeError("cd-hit requested but not on PATH (Kaggle images need a dataset or the kmer fallback)")
    if method in ("mmseqs", "auto"):
        mapping = _run_mmseqs(seqs, cache_dir, identity, coverage)
        if mapping is not None:
            return mapping, "mmseqs"
        if method == "mmseqs":
            raise RuntimeError("mmseqs requested but not on PATH")
    if method in ("kmer", "auto"):
        if logger:
            logger.warning(
                "  CD-HIT / MMseqs2 not found - using the built-in k-mer clustering fallback. "
                "Record this in the methods section (plan §5 requires naming the tool and params)."
            )
        return _kmer_cluster(seqs, identity), f"kmer_fallback(k={3 if identity < 0.6 else 4})"
    raise ValueError(f"unknown cluster method {method!r}")


def load_precomputed_clusters(path: str | Path, seqs: Iterable[str]) -> dict[str, int]:
    df = pd.read_csv(path, sep=None, engine="python")
    if not {"seq", "cluster"} <= set(df.columns):
        raise ValueError("precomputed cluster table needs columns: seq, cluster")
    mapping = dict(zip(df["seq"], df["cluster"].astype(int)))
    missing = [s for s in seqs if s not in mapping]
    if missing:
        raise ValueError(f"precomputed cluster table misses {len(missing)} sequences")
    return mapping


# --------------------------------------------------------------------------- #
# splitting
# --------------------------------------------------------------------------- #


def assign_splits(
    df: pd.DataFrame,
    test_frac: float,
    val_frac: float,
    seed: int,
    logger=None,
) -> pd.DataFrame:
    """Cluster-level, label-stratified 3-way split (dev = train + val)."""

    df = df.copy()
    df["split"] = pd.NA
    trainable = df[df["layer"].isin(TRAINABLE_LAYERS)].copy()
    if trainable.empty:
        return df

    cluster_sizes = trainable.groupby(["cluster", "label"]).size().reset_index(name="n")
    # a cluster that contains both labels is a homology/label conflict: keep it out
    clash = cluster_sizes.groupby("cluster")["label"].nunique()
    clash_clusters = set(clash[clash > 1].index)
    if clash_clusters:
        if logger:
            logger.warning(
                "  %d homology clusters contain both labels - assigned to 'review' (never trained on)",
                len(clash_clusters),
            )
        df.loc[df["cluster"].isin(clash_clusters), "split"] = "review"
        trainable = trainable[~trainable["cluster"].isin(clash_clusters)]
        cluster_sizes = cluster_sizes[~cluster_sizes["cluster"].isin(clash_clusters)]

    targets = {"train": 1.0 - test_frac - val_frac, "val": val_frac, "test": test_frac}
    for label in sorted(cluster_sizes["label"].unique()):
        subset = cluster_sizes[cluster_sizes["label"] == label].sample(frac=1.0, random_state=seed)
        total = int(subset["n"].sum())
        current = {k: 0 for k in targets}
        for _, row in subset.sort_values("n", ascending=False).iterrows():
            deficits = {k: targets[k] * total - current[k] for k in targets}
            # prefer the split with the largest remaining deficit
            choice = max(deficits, key=lambda k: (deficits[k], k == "train"))
            df.loc[df["cluster"] == row["cluster"], "split"] = choice
            current[choice] += int(row["n"])
    df.loc[df["layer"] == "scrambled", "split"] = "scrambled"
    df.loc[df["layer"] == "external", "split"] = "external"

    # External peptides that share a homology cluster with a development/test
    # peptide are not an independent validation of generalisation. They are kept
    # (never discarded silently) under the split ``external_homolog`` and reported
    # separately instead of inflating the D11 numbers.
    dev_clusters = set(df.loc[df["split"].isin(["train", "val", "test", "review"]), "cluster"])
    is_external = df["layer"] == "external"
    homolog = is_external & df["cluster"].isin(dev_clusters)
    df.loc[homolog, "split"] = "external_homolog"
    if logger and int(homolog.sum()):
        logger.warning(
            "  %d/%d external peptides share a homology cluster with dev/test -> split 'external_homolog'",
            int(homolog.sum()), int(is_external.sum()),
        )

    if logger:
        counts = df["split"].value_counts(dropna=False).to_dict()
        logger.info("  split sizes: %s", counts)
    return df


# --------------------------------------------------------------------------- #
# top level
# --------------------------------------------------------------------------- #


def build_dataset(
    cfg: DatasetConfig,
    paths: Paths,
    manifest: str | Path | None = None,
    demo_source: pd.DataFrame | None = None,
    logger=None,
) -> dict:
    logger = logger or get_logger(paths.logs / "build_dataset.log")
    paths.split_dir.mkdir(parents=True, exist_ok=True)

    if demo_source is not None:
        raw = demo_source
        audit: list[dict] = []
        logger.info("DEMO MODE - synthetic sequences, results are plumbing checks only")
    else:
        if manifest is None:
            raise ValueError("build_dataset needs either a manifest or demo_source")
        logger.info("reading sources from %s", manifest)
        raw, audit = read_sources(manifest, cfg.min_len, cfg.max_len, logger=logger)

    raw = raw[raw["seq"].map(lambda s: is_valid_sequence(s, cfg.min_len, cfg.max_len))].copy()
    logger.info("after length/alphabet filtering: %d records", len(raw))

    df = deduplicate(raw, cfg.drop_conflicts, audit, logger=logger)
    df = add_scrambled(df, cfg.max_scrambled, cfg.seed, logger=logger)

    seqs = df["seq"].tolist()
    if cfg.cluster_method == "precomputed":
        if not cfg.cluster_table:
            raise ValueError("cluster_method='precomputed' needs cluster_table")
        mapping = load_precomputed_clusters(cfg.cluster_table, seqs)
        used = "precomputed"
    else:
        mapping, used = cluster_sequences(
            seqs, cfg.cluster_method, cfg.cluster_identity, cfg.cluster_coverage, paths.cache, logger
        )
    df["cluster"] = df["seq"].map(mapping).astype(int)
    logger.info(
        "clustering: %s at identity %.2f / coverage %.2f -> %d clusters",
        used,
        cfg.cluster_identity,
        cfg.cluster_coverage,
        df["cluster"].nunique(),
    )

    df = assign_splits(df, cfg.test_frac, cfg.val_frac, cfg.seed, logger=logger)

    # deterministic column order
    columns = [
        "seq_id", "seq", "length", "label", "layer", "split", "cluster",
        "sources", "n_source_records", "has_bacterial_origin", *META_COLUMNS,
    ]
    df = df[columns].sort_values(["split", "layer", "length"], na_position="last").reset_index(drop=True)

    df.to_csv(paths.dataset_all, index=False)
    write_fasta(((f"{r.seq_id}|{r.layer}|label={r.label}", r.seq) for r in df.itertuples()), paths.dataset_fasta)
    df[["seq", "cluster"]].drop_duplicates().rename(columns={"cluster": "cluster"}).to_csv(
        paths.cluster_table, sep="\t", index=False
    )

    for split in ("train", "val", "dev", "test", "external", "external_homolog", "scrambled", "review"):
        if split == "dev":
            part = df[df["split"].isin(["train", "val"])]
        else:
            part = df[df["split"] == split]
        part.to_csv(paths.split_csv(split), index=False)

    audit_df = pd.DataFrame(audit)
    if audit_df.empty:
        audit_df = pd.DataFrame(columns=["seq", "reason", "detail", "source", "layer"])
    audit_df.to_csv(paths.label_audit, index=False)

    # D1: template only - the AD cohort metadata is a manual curation task (§4.2)
    if not paths.metadata_table.exists():
        pd.DataFrame(
            columns=[
                "bioproject", "subject_id", "biosample", "experiment", "run",
                "diagnosis", "sample_type", "age", "sex", "bmi", "batch", "include", "exclusion_reason",
            ]
        ).to_csv(paths.metadata_table, index=False)

    summary = {
        "cluster_method": used,
        "cluster_identity": cfg.cluster_identity,
        "cluster_coverage": cfg.cluster_coverage,
        "n_clusters": int(df["cluster"].nunique()),
        "n_sequences": int(len(df)),
        "layer_counts": {k: int(v) for k, v in df["layer"].value_counts().items()},
        "split_counts": {
            **{str(k): int(v) for k, v in df["split"].value_counts(dropna=False).items()},
            "dev": int(df["split"].isin(["train", "val"]).sum()),
        },
        "split_positives": {
            s: int(((df["split"] == s) & (df["label"] == 1)).sum())
            for s in ("train", "val", "test", "dev", "external", "external_homolog", "scrambled", "review")
        },
        "split_negatives": {
            s: int(((df["split"] == s) & (df["label"] == 0)).sum())
            for s in ("train", "val", "test", "dev", "external", "external_homolog", "scrambled", "review")
        },
        "external_homolog_overlap": int((df["split"] == "external_homolog").sum()),
        "dropped_records": int(len(audit_df)),
        "drop_reasons": {k: int(v) for k, v in audit_df.get("reason", pd.Series(dtype=str)).value_counts().items()},
        "inputs": (
            {"manifest": str(manifest), "sha256": sha256_file(manifest)}
            if manifest and Path(manifest).exists()
            else {"demo": True}
        ),
        "min_len": cfg.min_len,
        "max_len": cfg.max_len,
        "demo_mode": demo_source is not None,
    }
    write_json(paths.dataset / "dataset_summary.json", summary)
    logger.info(
        "dataset written: %d sequences, %d clusters, test=%d (pos=%d) - see %s",
        summary["n_sequences"],
        summary["n_clusters"],
        summary["split_counts"].get("test", 0),
        summary["split_positives"]["test"],
        paths.dataset_all,
    )
    return summary
