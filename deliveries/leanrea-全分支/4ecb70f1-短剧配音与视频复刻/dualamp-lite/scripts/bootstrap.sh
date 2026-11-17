#!/usr/bin/env bash
# Install the pipeline dependencies without destroying a preinstalled CUDA torch.
#
#   bash scripts/bootstrap.sh            # core deps + fair-esm
#   bash scripts/bootstrap.sh --mock     # CPU-only smoke test (no ESM-2)
set -euo pipefail

MODE="${1:-full}"
PY="${PYTHON:-python3}"

echo "[1/3] core packages"
"$PY" -m pip install -q numpy pandas scipy scikit-learn biopython pyyaml joblib matplotlib

if [[ "$MODE" == "--mock" ]]; then
  echo "[2/3] torch (CPU wheel)"
  "$PY" -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu || \
    echo "torch install skipped (features/train with --backend mock still need torch for M1-M3)"
  echo "[3/3] done - use: python -m dualamp_lite demo --backend mock"
  exit 0
fi

echo "[2/3] torch (kept as installed if present)"
"$PY" - <<'PY'
try:
    import torch  # noqa: F401
    print("torch already available:", torch.__version__)
except Exception:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "torch"], check=False)
PY

echo "[3/3] fair-esm (--no-deps so pip does not replace torch)"
"$PY" -m pip install -q fair-esm --no-deps

"$PY" - <<'PY'
import importlib
for name in ("numpy", "pandas", "sklearn", "scipy", "Bio", "yaml", "torch", "esm"):
    try:
        module = importlib.import_module(name)
        print(f"  {name:<10} {getattr(module, '__version__', 'ok')}")
    except Exception as exc:
        print(f"  {name:<10} MISSING ({exc})")
PY
