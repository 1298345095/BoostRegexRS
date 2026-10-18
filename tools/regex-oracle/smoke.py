"""Bounded complete-result smoke for the independently built native reference."""

from collections import Counter
import csv
import json
import re

from protocol import HEADER, read_cases, read_results


def write_rows(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def byte_cases():
    inputs = [
        ("compile-captures", "compile", b"(a)(b)?", b"", b"", 0, 0),
        ("compile-empty", "compile", b"", b"", b"", 0, 0),
        ("compile-error", "compile", b"(", b"", b"", 0, 0),
        ("search-byte-nul", "search", b"(a+)(b)?", b"\xffaa\x00b", b"", 0, 0),
        ("match-literal-nul", "match", b"a\x00b", b"a\x00b", b"", 2, 0),
        ("iterate-empty-progress", "iterate", b"a*", b"ba", b"", 0, 0),
        ("search-true-empty", "search", b"a*", b"", b"", 0, 0),
        ("capture-history", "search", b"(a|b)+", b"aba", b"", 0, 524288),
        ("partial", "search", b"abcd", b"abc", b"", 0, 8192),
        ("format-captures", "format", b"(a)(b)?", b"za", b"<$1:$2>$&", 0, 0),
        ("replace-nul", "replace", b"\x00", b"a\x00b\x00", b"\x00X", 2, 0),
        ("search-no-match", "search", b"a", b"b", b"", 0, 0),
        ("search-invalid-utf8-byte", "search", b"\xff", b"aa\xff", b"", 2, 0),
    ]
    return [(name, operation, syntax, flags, pattern.hex(), text.hex(), replacement.hex())
            for name, operation, pattern, text, replacement, syntax, flags in inputs]


def run_bytes(cache, command, env):
    path = cache / "smoke/byte-input.tsv"
    write_rows(path, HEADER, byte_cases())
    executable = str(cache / "bin/byte-reference")
    _, metadata_log = command([executable, "--metadata"], cache, "byte-metadata", env=env)
    metadata = json.loads(metadata_log.read_text())
    if metadata["boost"] != "1_89" or metadata["capture_history_compiled"] is not True:
        raise ValueError("The byte reference has the wrong version or capture-history configuration")
    _, output = command([executable], cache, "byte-smoke", env=env, input_path=path)
    cases = read_cases(path)
    rows, values = read_results(output, cases)
    counts = dict(sorted(Counter(row[1] for row in rows).items()))
    by_id = {row[0]: value for row, value in zip(rows, values, strict=True)}
    for row in rows:
        expected_status = "compile_error" if row[0] == "compile-error" else "ok"
        if row[1] != expected_status:
            raise ValueError(f"The bounded byte smoke failed: {row[0]} / {row[1]}")
    if by_id["compile-empty"] != {"mark_count": 0, "compile_status": 0}:
        raise ValueError("The empty pattern did not compile successfully with zero captures")
    if by_id["compile-captures"] != {"mark_count": 2, "compile_status": 0}:
        raise ValueError("The capture pattern did not compile successfully with both captures")
    if by_id["match-literal-nul"]["matches"][0]["range"] != [0, 3]:
        raise ValueError("The byte reference truncated embedded NUL")
    if by_id["search-true-empty"]["matches"][0]["range"] != [0, 0]:
        raise ValueError("The byte reference did not retain the true-empty match")
    if by_id["capture-history"]["matches"][0]["histories"][1] != [[0, 1], [1, 2], [2, 3]]:
        raise ValueError("The reference did not return every repeated capture")
    if by_id["replace-nul"]["output_hex"] != b"a\x00Xb\x00X".hex():
        raise ValueError("The byte reference truncated the replacement at NUL")
    if by_id["compile-error"] != {"code": 8, "position": 1}:
        raise ValueError("The compile error did not retain its Boost category and original byte position")
    return {"records": len(rows), "result_counts": counts, "metadata": metadata,
            "operations": sorted({case[1] for case in cases}),
            "schema": "complete byte results: ranges, all groups/history, prefix/suffix, output or error"}


def read_keys(path, expected):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream, delimiter="\t", strict=True)
        if next(reader, None) != ["case_id", "raw_icu_hex", "boost_u32_hex"]:
            raise ValueError(f"Malformed key output header: {path}")
        rows = list(reader)
    if any(len(row) != 3 for row in rows) or [row[0] for row in rows] != expected:
        raise ValueError(f"Incomplete or reordered key output: {path}")
    for _, raw, exposed in rows:
        if re.fullmatch(r"[0-9a-f]{2}(,[0-9a-f]{2})*", raw) is None:
            raise ValueError("Invalid full ICU byte key")
        if re.fullmatch(r"[0-9a-f]{8}(,[0-9a-f]{8})*", exposed) is None:
            raise ValueError("Invalid full Boost u32 key")
        raw_key = [int(value, 16) for value in raw.split(",")]
        boost_key = [int(value, 16) for value in exposed.split(",")]
        if raw_key[-1] != 0 or boost_key != (raw_key[:-1] if len(raw_key) > 1 else raw_key):
            raise ValueError("The observed Boost wrapper differs from its complete ICU key")
    return rows


def run_keys(cache, command, env):
    strings = [("ascii", "abc"), ("nul", "a\x00b"), ("combining", "e\u0301"),
               ("han", "漢字"), ("hangul", "가"), ("supplementary", "😀"),
               ("non-fcd", "a\u0315\u0300"), ("long", "a" * 101)]
    cases = [(name, value.encode("utf-8").hex()) for name, value in strings]
    executable = str(cache / "bin/sortkey-reference")
    result = {}
    for strength in ("primary", "identical"):
        rows = cases + ([("empty", "")] if strength == "primary" else [])
        path = cache / "smoke" / (strength + "-input.tsv")
        write_rows(path, ("case_id", "utf8_hex"), rows)
        metadata_path = cache / "smoke" / (strength + "-metadata.json")
        _, log = command([executable, "--strength", strength, "--metadata", str(metadata_path)],
                         cache, strength + "-smoke", env=env, input_path=path)
        keys = read_keys(log, [row[0] for row in rows])
        metadata = json.loads(metadata_path.read_text())
        expected = {"boost": "1.89.0", "icu": "77.1", "unicode": "16.0.0", "cldr": "47.0",
                    "locale": "root", "strength": strength}
        if any(metadata.get(name) != value for name, value in expected.items()):
            raise ValueError("Runtime Boost/ICU/Unicode/CLDR identity differs")
        result[strength] = {"valid_full_keys": len(keys), "metadata": metadata}
    empty = cache / "smoke/empty-input.tsv"
    write_rows(empty, ("case_id", "utf8_hex"), [("empty", "")])
    record, log = command([executable, "--strength", "identical"], cache, "empty-original-identical",
                          env=env, input_path=empty, check=False)
    if record["timed_out"] or record["launch_error"]:
        raise ValueError("The original empty-input diagnostic did not finish")
    original_status = "reference_error"
    if record["returncode"] == 0:
        read_keys(log, ["empty"])
        original_status = "valid_original_key"
    _, log = command([executable, "--strength", "identical", "--approved-empty-exception"],
                     cache, "empty-adr0005-identical", env=env, input_path=empty)
    expected = read_keys(log, ["empty"])[0]
    if expected[1:] != ["01,01,01,01,00", "00000001,00000001,00000001,00000001"]:
        raise ValueError("ADR-0005 root empty-key evidence differs")
    result["true_empty_identical"] = {"original_status": original_status,
                                      "original_exit_code": record["returncode"],
                                      "approved_exception_references": 1,
                                      "original_failure_preserved": original_status == "reference_error"}
    return result


def run_smoke(cache, command, env):
    (cache / "smoke").mkdir(parents=True)
    return {"byte": run_bytes(cache, command, env), "keys": run_keys(cache, command, env),
            "candidate_comparison_performed": False,
            "meaning": "Reference build/protocol smoke; not whole-library or six-platform compatibility"}
