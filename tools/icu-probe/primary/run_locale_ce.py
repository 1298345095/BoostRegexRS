#!/usr/bin/env python3
"""Compare complete native CE64 and PRIMARY/IDENTICAL keys for owner contexts.

Inputs come from the fixed owner/context tables. Nested skipped-mark cases use
the exported FCD classes and actual top/base contraction entries, never keys.
"""

import argparse
import bisect
from concurrent.futures import ThreadPoolExecutor
import csv
import datetime as dt
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import sys

from run_locales import (PRIMARY, REPO, bounded, build_oracle, check_metadata, commands, compare,
                        configurations, contexts, identity, owner_context_report,
                        read_data, read_owner, run_logged, run_reference, save, sha256,
                        source_data_identity, write_cases)


CE = re.compile(r"[0-9a-f]{16}")


def lookup(ranges):
    ends = [end for end, _ in ranges]
    return lambda cp: ranges[bisect.bisect_left(ends, cp)][1]


def nested_cases(owner, data, report, root, root_report):
    """Compose real nonstarter contractions inside another skipped-mark buffer.

    CollationIterator::nextCE32FromDiscontiguousContraction requires strictly
    increasing CCC for a non-blocked suffix. The inner trigger and its suffix
    are lower-class marks than the outer suffix. A source-selected class-1 mark
    additionally exercises recursive skipping and buffer replacement.
    """
    fcd = lookup(root["fcd16_ranges"])
    top = lookup(data["ce32_ranges"])
    available = [(owner, report, trigger) for trigger in report["triggers"]]
    if owner:
        available.extend((0, root_report, trigger) for trigger in root_report["triggers"]
                         if top(trigger["codepoint"]) == 0xC0)
    contractions = []
    for origin, table, trigger in available:
        if trigger["tag"] != 9:
            continue
        context = next(row for row in table["contexts"] if row["index"] == trigger["context_index"])
        for index, entry in enumerate(context["entries"]):
            suffix = entry["codepoints"]
            if suffix and all(fcd(cp) >> 8 for cp in suffix):
                contractions.append((origin, trigger, index, suffix))
    low_marks = []
    start = 0
    for end, value in root["fcd16_ranges"]:
        if value == 0x0101 and start <= 0xD7FF:
            low_marks.append(start)
        start = end + 1
    if not low_marks:
        raise ValueError("Fixed FCD data lacks a source-selected class-1 mark")
    low = low_marks[0]
    for outer_origin, outer, outer_entry, outer_suffix in contractions:
        outer_class = fcd(outer_suffix[0]) >> 8
        for inner_origin, inner, inner_entry, inner_suffix in contractions:
            inner_start = fcd(inner["codepoint"]) >> 8
            if not inner_start or inner_start >= outer_class:
                continue
            if any(not inner_start < (fcd(cp) >> 8) < outer_class for cp in inner_suffix):
                continue
            label = (f"o{outer_origin}-{outer['codepoint']:06x}-{outer['context_index']}-{outer_entry}-"
                     f"i{inner_origin}-{inner['codepoint']:06x}-{inner['context_index']}-{inner_entry}")
            for variant, middle in (("contiguous", []), ("recursive-skip", [low]),
                                    ("recursive-multiple-skips", [low, low]),
                                    ("blocked-inner", [outer_suffix[0]])):
                values = [outer["codepoint"], inner["codepoint"], *middle, *inner_suffix, *outer_suffix]
                yield f"nested/{label}/{variant}", "".join(map(chr, values))


def prepare_owner_inputs(output, owner, data_directory, catalog, root, root_report):
    directory = output / f"owner-{owner:04d}"
    directory.mkdir()
    source = PRIMARY / "data/root-icu77.bin" if owner == 0 else data_directory / catalog["owner_files"][owner]["file"]
    data = root if owner == 0 else read_owner(source)
    report = owner_context_report(data)
    report_path = directory / "contexts.json"
    save(report_path, report)
    counts, seen = {}, set()
    controls = [("control/empty", ""), ("control/nul", "\0"),
                ("control/hangul", "\uac00\uac01\ud7a3"),
                ("control/jamo", "\u1100\u1161\u1100\u1161\u11a8\u1112\u1175\u11c2"),
                ("control/supplementary", "\U0001d165\U00020000\U0010ffff")]

    def values():
        for name, text in itertools.chain(contexts(report_path),
                                          nested_cases(owner, data, report, root, root_report), controls):
            if name in seen:
                raise ValueError(f"Duplicate owner CE input: {name}")
            seen.add(name)
            category = name.split("/", 1)[0]
            counts[category] = counts.get(category, 0) + 1
            encoded = text.encode("utf-16-le")
            yield name, [int.from_bytes(encoded[i:i + 2], "little") for i in range(0, len(encoded), 2)]

    inputs = directory / "inputs-u16.tsv"
    count = write_cases(inputs, values(), "u16")
    generation = {"owner": owner, "owner_data": identity(source), "context_report": identity(report_path),
                  "input": identity(inputs), "count": count, "categories": counts,
                  "base_owner": catalog["owners"][owner]["base"], "fixed_fcd": root["sha256"],
                  "reference_keys_used": False, "normalization_performed": False}
    save(directory / "generation.json", generation)
    return directory, inputs, generation


def compare_ces(inputs, expected, actual):
    totals = {"passed": 0, "mismatched": 0, "unsupported": 0, "reference_error": 0}
    examples = []
    with inputs.open(encoding="utf-8", newline="") as input_stream, \
         expected.open(encoding="utf-8", newline="") as native_stream, \
         actual.open(encoding="utf-8") as candidate_stream:
        originals = csv.DictReader(input_stream, delimiter="\t")
        references = csv.DictReader(native_stream, delimiter="\t")
        if originals.fieldnames != ["case_id", "u16_hex"] or references.fieldnames != ["case_id", "ces64_hex"]:
            raise ValueError("Invalid CE64 protocol header")
        candidates = (json.loads(line) for line in candidate_stream)
        for original, reference, candidate in itertools.zip_longest(originals, references, candidates):
            if original is None or reference is None or candidate is None:
                raise ValueError("Missing or extra CE64 input/reference/candidate row")
            if not original["case_id"] == reference["case_id"] == candidate["case_id"]:
                raise ValueError("Reordered CE64 rows")
            ces = reference["ces64_hex"].split(",")
            if any(CE.fullmatch(value) is None for value in ces) or ces[-1] != "0000000101000100":
                raise ValueError("Malformed native CE64 or missing end sentinel")
            if "error" in candidate:
                totals["unsupported"] += 1
            else:
                actual_ces = candidate["ces"]
                if not actual_ces or any(not isinstance(value, str) or CE.fullmatch(value) is None for value in actual_ces):
                    raise ValueError("Malformed candidate CE64")
                category = "passed" if actual_ces == ces else "mismatched"
                totals[category] += 1
                if category == "mismatched" and len(examples) < 8:
                    examples.append({"case_id": original["case_id"], "reference": ces, "candidate": actual_ces})
    return {"status": "passed_for_recorded_inputs" if not sum(totals[key] for key in totals if key != "passed") else "differences_or_incomplete",
            "totals": totals, "examples": examples, "native_ce_sentinel": "ICU internalGetCEs omits NO_CE; trace-locale appends it once"}


def run(args):
    cache, output, data_directory = args.cache.resolve(), args.output.resolve(), args.data_directory.resolve()
    candidate = args.candidate.resolve()
    catalog = json.loads((data_directory / "catalog.json").read_text())
    provenance = json.loads(args.candidate_provenance.read_text())
    if provenance["candidate"]["sha256"] != sha256(candidate) or provenance["status"] != "passed_for_recorded_inputs":
        raise ValueError("Candidate does not match its completed fixed verification")
    output.mkdir(parents=True, exist_ok=False)
    oracle = build_oracle(cache, output)
    trace = cache / "build/locales" / output.name / "trace-locale"
    prefix, sources = cache / "install/icu", cache / "deps/icu/source"
    command = ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-DU_STATIC_IMPLEMENTATION",
               "-I", prefix / "include", "-I", sources / "common", "-I", sources / "i18n",
               PRIMARY / "export/trace-locale.cpp", *[prefix / "lib" / name for name in
               ("libicui18n.a", "libicuuc.a", "libicudata.a")], "-lpthread", "-ldl", "-lm", "-o", trace]
    run_logged(bounded(command, 180), cwd=REPO, log=output / "trace-build.log", timeout=190)
    native = dict(os.environ)
    for name in ("ICU_DATA", "ICU_DATA_FILTER_FILE"):
        native.pop(name, None)
    native["LD_LIBRARY_PATH"] = str(prefix / "lib")
    rust = dict(os.environ)
    for name in ("LD_LIBRARY_PATH", "ICU_DATA_FILTER_FILE"):
        rust.pop(name, None)
    rust["ICU_DATA"] = str(cache / "intentionally-absent-icu-data")
    root = read_data(PRIMARY / "data/root-icu77.bin")
    root_report = owner_context_report(root)
    all_configurations = configurations(catalog)
    owners = list(range(len(catalog["owners"]))) if args.owner is None else args.owner
    source_files = [Path(__file__), PRIMARY / "run_locales.py", PRIMARY / "generate_cases.py",
                    PRIMARY / "reference_process.py", PRIMARY / "compare.py", PRIMARY.parent / "cloud/prepare.py",
                    PRIMARY / "export/trace-locale.cpp", PRIMARY / "oracle.cpp",
                    PRIMARY / "export/data_format.py", PRIMARY / "export/locale_format.py"]
    result = {"schema": "boostregexrs.icu77-owner-ce-acceptance.v1", "status": "running",
              "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "groups": [],
              "selected_owners": owners, "complete_owner_selection": set(owners) == set(range(len(catalog["owners"]))),
              "candidate": identity(candidate), "oracle": identity(oracle), "ce_reference": identity(trace),
              "candidate_provenance": identity(args.candidate_provenance.resolve()),
              "catalog": identity(data_directory / "catalog.json"),
              "data": source_data_identity(data_directory, catalog), "sources": [identity(path) for path in source_files],
              "native_libraries": [identity(prefix / "lib" / name) for name in
                                   ("libicui18n.a", "libicuuc.a", "libicudata.a",
                                    "libicui18n.so.77.1", "libicuuc.so.77.1", "libicudata.so.77.1")],
              "native_source_manifests": [identity(cache / "source-manifests" / name)
                                          for name in ("boost_1_89_0.tsv.xz", "icu.tsv.xz")],
              "execution": {"command": [sys.executable, *sys.argv], "process_timeout_seconds": args.process_timeout,
                            "native_LD_LIBRARY_PATH": native["LD_LIBRARY_PATH"], "candidate_ICU_DATA": rust["ICU_DATA"]},
              "not_covered": ["all-scalar domain (separate owner sweep)", "arbitrary settings (separate settings sweep)"]}
    snapshot = output / "source-snapshot"
    snapshot.mkdir()
    for path in source_files:
        shutil.copyfile(path, snapshot / path.name)
    completed = False
    save(output / "summary.json", result)
    try:
        for owner in owners:
            configuration = min((row for row in all_configurations if row["owner"] == owner),
                                key=lambda row: (not row["source_request"]["default_attributes"], row["settings"]))
            directory, inputs, generation = prepare_owner_inputs(output, owner, data_directory, catalog, root, root_report)
            run_logged(bounded([trace, configuration["locale"]], args.process_timeout), cwd=REPO,
                       input_path=inputs, log=directory / "native-ces.tsv", env=native, timeout=args.process_timeout + 10)
            key_groups = []
            for strength in ("primary", "identical"):
                group = directory / strength
                group.mkdir()
                reference, actual = commands(configuration, strength, "u16", oracle, candidate, data_directory, catalog)
                if strength == "primary":
                    actual.append("--trace")
                with ThreadPoolExecutor(max_workers=2) as pool:
                    expected_future = pool.submit(run_reference, bounded(reference + ["--metadata", group / "metadata.json"], args.process_timeout),
                                                  inputs, group / "expected.tsv", native, REPO)
                    actual_future = pool.submit(run_logged, bounded(actual, args.process_timeout), cwd=REPO,
                                                input_path=inputs, log=group / "candidate.tsv", env=rust,
                                                timeout=args.process_timeout + 10)
                    reference_process, candidate_process = expected_future.result(), actual_future.result()
                metadata = json.loads((group / "metadata.json").read_text())
                check_metadata(metadata, catalog["settings"][configuration["settings"]], strength)
                compared = compare(inputs, group / "expected.tsv", group / "candidate.tsv", "u16", strength=strength,
                                   approved_empty_exceptions=strength == "identical", locale=configuration["locale"])
                compared.update(reference_process=reference_process, candidate_process=candidate_process, metadata=metadata)
                if not reference_process["reference_error_free"]:
                    compared["status"] = "differences_or_incomplete"
                save(group / "summary.json", compared)
                key_groups.append({"strength": strength, "status": compared["status"], "totals": compared["totals"]})
            ces = compare_ces(inputs, directory / "native-ces.tsv", directory / "primary/candidate.stderr.log")
            save(directory / "ce-comparison.json", ces)
            row = {"owner": owner, "configuration": configuration, "input": generation,
                   "keys": key_groups, "ces": ces}
            result["groups"].append(row)
            save(output / "summary.json", result)
            print(json.dumps({"owner": owner, "inputs": generation["count"], "categories": generation["categories"],
                              "CE64": ces["totals"], "keys": key_groups}), flush=True)
            if ces["status"] != "passed_for_recorded_inputs" or any(group["status"] != "passed_for_recorded_inputs" for group in key_groups):
                return 1
        completed = True
    except Exception as error:
        result["execution_error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        fixed = [result[key] for key in ("candidate", "oracle", "ce_reference", "catalog")] + result["data"] + result["sources"]
        fixed += result["native_libraries"] + result["native_source_manifests"]
        result["identities_unchanged_during_run"] = all(sha256(Path(item["path"])) == item["sha256"] for item in fixed)
        result["status"] = "passed_for_recorded_inputs" if completed and result["identities_unchanged_during_run"] else "differences_or_incomplete"
        result["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save(output / "summary.json", result)
    return int(result["status"] != "passed_for_recorded_inputs")


def main():
    csv.field_size_limit(sys.maxsize)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-provenance", type=Path, required=True)
    parser.add_argument("--data-directory", type=Path, default=PRIMARY / "data/locales")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--process-timeout", type=int, default=180)
    parser.add_argument("--owner", type=int, action="append", help="diagnostic subset, not complete owner acceptance")
    args = parser.parse_args()
    if args.process_timeout <= 0 or (args.owner is not None and (len(set(args.owner)) != len(args.owner) or any(owner < 0 for owner in args.owner))):
        parser.error("Invalid process deadline or duplicate/negative owner selection")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
