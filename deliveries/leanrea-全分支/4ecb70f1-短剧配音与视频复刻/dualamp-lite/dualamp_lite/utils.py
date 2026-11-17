"""Small shared helpers: logging, seeding, hashing, manifests, atomic writes."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np

LOGGER_NAME = "dualamp"


def get_logger(log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """Idempotent logger with a console handler and an optional file handler."""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if not logger.handlers:
        fmt = logging.Formatter("[%(asctime)s] %(levelname)-7s %(message)s", "%H:%M:%S")
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(fmt)
        logger.addHandler(console)
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        already = any(
            isinstance(h, logging.FileHandler) and Path(h.baseFilename) == log_file.resolve()
            for h in logger.handlers
        )
        if not already:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"
                )
            )
            logger.addHandler(fh)
    return logger


def set_seed(seed: int, deterministic: bool = True) -> None:
    """Seed python/numpy/torch. Torch is optional at import time."""

    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:  # pragma: no cover - torch is optional for the baseline-only paths
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except Exception:  # pragma: no cover
        pass


def device_of(preference: str = "auto"):
    import torch

    if preference == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(preference)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def write_file_manifest(root: Path, out_tsv: Path, skip_dirs: Iterable[str] = ("cache",)) -> int:
    """D15: SHA256 of every produced file (recursive, stable ordering)."""

    root = Path(root)
    skip = {root / d for d in skip_dirs}
    rows = ["sha256\tbytes\tpath"]
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(str(path).startswith(str(s)) for s in skip):
            continue
        if path.name.endswith(".tmp"):
            continue
        rows.append(f"{sha256_file(path)}\t{path.stat().st_size}\t{path.relative_to(root).as_posix()}")
    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    out_tsv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows) - 1


class Timer:
    def __init__(self, logger: logging.Logger | None = None, label: str = "") -> None:
        self.logger = logger
        self.label = label

    def __enter__(self) -> "Timer":
        self.t0 = time.time()
        return self

    def __exit__(self, *exc: object) -> None:
        elapsed = time.time() - self.t0
        if self.logger is not None:
            self.logger.info("%s finished in %.1fs", self.label or "step", elapsed)
        else:
            print(f"{self.label or 'step'} finished in {elapsed:.1f}s")


def describe_environment() -> dict:
    """Recorded in every report so a run can be reproduced."""

    import platform

    env: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {},
    }
    for name in ("numpy", "pandas", "sklearn", "scipy", "torch", "Bio", "fair_esm", "transformers"):
        try:
            mod = __import__(name)
            env["packages"][name] = getattr(mod, "__version__", "unknown")
        except Exception:
            env["packages"][name] = None
    try:
        import torch

        env["cuda"] = torch.cuda.is_available()
        env["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        env["cuda"] = None
        env["gpu"] = None
    return env
