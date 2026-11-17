"""V4 test 6: encoder output shapes, masking and determinism."""

import unittest

import numpy as np

from dualamp_lite.v4.features import MockEncoder
from tests.v4_fixture import build_workspace, cleanup


class ESMShapeTest(unittest.TestCase):
    def test_mock_encoder_shapes(self):
        encoder = MockEncoder(embed_dim=480, max_len=50)
        seqs = ["KRFAIKKLLR", "GAVLIPFYWSTV"]
        residue, mean, mask = encoder.encode(seqs)
        self.assertEqual(residue.shape[1:], (12, 480))
        self.assertEqual(mean.shape, (2, 480))
        self.assertEqual(mask.shape, (2, 12))
        self.assertEqual(int(mask.sum(axis=1)[0]), 10)
        self.assertEqual(int(mask.sum(axis=1)[1]), 12)

    def test_mean_is_the_masked_mean(self):
        encoder = MockEncoder(embed_dim=32, max_len=20)
        residue, mean, mask = encoder.encode(["ACDEFGHIKL"])
        expected = residue[0, :10].astype(np.float32).mean(axis=0)
        np.testing.assert_allclose(mean[0], expected, rtol=1e-2, atol=1e-3)

    def test_encoding_is_deterministic(self):
        encoder = MockEncoder(embed_dim=16, max_len=20)
        a = encoder.encode(["KRFAIKKLLR"])[1]
        b = encoder.encode(["KRFAIKKLLR"])[1]
        np.testing.assert_allclose(a, b)


class FeatureCacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.paths, _, _ = build_workspace()

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.paths)

    def test_feature_files_and_shapes(self):
        blob = np.load(self.paths.esm_split("development"))
        self.assertEqual(blob["mean"].shape[1], 480)
        self.assertEqual(blob["residue"].shape[2], 480)
        self.assertEqual(len(blob["ids"]), blob["mask"].shape[0])
        self.assertTrue((blob["mask"].sum(axis=1) > 0).all())
        meta = __import__("json").loads((self.paths.features / "feature_meta.json").read_text())
        self.assertEqual(meta["backend"], "mock")
        self.assertTrue(meta["is_mock"])


if __name__ == "__main__":
    unittest.main()
