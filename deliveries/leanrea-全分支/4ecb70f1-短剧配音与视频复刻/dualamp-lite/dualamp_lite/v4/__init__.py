"""DualAMP-Lite V1.0 - the V4-frozen, reproducibility-first AMP model pipeline.

This sub-package implements the third review (V4, 2026-11-09 23:55) line by line:

* frozen 32-dimensional biophysical schema (``schema.py`` + ``feature_schema.json``)
* frozen M1 / M2 / M3 architectures (``models.py``)
* development 80 % / internal-test 20 % cluster-grouped split and 5 folds
* 5 seeds x 5 folds = 25 audited runs per model, each with its own directory
* 5 final full-development models + mean-probability ensemble, test touched once
* environment lock files, SHA256 manifest, staged ``run_pipeline.py`` entry point

The legacy modules one level up (``biophys``, ``features``, ``train``, ``cli``)
implement the earlier V3 draft and are kept only so that the historical unit
tests still run; nothing in this sub-package imports their training code.
"""

from __future__ import annotations

__version__ = "1.0.0"
SCHEMA_VERSION = "v1.0"

__all__ = ["__version__", "SCHEMA_VERSION"]
