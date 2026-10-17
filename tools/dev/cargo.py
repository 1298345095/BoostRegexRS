#!/usr/bin/env python3
"""Run Cargo with the verified stable toolchain used by cloud comparisons.

Example: python3 -B tools/dev/cargo.py test --locked
All remaining arguments are passed as an argv list to Cargo, without a shell.
"""

from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools/icu-probe/cloud"))
from prepare import DEFAULT_CACHE  # noqa: E402
from rust_toolchain import prepare_rust  # noqa: E402


def main():
    arguments = sys.argv[1:]
    env = prepare_rust(DEFAULT_CACHE)
    prefix = DEFAULT_CACHE / "toolchain/install"
    if arguments and arguments[0] in {"clippy", "fmt"}:
        env["RUSTC"] = str(prefix / "bin/rustc")
        env["RUSTDOC"] = str(prefix / "bin/rustdoc")
        env["LD_LIBRARY_PATH"] = str(prefix / "lib")
    return subprocess.run([str(prefix / "bin/cargo"), *arguments],
                          cwd=REPO, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
