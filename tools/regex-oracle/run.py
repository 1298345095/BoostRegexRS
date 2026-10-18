#!/usr/bin/env python3
"""Run every byte-regex case and preserve crashes, timeouts and raw process logs.

Failed batches are bisected to identify individual failures, with every original
batch retained. A failing case receives an explicit process-error row; it is
never omitted or converted to an ordinary no-match result.
"""

import argparse
from collections import Counter
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from protocol import HEADER, OUTPUT_HEADER, read_cases, read_results


ROOT = Path(__file__).resolve().parents[2]


def positive_timeout(value):
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("Timeout must be finite and positive")
    return timeout


def identity(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest}


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_rows(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def run_process(command, directory, timeout, input_path=None):
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    start = time.monotonic()
    timed_out = False
    error = None
    returncode = None
    with (directory / "stdout.tsv").open("wb") as output, (directory / "stderr.txt").open("wb") as errors:
        source = input_path.open("rb") if input_path else subprocess.DEVNULL
        try:
            result = subprocess.run(command, stdin=source, stdout=output, stderr=errors,
                                    timeout=timeout, check=False, shell=False)
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
        except OSError as exception:
            error = str(exception)
        finally:
            if input_path:
                source.close()
    record = {"command": command, "started_utc": started, "elapsed_seconds": time.monotonic() - start,
              "timeout_seconds": timeout, "timed_out": timed_out, "returncode": returncode,
              "launch_error": error}
    save_json(directory / "process.json", record)
    return record


class BatchRunner:
    def __init__(self, program, role, output, timeout):
        self.program = str(program)
        self.role = role
        self.output = output
        self.timeout = timeout
        self.processes = []

    def run(self, cases):
        index = len(self.processes)
        directory = self.output / "processes" / f"batch-{index:06d}"
        directory.mkdir(parents=True)
        input_path = directory / "input.tsv"
        write_rows(input_path, HEADER, cases)
        process = run_process([self.program], directory, self.timeout, input_path)
        process["directory"] = directory.relative_to(self.output).as_posix()
        process["records"] = len(cases)
        self.processes.append(process)
        if process["returncode"] == 0:
            try:
                rows, _ = read_results(directory / "stdout.tsv", cases)
                process["protocol_valid"] = True
                save_json(directory / "process.json", process)
                return rows
            except (OSError, ValueError, csv.Error) as error:
                process["protocol_error"] = str(error)
        process["protocol_valid"] = False
        save_json(directory / "process.json", process)
        if len(cases) > 1:
            middle = len(cases) // 2
            return self.run(cases[:middle]) + self.run(cases[middle:])
        value = {"exit_code": process["returncode"], "timeout": process["timed_out"],
                 "evidence": process["directory"]}
        return [(cases[0][0], self.role + "_process_error", json.dumps(value, separators=(",", ":")))]


def run(program, role, cases_path, output, batch_size, timeout, sources=()):
    timeout = positive_timeout(timeout)
    program = program.resolve(strict=True)
    cases = read_cases(cases_path)
    # Reproduction is a new observation; an existing historical run is immutable.
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(cases_path, output / "cases.tsv")
    metadata_directory = output / "metadata"
    metadata_directory.mkdir()
    metadata = run_process([str(program), "--metadata"], metadata_directory, timeout)
    runner = BatchRunner(program, role, output, timeout)
    results = []
    for start in range(0, len(cases), batch_size):
        results.extend(runner.run(cases[start:start + batch_size]))
        print(f"{role}: preserved {len(results)}/{len(cases)} records", flush=True)
    results_path = output / "results.tsv"
    write_rows(results_path, OUTPUT_HEADER, results)
    verified, _ = read_results(results_path, cases)
    counts = Counter(row[1] for row in verified)
    has_errors = (metadata["returncode"] != 0 or
                  any(status not in ("ok", "compile_error", "operation_error") for status in counts))
    script_paths = sorted(Path(__file__).parent.glob("*.py"))
    summary = {
        "schema": "boostregexrs.byte-regex-process-evidence.v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "role": role, "records": len(cases), "result_counts": dict(sorted(counts.items())),
        "status": "complete_with_errors" if has_errors else "complete_protocol_results",
        "meaning": "Process/protocol collection only; compatibility requires independent comparison",
        "program": identity(program), "cases": identity(cases_path), "results": identity(results_path),
        "environment": {"platform": platform.platform(), "uname": list(platform.uname()),
                        "libc": list(platform.libc_ver()), "python": sys.version,
                        "locale_environment": {key: os.environ.get(key) for key in ("LANG", "LC_ALL", "LC_CTYPE")}},
        "metadata_process": metadata,
        "source_files": [identity(path) for path in [*sources, *script_paths]],
        "process_count": len(runner.processes),
        "failed_batches_retained": sum(not process["protocol_valid"] for process in runner.processes),
        "batch_size": batch_size, "timeout_seconds": timeout,
        "timeouts_are_per_process_diagnostics_not_performance_results": True,
    }
    save_json(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--role", choices=("reference", "candidate"), required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--timeout", type=positive_timeout, default=30)
    parser.add_argument("--source", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("Batch size must be positive")
    summary = run(args.program, args.role, args.cases, args.output, args.batch_size, args.timeout, args.source)
    print(json.dumps({key: summary[key] for key in ("status", "records", "result_counts", "process_count")}, indent=2))
    return int(summary["status"] != "complete_protocol_results")


if __name__ == "__main__":
    raise SystemExit(main())
