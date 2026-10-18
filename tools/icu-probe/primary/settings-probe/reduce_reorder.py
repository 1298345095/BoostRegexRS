#!/usr/bin/env python3
"""Deterministically reduce a retained valid-native/rejected-Rust reorder list.

This diagnoses the failing request; it never changes the acceptance corpus.
Every trial invokes both independent processes and retains complete outputs.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_locales import PRIMARY, REPO, bounded, identity, rows, run_logged, save, sha256

FIELDS = ("case_id", "status", "implementation_error", "before_codes", "after_codes",
          "before_primary", "before_identical", "primary", "secondary", "tertiary", "quaternary", "identical")
ERROR = "DATA_ERROR: unexplained or missing split primary lead"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--failure", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build = json.loads(args.build.read_text())
    failure = json.loads(args.failure.read_text())
    original = next(row for row in failure["failure_examples"] if row["native"]["status"] == "U_ZERO_ERROR"
                    and row["rust"]["implementation_error"] == ERROR)
    for kind in ("candidate", "reference"):
        if sha256(Path(build[kind]["path"])) != build[kind]["sha256"]:
            raise ValueError("Original reduction binary identity changed")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    save(output / "original.json", original)
    environment = os.environ.copy()
    environment.pop("ICU_DATA", None)
    environment["LC_ALL"] = "C"
    summary = {"schema": "boostregexrs.icu77-reorder-reduction.v1", "status": "running",
               "candidate": build["candidate"], "reference": build["reference"],
               "failure_source": identity(args.failure), "reducer": identity(Path(__file__)),
               "command": [sys.executable, *sys.argv], "input_u16": "0061", "setup_codes": "~",
               "predicate": "Native U_ZERO_ERROR and unchanged Rust unexplained/missing split-lead data error", "batches": []}

    def test(candidates):
        directory = output / f"batch-{len(summary['batches']):04d}"
        directory.mkdir()
        inputs = directory / "inputs.tsv"
        with inputs.open("w", encoding="utf-8", newline="") as stream:
            stream.write("case_id\tsetup_codes\trequest_codes\tu16_hex\n")
            for index, codes in enumerate(candidates):
                stream.write(f"trial-{index:04d}\t~\t{','.join(map(str, codes))}\t0061\n")
        data = PRIMARY / "data"
        commands = {
            "native": [build["reference"]["path"], "root", directory / "metadata.json"],
            "candidate": [build["candidate"]["path"], data / "root-icu77.bin", data / "root-icu77-nfd.bin",
                          data / "locales/scripts.bin", data / "locales/settings-0000.bin",
                          data / "locales/settings-0000.bin", "-"]}
        processes = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {kind: pool.submit(run_logged, bounded(command, 30), cwd=REPO,
                                        log=directory / f"{kind}.tsv", env=environment,
                                        input_path=inputs, timeout=40) for kind, command in commands.items()}
            for kind, future in futures.items():
                processes[kind] = future.result()
        native = list(rows(directory / "native.tsv", FIELDS))
        rust = list(rows(directory / "candidate.tsv", FIELDS))
        if len(native) != len(candidates) or len(rust) != len(candidates):
            raise ValueError("Reduction trial output coverage differs")
        retained = []
        for index, (reference, candidate) in enumerate(zip(native, rust)):
            if reference["case_id"] != f"trial-{index:04d}" or candidate["case_id"] != reference["case_id"]:
                raise ValueError("Reduction trial output identity differs")
            retained.append(reference["status"] == "U_ZERO_ERROR" and candidate["implementation_error"] == ERROR)
        summary["batches"].append({"path": directory.name, "input": identity(inputs), "processes": processes,
                                   "candidate_lengths": list(map(len, candidates)), "retained_failure": retained})
        save(output / "summary.json", summary)
        return retained

    current = list(map(int, original["case"]["request_codes"].split(",")))
    if not test([current])[0]:
        raise ValueError("Original failure is not preserved for scalar a and default setup")
    granularity = 2
    while len(current) >= 2:
        chunk = (len(current) + granularity - 1) // granularity
        candidates = [current[:start] + current[start + chunk:] for start in range(0, len(current), chunk)]
        results = test(candidates)
        if any(results):
            current = candidates[results.index(True)]
            granularity = max(2, granularity - 1)
        elif granularity >= len(current):
            break
        else:
            granularity = min(len(current), granularity * 2)
    if any(test([current[:index] + current[index + 1:] for index in range(len(current))])):
        raise ValueError("Final failure is not one-deletion minimal")
    summary.update(status="one_deletion_minimal_counterexample", minimal_codes=current,
                   original_code_count=len(original["case"]["request_codes"].split(",")),
                   minimal_code_count=len(current), original_setup_and_text_reduced=True)
    save(output / "summary.json", summary)
    print(json.dumps({"status": summary["status"], "minimal_codes": current, "batches": len(summary["batches"])}))


if __name__ == "__main__":
    main()
