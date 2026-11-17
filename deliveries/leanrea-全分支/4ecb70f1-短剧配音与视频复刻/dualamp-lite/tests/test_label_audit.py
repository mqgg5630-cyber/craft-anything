"""V4 test 2: dataset_master / excluded_records / label audit."""

import unittest

import pandas as pd

from dualamp_lite.v4.config import POSITIVE_LAYERS
from tests.v4_fixture import build_workspace, cleanup


class LabelAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.paths, _, _ = build_workspace()

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.paths)

    def test_master_table_exists_and_is_unique(self):
        master = pd.read_csv(self.paths.dataset_master, sep="\t", keep_default_na=False)
        self.assertGreater(len(master), 50)
        self.assertFalse(master["seq"].duplicated().any())
        self.assertTrue(set(master["label"].unique()) <= {0, 1})

    def test_positive_layers_are_labelled_positive(self):
        master = pd.read_csv(self.paths.dataset_master, sep="\t", keep_default_na=False)
        positives = master[master["layer"].isin(POSITIVE_LAYERS)]
        self.assertTrue((positives["label"] == 1).all())
        negatives = master[master["layer"].isin(["negative_background", "hard_negative", "scrambled"])]
        self.assertTrue((negatives["label"] == 0).all())

    def test_hard_negatives_are_challenge_only(self):
        self.assertFalse(self.cfg.dataset.hard_negative_in_training)
        master = pd.read_csv(self.paths.dataset_master, sep="\t", keep_default_na=False)
        self.assertIn("hard_negative", set(master["layer"]))
        self.assertTrue((master.loc[master["layer"] == "hard_negative", "label"] == 0).all())

    def test_excluded_and_audit_files(self):
        excluded = pd.read_csv(self.paths.excluded_records, sep="\t")
        for column in ("sequence_id", "seq", "reason", "detail", "source", "layer"):
            self.assertIn(column, excluded.columns)
        audit = pd.read_csv(self.paths.label_audit)
        self.assertIn("general_amp", set(audit["layer"]))
        self.assertEqual(int(audit.loc[audit["layer"] == "general_amp", "n_positive"].iloc[0]) > 0, True)


if __name__ == "__main__":
    unittest.main()
