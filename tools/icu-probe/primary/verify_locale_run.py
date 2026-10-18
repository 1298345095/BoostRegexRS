#!/usr/bin/env python3
"""Check a locale run's declared coverage, width preservation and process records.

This verifier reads the saved evidence only. It does not generate oracle keys,
run the candidate, or widen a diagnostic run into full ticket acceptance.
"""

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sys


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def input_rows(path, kind):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != ["case_id", f"{kind}_hex"]:
            raise ValueError(f"Invalid input header: {path}")
        for row in reader:
            value = row[f"{kind}_hex"]
            if kind == "utf8":
                text = bytes.fromhex(value).decode("utf-8")
            elif kind == "u16":
                units = [] if not value else [int(item, 16) for item in value.split(",")]
                text = b"".join(unit.to_bytes(2, "little") for unit in units).decode("utf-16-le")
            else:
                text = "" if not value else "".join(chr(int(item, 16)) for item in value.split(","))
            yield row["case_id"], text


def verify(run):
    csv.field_size_limit(sys.maxsize)
    report = read_json(run / "summary.json")
    if report["schema"] != "boostregexrs.icu77-locales-fullkeys.v2":
        raise ValueError("Expected the version-2 complete-width run format")
    if report["status"] != "passed_for_recorded_inputs" or not report["identities_unchanged_during_run"]:
        raise ValueError("Run is not complete and passing for its explicitly selected inputs")
    generation = read_json(run / "inputs/generation.json")
    originals = list(input_rows(run / "inputs/common-utf8.tsv", "utf8"))
    for kind in ("u16", "u32"):
        converted = list(input_rows(run / f"inputs/common-{kind}.tsv", kind))
        if converted != originals:
            raise ValueError(f"Common {kind} inputs changed text or row order")
    if len(originals) != generation["common_inputs_per_width"]:
        raise ValueError("Width coverage count differs from the actual corpus")
    for item in generation["inputs"].values():
        if digest(run / "inputs" / Path(item["path"]).name) != item["sha256"]:
            raise ValueError("Input identity differs from generation manifest")
    for source in report["identity"]["sources"]:
        if digest(run / "generator-snapshot" / Path(source["path"]).name) != source["sha256"]:
            raise ValueError("Frozen harness snapshot differs from recorded source identity")

    configurations = read_json(run / "configurations.json")
    selected = configurations[:report["selected_configuration_count"]]
    expected = {(f"owner-{row['owner']:04d}-settings-{row['settings']:04d}", strength, kind)
                for row in selected for strength in ("primary", "identical") for kind in ("utf8", "u16", "u32")}
    actual, owners, process_count = set(), set(), 0
    boundary_counts = {str(length): 0 for length in (99, 100, 101)}
    for group in report["groups"]:
        path = run / group["path"]
        summary = read_json(path / "summary.json")
        if summary["status"] != "passed_for_recorded_inputs":
            raise ValueError(f"Non-passing group: {path}")
        if sum(summary["totals"].values()) != summary["case_count"]:
            raise ValueError(f"Unclassified or multiply classified inputs: {path}")
        if digest(run / group["input"]) != summary["input"]["sha256"]:
            raise ValueError(f"Group input hash differs from recorded identity: {path}")
        candidate = read_json(path / "candidate-keys.process.json")
        reference = read_json(path / "expected-keys.reference-process.json")
        if candidate != summary["candidate_process"] or reference != summary["reference_process"]:
            raise ValueError(f"Group process records differ from the saved summary: {path}")
        if candidate["exit_status"] != 0 or candidate["returncode"] != 0 or candidate["timed_out"]:
            raise ValueError(f"Candidate process was incomplete: {path}")
        if not reference["reference_error_free"] or any(attempt["returncode"] != 0 for attempt in reference["attempts"]):
            raise ValueError(f"In-scope native reference process was incomplete: {path}")
        for process in (candidate, reference):
            if process["command"][:3] != ["timeout", "--signal=TERM", "--kill-after=5s"]:
                raise ValueError(f"A compared process did not have its declared GNU deadline: {path}")
        process_count += 2
        for length, count in summary["raw_key_length"]["boost_buffer_boundary_counts"].items():
            boundary_counts[length] += count
        key = (group["configuration"], group["strength"], group["input_format"])
        if summary["phase"] == "owner-data":
            owner_key = (group["owner"], group["strength"])
            if owner_key in owners:
                raise ValueError("Duplicate owner/strength group")
            owners.add(owner_key)
        else:
            if key in actual:
                raise ValueError("Duplicate configuration/strength/width group")
            actual.add(key)
    if actual != expected or owners != set(itertools.product(report["selected_owners"], ("primary", "identical"))):
        raise ValueError("Executed groups differ from the declared phase/selection")
    for owner in report["selected_owners"]:
        coverage = read_json(run / "inputs" / f"owner-{owner:04d}-utf8.coverage.json")
        if coverage["uncovered_context_entries"]:
            raise ValueError(f"Owner {owner} has uncovered exported context entries")
        if any(row["covered_entries"] != list(range(row["expected_entries"])) for row in coverage["contexts"]):
            raise ValueError(f"Owner {owner} context entry inventory is incomplete")
    return {
        "schema": "boostregexrs.icu77-locale-run-verification.v1", "status": "passed",
        "run": str(run), "run_summary_sha256": digest(run / "summary.json"),
        "verifier_sha256": digest(Path(__file__)), "coverage_profile": report["coverage_profile"],
        "selected_phase": report["selected_phase"], "common_inputs_per_width": len(originals),
        "configuration_strength_width_groups": len(actual), "owner_strength_groups": len(owners),
        "compared_process_records": process_count, "raw_key_boundary_counts": boundary_counts,
        "original_empty_reference_error_count": report["original_empty_reference_error_count"],
        "not_covered": report["not_covered"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    result = verify(run)
    output = run / "verification.json"
    if output.exists():
        raise ValueError("Verification output already exists; preserve the prior evidence")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
