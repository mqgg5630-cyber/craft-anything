#!/usr/bin/env bash
# One-shot local / server run of the full DualAMP-Lite chain.
#
#   bash scripts/run_all.sh /path/to/sources.yaml [/path/to/workdir]
#
# Environment knobs:
#   BACKEND=fair-esm|transformers|mock   WEIGHTS_DIR=...   CLUSTER=auto|cdhit|mmseqs|kmer
#   SEEDS=1,2,3,4,5   MODELS=...   FOLDS=5   EPOCHS=60   DEVICE=auto|cuda|cpu
set -euo pipefail

MANIFEST="${1:?usage: run_all.sh <sources.yaml> [workdir]}"
WORK="${2:-./2026-11-09_DualAMP-Lite}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PY="${PYTHON:-python3}"
BACKEND="${BACKEND:-auto}"
WEIGHTS_DIR="${WEIGHTS_DIR:-}"
CLUSTER="${CLUSTER:-auto}"
SEEDS="${SEEDS:-1,2,3,4,5}"
MODELS="${MODELS:-M0_RF,M0_HGB,M0_CNN_BiGRU,M1,M2,M3,M3_NOPHYS}"
FOLDS="${FOLDS:-5}"
EPOCHS="${EPOCHS:-60}"
DEVICE="${DEVICE:-auto}"

echo "=== 0. environment ==="
"$PY" -m dualamp_lite --workdir "$WORK" check

echo "=== 1. dataset (D2/D3) ==="
"$PY" -m dualamp_lite build --workdir "$WORK" --manifest "$MANIFEST" --cluster-method "$CLUSTER"

echo "=== 2. features (D4) ==="
ARGS=(features --workdir "$WORK" --backend "$BACKEND" --device "$DEVICE" --batch-size 64)
[[ -n "$WEIGHTS_DIR" ]] && ARGS+=(--weights-dir "$WEIGHTS_DIR" --local-files-only)
"$PY" -m dualamp_lite "${ARGS[@]}"

echo "=== 3. train + ablation (D5-D11) ==="
"$PY" -m dualamp_lite train --workdir "$WORK" --models "$MODELS" \
  --seeds "$SEEDS" --folds "$FOLDS" --epochs "$EPOCHS" --device "$DEVICE"

echo "=== 4. report + manifest (D10/D15) ==="
"$PY" -m dualamp_lite report --workdir "$WORK"

echo "done -> $WORK/manuscript/D10_evaluation_report.md"
