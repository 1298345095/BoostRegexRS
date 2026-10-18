"""Regressions for false passes in the independent full-result comparison."""

import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from compare import compare
from protocol import HEADER, OUTPUT_HEADER, result_value


MATCH = {"mark_count": 2, "matches": [
    {"range": [0, 3], "partial": False, "groups": [[0, 3], [2, 3], None],
     "histories": [[[0, 3]], [[0, 1], [1, 2], [2, 3]], []],
     "prefix": [0, 0], "suffix": [3, 4]}]}


class FullComparison(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.cases, self.reference, self.candidate = (root / name for name in ("cases.tsv", "reference.tsv", "candidate.tsv"))
        self.write(self.cases, HEADER, [("one", "search", "0", "524288", "2861292b2862293f", "61616121", "")])

    @staticmethod
    def write(path, header, rows):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)

    def observe(self, expected, actual, reference_status="ok", candidate_status="ok"):
        self.write(self.reference, OUTPUT_HEADER, [("one", reference_status, json.dumps(expected))])
        self.write(self.candidate, OUTPUT_HEADER, [("one", candidate_status, json.dumps(actual))])
        return compare(self.cases, self.reference, self.candidate)

    def test_equal_complete_results_pass(self):
        summary, differences = self.observe(MATCH, MATCH)
        self.assertEqual(summary["counts"], {"passed": 1})
        self.assertEqual(differences, [])

    def test_every_capture_field_and_history_order_affects_the_result(self):
        mutations = [
            lambda match: match["groups"].__setitem__(2, [3, 3]),
            lambda match: match["histories"][1].reverse(),
            lambda match: match["histories"][1].pop(),
            lambda match: match.__setitem__("prefix", [1, 1]),
            lambda match: match.__setitem__("suffix", [3, 3]),
            lambda match: match.__setitem__("range", [1, 3]),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                actual = copy.deepcopy(MATCH)
                mutate(actual["matches"][0])
                summary, _ = self.observe(MATCH, actual)
                self.assertEqual(summary["counts"], {"difference": 1})

    def test_missing_fields_and_wrong_json_types_cannot_pass_even_when_equal(self):
        invalid = [{}, {"mark_count": True, "matches": []}, {"mark_count": 2.0, "matches": []}]
        for field in ("range", "partial", "groups", "histories", "prefix", "suffix"):
            value = copy.deepcopy(MATCH)
            del value["matches"][0][field]
            invalid.append(value)
        value = copy.deepcopy(MATCH)
        value["matches"][0]["groups"][0][0] = False
        invalid.append(value)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.observe(value, value)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            result_value(("one", "ok", '{"mark_count":0,"mark_count":1,"matches":[]}'), "search")

    def test_missing_extra_duplicate_and_reordered_rows_cannot_pass(self):
        self.write(self.reference, OUTPUT_HEADER, [("one", "ok", json.dumps(MATCH))])
        for rows in ([], [("other", "ok", json.dumps(MATCH))],
                     [("one", "ok", json.dumps(MATCH)), ("one", "ok", json.dumps(MATCH))]):
            self.write(self.candidate, OUTPUT_HEADER, rows)
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                compare(self.cases, self.reference, self.candidate)
        second = ["two", "search", "0", "0", "61", "61", ""]
        self.write(self.cases, HEADER, [["one", "search", "0", "0", "61", "61", ""], second])
        rows = [(name, "ok", json.dumps(MATCH)) for name in ("one", "two")]
        self.write(self.reference, OUTPUT_HEADER, rows)
        self.write(self.candidate, OUTPUT_HEADER, list(reversed(rows)))
        with self.assertRaisesRegex(ValueError, "reordered"):
            compare(self.cases, self.reference, self.candidate)

    def test_compile_error_position_is_compared(self):
        summary, _ = self.observe({"code": 8, "position": 4}, {"code": 8, "position": 3},
                                  "compile_error", "compile_error")
        self.assertEqual(summary["counts"], {"difference": 1})

    def test_reference_errors_and_unsupported_operations_never_pass(self):
        error = {"message_hex": "6572726f72"}
        summary, _ = self.observe(error, error, "reference_resource_error", "reference_resource_error")
        self.assertEqual(summary["counts"], {"reference_resource_error": 1})
        summary, _ = self.observe(MATCH, {"reason": "missing"}, candidate_status="unsupported")
        self.assertEqual(summary["counts"], {"unsupported": 1})

    def test_partial_extent_is_separate_from_unmatched_group_zero(self):
        partial = {"mark_count": 0, "matches": [
            {"range": [0, 2], "partial": True, "groups": [None], "histories": [[]],
             "prefix": [0, 0], "suffix": [2, 2]}]}
        summary, _ = self.observe(partial, partial)
        self.assertEqual(summary["counts"], {"passed": 1})
        actual = copy.deepcopy(partial)
        actual["matches"][0]["range"] = [0, 1]
        summary, _ = self.observe(partial, actual)
        self.assertEqual(summary["counts"], {"difference": 1})

    def test_operation_errors_compare_category_and_position_without_message_text(self):
        expected = {"category": "invalid_match_options", "position": None, "message_hex": "426f6f7374"}
        actual = {"category": "invalid_match_options", "position": None, "message_hex": "52757374"}
        summary, _ = self.observe(expected, actual, "operation_error", "operation_error")
        self.assertEqual(summary["counts"], {"operation_error_matched": 1})
        actual["category"] = "invalid_argument"
        summary, _ = self.observe(expected, actual, "operation_error", "operation_error")
        self.assertEqual(summary["counts"], {"difference": 1})


if __name__ == "__main__":
    unittest.main()
