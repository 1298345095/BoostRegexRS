#!/usr/bin/env python3
"""Build and validate the pure Rust root PRIMARY prototype against fixed ICU77."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from compare import compare, sha256
from generate_cases import SEED, contexts, directed, generated, input_boundaries, write_cases
from reference_process import run_reference


REPO = Path(__file__).resolve().parents[3]
PRIMARY = Path(__file__).resolve().parent


def run_to_file(command, source, output, env):
    with source.open("rb") as stdin, output.open("wb") as stdout, output.with_suffix(".stderr.log").open("wb") as stderr:
        result = subprocess.run([str(arg) for arg in command], stdin=stdin, stdout=stdout, stderr=stderr, env=env, cwd=REPO)
    if result.returncode:
        raise RuntimeError(f"Process failed ({result.returncode}): {command[0]}; see {output.with_suffix('.stderr.log')}")


def command_log(command, path, env=None):
    with path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps([str(arg) for arg in command]) + "\n")
        stream.flush()
        result = subprocess.run([str(arg) for arg in command], stdout=stream, stderr=subprocess.STDOUT, env=env, cwd=REPO)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); see {path}")


def run(cache, output, *, all_scalars=True, count=20000, seed=SEED, build=True, rust_env=None):
    cache, output = cache.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    build_dir = cache / "build/primary"
    build_dir.mkdir(parents=True, exist_ok=True)
    native_env = dict(os.environ)
    native_env.pop("ICU_DATA", None)
    native_env["LD_LIBRARY_PATH"] = str(cache / "install/icu/lib")
    candidate_env = dict(os.environ)
    for name in ("LD_LIBRARY_PATH", "ICU_DATA", "ICU_DATA_FILTER_FILE"):
        candidate_env.pop(name, None)
    candidate_env["ICU_DATA"] = str(cache / "intentionally-absent-icu-data")
    build_env = dict(rust_env or os.environ)
    build_env["CARGO_TARGET_DIR"] = str(build_dir)
    oracle = build_dir / "oracle"
    candidate = build_dir / "release/icu77-root-primary"
    data = PRIMARY / "data/root-icu77.bin"
    if build:
        command_log(["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                     "-I", cache / "deps/boost_1_89_0", "-I", cache / "install/icu/include",
                     PRIMARY / "oracle.cpp", "-L", cache / "install/icu/lib",
                     "-Wl,-rpath," + str(cache / "install/icu/lib"), "-licui18n", "-licuuc", "-licudata", "-o", oracle],
                    output / "oracle-build.log")
        command_log(["cargo", "build", "--locked", "--release", "--manifest-path", PRIMARY / "rust/Cargo.toml"], output / "rust-build.log", build_env)
    cases_dir = output / "cases"
    cases_dir.mkdir(exist_ok=True)
    context_report = cache / "build/root-contexts.json"
    # Re-read the binary rather than trusting a stale diagnostic JSON file.
    command_log([sys.executable, "-B", PRIMARY / "export/data_format.py", data, "--contexts-output", context_report], output / "contexts-export.log")
    collections = {"directed": ("utf8", directed()), "generated": ("utf8", generated(count, seed)), "contexts": ("utf8", contexts(context_report))}
    for kind in ("u32", "u16"):
        collections[kind] = kind, input_boundaries(kind)
    if all_scalars:
        collections["all-scalars"] = "utf8", ((f"scalar/{cp:06x}", chr(cp)) for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF)
    generation = {"algorithm": "SplitMix64", "seed": f"0x{seed:016x}", "host_unicode_database_used": False, "counts": {}}
    summaries = {}
    for label, (kind, values) in collections.items():
        cases = cases_dir / f"{label}.tsv"
        generation["counts"][label] = write_cases(cases, values, kind)
        group = output / label
        group.mkdir(exist_ok=True)
        reference, actual = group / "reference.tsv", group / "candidate.tsv"
        oracle_command = [oracle, "--input-format", kind]
        rust_command = [candidate, "--data", data, "--input-format", kind]
        print(f"{label}: comparing {generation['counts'][label]} complete keys", flush=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            reference_future = pool.submit(run_reference, oracle_command, cases, reference, native_env, REPO)
            candidate_future = pool.submit(run_to_file, rust_command, cases, actual, candidate_env)
            reference_process = reference_future.result()
            candidate_future.result()
        ordering = None
        if kind == "utf8" and label != "all-scalars" and reference_process["reference_error_free"]:
            ordering = group / "icu-ordering.tsv"
            run_to_file(oracle_command + ["--order-pairs"], cases, ordering, native_env)
        summary = compare(cases, reference, actual, kind, ordering)
        summary["reference_process"] = reference_process
        if not reference_process["reference_error_free"]:
            summary["status"] = "differences_or_incomplete"
            summary["ordering_unavailable_reason"] = "native reference errors preserved; adjacent compare not run across failing inputs"
            summary["unresolved_reference_signal_ranges"] = reference_process["unresolved_signal_ranges"]
        (group / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        summaries[label] = summary
        print(f"{label}: {summary['totals']}", flush=True)
    totals = {name: sum(item["totals"][name] for item in summaries.values()) for name in next(iter(summaries.values()))["totals"]}
    result = {
        "scope": "ICU77 root PRIMARY full-key prototype only",
        "status": "passed_for_recorded_inputs" if all(item["status"] == "passed_for_recorded_inputs" for item in summaries.values()) else "differences_or_incomplete",
        "totals": totals, "generation": generation,
        "groups": {label: {"summary": str(Path(label) / "summary.json"), "case_count": value["case_count"], "totals": value["totals"]} for label, value in summaries.items()},
        "out_of_scope": ["IDENTICAL writer and 145 historical differences", "non-root locale tailoring/FCD settings", "complete regex engine", "six-platform release acceptance", "engine performance/memory acceptance", "librime-rs integration"],
        "rust_runtime_environment": {"LD_LIBRARY_PATH": "unset", "ICU_DATA": "intentionally absent directory", "reference_program_invoked_by_candidate": False},
        "identity": {"python": sys.version, "platform": platform.platform(), "data_sha256": sha256(data), "oracle_sha256": sha256(oracle), "candidate_sha256": sha256(candidate),
                     "source_sha256": {str(path.relative_to(REPO)): sha256(path) for path in sorted(PRIMARY.rglob('*')) if path.is_file() and path.suffix in (".rs", ".py", ".cpp", ".toml", ".lock")}},
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "cases/generation.json").write_text(json.dumps(generation, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=REPO / "target/research/icu77-cloud")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-build", action="store_true", help="reuse binaries for diagnosis; build identity is still recorded")
    parser.add_argument("--skip-all-scalars", action="store_true")
    parser.add_argument("--count", type=int, default=20000)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")
    result = run(args.cache, args.output or args.cache / "primary", all_scalars=not args.skip_all_scalars, count=args.count, build=not args.skip_build)
    print(json.dumps(result["totals"]))
    return int(result["status"] != "passed_for_recorded_inputs")


if __name__ == "__main__":
    raise SystemExit(main())
