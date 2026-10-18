#!/usr/bin/env python3
"""Record the execution owner's exact A-snapshot lint overrides afterward.

This is a supplemental record, not a capture of the historical process's full
environment. It never reruns a command or alters its original process record.
"""

import argparse
import datetime as dt
import json
from pathlib import Path

from refresh_fcd_fixtures import identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-directory", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--target-directory", type=Path, required=True)
    args = parser.parse_args()
    directory = args.execution_directory.resolve()
    prefix = args.prefix.resolve()
    process = directory / "clippy.process.json"
    original = json.loads(process.read_text())
    if original["exit_status"] != 0:
        raise ValueError("This supplement is for the successful recorded A lint invocation")
    command = original["command"]
    if command[:4] != [str(prefix / "bin/cargo"), "check", "--locked", "--all-targets"]:
        raise ValueError("The recorded process does not use the supplied Cargo and expected A lint command")
    tools = [prefix / "bin" / name for name in ("cargo", "clippy-driver", "rustc", "rustfmt")]
    document = {
        "schema": "boostregexrs.execution-environment-supplement.v1",
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "recorded_after_execution": True,
        "basis": "Exact overrides supplied by the execution owner from the original command; tool identities measured when recording this supplement",
        "scope": "A snapshot Clippy invocation only; unlisted inherited variables and the format/test environments are not reconstructed",
        "original_process": identity(process),
        "original_started_utc": original["started_utc"],
        "environment": {
            "RUSTC": str(prefix / "bin/clippy-driver"),
            "SYSROOT": str(prefix),
            "LD_LIBRARY_PATH": str(prefix / "lib"),
            "RUSTFLAGS": f"-C link-arg=-fuse-ld=bfd --sysroot {prefix} -D warnings",
            "CARGO_TARGET_DIR": str(args.target_directory.resolve()),
        },
        "tools": [identity(path) for path in tools],
        "toolchain_manifest": identity(directory / "rust-toolchain-manifest.json"),
        "recorder": identity(Path(__file__)),
    }
    output = directory / "execution-environments.json"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(document, indent=2) + "\n")
    print(json.dumps({"output": str(output), "sha256": identity(output)["sha256"]}))


if __name__ == "__main__":
    main()
