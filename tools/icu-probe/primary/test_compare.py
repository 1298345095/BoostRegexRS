"""Regression gates against false full-key compatibility claims."""

import tempfile
import unittest
from pathlib import Path

from compare import compare


class FullKeyComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.cases, self.reference, self.candidate = (root / name for name in ("cases.tsv", "reference.tsv", "candidate.tsv"))
        self.cases.write_text("case_id\tutf8_hex\nempty\t\na\t61\n", encoding="utf-8")
        self.good = "case_id\traw_icu_hex\tboost_u32_hex\nempty\t00\t00000000\na\t2a,00\t0000002a\n"
        self.reference.write_text(self.good, encoding="utf-8")
        self.candidate.write_text(self.good, encoding="utf-8")

    def result(self):
        return compare(self.cases, self.reference, self.candidate)

    def test_full_keys_and_empty_single_zero_pass(self):
        self.assertEqual(self.result()["totals"]["passed"], 2)

    def test_same_order_different_complete_key_fails(self):
        self.candidate.write_text(self.good.replace("2a", "2b"), encoding="utf-8")
        self.assertEqual(self.result()["totals"]["mismatched"], 1)

    def test_changed_boost_wrapper_fails_even_if_icu_bytes_match(self):
        self.candidate.write_text(self.good.replace("0000002a", "0000002b"), encoding="utf-8")
        result = self.result()
        self.assertEqual(result["raw_icu_bytes_passed"], 2)
        self.assertEqual(result["boost_u32_keys_passed"], 1)
        self.assertEqual(result["totals"]["mismatched"], 1)

    def test_missing_and_duplicate_outputs_are_invalid(self):
        for value in (self.good.split("a\t2a")[0], self.good + "a\t2a,00\t0000002a\n"):
            with self.subTest(value=value):
                self.candidate.write_text(value, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.result()

    def test_reference_error_is_never_a_pass(self):
        self.reference.write_text(self.good.replace("00\t00000000", "ERROR:SIGNAL_11\tERROR:SIGNAL_11", 1), encoding="utf-8")
        result = self.result()
        self.assertEqual(result["totals"]["reference_error"], 1)
        self.assertEqual(result["totals"]["passed"], 1)

    def test_unsupported_is_never_a_pass(self):
        self.candidate.write_text(self.good.replace("00\t00000000", "UNSUPPORTED:INPUT\tUNSUPPORTED:INPUT", 1), encoding="utf-8")
        self.assertEqual(self.result()["totals"]["unsupported"], 1)

    def test_invalid_input_agreement_is_separate_from_key_passes(self):
        self.cases.write_text("case_id\tu32_hex\nsurrogate\t0000d800\n", encoding="utf-8")
        value = "case_id\traw_icu_hex\tboost_u32_hex\nsurrogate\tERROR:INVALID_UTF32\tERROR:INVALID_UTF32\n"
        self.reference.write_text(value, encoding="utf-8")
        self.candidate.write_text(value, encoding="utf-8")
        result = compare(self.cases, self.reference, self.candidate, "u32")
        self.assertEqual(result["totals"]["passed"], 0)
        self.assertEqual(result["totals"]["rejected_as_expected"], 1)

    def test_broken_oracle_wrapper_or_terminator_is_invalid(self):
        for value in (self.good.replace("0000002a", "0000002b"), self.good.replace("2a,00", "2a,01")):
            with self.subTest(value=value):
                self.reference.write_text(value, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.result()

    def test_agreeing_rejection_of_valid_input_is_not_a_pass(self):
        wrong = self.good.replace("2a,00\t0000002a", "ERROR:INVALID_UTF8\tERROR:INVALID_UTF8")
        self.reference.write_text(wrong, encoding="utf-8")
        self.candidate.write_text(wrong, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid oracle rejection"):
            self.result()

    def test_wrong_format_rejection_is_not_a_pass(self):
        self.cases.write_text("case_id\tu32_hex\nsurrogate\t0000d800\n", encoding="utf-8")
        wrong = "case_id\traw_icu_hex\tboost_u32_hex\nsurrogate\tERROR:INVALID_UTF16\tERROR:INVALID_UTF16\n"
        self.reference.write_text(wrong, encoding="utf-8")
        self.candidate.write_text(wrong, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid oracle rejection"):
            compare(self.cases, self.reference, self.candidate, "u32")


if __name__ == "__main__":
    unittest.main()
