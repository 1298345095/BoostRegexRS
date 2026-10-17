#!/usr/bin/env python3
"""Build and replay the existing Boost/ICU probes in the prepared Linux cache."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import resource
import signal
import subprocess

from prepare import DEFAULT_CACHE, REPO, command_output, file_identity, run_logged, write_json


REFERENCE = REPO / "tools/icu-probe/reference"


def runtime_environment(cache: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(cache / "install/icu/lib")
    env["TMPDIR"] = str(cache / "build/tmp")
    env.pop("ICU_DATA", None)
    env.pop("ICU_DATA_FILTER_FILE", None)
    return env


def build_reference(cache: Path, cxx: str = "c++") -> dict[str, Path]:
    cache = cache.resolve()
    boost = cache / "deps/boost_1_89_0"
    prefix = cache / "install/icu"
    if not (cache / "environment-manifest.json").is_file():
        raise RuntimeError("Run cloud/prepare.py before building the reference")
    binaries = cache / "bin"
    binaries.mkdir(parents=True, exist_ok=True)
    environment = runtime_environment(cache)
    result = {}
    commands = []
    for source, name in [("probe.cpp", "icu-reference"), ("empty-probe.cpp", "empty-probe"),
                         ("empty-keys.cpp", "empty-keys")]:
        executable = binaries / name
        command = [cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
                   "-I" + str(boost), "-I" + str(prefix / "include"), str(REFERENCE / source),
                   "-L" + str(prefix / "lib"), "-Wl,-rpath," + str(prefix / "lib"),
                   "-licui18n", "-licuuc", "-licudata", "-o", str(executable)]
        run_logged(command, cwd=REPO, log=cache / "logs" / (name + "-build.log"), env=environment)
        commands.append(command)
        result[name] = executable
        loaded = subprocess.run(["ldd", str(executable)], env=environment,
                                text=True, capture_output=True, check=True)
        (cache / "logs" / (name + "-ldd.txt")).write_text(loaded.stdout, encoding="utf-8")
        for library in ["libicui18n.so.77", "libicuuc.so.77", "libicudata.so.77"]:
            expected = f"{library} => {prefix / 'lib' / library} "
            if expected not in loaded.stdout:
                raise RuntimeError(f"Reference did not load the pinned {library}: {loaded.stdout}")
    write_json(cache / "reference-build-manifest.json", {
        "schema": "boostregexrs.icu77-cloud-reference-build.v1",
        "compiler": command_output([cxx, "--version"]), "commands": commands,
        "source_files": [file_identity(REFERENCE / name) for name in ["probe.cpp", "empty-probe.cpp", "empty-keys.cpp"]],
        "binaries": [file_identity(path) for path in result.values()],
        "environment_manifest": file_identity(cache / "environment-manifest.json"),
        "dynamic_libraries_verified_local": True,
    })
    return result


def run_captured(command: list[str], output: Path, cache: Path, *, allow_failure: bool = False) -> subprocess.CompletedProcess:
    output.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, env=runtime_environment(cache), capture_output=True)
    (output / "stdout.log").write_bytes(result.stdout)
    (output / "stderr.log").write_bytes(result.stderr)
    if result.returncode and not allow_failure:
        raise RuntimeError(f"Reference command failed ({result.returncode}): {command}; see {output}")
    return result


def count_keys(path: Path) -> dict:
    counts = {"requested": 0, "valid_keys": 0, "reference_error": 0}
    errors = []
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            for strength in ["primary", "identical"]:
                counts["requested"] += 1
                if row[strength].startswith("ERROR:"):
                    counts["reference_error"] += 1
                    errors.append({"locale": row["locale"], "case_id": row["case_id"],
                                   "strength": strength, "marker": row[strength]})
                else:
                    key = [int(value, 16) for value in row[strength].split(",")]
                    if any(value > 255 for value in key):
                        raise RuntimeError("Unexpected non-byte element in Boost's exposed u32 key")
                    counts["valid_keys"] += 1
    return {**counts, "errors": errors}


def run_reference(cache: Path, output: Path | None = None, cxx: str = "c++") -> dict:
    cache = cache.resolve()
    output = output.resolve() if output is not None else cache / "reference"
    binaries = build_reference(cache, cxx)
    # Diagnostic crashes must not leave potentially large core files behind.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    corpora = {}
    for name, cases in [("baseline", REFERENCE / "cases.tsv"),
                        ("non-fcd", REPO / "tools/icu-probe/non-fcd-cases.tsv")]:
        directory = output / name
        run_captured([str(binaries["icu-reference"]), str(directory), str(cases)], directory, cache)
        metadata = json.loads((directory / "metadata.json").read_text())
        expected = {"boost": "1_89", "icu": "77.1", "unicode": "16.0", "cldr": "47.0", "data": "77.1"}
        if any(metadata[key] != value for key, value in expected.items()):
            raise RuntimeError(f"Unexpected runtime identity: {metadata}")
        corpora[name] = {"cases": file_identity(cases), "counts": count_keys(directory / "sortkeys.tsv"),
                         "metadata": metadata, "files": [file_identity(path) for path in sorted(directory.iterdir()) if path.is_file()]}

    diagnostics = []
    for mode in ["boost_primary", "boost_identical", "icu_null", "icu_nonnull"]:
        result = run_captured([str(binaries["empty-probe"]), mode], output / "empty-diagnostics" / mode,
                              cache, allow_failure=True)
        diagnostics.append({
            "mode": mode, "exit_code": result.returncode,
            "outcome": "valid_reference_result" if result.returncode == 0 else "reference_error",
            "signal": signal.Signals(-result.returncode).name if result.returncode < 0 else None,
            "stdout": result.stdout.decode("utf-8", errors="replace").strip(),
            "stderr": result.stderr.decode("utf-8", errors="replace").strip(),
        })
    write_json(output / "empty-diagnostics.json", diagnostics)
    empty_directory = output / "empty-keys"
    run_captured([str(binaries["empty-keys"]), str(empty_directory)], empty_directory, cache)
    manifest = {
        "schema": "boostregexrs.icu77-cloud-reference-run.v1",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "environment_manifest": file_identity(cache / "environment-manifest.json"),
        "build_manifest": file_identity(cache / "reference-build-manifest.json"),
        "corpora": corpora, "empty_original_diagnostics": diagnostics,
        "empty_exception": {"basis": "ADR-0005 valid-pointer ICU call; not original Boost results",
                            "rust_implementation_verified": False,
                            "files": [file_identity(path) for path in sorted(empty_directory.iterdir()) if path.is_file()]},
        "locale_environment": {name: os.environ.get(name) for name in ["LANG", "LC_ALL", "LC_COLLATE"]},
        "scripts": [file_identity(Path(__file__))],
        "historical_evidence_modified": False,
    }
    write_json(output / "manifest.json", manifest)
    print(json.dumps({name: data["counts"] for name, data in corpora.items()}, ensure_ascii=False), flush=True)
    print(f"Cloud reference evidence: {output}", flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cxx", default="c++")
    args = parser.parse_args()
    run_reference(args.cache, args.output, args.cxx)


if __name__ == "__main__":
    main()
