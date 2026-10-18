#!/usr/bin/env python3
"""Run bounded U01 Rust gates and complete CLI key/CE comparisons in a fresh directory."""

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import time

from refresh_fcd_fixtures import PROFILES, PRIMARY, REPO, TESTS, identity, read_rows, save

sys.path.insert(0, str(PRIMARY))
from compare import compare  # noqa: E402
sys.path.insert(0, str(REPO / "tools/icu-probe/cloud"))
from rust_toolchain import prepare_rust  # noqa: E402


def verify_historical_reference(fixtures):
    """Compare preserved failure evidence with independently regenerated native rows."""
    history = REPO / "docs/research/assets/icu77-locales/diagnostics"
    keys = [row for row in read_rows(fixtures / "native-keys-ces.tsv")
            if row["profile"] == "fo-on" and row["strength"] == "identical"]
    cursors = read_rows(fixtures / "native-cursor.tsv")
    checks = []
    for relative, fresh, identifiers in (
        ("fo-search-fcd-22721fc2/expected-keys.tsv", keys, ("case_id",)),
        ("fo-search-fcd-22721fc2/native-ces.tsv", keys, ("case_id",)),
        ("fo-search-fcd-cursor/native-fcd.tsv", cursors, ("case_id", "direction", "index")),
        ("fo-search-fcd-reduced/native-fcd.tsv", cursors, ("case_id", "direction", "index")),
    ):
        path = history / relative
        preserved = read_rows(path)
        index = {tuple(row[key] for key in identifiers): row for row in fresh}
        for row in preserved:
            observed = index[tuple(row[key] for key in identifiers)]
            if any(observed[key] != value for key, value in row.items()):
                raise ValueError(f"Regenerated native reference differs from preserved evidence: {path}/{row}")
        checks.append({"reference": identity(path), "rows_passed": len(preserved)})
    old_flags = history / "fcd-unit-flags/native-fcd-flags.bin"
    if old_flags.read_bytes() != (fixtures / "native-flags.bin").read_bytes():
        raise ValueError("Regenerated FCD flags differ from preserved native evidence")
    checks.append({"reference": identity(old_flags), "bytes_passed": old_flags.stat().st_size})
    return checks


def run(args):
    fixtures = TESTS / "data/fcd77"
    if not (fixtures / "native-keys-ces.tsv").is_file():
        raise ValueError("Full native key fixtures are required; run refresh_fcd_fixtures.py --update-fixtures first")
    fixture_manifest = json.loads((fixtures / "provenance.json").read_text())
    for item in fixture_manifest["fixtures"]:
        path = fixtures / Path(item["path"]).name
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Frozen fixture no longer matches native provenance: {path}")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%S.%fZ")
    output = (args.output or REPO / "docs/research/assets/icu77-locales/fcd-repair" / stamp).resolve()
    output.mkdir(parents=True, exist_ok=False)
    cache = args.cache.resolve()
    build = cache / "build/fcd-repair" / output.name
    prefix = cache / "toolchain/install"
    environment = prepare_rust(cache)
    environment.update({"CARGO_TARGET_DIR": str(build), "CARGO_INCREMENTAL": "0"})
    commands = []

    def execute(command, label, env, *, input_path=None, seconds=120):
        argv = ["timeout", "--signal=TERM", "--kill-after=5s", f"{seconds}s", *map(str, command)]
        print(shlex.join(argv), flush=True)
        target = output / label
        stderr_path = target.with_suffix(target.suffix + ".stderr.log")
        started = time.monotonic()
        with target.open("wb") as stdout, stderr_path.open("wb") as stderr:
            with (input_path or Path(os.devnull)).open("rb") as stdin:
                result = subprocess.run(argv, cwd=REPO, env=env, stdin=stdin, stdout=stdout, stderr=stderr,
                                        timeout=seconds + 10, check=False)
        commands.append({"argv": argv, "exit_code": result.returncode, "seconds": time.monotonic() - started,
                         "stdout": identity(target), "stderr": identity(stderr_path),
                         "environment": {key: env.get(key) for key in (
                             "RUSTC", "RUSTDOC", "RUSTFLAGS", "RUSTC_WORKSPACE_WRAPPER", "CLIPPY_ARGS",
                             "CARGO_TARGET_DIR", "CARGO_INCREMENTAL", "LD_LIBRARY_PATH", "ICU_DATA")}})
        save(output / "commands.json", commands)
        if result.returncode:
            raise RuntimeError(f"Command exited {result.returncode}: {stderr_path}")
        return target, stderr_path

    compiler = prefix / "bin"
    manifest = PRIMARY / "rust/Cargo.toml"
    lint_environment = {**environment, "RUSTC": str(compiler / "rustc"), "RUSTDOC": str(compiler / "rustdoc"),
                        "LD_LIBRARY_PATH": str(prefix / "lib")}
    rust_sources = sorted((PRIMARY / "rust/src").glob("*.rs")) + sorted(TESTS.glob("*.rs"))
    execute([compiler / "rustfmt", "--edition", "2024", "--check", *rust_sources], "fmt.log", lint_environment, seconds=60)
    lint_environment.update({"RUSTC_WORKSPACE_WRAPPER": str(compiler / "clippy-driver"),
                             "CLIPPY_ARGS": "-D__CLIPPY_HACKERY__warnings"})
    # Invoke the same stable tools directly where cargo-fmt/cargo-clippy cannot
    # resolve /proc/self/exe, retaining Cargo's complete all-targets graph.
    execute([compiler / "cargo", "check", "--locked", "--all-targets", "--manifest-path", manifest],
            "clippy.log", lint_environment, seconds=180)
    execute([compiler / "cargo", "test", "--locked", "--manifest-path", manifest], "tests.log", environment, seconds=180)
    execute([compiler / "cargo", "build", "--locked", "--release", "--manifest-path", manifest],
            "build.log", environment, seconds=180)
    candidate = build / "release/icu77-root-primary"
    candidate_environment = dict(os.environ)
    candidate_environment.pop("LD_LIBRARY_PATH", None)
    candidate_environment["ICU_DATA"] = str(cache / "intentionally-absent-icu-data")
    linkage, _ = execute(["ldd", candidate], "linkage.txt", candidate_environment, seconds=20)
    if any(name in linkage.read_text().lower() for name in ("libicu", "libboost", "libstdc++")):
        raise ValueError("Rust candidate links a prohibited native reference library")
    inputs = fixtures / "inputs-u16.tsv"
    native = read_rows(fixtures / "native-keys-ces.tsv")
    groups = []
    for profile, locale, tailored, normalization in PROFILES:
        if tailored:
            settings = bytearray((PRIMARY / "data/locales/settings-0001.bin").read_bytes())
        else:
            settings = bytearray(struct.pack("<8s7I2I4I", b"BRSSET77", 1, 77, 1, 16, 0, 47, 0,
                                             0x2010, 0x0BFFFFFF, 0, 0, 0, 0))
        options, = struct.unpack_from("<I", settings, 36)
        struct.pack_into("<I", settings, 36, (options & ~1) | int(normalization))
        settings_path = output / f"{profile}-settings.bin"
        settings_path.write_bytes(settings)
        for strength in ("primary", "identical"):
            name = f"{profile}-{strength}"
            reference = [row for row in native if row["profile"] == profile and row["strength"] == strength]
            expected = output / f"{name}-expected.tsv"
            with expected.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=("case_id", "raw_icu_hex", "boost_u32_hex"), delimiter="\t", lineterminator="\n", extrasaction="ignore")
                writer.writeheader()
                writer.writerows(reference)
            command = [candidate, "--settings", settings_path, "--strength", strength, "--input-format", "u16", "--trace"]
            if tailored:
                command += ["--owner", PRIMARY / "data/locales/owner-0043.bin"]
            actual, trace = execute(command, f"{name}-actual.tsv", candidate_environment, input_path=inputs, seconds=60)
            summary = compare(inputs, expected, actual, "u16", strength=strength, locale=locale,
                              approved_empty_exceptions=strength == "identical")
            traces = [json.loads(line) for line in trace.read_text().splitlines()]
            ce_passed = 0
            for oracle, observed in zip(reference, traces, strict=True):
                expected_ces = [int(value, 16) for value in oracle["ces64_hex"].split(",")]
                if observed["case_id"] != oracle["case_id"] or [int(value, 16) for value in observed["ces"]] != expected_ces:
                    raise ValueError(f"Complete CE64 sequence differs: {name}/{oracle['case_id']}")
                ce_passed += 1
            summary.update({"profile": profile, "strength": strength, "ce64_rows_passed": ce_passed,
                            "settings": identity(settings_path), "trace": identity(trace)})
            save(output / f"{name}-summary.json", summary)
            groups.append(summary)
            if summary["status"] != "passed_for_recorded_inputs":
                raise ValueError(f"Full-key comparison failed: {name}")
    old = cache / "build/locales-rust/release/icu77-root-primary"
    old_identity = identity(old) if old.is_file() else None
    if old_identity and old_identity["sha256"] != "22721fc23f6ff811b27291234871a4e230833c653dde5a59900437b69093d5a5":
        raise ValueError("The recorded failed candidate was replaced")
    count_names = dict.fromkeys(key for group in groups for key in group["totals"])
    totals = {key: sum(group["totals"].get(key, 0) for group in groups) for key in count_names}
    report = {"schema": "boostregexrs.icu77-fcd-repair.v2", "status": "passed_for_recorded_inputs",
              "totals": totals, "ce64_rows_passed": sum(group["ce64_rows_passed"] for group in groups),
              "historical_reference": verify_historical_reference(fixtures),
              "native_reference": identity(fixtures / "provenance.json"), "candidate": identity(candidate),
              "preserved_failed_candidate": old_identity,
              "historical_binary_note": "An absent old binary was pruned with the prior workspace; only an existing file is hash-verified here",
              "rust_toolchain": json.loads((cache / "rust-toolchain-manifest.json").read_text()),
              "rust_sources": [identity(path) for path in rust_sources],
              "tools": [identity(Path(__file__)), identity(TESTS / "refresh_fcd_fixtures.py")],
              "data": [identity(path) for path in sorted((PRIMARY / "data").rglob("*.bin"))],
              "groups": [{"profile": group["profile"], "strength": group["strength"], "totals": group["totals"]} for group in groups],
              "not_covered": ["U02 complete tailoring owner sweeps", "U03 all settings configurations",
                              "production regex integration", "six-platform release acceptance", "release performance and memory"]}
    save(output / "summary.json", report)
    print(json.dumps({"output": str(output), "totals": totals, "candidate": report["candidate"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=REPO / "target/research/icu77-cloud")
    parser.add_argument("--output", type=Path)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
