"""Unit tests for cleaning, scrambling, clustering and the group-based split."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dualamp_lite import seq  # noqa: E402
from dualamp_lite.config import DatasetConfig, Paths  # noqa: E402
from dualamp_lite.dataset import build_dataset, seq_id  # noqa: E402
from dualamp_lite.synth import demo_dataframe  # noqa: E402


class TestSequenceIO(unittest.TestCase):
    def test_clean_sequence(self):
        self.assertEqual(seq.clean_sequence(" acd-ef gh12* "), "ACD-EFGH")
        self.assertEqual(seq.clean_sequence("MKTAYIAKQRQISFVKSHFSRQDILDLWIY"), "MKTAYIAKQRQISFVKSHFSRQDILDLWIY")

    def test_validation(self):
        self.assertTrue(seq.is_valid_sequence("GIGKFLHSAKKF"))
        self.assertFalse(seq.is_valid_sequence("GIGKFLHSAKKF", max_len=5))
        self.assertFalse(seq.is_valid_sequence("GIGKFLHSAXB"))
        self.assertIn("non_standard", seq.sequence_problems("GIGKFLHSAXB"))

    def test_fasta_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.fasta"
            seq.write_fasta([("a", "MKTAYIAKQ"), ("b", "GIGKFLHSAKKF")], path)
            records = list(seq.read_fasta(path))
            self.assertEqual(records[0], ("a", "MKTAYIAKQ"))
            self.assertEqual(len(records), 2)

    def test_scramble_preserves_composition(self):
        original = "GIGKFLHSAKKFGKAFVGEIMNS"
        shuffled = seq.scramble(original, __import__("random").Random(0))
        self.assertNotEqual(original, shuffled)
        self.assertEqual(sorted(original), sorted(shuffled))

    def test_kmer_containment(self):
        self.assertAlmostEqual(seq.kmer_containment("ACDEFG", "ACDEFG", 3), 1.0)
        self.assertLess(seq.kmer_containment("ACDEFG", "WWWWWW", 3), 0.2)


class TestBuildDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.paths = Paths(Path(cls.tmp.name) / "work")
        cls.cfg = DatasetConfig(
            cluster_method="kmer", cluster_identity=0.4, max_scrambled=100,
            min_len=5, max_len=50, seed=3,
        )
        cls.summary = build_dataset(cls.cfg, cls.paths, demo_source=demo_dataframe(), logger=None)
        import pandas as pd

        cls.df = pd.read_csv(cls.paths.dataset_all)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_outputs_exist(self):
        for path in (
            self.paths.dataset_all, self.paths.dataset_fasta, self.paths.cluster_table,
            self.paths.split_csv("train"), self.paths.split_csv("test"), self.paths.label_audit,
            self.paths.metadata_table,
        ):
            self.assertTrue(Path(path).exists(), path)

    def test_no_cluster_straddles_dev_or_test(self):
        # external/scrambled sequences may legitimately share a cluster with dev:
        # the scrambled set is derived from positives and external homology is the
        # whole point of the external_homolog split. Train/val/test must not.
        trainable = self.df[self.df["split"].isin(["train", "val", "test", "review"])]
        per_cluster = trainable.groupby("cluster")["split"].nunique()
        self.assertTrue((per_cluster == 1).all(), "a homology cluster leaked across train/val/test")

    def test_trainable_clusters_are_label_pure(self):
        # clusters with conflicting labels are allowed to exist, but only inside the
        # 'review' bucket - they must never reach train/val/test
        used = self.df[self.df["split"].isin(["train", "val", "test"])]
        labels = used.groupby("cluster")["label"].nunique()
        self.assertTrue((labels == 1).all(), "mixed-label cluster reached train/val/test")
        review = self.df[self.df["split"] == "review"]
        self.assertTrue(len(review) > 0)
        self.assertTrue(set(review["layer"]) <= {
            "general_amp", "bacterial_amp", "negative_background", "hard_negative"})

    def test_all_splits_have_both_classes(self):
        for split in ("train", "val", "test"):
            part = self.df[self.df["split"] == split]
            self.assertGreater(part["label"].nunique(), 1, split)

    def test_external_homologs_are_separated(self):
        external = self.df[self.df["layer"] == "external"]
        self.assertTrue(external["split"].isin(["external", "external_homolog"]).all())

    def test_split_sizes_are_sane(self):
        counts = self.df["split"].value_counts()
        self.assertGreater(counts.get("test", 0), 40)
        self.assertGreater(counts.get("train", 0), counts.get("test", 0))

    def test_scrambled_and_external_are_isolated(self):
        self.assertTrue((self.df.loc[self.df["layer"] == "scrambled", "split"] == "scrambled").all())
        external = self.df.loc[self.df["layer"] == "external", "split"]
        self.assertTrue(external.isin(["external", "external_homolog"]).all())

    def test_seq_id_is_stable(self):
        self.assertEqual(seq_id("MKTAYIAKQ"), seq_id("MKTAYIAKQ"))
        self.assertNotEqual(seq_id("MKTAYIAKQ"), seq_id("MKTAYIAKA"))

    def test_summary_counts_match_table(self):
        self.assertEqual(self.summary["n_sequences"], len(self.df))


if __name__ == "__main__":
    unittest.main()
