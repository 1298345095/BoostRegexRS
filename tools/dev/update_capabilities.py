#!/usr/bin/env python3
"""Refresh the acceptance inventory from the verified Boost 1.89.0 sources.

Preserve implementation/evidence decisions already recorded for each stable ID.
This inventory discovers work; generating it does not pass any capability.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re


REPO = Path(__file__).resolve().parents[2]
DESTINATION = REPO / "docs/development"
DEFAULT_SOURCE = REPO / "target/research/icu77-cloud/deps/boost_1_89_0"
UPSTREAM = "https://github.com/boostorg/regex/blob/boost-1.89.0/"

API = {
    "basic_regex": "construct assign flags mark_count pattern subexpression_locations named_subexpressions status compare swap imbue getloc",
    "regex_search": "search search_from search_range previous_context",
    "regex_match": "full_match",
    "match_result": "ready size empty indexed_capture named_capture prefix suffix position length format all_capture_histories partial_match",
    "sub_match": "matched range text compare",
    "regex_replace": "replace_all replace_first callback write_to",
    "regex_iterator": "iteration zero_width_progress error_once_then_end",
    "regex_token_iterator": "selected_groups multiple_groups unmatched_tokens trailing_unmatched",
    "regex_grep": "callback early_stop",
    "regex_split": "split captures input_consumption limit",
    "regex_traits": "translate translate_nocase transform transform_primary lookup_classname lookup_collatename isctype value length imbue getloc custom_single_thread custom_send_sync",
    "posix_api": "basic_extended_compile search captures error_categories execution_flags",
}

CONTRACTS = {
    "input": "arbitrary_bytes utf8 utf16 utf32 native_wide invalid_utf8 invalid_utf16 invalid_utf32 original_positions",
    "unicode": "fixed_data_version case_mapping classification digits names extended_names property_aliases primary_root identical_root complete_locales collation_types locale_aliases locale_fallback locale_settings system_default_getloc previous_imbue empty_key_exception",
    "native_traits": "c_locale cpp_locale win32_locale code_pages custom_collation custom_classes",
    "resources": "compile_work execution_work engine_memory output_budget match_count_budget explicit_limit_errors result_atomicity streaming_partial_output iterator_terminal_error independent_match_state",
    "platform": "windows_x64_msvc windows_arm64_msvc linux_x64_glibc linux_arm64_glibc macos_intel macos_arm64",
    "performance": "compile ordinary_search ordinary_captures ordinary_replace complex_syntax unicode short_inputs large_inputs backtracking_inputs engine_working_memory",
    "validation": "official_source_identity upstream_tests deterministic_generation fuzz_minimized_regressions all_option_interactions patched_consumer_reference sonar_quality_gate clean_checkout",
    "documentation": "public_api examples compatibility approved_exceptions build_test_instructions performance_protocol licenses",
}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def source_reference(relative):
    path = relative.as_posix()
    return UPSTREAM + (path.removeprefix("libs/regex/") if path.startswith("libs/") else "include/" + path)


def inventory(source):
    rows = []
    identities = {}

    def add(identity, group, title, relative=None, line=None):
        row = {"id": identity, "group": group, "capability": title,
               "upstream": source_reference(relative) if relative else "docs/adr/",
               "status": "not_implemented", "implementation": [], "tests": [],
               "evidence": [], "platforms_verified": [], "notes": ""}
        if relative:
            path = source / relative
            identities[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            if line:
                row["upstream"] += f"#L{line}"
        rows.append(row)

    for filename, pattern, group in (
        ("regbase.hpp", r"^\s{6}([A-Za-z][A-Za-z_0-9]*)\s*=", "syntax_option"),
        ("match_flags.hpp", r"^\s+((?:match|format)_[a-z_0-9]+)\s*=", "match_format_option"),
        ("error_type.hpp", r"^\s+(error_[a-z_]+)\s*=", "error_category"),
    ):
        relative = Path("boost/regex/v5") / filename
        for number, line in enumerate((source / relative).read_text().splitlines(), 1):
            if filename == "regbase.hpp" and "enum restart_info" in line:
                break
            match = re.match(pattern, line)
            if match:
                name = match.group(1)
                add(f"{group}.{name}", group, name, relative, number)
                if name in {"match_init", "match_unused1", "match_unused2", "match_unused3", "match_max", "match_not_any", "format_is_if"}:
                    rows[-1]["status"] = "mapping_pending"
                    rows[-1]["notes"] = "Upstream internal/sentinel flag: record public semantic applicability before closing."

    for filename in ("syntax_perl", "syntax_basic", "syntax_extended", "format_syntax", "format_boost_syntax", "format_sed_syntax"):
        relative = Path("libs/regex/doc") / f"{filename}.qbk"
        for number, line in enumerate((source / relative).read_text().splitlines(), 1):
            match = re.match(r"\[h[345] (.+)\]$", line)
            if match and match.group(1) not in {"Synopsis", "References", "Options"}:
                title = match.group(1)
                identity = f"{filename}.{slug(title)}"
                if not any(row["id"] == identity for row in rows):
                    add(identity, "syntax" if filename.startswith("syntax") else "format", title, relative, number)

    for filename, names in API.items():
        relative = Path("libs/regex/doc") / f"{filename}.qbk"
        for name in names.split():
            add(f"api.{filename}.{name}", "api", f"{filename}: {name}", relative)
    for group, names in CONTRACTS.items():
        for name in names.split():
            add(f"{group}.{name}", group, name)
    for path in sorted((source / "libs/regex/test").rglob("*.cpp")):
        relative = path.relative_to(source)
        add("upstream_test." + slug(str(path.relative_to(source / "libs/regex/test"))),
            "upstream_test", str(path.relative_to(source / "libs/regex/test")), relative)
        rows[-1]["status"] = "mapping_pending"
    return rows, identities


def render(document):
    lines = ["# Full compatibility capability matrix", "",
             "Tracked by [issue #2](https://github.com/1298345095/BoostRegexRS/issues/2). "
             "Generated from the verified Boost 1.89.0 public options, error categories, "
             "syntax documentation, API families and upstream test files. "
             "Individual interactions are added as source review and counterexamples identify them.", "",
             "`not_implemented` and `mapping_pending` are open work. `implemented` requires tests; "
             "`reference_passed` requires linked actual comparison evidence. Platform and performance "
             "acceptance remain separate dimensions. A research prototype result does not imply "
             "that the public library implements that capability.", "",
             "Edit per-ID decisions in capability-matrix.json; regenerate with "
             "`python3 -B tools/dev/update_capabilities.py`. No existing decision is reset by regeneration.", ""]
    groups = dict.fromkeys(row["group"] for row in document["capabilities"])
    for group in groups:
        lines += [f"## {group}", "", "| ID / capability | Status | Implementation / tests / evidence |", "| --- | --- | --- |"]
        for row in document["capabilities"]:
            if row["group"] != group:
                continue
            links = row["implementation"] + row["tests"] + row["evidence"]
            details = "; ".join(f"`{item}`" for item in links) or "Pending"
            upstream = "../adr/" if row["upstream"] == "docs/adr/" else row["upstream"]
            lines.append(f"| [{row['id']}]({upstream}) | {row['status']} | {details} |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boost-source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    version = (args.boost_source / "boost/version.hpp").read_text()
    if not re.search(r"#define BOOST_VERSION 108900\b", version):
        raise RuntimeError("The capability inventory requires Boost 1.89.0")
    destination = DESTINATION / "capability-matrix.json"
    old = json.loads(destination.read_text()) if destination.exists() else {"capabilities": []}
    existing = {row["id"]: row for row in old["capabilities"]}
    rows, identities = inventory(args.boost_source)
    for row in rows:
        previous = existing.pop(row["id"], {})
        for field in ("status", "implementation", "tests", "evidence", "platforms_verified", "notes"):
            if field in previous:
                row[field] = previous[field]
    rows.extend(existing.values())
    document = {"schema": 1, "baseline": "Boost.Regex 1.89.0", "tracking_issue": 2,
                "source_sha256": identities, "capabilities": rows}
    DESTINATION.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    (DESTINATION / "capability-matrix.md").write_text(render(document))
    print(f"Recorded {len(rows)} capability/test rows from {len(identities)} upstream files")


if __name__ == "__main__":
    main()
