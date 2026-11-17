"""Unit tests for the §5 statistical machinery."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dualamp_lite import evaluate as ev  # noqa: E402


class TestBinaryMetrics(unittest.TestCase):
    def test_perfect_classifier(self):
        y = np.array([1, 1, 1, 0, 0, 0])
        s = np.array([0.9, 0.8, 0.7, 0.2, 0.1, 0.05])
        m = ev.binary_metrics(y, s, threshold=0.5)
        self.assertAlmostEqual(m["auroc"], 1.0)
        self.assertAlmostEqual(m["mcc"], 1.0)
        self.assertAlmostEqual(m["sensitivity"], 1.0)
        self.assertAlmostEqual(m["specificity"], 1.0)

    def test_inverted_classifier(self):
        y = np.array([1, 1, 1, 0, 0, 0])
        s = np.array([0.1, 0.2, 0.05, 0.9, 0.8, 0.7])
        m = ev.binary_metrics(y, s, threshold=0.5)
        self.assertAlmostEqual(m["auroc"], 0.0)
        self.assertLess(m["mcc"], 0)

    def test_threshold_rule_improves_mcc(self):
        rng = np.random.default_rng(1)
        y = rng.integers(0, 2, 200)
        s = np.clip(y * 0.35 + rng.normal(0, 0.35, 200) + 0.1, 0, 1)
        tuned = ev.best_threshold(y, s, "mcc")
        self.assertGreaterEqual(
            ev.binary_metrics(y, s, tuned)["mcc"],
            ev.binary_metrics(y, s, 0.5)["mcc"] - 1e-9,
        )


class TestDeLong(unittest.TestCase):
    def test_identical_scores_are_not_different(self):
        rng = np.random.default_rng(0)
        y = np.r_[np.ones(60), np.zeros(60)].astype(int)
        s = y * 0.5 + rng.normal(0, 0.4, 120)
        out = ev.delong_test(y, s, s.copy())
        self.assertAlmostEqual(out["auc_diff"], 0.0)
        self.assertAlmostEqual(out["p_value"], 1.0)

    def test_better_model_has_negative_log_p(self):
        rng = np.random.default_rng(2)
        y = np.r_[np.ones(80), np.zeros(80)].astype(int)
        good = y * 0.8 + rng.normal(0, 0.25, 160)
        bad = y * 0.2 + rng.normal(0, 0.8, 160)
        out = ev.delong_test(y, good, bad)
        self.assertGreater(out["auc_diff"], 0)
        self.assertLess(out["p_value"], 0.01)

    def test_ci_brackets_point_estimate(self):
        rng = np.random.default_rng(3)
        y = np.r_[np.ones(50), np.zeros(50)].astype(int)
        s = y * 0.6 + rng.normal(0, 0.5, 100)
        point, lo, hi = ev.delong_ci(y, s)
        self.assertLessEqual(lo, point)
        self.assertGreaterEqual(hi, point)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)

    def test_degenerate_labels(self):
        out = ev.delong_test(np.zeros(10, dtype=int), np.random.rand(10), np.random.rand(10))
        self.assertTrue(np.isnan(out["p_value"]))


class TestBootstrap(unittest.TestCase):
    def test_cluster_bootstrap_returns_intervals(self):
        rng = np.random.default_rng(4)
        y = rng.integers(0, 2, 120)
        s = np.clip(y * 0.4 + rng.normal(0, 0.4, 120), 0, 1)
        clusters = np.repeat(np.arange(60), 2)
        out = ev.cluster_bootstrap(y, s, clusters, n_boot=300, seed=1)
        for metric in ("auroc", "mcc", "auprc"):
            self.assertIn(metric, out)
            self.assertLessEqual(out[metric]["ci_low"], out[metric]["ci_high"])
            self.assertGreater(out[metric]["n_boot_effective"], 50)

    def test_paired_bootstrap_detects_identical_models(self):
        rng = np.random.default_rng(5)
        y = rng.integers(0, 2, 100)
        s = rng.random(100)
        out = ev.paired_bootstrap(y, s, s.copy(), np.arange(100), metric="mcc", n_boot=200)
        self.assertAlmostEqual(out["delta"], 0.0)
        self.assertGreater(out["p_value"], 0.5)

    def test_fdr_is_monotone_and_bounded(self):
        rows = ev.bh_fdr([0.001, 0.01, 0.2, 0.9])
        q = [r["q_value"] for r in rows]
        self.assertTrue(all(0 <= v <= 1 for v in q))
        self.assertTrue(rows[0]["significant"])
        self.assertFalse(rows[-1]["significant"])
        self.assertLessEqual(q[0], q[1])


class TestComparison(unittest.TestCase):
    def test_equivalence_margin_prevents_overclaiming(self):
        comp = ev.Comparison(
            model_a="M3", model_b="M2", metric="mcc", delta=0.005,
            ci_low=-0.02, ci_high=0.03, p_value=0.6, equivalence_margin=0.02,
        )
        row = comp.to_row()
        self.assertTrue(row["within_margin"])
        self.assertIn("no meaningful difference", row["conclusion"])


if __name__ == "__main__":
    unittest.main()
