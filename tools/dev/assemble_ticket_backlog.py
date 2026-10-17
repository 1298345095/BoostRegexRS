#!/usr/bin/env python3
"""Reproduce the reviewed paused backlog from the preserved planning drafts.

This is documentation tooling. It does not build, run or change the library.
The explicit maps below resolve draft lane placeholders to concrete tickets.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "docs/development/tickets"
PLANNING = STORE / "planning"
BOOST = "https://github.com/boostorg/regex/blob/boost-1.89.0/"
ICU = "https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/"
ADRS = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "docs/adr").glob("*.md"))


def unique(values):
    return list(dict.fromkeys(values))


def read(name):
    return json.loads((PLANNING / f"{name}-draft.json").read_text(encoding="utf-8"))


def describe(record):
    return " ".join(f"{key.replace('_', ' ').capitalize()}: {value}" for key, value in record.items())


def expand_braces(value):
    match = re.search(r"\{([^{}]+)\}", value)
    if not match:
        return [value]
    return [
        expanded
        for part in match.group(1).split(",")
        for expanded in expand_braces(value[:match.start()] + part + value[match.end():])
    ]


def unicode_sources(source_map):
    references = []
    for source in source_map:
        kind, separator, remainder = source.partition(":")
        if not separator:
            references.append(source)
            continue
        path = remainder.split("::", 1)[0].split(" and ", 1)[0]
        for expanded in expand_braces(path):
            if kind == "icu":
                references.append(ICU + expanded)
            elif kind == "boost":
                if expanded.startswith(("include/", "src/", "test/")):
                    relative = expanded
                elif expanded == "icu.hpp":
                    relative = "include/boost/regex/icu.hpp"
                elif expanded.startswith("pending/"):
                    relative = "include/boost/regex/" + expanded
                else:
                    relative = "include/boost/regex/v5/" + expanded
                references.append(BOOST + relative)
            else:
                references.append(expanded)
    return unique(references)


def byte_tickets(draft):
    for source in draft["tickets"]:
        acceptance = [
            text for text in source["acceptance_criteria"]
            if not text.startswith("All shared_acceptance requirements")
        ] + draft["shared_acceptance"]
        blockers = source["blocked_by"] + ["V03"]
        if source["id"] == "B39":
            blockers += ["N03", "N05", "N06"]
        yield {
            "id": source["id"], "title": source["title"],
            "kind": source["kind"], "workstream": "Byte regex and public operations",
            "blocked_by": unique(blockers), "external_dependencies": [],
            "capabilities": unique(source["capability_ids"]),
            "problem": source["outcome"], "current_state": describe(source["checkpoint"]),
            "deliverables": source["scope"], "acceptance": acceptance,
            "source_refs": unique(ADRS + [item.get("upstream_url", BOOST + item["path"])
                                          for item in source["source_map"]]
                                  + ["docs/development/byte-engine-architecture.md"]),
            "sizing": source["context_window_boundary"],
            "notes": ["Validation partition: " + item for item in source["validation_partitions"]]
                     + [f"Source functions: {item['path']} — {item['symbols']} (pinned-source lines {item.get('lines', 'see file')})."
                        for item in source["source_map"]]
                     + ["Likely implementation/test location: " + path for path in source["target_paths"]]
                     + ["Coordinate with the linked capability workstream: " + item["reason"]
                        for item in source.get("external_dependencies", [])]
                     + ["Upstream semantic coverage (full-file ownership is in V04–V10): " + key
                        for key in source["upstream_test_ids"]],
        }


UNICODE_CAPABILITIES = {
    "U01": ["unicode.complete_locales", "unicode.locale_settings"],
    "U02": ["unicode.complete_locales", "unicode.collation_types"],
    "U03": ["unicode.locale_settings", "unicode.collation_types"],
    "U04": ["unicode.fixed_data_version", "unicode.primary_root", "unicode.identical_root",
            "api.regex_traits.transform", "api.regex_traits.transform_primary"],
    "U05": ["unicode.locale_aliases"], "U06": ["unicode.locale_aliases"],
    "U07": ["unicode.locale_aliases", "unicode.locale_settings"],
    "U08": ["unicode.locale_fallback", "unicode.collation_types"],
    "U09": ["unicode.locale_settings"],
    "U10": ["unicode.complete_locales", "unicode.locale_fallback", "unicode.collation_types"],
    "U11": ["unicode.system_default_getloc", "unicode.previous_imbue", "api.regex_traits.getloc",
            "api.regex_traits.imbue", "api.basic_regex.getloc", "api.basic_regex.imbue"],
    "U12": ["unicode.system_default_getloc", "unicode.previous_imbue"],
    "U13": ["unicode.system_default_getloc", "unicode.previous_imbue"],
    "U14": ["unicode.empty_key_exception"],
    "U15": ["unicode.case_mapping", "api.regex_traits.translate", "api.regex_traits.translate_nocase"],
    "U16": ["unicode.classification", "api.regex_traits.isctype"],
    "U17": ["unicode.property_aliases", "api.regex_traits.lookup_classname"],
    "U18": ["unicode.digits", "api.regex_traits.value"],
    "U19": ["unicode.names", "api.regex_traits.lookup_collatename"],
    "U20": ["unicode.extended_names", "unicode.names", "api.regex_traits.lookup_collatename"],
    "U21": ["api.regex_traits." + name for name in (
        "translate", "translate_nocase", "transform", "transform_primary", "lookup_classname",
        "lookup_collatename", "isctype", "value", "length", "imbue", "getloc")],
    "U22": ["unicode.case_mapping", "syntax_option.icase"]
           + [f"syntax_{grammar}.back_references" for grammar in ("perl", "basic", "extended")],
    "U23": ["unicode.classification", "unicode.property_aliases", "syntax_option.no_char_classes",
            "error_category.error_ctype"]
           + [f"syntax_{grammar}.{feature}" for grammar in ("perl", "basic", "extended")
              for feature in ("character_sets", "character_ranges", "negation", "character_classes")]
           + [f"syntax_{grammar}.{feature}" for grammar in ("perl", "extended")
              for feature in ("single_character_character_classes", "character_properties", "word_boundaries")],
    "U24": ["syntax_perl.matching_line_endings", "syntax_perl.unicode_escapes",
            "syntax_extended.unicode_escapes", "syntax_perl.single_character_character_classes"]
           + [f"syntax_{grammar}.{feature}" for grammar in ("perl", "basic", "extended")
              for feature in ("wildcard", "anchors")],
    "U25": [f"syntax_{grammar}.{feature}" for grammar in ("perl", "basic", "extended")
            for feature in ("collating_elements", "equivalence_classes", "character_ranges")]
           + ["syntax_option.collate", "syntax_option.nocollate", "error_category.error_collate"],
    "U26": ["unicode.fixed_data_version", "documentation.licenses", "validation.clean_checkout"],
}


def unicode_tickets(draft):
    evidence = {item["id"]: item for item in draft["prerequisites"]}
    engine = {"U22": ["B12", "B21", "B26"], "U23": ["B06", "B22", "B26"],
              "U24": ["B05", "B22", "B26"], "U25": ["B07", "B25", "B26"]}
    for source in draft["tickets"]:
        identity = source["id"]
        if identity in ("U27", "U28"):
            continue  # Obligations are transferred below, not discarded.
        blockers, notes, evidence_refs = [], [], []
        for blocker in source["blocked_by"]:
            if blocker.startswith("E_"):
                item = evidence[blocker]
                notes.append((f"Existing prerequisite {blocker} ({item['status']}): "
                              + item.get("result", "See immutable evidence.") + " " + item.get("boundary", "")).rstrip())
                evidence_refs += item.get("evidence", [])
            elif blocker == "X_ENGINE_SEMANTICS":
                blockers += engine[identity]
            elif blocker == "X_COMPLETE_RESULT_ORACLE":
                blockers += ["V03"]
            elif blocker == "X_SIX_TARGET_CI":
                blockers += ["P05", "P06"] if identity == "U12" else ["P07", "P08"]
            else:
                blockers.append(blocker)
        if identity == "U11":
            blockers += ["P03", "P04"]
        scope = source["vertical_slice"]
        yield {
            "id": identity, "title": source["title"], "kind": source["kind"],
            "workstream": "Fixed Unicode and ICU locale behavior",
            "blocked_by": unique(blockers), "external_dependencies": [],
            "capabilities": UNICODE_CAPABILITIES[identity],
            "problem": scope["behavior"], "current_state": describe(source["current_checkpoint"]),
            "deliverables": ["Entry point: " + scope["entry_point"]] + scope["in_scope"],
            "acceptance": source["acceptance"] + draft["common_acceptance"],
            "source_refs": unique(ADRS + unicode_sources(source["source_map"]) + evidence_refs),
            "sizing": source["one_context_bound"],
            "notes": notes + ["Pinned source detail: " + item for item in source["source_map"]]
                     + ["Separate scope: " + item for item in scope["excludes"]]
                     + ["Future evidence location: " + source["evidence_output"]],
        }


INTEGRATION_EXTERNALS = {
    "byte_checkpoint_replay_harness": ["V03"],
    "unicode_character_rules": ["U21"], "unicode_traits_production": ["U21"],
    "byte_formatter_acceptance": ["B38"],
    "byte_iteration_acceptance": ["B29", "B31"],
    "windows_reference_environment": ["P05", "P06"],
    "byte_core_checkpoint": ["V03"],
    "byte_core_independent_acceptance": ["B13", "B17", "B20", "B23", "B25"],
}


def integration_tickets(draft):
    for source in draft["tickets"]:
        ticket = copy.deepcopy(source)
        for dependency in ticket.pop("external_dependencies", []):
            ticket["blocked_by"] += INTEGRATION_EXTERNALS[dependency]
        # Native backend implementation needs an actual native reference, not the later package CI.
        reference = {"N03": ["P03", "P04"], "N04": ["P03", "P04"],
                     "N05": ["P07", "P08"], "N06": ["P05", "P06"],
                     "N07": ["P05", "P06"], "N11": ["P07", "P08"],
                     "N12": ["P05", "P06"]}
        ticket["blocked_by"] = unique(ticket["blocked_by"] + reference.get(ticket["id"], []))
        ticket["external_dependencies"] = []
        if ticket["id"].startswith("R"):
            ticket["workstream"] = "Resources and delivery semantics"
        elif ticket["id"].startswith("N"):
            ticket["workstream"] = "Native and custom character rules"
        else:
            ticket["workstream"] = "Input adapters and migration"
        yield ticket


def validation_blockers(source):
    identity = source["id"]
    # Family-specific concrete prerequisites keep byte grammar acceptance independent
    # of the later native/Unicode package wherever its source family permits it.
    core = {
        "V04": ["B03", "B04", "B06", "B10", "B11", "B12", "B22"],
        "V05": ["B09", "B19", "B20", "B21", "B23", "B24", "B25"],
        "V06": ["B21", "B23", "B24", "B26", "B27"],
        "V07": ["B31", "B38", "B40", "P10"],
        "V08": ["B07", "B12", "B22", "B25"],
        "V09": ["B14", "B17", "B20", "B25"],
    }.get(identity, ["B09", "B21", "B24", "B25", "B27", "B40"])
    results = ["B22", "B23", "B26", "B27"]
    streams = ["B29", "B31", "B38"]
    unicode = ["U12", "U13", "U22", "U23", "U24", "U25", "U26"]
    native = ["N02", "N04", "N07", "N08", "N09", "N10", "N11", "N12"]
    if identity in ("V21", "V22"):
        native = ["N02", "N06", "N07", "N08", "N09", "N10", "N12"]
    elif identity in ("V23", "V24"):
        native = ["N02", "N03", "N04", "N09", "N10"]
    elif identity in ("V25", "V26"):
        native = ["N02", "N05", "N09", "N10", "N11"]
    inputs = ["B22"] if identity in ("V04", "V16") else ["I10"]
    aliases = {
        "X_CORE_RUNTIME": core, "X_API_RESULTS": results, "X_API_STREAM_FORMAT": streams,
        "X_UNICODE_COLLATION": unicode, "X_NATIVE_CUSTOM_TRAITS": native,
        "X_INPUT_POSITIONS": inputs, "X_RESOURCE_THREAD_CONTRACT": ["R04", "N02"],
        "X_DEFAULT_FEATURE_SURFACE": [] if identity in ("V27", "V38") else ["P09"],
        "X_CONSUMER_SOURCE": ["P02", "P05", "P06"],
        "X_NATIVE_RUNNERS": [f"P{number:02}" for number in range(3, 9)],
        # Availability/noise is qualified in the protocol and actual measurement
        # tickets; do not invent an external infrastructure purchase as a blocker.
        "X_STABLE_BENCH_HOSTS": [], "X_SONAR_ISSUE_CONTROL": ["P01"],
        "X_SONAR_ANALYSIS_CONTROL": [],
    }
    return unique(item for key in source["blocked_by"] for item in aliases.get(key, [key]))


def validation_tickets(draft):
    for source in draft["tickets"]:
        identity = source["id"]
        if identity in ("V01", "V03"):
            state = ("Pinned cloud Boost/ICU sources and root key evidence exist. The retained byte native run "
                     "has 20,212 records; subsequent protocol/generator/adapter edits are unbuilt and unverified. "
                     "No complete independent Rust byte comparison exists.")
        elif identity == "V02":
            state = ("The paused checkpoint now preserves 629 source/data files, 433 selected evidence files "
                     "and the complete 21,677-file failed locale run. Original archives were byte-verified without "
                     "new experiments; audit the complete cross-environment ledger and remaining provenance obligations.")
        elif identity in ("V37", "V38", "V39"):
            state = ("The observed Sonar gate failed New Code Security Rating E versus required A. Historical "
                     "reads contain 89 open issues and 18 security flows. Installed Sonar skills are visible but "
                     "no callable Sonar tool or management authority was established at pause. Direct Rust "
                     "format/lint drivers ran; normal Cargo launcher commands failed on missing /proc/self/exe.")
        elif 20 <= int(identity[1:]) <= 36:
            state = ("Six native research-crate CI jobs on 1b0149ef passed 19 executable tests each with Rust "
                     "1.99.1 and zero doctest cases. They do not establish complete-library platform, native "
                     "reference, performance or memory acceptance; those obligations remain open.")
        else:
            state = ("Root PRIMARY and IDENTICAL research evidence is published. The byte implementation and "
                     "locale work remain unfinished checkpoints: 35 local byte tests lack archived raw output, "
                     "the locale run retained two differences, and the written FCD repair is unbuilt/untested. "
                     "This ticket's complete-library acceptance has not run.")
        workstream = "Compatibility and independent testing"
        if identity in ("V01", "V02", "V03"):
            workstream = "Reference and evidence infrastructure"
        elif 20 <= int(identity[1:]) <= 26:
            workstream = "Six native platform acceptance"
        elif 27 <= int(identity[1:]) <= 36:
            workstream = "Performance and memory acceptance"
        elif identity in ("V37", "V38", "V39"):
            workstream = "Sonar and code quality"
        elif int(identity[1:]) >= 40:
            workstream = "Documentation and final package acceptance"
        assigned = [item for item in draft["upstream_assignments"]
                    if item["applicability_owner_ticket"] == identity]
        yield {
            "id": identity, "title": source["title"], "kind": "acceptance_vertical",
            "workstream": workstream, "blocked_by": validation_blockers(source),
            "external_dependencies": [], "capabilities": source["capability_rows"],
            "problem": source["objective"], "current_state": state,
            "deliverables": source["deliverables"], "acceptance": source["acceptance_criteria"],
            "source_refs": unique(source["source_refs"] + [item["source_url"] for item in assigned]),
            "sizing": ("One fresh context: use the accepted implementation and reusable harness for this "
                       "named family, target, measurement pack or audit. A newly discovered implementation "
                       "mechanism or substantial optimization becomes a bounded blocking ticket; keep this "
                       "gate open until its linked fix passes. " + source["scope_boundary"]),
            "notes": [f"Full upstream file owner: {item['capability_id']} — {item['source_path']}. "
                      + item["cross_family_rule"] for item in assigned],
        }


def apply_review(tickets, unicode_draft):
    by_id = {ticket["id"]: ticket for ticket in tickets}
    by_id["P09"]["blocked_by"] = ["B09", "B31", "B38", "B40", "P10", "I10", "N02",
                                        "N09", "N10", "U12", "U13", "U22", "U23", "U24", "U26", "R04"]
    # U27/U28 are duplicate acceptance orchestration, not omitted functionality.
    drafts = {ticket["id"]: ticket for ticket in unicode_draft["tickets"]}
    by_id["V15"]["acceptance"] += [drafts["U27"]["acceptance"][index] for index in (0, 2, 3, 4)]
    by_id["V15"]["deliverables"] += drafts["U27"]["vertical_slice"]["in_scope"][1:]
    for number in range(21, 27):
        by_id[f"V{number}"]["acceptance"] += [
            "On this actual native target, all declared Unicode operation families compare complete "
            "observable outputs, including capture histories, original half-open positions, prefix/suffix, "
            "iterations, formatting and typed failures; cover malformed-input timing, direct32 input domains, "
            "true-empty exceptions, locale defaults and conditional sharing. Component/research-only success "
            "cannot substitute for this public-operation gate."
        ]
        by_id[f"V{number}"]["notes"].append("Includes this target's obligations from draft U27; no duplicate six-target gate is created.")
    by_id["V36"]["acceptance"] += drafts["U28"]["acceptance"]
    by_id["V36"]["deliverables"] += drafts["U28"]["vertical_slice"]["in_scope"]
    by_id["V36"]["notes"].append("Includes draft U28's Unicode benchmark pack and every acceptance obligation.")
    by_id["V27"]["acceptance"].append(
        "Freeze the complete workload/measurement contract before acceptance measurements; exercise only a "
        "bounded existing byte tracer for early harness calibration. Package assembly is not a prerequisite "
        "for defining this protocol. Host suitability is established with measured noise/availability; absent "
        "resources are reported concretely, not assumed missing or counted as passes.")
    quality = by_id["V38"]
    quality.update({
        "title": "Make whole-library format, lint, build and documentation checks reproducible",
        "blocked_by": [],
        "capabilities": ["validation.clean_checkout", "documentation.build_test_instructions"],
        "problem": "Provide a reproducible quality-check path for the actual Rust library and active "
                   "development tools while preserving the independently required remote Sonar gate.",
        "deliverables": [
            "Tracked local and CI commands for format, warnings-as-errors lint, build, tests, documentation "
            "and applicable Python/C++ checks, with actual scope and tool identities.",
            "A source-backed diagnosis of the Cargo format/clippy launcher failure and a portable invocation "
            "path; record direct-driver checks separately when a restricted environment cannot launch Cargo tooling.",
        ],
        "acceptance": [
            "The defined checks execute on the current implemented library and active tools with recorded "
            "commands, versions, exits and logs; a research-only or zero-case run is never labeled whole-library acceptance.",
            "The missing /proc/self/exe/current_exe failure is reproduced and accurately attributed; the "
            "documented command works in its claimed supported environment without hiding source diagnostics.",
            "Real format/lint/build/doc failures are fixed or remain explicitly blocking. Checks are not "
            "weakened, disabled or narrowed to make a candidate pass; final candidate execution is required by V43.",
            "Any change to the existing Sonar analysis setup uses observed supported capabilities and current "
            "authority. Rust-capable Sonar migration, paid features, new credentials and changed gates are "
            "not prerequisites invented by this ticket; current analysis scope and uncovered languages stay explicit.",
            "The quality workflow is reproducible from tracked commands outside target, and documentation "
            "distinguishes local checks from V39's actual server-side gate.",
        ],
    })
    by_id["V39"]["blocked_by"] = ["V37"]
    by_id["V39"]["problem"] = "Close the real server-side gate with unambiguous source attribution after scoped findings are resolved."
    by_id["V43"]["blocked_by"] += ["V38"]
    by_id["V43"]["acceptance"].append(
        "Run V38's complete format/lint/build/test/documentation checks on the exact final candidate; "
        "an earlier checkpoint's launcher workaround or quality result cannot silently accept changed sources.")
    by_id["V40"]["title"] = "Audit complete public API documentation and execute the assembled examples"
    by_id["V40"]["sizing"] = (
        "One fresh context: audit and execute documentation/examples delivered by the individual feature "
        "tickets. Missing substantial documentation is a bounded blocker owned by that feature; this final "
        "audit does not author the entire API manual from scratch.")
    by_id["U01"]["notes"] = [
        note.replace("Full 538-configuration acceptance, owned by U03",
                     "The 538-configuration settings matrix belongs to U03; complete owner/context sweeps belong to U02")
        for note in by_id["U01"]["notes"]
    ]
    # Preserve the exact accepted non-modernized meaning of Boost's Unicode operators.
    by_id["U24"]["acceptance"].append(
        "Derive combining-sequence and line-separator behavior from Boost 1.89.0's fixed is_combining/"
        "is_separator implementation; do not substitute a current UAX #29 grapheme algorithm.")
    by_id["U04"]["acceptance"][1] = (
        "Production calls reproduce the frozen root and accepted owner/settings fixtures byte-for-byte. "
        "Preserve typed malformed-sort-key errors, explicit lengths and embedded NUL; original-unit error "
        "locations are required where the source/API contract exposes them.")
    by_id["U10"]["acceptance"][1] = (
        "Requests rejected by the native constructor produce matching typed failures. Source-accepted "
        "truncation, partial parsing and fallback remain accepted, and processing continues with the next "
        "CLI row; process signals and data loading failures are never counted as compatible output.")
    by_id["U21"]["acceptance"].append(
        "The callable traits facade implements source-equivalent terminator-based length, distinguished "
        "from explicit-range length. Explicit ranges retain embedded NUL; this primitive is available "
        "before any Unicode regex adapter.")
    by_id["U26"]["acceptance"][2] = (
        "All collation/locale/rules services and fixed data delivered by the prerequisites are enabled by "
        "default; the complete Unicode regex operation surface remains separately gated by U22-U24, "
        "V15 and the six native acceptance tickets. No opt-in feature silently removes promised scope.")
    for ticket in tickets:
        for field in ("blocked_by", "capabilities", "deliverables", "acceptance", "source_refs", "notes"):
            if field in ticket:
                ticket[field] = unique(ticket[field])
        if any(key.startswith(("X_", "E_", "EXT_")) for key in ticket["blocked_by"]):
            raise ValueError(f"Unresolved dependency in {ticket['id']}")


def main():
    byte, unicode, integration, validation, prerequisite = (
        read(name) for name in ("byte", "unicode", "integration", "validation", "prerequisite")
    )
    tickets = (copy.deepcopy(prerequisite["tickets"]) + list(byte_tickets(byte))
               + list(unicode_tickets(unicode)) + list(integration_tickets(integration))
               + list(validation_tickets(validation)))
    apply_review(tickets, unicode)
    document = {
        "schema": "boostregexrs.remaining-tickets.v1", "state": "paused",
        "created_date": "2026-10-17", "skill": "to-tickets", "parent_issue": 2,
        "base_commit": "1b0149efb649bcec7b5d6c4c0be2f7e403189cea",
        "final_acceptance_ticket": "V43",
        "merged_draft_tickets": {"U27": ["V15", "V21", "V22", "V23", "V24", "V25", "V26"],
                                 "U28": ["V36"]},
        "upstream_file_ownership": validation["upstream_assignments"],
        "tickets": tickets,
    }
    (STORE / "backlog.json").write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"tickets": len(tickets), "implementation": "paused", "output": str(STORE / "backlog.json")}))


if __name__ == "__main__":
    main()
