#!/usr/bin/env python3
"""Retain completed C reordering runs without rerunning or rewriting evidence."""

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from archive_evidence import archive
from run_locales import REPO, identity, save, sha256


RUNS = {
    "reorder": (
        "api-build-c-v1-20261018", "api-build-c-v2-20261018",
        "reorder-smoke-c-v1-20261018", "reorder-root-full-c-v1-20261018",
        "reorder-root-classified-c-v1-20261018", "reorder-reduced-v1-20261018",
        "reorder-fields-v1-20261018",
    ),
    "boost-scope": (
        "api-build-c-boost-v1-20261018", "api-build-c-boost-v2-20261018",
        "boost-reorder-scope-v2-20261018", "boost-reset-scope-v1-20261018",
    ),
    "goldens": (
        "api-build-c-goldens-v1-20261018", "golden-extraction-v2-20261018",
    ),
}


def collect(group, runs):
    selected = {}
    for name in RUNS[group]:
        directory = runs / name
        if not directory.is_dir():
            raise ValueError(f"Missing actual execution evidence: {directory}")
        selected.update({f"runs/{name}/{path.relative_to(directory).as_posix()}": path
                         for path in directory.rglob("*") if path.is_file()})

    def binary(label, record):
        path = Path(record["path"])
        if identity(path)["sha256"] != record["sha256"]:
            raise ValueError(f"Executable differs from the actual recorded run: {path}")
        selected[f"binaries/{label}"] = path

    if group == "reorder":
        build = json.loads((runs / "api-build-c-v2-20261018/summary.json").read_text())
        binary("icu77-settings-probe-c", build["candidate"])
        for record in build["rust_runtime_sources"]:
            path = Path(record["path"])
            if sha256(path) != record["sha256"]:
                raise ValueError(f"Frozen C runtime source changed: {path}")
            selected[f"source/{path.relative_to(REPO).as_posix()}"] = path
        observation = runs / "reorder-root-driver-observation-v1-20261018.json"
        selected[f"runs/{observation.name}"] = observation
        for path in HERE.glob("*"):
            if (path.is_file() and path.name != Path(__file__).name
                    and path.suffix in (".cpp", ".py", ".toml", ".lock")):
                selected[f"source/{path.relative_to(REPO).as_posix()}"] = path
    elif group == "boost-scope":
        reorder = json.loads((runs / "boost-reorder-scope-v2-20261018/summary.json").read_text())
        reset = json.loads((runs / "boost-reset-scope-v1-20261018/summary.json").read_text())
        binary("icu77-settings-probe-boost-fields", reorder["candidate"])
        binary("boost-reorder-keys", reorder["binary"])
        binary("boost-locale-reset", reset["binary"])
        for record in (*reorder["sources"], *reset["sources"]):
            path = Path(record["path"])
            if sha256(path) != record["sha256"]:
                raise ValueError(f"Frozen Boost scope source changed: {path}")
            selected[f"source/{record['sha256']}/{path.name}"] = path
    else:
        build = json.loads((runs / "api-build-c-goldens-v1-20261018/summary.json").read_text())
        checks = build["library_checks"]
        if build["status"] != "passed" or checks["tests"]["exit_status"] != 0:
            raise ValueError("Golden regression must have completed successfully")
        for record in (*checks["sources"], *checks["fixtures"]):
            path = Path(record["path"])
            if sha256(path) != record["sha256"]:
                raise ValueError(f"Golden regression input changed: {path}")
            if path.name in ("locale_fixtures.rs", "locales-v2.tsv", "locales-v2.json"):
                selected[f"source/{path.relative_to(REPO).as_posix()}"] = path
        cli = Path(build["build_environment"]["CARGO_TARGET_DIR"]) / "debug/icu77-root-primary"
        selected["binaries/icu77-root-primary-c-goldens"] = cli

    for path in (HERE.parent / "data").glob("LICENSE*"):
        selected[f"licenses/{path.name}"] = path
    selected["licenses/NOTICE.md"] = HERE.parent / "data/NOTICE.md"
    selected["retention-source/package_evidence.py"] = Path(__file__)
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=tuple(RUNS), required=True)
    parser.add_argument("--runs", type=Path,
                        default=REPO / "docs/research/assets/icu77-locales/settings-acceptance")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = collect(args.group, args.runs.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="icu77-collection-", dir=args.output.parent) as temporary:
        source = Path(temporary)
        for name, path in sorted(selected.items()):
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        save(source / "summary.json", {
            "schema": "boostregexrs.icu77-settings-evidence-collection.v1",
            "status": "retained_completed_execution_evidence", "group": args.group,
            "command": [sys.executable, *sys.argv], "cwd": str(REPO),
            "sources": [{"member": name, **identity(path)} for name, path in sorted(selected.items())],
            "preservation": "Original completed and failed records copied byte-for-byte; no native or Rust tests rerun",
            "binary_identity_timing": "Recorded run hashes checked where present; the golden test CLI hash is first recorded during retention after its completed Cargo test",
            "shared_failed_binaries": "The exact f7d034c8 native settings reference and B failed probe remain in reorder-failure-retained-v1-20261018; the native DEFAULT crash remains in default-reset-retained-v1-20261018",
            "publication": "Archive is a separate retention package, not a new compatibility pass; original statuses and complete keys are unchanged",
        })
        print(json.dumps(archive(source, args.output, "xz")))


if __name__ == "__main__":
    main()
