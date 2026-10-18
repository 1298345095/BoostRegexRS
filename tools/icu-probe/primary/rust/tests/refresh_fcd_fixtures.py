#!/usr/bin/env python3
"""Rebuild ICU77 FCD references, or restore the archived cursor-only A fixtures.

This v2 generator was reconstructed after workspace maintenance removed v1's
unpublished script/fixtures. It retains the six exact historical inputs and the
source-defined coverage classes/seed; it makes no byte-equality claim for the
lost generated inputs. Native references are always computed independently.
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

TESTS = Path(__file__).resolve().parent
PRIMARY = TESTS.parents[1]
REPO = PRIMARY.parents[2]
HISTORY = REPO / "docs/research/assets/icu77-locales/diagnostics"
SEED = 0x0042494355464344
FLAG_SHA256 = "11fa8680ed9a86ccfaf71bc286b7790226e2d129b3b5548ba376589a01bc4b24"
PROFILES = (
    ("root-off", "root", False, False),
    ("root-on", "root@colNormalization=yes", False, True),
    ("fo-off", "fo@collation=search;colNormalization=no", True, False),
    ("fo-on", "fo@collation=search", True, True),
)

sys.path.insert(0, str(PRIMARY / "export"))
from data_format import codepoints, read_data  # noqa: E402
from generate import SOURCE_FILES, verify_source  # noqa: E402


def identity(path):
    path = Path(path).resolve()
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return {"path": os.path.relpath(path, REPO), "bytes": path.stat().st_size,
            "sha256": hasher.hexdigest()}


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def read_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_rows(path, fields, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def historical_inputs():
    # Preserve archived UTF-16 order, including the independently recorded NFD
    # controls. Decoding pairs here does not normalize or reorder the input.
    return [
        (row["case_id"], codepoints([int(unit, 16) for unit in row["u16_hex"].split(",") if unit]))
        for name in ("fo-search-fcd-cursor", "fo-search-fcd-reduced")
        for row in read_rows(HISTORY / name / "input-u16.tsv")
    ]


def input_rows(cases):
    rows = []
    for name, scalars in cases:
        units = []
        for cp in scalars:
            if cp < 0x10000:
                units.append(cp)
            else:
                units.extend((0xd800 + ((cp - 0x10000) >> 10), 0xdc00 + ((cp - 0x10000) & 1023)))
        rows.append({"case_id": name, "u16_hex": ",".join(f"{unit:04x}" for unit in units)})
    return rows


def splitmix64(seed):
    mask = (1 << 64) - 1
    while True:
        seed = (seed + 0x9e3779b97f4a7c15) & mask
        value = seed
        value = ((value ^ (value >> 30)) * 0xbf58476d1ce4e5b9) & mask
        value = ((value ^ (value >> 27)) * 0x94d049bb133111eb) & mask
        yield value ^ (value >> 31)


def generated_inputs():
    data = read_data(PRIMARY / "data/root-icu77.bin")
    points = {0x10000, 0x10ffff}
    blocks = set()
    start = 0
    for end, fcd in data["fcd16_ranges"]:
        if fcd and end >= 0x10000:
            first = max(start, 0x10000)
            points.update(point + delta for point in (first, end) for delta in (-1, 0, 1)
                          if 0x10000 <= point + delta <= 0x10ffff)
            blocks.update(range(first >> 10, (end >> 10) + 1))
        start = end + 1
    # Conservative lead-surrogate guards summarize these 1,024-scalar blocks.
    for block in blocks:
        points.update((block << 10, (block << 10) + 1023))
    cases = historical_inputs() + [("empty", []), ("nul", [0]),
                                   ("embedded-nul", [0xe9, 0, 0x1d165, 0x323]),
                                   ("merge", [0xe9, 0xfffe, 0x1d165, 0x327])]
    for cp in sorted(points):
        for mark in (0x323, 0x327):
            cases.append((f"fcd/boundary-{cp:06x}-{mark:04x}", [0xe9, cp, mark]))
    for cp in range(0x0f00, 0x1000):
        if cp & 0xff01 == 0x0f01:
            cases.append((f"fcd/tibetan-{cp:04x}", [0xe9, cp, 0x323, 0x327]))
    prefixes = ([], [0x6c, 0xb7], [0x438], [0x6c, 0xb7, 0x438])
    marks = ((0x301, 0x323), (0x323, 0x301), (0x327, 0x306),
             (0x306, 0x327), (0x301, 0x301), (0x315, 0x300))
    for prefix_index, prefix in enumerate(prefixes):
        for mark_index, suffix in enumerate(marks):
            cases.append((f"fcd/context-{prefix_index}-{mark_index}",
                          [*prefix, 0xe9, 0x1d165, *suffix, 0x438, 0x327, 0x306]))
    fragments = ((0xe9,), (0x65, 0x301), (0x6c, 0xb7), (0x438,), (0,), (0xfffe,),
                 (0x1d165,), (0x1d166,), (0x301,), (0x323,), (0x327,), (0x306,),
                 (0x315, 0x300), (0x345,), (0xf73,), (0xf75,), (0x4e00,), (0xac00,),
                 (0x1f600,), (0x10ffff,))
    random = splitmix64(SEED)
    for index in range(512):
        scalars = []
        for _ in range(1 + next(random) % 12):
            scalars.extend(fragments[next(random) % len(fragments)])
        cases.append((f"fcd/generated-{index:04d}", scalars))
    rows = input_rows(cases)
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("FCD fixture identifiers must be unique")
    return rows, {"algorithm": "SplitMix64", "seed": f"0x{SEED:016x}", "generated_inputs": 512,
                  "input_count": len(rows), "distinct_input_count": len({row["u16_hex"] for row in rows}),
                  "supplementary_boundary_points": len(points), "host_unicode_database_used": False,
                  "reference_keys_used_to_choose_inputs": False, "generator_revision": 2}


def install_fixtures(output, filenames):
    destination = TESTS / "data/fcd77"
    destination.mkdir(parents=True, exist_ok=True)
    for name in (*filenames, "provenance.json"):
        shutil.copyfile(output / name, destination / name)


def restore_history(output, update):
    if update and (TESTS / "data/fcd77/native-keys-ces.tsv").exists():
        raise ValueError("Cursor-only recovery cannot replace a complete key fixture set")
    rows = input_rows(historical_inputs())
    write_rows(output / "inputs-u16.tsv", ("case_id", "u16_hex"), rows)
    sources = ("fo-search-fcd-cursor", "fo-search-fcd-reduced")
    original_inputs = [HISTORY / name / "input-u16.tsv" for name in sources]
    if rows != [row for path in original_inputs for row in read_rows(path)]:
        raise ValueError("Historical UTF-16 inputs did not round-trip byte order unchanged")
    originals = [HISTORY / name / "native-fcd.tsv" for name in sources]
    cursor = [row for path in originals for row in read_rows(path)]
    if list(dict.fromkeys(row["case_id"] for row in cursor)) != [row["case_id"] for row in rows]:
        raise ValueError("Archived cursor inputs do not match the six historical cases")
    write_rows(output / "native-cursor.tsv", ("case_id", "direction", "index", "code_point_hex", "utf16_offset_after", "terminal"), cursor)
    original_flags = HISTORY / "fcd-unit-flags/native-fcd-flags.bin"
    if identity(original_flags)["sha256"] != FLAG_SHA256:
        raise ValueError("Archived native flags no longer match their recorded digest")
    shutil.copyfile(original_flags, output / "native-flags.bin")
    filenames = ("inputs-u16.tsv", "native-cursor.tsv", "native-flags.bin")
    save(output / "provenance.json", {
        "schema": "boostregexrs.icu77-fcd-history-fixtures.v1", "status": "historical_cursor_subset_only",
        "input_count": len(rows), "cursor_rows": len(cursor), "native_execution_performed": False,
        "generator": identity(Path(__file__)),
        "archived_sources": [identity(path) for path in (*original_inputs, *originals, original_flags)],
        "fixtures": [identity(output / name) for name in filenames],
        "not_covered": ["full native key/CE fixture regeneration", "new Rust execution after recovery"],
    })
    if update:
        install_fixtures(output, filenames)
    print(json.dumps({"output": str(output), "historical_inputs": len(rows), "cursor_rows": len(cursor)}), flush=True)


def run(args):
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%S.%fZ")
    output = (args.output or REPO / "docs/research/assets/icu77-locales/fcd-repair" / stamp).resolve()
    output.mkdir(parents=True, exist_ok=False)
    if args.historical_only:
        restore_history(output, args.update_fixtures)
        return
    cache = args.cache.resolve()
    build = cache / "build/fcd-fixtures" / output.name
    build.mkdir(parents=True, exist_ok=False)
    prefix = cache / "install/icu"
    environment = dict(os.environ)
    environment.pop("ICU_DATA", None)
    environment["LD_LIBRARY_PATH"] = str(prefix / "lib")
    source, source_files = verify_source(cache, SOURCE_FILES + (
        "source/i18n/ucol_imp.h", "source/i18n/ucol_res.cpp", "source/i18n/collationfcd.h", "source/i18n/collationfcd.cpp"))
    save(output / "source.json", {"source": source, "source_files": source_files})
    commands = []

    def execute(command, label, *, input_path=None, seconds=120):
        argv = ["timeout", "--signal=TERM", "--kill-after=5s", f"{seconds}s", *map(str, command)]
        print(shlex.join(argv), flush=True)
        target = output / label
        errors = target.with_suffix(target.suffix + ".stderr.log")
        started = time.monotonic()
        with target.open("wb") as stdout, errors.open("wb") as stderr:
            with (input_path or Path(os.devnull)).open("rb") as stdin:
                result = subprocess.run(argv, cwd=REPO, env=environment, stdin=stdin, stdout=stdout, stderr=stderr,
                                        timeout=seconds + 10, check=False)
        commands.append({"argv": argv, "exit_code": result.returncode, "seconds": time.monotonic() - started,
                         "stdout": identity(target), "stderr": identity(errors),
                         "environment": {key: environment.get(key) for key in ("LD_LIBRARY_PATH", "ICU_DATA")}})
        save(output / "commands.json", commands)
        if result.returncode:
            raise RuntimeError(f"Native command exited {result.returncode}: {errors}")
        return target

    compiler = shlex.split(args.cxx)
    flags = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", prefix / "include"]
    libraries = [prefix / "lib" / name for name in ("libicui18n.a", "libicuuc.a", "libicudata.a")]
    for name in ("trace-fcd", "trace-locale"):
        execute([*compiler, *flags, "-DU_STATIC_IMPLEMENTATION", "-I", cache / "deps/icu/source/common",
                 "-I", cache / "deps/icu/source/i18n", PRIMARY / "export" / f"{name}.cpp", *libraries,
                 "-lpthread", "-ldl", "-lm", "-o", build / name], f"build-{name}.log", seconds=180)
    execute([*compiler, *flags, "-I", cache / "deps/boost_1_89_0", PRIMARY / "oracle.cpp",
             "-L", prefix / "lib", "-Wl,-rpath," + str(prefix / "lib"), "-licui18n", "-licuuc", "-licudata",
             "-o", build / "oracle"], "build-oracle.log", seconds=180)
    execute([*compiler, "--version"], "compiler.txt", seconds=20)
    rows, generation = generated_inputs()
    inputs = output / "inputs-u16.tsv"
    write_rows(inputs, ("case_id", "u16_hex"), rows)
    execute([build / "trace-fcd", "--fcd-flags"], "native-flags.bin", seconds=20)
    if identity(output / "native-flags.bin")["sha256"] != FLAG_SHA256:
        raise ValueError("Regenerated native FCD flags differ from preserved ICU77 flags")
    execute([build / "trace-fcd", "fo@collation=search"], "native-cursor.tsv", input_path=inputs, seconds=60)
    combined = []
    for profile, locale, tailored, normalization in PROFILES:
        ces_file = execute([build / "trace-locale", locale], f"{profile}-ces.tsv", input_path=inputs, seconds=60)
        ces = read_rows(ces_file)
        for strength in ("primary", "identical"):
            name = f"{profile}-{strength}"
            metadata = output / f"{name}-metadata.json"
            command = [build / "oracle", "--input-format", "u16", "--locale", locale,
                       "--strength", strength, "--metadata", metadata]
            if strength == "identical":
                command.append("--approved-empty-exception")
            keys_file = execute(command, f"{name}-keys.tsv", input_path=inputs, seconds=60)
            runtime = json.loads(metadata.read_text())
            for key, expected in (("boost", "1.89.0"), ("icu", "77.1"), ("unicode", "16.0.0"), ("cldr", "47.0")):
                if runtime[key] != expected:
                    raise ValueError(f"Native {key} version differs: {runtime[key]}")
            if runtime["attributes"]["normalization"] != (17 if normalization else 16):
                raise ValueError(f"Native FCD setting differs: {profile}")
            for case, key, ce in zip(rows, read_rows(keys_file), ces, strict=True):
                if not case["case_id"] == key["case_id"] == ce["case_id"]:
                    raise ValueError("Native reference row order differs")
                if any("ERROR" in value for value in (*key.values(), ce["ces64_hex"])):
                    raise ValueError(f"Native reference error: {name}/{case['case_id']}")
                combined.append({"profile": profile, "strength": strength, **case, **key, "ces64_hex": ce["ces64_hex"]})
    write_rows(output / "native-keys-ces.tsv", ("profile", "strength", "case_id", "u16_hex", "raw_icu_hex", "boost_u32_hex", "ces64_hex"), combined)
    filenames = ("inputs-u16.tsv", "native-flags.bin", "native-cursor.tsv", "native-keys-ces.tsv")
    save(output / "provenance.json", {
        "schema": "boostregexrs.icu77-fcd-fixtures.v2", "source": source, "generation": generation,
        "recovery": "v1 generated rows/logs were pruned; this reconstructed generator and fresh native outputs have independent identities",
        "profiles": [{"id": name, "locale": locale, "owner": 43 if tailored else 0, "normalization": normalization}
                     for name, locale, tailored, normalization in PROFILES],
        "approved_empty_keys": 4, "ordinary_key_rows": len(combined) - 4,
        "scope": "Native reference fixtures only; Rust acceptance is recorded separately",
        "generator": identity(Path(__file__)), "output": str(output.relative_to(REPO)),
        "historical_inputs": [identity(HISTORY / name / "input-u16.tsv")
                              for name in ("fo-search-fcd-cursor", "fo-search-fcd-reduced")],
        "fixtures": [identity(output / name) for name in filenames],
        "executables": [identity(build / name) for name in ("trace-fcd", "trace-locale", "oracle")],
        "data": [identity(PRIMARY / "data" / name) for name in ("root-icu77.bin", "root-icu77-nfd.bin", "locales/owner-0043.bin", "locales/settings-0001.bin")],
        "native_sources": [identity(PRIMARY / name) for name in ("oracle.cpp", "export/trace-fcd.cpp", "export/trace-locale.cpp")],
        "static_libraries": [identity(path) for path in libraries],
        "reference_environment": identity(cache / "environment-manifest.json"),
    })
    if args.update_fixtures:
        install_fixtures(output, filenames)
    print(json.dumps({"output": str(output), "inputs": len(rows), "complete_keys": len(combined)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=REPO / "target/research/icu77-cloud")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    parser.add_argument("--update-fixtures", action="store_true")
    parser.add_argument("--historical-only", action="store_true", help="restore only archived cursor/flag evidence; does not generate key expectations")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
