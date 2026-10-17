#!/usr/bin/env python3
"""Replay the locked ICU4X candidate and keep cloud/historical evidence separate."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import datetime as dt
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import subprocess

from prepare import DEFAULT_CACHE, REPO, file_identity, write_json


PROBE = REPO / "tools/icu-probe"
HISTORICAL = REPO / "docs/research/assets/icu-probe"


def comparator_module():
    spec = importlib.util.spec_from_file_location("cloud_ordering_comparator", PROBE / "compare_ordering.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load ordering comparator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def table(path: Path, columns: tuple[str, ...]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != list(columns):
            raise ValueError(f"Unexpected columns in {path}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"Incomplete or excess fields in {path}")
    return rows


def original_keys(path: Path, comparator) -> dict[tuple[str, str, str], tuple[int, ...] | str]:
    result = {}
    for row in table(path, ("locale", "case_id", "primary", "identical")):
        for strength in comparator.STRENGTHS:
            identity = (row["locale"], row["case_id"], strength)
            if identity in result:
                raise ValueError(f"Duplicate reference key in {path}: {identity}")
            value = row[strength]
            if comparator.REFERENCE_ERROR.fullmatch(value):
                result[identity] = value
            else:
                key = tuple(int(part, 16) for part in value.split(","))
                if any(value < 0 or value > 255 for value in key):
                    raise ValueError(f"Invalid Boost byte-promoted u32 key: {identity}")
                result[identity] = key
    return result


def compare_originals(cloud: Path, historical: Path, cases: Path, comparator) -> dict:
    windows_keys = original_keys(historical / "reference-sortkeys.tsv", comparator)
    linux_keys = original_keys(cloud / "sortkeys.tsv", comparator)
    ids = [row["case_id"] for row in table(cases, ("case_id", "utf8_hex"))]
    expected = set(itertools.product(comparator.LOCALES, ids, comparator.STRENGTHS))
    if set(windows_keys) != expected or set(linux_keys) != expected:
        raise ValueError("Original reference corpus coverage differs between platforms")
    totals = {"requested_keys": len(expected), "equal_valid_keys": 0, "different_valid_keys": 0,
              "reference_error_keys": 0, "uncovered_keys": 0}
    errors = []
    differences = []
    for identity in sorted(expected):
        windows, linux = windows_keys[identity], linux_keys[identity]
        row = dict(zip(("locale", "case_id", "strength"), identity))
        if isinstance(windows, str) or isinstance(linux, str):
            totals["reference_error_keys"] += 1
            errors.append({**row,
                           "historical_windows": windows if isinstance(windows, str) else "valid_key",
                           "cloud_linux": linux if isinstance(linux, str) else "valid_key"})
        elif windows == linux:
            totals["equal_valid_keys"] += 1
        else:
            totals["different_valid_keys"] += 1
            first = next(index for index, pair in enumerate(itertools.zip_longest(windows, linux))
                         if pair[0] != pair[1])
            differences.append({**row, "first_different_u32_element": first,
                                "historical_windows_key": windows, "cloud_linux_key": linux})
    return {
        "comparison": "all u32 key elements and lengths; original error markers remain distinct evidence",
        "totals": totals,
        "error_categories": {
            "historical_windows": dict(Counter(row["historical_windows"] for row in errors)),
            "cloud_linux": dict(Counter(row["cloud_linux"] for row in errors)),
        },
        "reference_errors": errors, "valid_key_differences": differences,
        "source_files": [file_identity(historical / "reference-sortkeys.tsv"), file_identity(cloud / "sortkeys.tsv")],
    }


def compare_locale_queries(cloud: Path) -> dict:
    origins = {}
    for name, metadata_file, locale_file in [
        ("historical_windows", HISTORICAL / "reference-metadata.json", HISTORICAL / "locales.tsv"),
        ("cloud_linux", cloud / "metadata.json", cloud / "locales.tsv"),
    ]:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8-sig"))
        rows = table(locale_file, ("requested", "imbue_previous", "getloc", "second_imbue_previous"))
        origins[name] = {
            "default_locale": metadata["default_locale"], "rows": len(rows),
            "getloc_equals_process_default": sum(row["getloc"] == metadata["default_locale"] for row in rows),
            "first_imbue_returns_process_default": sum(row["imbue_previous"] == metadata["default_locale"] for row in rows),
            "second_imbue_returns_actual_requested_locale": sum(
                row["second_imbue_previous"] == ("" if row["requested"] == "root" else row["requested"])
                for row in rows),
            "files": [file_identity(metadata_file), file_identity(locale_file)],
        }
    return {"contract": "ADR-0005: getloc queries the process default; the actual imbued sorting locale is preserved",
            "platform_default_difference_is_a_key_mismatch": False, **origins}


def compare_codepoint_digest(cloud: Path) -> dict:
    historical_manifest = HISTORICAL / "reference-manifest.json"
    manifest = json.loads(historical_manifest.read_text(encoding="utf-8-sig"))
    entries = [item for item in manifest["files"] if item["path"].replace("\\", "/").endswith("/codepoints.bin")]
    if len(entries) != 1:
        raise ValueError("Expected exactly one historical codepoint file identity")
    actual = file_identity(cloud / "codepoints.bin")
    return {"historical_binary_available": False,
            "comparison": "regenerated cloud bytes against the preserved historical SHA256 and byte length",
            "historical_windows": entries[0], "cloud_linux": actual,
            "sha256_equal": actual["sha256"] == entries[0]["sha256"],
            "byte_length_equal": actual["bytes"] == entries[0]["bytes"],
            "historical_manifest": file_identity(historical_manifest)}


def copy_snapshot(cache: Path, output: Path, snapshot: Path) -> None:
    snapshot = snapshot.resolve()
    if snapshot == HISTORICAL or HISTORICAL in snapshot.parents:
        raise RuntimeError("Cloud evidence must not replace any historical Windows evidence")
    snapshot.mkdir(parents=True, exist_ok=True)
    for name in ["baseline", "non-fcd"]:
        destination = snapshot / name
        destination.mkdir(parents=True, exist_ok=True)
        reference = cache / "reference" / name
        for source_name, destination_name in [
            ("sortkeys.tsv", "reference-sortkeys.tsv"), ("metadata.json", "reference-metadata.json"),
            ("locales.tsv", "locales.tsv"), ("names.tsv", "names.tsv"),
            ("stdout.log", "reference-stdout.log"), ("stderr.log", "reference-stderr.log"),
        ]:
            shutil.copyfile(reference / source_name, destination / destination_name)
        for filename in ["codepoint-summary.json", "candidate-ordering.tsv", "ordering-summary.json",
                         "candidate-stdout.log", "candidate-stderr.log"]:
            shutil.copyfile(output / name / filename, destination / filename)
    empty_destination = snapshot / "empty-keys"
    empty_destination.mkdir(parents=True, exist_ok=True)
    for path in (cache / "reference/empty-keys").iterdir():
        if path.is_file():
            shutil.copyfile(path, empty_destination / path.name)
    for source, name in [
        (cache / "environment-manifest.json", "environment-manifest.json"),
        (cache / "reference-build-manifest.json", "reference-build-manifest.json"),
        (cache / "reference/manifest.json", "reference-manifest.json"),
        (cache / "reference/empty-diagnostics.json", "empty-diagnostics.json"),
        (output / "cross-platform-summary.json", "cross-platform-summary.json"),
        (output / "manifest.json", "replay-manifest.json"),
    ]:
        shutil.copyfile(source, snapshot / name)
    write_json(snapshot / "snapshot-manifest.json", {
        "schema": "boostregexrs.icu77-cloud-snapshot.v1",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "fresh cloud original-reference and unchanged ICU4X candidate replay; historical Windows evidence remains separate",
        "large_reproducible_files_omitted": ["codepoints.bin", "source archives", "native/Rust executables", "native libraries"],
        "files": [file_identity(path, snapshot) for path in sorted(snapshot.rglob("*"))
                  if path.is_file() and path.name != "snapshot-manifest.json"
                  and path.relative_to(snapshot).parts[0] != "primary"],
        "separate_snapshot": "primary/snapshot-manifest.json is produced by cloud/run.py after PRIMARY validation",
    })


def run_replay(cache: Path, output: Path | None = None, snapshot: Path | None = None,
               candidate: Path | None = None) -> dict:
    cache = cache.resolve()
    output = output.resolve() if output is not None else cache / "replay"
    candidate = candidate.resolve() if candidate is not None else cache / "build/candidate/release/icu4x-compat-probe"
    if not candidate.is_file():
        raise RuntimeError(f"Build the locked ICU4X candidate first: {candidate}")
    comparator = comparator_module()
    results = {}
    cross_platform = {}
    commands = []
    for name, cases, historical in [
        ("baseline", PROBE / "reference/cases.tsv", HISTORICAL),
        ("non-fcd", PROBE / "non-fcd-cases.tsv", HISTORICAL / "non-fcd"),
    ]:
        destination = output / name
        destination.mkdir(parents=True, exist_ok=True)
        reference = cache / "reference" / name
        command = [str(candidate), "--reference", str(cache / "reference/baseline/codepoints.bin"),
                   "--summary", str(destination / "codepoint-summary.json"), "--cases", str(cases),
                   "--ordering-output", str(destination / "candidate-ordering.tsv")]
        completed = subprocess.run(command, capture_output=True)
        (destination / "candidate-stdout.log").write_bytes(completed.stdout)
        (destination / "candidate-stderr.log").write_bytes(completed.stderr)
        if completed.returncode:
            raise RuntimeError(f"ICU4X replay failed ({completed.returncode}); see {destination}")
        commands.append(command)
        result = comparator.compare(cases, reference / "sortkeys.tsv", destination / "candidate-ordering.tsv")
        write_json(destination / "ordering-summary.json", result)
        results[name] = result
        cross_platform[name] = compare_originals(reference, historical, cases, comparator)
        historic_ordering = table(historical / "candidate-ordering.tsv",
                                 ("locale", "strength", "left_id", "right_id", "ordering"))
        cloud_ordering = table(destination / "candidate-ordering.tsv",
                              ("locale", "strength", "left_id", "right_id", "ordering"))
        cross_platform[name]["candidate_sign_rows"] = {
            "historical_windows": len(historic_ordering), "cloud_linux": len(cloud_ordering),
            "same_rows_in_same_order": historic_ordering == cloud_ordering,
        }

    cross_platform_summary = {
        "schema": "boostregexrs.icu77-cloud-cross-platform.v1", "corpora": cross_platform,
        "codepoint_reference": compare_codepoint_digest(cache / "reference/baseline"),
        "locale_query": compare_locale_queries(cache / "reference/baseline"),
        "empty_exception": {"basis": "ADR-0005; valid-pointer expected values are separate from original-reference errors",
                            "cloud_expected_values": file_identity(cache / "reference/empty-keys/keys.tsv"),
                            "historical_expected_values": file_identity(HISTORICAL / "empty-keys/keys.tsv"),
                            "same_rows": table(cache / "reference/empty-keys/keys.tsv", ("locale", "strength", "icu_raw_bytes", "boost_u32_key")) ==
                                         table(HISTORICAL / "empty-keys/keys.tsv", ("locale", "strength", "icu_raw_bytes", "boost_u32_key")),
                            "rust_identical_verified": False},
        "primary_stage_repairs_145_identical_differences": False,
    }
    write_json(output / "cross-platform-summary.json", cross_platform_summary)
    manifest = {
        "schema": "boostregexrs.icu77-cloud-replay.v1", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "candidate_binary": file_identity(candidate), "candidate_cargo_lock": file_identity(PROBE / "rust/Cargo.lock"),
        "candidate_sources": [file_identity(PROBE / "rust/src/main.rs"), file_identity(PROBE / "rust/Cargo.toml")],
        "commands": commands,
        "result_totals": {name: result["totals"] for name, result in results.items()},
        "sort_key_bytes_from_icu4x": "unsupported; only the separate PRIMARY prototype provides complete keys",
        "scripts": [file_identity(Path(__file__)), file_identity(PROBE / "compare_ordering.py")],
        "files": [file_identity(path) for path in sorted(output.rglob("*"))
                  if path.is_file() and path.name != "manifest.json"],
    }
    write_json(output / "manifest.json", manifest)
    if snapshot is not None:
        copy_snapshot(cache, output, snapshot)
    print(json.dumps(manifest["result_totals"]), flush=True)
    return {"manifest": manifest, "cross_platform": cross_platform_summary, "ordering": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    result = run_replay(args.cache, args.output, args.snapshot, args.candidate)
    # An unchanged ICU4X replay still has the historical known differences and
    # original-reference errors. Collection success is not compatibility success.
    totals = result["manifest"]["result_totals"].values()
    return int(any(group[status] for group in totals for status in ["mismatched", "unsupported", "reference_error"]))


if __name__ == "__main__":
    raise SystemExit(main())
