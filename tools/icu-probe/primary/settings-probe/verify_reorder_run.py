#!/usr/bin/env python3
"""Reclassify complete recorded root setter outputs with the fixed key contract.

This never executes a candidate/reference or rewrites the original run. The
separate public Boost proof anchors all observed internal-NUL return vectors.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_locales import REPO, identity, rows, save, sha256

spec = importlib.util.spec_from_file_location("settings_acceptance_run", HERE / "run.py")
settings_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings_run)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--boost-scope", type=Path, required=True)
    parser.add_argument("--driver-observation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    original_path = args.run / "summary.json"
    original = json.loads(original_path.read_text())
    generation = json.loads((args.run / "generation.json").read_text())
    proof = json.loads((args.boost_scope / "summary.json").read_text())
    if original["mode"] != "reorder" or not original["identities_unchanged_during_run"]:
        raise ValueError("Expected an unchanged recorded setter run")
    if generation["selected_profiles"] != ["root"]:
        raise ValueError("This evidence verifier is scoped to the complete root setter matrix")
    if proof["status"] != "passed_for_recorded_calls" or proof["source_run"]["sha256"] != sha256(original_path):
        raise ValueError("Public Boost proof is not a passed check of this exact original run")
    if not proof["normal_destruction_completed"] or proof["differences"]:
        raise ValueError("Public Boost scope run did not complete normally without differences")
    preserved_sources = []
    for record in original["sources"]:
        snapshot = args.run / "harness-source" / Path(record["path"]).relative_to(REPO)
        if sha256(snapshot) != record["sha256"]:
            raise ValueError("Original harness snapshot differs from its recorded pre-run identity")
        preserved_sources.append(identity(snapshot))
    fixed = [identity(original_path), identity(args.run / "inputs.tsv"), identity(args.run / "generation.json"),
             identity(args.driver_observation), identity(args.boost_scope / "summary.json"),
             identity(args.boost_scope / "inputs.tsv"), identity(args.boost_scope / "native.tsv"),
             identity(args.boost_scope / "candidate.tsv")]
    directories = sorted(path for path in args.run.glob("owner-*-settings-*") if path.is_dir())
    if len(directories) != len(generation["selected_profiles"]):
        raise ValueError("Recorded profile coverage differs from its generation manifest")
    for label, field in (("native", "source_native"), ("candidate", "source_candidate")):
        if proof[field]["sha256"] != sha256(directories[0] / f"{label}.tsv"):
            raise ValueError("Public Boost proof refers to different original output bytes")
        path = args.boost_scope / f"{label}.process.json"
        process = json.loads(path.read_text())
        if process["exit_status"] != 0 or process["timed_out"] or process["launch_error"]:
            raise ValueError("Public Boost proof process did not actually complete successfully")
        fixed.append(identity(path))
    groups = []
    unusual_names = set()
    for directory in directories:
        processes = {}
        for label in ("native", "candidate"):
            path = directory / f"{label}.process.json"
            process = json.loads(path.read_text())
            if process["exit_status"] != 0 or process["timed_out"] or process["launch_error"]:
                raise ValueError("Native cleanup/reference failures require their own reference-error evidence")
            processes[label] = process
            fixed.extend((identity(path), identity(directory / f"{label}.tsv")))
        report = settings_run.compare_setters(args.run / "inputs.tsv", directory / "native.tsv", directory / "candidate.tsv")
        if report["case_count"] != generation["case_count"]:
            raise ValueError("Complete native/Rust row count differs from generated inputs")
        unusual_names.update(report["native_internal_nul_observations"]["cases"])
        report["processes"] = processes
        report["original_directory"] = str(directory)
        save(output / f"{directory.name}.json", report)
        groups.append(report)
    proof_inputs = list(rows(args.boost_scope / "inputs.tsv", settings_run.INPUT_COLUMNS))
    names = [row["case_id"] for row in proof_inputs]
    if len(names) != len(set(names)) or set(names) != unusual_names:
        raise ValueError("Public Boost proof does not cover every recorded internal-NUL input")
    native_columns = ("case_id", "locale", "load_status", "reorder_codes", "primary", "boost_primary", "identical", "boost_identical")
    boost_rows = list(rows(args.boost_scope / "native.tsv", native_columns))
    rust_rows = list(rows(args.boost_scope / "candidate.tsv", (*settings_run.OUTPUT_COLUMNS, "boost_primary", "boost_identical")))
    for values in (boost_rows, rust_rows):
        if [row["case_id"] for row in values] != names:
            raise ValueError("Public Boost proof row identities differ")
    for native, rust in zip(boost_rows, rust_rows, strict=True):
        if any(native[field] != rust[field] for field in ("primary", "identical", "boost_primary", "boost_identical")):
            raise ValueError("An actual complete public Boost vector differs from the Rust API output")
    sources = [identity(HERE / name) for name in ("verify_reorder_run.py", "run.py")]
    for record in sources:
        source = Path(record["path"])
        shutil.copyfile(source, output / source.name)
    shutil.copyfile(args.driver_observation, output / "original-driver-observation.json")
    if any(sha256(Path(record["path"])) != record["sha256"] for record in fixed):
        raise ValueError("Original evidence changed during this read-only classification")
    result = {"schema": "boostregexrs.icu77-reorder-evidence-verification.v1",
              "status": "passed_for_recorded_inputs" if all(group["status"] == "passed_for_recorded_inputs" for group in groups)
                        else "differences_or_incomplete",
              "execution": "Evidence-only; no candidate or native process rerun",
              "original_run_status_preserved": original["status"], "original_run": identity(original_path),
              "command": [sys.executable, *sys.argv], "sources": sources, "original_sources_verified": preserved_sources,
              "evidence_identities": fixed, "complete_case_count": sum(group["case_count"] for group in groups),
              "raw_key_sequences_compared": sum(group["after_key_sequences_compared"] + group["before_state_key_sequences_compared"] for group in groups),
              "public_boost_scope": identity(args.boost_scope / "summary.json"),
              "internal_nul_rows_retained": len(unusual_names), "original_driver_abort_retained": identity(args.driver_observation),
              "selected_profiles": generation["selected_profiles"], "not_covered": generation["not_covered"],
              "contract": "Exact complete returned lengths and all bytes, statuses and before/after state; no NUL truncation or input normalization"}
    save(output / "summary.json", result)
    print(json.dumps({key: result[key] for key in ("status", "complete_case_count", "raw_key_sequences_compared", "internal_nul_rows_retained", "original_run_status_preserved")}))
    return 0 if result["status"] == "passed_for_recorded_inputs" else 1


if __name__ == "__main__":
    raise SystemExit(main())
