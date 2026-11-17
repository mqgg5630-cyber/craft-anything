#!/usr/bin/env bash
# DualAMP-Lite V1.0 (V4 freeze) - single entry point.
#
#   ./scripts/run_v4.sh demo     # plumbing self-test: synthetic peptides + mock encoder
#   ./scripts/run_v4.sh real     # real run: needs configs/sources.yaml + ESM-2 weights
#
set -euo pipefail
cd "$(dirname "$0")/.."

export PYTHONHASHSEED="${PYTHONHASHSEED:-0}"
export CUBLAS_WORKSPACE_CONFIG="${CUBLAS_WORKSPACE_CONFIG:-:4096:8}"

mode="${1:-demo}"
case "$mode" in
  demo)
    python run_pipeline.py --stage all --demo --epochs 20 \
      --workdir demo_run --threads 2
    ;;
  real)
    : "${DUALAMP_MANIFEST:=configs/sources.yaml}"
    : "${DUALAMP_WORKDIR:=2026-11-09_DualAMP-Lite}"
    python run_pipeline.py --stage all \
      --manifest "$DUALAMP_MANIFEST" \
      --backend fair-esm --weights-dir cache/weights \
      --workdir "$DUALAMP_WORKDIR"
    ;;
  *)
    echo "usage: $0 {demo|real}" >&2
    exit 2
    ;;
esac
