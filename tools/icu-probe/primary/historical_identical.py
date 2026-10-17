#!/usr/bin/env python3
"""Relate new root IDENTICAL keys to the preserved 13-input non-FCD experiment.

This reads recorded outputs only. It does not rerun either implementation or
add the derived key/pair counts to the new run's accepted input count.
"""

import argparse
import csv
import itertools
import json
from pathlib import Path

from compare import KEY_COLUMNS, decode, key, rows, sha256


REPO = Path(__file__).resolve().parents[3]
HISTORICAL = REPO / "docs/research/assets/icu-probe/non-fcd"


def sign(left, right):
    return (left > right) - (left < right)


def relate(run, output):
    original_keys = HISTORICAL / "reference-sortkeys.tsv"
    original_ordering = HISTORICAL / "candidate-ordering.tsv"
    keys = {(row["locale"], row["case_id"]): key(row["identical"], 8)
            for row in rows(original_keys, ("locale", "case_id", "primary", "identical"))}
    old_pairs = [row for row in rows(original_ordering, ("locale", "strength", "left_id", "right_id", "ordering"))
                 if row["strength"] == "identical"]
    old_differences = [row for row in old_pairs if int(row["ordering"]) != sign(
        keys[row["locale"], row["left_id"]], keys[row["locale"], row["right_id"]])]
    expected = {case_id: value for (locale, case_id), value in keys.items() if locale == "root"}
    candidate_path = run / "directed/candidate-keys.tsv"
    candidate = {row["case_id"].removeprefix("nonfcd13/"): decode(row, False)
                 for row in rows(candidate_path, KEY_COLUMNS) if row["case_id"].startswith("nonfcd13/")}
    if len(expected) != 13 or set(candidate) != set(expected):
        raise ValueError("The historical and new root non-FCD inputs must both cover all 13 IDs")
    output.mkdir(parents=True, exist_ok=True)
    failures = []
    with (output / "keys.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["case_id", "historical_boost_u32_hex", "current_raw_icu_hex", "current_boost_u32_hex", "status"])
        for case_id, historical in expected.items():
            kind, actual = candidate[case_id]
            if kind != "key":
                raise ValueError("The current non-FCD output must contain a complete key")
            passed = actual == (historical + (0,), historical)
            if not passed:
                failures.append(case_id)
            writer.writerow([case_id, ",".join(f"{value:08x}" for value in historical),
                             ",".join(f"{value:02x}" for value in actual[0]),
                             ",".join(f"{value:08x}" for value in actual[1]), "passed" if passed else "mismatched"])
    root_pairs = [row for row in old_pairs if row["locale"] == "root"]
    expected_pairs = set(itertools.combinations(expected, 2))
    if {(row["left_id"], row["right_id"]) for row in root_pairs} != expected_pairs:
        raise ValueError("The original root pair coverage is not all 78 unordered input pairs")
    pair_failures = 0
    fixed = 0
    with (output / "pairs.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["left_id", "right_id", "historical_reference", "historical_icu4x", "current_rust", "previous_difference", "status"])
        for row in root_pairs:
            left, right = row["left_id"], row["right_id"]
            reference = sign(expected[left], expected[right])
            current = sign(candidate[left][1][1], candidate[right][1][1])
            previous_difference = int(row["ordering"]) != reference
            fixed += previous_difference and current == reference
            pair_failures += current != reference
            writer.writerow([left, right, reference, row["ordering"], current,
                             str(previous_difference).lower(), "passed" if current == reference else "mismatched"])
    summary = {
        "schema": "boostregexrs.historical-root-identical.v1",
        "scope": "Derived comparison of preserved non-FCD evidence with one recorded new root run",
        "status": "passed_for_recorded_inputs" if not failures and not pair_failures else "differences_or_incomplete",
        "historical_all_locale_identical_differences": len(old_differences),
        "historical_root_identical_differences": sum(row["locale"] == "root" for row in old_differences),
        "root_full_keys": {"total": len(expected), "passed": len(expected) - len(failures), "differences": failures},
        "root_ordering_pairs": {"total": len(root_pairs), "passed": len(root_pairs) - pair_failures,
                                "mismatched": pair_failures, "previous_differences_now_agree": fixed},
        "other_locale_difference_records_not_addressed_by_this_root_run": sum(row["locale"] != "root" for row in old_differences),
        "included_in_new_run_input_totals": False,
        "historical_files_modified": False,
        "sources": [{"path": str(path.resolve()), "sha256": sha256(path)} for path in
                    (original_keys, original_ordering, candidate_path, run / "summary.json", Path(__file__))],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = relate(args.run_directory, args.output)
    print(json.dumps(summary))
    return int(summary["status"] != "passed_for_recorded_inputs")


if __name__ == "__main__":
    raise SystemExit(main())
