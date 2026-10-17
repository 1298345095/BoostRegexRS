#!/usr/bin/env python3
"""Diagnostic CE64 differential for a finite valid-UTF-8 corpus, including sentinel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[4]
CE = re.compile(r"[0-9a-f]{16}")


def file_record(path: Path) -> dict:
    source = path.read_bytes()
    return {"path": str(path), "bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()}


def main() -> int:
    # Long-key diagnostics deliberately exceed Python csv's default 128 KiB
    # field limit; this parser does not impose a smaller collation-input scope.
    csv.field_size_limit(2**31 - 1)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=ROOT / "target/research/icu77-cloud")
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    cache = args.cache.resolve()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    reference = cache / "build/primary-export/trace-root"
    candidate = args.candidate.resolve()
    expected = []
    with args.cases.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if reader.fieldnames != ["case_id", "utf8_hex"]:
            raise ValueError("expected case_id<TAB>utf8_hex input header")
        seen = set()
        with (output / "inputs-u16.tsv").open("w", encoding="utf-8", newline="") as target:
            writer = csv.writer(target, delimiter="\t", lineterminator="\n")
            writer.writerow(["case_id", "u16_hex"])
            for row in reader:
                case_id = row["case_id"]
                if not case_id or case_id in seen or None in row or row["utf8_hex"] is None:
                    raise ValueError("missing, duplicate, or malformed input row")
                seen.add(case_id)
                expected.append(case_id)
                units = bytes.fromhex(row["utf8_hex"]).decode("utf-8").encode("utf-16-le")
                value = ",".join(f"{int.from_bytes(units[i:i + 2], 'little'):04x}"
                                 for i in range(0, len(units), 2))
                writer.writerow([case_id, value])

    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(cache / "install/icu/lib")
    environment.pop("ICU_DATA", None)
    with (output / "inputs-u16.tsv").open("rb") as source, \
         (output / "reference-ces.tsv").open("wb") as target, \
         (output / "reference-stderr.log").open("wb") as errors:
        subprocess.run([str(reference), "--batch-utf16"], stdin=source, stdout=target,
                       stderr=errors, env=environment, check=True)
    environment.pop("LD_LIBRARY_PATH", None)
    with (output / "inputs-u16.tsv").open("rb") as source, \
         (output / "candidate-keys.tsv").open("wb") as target, \
         (output / "candidate-traces.jsonl").open("wb") as traces:
        subprocess.run([str(candidate), "--input-format", "u16", "--trace"], stdin=source,
                       stdout=target, stderr=traces, env=environment, check=True)

    reference_rows = {}
    with (output / "reference-ces.tsv").open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if reader.fieldnames != ["case_id", "ces64_hex"]:
            raise ValueError("invalid reference CE64 header")
        for row in reader:
            key = row["case_id"]
            if key in reference_rows:
                raise ValueError("duplicate reference CE64 row")
            values = row["ces64_hex"].split(",")
            if not values or any(CE.fullmatch(value) is None for value in values):
                raise ValueError("malformed reference CE64 value")
            reference_rows[key] = values
    candidate_rows = {}
    with (output / "candidate-traces.jsonl").open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            key = row["case_id"]
            if key in candidate_rows:
                raise ValueError("duplicate candidate CE64 trace")
            candidate_rows[key] = row
    if set(reference_rows) != set(expected) or set(candidate_rows) != set(expected):
        raise ValueError("missing or unexpected reference/candidate CE64 records")

    passed = 0
    differences = []
    unsupported = []
    for key in expected:
        row = candidate_rows[key]
        if "error" in row:
            unsupported.append({"case_id": key, "error": row["error"]})
            continue
        values = row["ces"]
        if not values or any(not isinstance(value, str) or CE.fullmatch(value) is None for value in values):
            raise ValueError("malformed candidate CE64 value")
        if values != reference_rows[key]:
            differences.append({"case_id": key, "reference": reference_rows[key], "candidate": values})
        else:
            passed += 1
    summary = {
        "schema": "boostregexrs.icu77-primary-ce-audit.v1",
        "scope": "finite root CE64 diagnostic, including end sentinel; not IDENTICAL acceptance",
        "input": file_record(args.cases.resolve()),
        "reference_executable": file_record(reference),
        "candidate_executable": file_record(candidate),
        "data": file_record(ROOT / "tools/icu-probe/primary/data/root-icu77.bin"),
        "counts": {"total": len(expected), "passed": passed, "differences": len(differences),
                   "unsupported": len(unsupported), "reference_error": 0},
        "differences": differences,
        "unsupported": unsupported,
        "evidence": [file_record(output / name) for name in
                     ("inputs-u16.tsv", "reference-ces.tsv", "candidate-keys.tsv", "candidate-traces.jsonl")],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["counts"]))
    return int(bool(differences or unsupported))


if __name__ == "__main__":
    raise SystemExit(main())
