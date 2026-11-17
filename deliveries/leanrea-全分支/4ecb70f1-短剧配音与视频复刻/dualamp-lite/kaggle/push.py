#!/usr/bin/env python3
"""Push the DualAMP-Lite Kaggle notebook and follow its status.

    python kaggle/push.py --id yourname/dualamp-lite-run \
        --dataset yourname/dualamp-raw [--dataset yourname/dualamp-esm2]

Requires the Kaggle CLI and `~/.kaggle/kaggle.json`:
    pip install kaggle
    # Account -> Create New API Token -> ~/.kaggle/kaggle.json

The script edits a *copy* of kernel-metadata.json in a temp folder so the
committed template keeps its placeholder values.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE.parent / "notebooks" / "DualAMP_Lite_Kaggle.ipynb"
METADATA = HERE / "kernel-metadata.json"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--id", required=True, help="kernel id, e.g. yourname/dualamp-lite-run")
    parser.add_argument("--dataset", action="append", default=[], help="dataset slug (repeatable)")
    parser.add_argument("--no-internet", action="store_true", help="keep internet disabled (offline weights)")
    parser.add_argument("--cpu", action="store_true", help="disable GPU (only useful for a demo run)")
    parser.add_argument("--status", action="store_true", help="poll `kaggle kernels status` after pushing")
    args = parser.parse_args()

    if shutil.which("kaggle") is None:
        print("kaggle CLI not found: pip install kaggle", file=sys.stderr)
        return 2
    if not NOTEBOOK.exists():
        print(f"notebook missing: {NOTEBOOK}", file=sys.stderr)
        return 2

    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    metadata["id"] = args.id
    metadata["title"] = args.id.split("/")[-1].replace("-", " ").title()
    metadata["enable_internet"] = not args.no_internet
    metadata["enable_gpu"] = not args.cpu
    if args.dataset:
        metadata["dataset_sources"] = args.dataset
    elif metadata["dataset_sources"] == ["yourname/dualamp-raw"]:
        print("warning: dataset_sources still contains the placeholder 'yourname/dualamp-raw'",
              file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        shutil.copy2(NOTEBOOK, tmpdir / NOTEBOOK.name)
        payload = dict(metadata)
        payload["code_file"] = NOTEBOOK.name
        (tmpdir / "kernel-metadata.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        run(["kaggle", "kernels", "push", "-p", str(tmpdir)])

    if args.status:
        run(["kaggle", "kernels", "status", args.id])
    print(
        "\nfetch the artefacts with:\n"
        f"  kaggle kernels output {args.id} -p ./kaggle_out\n"
        "and unzip: ./kaggle_out/dualamp-lite-output.zip"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
