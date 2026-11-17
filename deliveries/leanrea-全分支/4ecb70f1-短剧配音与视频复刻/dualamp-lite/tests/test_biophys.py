"""Unit tests for the V3 formula fixes (§3.3 P0)."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dualamp_lite import biophys  # noqa: E402


class TestAliphaticIndex(unittest.TestCase):
    def test_expasy_definition(self):
        # A=2/6, V=1/6, I=1/6, L=2/6  ->  33.333 + 2.9*16.667 + 3.9*(16.667+33.333)
        expected = 100 * (2 / 6) + 2.9 * 100 * (1 / 6) + 3.9 * 100 * ((1 / 6) + (2 / 6))
        self.assertAlmostEqual(biophys.aliphatic_index("ALVAIL"), expected, places=6)

    def test_poly_alanine(self):
        self.assertAlmostEqual(biophys.aliphatic_index("AAAAAA"), 100.0, places=6)

    def test_old_broken_formula_is_not_used(self):
        # the rejected V3 draft formula missed alanine entirely
        self.assertNotAlmostEqual(biophys.aliphatic_index("AAAAAAAAAV"), 29.0, places=2)


class TestChargeAndPI(unittest.TestCase):
    def test_net_charge_signs(self):
        self.assertGreater(biophys.net_charge("KKKK"), 3.5)
        self.assertLess(biophys.net_charge("DDDD"), -3.5)
        self.assertAlmostEqual(biophys.net_charge("KRDE"), 0.0, delta=0.35)

    def test_isoelectric_point(self):
        self.assertGreater(biophys.isoelectric_point("KKRK"), 9.0)
        self.assertLess(biophys.isoelectric_point("DDED"), 4.5)
        self.assertTrue(0 <= biophys.isoelectric_point("ACDEFGHIKLMNPQRSTVWY") <= 14)

    def test_charge_is_zero_at_pi(self):
        seq = "GIGKFLHSAKKFGKAFVGEIMNS"
        pi = biophys.isoelectric_point(seq)
        self.assertLess(abs(biophys.net_charge(seq, pi)), 0.05)


class TestDescriptors(unittest.TestCase):
    def test_gravy_and_mw(self):
        self.assertAlmostEqual(biophys.gravy("IIII"), 4.5, places=6)
        self.assertAlmostEqual(biophys.gravy("RRRR"), -4.5, places=6)
        self.assertGreater(biophys.molecular_weight("WWWW"), 700)

    def test_boman_fixed_source(self):
        self.assertAlmostEqual(biophys.boman_index("LLL"), 2.35, places=6)
        self.assertAlmostEqual(biophys.boman_index("RRR"), -14.92, places=6)

    def test_hydrophobic_moment_range(self):
        self.assertGreater(biophys.hydrophobic_moment("GIGKFLHSAKKFGKAFVGEIMNS"), 0)
        self.assertLessEqual(biophys.hydrophobic_moment("AAAAAA"), 0.3)

    def test_feature_vector_contract(self):
        seqs = ["GIGKFLHSAKKFGKAFVGEIMNS", "ACDEFGHIKLMNPQRSTVWY", "KKLLKKLL"]
        X = biophys.compute_features(seqs)
        self.assertEqual(X.shape, (3, biophys.N_FEATURES))
        self.assertEqual(biophys.N_FEATURES, 35)  # 20 AAC + 7 global + 5 amphipathic + 3 supplementary
        self.assertTrue(np.isfinite(X).all())
        # AAC block is a mole-percent composition and sums to 100 for each row
        self.assertTrue(np.allclose(X[:, :20].sum(axis=1), 100.0, atol=1e-3))
        # supplemental flag is binary and matches the instability threshold
        unstable = X[:, biophys.FEATURE_NAMES.index("unstable_flag")]
        self.assertTrue(set(np.unique(unstable)) <= {0.0, 1.0})

    def test_aac_is_permutation_invariant_but_moment_is_not(self):
        a = biophys.feature_dict("KKLLKKLL")
        b = biophys.feature_dict("LKLKLLKK")
        self.assertAlmostEqual(a["aac_K"], b["aac_K"])
        self.assertNotAlmostEqual(a["hydrophobic_moment_100deg"], b["hydrophobic_moment_100deg"], places=6)


class TestRedundancy(unittest.TestCase):
    def test_redundancy_report_finds_perfect_correlation(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=(50, 3))
        X = np.column_stack([x, x[:, 0] * 2.0])
        pairs = biophys.redundancy_report(X, names=["a", "b", "c", "d"], threshold=0.85)
        keys = {(p["feature_a"], p["feature_b"]) for p in pairs}
        self.assertIn(("a", "d"), keys)
        self.assertEqual(len(pairs), 1)


if __name__ == "__main__":
    unittest.main()
