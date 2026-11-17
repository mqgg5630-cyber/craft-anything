"""V4 test 11: same seed twice -> identical probabilities; RNG state archived."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from dualamp_lite.v4.train import FeatureStore, train_fold
from tests.v4_fixture import build_workspace, cleanup


class ReproducibilityTest(unittest.TestCase):
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

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.paths)

    def test_same_seed_is_bit_identical(self):
        probs = []
        for repeat in range(2):
            result = train_fold(
                self.cfg.train, "M1", 11, 0, self.train_pool, self.val_pool,
                Path(tempfile.mkdtemp(prefix=f"dualamp_repro_{repeat}_")), None,
                embed_dim=self.cfg.features.embed_dim, max_epochs=1, save=False,
            )
            probs.append(result["val_probs"])
        np.testing.assert_allclose(probs[0], probs[1], atol=1e-8)

    def test_different_seed_changes_the_result(self):
        a = train_fold(self.cfg.train, "M1", 11, 0, self.train_pool, self.val_pool, Path(tempfile.mkdtemp()), None, embed_dim=self.cfg.features.embed_dim, max_epochs=1, save=False)
        b = train_fold(self.cfg.train, "M1", 23, 0, self.train_pool, self.val_pool, Path(tempfile.mkdtemp()), None, embed_dim=self.cfg.features.embed_dim, max_epochs=1, save=False)
        self.assertGreater(float(np.abs(a["val_probs"] - b["val_probs"]).max()), 0.0)


if __name__ == "__main__":
    unittest.main()
