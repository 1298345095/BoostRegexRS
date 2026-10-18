"""Phase/code regressions for Boost's actual exception hierarchy."""

import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from compare import compare
from protocol import HEADER, OUTPUT_HEADER, result_value


FAILURE = {"schema": "boostregexrs.reference-failure.v1", "phase": "search",
           "kind": "regex_resource", "code": 18, "position": 0, "message_hex": "426f6f7374"}
OPERATION_ERROR = {"category": "invalid_argument", "position": None, "message_hex": "426f6f7374"}
INVALID_COMPILE = {"mark_count": 18446744073709551615, "compile_status": 18}
LATER_OPERATIONS = ("search", "match", "iterate", "format", "replace")


class ReferenceFailures(unittest.TestCase):
    def result(self, value, operation="search"):
        return result_value(("case", "reference_failure", json.dumps(value)), operation)

    def compare_failure(self, value, operation="search", reference_status="reference_failure", *,
                        syntax=0, candidate_value=None, candidate_status="candidate_resource_error"):
        if candidate_value is None:
            candidate_value = {"code": 18, "position": 0}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [("cases.tsv", HEADER, [("case", operation, str(syntax), "0", "61", "61", "")]),
                       ("reference.tsv", OUTPUT_HEADER, [("case", reference_status, json.dumps(value))]),
                       ("candidate.tsv", OUTPUT_HEADER, [("case", candidate_status, json.dumps(candidate_value))])]
            for name, header, rows in sources:
                with (root / name).open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
                    writer.writerow(header)
                    writer.writerows(rows)
            return compare(root / "cases.tsv", root / "reference.tsv", root / "candidate.tsv")

    def test_compile_and_matcher_resources_never_pass_as_expected_rejections(self):
        for operation, phase, position in (("compile", "compile", 400), ("search", "search", 0),
                                           ("format", "search", 0), ("replace", "replace", 0)):
            with self.subTest(operation=operation):
                value = {**FAILURE, "phase": phase, "position": position}
                summary, differences = self.compare_failure(value, operation)
                self.assertEqual(summary["counts"], {"reference_resource_error": 1})
                self.assertEqual(differences[0]["reference"], value)
                self.assertEqual(summary["status"], "differences_or_unverified")

    def test_phase_code_position_and_message_survive_validation(self):
        for code in (12, 15, 18, 19):
            value = {**FAILURE, "code": code}
            with self.subTest(code=code):
                self.assertEqual(self.result(value), value)
        for kind in ("allocation", "capacity", "runtime"):
            value = {**FAILURE, "kind": kind, "code": None, "position": None}
            with self.subTest(kind=kind):
                self.assertEqual(self.result(value), value)
        value = {**FAILURE, "kind": "regex", "code": 21}
        self.assertEqual(self.result(value), value)

    def test_plain_runtime_error_is_not_automatically_resource_exhaustion(self):
        value = {**FAILURE, "kind": "runtime", "code": None, "position": None}
        summary, differences = self.compare_failure(value)
        self.assertEqual(summary["counts"], {"reference_error": 1})
        self.assertEqual(differences[0]["reference"], value)

    def test_incomplete_wrongly_typed_or_misclassified_failure_is_rejected(self):
        invalid = []
        for key in FAILURE:
            value = copy.deepcopy(FAILURE)
            del value[key]
            invalid.append(value)
        invalid.extend([{**FAILURE, "schema": "future"}, {**FAILURE, "phase": "replace"},
                        {**FAILURE, "kind": "unknown"}, {**FAILURE, "code": True},
                        {**FAILURE, "position": None}, {**FAILURE, "code": 8},
                        {**FAILURE, "kind": "regex"}, {**FAILURE, "message_hex": "odd"},
                        {**FAILURE, "kind": "runtime"}, {**FAILURE, "extra": 0}])
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.result(value)

    def test_ordinary_compile_error_cannot_be_hidden_as_reference_failure(self):
        value = {**FAILURE, "phase": "compile", "kind": "regex", "code": 8, "position": 1}
        with self.assertRaisesRegex(ValueError, "compile_error"):
            self.result(value, "compile")

    def test_serialization_resource_failure_remains_an_oracle_failure(self):
        value = {**FAILURE, "phase": "serialize", "kind": "allocation", "code": None, "position": None}
        summary, _ = self.compare_failure(value)
        self.assertEqual(summary["counts"], {"reference_resource_error": 1})

    def test_no_except_resource_status_is_preserved_without_counting_as_pass(self):
        value = {"mark_count": 18446744073709551615, "compile_status": 18}
        summary, differences = self.compare_failure(value, "compile", "ok")
        self.assertEqual(summary["counts"], {"reference_resource_error": 1})
        self.assertEqual(differences[0]["reference"], value)

    def test_historical_resource_code_mislabeled_compile_error_cannot_pass(self):
        value = {"code": 18, "position": 0}
        summary, _ = self.compare_failure(value, "search", "compile_error")
        self.assertEqual(summary["counts"], {"reference_resource_error": 1})

    def test_no_except_resources_survive_every_later_operation_error(self):
        for operation in LATER_OPERATIONS:
            for code in (12, 15, 18, 19):
                value = {**OPERATION_ERROR, "preceding_compile": {**INVALID_COMPILE, "compile_status": code}}
                with self.subTest(operation=operation, code=code):
                    summary, differences = self.compare_failure(
                        value, operation, "operation_error", syntax=262144,
                        candidate_value=value, candidate_status="operation_error")
                    self.assertEqual(summary["counts"], {"reference_resource_error": 1})
                    self.assertEqual(differences[0]["reference"], value)
                    self.assertEqual(differences[0]["candidate"], value)

    def test_ordinary_no_except_outcome_is_compared_with_the_later_error(self):
        value = {**OPERATION_ERROR, "preceding_compile": {**INVALID_COMPILE, "compile_status": 8}}
        for operation in LATER_OPERATIONS:
            with self.subTest(operation=operation):
                actual = {**value, "message_hex": "52757374"}
                summary, _ = self.compare_failure(value, operation, "operation_error", syntax=262144,
                                                  candidate_value=actual, candidate_status="operation_error")
                self.assertEqual(summary["counts"], {"operation_error_matched": 1})
                changed = [{**value, "preceding_compile": {**value["preceding_compile"], "compile_status": 5}},
                           {**value, "preceding_compile": {**value["preceding_compile"], "mark_count": 0}},
                           OPERATION_ERROR]
                for actual in changed:
                    summary, _ = self.compare_failure(value, operation, "operation_error", syntax=262144,
                                                      candidate_value=actual, candidate_status="operation_error")
                    self.assertEqual(summary["counts"], {"difference": 1})

    def test_historical_no_except_invalid_object_error_is_narrowly_unverified(self):
        for operation in LATER_OPERATIONS:
            for syntax, category, expected in ((262144, "invalid_argument", "reference_error"),
                                                (0, "invalid_argument", "operation_error_matched"),
                                                (262144, "invalid_match_options", "operation_error_matched")):
                value = {**OPERATION_ERROR, "category": category}
                with self.subTest(operation=operation, syntax=syntax, category=category):
                    summary, _ = self.compare_failure(value, operation, "operation_error", syntax=syntax,
                                                      candidate_value=value, candidate_status="operation_error")
                    self.assertEqual(summary["counts"], {expected: 1})

    def test_preceding_compile_has_strict_fields_types_and_lifetime(self):
        invalid = [None, {}, {"mark_count": 0}, {"compile_status": 18},
                   {**INVALID_COMPILE, "position": 400}, {**INVALID_COMPILE, "code": 18},
                   {**INVALID_COMPILE, "mark_count": True}, {**INVALID_COMPILE, "mark_count": -1},
                   {**INVALID_COMPILE, "compile_status": True}, {**INVALID_COMPILE, "compile_status": "18"},
                   {**INVALID_COMPILE, "compile_status": 0}]
        for preceding in invalid:
            value = {**OPERATION_ERROR, "preceding_compile": preceding}
            with self.subTest(preceding=preceding), self.assertRaises(ValueError):
                result_value(("case", "operation_error", json.dumps(value)), "search")
        for status, operation, value in (
                ("ok", "compile", {**INVALID_COMPILE, "preceding_compile": INVALID_COMPILE}),
                ("compile_error", "search", {"code": 8, "position": 1, "preceding_compile": INVALID_COMPILE}),
                ("reference_failure", "search", {**FAILURE, "phase": "compile", "preceding_compile": INVALID_COMPILE}),
                ("ok", "search", {"mark_count": 0, "matches": [], "preceding_compile": INVALID_COMPILE})):
            with self.subTest(status=status, operation=operation), self.assertRaises(ValueError):
                result_value(("case", status, json.dumps(value)), operation)

    def test_preceding_compile_is_bound_to_no_except_input_flags(self):
        value = {**OPERATION_ERROR, "preceding_compile": INVALID_COMPILE}
        with self.assertRaisesRegex(ValueError, "requires no_except"):
            self.compare_failure(value, "search", "operation_error", syntax=0,
                                 candidate_value=value, candidate_status="operation_error")


if __name__ == "__main__":
    unittest.main()
