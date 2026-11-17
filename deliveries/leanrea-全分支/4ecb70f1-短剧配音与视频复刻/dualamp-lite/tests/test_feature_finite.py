"""V4 test 5: every feature is finite on real data, and bad input errors out."""

import unittest

import numpy as np
import pandas as pd

from dualamp_lite.v4 import schema
from tests.v4_fixture import build_workspace, cleanup


class FeatureFiniteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.paths, _, _ = build_workspace()

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.paths)

    def test_matrix_is_finite_and_complete(self):
        blob = np.load(self.paths.physchem)
        X = blob["X"]
        self.assertEqual(X.shape[1], 32)
        self.assertTrue(np.all(np.isfinite(X)))
        self.assertEqual(len(blob["ids"]), len(set(blob["ids"].tolist())))

    def test_no_zero_variance_columns(self):
        X = np.load(self.paths.physchem)["X"]
        self.assertEqual(schema.zero_variance_columns(X), [])

    def test_moments_and_redundancy_tables(self):
        moments = pd.read_csv(self.paths.physchem_moments, index_col=0)
        self.assertEqual(len(moments), 32)
        redundancy = pd.read_csv(self.paths.redundancy)
        self.assertIn("feature_a", redundancy.columns)
        self.assertIn("pearson_r", redundancy.columns)

    def test_missing_value_policy_is_error(self):
        with self.assertRaises(ValueError):
            schema.compute_matrix(["ACDEFGHIKL", "ACDEFGHIKX"])
        # the length window is enforced at the boundary of the pipeline
        with self.assertRaises(ValueError):
            schema.assert_valid("ACDEFGHIK")


if __name__ == "__main__":
    unittest.main()
