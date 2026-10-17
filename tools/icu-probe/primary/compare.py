"""Strict, streaming comparison of complete ICU bytes and Boost u32 keys."""

import argparse
import collections
import csv
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path


KEY_COLUMNS = ("case_id", "raw_icu_hex", "boost_u32_hex")
INVALID_INPUT = {"ERROR:INVALID_UTF8", "ERROR:INVALID_UTF16", "ERROR:INVALID_UTF32"}
REFERENCE_ERROR = re.compile(r"ERROR:(?:ACCESS_VIOLATION|SIGNAL_[1-9][0-9]*|EXIT_[1-9][0-9]*|CPP_EXCEPTION)")
COUNTS = ("passed", "mismatched", "unsupported", "reference_error", "rejected_as_expected")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path, columns):
    # Long valid inputs and complete keys intentionally cross csv's small
    # default field limit; the comparator must not truncate this evidence.
    csv.field_size_limit(sys.maxsize)
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != list(columns):
            raise ValueError(f"Unexpected header in {path}: {reader.fieldnames}")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed row in {path}")
            yield row


def key(value, width):
    if not value or any(not re.fullmatch(rf"[0-9a-fA-F]{{{width}}}", part) for part in value.split(",")):
        raise ValueError(f"Malformed key: {value[:80]!r}")
    result = tuple(int(part, 16) for part in value.split(","))
    if any(unit > 255 for unit in result):
        raise ValueError("Boost must promote each byte individually to u32")
    return result


def decode(row, reference):
    raw, boost = row["raw_icu_hex"], row["boost_u32_hex"]
    if raw in INVALID_INPUT and boost == raw:
        return "rejected", raw
    if REFERENCE_ERROR.fullmatch(raw) and boost == raw:
        return "reference_error" if reference else "candidate_error", raw
    if not reference and (raw.startswith("UNSUPPORTED:") or raw == "ERROR:UNSUPPORTED_CE32") and boost == raw:
        return "unsupported", raw
    if not reference and raw.startswith("ERROR:") and boost == raw:
        return "candidate_error", raw
    raw_key, boost_key = key(raw, 2), key(boost, 8)
    if raw_key[-1] != 0 or 0 in raw_key[:-1]:
        raise ValueError("ICU key must have exactly one final terminator")
    # The reference has independently called ICU and the actual Boost traits.
    # A disagreement here is an invalid oracle, never a candidate pass.
    wrapped = raw_key[:-1] if len(raw_key) > 1 else raw_key
    if reference and wrapped != boost_key:
        raise ValueError("Independent ICU bytes and actual Boost wrapper disagree")
    return "key", (raw_key, boost_key)


def input_error(value, kind):
    """Validate the protocol and derive rejection expectations from the input."""
    if kind == "utf8":
        if len(value) % 2 or not re.fullmatch(r"[0-9a-fA-F]*", value):
            raise ValueError("Malformed UTF-8 hexadecimal protocol field")
        try:
            bytes.fromhex(value).decode("utf-8")
        except UnicodeDecodeError:
            return "ERROR:INVALID_UTF8"
    else:
        width = 8 if kind == "u32" else 4
        parts = value.split(",") if value else []
        if any(not re.fullmatch(rf"[0-9a-fA-F]{{{width}}}", part) for part in parts):
            raise ValueError(f"Malformed {kind} hexadecimal protocol field")
        units = [int(part, 16) for part in parts]
        if kind == "u32":
            if any(cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF for cp in units):
                return "ERROR:INVALID_UTF32"
        else:
            try:
                b"".join(unit.to_bytes(2, "little") for unit in units).decode("utf-16-le")
            except UnicodeDecodeError:
                return "ERROR:INVALID_UTF16"
    return None


def compare(cases_path, reference_path, candidate_path, input_format="utf8", ordering_path=None):
    totals = dict.fromkeys(COUNTS, 0)
    groups = collections.defaultdict(lambda: dict.fromkeys(COUNTS, 0))
    examples = []
    seen = set()
    raw_passed = boost_passed = count = 0
    length_min = None
    length_max = 0
    boundary_lengths = {str(n): 0 for n in (99, 100, 101)}
    ordering = iter(rows(ordering_path, ("left_id", "right_id", "ordering"))) if ordering_path else None
    ordering_counts = {"passed": 0, "mismatched": 0, "unavailable": 0}
    previous = None
    streams = (rows(cases_path, ("case_id", f"{input_format}_hex")), rows(reference_path, KEY_COLUMNS), rows(candidate_path, KEY_COLUMNS))
    for case, reference, candidate in itertools.zip_longest(*streams):
        if case is None or reference is None or candidate is None:
            raise ValueError("Missing or extra rows: input and both outputs must have identical coverage")
        identity = case["case_id"]
        if not identity or identity in seen:
            raise ValueError(f"Empty or duplicate case ID: {identity!r}")
        seen.add(identity)
        if identity != reference["case_id"] or identity != candidate["case_id"]:
            raise ValueError(f"Missing, reordered, or unexpected output at {identity}")
        expected_kind, expected = decode(reference, True)
        actual_kind, actual = decode(candidate, False)
        rejection = input_error(case[f"{input_format}_hex"], input_format)
        if expected_kind == "rejected" and expected != rejection:
            raise ValueError(f"Invalid oracle rejection for input domain at {identity}")
        if expected_kind == "key" and rejection is not None:
            raise ValueError(f"Oracle produced a key for invalid input at {identity}")
        if expected_kind == "reference_error":
            outcome = "reference_error"
        elif actual_kind == "unsupported":
            outcome = "unsupported"
        elif expected_kind == "rejected":
            outcome = "rejected_as_expected" if actual_kind == "rejected" and actual == expected else "mismatched"
        elif actual_kind != "key":
            outcome = "mismatched"
        else:
            raw_passed += expected[0] == actual[0]
            boost_passed += expected[1] == actual[1]
            outcome = "passed" if expected == actual else "mismatched"
        if expected_kind == "key":
            length = len(expected[0])
            length_min = length if length_min is None else min(length_min, length)
            length_max = max(length_max, length)
            if str(length) in boundary_lengths:
                boundary_lengths[str(length)] += 1
        count += 1
        totals[outcome] += 1
        groups[identity.split("/", 1)[0]][outcome] += 1
        if outcome not in ("passed", "rejected_as_expected") and len(examples) < 40:
            examples.append({"case": case, "reference": reference, "candidate": candidate, "outcome": outcome})
        if ordering is not None and previous is not None:
            pair = next(ordering, None)
            if pair is None or (pair["left_id"], pair["right_id"]) != (previous[0], identity):
                raise ValueError("Missing or unexpected ICU ordering pair")
            if pair["ordering"] not in ("-1", "0", "1"):
                raise ValueError("Invalid ICU ordering sign")
            if previous[1] is None or actual_kind != "key":
                ordering_counts["unavailable"] += 1
            else:
                sign = (previous[1] > actual[1]) - (previous[1] < actual[1])
                label = "passed" if sign == int(pair["ordering"]) else "mismatched"
                ordering_counts[label] += 1
        previous = identity, actual[1] if actual_kind == "key" else None
    if not count:
        raise ValueError("Empty test corpus")
    if ordering is not None and next(ordering, None) is not None:
        raise ValueError("Extra ICU ordering pairs")
    complete = all(totals[name] == 0 for name in ("mismatched", "unsupported", "reference_error"))
    complete &= ordering_counts["mismatched"] == 0 and ordering_counts["unavailable"] == 0
    return {
        "status": "passed_for_recorded_inputs" if complete else "differences_or_incomplete",
        "scope": "root PRIMARY; complete raw ICU bytes and actual Boost u32 keys",
        "input_format": input_format, "case_count": count, "totals": totals,
        "raw_icu_bytes_passed": raw_passed, "boost_u32_keys_passed": boost_passed,
        "by_category": dict(sorted(groups.items())), "examples": examples,
        "raw_key_length": {"minimum": length_min, "maximum": length_max, "boost_buffer_boundary_counts": boundary_lengths},
        "adjacent_icu_compare": ordering_counts if ordering_path else "not_requested",
        "sha256": {name: sha256(path) for name, path in (("cases", cases_path), ("reference", reference_path), ("candidate", candidate_path))},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cases", "reference", "candidate", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--input-format", choices=("utf8", "u32", "u16"), default="utf8")
    parser.add_argument("--ordering", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.cases, args.reference, args.candidate, args.input_format, args.ordering)
        status = int(result["status"] != "passed_for_recorded_inputs")
    except (ValueError, OSError, UnicodeError, csv.Error) as error:
        result, status = {"status": "invalid_input", "error": str(error)}, 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result.get("totals", result), ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
