#!/usr/bin/env python3
"""Export every packaged ICU77 collation owner and real locale/type/settings data."""

import argparse
import collections
import datetime as dt
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from data_format import read_data
from generate import ROOT, EXPORT, DATA, SOURCE_FILES, digest, file_record, save_json, verify_source
from locale_configurations import default_requests
from locale_format import read_owner, read_scripts, read_settings


SOURCES = tuple(dict.fromkeys(SOURCE_FILES + (
    "source/i18n/coll.cpp", "source/i18n/ucol_res.cpp", "source/i18n/ucol_imp.h",
    "source/i18n/collationtailoring.cpp", "source/i18n/collationtailoring.h",
    "source/i18n/unicode/coll.h", "source/i18n/unicode/tblcoll.h",
    "source/common/locid.cpp", "source/common/uloc.cpp", "source/common/uloc_tag.cpp",
    "source/common/uresbund.cpp", "source/common/uresdata.cpp", "source/common/uresdata.h",
)))
GENERATORS = ("inventory-locales.cpp", "inventory_locales.py", "locale_data.h",
              "locale_resources.h", "locale_format.py", "locale_configurations.py",
              "generate.py", "data_format.py")


def record(path, relative_to=ROOT):
    try:
        name = str(path.relative_to(relative_to))
    except ValueError:
        name = str(path)
    return {"path": name, "bytes": path.stat().st_size, "sha256": digest(path)}


def run_logged(command, output, environment):
    with output.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps([str(arg) for arg in command]) + "\n")
        stream.flush()
        result = subprocess.run([str(arg) for arg in command], env=environment,
                                stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Command exited {result.returncode}; see {output}")


def package_resources(cache, output, environment):
    tool = cache / "install/icu/sbin/icupkg"
    package = cache / "deps/icu/source/data/in/icudt77l.dat"
    result = subprocess.run([str(tool), "-l", str(package)], env=environment,
                            capture_output=True, text=True, check=True)
    (output / "package-list.txt").write_text(result.stdout, encoding="utf-8")
    (output / "package-list.stderr.log").write_text(result.stderr, encoding="utf-8")
    names = sorted(Path(name).stem for name in result.stdout.splitlines()
                   if name.startswith("coll/") and name.endswith(".res") and name != "coll/res_index.res")
    if not names or len(names) != len(set(names)):
        raise ValueError("Empty or ambiguous packaged collation resource names")
    path = output / "resource-locales.txt"
    path.write_text("".join(name + "\n" for name in names), encoding="utf-8")
    return path, {"tool": record(tool), "package": record(package), "resource_count": len(names)}


def validate_data(directory, inventory):
    root = read_data(DATA / "root-icu77.bin")
    exported_root = read_owner(directory / "owner-0000.bin")
    for key, value in exported_root.items():
        if key not in ("sha256", "bytes") and value != root[key]:
            raise ValueError(f"Static ICU root export differs from frozen root data: {key}")
    owners = []
    for owner in inventory["owners"]:
        path = directory / f"owner-{owner['id']:04d}.bin"
        data = read_owner(path)
        for key, actual in (("ce32_ranges", len(data["ce32_ranges"])), ("ce32s", len(data["ce32s"])),
                            ("ces", len(data["ces"])), ("raw_context_units", len(data["raw_contexts"])),
                            ("numeric_primary", data["numeric_primary"])):
            if actual != owner[key]:
                raise ValueError(f"Owner {owner['id']} inventory/binary mismatch: {key}")
        source = DATA / "root-icu77.bin" if owner["id"] == 0 else path
        owners.append({"id": owner["id"], "base": owner["base"],
                       "file": "../root-icu77.bin" if owner["id"] == 0 else path.name,
                       "format": "BRSPRI77" if owner["id"] == 0 else "BRSOWN77",
                       "contexts": len(data["contexts"]),
                       **{key: value for key, value in record(source).items() if key != "path"}})
    settings = []
    for index, expected in enumerate(inventory["settings"]):
        path = directory / f"settings-{index:04d}.bin"
        actual = read_settings(path)
        if any(actual[key] != value for key, value in expected.items() if key != "attributes"):
            raise ValueError(f"Settings {index} inventory/binary mismatch")
        settings.append({"id": index, **record(path, directory)})
    scripts = read_scripts(directory / "scripts.bin")
    for owner in inventory["owners"]:
        for key in ("num_scripts", "scripts_index", "script_starts"):
            if scripts[key] != owner[key]:
                raise ValueError(f"Owner {owner['id']} uses unexported script metadata")
    return owners, settings, record(directory / "scripts.bin", directory)


def generate(args):
    cache = args.cache.resolve()
    output = (args.output or ROOT / "docs/research/assets/icu77-locales/exports" /
              dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%S.%fZ")).resolve()
    destination = args.data_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    build = cache / "build/locale-export"
    build.mkdir(parents=True, exist_ok=True)
    provenance, sources = verify_source(cache, SOURCES)
    prefix = cache / "install/icu"
    libraries = [prefix / "lib" / name for name in ("libicui18n.a", "libicuuc.a", "libicudata.a")]
    environment = dict(os.environ)
    environment.pop("ICU_DATA", None)
    environment["LD_LIBRARY_PATH"] = str(prefix / "lib")
    resource_file, package = package_resources(cache, output, environment)
    extra = set(args.extra_requests.read_text().splitlines()) if args.extra_requests else set()
    requests = sorted(set(default_requests()) | extra)
    request_file = output / "extra-requests.txt"
    request_file.write_text("".join(value + "\n" for value in requests if value), encoding="utf-8")
    compiler = shlex.split(args.cxx)
    executable = build / "inventory-locales"
    command = compiler + ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-DU_STATIC_IMPLEMENTATION",
                          "-I" + str(prefix / "include"), "-I" + str(cache / "deps/icu/source/common"),
                          "-I" + str(cache / "deps/icu/source/i18n"), str(EXPORT / "inventory-locales.cpp"),
                          *map(str, libraries), "-lpthread", "-ldl", "-lm", "-o", str(executable)]
    run_logged(command, output / "build.log", environment)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    runs = []
    for number in (1, 2):
        directory = build / f"export-{number}"
        directory.mkdir(exist_ok=True)
        inventory_path = output / f"inventory-{number}.json"
        result = subprocess.run([str(executable), str(inventory_path), str(resource_file),
                                 str(directory), str(request_file)], env=environment,
                                capture_output=True, text=True)
        (output / f"stdout-{number}.log").write_text(result.stdout, encoding="utf-8")
        (output / f"stderr-{number}.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"Locale exporter exited {result.returncode}; see {output / f'stderr-{number}.log'}")
        runs.append((directory, inventory_path, json.loads(result.stdout)))
    first, inventory_path, counts = runs[0]
    second, second_inventory, second_counts = runs[1]
    if counts != second_counts or inventory_path.read_bytes() != second_inventory.read_bytes():
        raise ValueError("Independent locale inventories differ")
    inventory = json.loads(inventory_path.read_text())
    owners, settings, scripts = validate_data(first, inventory)
    generated_files = ([item["file"] for item in owners if item["id"] != 0] +
                       [item["path"] for item in settings] + [scripts["path"]])
    for name in generated_files + ["owner-0000.bin"]:
        if (first / name).read_bytes() != (second / name).read_bytes():
            raise ValueError(f"Independent locale exports differ: {name}")
    catalog = {**inventory, "schema": "boostregexrs.icu77-locale-catalog.v1",
               "owner_files": owners, "settings_files": settings, "scripts_file": scripts,
               "root_fcd_shared": True,
               "representation_scope": "Complete packaged collation owners and raw resource metadata; enumerated request outcomes are diagnostics, not an arbitrary locale parser"}
    catalog_path = output / "catalog.json"
    save_json(catalog_path, catalog)
    if args.check:
        for name in generated_files:
            if (destination / name).read_bytes() != (first / name).read_bytes():
                raise ValueError(f"Regenerated locale data differs: {destination / name}")
        if (destination / "catalog.json").read_bytes() != catalog_path.read_bytes():
            raise ValueError("Regenerated locale catalog differs")
    else:
        destination.mkdir(parents=True, exist_ok=True)
        for name in generated_files:
            shutil.copyfile(first / name, destination / name)
        shutil.copyfile(catalog_path, destination / "catalog.json")
    metadata = {
        "schema": "boostregexrs.icu77-locale-generation.v1",
        "started_utc": started, "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope": "Complete packaged locale/type owner data export; no arbitrary-string compatibility claim",
        "counts": counts, "checked_existing_data": args.check,
        "observed_options": sorted({row["options"] for row in inventory["settings"]}),
        "request_statuses": dict(collections.Counter(row["public_status"] for row in inventory["requests"])),
        "request_outcomes": dict(collections.Counter(row["status"] for row in inventory["requests"])),
        "determinism": {"independent_processes": 2, "all_binary_bytes_equal": True, "inventory_equal": True},
        "source": provenance, "source_files": sources, "packaged_resources": package,
        "installed_static_libraries": [file_record(path, prefix) for path in libraries],
        "static_library_identity_scope": "Recorded for this export; root tables cross-checked with frozen shared-library root data",
        "compiler": subprocess.check_output(compiler + ["--version"], text=True).strip(),
        "generator_files": [file_record(EXPORT / name, ROOT) for name in GENERATORS],
        "executable": record(executable), "catalog": record(catalog_path),
        "raw_inventories": [record(path) for _, path, _ in runs],
        "raw_resource_alias_substitution": False,
        "public_private_default_settings_cross_checked": True,
        "effective_keyword_settings": "Official public attributes/reorderCodes applied with official ICU CollationSettings setters",
        "frozen_root_tables_equal": True, "root_data_modified": False,
        "host_unicode_database_used": False, "candidate_runtime_native_dependency": False,
    }
    save_json(output / "summary.json", metadata)
    print(json.dumps({"counts": counts, "request_outcomes": metadata["request_outcomes"],
                      "data": str(destination), "evidence": str(output), "catalog_sha256": digest(catalog_path)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "target/research/icu77-cloud")
    parser.add_argument("--output", type=Path, help="evidence directory (default: new dated docs/research/assets/icu77-locales/exports directory)")
    parser.add_argument("--data-directory", type=Path, default=DATA / "locales")
    parser.add_argument("--extra-requests", type=Path, help="additional ICU locale IDs, one per line")
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    parser.add_argument("--check", action="store_true", help="compare against existing data without replacing it")
    generate(parser.parse_args())


if __name__ == "__main__":
    main()
