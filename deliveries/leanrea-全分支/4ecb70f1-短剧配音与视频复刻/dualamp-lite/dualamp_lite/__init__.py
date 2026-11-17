"""DualAMP-Lite: ESM-2 frozen backbone + multi-scale CNN + biophysical prior.

Two generations of code live here:

* ``dualamp_lite.v4`` - the **V4-frozen, reproducibility-first pipeline**
  (32-dim schema, M1/M2/M3, 5x5 CV, staged ``run_pipeline.py``). This is the
  official implementation of the third review (2026-11-09 23:55).
* the modules directly in this package (``dataset``, ``biophys``, ``features``,
  ``train``, ``report``, ``cli``) implement the earlier V3 draft. They are kept
  only so the historical unit tests still run; nothing in ``v4`` imports their
  training code.

Entry points::

    python run_pipeline.py --stage all --demo --epochs 20   # V4 (official)
    python -m dualamp_lite --help                           # V3 (legacy)
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
