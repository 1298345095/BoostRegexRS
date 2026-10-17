#!/usr/bin/env python3
"""Reproduce root IDENTICAL complete-key checks, preserving ADR-0005 evidence."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from compare import compare, rows, sha256
from generate_cases import SEED, contexts, generated, identical_directed, input_boundaries, write_cases
from reference_process import run_reference
from run import PRIMARY, REPO, command_log, run_to_file


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def identity(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def run(cache, output, *, all_scalars=True, count=20000, build=True, candidate=None, system_rust=False):
    cache, output = cache.resolve(), output.resolve()
    if output == cache / "primary":
        raise ValueError("IDENTICAL evidence must not replace the historical PRIMARY directory")
    output.mkdir(parents=True, exist_ok=True)
    build_dir = cache / "build/identical"
    build_dir.mkdir(parents=True, exist_ok=True)
    oracle = build_dir / "oracle"
    candidate = candidate.resolve() if candidate else build_dir / "release/icu77-root-primary"
    native = dict(os.environ)
    native.pop("ICU_DATA", None)
    native["LD_LIBRARY_PATH"] = str(cache / "install/icu/lib")
    rust = dict(os.environ)
    rust.pop("LD_LIBRARY_PATH", None)
    rust["ICU_DATA"] = str(cache / "intentionally-absent-icu-data")
    if build:
        command_log(["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                     "-I", cache / "deps/boost_1_89_0", "-I", cache / "install/icu/include",
                     PRIMARY / "oracle.cpp", "-L", cache / "install/icu/lib",
                     "-Wl,-rpath," + str(cache / "install/icu/lib"), "-licui18n", "-licuuc", "-licudata", "-o", oracle],
                    output / "oracle-build.log")
        if system_rust:
            build_env = dict(os.environ)
            version = subprocess.check_output(["rustc", "--version"], text=True)
            if any(word in version for word in ("nightly", "beta", "dev")):
                raise ValueError("The reference suite requires Rust stable")
        else:
            sys.path.insert(0, str(PRIMARY.parent / "cloud"))
            from rust_toolchain import prepare_rust
            build_env = prepare_rust(cache)
        build_env["CARGO_TARGET_DIR"] = str(build_dir)
        command_log(["cargo", "build", "--locked", "--release", "--manifest-path", PRIMARY / "rust/Cargo.toml"],
                    output / "rust-build.log", build_env)

    started = dt.datetime.now(dt.timezone.utc).isoformat()
    original_empty = {}
    original_dir = output / "original-empty"
    original_dir.mkdir(exist_ok=True)
    # Three explicit original calls preserve actual failures independently of
    # the approved valid-pointer expectation used for empty rows in the suite.
    for kind in ("utf8", "u16", "u32"):
        source = original_dir / f"{kind}-input.tsv"
        source.write_text(f"case_id\t{kind}_hex\noriginal-empty\t\n", encoding="utf-8")
        result_path = original_dir / f"{kind}-reference.tsv"
        original_empty[kind] = run_reference(
            [oracle, "--input-format", kind, "--strength", "identical"], source, result_path, native, REPO)

    context_report = output / "root-contexts.json"
    command_log([sys.executable, "-B", PRIMARY / "export/data_format.py", PRIMARY / "data/root-icu77.bin",
                 "--contexts-output", context_report], output / "contexts-export.log")
    collections = {
        "directed": ("utf8", identical_directed()),
        "generated": ("utf8", generated(count, SEED)),
        "contexts": ("utf8", contexts(context_report)),
        "u32": ("u32", input_boundaries("u32")),
        "u16": ("u16", input_boundaries("u16")),
    }
    if all_scalars:
        collections["all-scalars"] = "utf8", ((f"scalar/{cp:06x}", chr(cp)) for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF)
    summaries = {}
    for label, (kind, values) in collections.items():
        group = output / label
        group.mkdir(exist_ok=True)
        cases = group / "cases.tsv"
        case_count = write_cases(cases, values, kind)
        origins = group / "expectation-origins.tsv"
        with origins.open("w", encoding="utf-8") as stream:
            stream.write("case_id\texpectation_source\n")
            for row in rows(cases, ("case_id", f"{kind}_hex")):
                source = "adr0005_valid_pointer_empty" if not row[f"{kind}_hex"] else "original_boost_call"
                stream.write(f"{row['case_id']}\t{source}\n")
        expected, actual = group / "expected-keys.tsv", group / "candidate-keys.tsv"
        oracle_command = [oracle, "--input-format", kind, "--strength", "identical", "--approved-empty-exception"]
        candidate_command = [candidate, "--input-format", kind, "--strength", "identical",
                             "--data", PRIMARY / "data/root-icu77.bin", "--nfd-data", PRIMARY / "data/root-icu77-nfd.bin"]
        print(f"IDENTICAL {label}: {case_count} inputs", flush=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            reference_future = pool.submit(run_reference, oracle_command + ["--metadata", group / "oracle-metadata.json"], cases, expected, native, REPO)
            candidate_future = pool.submit(run_to_file, candidate_command, cases, actual, rust)
            process = reference_future.result()
            candidate_future.result()
        ordering = None
        if kind == "utf8" and label != "all-scalars" and process["reference_error_free"]:
            ordering = group / "icu-ordering.tsv"
            run_to_file(oracle_command + ["--order-pairs"], cases, ordering, native)
        summary = compare(cases, expected, actual, kind, ordering,
                          strength="identical", approved_empty_exceptions=True)
        summary["reference_process"] = process
        if not process["reference_error_free"]:
            summary["status"] = "differences_or_incomplete"
        metadata = json.loads((group / "oracle-metadata.json").read_text())
        attributes = metadata["attributes"]
        if (attributes["strength"] != 15 or any(attributes[name] != 16 for name in
                ("normalization", "numeric", "case_level", "case_first", "french_secondary")) or
                attributes["alternate"] != 21):
            raise ValueError("Unexpected effective root IDENTICAL settings")
        summary["oracle_metadata"] = metadata
        summary["expectation_origins"] = identity(origins)
        summary["commands"] = {"reference": [str(item) for item in oracle_command],
                               "candidate": [str(item) for item in candidate_command]}
        save(group / "summary.json", summary)
        summaries[label] = summary
        print(f"IDENTICAL {label}: {summary['totals']}", flush=True)
        if summary["status"] != "passed_for_recorded_inputs":
            break
    totals = {key: sum(value["totals"][key] for value in summaries.values()) for key in next(iter(summaries.values()))["totals"]}
    completed = len(summaries) == len(collections) and all(value["status"] == "passed_for_recorded_inputs" for value in summaries.values())
    result = {
        "schema": "boostregexrs.root-identical.v1", "scope": "root IDENTICAL with original normalization-OFF CE iteration and NFD/BOCSU final level",
        "started_utc": started, "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "passed_for_recorded_inputs" if completed else "differences_or_incomplete",
        "coverage_profile": "full_recorded_suite" if all_scalars else "diagnostic_without_scalar_sweep",
        "totals": totals, "original_empty_reference": original_empty,
        "original_empty_reference_error_count": sum(item["reference_error_count"] for item in original_empty.values()),
        "approved_exception_policy": "ADR-0005 valid-pointer empty expectation only; separately counted from original Boost compatibility",
        "generation": {"algorithm": "SplitMix64", "seed": f"0x{SEED:016x}", "generated_count": count, "host_unicode_database_used": False},
        "groups": {label: {"summary": str(Path(label) / "summary.json"), "case_count": value["case_count"], "totals": value["totals"]} for label, value in summaries.items()},
        "groups_not_run": [label for label in collections if label not in summaries],
        "identity": {"python": sys.version, "platform": platform.platform(), "candidate": identity(candidate), "oracle": identity(oracle),
                     "data": [identity(PRIMARY / "data" / name) for name in ("root-icu77.bin", "root-icu77-nfd.bin")],
                     "sources": [identity(path) for path in sorted(PRIMARY.rglob("*")) if path.is_file() and path.suffix in (".rs", ".py", ".cpp", ".toml", ".lock")]},
        "primary_historical_evidence_modified": False,
    }
    save(output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=REPO / "target/research/icu77-cloud")
    parser.add_argument("--output", type=Path, help="evidence directory; defaults to a new dated docs/research/assets/icu77-identical/runs directory")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--system-rust", action="store_true")
    parser.add_argument("--skip-all-scalars", action="store_true")
    parser.add_argument("--count", type=int, default=20000)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")
    output = args.output or (REPO / "docs/research/assets/icu77-identical/runs" /
                             dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%S.%fZ"))
    result = run(args.cache, output, all_scalars=not args.skip_all_scalars,
                 count=args.count, build=not args.skip_build, candidate=args.candidate, system_rust=args.system_rust)
    print(json.dumps({"status": result["status"], "coverage_profile": result["coverage_profile"], "totals": result["totals"]}))
    return int(result["status"] != "passed_for_recorded_inputs")


if __name__ == "__main__":
    raise SystemExit(main())
