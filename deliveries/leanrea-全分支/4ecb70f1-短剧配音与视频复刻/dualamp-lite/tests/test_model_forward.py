"""V4 test 8: frozen architecture shapes (batch 32, L 50, 480 + 32)."""

import unittest

import torch

from dualamp_lite.v4.models import M2, M3, build_model, count_parameters


class ModelForwardTest(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(0)
        self.batch = 32
        self.length = 50
        self.mean = torch.randn(self.batch, 480)
        self.phys = torch.randn(self.batch, 32)
        self.residue = torch.randn(self.batch, self.length, 480)
        self.mask = torch.ones(self.batch, self.length, dtype=torch.bool)
        self.mask[:4, -5:] = False

    def test_all_models_return_one_logit_per_sample(self):
        for name in ("M1", "M2", "M3"):
            model = build_model(name, embed_dim=480, n_phys=32, dropout=0.0).eval()
            with torch.no_grad():
                out = model(mean=self.mean, phys=self.phys, residue=self.residue, mask=self.mask)
            self.assertEqual(tuple(out.shape), (self.batch,), name)
            self.assertTrue(torch.isfinite(out).all(), name)

    def test_parameter_counts_are_stable(self):
        counts = {name: count_parameters(build_model(name, 480, 32, 0.3)) for name in ("M1", "M2", "M3")}
        self.assertEqual(counts["M1"], 480 * 128 + 128 + 32 * 64 + 64 + 192 * 64 + 64 + 64 + 1)
        self.assertGreater(counts["M2"], 480 * 128)
        self.assertGreater(counts["M3"], counts["M2"])

    def test_m3_has_no_extra_pooling_module(self):
        model = M3()
        names = {name for name, _ in model.named_modules()}
        self.assertFalse(any("pool" in n for n in names))

    def test_m2_and_m3_share_the_cnn_branch_definition(self):
        self.assertIsInstance(M2().branch, type(M3().branch))
        self.assertEqual(M2().branch.compress[0].out_features, 128)
        self.assertEqual(M3().phys_proj[0].out_features, 64)


if __name__ == "__main__":
    unittest.main()
