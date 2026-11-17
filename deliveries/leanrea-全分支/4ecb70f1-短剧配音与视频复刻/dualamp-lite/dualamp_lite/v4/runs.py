"""Run identity, environment snapshots and hashing (V4 sections 5 and 7).

Nothing is ever overwritten: every invocation gets ``run_id = YYYYMMDD_HHMMSS``
(``_01``, ``_02`` ... if two runs start inside the same second) and all outputs
are written below ``runs/<run_id>``, ``results/<run_id>`` and
``final_models/<run_id>``. ``latest_run.txt`` only *points* at the newest run.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from ..utils import sha256_file
from .config import Paths


# --------------------------------------------------------------------------- #
# run identity
# --------------------------------------------------------------------------- #


def new_run_id(now: _dt.datetime | None = None) -> str:
    now = now or _dt.datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")


def unique_run_id(paths: Paths, base: str | None = None) -> str:
    base = base or new_run_id()
    candidate = base
    suffix = 0
    while (paths.runs / candidate).exists() or (paths.results / candidate).exists():
        suffix += 1
        candidate = f"{base}_{suffix:02d}"
    return candidate


def run_dir(paths: Paths, run_id: str, model: str, seed: int, fold: int) -> Path:
    path = paths.runs / run_id / model / f"seed_{seed}" / f"fold_{fold}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_latest(paths: Paths, run_id: str) -> None:
    (paths.root / "latest_run.txt").write_text(run_id + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# environment
# --------------------------------------------------------------------------- #


def _version(module: str) -> str:
    try:
        mod = __import__(module)
        return str(getattr(mod, "__version__", "unknown"))
    except Exception:  # pragma: no cover - optional packages
        return "not installed"


def _tool_version(executable: str, flag: str = "--version") -> str:
    if shutil.which(executable) is None:
        return "not installed"
    try:
        out = subprocess.run([executable, flag], capture_output=True, text=True, timeout=10)
        return (out.stdout or out.stderr).strip().splitlines()[0][:120]
    except Exception:
        return "unknown"


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception:
        return ""


def environment_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        "os": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "numpy": _version("numpy"),
        "pandas": _version("pandas"),
        "scipy": _version("scipy"),
        "sklearn": _version("sklearn"),
        "biopython": _version("Bio"),
        "yaml": _version("yaml"),
        "torch": _version("torch"),
        "fair_esm": _version("esm"),
        "transformers": _version("transformers"),
        "xgboost": _version("xgboost"),
        "cuda_available": False,
        "cuda_version": None,
        "cudnn_version": None,
        "gpu": None,
        "cd_hit": _tool_version("cd-hit", "-h"),
        "mmseqs": _tool_version("mmseqs", "version"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
    }
    try:
        import torch

        info["cuda_available"] = bool(torch.cuda.is_available())
        info["cuda_version"] = torch.version.cuda
        info["cudnn_version"] = torch.backends.cudnn.version() if torch.cuda.is_available() else None
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
        info["torch_deterministic_algorithms"] = True
    except Exception:
        pass
    return info


def environment_yaml(info: dict[str, Any]) -> str:
    py = ".".join(info["python"].split(".")[:2])
    lines = [
        "name: dualamp-lite",
        "channels:",
        "  - conda-forge",
        "  - pytorch",
        "dependencies:",
        f"  - python={py}",
        f"  - numpy={info.get('numpy', '')}",
        f"  - pandas={info.get('pandas', '')}",
        f"  - scikit-learn={info.get('sklearn', '')}",
        f"  - scipy={info.get('scipy', '')}",
        f"  - biopython={info.get('biopython', '')}",
        "  - pyyaml",
        "  - pip",
        "  - pip:",
        f"      - torch=={info.get('torch', '')}",
        f"      - fair-esm=={info.get('fair_esm', '')}" if info.get("fair_esm") not in (None, "not installed") else "      - fair-esm",
        "      # cd-hit / mmseqs2: install with conda (bioconda) - versions recorded in environment_info.txt",
    ]
    return "\n".join(lines) + "\n"


def requirements_lock() -> str:
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, timeout=60
        )
        text = out.stdout.strip()
        if text:
            return text + "\n"
    except Exception:
        pass
    packages = []
    for module in ("numpy", "pandas", "scipy", "sklearn", "Bio", "yaml", "torch", "esm", "transformers"):
        packages.append(f"# {module}=={_version(module)}")
    return "\n".join(packages) + "\n"


def snapshot_environment(paths: Paths, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    info = environment_info()
    if extra:
        info.update(extra)
    paths.environment.mkdir(parents=True, exist_ok=True)
    (paths.environment / "environment.yml").write_text(environment_yaml(info), encoding="utf-8")
    (paths.environment / "requirements.lock").write_text(requirements_lock(), encoding="utf-8")
    text = "\n".join(f"{k}: {v}" for k, v in info.items()) + "\n"
    (paths.environment / "environment_info.txt").write_text(text, encoding="utf-8")
    (paths.environment / "environment_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def short_environment() -> str:
    info = environment_info()
    return (
        f"os={info['os']}\npython={info['python']}\ntorch={info['torch']}\n"
        f"cuda={info['cuda_version']} cudnn={info['cudnn_version']} gpu={info['gpu']}\n"
        f"numpy={info['numpy']} pandas={info['pandas']} sklearn={info['sklearn']} "
        f"biopython={info['biopython']} fair_esm={info['fair_esm']}\n"
        f"cd_hit={info['cd_hit']}\nmmseqs={info['mmseqs']}\n"
    )


# --------------------------------------------------------------------------- #
# determinism helpers
# --------------------------------------------------------------------------- #


def save_rng_state(path: Path) -> None:
    import random

    import torch

    state = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    torch.save(state, path)


# --------------------------------------------------------------------------- #
# hashing
# --------------------------------------------------------------------------- #


def hash_manifest(paths: Paths, run_id: str, extra_files: list[Path] | None = None) -> Path:
    """SHA256 of every input, feature file, config, checkpoint and source file."""

    targets: list[Path] = []
    for folder in (paths.raw, paths.data, paths.features, paths.environment):
        if folder.exists():
            targets.extend(sorted(p for p in folder.rglob("*") if p.is_file()))
    for folder in (paths.runs / run_id, paths.results / run_id, paths.final_models / run_id):
        if folder.exists():
            targets.extend(sorted(p for p in folder.rglob("*") if p.is_file()))
    package = Path(__file__).resolve().parent
    targets.extend(sorted(p for p in package.glob("*.py")))
    targets.extend(sorted(p for p in (package.parent.parent / "configs").glob("*.yaml")))
    if extra_files:
        targets.extend(extra_files)
    rows = ["sha256\tsize_bytes\tpath"]
    seen = set()
    for path in targets:
        path = Path(path)
        if not path.is_file() or path in seen:
            continue
        seen.add(path)
        digest = sha256_file(path)
        rows.append(f"{digest}\t{path.stat().st_size}\t{path}")
    out = paths.sha / f"manifest_{run_id}.tsv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return out


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def env_flag() -> dict[str, str]:
    return {
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", ""),
        "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG", ""),
    }
