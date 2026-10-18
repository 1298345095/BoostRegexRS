#!/usr/bin/env python3
"""Compare complete structured regex results; missing/error rows cannot pass."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from protocol import HEADER, NO_EXCEPT, RESOURCE_CODES, RESOURCE_FAILURE_KINDS, read_cases, read_results


def resource_failure(status, value, operation):
    if value.get("preceding_compile", {}).get("compile_status") in RESOURCE_CODES:
        return True
    if status == "reference_failure":
        return value["kind"] in RESOURCE_FAILURE_KINDS
    if status in ("compile_error", "candidate_error", "candidate_resource_error"):
        return value["code"] in RESOURCE_CODES
    # no_except reports the invalid compiled object's real status without
    # throwing; its resource limit must not become an ordinary successful test.
    return status == "ok" and operation == "compile" and value["compile_status"] in RESOURCE_CODES


def missing_compile_outcome(test, status, value):
    # Historical no_except rows can lose a resource compilation behind the
    # invalid-object operation error. Its category alone cannot recover that
    # preceding status, so identical incomplete observations are not evidence.
    return (test[1] != "compile" and int(test[2]) & NO_EXCEPT and status == "operation_error"
            and value["category"] == "invalid_argument" and "preceding_compile" not in value)


def compare(cases, reference, candidate):
    inputs = read_cases(cases)
    expected, ref_values = read_results(reference, inputs)
    actual, rust_values = read_results(candidate, inputs)
    counts = Counter()
    by_operation = {}
    differences = []
    for test, original, rust, ref_value, rust_value in zip(inputs, expected, actual, ref_values, rust_values, strict=True):
        if original[1] == "reference_resource_error" or resource_failure(original[1], ref_value, test[1]):
            # Retain the historical resource label as a non-pass observation;
            # its message-only payload is not modern phase/code evidence.
            status = "reference_resource_error"
        elif (missing_compile_outcome(test, original[1], ref_value)
              or original[1] not in ("ok", "compile_error", "operation_error")):
            status = "reference_error"
        elif rust[1] == "unsupported":
            status = "unsupported"
        elif resource_failure(rust[1], rust_value, test[1]):
            status = "candidate_resource_error"
        elif rust[1] in ("candidate_resource_error", "candidate_process_error", "candidate_error"):
            status = rust[1]
        elif original[1] == rust[1] == "operation_error":
            # ADR-0001 requires error category and position, not identical
            # diagnostic prose. Both original messages remain in raw evidence.
            status = ("operation_error_matched" if all(ref_value.get(key) == rust_value.get(key)
                      for key in ("category", "position", "preceding_compile")) else "difference")
        elif original[1] != rust[1] or ref_value != rust_value:
            status = "difference"
        elif original[1] == "compile_error":
            status = "compile_error_matched"
        else:
            status = "passed"
        counts[status] += 1
        by_operation.setdefault(test[1], Counter())[status] += 1
        if status not in ("passed", "compile_error_matched", "operation_error_matched"):
            differences.append({"case_id": test[0], "classification": status,
                                "input": dict(zip(HEADER, test, strict=True)),
                                "reference_status": original[1], "reference": ref_value,
                                "candidate_status": rust[1], "candidate": rust_value})
    return {"status": "passed_for_recorded_inputs" if not differences else "differences_or_unverified",
            "records": len(inputs), "counts": dict(sorted(counts.items())),
            "by_operation": {key: dict(sorted(value.items())) for key, value in sorted(by_operation.items())},
            "comparison": "Complete result fields including ordered ranges and capture histories",
            "scope": "Byte traits in the classic C locale; full-library acceptance remains separately tracked"}, differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        summary, differences = compare(args.cases, args.reference, args.candidate)
    except (OSError, ValueError, csv.Error) as error:
        summary = {"status": "comparison_error", "error": str(error)}
        differences = []
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (args.output / "differences.jsonl").open("w", encoding="utf-8") as stream:
        for row in differences:
            stream.write(json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n")
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["status"] == "passed_for_recorded_inputs" else 1)


if __name__ == "__main__":
    main()
