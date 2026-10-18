#!/usr/bin/env python3
"""Bounded public-reordering and intermediate-strength acceptance gates.

The reordering gate calls the Rust public setter through its independent CLI;
the intermediate gate calls the previously verified, frozen main Rust CLI.
Both compare complete raw ICU keys against a separately built native process.
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import itertools
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_locales import (PRIMARY, REPO, bounded, commands, configuration_id, configurations,
                         identity, read_data, rows, run_logged, save, sha256, source_data_identity)
from compare import KEY_COLUMNS, decode
from cases import reordered_cases, write_inputs
from locale_format import read_scripts

INPUT_COLUMNS = ("case_id", "setup_codes", "request_codes", "u16_hex")
STRENGTHS = ("primary", "secondary", "tertiary", "quaternary", "identical")
OUTPUT_COLUMNS = ("case_id", "status", "implementation_error", "before_codes", "after_codes",
                  "before_primary", "before_identical", *STRENGTHS)
STATUSES = {"U_ZERO_ERROR", "U_ILLEGAL_ARGUMENT_ERROR", "U_BUFFER_OVERFLOW_ERROR"}


def hex_key(value):
    if not value or len(value) % 2 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("Malformed continuous hexadecimal key in settings protocol")
    result = bytes.fromhex(value)
    # The fixed contract compares the complete getSortKey return length.
    # ICU77 public colReorder can place a zero inside that returned sequence;
    # Boost v5/icu.hpp do_transform retains it and removes only the final zero.
    # diagnose_boost_reorder.py verifies the actual Boost vectors for every
    # such row found by the complete public-code matrix. Never split at NUL.
    if result[-1] != 0:
        raise ValueError("Settings reference did not return a complete terminated key")
    return result


def metadata(path, expected):
    actual = json.loads(path.read_text())
    if (actual["icu"], actual["unicode"], actual["cldr"]) != ("77.1", "16.0.0", "47.0"):
        raise ValueError("Unexpected native settings reference versions")
    for field in ("attributes", "variable_top", "reorder_codes"):
        if actual[field] != expected[field]:
            raise ValueError(f"Native effective {field} differs from fixed settings export")
    return actual


def compare_setters(inputs, expected, actual):
    totals = Counter(passed=0, mismatched=0, reference_error=0, unsupported=0)
    outcomes, categories, failures = Counter(), Counter(), []
    preserved = after_keys = before_keys = 0
    internal_nul_rows = {}
    internal_nul_strengths = Counter()
    boundaries = Counter({"99": 0, "100": 0, "101": 0})
    streams = (rows(inputs, INPUT_COLUMNS), rows(expected, OUTPUT_COLUMNS), rows(actual, OUTPUT_COLUMNS))
    seen = set()
    for case, native, rust in itertools.zip_longest(*streams):
        if any(item is None for item in (case, native, rust)):
            raise ValueError("Settings input/native/Rust row coverage differs")
        name = case["case_id"]
        if not name or name in seen or native["case_id"] != name or rust["case_id"] != name:
            raise ValueError("Missing, duplicate, or reordered settings output identity")
        seen.add(name)
        categories[name.split("/")[0]] += 1
        if native["status"] not in STATUSES:
            totals["reference_error"] += 1
            failures.append({"case": case, "native": native, "rust": rust})
            continue
        outcomes[native["status"]] += 1
        keys_equal = True
        for strength in (*STRENGTHS, "before_primary", "before_identical"):
            native_key = hex_key(native[strength])
            rust_key = hex_key(rust[strength])
            keys_equal &= native_key == rust_key
            positions = [index for index, byte in enumerate(native_key[:-1]) if byte == 0]
            if positions:
                internal_nul_rows.setdefault(name, []).append({"strength": strength, "offsets": positions,
                                                               "complete_key_bytes": len(native_key)})
                internal_nul_strengths[strength] += 1
            if strength in STRENGTHS:
                after_keys += 1
                if str(len(native_key)) in boundaries:
                    boundaries[str(len(native_key))] += 1
            else:
                before_keys += 1
        if native["status"] != "U_ZERO_ERROR":
            for implementation in (native, rust):
                if any(implementation[before] != implementation[after]
                       for before, after in (("before_codes", "after_codes"),
                                             ("before_primary", "primary"), ("before_identical", "identical"))):
                    keys_equal = False
            if keys_equal:
                preserved += 1
        equal = keys_equal and all(native[field] == rust[field]
                                  for field in ("status", "before_codes", "after_codes"))
        if (rust["status"] == "U_ZERO_ERROR") != (not rust["implementation_error"]):
            equal = False
        totals["passed" if equal else "mismatched"] += 1
        if not equal and len(failures) < 20:
            failures.append({"case": case, "native": native, "rust": rust})
    return {"status": "passed_for_recorded_inputs" if not any(totals[key] for key in ("mismatched", "reference_error", "unsupported"))
            else "differences_or_incomplete", "totals": dict(totals), "case_count": len(seen),
            "native_setter_outcomes": dict(outcomes), "categories": dict(categories),
            "failed_setter_state_preserved": preserved, "after_key_sequences_compared": after_keys,
            "before_state_key_sequences_compared": before_keys, "raw_key_boundary_counts": dict(boundaries),
            "native_internal_nul_observations": {"row_count": len(internal_nul_rows),
                "key_sequence_count": sum(internal_nul_strengths.values()), "by_strength": dict(internal_nul_strengths),
                "cases": internal_nul_rows, "policy": "Compare every byte through the actual returned length; internal zero bytes are retained"},
            "failure_examples": failures,
            "comparison_error_labels": "Exact ICU error names; the Rust adapter preserves its original error cause separately"}


def compare_intermediate(inputs, expected, actual, strength):
    totals = Counter(passed=0, mismatched=0, unsupported=0, reference_error=0)
    boundaries = Counter({"99": 0, "100": 0, "101": 0})
    failures, seen = [], set()
    streams = (rows(inputs, INPUT_COLUMNS), rows(expected, OUTPUT_COLUMNS), rows(actual, KEY_COLUMNS))
    for case, native, rust in itertools.zip_longest(*streams):
        if any(item is None for item in (case, native, rust)):
            raise ValueError("Intermediate input/native/Rust row coverage differs")
        name = case["case_id"]
        if name in seen or native["case_id"] != name or rust["case_id"] != name:
            raise ValueError("Missing, duplicate, or reordered intermediate output")
        seen.add(name)
        if native["status"] != "U_ZERO_ERROR":
            totals["reference_error"] += 1
            continue
        reference = hex_key(native[strength])
        if str(len(reference)) in boundaries:
            boundaries[str(len(reference))] += 1
        kind, value = decode(rust, False)
        if kind == "unsupported":
            totals["unsupported"] += 1
        elif kind != "key" or bytes(value[0]) != reference:
            totals["mismatched"] += 1
            if len(failures) < 20:
                failures.append({"case": case, "native": native[strength], "rust": rust})
        else:
            totals["passed"] += 1
    return {"status": "passed_for_recorded_inputs" if not any(totals[key] for key in ("mismatched", "reference_error", "unsupported"))
            else "differences_or_incomplete", "strength": strength, "totals": dict(totals), "case_count": len(seen),
            "raw_key_boundary_counts": dict(boundaries), "failure_examples": failures,
            "comparison": "Complete raw ICU bytes, including final NUL; no Boost intermediate-strength API claim"}


def invoke(command, inputs, output, environment, timeout_seconds):
    return run_logged(bounded(command, timeout_seconds), cwd=REPO, log=output,
                      env=environment, input_path=inputs, timeout=timeout_seconds + 10)


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = json.loads(args.build.read_text())
    if build["status"] != "passed":
        raise ValueError("Settings probe build did not pass its recorded gates")
    build_fixed = [build["candidate"], build["reference"], *build["rust_runtime_sources"]]
    if any(sha256(Path(item["path"])) != item["sha256"] for item in build_fixed):
        raise ValueError("Settings probe binary or frozen runtime source changed after build")
    reference, candidate = Path(build["reference"]["path"]), Path(build["candidate"]["path"])
    catalog_path = PRIMARY / "data/locales/catalog.json"
    data = catalog_path.parent
    catalog = json.loads(catalog_path.read_text())
    fixed = [identity(args.build), identity(catalog_path), *build_fixed, *source_data_identity(data, catalog)]
    sources = [HERE / name for name in ("run.py", "cases.py", "build.py", "reference.cpp", "src/main.rs", "Cargo.toml", "Cargo.lock")]
    sources += [PRIMARY / name for name in ("run_locales.py", "compare.py", "generate_cases.py",
                                           "export/data_format.py", "export/locale_format.py", "../cloud/prepare.py")]
    source_records = [identity(path.resolve()) for path in sources]
    fixed.extend(source_records)
    for record in source_records:
        source = Path(record["path"])
        target = output / "harness-source" / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    environment = os.environ.copy()
    environment.pop("ICU_DATA", None)
    environment["LC_ALL"] = "C"
    inputs = output / "inputs.tsv"
    if args.mode == "reorder":
        values, coverage = reordered_cases(read_data(PRIMARY / "data/root-icu77.bin"),
                                          read_scripts(data / "scripts.bin"), args.smoke)
        write_inputs(inputs, values)
        if not args.smoke and coverage["ordered_pair_count"] != coverage["expected_complete_ordered_pair_count"]:
            raise ValueError("Public reorder code pair matrix is incomplete")
        profiles = []
        for name in ("root", "am"):
            row = next(row for row in catalog["requests"] if row["requested"] == name and row["status"] == "loaded")
            profiles.append({"locale": name, "owner": row["owner"], "settings": row["settings"]})
        if catalog["settings"][profiles[0]["settings"]]["reorder_codes"] or not catalog["settings"][profiles[1]["settings"]]["reorder_codes"]:
            raise ValueError("DEFAULT state test requires distinct empty/nonempty tailoring defaults")
        if args.profile:
            profiles = [profile for profile in profiles if profile["locale"] in args.profile]
            coverage["scope"] += "_selected_profiles"
        coverage["selected_profiles"] = [profile["locale"] for profile in profiles]
        coverage["complete_default_profile_classes"] = ["root", "am"]
    else:
        if args.configurations_run is None or args.candidate is None or args.candidate_provenance is None:
            raise ValueError("Intermediate gate requires complete configuration provenance and frozen CLI")
        verification = json.loads((args.configurations_run / "verification.json").read_text())
        provenance = json.loads(args.candidate_provenance.read_text())
        profiles = configurations(catalog)
        if verification["status"] != "passed" or verification["configuration_strength_width_groups"] != len(profiles) * 6:
            raise ValueError("Intermediate inputs require the complete passed configuration matrix")
        candidate = args.candidate.resolve()
        if provenance["status"] != "passed_for_recorded_inputs" or sha256(candidate) != provenance["candidate"]["sha256"]:
            raise ValueError("Main CLI does not match the independently passed B candidate")
        original = args.configurations_run / "inputs/common-u16.tsv"
        values = []
        for row in rows(original, ("case_id", "u16_hex")):
            encoded = b"".join(int(unit, 16).to_bytes(2, "little") for unit in row["u16_hex"].split(",") if unit)
            values.append({"case_id": row["case_id"], "setup": None, "requested": None,
                           "text": encoded.decode("utf-16-le")})
        if len(values) != verification["common_inputs_per_width"]:
            raise ValueError("Intermediate input count differs from the verified common corpus")
        write_inputs(inputs, values)
        shutil.copyfile(original, output / "cli-inputs-u16.tsv")
        if args.smoke:
            profiles = profiles[:1]
        coverage = {"schema": "boostregexrs.icu77-intermediate-inputs.v1",
                    "scope": "diagnostic_smoke" if args.smoke else "all_effective_configurations",
                    "source_verification": identity(args.configurations_run / "verification.json"),
                    "original_inputs": identity(original), "case_count": len(values),
                    "configurations": len(profiles), "strengths": list(STRENGTHS[1:4]),
                    "input_width": "u16 (same original common inputs as the passed three-width P/I matrix)",
                    "unicode_normalization_performed": False,
                    "not_covered": ["arbitrary locale resolver", "Boost does not expose intermediate strengths through transform/transform_primary"]}
        fixed += [identity(candidate), identity(args.candidate_provenance), coverage["source_verification"], coverage["original_inputs"]]
    save(output / "generation.json", coverage)
    fixed.append(identity(inputs))
    result = {"schema": "boostregexrs.icu77-settings-acceptance.v1", "status": "running",
              "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "mode": args.mode,
              "scope": coverage["scope"], "command": [sys.executable, *sys.argv], "cwd": str(REPO),
              "process_environment": {"set": {"LC_ALL": "C"}, "unset": ["ICU_DATA"]},
              "process_timeout_seconds": args.process_timeout, "candidate": identity(candidate),
              "reference": identity(reference), "input": identity(inputs), "sources": source_records,
              "fixed_identities": fixed, "groups": [], "not_covered": coverage["not_covered"]}
    save(output / "summary.json", result)
    completed = False
    try:
        for configuration in profiles:
            directory = output / configuration_id(configuration)
            directory.mkdir()
            expected = directory / "native.tsv"
            native_command = [reference, configuration["locale"], directory / "metadata.json"]
            if args.mode == "reorder":
                settings = data / catalog["settings_files"][configuration["settings"]]["path"]
                owner = data / catalog["owner_files"][configuration["owner"]]["file"] if configuration["owner"] else "-"
                rust_command = [candidate, PRIMARY / "data/root-icu77.bin", PRIMARY / "data/root-icu77-nfd.bin",
                                data / "scripts.bin", settings, settings, owner]
                actual = directory / "candidate.tsv"
                with ThreadPoolExecutor(max_workers=2) as pool:
                    native_future = pool.submit(invoke, native_command, inputs, expected, environment, args.process_timeout)
                    rust_future = pool.submit(invoke, rust_command, inputs, actual, environment, args.process_timeout)
                    native_process, rust_process = native_future.result(), rust_future.result()
                report = compare_setters(inputs, expected, actual)
                report["processes"] = {"native": native_process, "rust": rust_process}
            else:
                native_process = invoke(native_command, inputs, expected, environment, args.process_timeout)
                reports = []
                for strength in STRENGTHS[1:4]:
                    _, rust_command = commands(configuration, strength, "u16", reference, candidate, data, catalog)
                    actual = directory / f"{strength}.tsv"
                    rust_process = invoke(rust_command, output / "cli-inputs-u16.tsv", actual, environment, args.process_timeout)
                    compared = compare_intermediate(inputs, expected, actual, strength)
                    compared["process"] = rust_process
                    reports.append(compared)
                report = {"status": "passed_for_recorded_inputs" if all(item["status"] == "passed_for_recorded_inputs" for item in reports)
                          else "differences_or_incomplete", "strengths": reports, "native_process": native_process}
            report["metadata"] = metadata(directory / "metadata.json", catalog["settings"][configuration["settings"]])
            report["configuration"] = configuration
            save(directory / "summary.json", report)
            result["groups"].append({"path": str(directory.relative_to(output)), "configuration": configuration,
                                     "status": report["status"], **({"totals": report["totals"]} if args.mode == "reorder" else {})})
            save(output / "summary.json", result)
            print(json.dumps({"completed_configurations": len(result["groups"]), "expected_configurations": len(profiles),
                              "mode": args.mode, "status": report["status"]}), flush=True)
            if report["status"] != "passed_for_recorded_inputs":
                raise ValueError(f"Settings acceptance differs for {configuration_id(configuration)}; complete rows retained")
        completed = True
    finally:
        result["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        result["identities_unchanged_during_run"] = all(sha256(Path(item["path"])) == item["sha256"] for item in fixed)
        result["status"] = "passed_for_recorded_inputs" if completed and result["identities_unchanged_during_run"] else "differences_or_incomplete"
        save(output / "summary.json", result)
    return 0 if result["status"] == "passed_for_recorded_inputs" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("reorder", "intermediate"), required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--profile", choices=("root", "am"), action="append",
                        help="Run selected reorder profiles; coverage remains explicitly partial")
    parser.add_argument("--process-timeout", type=int, default=180)
    parser.add_argument("--configurations-run", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--candidate-provenance", type=Path)
    args = parser.parse_args()
    if not 1 <= args.process_timeout <= 600:
        parser.error("process timeout must be between 1 and 600 seconds")
    if args.profile and args.mode != "reorder":
        parser.error("--profile is only applicable to the public reorder gate")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
