"""Compare ICU4X ordering signs against Boost's exported sort keys.

This does NOT validate ICU4X sort-key bytes. Missing or unsupported observations
are never counted as passes. Only Python's standard library is required.
"""

import argparse
import csv
import hashlib
import itertools
import json
import re
from pathlib import Path


LOCALES = (
    "root", "en_US", "tr_TR", "de_DE", "sv_SE", "fr_CA",
    "es_ES@collation=traditional", "zh_CN", "ja_JP", "th_TH",
)
STRENGTHS = ("primary", "identical")
REFERENCE_ERROR = re.compile(r"ERROR:(?:ACCESS_VIOLATION|SIGNAL_[1-9][0-9]*|EXIT_[1-9][0-9]*|CPP_EXCEPTION)")


def read_rows(path, columns):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != list(columns):
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Incomplete or extra fields in {path}:{line}")
            yield row


def compare(cases_path, reference_path, candidate_path, locales=LOCALES):
    cases = []
    for row in read_rows(cases_path, ("case_id", "utf8_hex")):
        case_id = row["case_id"]
        if not case_id or case_id in cases:
            raise ValueError(f"Empty or duplicate case ID: {case_id!r}")
        bytes.fromhex(row["utf8_hex"]).decode("utf-8")
        cases.append(case_id)
    if len(cases) < 2:
        raise ValueError("At least two cases are required")
    if not locales or len(locales) != len(set(locales)):
        raise ValueError("Locales must be a nonempty distinct sequence")

    keys = {}
    for row in read_rows(reference_path, ("locale", "case_id", "primary", "identical")):
        identity = row["locale"], row["case_id"]
        if identity in keys:
            raise ValueError(f"Duplicate reference row: {identity}")
        decoded = {}
        for strength in STRENGTHS:
            if REFERENCE_ERROR.fullmatch(row[strength]):
                decoded[strength] = None
                continue
            decoded[strength] = tuple(int(part, 16) for part in row[strength].split(",")) if row[strength] else ()
            if any(value < 0 or value > 0xFFFFFFFF for value in decoded[strength]):
                raise ValueError(f"Reference key outside u32: {identity}")
        keys[identity] = decoded
    expected_keys = set(itertools.product(locales, cases))
    if set(keys) != expected_keys:
        raise ValueError(f"Reference coverage differs: missing={len(expected_keys - set(keys))}, extra={len(set(keys) - expected_keys)}")

    pairs = list(itertools.combinations(cases, 2))
    expected = {
        (locale, strength, left, right)
        for locale in locales for strength in STRENGTHS for left, right in pairs
    }
    seen = set()
    groups = {
        (locale, strength): {"locale": locale, "strength": strength, "passed": 0, "mismatched": 0, "unsupported": 0, "reference_error": 0}
        for locale in locales for strength in STRENGTHS
    }
    examples = []
    for row in read_rows(candidate_path, ("locale", "strength", "left_id", "right_id", "ordering")):
        identity = row["locale"], row["strength"], row["left_id"], row["right_id"]
        if identity not in expected or identity in seen:
            raise ValueError(f"Unexpected or duplicate candidate pair: {identity}")
        seen.add(identity)
        locale, strength, left, right = identity
        a, b = keys[locale, left][strength], keys[locale, right][strength]
        reference_order = None if a is None or b is None else (a > b) - (a < b)
        actual = row["ordering"]
        if actual not in ("-1", "0", "1", "unsupported"):
            raise ValueError(f"Invalid ordering {actual!r}: {identity}")
        if reference_order is None:
            outcome = "reference_error"
        elif actual == "unsupported":
            outcome = "unsupported"
        elif actual in ("-1", "0", "1"):
            outcome = "passed" if int(actual) == reference_order else "mismatched"
        groups[locale, strength][outcome] += 1
        if outcome != "passed" and len(examples) < 30:
            examples.append({**row, "expected_ordering": reference_order, "outcome": outcome})
    if seen != expected:
        raise ValueError(f"Missing {len(expected - seen)} candidate pairs")
    totals = {name: sum(group[name] for group in groups.values()) for name in ("passed", "mismatched", "unsupported", "reference_error")}
    complete = all(totals[name] == 0 for name in ("mismatched", "unsupported", "reference_error"))
    return {
        "comparison_sign_status": "passed_for_this_corpus" if complete else "differences_or_incomplete",
        "sort_key_byte_compatibility": "not_validated_candidate_has_no_key_output",
        "case_count": len(cases), "locale_count": len(locales), "pair_count": len(expected),
        "totals": totals, "by_locale_strength": list(groups.values()), "examples": examples,
        "source_sha256": {label: hashlib.sha256(Path(path).read_bytes()).hexdigest() for label, path in (
            ("cases", cases_path), ("reference_sortkeys", reference_path), ("candidate_ordering", candidate_path))},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = compare(args.cases, args.reference, args.candidate)
        status = 0 if result["comparison_sign_status"] == "passed_for_this_corpus" else 1
    except (OSError, ValueError, UnicodeError) as error:
        result = {"comparison_sign_status": "invalid_input", "error": str(error)}
        status = 2
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result.get("totals", result), ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
