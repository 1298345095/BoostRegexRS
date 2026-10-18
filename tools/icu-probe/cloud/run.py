#!/usr/bin/env python3
"""Reproduce the cloud reference and root PRIMARY stage from a clean checkout."""

import argparse
import csv
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from prepare import DEFAULT_CACHE, REPO, file_identity, prepare, write_json
from reference import run_reference
from replay import run_replay
from rust_toolchain import prepare_rust


PROBE = REPO / "tools/icu-probe"
PRIMARY = PROBE / "primary"
CARGO_MANIFEST = "Cargo.toml"


def command(command, log, env):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps([str(arg) for arg in command]) + "\n")
        stream.flush()
        result = subprocess.run([str(arg) for arg in command], cwd=REPO, env=env, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); see {log}")


def primary_module():
    sys.path.insert(0, str(PRIMARY))
    spec = importlib.util.spec_from_file_location("primary_validation", PRIMARY / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rust_environment(cache, system_rust):
    if not system_rust:
        return prepare_rust(cache)
    env = dict(os.environ)
    env["CARGO_HOME"] = str(cache / "cargo-home")
    env["TMPDIR"] = str(cache / "build/tmp")
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    versions = {name: subprocess.run([name, "--version"], capture_output=True, text=True, check=True).stdout.strip() for name in ("rustc", "cargo")}
    if any(word in versions["rustc"] for word in ("nightly", "beta", "dev")):
        raise RuntimeError("This stage requires Rust stable")
    write_json(cache / "rust-toolchain-manifest.json", {"source": "caller-supplied stable", "actual": versions, "environment": {name: env.get(name) for name in ("RUSTFLAGS", "RUSTC", "RUSTDOC")}})
    return env


def gates(cache, env):
    logs = cache / "validation"
    logs.mkdir(exist_ok=True)
    for folder, pattern, label in ((PROBE, "test_compare_ordering.py", "ordering-comparator"), (PRIMARY, "test_*.py", "primary-harness")):
        command([sys.executable, "-B", "-m", "unittest", "discover", "-s", folder, "-p", pattern], logs / f"{label}.log", env)
    command(["cargo", "test", "--locked", "--manifest-path", REPO / CARGO_MANIFEST], logs / "root-tests.log", env)
    for folder, label in ((PROBE / "rust", "candidate"), (PRIMARY / "rust", "primary")):
        package_env = {**env, "CARGO_TARGET_DIR": str(cache / "build" / label)}
        command(["cargo", "test", "--locked", "--manifest-path", folder / CARGO_MANIFEST], logs / f"{label}-tests.log", package_env)
        # Cargo's clippy driver recognizes the compiler by the rustc filename;
        # use the unmodified binary for these companion-tool invocations.
        lint_env = dict(package_env)
        if (cache / "toolchain/install/bin/rustc").is_file() and env.get("RUSTC", "").endswith("rustc-local.py"):
            lint_env["RUSTC"] = str(cache / "toolchain/install/bin/rustc")
            lint_env["RUSTDOC"] = str(cache / "toolchain/install/bin/rustdoc")
            lint_env["LD_LIBRARY_PATH"] = str(cache / "toolchain/install/lib")
        command(["cargo", "fmt", "--manifest-path", folder / CARGO_MANIFEST, "--", "--check"], logs / f"{label}-fmt.log", lint_env)
        command(["cargo", "clippy", "--locked", "--all-targets", "--manifest-path", folder / CARGO_MANIFEST, "--", "-D", "warnings"], logs / f"{label}-clippy.log", lint_env)
    command(["git", "diff", "--check"], logs / "diff-check.log", env)
    # The candidate itself runs with the native ICU search path absent. These
    # two extra observations make the runtime boundary independently reviewable.
    executable = cache / "build/primary/release/icu77-root-primary"
    linkage = subprocess.run(["ldd", str(executable)], capture_output=True, text=True, check=True).stdout
    if any(name in linkage.lower() for name in ("libicu", "libboost", "libstdc++")):
        raise RuntimeError("Unexpected native collation/C++ dependency in Rust executable")
    (logs / "primary-ldd.txt").write_text(linkage, encoding="utf-8")
    metadata = subprocess.run(["cargo", "metadata", "--locked", "--no-deps", "--format-version", "1", "--manifest-path", str(PRIMARY / "rust/Cargo.toml")], env=env, capture_output=True, text=True, check=True)
    manifest = json.loads(metadata.stdout)
    if any(package["dependencies"] for package in manifest["packages"]):
        raise RuntimeError("Root PRIMARY prototype unexpectedly has runtime package dependencies")
    write_json(logs / "primary-cargo-metadata.json", manifest)
    return {"status": "passed", "logs": [file_identity(path) for path in sorted(logs.iterdir()) if path.is_file()],
            "root_baseline_warning": "The pre-existing root crate name BoostRegexRS emits non_snake_case; root API was not renamed",
            "primary_and_candidate_clippy": "--all-targets -- -D warnings", "primary_native_collation_linkage": False}


def snapshot_primary(cache, destination, result):
    csv.field_size_limit(sys.maxsize)
    destination = destination / "primary"
    destination.mkdir(parents=True, exist_ok=True)
    sources = [cache / "cloud-summary.json", cache / "rust-toolchain-manifest.json", cache / "primary/summary.json", cache / "primary/cases/generation.json"]
    sources += [cache / "primary" / name / "summary.json" for name in result["primary"]["groups"]]
    sources += sorted((cache / "primary").glob("ce-audit-final-*/summary.json"))
    sources += sorted((cache / "validation").glob("*.log"))
    sources += [cache / "validation/primary-ldd.txt"]
    sources += [cache / "build/primary-export/generation-manifest.json"]
    for source in sources:
        if not source.is_file():
            raise RuntimeError(f"Expected completed-run evidence is missing: {source}")
        if source.is_relative_to(cache / "primary"):
            relative = source.relative_to(cache / "primary")
        elif source == cache / "build/primary-export/generation-manifest.json":
            relative = Path("data-generation-manifest.json")
        else:
            relative = source.relative_to(cache)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    # Preserve full key values for historical and representative new cases.
    # Large exhaustive evidence remains separately reproducible under target/;
    # its exact input/output SHA256 is recorded in each group summary.
    selected = []
    with (cache / "primary/cases/directed.tsv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            identity = row["case_id"]
            if identity.startswith(("existing24/", "nonfcd13/", "directed/")) or identity in {f"long/ascii-{n}" for n in (97, 98, 99, 100, 101, 1024)}:
                selected.append(row)
    identities = {row["case_id"] for row in selected}
    with (destination / "sample-cases.tsv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, ("case_id", "utf8_hex"), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(selected)
    for name in ("reference", "candidate"):
        with (cache / "primary/directed" / f"{name}.tsv").open(encoding="utf-8", newline="") as source, (destination / f"sample-{name}.tsv").open("w", encoding="utf-8", newline="") as target:
            reader = csv.DictReader(source, delimiter="\t")
            writer = csv.DictWriter(target, reader.fieldnames, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(row for row in reader if row["case_id"] in identities)
    files = [file_identity(path, destination) for path in sorted(destination.rglob("*")) if path.is_file() and path.name != "snapshot-manifest.json"]
    write_json(destination / "snapshot-manifest.json", {"schema": 1, "purpose": "new cloud root PRIMARY evidence, separate from historical Windows", "files": files})


def replay_checks(cache, cross_platform):
    """Require the entire recorded replay contract, retaining known failures."""
    corpora = cross_platform["corpora"].values()
    valid_keys_equal = all(item["totals"]["different_valid_keys"] == 0
                           and item["totals"]["uncovered_keys"] == 0 for item in corpora)
    error_statuses_preserved = all(
        row["historical_windows"] != "valid_key" and row["cloud_linux"] != "valid_key"
        for item in corpora for row in item["reference_errors"])
    candidate_signs_equal = all(item["candidate_sign_rows"]["same_rows_in_same_order"] for item in corpora)
    digest = cross_platform["codepoint_reference"]
    locale = cross_platform["locale_query"]
    locale_queries_preserved = all(
        locale[platform]["rows"] == 10 and all(locale[platform][name] == 10 for name in (
            "getloc_equals_process_default", "first_imbue_returns_process_default",
            "second_imbue_returns_actual_requested_locale"))
        for platform in ("historical_windows", "cloud_linux"))
    adapter_fields = {"blank", "category", "digit10", "digit16", "digit36", "fold", "lower", "space", "upper"}
    adapters_equal = True
    for name in cross_platform["corpora"]:
        candidate = json.loads((cache / "replay" / name / "codepoint-summary.json").read_text(encoding="utf-8"))
        fields = candidate["icu_compat_adapter"]
        adapters_equal &= set(fields) == adapter_fields and all(
            item["compared"] == 0x110000 and item["mismatches"] == 0 and item["unsupported"] == 0
            for item in fields.values())
    return {"valid_keys_equal_across_platforms": valid_keys_equal,
            "reference_error_statuses_preserved": error_statuses_preserved,
            "candidate_sign_rows_equal": candidate_signs_equal,
            "codepoint_reference_digest_equal": digest["sha256_equal"] and digest["byte_length_equal"],
            "codepoint_adapter_fields_equal": adapters_equal,
            "locale_query_contract_preserved": locale_queries_preserved,
            "approved_empty_expected_rows_equal": cross_platform["empty_exception"]["same_rows"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 2, 8))
    parser.add_argument("--system-rust", action="store_true", help="use an already installed stable; record its actual identity")
    parser.add_argument("--skip-all-scalars", action="store_true", help="diagnostic shorter run; no all-scalar completion claim")
    parser.add_argument("--snapshot", type=Path, help="save new small evidence at this explicit destination")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    cache = args.cache.resolve()
    prepare(cache, args.jobs)
    env = rust_environment(cache, args.system_rust)
    run_reference(cache)
    candidate_env = {**env, "CARGO_TARGET_DIR": str(cache / "build/candidate")}
    command(["cargo", "build", "--locked", "--release", "--manifest-path", PROBE / "rust/Cargo.toml"], cache / "logs/candidate-build.log", candidate_env)
    replay = run_replay(cache, snapshot=args.snapshot)
    command([sys.executable, "-B", PRIMARY / "export/generate.py", "--cache", cache, "--check"], cache / "logs/data-generation.log", env)
    primary = primary_module().run(cache, cache / "primary", all_scalars=not args.skip_all_scalars, rust_env=env)
    for label in ("directed", "contexts"):
        command([sys.executable, "-B", PRIMARY / "export/compare_ce_traces.py", "--cache", cache,
                 "--cases", cache / "primary/cases" / f"{label}.tsv", "--candidate", cache / "build/primary/release/icu77-root-primary",
                 "--output-directory", cache / "primary" / f"ce-audit-final-{label}"], cache / "logs" / f"ce-audit-{label}.log", env)
    validation = gates(cache, env)
    cross_platform = replay["cross_platform"]
    checked_replay = replay_checks(cache, cross_platform)
    replay_ok = all(checked_replay.values())
    result = {"schema": "boostregexrs.icu77-cloud-stage.v1", "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "stage_status": "passed" if primary["status"] == "passed_for_recorded_inputs" and replay_ok else "differences_or_incomplete",
              "coverage_profile": "diagnostic_without_scalar_sweep" if args.skip_all_scalars else "full_recorded_suite",
              "primary": primary, "validation": validation,
              "historical_replay": {"ordering": replay["ordering"], **checked_replay,
                                    "known_identical_differences_are_not_fixed_by_this_stage": True,
                                    "original_empty_identical_reference_errors_preserved": True},
              "complete_library_acceptance": "not attempted; root PRIMARY prototype stage only"}
    if args.skip_all_scalars and result["stage_status"] == "passed":
        result["stage_status"] = "diagnostic_passed"
    write_json(cache / "cloud-summary.json", result)
    if args.snapshot:
        snapshot_primary(cache, args.snapshot, result)
    print(json.dumps({"stage_status": result["stage_status"], "primary": primary["totals"]}), flush=True)
    return int(result["stage_status"] not in ("passed", "diagnostic_passed"))


if __name__ == "__main__":
    raise SystemExit(main())
