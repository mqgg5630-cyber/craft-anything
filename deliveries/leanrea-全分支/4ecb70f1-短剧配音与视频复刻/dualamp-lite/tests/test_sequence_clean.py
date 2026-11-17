"""V4 test 1: sequence cleaning and the 10-50 aa / 20-AA contract."""

import unittest

from dualamp_lite.seq import clean_sequence, sequence_problems
from dualamp_lite.v4 import schema


class SequenceCleanTest(unittest.TestCase):
    def test_cleaning_normalises_case_and_whitespace(self):
        self.assertEqual(clean_sequence(" acd ef\nghik "), "ACDEFGHIK")
        self.assertEqual(clean_sequence("ACDEF*"), "ACDEF")
        self.assertEqual(clean_sequence("ACD123EF"), "ACDEF")

    def test_length_window_is_enforced(self):
        self.assertIn("too_short", sequence_problems("ACDEFGHIK", 10, 50))
        self.assertIn("too_long", sequence_problems("A" * 51, 10, 50))
        self.assertIsNone(sequence_problems("ACDEFGHIKL", 10, 50))

    def test_non_standard_residues_are_rejected(self):
        self.assertIn("non_standard", sequence_problems("ACDEFGHIKB", 10, 50))
        with self.assertRaises(ValueError):
            schema.assert_valid("ACDEFGHIKB")
        with self.assertRaises(ValueError):
            schema.assert_valid("ACDEFGHIK")  # 9 aa < 10

    def test_valid_sequence_passes(self):
        schema.assert_valid("KRFAIKKLLR")  # 10 aa, only standard residues


if __name__ == "__main__":
    unittest.main()
