"""End-to-end smoke test: demo data -> features -> two models -> report.

Kept deliberately tiny (60 s on 2 CPU cores) so it can run in CI and in the first
cell of a Kaggle/Colab notebook. It uses the mock encoder, therefore the metrics
are assertions about *plumbing*, not about peptides.
"""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dualamp_lite.config import DatasetConfig, DemoConfig, FeatureConfig, Paths, TrainConfig  # noqa: E402
from dualamp_lite.dataset import build_dataset  # noqa: E402
from dualamp_lite.features import extract_all  # noqa: E402
from dualamp_lite.report import build_report  # noqa: E402
from dualamp_lite.synth import demo_dataframe  # noqa: E402
from dualamp_lite.train import run_training  # noqa: E402


class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.paths = Paths(Path(cls.tmp.name) / "run")
        build_dataset(
            DatasetConfig(cluster_method="kmer", max_scrambled=20, seed=1),
            cls.paths,
            demo_source=demo_dataframe(
                DemoConfig(n_positive=80, n_negative=80, n_hard_negative=20, n_bacterial=20, n_external=20)
            ),
        )
        extract_all(
            FeatureConfig(backend="mock", embed_dim=32, batch_size=32),
            cls.paths,
            force=True,
        )
        cls.payload = run_training(
            TrainConfig(models=("M0_RF", "M1"), seeds=(1,), folds=2, epochs=2, batch_size=32,
                        num_workers=0, n_boot=50, patience=2),
            cls.paths,
        )
        build_report(cls.paths, with_figures=False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_feature_shapes(self):
        data = np.load(self.paths.split_features("train"))
        self.assertEqual(data["residue"].shape[0], data["labels"].shape[0])
        self.assertEqual(data["residue"].shape[2], 32)
        self.assertEqual(data["physio"].shape[1], 35)
        self.assertTrue(data["mask"].dtype == bool)
        # masked mean must equal the manual computation over real residues only
        residue, mask, mean = data["residue"], data["mask"], data["mean"]
        manual = (residue.astype(np.float32) * mask[..., None]).sum(1) / mask.sum(1, keepdims=True)
        self.assertTrue(np.allclose(mean, manual, atol=1e-2))

    def test_metrics_and_scores_written(self):
        self.assertTrue(self.paths.metrics_table.exists())
        self.assertTrue(self.paths.ablation_table.exists())
        self.assertTrue((self.paths.model / "M1_scores.npz").exists())
        self.assertTrue((self.paths.model / "M1_seed1.pt").exists())
        import pandas as pd

        df = pd.read_csv(self.paths.metrics_table)
        self.assertEqual(set(df["model"]), {"M0_RF", "M1"})
        for column in ("auroc", "auprc", "mcc", "sensitivity", "specificity"):
            self.assertTrue(df[column].between(0, 1).all(), column)

    def test_checkpoint_reloads(self):
        import torch

        from dualamp_lite.features import load_split
        from dualamp_lite.models import build_model

        blob = torch.load(self.paths.model / "M1_seed1.pt", weights_only=False)
        model = build_model("M1", embed_dim=blob["embed_dim"], n_physio=blob["n_physio"])
        model.load_state_dict(blob["state_dict"])
        data = load_split(self.paths, "test")
        with torch.no_grad():
            logits = model(
                torch.from_numpy(data["residue"].astype(np.float32)),
                torch.from_numpy(data["mask"]),
                torch.from_numpy(data["physio"]),
                torch.from_numpy(data["mean"]),
            )
        self.assertEqual(logits.shape, (len(data["labels"]),))
        self.assertTrue(torch.isfinite(logits).all())

    def test_report_and_manifest(self):
        self.assertTrue(self.paths.report.exists())
        text = self.paths.report.read_text(encoding="utf-8")
        self.assertIn("Mandatory caveats", text)
        self.assertIn("MOCK encoder", text)  # the report must flag meaningless numbers
        from dualamp_lite.utils import write_file_manifest

        n = write_file_manifest(self.paths.root, self.paths.file_manifest)
        self.assertGreater(n, 5)

    def test_training_result_structure(self):
        models = {m["model"]: m for m in self.payload["models"]}
        self.assertEqual(set(models), {"M0_RF", "M1"})
        m1 = models["M1"]
        self.assertEqual(len(m1["per_seed"]), 1)
        self.assertIn("auroc", m1["test_ci"])
        self.assertLessEqual(m1["test_ci"]["auroc"]["ci_low"], m1["test_metrics"]["auroc"] + 1e-6)
        self.assertGreaterEqual(m1["test_ci"]["auroc"]["ci_high"], m1["test_metrics"]["auroc"] - 1e-6)


if __name__ == "__main__":
    unittest.main()
