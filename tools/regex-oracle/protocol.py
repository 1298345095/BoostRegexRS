"""Validate the complete byte-reference protocol before comparing any results."""

import csv
import json
import re

HEADER = ("case_id", "operation", "syntax", "match", "pattern_hex", "input_hex", "format_hex")
OUTPUT_HEADER = ("case_id", "status", "result")
OPERATIONS = frozenset(("compile", "search", "match", "iterate", "format", "replace"))
HEX = re.compile(r"(?:[0-9a-fA-F]{2})*", re.ASCII)
DECIMAL = re.compile(r"[0-9]+", re.ASCII)
RESOURCE_CODES = frozenset((12, 15, 18, 19))
RESOURCE_FAILURE_KINDS = frozenset(("regex_resource", "allocation", "capacity"))
NO_EXCEPT = 1 << 18


def read_rows(path, header):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream, delimiter="\t", strict=True)
        if next(reader, None) != list(header):
            raise ValueError(f"Invalid header: {path}")
        rows = list(reader)
    if any(len(row) != len(header) for row in rows):
        raise ValueError(f"Invalid column count: {path}")
    identifiers = [row[0] for row in rows]
    if any(not identifier for identifier in identifiers):
        raise ValueError(f"Empty case ID: {path}")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError(f"Duplicate case ID: {path}")
    return rows


def read_cases(path):
    rows = read_rows(path, HEADER)
    for row in rows:
        if row[1] not in OPERATIONS:
            raise ValueError(f"Unknown operation for {row[0]}")
        for value in row[2:4]:
            if DECIMAL.fullmatch(value) is None or int(value) > 0xFFFF_FFFF:
                raise ValueError(f"Invalid u32 flags for {row[0]}")
        for value in row[4:]:
            hexadecimal(value)
    return rows


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Nonstandard JSON constant: {value}")


def fields(value, expected):
    if type(value) is not dict or value.keys() != set(expected):
        raise ValueError(f"Expected exactly these result fields: {', '.join(expected)}")


def integer(value):
    # Python bool is an int subclass and compares equal to 0/1. It is never
    # an acceptable substitute for a Boost error code, count or input offset.
    if type(value) is not int:
        raise ValueError("An integer result field has a different JSON type")


def hexadecimal(value):
    if type(value) is not str or HEX.fullmatch(value) is None:
        raise ValueError("Invalid byte-hex result")


def range_pair(value):
    if type(value) is not list or len(value) != 2:
        raise ValueError("A range must contain exactly two original input offsets")
    for item in value:
        integer(item)
    # Do not impose new ordering/bounds semantics on Boost ranges: reset-start
    # verbs and assertions must be compared exactly with the observed source.


def match_result(value):
    fields(value, ("range", "partial", "groups", "histories", "prefix", "suffix"))
    for name in ("range", "prefix", "suffix"):
        range_pair(value[name])
    if type(value["partial"]) is not bool:
        raise ValueError("Partial must be a JSON boolean")
    groups, histories = value["groups"], value["histories"]
    if type(groups) is not list or not groups:
        raise ValueError("A found match must include indexed group zero")
    if type(histories) is not list or len(histories) != len(groups):
        raise ValueError("Every indexed capture must have a history array")
    for group, history in zip(groups, histories, strict=True):
        if group is not None:
            range_pair(group)
        if type(history) is not list:
            raise ValueError("A capture history must be an ordered array")
        for capture in history:
            range_pair(capture)
    if value["partial"] and groups[0] is not None:
        raise ValueError("A partial result retains its extent separately from unmatched group zero")


def successful_result(value, operation):
    if operation == "compile":
        fields(value, ("mark_count", "compile_status"))
        integer(value["compile_status"])
    elif operation == "replace":
        fields(value, ("mark_count", "output_hex"))
        hexadecimal(value["output_hex"])
    else:
        expected = ("mark_count", "matches", "output_hex") if operation == "format" else ("mark_count", "matches")
        fields(value, expected)
        matches = value["matches"]
        if type(matches) is not list or (operation != "iterate" and len(matches) > 1):
            raise ValueError("Invalid match-result array for the operation")
        for match in matches:
            match_result(match)
        if operation == "format":
            hexadecimal(value["output_hex"])
    integer(value["mark_count"])
    if value["mark_count"] < 0:
        raise ValueError("A capture count cannot be negative")


def reference_failure(value, operation):
    fields(value, ("schema", "phase", "kind", "code", "position", "message_hex"))
    if value["schema"] != "boostregexrs.reference-failure.v1":
        raise ValueError("Unknown reference-failure schema")
    phases = {"compile", "serialize", operation}
    if operation == "format":
        phases.add("search")
    if value["phase"] not in phases:
        raise ValueError("Reference failure phase does not belong to the requested operation")
    kind = value["kind"]
    if kind in ("regex", "regex_resource"):
        integer(value["code"])
        integer(value["position"])
        if (value["code"] in RESOURCE_CODES) != (kind == "regex_resource"):
            raise ValueError("Boost resource code has the wrong failure classification")
        if kind == "regex" and value["phase"] == "compile":
            raise ValueError("Ordinary compilation regex_error requires compile_error status")
    elif kind in ("allocation", "capacity", "runtime"):
        if value["code"] is not None or value["position"] is not None:
            raise ValueError("C++ failures without Boost fields must preserve null code and position")
    else:
        raise ValueError("Unknown reference-failure kind")
    hexadecimal(value["message_hex"])


def result_value(row, operation):
    value = json.loads(row[2], object_pairs_hook=unique_object, parse_constant=reject_constant)
    original = value
    status = row[1]
    preceding = None
    if type(value) is dict and "preceding_compile" in value:
        if operation == "compile" or status not in ("ok", "operation_error", "reference_failure",
                                                    "candidate_error", "candidate_resource_error"):
            raise ValueError("A preceding compilation requires a later operation result")
        preceding = value["preceding_compile"]
        successful_result(preceding, "compile")
        if preceding["compile_status"] == 0:
            raise ValueError("Preceding compilation records only a returned nonzero status")
        value = {key: item for key, item in value.items() if key != "preceding_compile"}
        if status == "reference_failure" and value.get("phase") == "compile":
            raise ValueError("A compilation exception cannot follow its own returned outcome")
    if status == "ok":
        successful_result(value, operation)
        if preceding is not None and value["mark_count"] != preceding["mark_count"]:
            raise ValueError("The operation's capture count differs from its compiled object")
    elif status in ("compile_error", "candidate_error", "candidate_resource_error"):
        fields(value, ("code", "position"))
        integer(value["code"])
        integer(value["position"])
    elif status == "operation_error":
        fields(value, ("category", "position", "message_hex"))
        if value["category"] not in ("invalid_argument", "invalid_match_options"):
            raise ValueError("Unknown operation-error category")
        if value["position"] is not None:
            integer(value["position"])
        hexadecimal(value["message_hex"])
    elif status in ("protocol_error", "reference_resource_error"):
        fields(value, ("message_hex",))
        hexadecimal(value["message_hex"])
    elif status == "reference_failure":
        reference_failure(value, operation)
    elif status == "unsupported":
        fields(value, ("reason",))
        if type(value["reason"]) is not str or not value["reason"]:
            raise ValueError("Unsupported results must identify the missing operation")
    elif status in ("reference_process_error", "candidate_process_error"):
        fields(value, ("exit_code", "timeout", "evidence"))
        if value["exit_code"] is not None:
            integer(value["exit_code"])
        if type(value["timeout"]) is not bool or type(value["evidence"]) is not str:
            raise ValueError("Invalid process-failure evidence")
    else:
        raise ValueError(f"Unknown result status: {status}")
    return original


def read_results(path, cases):
    rows = read_rows(path, OUTPUT_HEADER)
    if [row[0] for row in rows] != [row[0] for row in cases]:
        raise ValueError(f"Result rows are missing, reordered or unexpected: {path}")
    values = []
    for case, row in zip(cases, rows, strict=True):
        try:
            value = result_value(row, case[1])
            if "preceding_compile" in value and not (int(case[2]) & NO_EXCEPT):
                raise ValueError("A returned invalid compiled object requires no_except syntax")
            values.append(value)
        except (ValueError, TypeError) as error:
            raise ValueError(f"{case[0]}: {error}") from error
    return rows, values
