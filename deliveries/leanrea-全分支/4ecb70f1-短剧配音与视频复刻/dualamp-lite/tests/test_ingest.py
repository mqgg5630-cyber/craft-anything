"""Source-manifest ingestion: CSV/TSV columns, filters, fragmenting, audit rows."""

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dualamp_lite.config import DatasetConfig, Paths  # noqa: E402
from dualamp_lite.dataset import build_dataset, load_manifest, read_sources  # noqa: E402


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return path


class TestManifestIngestion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw"

        write(self.raw / "amp.csv", """
            ID,Sequence,Validity,Source,Activity
            1,GIGKFLHSAKKF,Experimentally Validated,Frog,Skin
            2,GLFDIIKKIAESF,Experimentally Validated,Bacteria,Gut
            3,ACDEFGHIKLMNPQRSTVWY,Patent,Company,None
            4,KKLLKKLL,Experimentally Validated,Human,Gut
            5,GIGKFLHSAKK,Not validated,Unknown,None
        """)
        write(self.raw / "inactive.tsv", """
            Sequence\tActivity\tMIC\tTarget Species
            ACDEFGHIK\tInactive\t128\tE. coli
            KLKLKLKLK\tInactive\t64\tS. aureus
            GIGKFLHSA\tActive\t4\tE. coli
        """)
        write(self.raw / "background.fasta", """
            >sp|P00001|AMPR_BACSU Antimicrobial resistance protein
            MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR
            >sp|P00002|HOUSE_MOUSE Uncharacterized protein
            MGSSHHHHHHSSGLVPRGSHMASMTGGQQMGRGSMAHHHHHHVGTGSNDDDDKSPDPTTPDFLNSLLL
        """)
        write(self.raw / "sources.yaml", """
            sources:
              - id: amp_csv
                path: amp.csv
                format: csv
                layer: general_amp
                seq_column: Sequence
                label_column: Validity
                positive_values: ["Experimentally Validated"]
                negative_values: ["Patent", "Not validated"]
                filters:
                  notna: [Sequence]
                metadata:
                  organism: Source
                  activity: Activity
              - id: inactive_tsv
                path: inactive.tsv
                format: tsv
                layer: hard_negative
                seq_column: Sequence
                label_column: Activity
                positive_values: ["Active"]
                negative_values: ["Inactive"]
                metadata:
                  mic: MIC
                  strain: Target Species
              - id: background
                path: background.fasta
                format: fasta
                layer: negative_background
                label: 0
                fragment:
                  min_len: 8
                  max_len: 20
                  per_protein: 2
                  seed: 5
                  exclude_keywords: [antimicrobial]
        """)
        self.manifest = self.raw / "sources.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def test_manifest_parses(self):
        specs, base = load_manifest(self.manifest)
        self.assertEqual(len(specs), 3)
        self.assertEqual(specs[0].id, "amp_csv")
        self.assertEqual(specs[1].format, "tsv")
        self.assertEqual(specs[2].fragment["per_protein"], 2)
        self.assertEqual(base, self.raw)

    def test_columns_labels_filters_and_metadata(self):
        df, audit = read_sources(self.manifest, min_len=5, max_len=50)
        by_source = df.groupby("source")
        # the "Patent" row is mapped to label 0, not silently treated as a positive
        self.assertEqual(len(by_source.get_group("amp_csv")), 5)
        valid = df[df["seq"] == "GIGKFLHSAKKF"].iloc[0]
        self.assertEqual(valid["label"], 1)
        self.assertEqual(valid["organism"], "Frog")
        self.assertEqual(df[df["seq"] == "ACDEFGHIKLMNPQRSTVWY"].iloc[0]["label"], 0)
        # MIC metadata is carried through for hard negatives
        inactive = df[df["seq"] == "ACDEFGHIK"].iloc[0]
        self.assertEqual(inactive["mic"], "128")
        self.assertEqual(inactive["strain"], "E. coli")
        # the AMP-annotated UniProt entry is excluded from the negative background
        background = by_source.get_group("background")
        self.assertEqual(len(background), 2)  # one protein x per_protein=2

    def test_fragment_lengths_respect_window(self):
        df, _ = read_sources(self.manifest, min_len=5, max_len=50)
        background = df[df["source"] == "background"]
        lengths = background["seq"].str.len()
        self.assertTrue(((lengths >= 8) & (lengths <= 20)).all(), lengths.tolist())
        self.assertTrue(background["uniprot_id"].str.startswith("P00002").all())

    def test_bad_manifest_is_rejected(self):
        write(self.raw / "bad.yaml", """
            sources:
              - id: x
                path: amp.csv
                format: csv
                seq_column: not_a_column
        """)
        with self.assertRaises(ValueError):
            read_sources(self.raw / "bad.yaml", 5, 50)

    def test_missing_source_file_raises(self):
        write(self.raw / "missing.yaml", """
            sources:
              - id: x
                path: nope.csv
                format: csv
        """)
        with self.assertRaises(FileNotFoundError):
            read_sources(self.raw / "missing.yaml", 5, 50)

    def test_end_to_end_build_from_manifest(self):
        paths = Paths(self.root / "work")
        cfg = DatasetConfig(cluster_method="kmer", max_scrambled=0, test_frac=0.3, val_frac=0.2)
        summary = build_dataset(cfg, paths, manifest=self.manifest)
        self.assertGreater(summary["n_sequences"], 5)
        self.assertEqual(summary["inputs"]["manifest"], str(self.manifest))
        # label audit records at least the too-short/duplicate decisions
        audit = pd.read_csv(paths.label_audit)
        self.assertIn("reason", audit.columns)
        dataset = pd.read_csv(paths.dataset_all)
        self.assertTrue(set(dataset["layer"]) <= {
            "general_amp", "hard_negative", "negative_background", "bacterial_amp", "external", "scrambled"})


if __name__ == "__main__":
    unittest.main()
