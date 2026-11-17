"""V4 test 4: the frozen 32-dim schema cannot drift."""

import json
import unittest

import numpy as np

from dualamp_lite.v4 import schema


class FeatureDimensionTest(unittest.TestCase):
    def test_exactly_32_features_in_frozen_order(self):
        self.assertEqual(schema.N_FEATURES, 32)
        self.assertEqual(len(schema.FEATURE_NAMES), 32)
        self.assertEqual(schema.FEATURE_NAMES[:20], tuple(f"aac_{aa}" for aa in "ACDEFGHIKLMNPQRSTVWY"))
        self.assertEqual(
            schema.FEATURE_NAMES[20:],
            (
                "molecular_weight",
                "net_charge_ph7_4",
                "isoelectric_point",
                "gravy",
                "instability_index",
                "aromaticity",
                "hydrophobic_moment_alpha",
                "hydrophobic_moment_beta",
                "cationic_residue_ratio",
                "boman_index",
                "aliphatic_index",
                "sequence_length",
            ),
        )

    def test_schema_file_is_written_with_the_policy(self):
        import tempfile
        from pathlib import Path

        path, digest = schema.write_schema(Path(tempfile.mkdtemp()) / "feature_schema.json")
        payload = json.loads(path.read_text())
        self.assertEqual(payload["feature_version"], "v1.0")
        self.assertEqual(payload["n_features"], 32)
        self.assertEqual(payload["aa_order"], "ACDEFGHIKLMNPQRSTVWY")
        self.assertEqual(payload["scaling"], "StandardScaler")
        self.assertEqual(payload["missing_value_policy"], "error")
        self.assertEqual(len(payload["features"]), 32)
        self.assertEqual(len(digest), 64)

    def test_aac_block_sums_to_one(self):
        values = schema.feature_dict("KRFAIKKLLR")
        aac = sum(v for k, v in values.items() if k.startswith("aac_"))
        self.assertAlmostEqual(aac, 1.0, places=9)
        self.assertEqual(values["sequence_length"], 10.0)

    def test_matrix_shape(self):
        X = schema.compute_matrix(["KRFAIKKLLR", "GAVLIPFYWST"])
        self.assertEqual(X.shape, (2, 32))
        self.assertTrue(np.all(np.isfinite(X)))


if __name__ == "__main__":
    unittest.main()
