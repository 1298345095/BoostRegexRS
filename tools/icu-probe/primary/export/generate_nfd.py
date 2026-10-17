#!/usr/bin/env python3
"""Export fixed ICU77 recursive canonical decompositions and combining classes."""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from generate import ROOT, EXPORT, DATA, SOURCE_FILES, digest, file_record, save_json, verify_source


NFD_SOURCES = tuple(dict.fromkeys(SOURCE_FILES + (
    "source/common/normalizer2.cpp", "source/common/unicode/normalizer2.h",
    "source/i18n/bocsu.cpp", "source/i18n/bocsu.h",
)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "target/research/icu77-cloud")
    parser.add_argument("--output-directory", type=Path, default=DATA)
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    cache, output = args.cache.resolve(), args.output_directory.resolve()
    build = cache / "build/identical-export"
    build.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    provenance, sources = verify_source(cache, NFD_SOURCES)
    prefix = cache / "install/icu"
    prepared = json.loads((cache / "environment-manifest.json").read_text())
    recorded = {Path(item["path"]).name: item["sha256"] for item in prepared["installed_libraries"]}
    libraries = [file_record(prefix / "lib" / name, prefix)
                 for name in ("libicui18n.so.77.1", "libicuuc.so.77.1", "libicudata.so.77.1")]
    if any(recorded[Path(item["path"]).name] != item["sha256"] for item in libraries):
        raise ValueError("ICU installed library differs from its prepared identity")
    environment = dict(os.environ)
    environment.pop("ICU_DATA", None)
    environment["LD_LIBRARY_PATH"] = str(prefix / "lib")
    compiler = shlex.split(args.cxx)
    executable = build / "export-nfd"
    command = compiler + ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                          "-I" + str(prefix / "include"),
                          "-I" + str(cache / "deps/icu/source/common"),
                          "-I" + str(cache / "deps/icu/source/i18n"), str(EXPORT / "export-nfd.cpp"),
                          "-L" + str(prefix / "lib"), "-Wl,-rpath," + str(prefix / "lib"),
                          "-licui18n", "-licuuc", "-licudata", "-o", str(executable)]
    with (build / "build.log").open("w") as log:
        log.write(json.dumps(command) + "\n"); log.flush()
        subprocess.run(command, env=environment, check=True, stdout=log, stderr=subprocess.STDOUT)
    exports = []
    for number in (1, 2):
        binary, metadata = build / f"nfd-{number}.bin", build / f"nfd-{number}.json"
        result = subprocess.run([str(executable), str(binary), str(metadata)], env=environment,
                                capture_output=True, text=True, check=True)
        (build / f"export-{number}.log").write_text(result.stdout + result.stderr)
        exports.append((binary, metadata))
    if any(left.read_bytes() != right.read_bytes() for left, right in zip(*exports)):
        raise ValueError("Independent NFD exports differ")
    binary, metadata = exports[0]
    manifest = {
        "schema": "boostregexrs.icu77-nfd-data.v1", "runtime": json.loads(metadata.read_text()),
        "source": provenance, "source_files": sources, "installed_libraries": libraries,
        "binary": {"path": "root-icu77-nfd.bin", "bytes": binary.stat().st_size, "sha256": digest(binary)},
        "generator_files": [file_record(EXPORT / name, ROOT) for name in ("export-nfd.cpp", "generate_nfd.py", "generate.py")],
        "compiler": subprocess.check_output(compiler + ["--version"], text=True).strip(),
        "determinism": {"independent_export_processes": 2, "binary_equal": True, "runtime_metadata_equal": True},
        "runtime_native_dependency": False,
    }
    save_json(build / "generation-manifest.json", manifest)
    target = output / "root-icu77-nfd.bin"
    if args.check:
        if target.read_bytes() != binary.read_bytes():
            raise ValueError("Regenerated NFD data differs from checked-in data")
    else:
        shutil.copyfile(binary, target)
        save_json(output / "root-icu77-nfd.json", manifest)
    print(json.dumps({"checked": args.check, "binary": manifest["binary"], "runtime": manifest["runtime"]}))


if __name__ == "__main__":
    main()
