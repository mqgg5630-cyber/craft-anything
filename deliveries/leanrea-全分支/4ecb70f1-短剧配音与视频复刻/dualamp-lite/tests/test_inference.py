"""V4 test 10: the exported inference program scores a FASTA end to end."""

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd

from dualamp_lite.v4.pipeline import stage_export
from dualamp_lite.v4.train import FeatureStore, run_final
from tests.v4_fixture import build_workspace, cleanup


class InferenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.paths, _, cls.ctx = build_workspace()
        cls.cfg.train.models = ("M1",)
        cls.cfg.train.seeds = (11,)
        run_final(cls.cfg, cls.paths, "test", FeatureStore(cls.paths), logger=None, epochs=1)
        stage_export(cls.ctx)
        export = cls.paths.root / "export"
        target = export / "final_models"
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(cls.paths.final_models / "test", target / "test")

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.paths)

    def test_export_files_exist(self):
        export = self.paths.root / "export"
        for name in ("inference.py", "example.fasta", "MODEL_CARD.md", "ensemble_recipe.json"):
            self.assertTrue((export / name).exists(), name)

    def test_inference_runs_and_writes_scores(self):
        export = self.paths.root / "export"
        out = export / "scores.csv"
        cmd = [
            sys.executable, str(export / "inference.py"),
            "--fasta", str(export / "example.fasta"),
            "--model", "M1", "--backend", "mock", "--out", str(out),
        ]
        env = dict(**os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        proc = subprocess.run(cmd, cwd=str(self.paths.root), capture_output=True, text=True, timeout=180, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        scores = pd.read_csv(out)
        self.assertEqual(len(scores), 10)
        self.assertTrue(scores["prob"].between(0, 1).all())
        self.assertEqual(scores["sequence_id"].nunique(), 10)


if __name__ == "__main__":
    unittest.main()
