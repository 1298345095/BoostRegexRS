#!/usr/bin/env python3
"""Check the public Boost locale/traits path without changing official sources."""

import argparse
import json
import os
from pathlib import Path
import shutil
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
    cache = args.cache.resolve()
    prefix = cache / "install/icu"
    boost = cache / "deps/boost_1_89_0"
    build = cache / "build/boost-locale-reset" / output.name
    build.mkdir(parents=True, exist_ok=False)
    binary = build / "boost-locale-reset"
    libraries = [prefix / f"lib/libicu{name}.a" for name in ("i18n", "uc", "data")]
    environment = os.environ.copy()
    environment.pop("ICU_DATA", None)
    environment["LC_ALL"] = "C"
    command = ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-DU_STATIC_IMPLEMENTATION",
               "-I", boost, "-I", prefix / "include", HERE / "boost-locale-reset.cpp", *libraries,
               "-lpthread", "-ldl", "-lm", "-o", binary]
    run_logged(bounded(command, 180), cwd=REPO, log=output / "build.log", env=environment, timeout=190)
    run_logged(bounded([binary], 30), cwd=REPO, log=output / "native.log", env=environment, timeout=40)
    run_logged(bounded(["c++", "--version"], 20), cwd=REPO, log=output / "compiler.log", env=environment, timeout=30)
    run_logged(bounded(["ldd", binary], 20), cwd=REPO, log=output / "linkage.log", env=environment, timeout=30)
    result = {"schema": "boostregexrs.boost189-locale-reset-scope.v1", "status": "passed_for_recorded_calls",
              "binary": identity(binary), "command": [sys.executable, *sys.argv],
              "process_environment": {"set": {"LC_ALL": "C"}, "unset": ["ICU_DATA"]},
              "compiler": identity(Path(shutil.which("c++")).resolve()),
              "process": json.loads((output / "native.process.json").read_text()),
              "sources": [identity(HERE / name) for name in ("boost-locale-reset.cpp", "diagnose_boost_reset.py")]
                         + [identity(boost / name) for name in ("boost/regex/icu.hpp", "boost/regex/v5/icu.hpp")],
              "libraries": list(map(identity, libraries)),
              "scope": "Public traits imbue am -> am@colReorder=Grek-Latn -> am; six complete nonempty Boost keys; normal destruction",
              "source_conclusion": "Boost imbue constructs fresh private collators; it exposes no public operation that restores DEFAULT on an existing owned ICU reorder buffer",
              "not_claimed": ["The direct ICU DEFAULT setter/destructor process passed", "Arbitrary locale resolver acceptance"],
              "official_cache_modified": False, "destruction_bypassed": False}
    save(output / "summary.json", result)
    print(json.dumps({key: result[key] for key in ("status", "binary", "scope")}))


if __name__ == "__main__":
    main()
