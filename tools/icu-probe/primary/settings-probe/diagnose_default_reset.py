#!/usr/bin/env python3
"""Build and run the minimal ICU77 public DEFAULT cleanup reproducer."""

import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_locales import REPO, bounded, identity, run_logged, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    prefix = args.cache.resolve() / "install/icu"
    source = args.cache.resolve() / "deps/icu/source"
    build = args.cache.resolve() / "build/default-reset" / output.name
    build.mkdir(parents=True, exist_ok=False)
    binary = build / "default-reset"
    libraries = [prefix / f"lib/libicu{name}.a" for name in ("i18n", "uc", "data")]
    command = ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-DU_STATIC_IMPLEMENTATION",
               "-I", prefix / "include", HERE / "default-reset.cpp", *libraries,
               "-lpthread", "-ldl", "-lm", "-o", binary]
    environment = os.environ.copy()
    environment.pop("ICU_DATA", None)
    environment["LC_ALL"] = "C"
    run_logged(bounded(command, 180), cwd=REPO, log=output / "build.log", env=environment, timeout=190)
    try:
        run_logged(bounded([binary], 30), cwd=REPO, log=output / "native.log", env=environment, timeout=40)
    except RuntimeError:
        pass  # Preserve and classify the actual process record below; never label it a pass.
    process = json.loads((output / "native.process.json").read_text())
    stdout = (output / "native.log").read_text()
    result = {"schema": "boostregexrs.icu77-default-reset-diagnostic.v1",
              "status": "reference_error" if process["exit_status"] != 0 else "reference_completed",
              "process": process, "binary": identity(binary), "command": [sys.executable, *sys.argv],
              "setter_and_all_five_keys_completed": "begin_normal_destruction\n" in stdout,
              "normal_destruction_completed": "normal_destruction_completed\n" in stdout,
              "sources": [identity(HERE / name) for name in ("default-reset.cpp", "diagnose_default_reset.py")]
                         + [identity(source / f"i18n/{name}") for name in ("rulebasedcollator.cpp", "collationsettings.cpp", "collationsettings.h")],
              "libraries": list(map(identity, libraries)),
              "official_cache_modified": False, "destruction_bypassed": False}
    save(output / "summary.json", result)
    print(json.dumps({key: result[key] for key in ("status", "setter_and_all_five_keys_completed", "normal_destruction_completed")}))
    return 0  # Successful diagnostic capture, distinct from the recorded native exit status.


if __name__ == "__main__":
    raise SystemExit(main())
