#!/usr/bin/env python3
"""Expose the source fields responsible for a minimized reorder rejection."""

import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_locales import PRIMARY, REPO, bounded, identity, run_logged, save
from locale_format import read_scripts, read_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--reduction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build = args.cache.resolve() / "build/settings-inspection" / output.name
    build.mkdir(parents=True, exist_ok=False)
    prefix = args.cache.resolve() / "install/icu"
    source = args.cache.resolve() / "deps/icu/source"
    libraries = [prefix / f"lib/libicu{name}.a" for name in ("i18n", "uc", "data")]
    binary = build / "inspect-reorder"
    compile_command = ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-DU_STATIC_IMPLEMENTATION",
                       "-I", prefix / "include", "-I", source / "common", "-I", source / "i18n",
                       HERE / "inspect-reorder.cpp", *libraries, "-lpthread", "-ldl", "-lm", "-o", binary]
    environment = os.environ.copy()
    environment.pop("ICU_DATA", None)
    environment["LC_ALL"] = "C"
    compiled = run_logged(bounded(compile_command, 180), cwd=REPO, log=output / "build.log", env=environment, timeout=190)
    reduction = json.loads(args.reduction.read_text())
    codes = reduction["minimal_codes"]
    binary_output = output / "native-settings.bin"
    process = run_logged(bounded([binary, ",".join(map(str, codes)), binary_output], 30),
                         cwd=REPO, log=output / "native.log", env=environment, timeout=40)
    settings = read_settings(binary_output)
    scripts = read_scripts(PRIMARY / "data/locales/scripts.bin")
    unused = set()
    for slot in (14, 15):
        index = scripts["scripts_index"][scripts["num_scripts"] + slot]
        if index:
            unused.update(range((scripts["script_starts"][index] + 255) // 256,
                                scripts["script_starts"][index + 1] // 256))
    split = {pair >> 24 for pair in settings["reorder_ranges"] if pair & 0xFF0000}
    rejected = [{"lead": lead, "table_byte": byte, "split": lead in split, "reserved_unused": lead in unused}
                for lead, byte in enumerate(settings["reorder_table"])
                if 3 <= lead < 255 and ((lead in split and byte != 0)
                   or (lead not in split and lead not in unused and not 3 <= byte < 255))]
    save(output / "settings.json", settings)
    save(output / "summary.json", {"schema": "boostregexrs.icu77-reorder-fields.v1", "status": "native_fields_recorded",
         "command": [sys.executable, *sys.argv], "codes": codes, "binary": identity(binary),
         "native_settings": identity(binary_output), "split_leads": sorted(split), "unused_reserved_leads": sorted(unused),
         "rejected_by_frozen_B_lead_validation": rejected,
         "sources": [identity(HERE / name) for name in ("inspect-reorder.cpp", "inspect_reorder.py")]
                    + [identity(source / f"i18n/{name}") for name in ("collationsettings.cpp", "collationsettings.h", "collationdata.cpp", "collationdata.h")],
         "libraries": list(map(identity, libraries)), "build_process": compiled, "native_process": process})
    print(json.dumps({"codes": codes, "rejected_by_frozen_B_lead_validation": rejected}))


if __name__ == "__main__":
    main()
