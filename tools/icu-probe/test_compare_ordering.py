"""Checks that gaps or a changed ordering cannot produce a false pass."""

import tempfile
import unittest
from pathlib import Path

from compare_ordering import compare


class OrderingComparisonTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.cases, self.reference, self.candidate = (root / name for name in ("cases.tsv", "reference.tsv", "candidate.tsv"))
        self.cases.write_text("case_id\tutf8_hex\nempty\t\na\t61\n", encoding="utf-8")
        self.reference.write_text("locale\tcase_id\tprimary\tidentical\nroot\tempty\t0\t1,1\nroot\ta\t2a\t1,1,2\n", encoding="utf-8")

    def candidate_rows(self, primary="-1", identical="-1"):
        text = "locale\tstrength\tleft_id\tright_id\tordering\n"
        if primary is not None:
            text += f"root\tprimary\tempty\ta\t{primary}\n"
        if identical is not None:
            text += f"root\tidentical\tempty\ta\t{identical}\n"
        self.candidate.write_text(text, encoding="utf-8")

    def result(self):
        return compare(self.cases, self.reference, self.candidate, ("root",))

    def test_valid_empty_input_and_prefix_keys(self):
        self.candidate_rows()
        result = self.result()
        self.assertEqual(result["totals"], {"passed": 2, "mismatched": 0, "unsupported": 0, "reference_error": 0})
        self.assertIn("not_validated", result["sort_key_byte_compatibility"])

    def test_changed_order_is_a_mismatch(self):
        self.candidate_rows(primary="1")
        self.assertEqual(self.result()["totals"]["mismatched"], 1)

    def test_unsupported_is_not_a_pass(self):
        self.candidate_rows(identical="unsupported")
        self.assertEqual(self.result()["totals"]["unsupported"], 1)

    def test_missing_pair_is_invalid(self):
        self.candidate_rows(identical=None)
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.result()

    def test_reference_failure_is_not_a_pass_or_rust_mismatch(self):
        self.candidate_rows()
        text = self.reference.read_text(encoding="utf-8").replace("empty\t0\t1,1", "empty\t0\tERROR:ACCESS_VIOLATION")
        self.reference.write_text(text, encoding="utf-8")
        result = self.result()
        self.assertEqual(result["totals"], {"passed": 1, "mismatched": 0, "unsupported": 0, "reference_error": 1})
        self.assertNotEqual(result["comparison_sign_status"], "passed_for_this_corpus")

    def test_duplicate_pair_is_invalid(self):
        self.candidate_rows()
        with self.candidate.open("a", encoding="utf-8") as stream:
            stream.write("root\tprimary\tempty\ta\t-1\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.result()


if __name__ == "__main__":
    unittest.main()
