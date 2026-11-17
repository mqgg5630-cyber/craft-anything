"""V4 test 3: cluster / parent leakage and fold integrity."""

import unittest

import pandas as pd

from tests.v4_fixture import build_workspace, cleanup


class SplitLeakageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.paths, _, _ = build_workspace()

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.paths)

    def test_no_cluster_or_parent_overlap(self):
        dev = pd.read_csv(self.paths.split_csv("development"))
        test = pd.read_csv(self.paths.split_csv("internal_test"))
        self.assertFalse(set(dev["identity_cluster"]) & set(test["identity_cluster"]))
        self.assertFalse((set(dev["parent_id"]) - {""}) & (set(test["parent_id"]) - {""}))
        self.assertFalse(set(dev["seq"]) & set(test["seq"]))

    def test_dev_test_ratio_and_classes(self):
        dev = pd.read_csv(self.paths.split_csv("development"))
        test = pd.read_csv(self.paths.split_csv("internal_test"))
        self.assertEqual(dev["label"].nunique(), 2)
        self.assertEqual(test["label"].nunique(), 2)
        share = len(test) / (len(dev) + len(test))
        self.assertGreater(share, 0.08)
        self.assertLess(share, 0.45)

    def test_every_fold_has_both_classes(self):
        dev = pd.read_csv(self.paths.split_csv("development"))
        for seed in self.cfg.train.seeds:
            column = f"fold_seed_{seed}"
            self.assertIn(column, dev.columns)
            self.assertTrue((dev[column] >= 0).all())
            for _, grp in dev.groupby(column):
                self.assertEqual(grp["label"].nunique(), 2)
            folds = pd.read_csv(self.paths.fold_csv(seed))
            self.assertEqual(len(folds), len(dev))

    def test_scrambled_and_hard_sets_are_separate(self):
        dev = pd.read_csv(self.paths.split_csv("development"))
        scrambled = pd.read_csv(self.paths.split_csv("scrambled_test"))
        hard = pd.read_csv(self.paths.split_csv("hard_negative_test"))
        self.assertNotIn("scrambled_test", set(dev["split"]))
        self.assertFalse(set(scrambled["seq"]) & set(dev["seq"]))
        self.assertFalse(set(hard["seq"]) & set(dev["seq"]))


if __name__ == "__main__":
    unittest.main()
