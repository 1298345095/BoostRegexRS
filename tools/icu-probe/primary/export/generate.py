#!/usr/bin/env python3
"""Build the ICU77 development exporter and verify deterministic root data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile

from data_format import context_report, read_data


ROOT = Path(__file__).resolve().parents[4]
EXPORT = Path(__file__).resolve().parent
DATA = EXPORT.parent / "data"
ICU_ARCHIVE = "icu4c-77_1-src.tgz"
ICU_BASE = "https://github.com/unicode-org/icu/releases/download/release-77-1/"
ICU_SHA512 = (
    "a47d6d9c327d037a05ea43d1d1a06b2fd757cc02a94f7c1a238f35cfc3dfd4ab78d061"
    "2790f3a3cca0292c77412a9c2c15c8f24b718f79a857e007e66f07e7cd"
)
SOURCE_FILES = (
    "LICENSE",
    "source/common/unicode/uvernum.h",
    "source/common/normalizer2impl.cpp",
    "source/common/normalizer2impl.h",
    "source/common/ucharstrie.cpp",
    "source/common/ucharstrieiterator.cpp",
    "source/common/unicode/ucharstrie.h",
    "source/common/utrie2.h",
    "source/data/in/icudt77l.dat",
    "source/data/in/nfc.nrm",
    "source/i18n/collation.cpp",
    "source/i18n/collation.h",
    "source/i18n/collationdata.cpp",
    "source/i18n/collationdata.h",
    "source/i18n/collationdatareader.cpp",
    "source/i18n/collationiterator.cpp",
    "source/i18n/collationiterator.h",
    "source/i18n/collationkeys.cpp",
    "source/i18n/collationkeys.h",
    "source/i18n/collationroot.cpp",
    "source/i18n/collationroot.h",
    "source/i18n/collationsettings.cpp",
    "source/i18n/collationsettings.h",
    "source/i18n/rulebasedcollator.cpp",
    "source/i18n/utf16collationiterator.cpp",
    "source/i18n/utf16collationiterator.h",
)


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def file_record(path: Path, relative_to: Path) -> dict:
    return {
        "path": str(path.relative_to(relative_to)),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def verify_source(cache: Path) -> tuple[dict, list[dict]]:
    archive = cache / "downloads" / ICU_ARCHIVE
    checksum_manifest = cache / "downloads" / "SHASUM512.txt"
    archive_hash = digest(archive, "sha512")
    if archive_hash != ICU_SHA512:
        raise ValueError("ICU release archive does not match the pinned official SHA-512")
    published = None
    for line in checksum_manifest.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip("*") == ICU_ARCHIVE:
            published = fields[0]
    if published != archive_hash:
        raise ValueError("ICU release archive does not match the downloaded official manifest")

    # Compare the relevant extracted algorithm/data files with their bytes in
    # the verified archive. A modified development source is not silently accepted.
    source_records = []
    with tarfile.open(archive, "r:gz") as release:
        for name in SOURCE_FILES:
            path = cache / "deps" / "icu" / name
            archived = release.extractfile("icu/" + name)
            if archived is None or archived.read() != path.read_bytes():
                raise ValueError(f"extracted ICU source differs from its release archive: {name}")
            source_records.append(file_record(path, cache / "deps" / "icu"))
    return {
        "archive_url": ICU_BASE + ICU_ARCHIVE,
        "checksum_manifest_url": ICU_BASE + "SHASUM512.txt",
        "algorithm": "sha512",
        "published_digest": published,
        "actual_digest": archive_hash,
        "published_digest_matches": True,
        "detached_signature_verified": False,
        "checksum_manifest_sha256": digest(checksum_manifest),
        "archive_sha256": digest(archive),
        "extracted_source_files_match_archive": True,
    }, source_records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "target/research/icu77-cloud")
    parser.add_argument("--output-directory", type=Path, default=DATA)
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    parser.add_argument(
        "--check", action="store_true",
        help="require generated binary to match the checked-in output; never replace it",
    )
    args = parser.parse_args()
    cache = args.cache.resolve()
    output = args.output_directory.resolve()
    build = cache / "build/primary-export"
    build.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    source_provenance, source_records = verify_source(cache)

    prefix = cache / "install/icu"
    library_directory = prefix / "lib"
    source = cache / "deps/icu/source"
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(library_directory)
    environment.pop("ICU_DATA", None)

    library_records = [
        file_record(library_directory / name, prefix)
        for name in ("libicui18n.so.77.1", "libicuuc.so.77.1", "libicudata.so.77.1")
    ]
    prepared = json.loads((cache / "environment-manifest.json").read_text(encoding="utf-8"))
    recorded_libraries = {
        Path(item["path"]).name: item["sha256"] for item in prepared["installed_libraries"]
    }
    for record in library_records:
        if recorded_libraries.get(Path(record["path"]).name) != record["sha256"]:
            raise ValueError("ICU installed library differs from the prepared reference environment")

    executable = build / "export-root"
    compiler = shlex.split(args.cxx)
    common_flags = [
        "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I" + str(prefix / "include"),
        "-I" + str(source / "common"),
        "-I" + str(source / "i18n"),
    ]
    link_flags = [
        "-L" + str(library_directory),
        "-Wl,-rpath," + str(library_directory),
        "-licui18n", "-licuuc", "-licudata",
    ]
    with (build / "build.log").open("w", encoding="utf-8") as log:
        for program in ("export-root", "trace-root"):
            command = compiler + common_flags + [str(EXPORT / (program + ".cpp"))] + link_flags
            command += ["-o", str(build / program)]
            subprocess.run(command, check=True, env=environment, stdout=log, stderr=subprocess.STDOUT)
    compiler_version = subprocess.check_output(compiler + ["--version"], text=True).strip()
    outputs = []
    for run in (1, 2):
        binary = build / f"root-{run}.bin"
        runtime_json = build / f"root-{run}.json"
        result = subprocess.run(
            [str(executable), str(binary), str(runtime_json)], check=True, env=environment,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        (build / f"export-{run}.log").write_text(result.stdout, encoding="utf-8")
        print(result.stdout, end="")
        outputs.append((binary, runtime_json))
    first_binary, first_runtime = outputs[0]
    second_binary, second_runtime = outputs[1]
    if first_binary.read_bytes() != second_binary.read_bytes():
        raise ValueError("independent ICU77 data exports produced different binary bytes")
    if first_runtime.read_bytes() != second_runtime.read_bytes():
        raise ValueError("independent ICU77 data exports produced different runtime metadata")

    data = read_data(first_binary)
    save_json(build / "root-contexts.json", context_report(data))
    runtime = json.loads(first_runtime.read_text(encoding="utf-8"))
    manifest = {
        "schema": "boostregexrs.icu77-root-data.v1",
        "scope": "complete root CE data for PRIMARY prototype; no test-input sort keys",
        "runtime": runtime,
        "binary": {"path": "root-icu77.bin", "bytes": data["bytes"], "sha256": data["sha256"]},
        "determinism": {"independent_export_processes": 2, "binary_equal": True,
                        "runtime_metadata_equal": True},
        "source": source_provenance,
        "source_files": source_records,
        "generator_files": [file_record(EXPORT / name, ROOT)
                            for name in ("export-root.cpp", "trace-root.cpp", "generate.py", "data_format.py")],
        "compiler": compiler_version,
        "installed_libraries": library_records,
        "generation": {
            "normalization": "root default OFF; input canonical closure preserved",
            "representation_changes": ["CE32 and FCD16 tries converted to value ranges",
                                       "UCharsTrie contexts additionally enumerated without truncation"],
            "icu_data_filter": None,
            "icu_runtime_in_rust": False,
        },
    }
    save_json(build / "generation-manifest.json", manifest)
    target = output / "root-icu77.bin"
    if args.check:
        if not target.exists() or target.read_bytes() != first_binary.read_bytes():
            raise ValueError(f"generated binary differs from {target}; output was not replaced")
        license_path = output / "LICENSE-ICU.txt"
        if license_path.read_bytes() != (cache / "deps/icu/LICENSE").read_bytes():
            raise ValueError("checked-in ICU license differs from the source release")
        print(f"PASS: checked-in data matches both exports ({data['bytes']} bytes, {data['sha256']})")
    else:
        shutil.copyfile(first_binary, target)
        shutil.copyfile(cache / "deps/icu/LICENSE", output / "LICENSE-ICU.txt")
        save_json(output / "root-icu77.json", manifest)
        print(f"generated {target} ({data['bytes']} bytes, {data['sha256']})")


if __name__ == "__main__":
    main()
