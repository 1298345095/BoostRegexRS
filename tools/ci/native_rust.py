#!/usr/bin/env python3
"""Collect native stable Rust collation checks on the six ADR-0002 targets."""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    "x86_64-pc-windows-msvc": ("x86_64", "windows", "X64"),
    "aarch64-pc-windows-msvc": ("aarch64", "windows", "ARM64"),
    "x86_64-unknown-linux-gnu": ("x86_64", "linux", "X64"),
    "aarch64-unknown-linux-gnu": ("aarch64", "linux", "ARM64"),
    "x86_64-apple-darwin": ("x86_64", "macos", "X64"),
    "aarch64-apple-darwin": ("aarch64", "macos", "ARM64"),
}
MANIFEST = ROOT / "tools/icu-probe/primary/rust/Cargo.toml"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def execute(command, directory, name, env):
    start = time.monotonic()
    returncode, error = None, None
    with (directory / f"{name}.stdout").open("wb") as stdout, (directory / f"{name}.stderr").open("wb") as stderr:
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                    check=False, timeout=900)
            returncode = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exception:
            error = str(exception)
    record = {"command": command, "returncode": returncode, "error": error,
              "elapsed_seconds": time.monotonic() - start}
    save(directory / f"{name}.json", record)
    print(f"{name}: exit {returncode}", flush=True)
    return record, (directory / f"{name}.stdout").read_text(encoding="utf-8", errors="replace")


def native_checks(target, output):
    toolchain = "stable-" + target
    build = ROOT / "target/native-rust" / target
    build.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(build)
    env["CARGO_INCREMENTAL"] = "0"
    commands = []

    def run(command, name):
        record, stdout = execute(command, output, name, env)
        commands.append(record)
        return record, stdout

    _, commit = run(["git", "rev-parse", "HEAD"], "git-commit")
    _, tree = run(["git", "rev-parse", "HEAD^{tree}"], "git-tree")
    rustc = ["rustup", "run", toolchain, "rustc"]
    cargo = ["rustup", "run", toolchain, "cargo"]
    compiler_record, compiler = run([*rustc, "--version", "--verbose"], "rustc-version")
    run([*cargo, "--version", "--verbose"], "cargo-version")
    if compiler_record["returncode"] != 0 or f"host: {target}" not in compiler.splitlines():
        raise RuntimeError("The installed compiler is not the requested native stable host toolchain")
    expected_arch, expected_os, runner_arch = TARGETS[target]
    observed_runner_arch = os.environ.get("RUNNER_ARCH")
    if observed_runner_arch and observed_runner_arch.upper() != runner_arch:
        raise RuntimeError("The GitHub runner architecture differs from the target")
    probe = build / ("host-probe.exe" if expected_os == "windows" else "host-probe")
    compiled, _ = run([*rustc, "--edition=2024", "--target", target,
                       str(ROOT / "tools/ci/host_probe.rs"), "-o", str(probe)], "compile-host-probe")
    if compiled["returncode"] != 0:
        raise RuntimeError("The native host probe could not be compiled")
    executed, raw_probe = run([str(probe)], "run-host-probe")
    actual = json.loads(raw_probe)
    if executed["returncode"] != 0 or actual != {"architecture": expected_arch, "os": expected_os, "pointer_bits": 64}:
        raise RuntimeError("The executed program does not identify the requested 64-bit target")
    if expected_os == "linux" and platform.libc_ver()[0] != "glibc":
        raise RuntimeError("The ADR requires a glibc Linux runner")

    manifest_argument = ["--manifest-path", str(MANIFEST)]
    run([*cargo, "fmt", *manifest_argument, "--", "--check"], "format")
    run([*cargo, "clippy", *manifest_argument, "--locked", "--all-targets", "--target", target,
         "--", "-D", "warnings"], "clippy")
    run([*cargo, "test", *manifest_argument, "--locked", "--all-targets", "--target", target], "tests")
    run([*cargo, "test", *manifest_argument, "--locked", "--doc", "--target", target], "doctests")
    run([*cargo, "doc", *manifest_argument, "--locked", "--no-deps", "--target", target], "documentation")
    inputs = [MANIFEST, MANIFEST.with_name("Cargo.lock"), ROOT / "tools/ci/native_rust.py", ROOT / "tools/ci/host_probe.rs"]
    for directory in (MANIFEST.parent / "src", MANIFEST.parent / "tests", MANIFEST.parent.parent / "data"):
        inputs.extend(sorted(path for path in directory.rglob("*") if path.is_file()))
    summary = {
        "schema": "boostregexrs.native-rust-collation-checks.v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "passed" if all(item["returncode"] == 0 for item in commands) else "failed",
        "scope": "Committed ICU77 Rust collation research crate: format, lint, executable tests, doctests and documentation",
        "full_library_platform_acceptance": "not_established_by_this_workflow",
        "target": target, "toolchain_selector": toolchain, "compiler": compiler,
        "executed_host_probe": actual, "commit": commit.strip(), "tree": tree.strip(),
        "environment": {"platform": platform.platform(), "uname": list(platform.uname()),
                        "libc": list(platform.libc_ver()), "python": sys.version,
                        "github": {key: os.environ.get(key) for key in (
                            "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "RUNNER_OS", "RUNNER_ARCH", "ImageOS", "ImageVersion")}},
        "versions": {"icu": "77.1", "unicode": "16.0.0", "cldr": "47"},
        "commands": commands,
        "inputs": [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                    "sha256": sha256(path)} for path in inputs],
    }
    save(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Create outside the failure-reporting block: a repeated output path must
    # fail without replacing an earlier run's summary.
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        summary = native_checks(args.target, args.output)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        summary = {"status": "failed", "target": args.target, "error": str(error),
                   "full_library_platform_acceptance": "not_established_by_this_workflow"}
        save(args.output / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return int(summary["status"] != "passed")


if __name__ == "__main__":
    sys.exit(main())
