"""Stage orchestration for ``run_pipeline.py`` (V4 section 14).

Stages (in order)::

    env  audit  dataset  split  features  baseline  cross_validation
    final_train  evaluation  reproducibility  export  all

Each invocation gets its own ``run_id``; ``all`` runs the complete chain once and
keeps every artefact. A failing stage leaves the logs and partial results in
place and exits non-zero - it never writes a "complete" marker.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..dataset import load_manifest
from ..synth import write_demo_sources
from ..utils import get_logger, sha256_file
from . import schema
from .config import DemoConfig, Paths
from .data import build_master
from .evaluate import run_evaluation
from .features import run_features
from .report import build_report, create_figures
from .runs import (
    hash_manifest,
    new_run_id,
    snapshot_environment,
    unique_run_id,
    write_latest,
)
from .split import run_split
from .train import FeatureStore, run_cross_validation, run_final, train_fold


@dataclass
class Context:
    cfg: object
    paths: Paths
    run_id: str
    logger: object
    manifest: Path | None = None
    max_epochs: int | None = None

    @property
    def demo(self) -> bool:
        return bool(self.cfg.demo_mode)


def build_context(cfg, paths: Paths, run_id: str | None = None, manifest: str | Path | None = None, max_epochs: int | None = None) -> Context:
    paths.logs.mkdir(parents=True, exist_ok=True)
    run_id = run_id or unique_run_id(paths, new_run_id())
    logger = get_logger(paths.logs / f"pipeline_{run_id}.log")
    logger.info("run_id=%s workdir=%s demo=%s", run_id, paths.root, cfg.demo_mode)
    return Context(cfg=cfg, paths=paths, run_id=run_id, logger=logger, manifest=Path(manifest) if manifest else None, max_epochs=max_epochs)


# --------------------------------------------------------------------------- #
# stage: environment
# --------------------------------------------------------------------------- #


def stage_env(ctx: Context) -> dict:
    info = snapshot_environment(ctx.paths, extra={"run_id": ctx.run_id, "demo_mode": ctx.demo, "backend": ctx.cfg.features.backend})
    ctx.cfg.write_yaml(ctx.paths.root / "configs" / f"resolved_{ctx.run_id}.yaml")
    ctx.logger.info("  environment snapshot written (torch=%s, cuda=%s)", info.get("torch"), info.get("cuda_version"))
    return info


# --------------------------------------------------------------------------- #
# stage: audit
# --------------------------------------------------------------------------- #


def ensure_manifest(ctx: Context) -> Path:
    if ctx.manifest is not None and Path(ctx.manifest).exists():
        return Path(ctx.manifest)
    if not ctx.demo:
        candidate = ctx.paths.root / "configs" / "sources.yaml"
        if candidate.exists():
            return candidate
        raise FileNotFoundError("no source manifest: pass --manifest or run with --demo")
    demo_dir = ctx.paths.raw / "demo"
    manifest = write_demo_sources(demo_dir, DemoConfig())
    ctx.logger.warning("  --demo: synthetic peptides in %s (never quotable)", demo_dir)
    return manifest


def stage_audit(ctx: Context) -> dict:
    manifest = ensure_manifest(ctx)
    specs, base = load_manifest(manifest)
    rows = []
    for spec in specs:
        path = Path(spec.path)
        path = path if path.is_absolute() else (base / path)
        rows.append(
            {
                "source_id": spec.id,
                "layer": spec.layer,
                "format": spec.format,
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "sha256": sha256_file(path) if path.exists() else "",
            }
        )
    registry = pd.DataFrame(rows)
    missing = registry[~registry["exists"]]
    if len(missing):
        raise FileNotFoundError(f"missing source files: {missing['path'].tolist()}")
    payload = {
        "run_id": ctx.run_id,
        "manifest": str(manifest),
        "manifest_sha256": sha256_file(manifest),
        "sources": rows,
        "label_policy": {
            "positive": "experimentally demonstrated mature antibacterial peptide (antiviral/antifungal NOT auto-positive)",
            "negative": "curated inactive / non-AMP background (weak UniProt fragments, DBAASP inactive)",
            "challenge_only": ["hard_negative", "scrambled", "external"],
        },
    }
    ctx.paths.manifests.mkdir(parents=True, exist_ok=True)
    (ctx.paths.manifests / "sources_manifest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    registry.to_csv(ctx.paths.manifests / "source_registry.csv", index=False)
    ctx.logger.info("  audit: %d sources, %d bytes total", len(registry), int(registry["size_bytes"].sum()))
    return payload


# --------------------------------------------------------------------------- #
# stage: dataset / split / features
# --------------------------------------------------------------------------- #


def stage_dataset(ctx: Context) -> dict:
    manifest = ensure_manifest(ctx)
    master = build_master(manifest, ctx.cfg.dataset, ctx.paths, logger=ctx.logger)
    return {"n_records": int(len(master)), "n_positive": int((master["label"] == 1).sum())}


def stage_split(ctx: Context) -> dict:
    meta = run_split(ctx.cfg, ctx.paths, logger=ctx.logger)
    ctx.logger.info("  split manifest written (n_clusters=%s)", meta.get("n_clusters"))
    return meta


def stage_features(ctx: Context) -> dict:
    info = run_features(ctx.cfg, ctx.paths, logger=ctx.logger)
    if info.get("is_mock"):
        ctx.logger.warning("  features are MOCK embeddings - results are not scientific")
    return info


# --------------------------------------------------------------------------- #
# stage: training
# --------------------------------------------------------------------------- #


def _store(ctx: Context) -> FeatureStore:
    return FeatureStore(ctx.paths)


def stage_baseline(ctx: Context) -> pd.DataFrame:
    return run_cross_validation(
        ctx.cfg, ctx.paths, ctx.run_id, _store(ctx), logger=ctx.logger,
        max_epochs=ctx.max_epochs, models=list(ctx.cfg.train.baselines),
    )


def stage_cross_validation(ctx: Context) -> pd.DataFrame:
    return run_cross_validation(
        ctx.cfg, ctx.paths, ctx.run_id, _store(ctx), logger=ctx.logger,
        max_epochs=ctx.max_epochs, models=list(ctx.cfg.train.models),
    )


def stage_final_train(ctx: Context) -> pd.DataFrame:
    return run_final(ctx.cfg, ctx.paths, ctx.run_id, _store(ctx), logger=ctx.logger)


# --------------------------------------------------------------------------- #
# stage: evaluation
# --------------------------------------------------------------------------- #


def stage_evaluation(ctx: Context) -> dict:
    payload = run_evaluation(ctx.cfg, ctx.paths, ctx.run_id, logger=ctx.logger)
    create_figures(ctx.paths, ctx.run_id)
    build_report(ctx.cfg, ctx.paths, ctx.run_id, logger=ctx.logger)
    return payload


# --------------------------------------------------------------------------- #
# stage: reproducibility
# --------------------------------------------------------------------------- #


def stage_reproducibility(ctx: Context) -> dict:
    """Test A: same seed twice -> identical probabilities. Test B: seed spread."""

    cfg = ctx.cfg
    store = _store(ctx)
    dev = store.pool(ctx.paths, "development")
    rng = np.random.default_rng(cfg.dataset.split_seed)
    index = rng.choice(len(dev), size=min(128, len(dev)), replace=False)
    index.sort()
    subset = dev.take(index)
    half = len(subset) // 2
    train_pool, val_pool = subset.take(np.arange(half)), subset.take(np.arange(half, len(subset)))
    epochs = 2
    runs = []
    for repeat in range(2):
        result = train_fold(
            cfg.train, "M1", cfg.train.seeds[0], 0, train_pool, val_pool,
            ctx.paths.cache / f"repro_{ctx.run_id}_{repeat}", ctx.logger,
            embed_dim=cfg.features.embed_dim, max_epochs=epochs, save=False,
        )
        runs.append(result["val_probs"])
    max_diff = float(np.max(np.abs(runs[0] - runs[1])))
    identical = max_diff <= 1e-6

    per_model = {}
    cv_path = ctx.paths.results / ctx.run_id / "cv_oof_metrics.csv"
    seed_mean = float("nan")
    seed_sd = float("nan")
    if cv_path.exists():
        cv = pd.read_csv(cv_path)
        for model, grp in cv.groupby("model"):
            per_model[model] = {"auroc_mean": float(grp["auroc"].mean()), "auroc_sd": float(grp["auroc"].std(ddof=1)) if len(grp) > 1 else 0.0}
        focus = per_model.get("M3") or next(iter(per_model.values()))
        seed_mean, seed_sd = focus["auroc_mean"], focus["auroc_sd"]
    payload = {
        "run_id": ctx.run_id,
        "test_a": {
            "protocol": f"M1, seed={cfg.train.seeds[0]}, {epochs} epochs, {len(subset)} sequences, identical split",
            "max_abs_prob_diff": max_diff,
            "threshold": 1e-6,
        },
        "same_seed_identical": bool(identical),
        "test_b": {
            "protocol": "per-seed OOF AUROC from the cross-validation stage",
            "seed_auroc_mean": seed_mean,
            "seed_auroc_sd": seed_sd,
            "stable": bool(np.isfinite(seed_sd) and seed_sd < 0.05),
            "per_model": per_model,
        },
        "note": (
            "PyTorch does not guarantee bit-identical results across versions, devices or CPU/GPU. "
            "The guarantee is: same environment + same seed + same data -> identical predictions."
        ),
    }
    out = ctx.paths.results / ctx.run_id / "reproducibility_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    ctx.logger.info("  reproducibility: same_seed_identical=%s (max|Δp|=%.2e), seed AUROC SD=%.4f", identical, max_diff, seed_sd)
    return payload


# --------------------------------------------------------------------------- #
# stage: export
# --------------------------------------------------------------------------- #

INFERENCE_TEMPLATE = '''#!/usr/bin/env python3
"""DualAMP-Lite inference (run_id {run_id}).

Usage
-----
    python inference.py --fasta example.fasta --model M3 --out scores.csv

The script rebuilds the frozen 32-dim feature block, applies the StandardScaler
saved with the checkpoint (fitted on all of Development) and runs the five final
seeds of the requested architecture, returning the mean probability.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT_DIR = Path(__file__).resolve().parent
# the repository root is one level above export/; make the package importable
sys.path.insert(0, str(ROOT_DIR.parent))
from dualamp_lite.v4 import schema
from dualamp_lite.v4.features import build_encoder
from dualamp_lite.v4.config import FeatureConfig
from dualamp_lite.v4.models import build_model
from dualamp_lite.seq import read_fasta

ROOT = Path(__file__).resolve().parent
MODEL_ROOT = ROOT / "final_models" / "{run_id}"
DEFAULT_SEEDS = {seeds}


def available_seeds(model_name: str) -> list[int]:
    """Every checkpoint that is actually present (never assume a seed exists)."""

    seeds = sorted(
        int(path.parent.name.split("_")[1])
        for path in (MODEL_ROOT / model_name).glob("seed_*/model.pt")
    )
    if not seeds:
        raise FileNotFoundError(f"no checkpoints under {{MODEL_ROOT / model_name}}")
    return seeds


def score(fasta: str, model_name: str = "{default_model}", backend: str = "{backend}") -> pd.DataFrame:
    records = [(h.split()[0], s.strip().upper()) for h, s in read_fasta(fasta)]
    for _, seq in records:
        if not (10 <= len(seq) <= 50):
            raise ValueError(f"sequence outside 10-50 aa: {{seq[:20]}}...")
        schema.assert_valid(seq)
    seqs = [s for _, s in records]
    phys = schema.compute_matrix(seqs).astype(np.float32)
    encoder = build_encoder(FeatureConfig(backend=backend), device="cpu")
    raw_residue, mean, mask = encoder.encode(seqs)

    probs = []
    for seed in available_seeds(model_name):
        ckpt_path = MODEL_ROOT / model_name / f"seed_{{seed}}" / "model.pt"
        ckpt = torch.load(ckpt_path, map_location="cpu")
        model = build_model(model_name, embed_dim=ckpt["embed_dim"], n_phys=ckpt["n_phys"], dropout=0.0)
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        mean_t = torch.from_numpy(np.asarray(mean, dtype=np.float32))
        res_t = torch.from_numpy(np.asarray(raw_residue, dtype=np.float32))
        mask_t = torch.from_numpy(np.asarray(mask, dtype=bool))
        scaled = (phys - ckpt["scaler_mean"]) / ckpt["scaler_scale"]
        phys_t = torch.from_numpy(scaled.astype(np.float32))
        with torch.no_grad():
            logits = model(mean=mean_t, phys=phys_t, residue=res_t, mask=mask_t)
        probs.append(torch.sigmoid(logits).numpy())
    mean_prob = np.mean(np.vstack(probs), axis=0)
    return pd.DataFrame({{"sequence_id": [i for i, _ in records], "sequence": seqs, "prob": mean_prob}})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fasta", required=True)
    parser.add_argument("--model", default="{default_model}", choices=["M1", "M2", "M3"])
    parser.add_argument("--backend", default="{backend}", choices=["fair-esm", "transformers", "mock"])
    parser.add_argument("--out", default="scores.csv")
    args = parser.parse_args()
    table = score(args.fasta, args.model, args.backend)
    table.to_csv(args.out, index=False)
    print(json.dumps({{"n": len(table), "mean_prob": float(table["prob"].mean())}}, indent=2))


if __name__ == "__main__":
    main()
'''


def stage_export(ctx: Context) -> dict:
    export_dir = ctx.paths.root / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    # final models live under final_models/<run_id>/..., but inference expects
    # to find them next to itself; a relative pointer keeps the export portable.
    (export_dir / "final_models").mkdir(exist_ok=True)
    (export_dir / "final_models" / "README.txt").write_text(
        f"Final checkpoints for run {ctx.run_id} are in ../../final_models/{ctx.run_id}/.\n"
        "Copy or symlink that directory to export/final_models/ before running inference.py.\n",
        encoding="utf-8",
    )
    default_model = "M3" if "M3" in ctx.cfg.train.models else ctx.cfg.train.models[0]
    (export_dir / "inference.py").write_text(
        INFERENCE_TEMPLATE.format(
            run_id=ctx.run_id,
            seeds=list(ctx.cfg.train.seeds),
            default_model=default_model,
            backend=ctx.cfg.features.backend,
        ),
        encoding="utf-8",
    )

    test = pd.read_csv(ctx.paths.split_csv("internal_test"))
    sample = pd.concat([test[test["label"] == 1].head(5), test[test["label"] == 0].head(5)])
    with open(export_dir / "example.fasta", "w", encoding="utf-8") as fh:
        for _, row in sample.iterrows():
            fh.write(f">{row['sequence_id']} label={row['label']} layer={row['layer']}\n{row['seq']}\n")

    summary_path = ctx.paths.results / ctx.run_id / "internal_test_summary.csv"
    summary = pd.read_csv(summary_path) if summary_path.exists() else None
    metrics_md = ""
    if summary is not None:
        pivot = summary.pivot_table(index="model", columns="metric", values="mean").round(3).reset_index()
        header = "| " + " | ".join(str(c) for c in pivot.columns) + " |"
        sep = "|" + "|".join(["---"] * len(pivot.columns)) + "|"
        body = ["| " + " | ".join(str(v) for v in row) + " |" for row in pivot.itertuples(index=False)]
        metrics_md = "\n".join([header, sep, *body])
    card = f"""# DualAMP-Lite 模型卡（run {ctx.run_id}）

## 用途
10–50 aa 标准氨基酸肽段的 AMP / 非 AMP 二分类打分。**不适用于**长前体蛋白、细菌素前体、非标准残基。

## 结构（冻结）
- M1：ESM-2 全局均值 480 → 128，理化 32 → 64，concat 192 → MLP 64 → 1
- M2：残基 (L,480) → 128 → Conv3/5/7 各 64 通道 + masked max → 192 → 128 → MLP → 1
- M3：M2 CNN 分支 128 + 理化 64 → 192 → 64 → 1（无额外全局池化）

## 训练协议
- Development 80% / 内部测试 20%，按 80% 同源簇分组，split_seed 20261109
- 5 种子 {list(ctx.cfg.train.seeds)} × 5 折交叉验证；最终每个模型 5 个全 Development 权重 + 均值概率集成
- 阈值、校准、模型选择全部来自 Development OOF；内部测试只评分一次

## 内部测试（Mean over seeds）
{metrics_md if metrics_md else '_（无）_'}

## 限制
- 编码器后端：{ctx.cfg.features.backend}；若为 `mock`，本卡片中的所有数值均不可引用。
- 仅适用标准 20 种氨基酸、长度 10–50；超出范围直接报错（missing_value_policy = error）。
- 概率已用 Development OOF 做 Platt 校准；校准不改变排序指标。
- 跨设备/跨版本不保证逐位复现（PyTorch 官方声明）。
"""
    (export_dir / "MODEL_CARD.md").write_text(card, encoding="utf-8")
    write_json_path = export_dir / "ensemble_recipe.json"
    write_json_path.write_text(
        json.dumps(
            {
                "run_id": ctx.run_id,
                "models": list(ctx.cfg.train.models),
                "seeds": list(ctx.cfg.train.seeds),
                "ensemble": "mean of sigmoid probabilities over the 5 seeds of the same architecture",
                "threshold_source": "Development OOF, MCC rule",
                "feature_schema": schema.SCHEMA_VERSION,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ctx.logger.info("  export: %s", export_dir)
    return {"export_dir": str(export_dir)}


# --------------------------------------------------------------------------- #
# drivers
# --------------------------------------------------------------------------- #


def _start(ctx: Context) -> None:
    ctx.cfg.write_yaml(ctx.paths.root / "configs" / f"resolved_{ctx.run_id}.yaml")
    if ctx.paths.runs.exists():
        write_latest(ctx.paths, ctx.run_id)


def _finish(ctx: Context, stages: list[str], started: float, complete: bool = False) -> None:
    """``complete: true`` is written only by the full ``--stage all`` chain.

    A single-stage invocation records its own status file; it never claims the
    run is complete (V4: a failed or partial run must not look finished).
    """

    effective = ctx.cfg.features.backend
    meta_path = ctx.paths.features / "feature_meta.json"
    if meta_path.exists():
        try:
            effective = json.loads(meta_path.read_text()).get("backend", effective)
        except Exception:
            pass
    status = {
        "run_id": ctx.run_id,
        "stages": stages,
        "started": started,
        "finished": time.time(),
        "seconds": round(time.time() - started, 1),
        "requested_backend": ctx.cfg.features.backend,
        "effective_backend": effective,
        "demo_mode": ctx.demo,
        "complete": bool(complete),
    }
    name = "run_status.json" if complete else f"stage_{stages[-1]}_status.json"
    status_path = ctx.paths.results / ctx.run_id / name
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")


def run_all(ctx: Context) -> dict:
    started = time.time()
    _start(ctx)
    stages: list[str] = []
    for name, fn in (
        ("env", stage_env),
        ("audit", stage_audit),
        ("dataset", stage_dataset),
        ("split", stage_split),
        ("features", stage_features),
        ("baseline", stage_baseline),
        ("cross_validation", stage_cross_validation),
        ("final_train", stage_final_train),
        ("reproducibility", stage_reproducibility),
        ("export", stage_export),
        ("evaluation", stage_evaluation),
    ):
        ctx.logger.info("=== stage %s ===", name)
        fn(ctx)
        stages.append(name)
    manifest = hash_manifest(ctx.paths, ctx.run_id)
    ctx.logger.info("  SHA256 manifest: %s", manifest)
    _finish(ctx, stages, started, complete=True)
    return {"run_id": ctx.run_id, "stages": stages, "sha256_manifest": str(manifest)}


STAGES = {
    "env": stage_env,
    "audit": stage_audit,
    "dataset": stage_dataset,
    "split": stage_split,
    "features": stage_features,
    "baseline": stage_baseline,
    "cross_validation": stage_cross_validation,
    "final_train": stage_final_train,
    "evaluation": stage_evaluation,
    "reproducibility": stage_reproducibility,
    "export": stage_export,
}


def run_stage(ctx: Context, stage: str) -> dict:
    started = time.time()
    if stage == "all":
        return run_all(ctx)
    if stage == "hash":
        path = hash_manifest(ctx.paths, ctx.run_id)
        return {"sha256_manifest": str(path)}
    if stage not in STAGES:
        raise SystemExit(f"unknown stage {stage!r}; choose from {sorted(list(STAGES) + ['hash', 'all'])}")
    _start(ctx)
    payload = STAGES[stage](ctx)
    if isinstance(payload, dict):
        write_json(ctx.paths.results / ctx.run_id / f"stage_{stage}.json", payload)
    _finish(ctx, [stage], started)
    return payload if isinstance(payload, dict) else {"stage": stage}


def write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path
