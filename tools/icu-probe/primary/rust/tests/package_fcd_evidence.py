#!/usr/bin/env python3
"""Package the completed A/B recovery evidence once, without duplicating old runs.

The original execution records remain unchanged. New collection metadata and
an exact native environment snapshot are added before deterministic archiving.
No implementation, native reference, or performance test is executed here.
"""

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import sys

from refresh_fcd_fixtures import PRIMARY, REPO, TESTS, identity

sys.path.insert(0, str(PRIMARY))
from archive_evidence import archive  # noqa: E402


def preserve(path, content):
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Existing collection metadata differs: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(content)


def save(path, value):
    preserve(path, (json.dumps(value, indent=2) + "\n").encode())


def test_counts(path):
    counts = [tuple(map(int, match)) for match in re.findall(
        r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;", path.read_text())]
    if not counts:
        raise ValueError(f"No successful Rust test summaries found: {path}")
    return dict(zip(("passed", "failed", "ignored"), map(sum, zip(*counts)), strict=True))


def historical_availability():
    checkpoint = REPO / "docs/development/tickets/checkpoint"
    old_run = checkpoint / "locale-failed-run"
    manifests = [json.loads((checkpoint / name).read_text())
                 for name in ("manifest.json", "evidence-manifest.json")]
    manifest_bytes = lzma.decompress((old_run / "manifest.json.xz").read_bytes())
    raw_manifest = json.loads(manifest_bytes)
    summary_bytes = lzma.decompress((old_run / "summary.json.xz").read_bytes())
    old_summary = json.loads(summary_bytes)
    if hashlib.sha256(summary_bytes).hexdigest() != raw_manifest["source_summary_sha256"]:
        raise ValueError("The old run summary no longer matches its archived manifest")
    parts = json.loads((old_run / "raw.tar.xz.parts/manifest.json").read_text())
    if parts["sha256"] != raw_manifest["archive"]["sha256"]:
        raise ValueError("Old run archive and transport identities disagree")
    diagnostic = REPO / "docs/research/assets/icu77-locales/diagnostics/fo-search-fcd-22721fc2/summary.json"
    candidate = json.loads(diagnostic.read_text())["identity"]["candidate"]
    binary_matches = [item for manifest in (*manifests, raw_manifest) for item in manifest["files"]
                      if item["sha256"] == candidate["sha256"]]
    recovered_binary = REPO / "target/research/icu77-cloud/build/locales-rust/release/icu77-root-primary"
    return {
        "recorded_failed_candidate": candidate,
        "original_path_exists": Path(candidate["path"]).is_file(),
        "recovery_cache_path_exists": recovered_binary.is_file(),
        "checkpoint_binary_digest_matches": binary_matches,
        "scope": "Metadata and file availability inspection; the lost candidate was not reconstructed or rerun",
        "source_checkpoint_exclusion": manifests[0]["excluded"],
        "diagnostic_summary": identity(diagnostic),
        "old_run": {
            "status": old_summary["status"], "totals": old_summary["totals"],
            "completed_configurations": old_summary["completed_configurations"],
            "configuration_count": old_summary["configuration_count"],
            "files": len(raw_manifest["files"]),
            "uncompressed_file_bytes": raw_manifest["uncompressed_file_bytes"],
            "archive": raw_manifest["archive"],
            "uncompressed_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "uncompressed_summary_sha256": hashlib.sha256(summary_bytes).hexdigest(),
            "metadata": [identity(old_run / name) for name in (
                "manifest.json.xz", "summary.json.xz", "verification.json", "raw.tar.xz.parts/manifest.json")],
            "transport_parts_present": all((old_run / "raw.tar.xz.parts" / part["path"]).is_file()
                                           for part in parts["parts"]),
            "raw_archive_verified_again": False,
            "preservation": "Already published checkpoint archive is referenced, not copied into this collection",
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--a-directory", required=True, help="A execution directory name below --source")
    parser.add_argument("--native-directory", required=True, help="Native v2 directory name below --source")
    parser.add_argument("--rust-directory", required=True, help="Rust v2 directory name below --source")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output == source or source in output.parents:
        raise ValueError("Archive output must be outside the raw source directory")
    a_dir, native_dir, rust_dir = [source / name for name in (
        args.a_directory, args.native_directory, args.rust_directory)]
    a = json.loads((a_dir / "summary.json").read_text())
    native = json.loads((native_dir / "provenance.json").read_text())
    rust = json.loads((rust_dir / "summary.json").read_text())
    if a["status"] != "passed_snapshot_tests_format_and_clippy" or rust["status"] != "passed_for_recorded_inputs":
        raise ValueError("Expected completed A and B execution records")
    for record in (native["generator"], *native["native_sources"], *rust["tools"], *rust["rust_sources"]):
        if identity(REPO / record["path"])["sha256"] != record["sha256"]:
            raise ValueError(f"Authored source differs from the executed version: {record['path']}")
    environment_path = source / "native-reference-environment.json"
    if not environment_path.exists():
        original = REPO / native["reference_environment"]["path"]
        preserve(environment_path, original.read_bytes())
    if identity(environment_path)["sha256"] != native["reference_environment"]["sha256"]:
        raise ValueError("Native environment snapshot differs from execution provenance")
    history_path = source / "historical-availability.json"
    save(history_path, historical_availability())
    summary = {
        "schema": "boostregexrs.icu77-fcd-evidence-collection.v2",
        "status": "passed_for_recorded_inputs",
        "scope": "U01 recovery, FCD cursor/contraction replay and prerequisite settings validation; no whole-library acceptance",
        "a_snapshot": {"summary": identity(a_dir / "summary.json"), "tree": a["tree"],
                       "tests": test_counts(a_dir / "tests.log"),
                       "lint_environment_supplement": identity(a_dir / "execution-environments.json")},
        "native_reference": {"provenance": identity(native_dir / "provenance.json"),
                             "environment": identity(environment_path), "generation": native["generation"]},
        "rust_candidate": {"summary": identity(rust_dir / "summary.json"), "binary": rust["candidate"],
                           "tests": test_counts(rust_dir / "tests.log"), "totals": rust["totals"],
                           "ce64_rows_passed": rust["ce64_rows_passed"]},
        "historical_availability": identity(history_path),
        "published_tool_sources": [identity(path) for path in (
            TESTS / "refresh_fcd_fixtures.py", TESTS / "verify_fcd_repair.py",
            TESTS / "record_fcd_environments.py", Path(__file__), PRIMARY / "archive_evidence.py")],
        "publication": "Track this compressed collection and its manifest, plus required frozen test fixtures and authored tools; leave expanded raw execution directories unstaged",
        "not_covered": rust["not_covered"],
    }
    save(source / "summary.json", summary)
    print(json.dumps(archive(source, output, "xz")))


if __name__ == "__main__":
    main()
