#!/usr/bin/env python3
"""Compare complete ICU77/Boost keys for every exported owner/settings combination.

The candidate receives source data and effective settings, not a locale-to-key
lookup. Locale ID parsing is recorded as an unexercised, separate capability.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import importlib.util
import itertools
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import sys

from compare import compare, rows, sha256
from generate_cases import SEED, contexts, directed, historical, input_boundaries, write_cases
from reference_process import run_reference
from run import PRIMARY, REPO

sys.path.insert(0, str(PRIMARY / "export"))
from data_format import context_report, read_data  # noqa: E402
from locale_format import read_owner  # noqa: E402
sys.path.insert(0, str(PRIMARY.parent / "cloud"))
from prepare import run_logged  # noqa: E402


def save(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def bounded(command, seconds):
    return ["timeout", "--signal=TERM", "--kill-after=5s", f"{seconds}s", *map(str, command)]


def identity(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def source_data_identity(data_directory, catalog):
    records = []
    for item in catalog["owner_files"]:
        path = PRIMARY / "data/root-icu77.bin" if item["id"] == 0 else data_directory / item["file"]
        actual = identity(path)
        if actual["sha256"] != item["sha256"]:
            raise ValueError("Owner data differs from the frozen catalog")
        records.append(actual)
    for item in catalog["settings_files"]:
        actual = identity(data_directory / item["path"])
        if actual["sha256"] != item["sha256"]:
            raise ValueError("Effective settings differ from the frozen catalog")
        records.append(actual)
    records.append(identity(PRIMARY / "data/root-icu77-nfd.bin"))
    scripts = identity(data_directory / catalog["scripts_file"]["path"])
    if scripts["sha256"] != catalog["scripts_file"]["sha256"]:
        raise ValueError("Script metadata differs from the frozen catalog")
    records.append(scripts)
    return records


def configuration_id(configuration):
    return f"owner-{configuration['owner']:04d}-settings-{configuration['settings']:04d}"


def configurations(catalog):
    grouped = {}
    for row in catalog["requests"]:
        if row["status"] == "loaded":
            grouped.setdefault((row["owner"], row["settings"]), []).append(row)
    result = []
    for (owner, settings), aliases in sorted(grouped.items()):
        selected = min(aliases, key=lambda row: (row["requested"] != "root", len(row["requested"]), row["requested"]))
        result.append({"owner": owner, "settings": settings, "locale": selected["requested"],
                       "source_request": selected,
                       "equivalent_exported_requests": [row["requested"] for row in aliases]})
    return result


def mechanism_module():
    path = PRIMARY / "rust/tests/locale_cases.py"
    specification = importlib.util.spec_from_file_location("icu77_locale_cases", path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module, path


def prepare_inputs(output, generated_count):
    directory = output / "inputs"
    directory.mkdir()
    module, generator = mechanism_module()
    common = directory / "common-utf8.tsv"
    values = list(itertools.chain(historical(), module.directed(), module.generated(generated_count, SEED)))
    if len({name for name, _ in values}) != len(values):
        raise ValueError("Duplicate common input identity")
    count = write_cases(common, values)
    inputs = {"common": {"path": common, "kind": "utf8", "count": count}}
    for kind in ("u16", "u32"):
        converted = []
        for name, value in values:
            if kind == "u32":
                units = list(map(ord, value))
            else:
                encoded = value.encode("utf-16-le")
                units = [int.from_bytes(encoded[i:i + 2], "little") for i in range(0, len(encoded), 2)]
            converted.append((name, units))
        write_cases(directory / f"common-{kind}.tsv", converted, kind)
        boundary_cases = list(input_boundaries(kind))
        write_cases(directory / f"boundaries-{kind}.tsv", boundary_cases, kind)
        path = directory / f"all-{kind}.tsv"
        count = write_cases(path, itertools.chain(converted, boundary_cases), kind)
        inputs[kind] = {"path": path, "kind": kind, "count": count}
    empty = directory / "original-empty-utf8.tsv"
    write_cases(empty, [("original-empty", "")])
    origins = directory / "identical-expectation-origins.tsv"
    with origins.open("w", encoding="utf-8") as stream:
        stream.write("case_id\texpectation_source\n")
        for row in rows(common, ("case_id", "utf8_hex")):
            source = "adr0005_valid_pointer_empty" if not row["utf8_hex"] else "original_boost_call"
            stream.write(f"{row['case_id']}\t{source}\n")
    save(directory / "generation.json", {
        "schema": "boostregexrs.icu77-locales-inputs.v2", "seed": f"0x{SEED:016x}",
        "random_algorithm": "SplitMix64", "generated_count": generated_count,
        "host_unicode_database_used": False, "reference_keys_used_to_choose_inputs": False,
        "width_coverage": "Every common input is encoded unchanged as UTF-8, UTF-16 and UTF-32; malformed width boundaries are appended separately",
        "unicode_normalization_performed": False, "common_inputs_per_width": len(values),
        "generator": identity(generator),
        "inputs": {name: {**record, "path": str(record["path"]), "sha256": sha256(record["path"])} for name, record in inputs.items()},
        "identical_expectation_origins": identity(origins),
    })
    return inputs, empty


def owner_scalars(owner, data):
    start = 0
    for end, ce32 in data["ce32_ranges"]:
        if owner == 0 or ce32 != 0xC0:
            for codepoint in range(start, end + 1):
                if not 0xD800 <= codepoint <= 0xDFFF:
                    yield f"owner_scalar/{codepoint:06x}", chr(codepoint)
        else:
            for codepoint in sorted({start, end}):
                if not 0xD800 <= codepoint <= 0xDFFF:
                    yield f"fallback_boundary/{codepoint:06x}", chr(codepoint)
        start = end + 1


def owner_context_report(data):
    """Resolve public DIGIT/NUL indirections before enumerating context tries.

    ICU77 collationiterator.cpp continues dispatch after DIGIT_TAG (numeric
    OFF) and U0000_TAG, whereas EXPANSION32 elements are terminal simple CEs.
    Jamo dispatch keeps the original Hangul scalar at the text cursor. Retain
    that scalar as the input anchor when a special owner Jamo reaches context.
    """
    report = context_report(data)
    known = {(row["codepoint"], row["ce32"]) for row in report["triggers"]}

    def context_value(ce32):
        seen = set()
        while (ce32 & 255) >= 0xC0 and (ce32 & 15) in (10, 11):
            if ce32 in seen:
                raise ValueError("Cycle in digit/NUL owner CE32 indirections")
            seen.add(ce32)
            index = ce32 >> 13 if (ce32 & 15) == 10 else 0
            ce32 = data["ce32s"][index]
        return ce32 if (ce32 & 255) >= 0xC0 and (ce32 & 15) in (8, 9) else None

    start = 0
    for end, original in data["ce32_ranges"]:
        tag = original & 15 if (original & 255) >= 0xC0 else -1
        if tag in (10, 11, 12):
            for cp in range(start, end + 1):
                if tag == 12:
                    if original & 0x100:  # HANGUL_NO_SPECIAL_JAMO
                        continue
                    leading_vowel, trailing = divmod(cp - 0xAC00, 28)
                    leading, vowel = divmod(leading_vowel, 21)
                    indexes = [leading, 19 + vowel] + ([39 + trailing] if trailing else [])
                    values = [context_value(data["jamo_ce32s"][index]) for index in indexes]
                else:
                    values = [context_value(original)]
                for value in values:
                    if value is not None and (cp, value) not in known:
                        known.add((cp, value))
                        report["triggers"].append({"codepoint": cp, "ce32": value, "tag": value & 15,
                                                   "flags": value & 0x1F00, "context_index": value >> 13,
                                                   "original_ce32": original, "indirect_tag": tag})
        start = end + 1
    return report


def owner_inputs(output, owner, data_directory, catalog):
    path = output / "inputs" / f"owner-{owner:04d}-utf8.tsv"
    source = PRIMARY / "data/root-icu77.bin" if owner == 0 else data_directory / catalog["owner_files"][owner]["file"]
    data = read_data(source) if owner == 0 else read_owner(source)
    report = path.with_suffix(".contexts.json")
    exported = owner_context_report(data)
    save(report, exported)
    covered = {item["index"]: set() for item in exported["contexts"]}
    categories = {}

    def recording_contexts():
        for name, value in contexts(report):
            category, label = name.split("/", 1)
            categories[category] = categories.get(category, 0) + 1
            if category == "context":
                _, index, entry, _ = label.split("-")
                covered[int(index)].add(int(entry))
            yield name, value

    # ICU77 CollationIterator::appendCEsFromCE32 handles all 11,172 Hangul
    # syllables with the selected owner's 67 Jamo CE32s. Exercise those source
    # decompositions for every owner, including owners sharing root Jamo data.
    algorithm_cases = ((name, value) for name, value in directed()
                       if name.startswith(("long/", "hangul_jamo/")))
    count = write_cases(path, itertools.chain(owner_scalars(owner, data), recording_contexts(), algorithm_cases))
    coverage = {
        "schema": "boostregexrs.icu77-owner-input-coverage.v1", "owner": owner,
        "owner_data": identity(source), "base_owner": catalog["owners"][owner]["base"],
        "jamo_shares_base": catalog["owners"][owner]["jamo_shares_base"],
        "jamo_ce32s": data["jamo_ce32s"], "hangul_jamo_inputs": 11172,
        "scalar_policy": "all root scalars; every non-fallback owner scalar; both scalar endpoints of fallback ranges",
        "context_report": identity(report), "context_cases_by_category": categories,
        "contexts": [{"index": item["index"], "expected_entries": len(item["entries"]),
                      "covered_entries": sorted(covered[item["index"]])} for item in exported["contexts"]],
        "uncovered_context_entries": [{"index": item["index"], "entry": entry}
                                      for item in exported["contexts"] for entry in range(len(item["entries"]))
                                      if entry not in covered[item["index"]]],
        "inputs": identity(path), "input_count": count,
    }
    save(path.with_suffix(".coverage.json"), coverage)
    if coverage["uncovered_context_entries"]:
        raise ValueError(f"Owner {owner} has exported context entries not reached by generated inputs")
    return {"path": path, "kind": "utf8", "count": count}


def commands(configuration, strength, kind, oracle, candidate, data_directory, catalog):
    reference = [oracle, "--locale", configuration["locale"], "--strength", strength, "--input-format", kind]
    if strength == "identical":
        reference.append("--approved-empty-exception")
    actual = [candidate, "--settings", data_directory / catalog["settings_files"][configuration["settings"]]["path"],
              "--strength", strength, "--input-format", kind,
              "--data", PRIMARY / "data/root-icu77.bin", "--nfd-data", PRIMARY / "data/root-icu77-nfd.bin"]
    if configuration["owner"]:
        actual += ["--owner", data_directory / catalog["owner_files"][configuration["owner"]]["file"]]
    return reference, actual


def check_metadata(metadata, settings, strength):
    expected = {**settings["attributes"], "strength": 0 if strength == "primary" else 15}
    if any(metadata["attributes"][key] != value for key, value in expected.items()):
        raise ValueError("Native locale attributes differ from the exported effective settings")
    if metadata["variable_top"] != settings["variable_top"] or metadata["reorder_codes"] != settings["reorder_codes"]:
        raise ValueError("Native variableTop/reorderCodes differ from exported settings")


def run_group(output, phase, configuration, strength, inputs, oracle, candidate, data_directory,
              catalog, native_environment, rust_environment, timeout_seconds=180):
    relative = Path(phase) / configuration_id(configuration) / strength / inputs["kind"]
    group = output / relative
    group.mkdir(parents=True)
    expected, actual = group / "expected-keys.tsv", group / "candidate-keys.tsv"
    reference_command, candidate_command = commands(configuration, strength, inputs["kind"], oracle, candidate, data_directory, catalog)
    reference_command = bounded(reference_command + ["--metadata", group / "oracle-metadata.json"], timeout_seconds)
    candidate_command = bounded(candidate_command, timeout_seconds)
    print(shlex.join(reference_command), flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reference_future = pool.submit(run_reference, reference_command,
                                       inputs["path"], expected, native_environment, REPO)
        candidate_future = pool.submit(run_logged, candidate_command, cwd=REPO, log=actual,
                                       env=rust_environment, input_path=inputs["path"], timeout=timeout_seconds + 10)
        process = reference_future.result()
        candidate_process = candidate_future.result()
    metadata = json.loads((group / "oracle-metadata.json").read_text())
    check_metadata(metadata, catalog["settings"][configuration["settings"]], strength)
    summary = compare(inputs["path"], expected, actual, inputs["kind"], strength=strength,
                      approved_empty_exceptions=strength == "identical", locale=configuration["locale"])
    if not process["reference_error_free"]:
        summary["status"] = "differences_or_incomplete"
    summary.update(configuration=configuration, strength=strength, phase=phase,
                   input=identity(inputs["path"]), reference_process=process, candidate_process=candidate_process,
                   oracle_metadata=metadata,
                   commands={"reference": [str(arg) for arg in reference_command],
                             "candidate": [str(arg) for arg in candidate_command]})
    save(group / "summary.json", summary)
    return {"path": str(relative), "configuration": configuration_id(configuration),
            "owner": configuration["owner"], "settings": configuration["settings"],
            "locale": configuration["locale"], "strength": strength, "input_format": inputs["kind"],
            "input": str(inputs["path"].relative_to(output)), "case_count": summary["case_count"],
            "status": summary["status"], "totals": summary["totals"]}, summary


def original_empty(output, configuration, empty, oracle, native_environment, timeout_seconds=30):
    directory = output / "original-empty" / configuration_id(configuration)
    directory.mkdir(parents=True)
    return run_reference(bounded([oracle, "--locale", configuration["locale"], "--strength", "identical"], timeout_seconds),
                         empty, directory / "original-boost-keys.tsv", native_environment, REPO)


def build_oracle(cache, output):
    build = cache / "build/locales" / output.name
    build.mkdir(parents=True, exist_ok=False)
    oracle = build / "oracle"
    run_logged(bounded(["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-I", cache / "deps/boost_1_89_0", "-I", cache / "install/icu/include", PRIMARY / "oracle.cpp",
                 "-L", cache / "install/icu/lib", "-Wl,-rpath," + str(cache / "install/icu/lib"),
                 "-licui18n", "-licuuc", "-licudata", "-o", oracle], 180),
               cwd=REPO, log=output / "oracle-build.log", timeout=190)
    return oracle


def run(args):
    cache, data_directory, candidate = args.cache.resolve(), args.data_directory.resolve(), args.candidate.resolve()
    output = (args.output or REPO / "docs/research/assets/icu77-locales/runs" /
              dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%S.%fZ")).resolve()
    output.mkdir(parents=True, exist_ok=False)
    oracle = build_oracle(cache, output)
    catalog_path = data_directory / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    configurations_list = configurations(catalog)
    if args.mechanisms_only:
        args.phase = "configurations"
    selected_configurations = configurations_list[:args.configuration_limit] if args.configuration_limit else configurations_list
    selected_owners = args.owner if args.owner is not None else list(range(len(catalog["owners"])))
    if len(selected_owners) != len(set(selected_owners)) or any(owner < 0 or owner >= len(catalog["owners"]) for owner in selected_owners):
        raise ValueError("Owner selection contains a duplicate or invalid exported owner")
    if args.candidate_provenance:
        provenance = json.loads(args.candidate_provenance.read_text())
        if provenance["status"] != "passed_for_recorded_inputs" or provenance["candidate"]["sha256"] != sha256(candidate):
            raise ValueError("Candidate differs from its completed passing provenance")
    inputs, empty = prepare_inputs(output, args.generated)
    save(output / "configurations.json", configurations_list)
    native = dict(os.environ)
    for key in ("ICU_DATA", "ICU_DATA_FILTER_FILE"):
        native.pop(key, None)
    native["LD_LIBRARY_PATH"] = str(cache / "install/icu/lib")
    rust = dict(os.environ)
    rust.pop("LD_LIBRARY_PATH", None)
    rust.pop("ICU_DATA_FILTER_FILE", None)
    rust["ICU_DATA"] = str(cache / "intentionally-absent-icu-data")
    result = {
        "schema": "boostregexrs.icu77-locales-fullkeys.v2", "status": "running",
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "groups": [], "original_empty": {},
        "coverage_profile": "selected_diagnostic" if args.configuration_limit or args.owner is not None else args.phase,
        "selected_phase": args.phase,
        "selected_configuration_count": len(selected_configurations) if args.phase != "owners" else 0,
        "selected_owners": selected_owners if args.phase != "configurations" else [],
        "not_covered": ["arbitrary public reorder setter lists", "intermediate strengths",
                        "locale ID parsing/default locale acquisition", "CE64 sequence diagnostics (separate gate)"],
        "execution": {"command": [sys.executable, *sys.argv], "cwd": str(REPO),
                      "per_process_timeout_seconds": args.process_timeout,
                      "native_environment": {"LD_LIBRARY_PATH": native["LD_LIBRARY_PATH"],
                                             "removed": ["ICU_DATA", "ICU_DATA_FILTER_FILE"]},
                      "candidate_environment": {"ICU_DATA": rust["ICU_DATA"],
                                                "removed": ["LD_LIBRARY_PATH", "ICU_DATA_FILTER_FILE"]}},
        "configuration_count": len(configurations_list), "owner_count": len(catalog["owners"]),
        "catalog_request_count": len(catalog["requests"]),
        "locale_creation_reference_rejections": [row for row in catalog["requests"] if row["status"] != "loaded"],
        "deduplication": "Only identical source owner and complete effective settings share key runs; every configuration remains in configurations.json",
        "candidate_ingress": "Owner/settings API; locale ID parsing and default-locale acquisition are not exercised by this runner",
        "approved_exception_policy": "ADR-0005 true empty IDENTICAL only, independently counted; original native calls remain separate diagnostics",
        "identity": {"catalog": identity(catalog_path), "candidate": identity(candidate), "oracle": identity(oracle),
                     "root": identity(PRIMARY / "data/root-icu77.bin"), "nfd": identity(PRIMARY / "data/root-icu77-nfd.bin"),
                     "runtime_data_files": source_data_identity(data_directory, catalog),
                     "python": sys.version, "platform": platform.platform(),
                     "sources": [identity(PRIMARY / name) for name in (
                         "run_locales.py", "oracle.cpp", "compare.py", "generate_cases.py", "reference_process.py", "run.py",
                         "rust/tests/locale_cases.py", "export/data_format.py", "export/locale_format.py", "../cloud/prepare.py")],
                     "candidate_provenance": identity(args.candidate_provenance.resolve()) if args.candidate_provenance else None,
                     "native_libraries": [identity(cache / "install/icu/lib" / name)
                                          for name in ("libicui18n.so.77.1", "libicuuc.so.77.1", "libicudata.so.77.1")],
                     "native_source_manifests": [identity(cache / "source-manifests" / name)
                                                 for name in ("boost_1_89_0.tsv.xz", "icu.tsv.xz")]},
    }
    completed = False
    snapshot = output / "generator-snapshot"
    snapshot.mkdir()
    for source in result["identity"]["sources"]:
        path = Path(source["path"])
        shutil.copyfile(path, snapshot / path.name)
    save(output / "summary.json", result)
    try:
        for index, configuration in enumerate(selected_configurations if args.phase != "owners" else []):
            for name in ("common", "u16", "u32"):
                for strength in ("primary", "identical"):
                    item, summary = run_group(output, name, configuration, strength, inputs[name], oracle, candidate,
                                              data_directory, catalog, native, rust, args.process_timeout)
                    result["groups"].append(item)
                    save(output / "summary.json", result)
                    if item["status"] != "passed_for_recorded_inputs":
                        result["first_incomplete_group"] = item
                        print(json.dumps({"first_incomplete": item, "examples": summary["examples"][:3]}), flush=True)
                        return result, output
            result["original_empty"][configuration_id(configuration)] = original_empty(output, configuration, empty, oracle, native)
            save(output / "summary.json", result)
            if (index + 1) % 10 == 0 or index == 0:
                print(f"locale configurations complete: {index + 1}/{len(selected_configurations)}", flush=True)
        if args.phase != "configurations":
            for owner in selected_owners:
                configuration = min((row for row in configurations_list if row["owner"] == owner),
                                    key=lambda row: (not row["source_request"]["default_attributes"], row["settings"]))
                owner_cases = owner_inputs(output, owner, data_directory, catalog)
                for strength in ("primary", "identical"):
                    item, summary = run_group(output, "owner-data", configuration, strength, owner_cases, oracle, candidate,
                                              data_directory, catalog, native, rust, args.process_timeout)
                    result["groups"].append(item)
                    save(output / "summary.json", result)
                    if item["status"] != "passed_for_recorded_inputs":
                        result["first_incomplete_group"] = item
                        print(json.dumps({"first_incomplete": item, "examples": summary["examples"][:3]}), flush=True)
                        return result, output
                print(f"owner data complete: {owner + 1}/{len(catalog['owners'])}, {owner_cases['count']} inputs", flush=True)
        completed = True
        return result, output
    except Exception as error:
        result["execution_error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        result["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        result["status"] = "passed_for_recorded_inputs" if completed else "differences_or_incomplete"
        result["totals"] = {name: sum(group["totals"].get(name, 0) for group in result["groups"])
                            for name in ("passed", "mismatched", "unsupported", "reference_error", "rejected_as_expected", "approved_exception_passed")}
        result["original_empty_reference_error_count"] = sum(row["reference_error_count"] for row in result["original_empty"].values())
        result["completed_configurations"] = len(result["original_empty"])
        result["completed_owner_data_groups"] = sum(group["path"].startswith("owner-data/") for group in result["groups"])
        fixed = [result["identity"][key] for key in ("candidate", "oracle", "catalog")]
        fixed += result["identity"]["runtime_data_files"]
        fixed += result["identity"]["sources"] + result["identity"]["native_libraries"]
        fixed += result["identity"]["native_source_manifests"]
        result["identities_unchanged_during_run"] = all(sha256(Path(item["path"])) == item["sha256"] for item in fixed)
        if not result["identities_unchanged_during_run"]:
            result["status"] = "differences_or_incomplete"
        save(output / "summary.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=REPO / "target/research/icu77-cloud")
    parser.add_argument("--data-directory", type=Path, default=PRIMARY / "data/locales")
    parser.add_argument("--candidate", type=Path, default=REPO / "target/research/icu77-cloud/build/locales-rust/release/icu77-root-primary")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generated", type=int, default=512)
    parser.add_argument("--mechanisms-only", action="store_true", help="explicit diagnostic: skip owner scalar/context/long-input sweep")
    parser.add_argument("--phase", choices=("both", "owners", "configurations"), default="both")
    parser.add_argument("--configuration-limit", type=int, help="diagnostic only: run the first N configurations")
    parser.add_argument("--owner", type=int, action="append", help="diagnostic only: selected exported owner; repeatable")
    parser.add_argument("--process-timeout", type=int, default=180)
    parser.add_argument("--candidate-provenance", type=Path, help="completed candidate verification summary, including its immutable digest")
    args = parser.parse_args()
    if args.generated < 0:
        parser.error("--generated must be nonnegative")
    if args.process_timeout <= 0 or (args.configuration_limit is not None and args.configuration_limit <= 0):
        parser.error("Process deadline and diagnostic configuration limit must be positive")
    result, output = run(args)
    print(json.dumps({"status": result["status"], "totals": result["totals"], "evidence": str(output)}))
    return int(result["status"] != "passed_for_recorded_inputs")


if __name__ == "__main__":
    raise SystemExit(main())
