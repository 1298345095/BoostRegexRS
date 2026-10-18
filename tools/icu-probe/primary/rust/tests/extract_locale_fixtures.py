#!/usr/bin/env python3
"""Extract focused golden keys from a completed independent locale oracle run.

Selections are defined by mechanisms and input identities before reading keys.
The candidate is never executed and its key output is never a fixture source.
The catalog/configuration mapping is test metadata, not a runtime locale parser.
"""

import argparse
from collections import defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path

from locale_cases import profiles


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_identity(request):
    """Match our fixed ICU test requests regardless of keyword name case/order."""
    base, separator, keywords = request.partition("@")
    if not separator:
        return base
    return base + "@" + ";".join(sorted(
        name.lower() + "=" + value
        for name, value in (part.split("=", 1) for part in keywords.split(";"))
    ))


def selections():
    """Focused interactions and source-defined boundaries, not observed diffs."""
    defined = {row["profile_id"]: row["locale"] for row in profiles()}

    def select(profile, *cases):
        return [(defined[profile], case) for case in cases]

    selected = []
    for profile in defined:
        if profile.startswith("fcd") and profile.endswith("-punct"):
            selected += select(profile, "locale/case_secondary_ignorable", "locale/variables")

    for variable in ("space", "punct", "symbol", "currency"):
        selected += select(f"fcd1-num1-back1-case1-upper-shift1-{variable}",
                           "locale/shift_adjacent", "locale/shift_merge", "compression/shifted-113")

    numeric = "fcd0-num1-back0-case0-no-shift0-punct"
    for value in (73, 74, 10233, 10234, 1042489, 1042490):
        for zeros in (0, 255):
            selected += select(numeric, f"numeric/dense-{value}-zero{zeros}")
    for length in (253, 254, 255, 256, 508):
        for kind in ("nines", "power", "alternating", "zero_segment"):
            selected += select(numeric, f"numeric/segment-{kind}-{length}")
    for base in (0x30, 0x660, 0x966, 0xff10, 0x1d7ce):
        selected += select(numeric, f"numeric/script-{base:x}-1042490")
    selected += select(numeric, "locale/numeric_boundaries_nul", "locale/numeric_ignorables",
                       "locale/numeric_non_decimal", "locale/numeric_script_transition")

    fcd = "fcd1-num0-back0-case0-no-shift0-punct"
    selected += select(fcd, "locale/prefix_fcd", "locale/discontiguous", "locale/tibetan",
                       "locale/fcd_starter_boundary", "locale/fcd_supplementary",
                       "locale/fcd_leading", "locale/fcd_merge", "locale/fcd_nul")
    for base in range(10):
        for first, second in ((2, 0), (2, 4)):
            selected += select(fcd, f"fcd/context-{base}-{first}-{second}")

    for first in ("no", "lower", "upper"):
        for level in (0, 1):
            for backward in (0, 1):
                selected += select(
                    f"fcd0-num0-back{backward}-case{level}-{first}-shift0-punct",
                    "compression/lower_upper-7", "compression/mixed-13",
                    "compression/above_secondary-33", "compression/reverse_segment-34",
                    "compression/upper_lower-97", "compression/quaternary-113",
                )

    for profile in defined:
        if profile.startswith("reorder-"):
            selected += select(profile, "locale/compress_up", "locale/compress_down",
                               "locale/compress_merge", "locale/variables",
                               "locale/numeric_script_transition")

    for locale in ("da", "fr_CA", "ja", "ko", "th", "vi", "de@collation=phonebook",
                   "es@collation=traditional", "hr", "cs", "hu", "sv",
                   "zh@collation=stroke", "zh@collation=pinyin", "zh@collation=zhuyin",
                   "@collation=emoji"):
        for case in ("locale/han_hangul_supplementary", "locale/case_letters", "locale/expansions",
                     "locale/discontiguous", "locale/fcd_starter_boundary"):
            selected.append((locale, case))
    return selected


def extract(run):
    report_path = run / "summary.json"
    report = json.loads(report_path.read_text())
    if report["status"] != "passed_for_recorded_inputs" or not report["identities_unchanged_during_run"]:
        raise ValueError("Golden fixture source must be a completed passing run with unchanged identities")
    verification_path = run / "verification.json"
    verification = json.loads(verification_path.read_text())
    configurations_path = run / "configurations.json"
    configurations = json.loads(configurations_path.read_text())
    complete_count = report["configuration_count"]
    if (verification["status"] != "passed" or verification["run_summary_sha256"] != digest(report_path)
            or report["selected_phase"] != "configurations"
            or report["selected_configuration_count"] != complete_count
            or report["completed_configurations"] != complete_count
            or len(configurations) != complete_count
            or verification["configuration_strength_width_groups"] != complete_count * 6):
        raise ValueError("Golden fixtures require the verified complete configuration, strength and three-width matrix")
    by_request = {}
    by_pair = {}
    for configuration in configurations:
        pair = configuration["owner"], configuration["settings"]
        by_pair[pair] = configuration
        for request in configuration["equivalent_exported_requests"]:
            name = request_identity(request)
            if name in by_request and by_request[name] != pair:
                raise ValueError("Inconsistent configuration identity for the same fixed request")
            by_request[name] = pair

    input_path = run / "inputs/common-utf8.tsv"
    with input_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != ["case_id", "utf8_hex"]:
            raise ValueError("Unexpected locale mechanism input columns")
        input_rows = list(reader)
    input_names = [row["case_id"] for row in input_rows]
    if len(input_names) != len(set(input_names)):
        raise ValueError("Duplicate fixture source input identity")
    inputs = {row["case_id"]: row["utf8_hex"] for row in input_rows}
    wanted = defaultdict(set)
    for request, name in selections():
        if name not in inputs:
            raise ValueError(f"Missing predefined mechanism input: {name}")
        owner, settings = by_request[request_identity(request)]
        for strength in ("primary", "identical"):
            wanted[owner, settings, strength].add(name)

    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(("fixture_id", "owner", "settings", "strength", "utf8_hex", "raw_icu_hex", "boost_u32_hex"))
    sources = []
    count = 0
    for (owner, settings, strength), names in sorted(wanted.items()):
        relative = Path("common") / f"owner-{owner:04d}-settings-{settings:04d}" / strength / "utf8"
        group = run / relative
        summary_path = group / "summary.json"
        summary = json.loads(summary_path.read_text())
        if summary["status"] != "passed_for_recorded_inputs" or summary["input"]["sha256"] != digest(input_path):
            raise ValueError(f"Unverified fixture source group: {relative}")
        expected_path = group / "expected-keys.tsv"
        with expected_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if reader.fieldnames != ["case_id", "raw_icu_hex", "boost_u32_hex"]:
                raise ValueError("Unexpected oracle output columns")
            reference = list(reader)
        if [row["case_id"] for row in reference] != input_names:
            raise ValueError("Reference omitted, duplicated, or reordered fixture source rows")
        selected = {row["case_id"]: row for row in reference if row["case_id"] in names}
        for name in sorted(names):
            row = selected[name]
            if "ERROR:" in row["raw_icu_hex"] or "ERROR:" in row["boost_u32_hex"]:
                raise ValueError(f"Reference error for fixture {relative}/{name}")
            fixture = f"o{owner:04d}-s{settings:04d}/{strength}/{name}"
            writer.writerow((fixture, owner, settings, strength, inputs[name],
                             row["raw_icu_hex"], row["boost_u32_hex"]))
            count += 1
        sources.append({"group": relative.as_posix(), "owner": owner, "settings": settings,
                        "strength": strength, "locale": by_pair[owner, settings]["locale"],
                        "case_count": len(names), "expected_keys_sha256": digest(expected_path),
                        "group_summary_sha256": digest(summary_path)})
    fixture_text = output.getvalue()
    manifest = {
        "schema": "boostregexrs.icu77-locale-rust-fixtures.v2",
        "fixture_count": count, "group_count": len(sources),
        "fixture_sha256": hashlib.sha256(fixture_text.encode()).hexdigest(),
        "input_sha256": digest(input_path), "catalog_sha256": report["identity"]["catalog"]["sha256"],
        "oracle_sha256": report["identity"]["oracle"]["sha256"],
        "source_run": run.name, "source_run_summary_sha256": digest(report_path),
        "source_run_verification_sha256": digest(verification_path),
        "verified_configuration_strength_width_groups": verification["configuration_strength_width_groups"],
        "configurations_sha256": digest(configurations_path),
        "extractor_sha256": digest(Path(__file__)),
        "profile_selection_sha256": digest(Path(__file__).with_name("locale_cases.py")),
        "selection": "Source-defined case identities and setting interactions; independent expected-keys.tsv only",
        "candidate_keys_used": False, "unicode_normalization_performed": False, "sources": sources,
    }
    return fixture_text, json.dumps(manifest, ensure_ascii=True, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data/locales.tsv")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    fixture, manifest = extract(args.run)
    outputs = ((args.output, fixture), (args.output.with_suffix(".json"), manifest))
    for path, contents in outputs:
        if args.check:
            if path.read_text() != contents:
                raise ValueError(f"Regenerated locale fixtures differ: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
    print(json.dumps({"status": "identical" if args.check else "written",
                      "fixture": str(args.output), "sha256": hashlib.sha256(fixture.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
