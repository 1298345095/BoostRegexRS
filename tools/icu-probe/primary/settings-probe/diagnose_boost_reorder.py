#!/usr/bin/env python3
"""Trace every recorded internal-NUL key through public Boost locale calls."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_locales import REPO, bounded, identity, rows, run_logged, save, sha256

spec = importlib.util.spec_from_file_location("settings_acceptance_run", HERE / "run.py")
settings_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings_run)
INPUT_COLUMNS, OUTPUT_COLUMNS, STRENGTHS = settings_run.INPUT_COLUMNS, settings_run.OUTPUT_COLUMNS, settings_run.STRENGTHS

NATIVE_COLUMNS = ("case_id", "locale", "load_status", "reorder_codes", "primary", "boost_primary", "identical", "boost_identical")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--root-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = json.loads(args.build.read_text())
    source_run = json.loads((args.root_run / "summary.json").read_text())
    if build["status"] != "passed" or not source_run["identities_unchanged_during_run"]:
        raise ValueError("Expected a checked probe and the unchanged original recorded root run")
    candidate = Path(build["candidate"]["path"])
    for record in (build["candidate"], *build["rust_runtime_sources"]):
        if sha256(Path(record["path"])) != record["sha256"]:
            raise ValueError("Probe candidate or runtime source changed after its checked build")
    group = args.root_run / "owner-0000-settings-0000"
    processes = [json.loads((group / f"{name}.process.json").read_text()) for name in ("native", "candidate")]
    if any(process["exit_status"] != 0 for process in processes):
        raise ValueError("This scope check requires completed original native and Rust processes")
    original_inputs = list(rows(args.root_run / "inputs.tsv", INPUT_COLUMNS))
    original_native = list(rows(group / "native.tsv", OUTPUT_COLUMNS))
    if [row["case_id"] for row in original_inputs] != [row["case_id"] for row in original_native]:
        raise ValueError("Original native row identity coverage differs from inputs")
    selected = []
    expected = {}
    for case, row in zip(original_inputs, original_native, strict=True):
        if any(0 in bytes.fromhex(row[strength])[:-1] for strength in STRENGTHS):
            if row["status"] != "U_ZERO_ERROR":
                raise ValueError("An internal-NUL source row unexpectedly has a failed setter")
            selected.append(case)
            expected[case["case_id"]] = row
    if not selected:
        raise ValueError("No internal-NUL keys in the recorded root run")
    inputs = output / "inputs.tsv"
    with inputs.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=INPUT_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(selected)
    cache = args.cache.resolve()
    prefix = cache / "install/icu"
    boost = cache / "deps/boost_1_89_0"
    directory = cache / "build/boost-reorder-keys" / output.name
    directory.mkdir(parents=True, exist_ok=False)
    binary = directory / "boost-reorder-keys"
    libraries = [prefix / f"lib/libicu{name}.a" for name in ("i18n", "uc", "data")]
    environment = os.environ.copy()
    environment.pop("ICU_DATA", None)
    environment["LC_ALL"] = "C"
    compile_command = ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-DU_STATIC_IMPLEMENTATION",
                       "-I", boost, "-I", prefix / "include", HERE / "boost-reorder-keys.cpp", *libraries,
                       "-lpthread", "-ldl", "-lm", "-o", binary]
    run_logged(bounded(compile_command, 180), cwd=REPO, log=output / "build.log", env=environment, timeout=190)
    primary = HERE.parent
    data = primary / "data"
    rust_command = [candidate, data / "root-icu77.bin", data / "root-icu77-nfd.bin", data / "locales/scripts.bin",
                    data / "locales/settings-0000.bin", data / "locales/settings-0000.bin", "-", "--boost-fields"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        native_future = pool.submit(run_logged, bounded([binary], 60), cwd=REPO, log=output / "native.tsv",
                                    env=environment, input_path=inputs, timeout=70)
        rust_future = pool.submit(run_logged, bounded(rust_command, 60), cwd=REPO, log=output / "candidate.tsv",
                                  env=environment, input_path=inputs, timeout=70)
        native_process, rust_process = native_future.result(), rust_future.result()
    native_rows = list(rows(output / "native.tsv", NATIVE_COLUMNS))
    rust_rows = list(rows(output / "candidate.tsv", (*OUTPUT_COLUMNS, "boost_primary", "boost_identical")))
    names = [case["case_id"] for case in selected]
    if any([row["case_id"] for row in values] != names for values in (native_rows, rust_rows)):
        raise ValueError("Boost scope execution omitted, duplicated or reordered selected rows")
    failures = []
    for native, rust in zip(native_rows, rust_rows, strict=True):
        original = expected[native["case_id"]]
        equal = native["reorder_codes"] == original["after_codes"] == rust["after_codes"]
        equal &= rust["status"] == "U_ZERO_ERROR" and not rust["implementation_error"]
        for strength in ("primary", "identical"):
            equal &= native[strength] == original[strength] == rust[strength]
            equal &= native[f"boost_{strength}"] == rust[f"boost_{strength}"]
        if not equal:
            failures.append({"native": native, "rust": rust, "original": original})
    source_paths = [HERE / name for name in ("diagnose_boost_reorder.py", "boost-reorder-keys.cpp", "src/main.rs")]
    source_paths += [boost / "boost/regex/v5/icu.hpp", cache / "deps/icu/source/i18n/coll.cpp"]
    sources = [identity(path) for path in source_paths]
    for index, path in enumerate(source_paths):
        target = output / "source" / f"{index:02d}-{path.name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    result = {"schema": "boostregexrs.boost189-reorder-key-scope.v1",
              "status": "passed_for_recorded_calls" if not failures else "differences_or_incomplete",
              "source_run": identity(args.root_run / "summary.json"), "source_native": identity(group / "native.tsv"),
              "source_candidate": identity(group / "candidate.tsv"), "build": identity(args.build),
              "candidate": identity(candidate), "binary": identity(binary), "libraries": list(map(identity, libraries)),
              "sources": sources, "input": identity(inputs), "command": [sys.executable, *sys.argv],
              "process_environment": {"set": {"LC_ALL": "C"}, "unset": ["ICU_DATA"]},
              "processes": {"native": native_process, "rust": rust_process},
              "selected_internal_nul_rows": len(selected), "completed_raw_keys_compared": len(selected) * 2,
              "completed_boost_vectors_compared": len(selected) * 2, "differences": len(failures),
              "failure_examples": failures, "unicode_normalization_performed": False,
              "normal_destruction_completed": native_process["exit_status"] == 0,
              "scope": "All recorded internal-NUL root setter cases through public named Boost colReorder locales; pure Rust receives explicit reorder codes",
              "not_claimed": ["Arbitrary locale parser acceptance", "Direct ICU DEFAULT cleanup succeeded"]}
    save(output / "summary.json", result)
    print(json.dumps({key: result[key] for key in ("status", "selected_internal_nul_rows", "completed_raw_keys_compared", "completed_boost_vectors_compared", "differences")}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
