#!/usr/bin/env python3
"""Audit this immutable V01 run and derive corrected runtime-metadata references."""

import argparse
from collections import Counter
import hashlib
import json
import lzma
from pathlib import Path
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools/regex-oracle"))
import build_reference


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="A new derived-report directory")
    args = parser.parse_args()
    cache = args.cache.resolve()
    output = args.output.resolve()
    summary_path, raw_path = HERE / "summary.json", HERE / "raw-run.tar.xz"
    summary = json.loads(summary_path.read_text())
    protected = (summary_path, raw_path, cache / "environment-manifest.json",
                 cache / "reference-manifest.json")
    before = {str(path): digest(path) for path in protected}
    require(before[str(raw_path)] == summary["raw_evidence_archive"]["sha256"], "Raw archive digest differs")
    require(summary["status"] == "passed_reference_reproduction", "Native build did not pass")
    process_rows = []
    source_entries = {}
    with tarfile.open(raw_path) as archive:
        members = {member.name: member for member in archive.getmembers()}
        require(not archive.extractfile("logs/checkout-status.log").read().strip(), "Checkout was dirty")
        head = archive.extractfile("logs/checkout-head.log").read().decode().strip()
        require(head == summary["checkout"]["commit"], "Recorded checkout differs")
        for name in sorted(members):
            if not name.endswith(".process.json"):
                continue
            record = json.loads(archive.extractfile(name).read())
            require(record["timeout_seconds"] > 0, f"Missing deadline: {name}")
            require(not record["timed_out"] and not record["launch_error"], f"Process did not finish: {name}")
            for field in ("stdout", "stderr", "stdin"):
                if record[field] is not None:
                    relative = Path(record[field]).relative_to(cache).as_posix()
                    require(relative in members, f"Missing {field} evidence: {name}")
            expected = -11 if name == "logs/empty-original-identical.process.json" else 0
            require(record["returncode"] == expected, f"Unexpected process outcome: {name}")
            process_rows.append({"record": name, "returncode": record["returncode"],
                                 "timeout_seconds": record["timeout_seconds"]})
        for source in summary["extracted_sources"]:
            relative = Path(source["manifest"]).relative_to(cache).as_posix()
            packed = archive.extractfile(relative).read()
            require(hashlib.sha256(packed).hexdigest() == source["manifest_sha256"], "Source manifest digest differs")
            plain = lzma.decompress(packed)
            require(hashlib.sha256(plain).hexdigest() == source["uncompressed_manifest_sha256"], "Source content manifest differs")
            require(len(plain.splitlines()) - 1 == source["entries"], "Source entry count differs")
            source_entries[Path(source["root"]).name] = source["entries"]
        for strength in ("primary", "identical"):
            relative = "smoke/" + strength + "-metadata.json"
            require(archive.extractfile(relative).read() == (cache / relative).read_bytes(), "Live smoke metadata differs from archive")
        linker_version = archive.extractfile("logs/linker-version.log").read().decode().splitlines()[0]

    native_root = cache.parents[2]
    identities = {}
    for reference in summary["references"].values():
        for identity in [reference["executable"], reference["source"], *reference["runtime_libraries"]]:
            path = (native_root / identity["path"]).resolve()
            require(digest(path) == identity["sha256"], f"Native identity differs: {path}")
            identities[str(path)] = identity["sha256"]
    linker = summary["linker"]
    require(digest((native_root / linker["path"]).resolve()) == linker["sha256"], "Linker identity differs")
    for compiler in summary["environment"]["compiler_executables"]:
        require(digest(Path(compiler["resolved_path"])) == compiler["sha256"], "Compiler identity differs")

    output.mkdir(parents=True, exist_ok=False)
    derived_path = output / "environment-derived.json"
    derived = build_reference.write_verified_environment(
        cache, summary["environment"], summary["smoke"], derived_path)
    require({str(path): digest(path) for path in protected} == before, "Original evidence changed")
    report = {
        "schema": "boostregexrs.v01-reporting-audit.v1",
        "status": "passed_integrity_and_reporting_checks",
        "native_commit": summary["checkout"]["commit"],
        "raw_archive_sha256": before[str(raw_path)],
        "process_records": process_rows,
        "process_returncodes": dict(Counter(str(row["returncode"]) for row in process_rows)),
        "source_entries": source_entries,
        "native_identities_rechecked": identities,
        "linker_version": linker_version,
        "original_metadata_locator": summary["environment"]["data"]["runtime_versions_verified_by"],
        "verified_metadata_locators": derived["data"]["runtime_versions_verified_by"],
        "derived_environment_sha256": digest(derived_path),
        "reporting_implementation_sha256": digest(ROOT / "tools/regex-oracle/build_reference.py"),
        "original_evidence_unchanged": True,
        "native_rebuild_performed": False,
    }
    (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("status", "process_returncodes", "source_entries", "linker_version",
                       "verified_metadata_locators", "original_evidence_unchanged")}, indent=2))


if __name__ == "__main__":
    main()
