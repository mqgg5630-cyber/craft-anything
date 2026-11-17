"""V4 test 9: every run directory is complete and the checkpoint reloads."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from dualamp_lite.v4.models import build_model
from dualamp_lite.v4.train import FeatureStore, train_fold
from tests.v4_fixture import build_workspace, cleanup

REQUIRED = (
    "config.yaml",
    "best_model.pt",
    "last_model.pt",
    "train_log.csv",
    "predictions.csv",
    "metrics.json",
    "environment.txt",
    "rng_state.pt",
    "scaler.joblib",
)


class CheckpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.paths, _, _ = build_workspace()
        store = FeatureStore(cls.paths)
        dev = store.pool(cls.paths, "development")
        folds = pd.read_csv(cls.paths.fold_csv(cls.cfg.train.seeds[0]))
        fold_of = dict(zip(folds["sequence_id"], folds["fold"]))
        fold = np.asarray([fold_of[sid] for sid in dev.ids])
        cls.train_pool = dev.take(np.where(fold != 0)[0])
        cls.val_pool = dev.take(np.where(fold == 0)[0])
        cls.out = Path(tempfile.mkdtemp(prefix="dualamp_ckpt_"))
        cls.result = train_fold(
            cls.cfg.train, "M1", 11, 0, cls.train_pool, cls.val_pool, cls.out,
            None, embed_dim=cls.cfg.features.embed_dim, max_epochs=1, save=True,
        )

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.paths)

    def test_all_artefacts_written(self):
        for name in REQUIRED:
            self.assertTrue((self.out / name).exists(), name)

    def test_metrics_payload(self):
        import json

        payload = json.loads((self.out / "metrics.json").read_text())
        self.assertEqual(payload["model"], "M1")
        self.assertEqual(payload["seed"], 11)
        self.assertIn("val_metrics", payload)
        self.assertIn("thresholds", payload)
        self.assertIn("n_params", payload)

    def test_checkpoint_reload_reproduces_predictions(self):
        ckpt = torch.load(self.out / "best_model.pt", map_location="cpu")
        model = build_model("M1", embed_dim=ckpt["embed_dim"], n_phys=ckpt["n_phys"], dropout=0.0)
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        phys = (self.val_pool.phys - ckpt["scaler_mean"]) / ckpt["scaler_scale"]
        with torch.no_grad():
            probs = torch.sigmoid(
                model(
                    mean=torch.from_numpy(self.val_pool.mean.astype(np.float32)),
                    phys=torch.from_numpy(phys.astype(np.float32)),
                    residue=torch.from_numpy(self.val_pool.residue.astype(np.float32)),
                    mask=torch.from_numpy(self.val_pool.mask.astype(bool)),
                )
            ).numpy()
        saved = pd.read_csv(self.out / "predictions.csv")["prob"].to_numpy()
        np.testing.assert_allclose(probs, saved, atol=1e-5)


if __name__ == "__main__":
    unittest.main()
