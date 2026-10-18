#!/usr/bin/env python3
"""Verify the retained native resource-error counterexample before and after repair."""

import argparse
import json
from pathlib import Path

from protocol import read_cases, read_results
from resource_cases import cases, no_except_flow_cases, stack_cases
from source_identity import sha256


def file_records(cases_path, before_path, after_path):
    return {key: {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for key, path in (("cases", cases_path), ("before", before_path), ("after", after_path))}


def verify(cases_path, before_path, after_path, *, stack_only=False):
    inputs = read_cases(cases_path)
    if inputs != list(stack_cases() if stack_only else cases()):
        raise ValueError("Resource regression inputs differ from the source-defined probes")
    before_rows, before_values = read_results(before_path, inputs)
    after_rows, after_values = read_results(after_path, inputs)
    phases = ({"match-stack-limit": ("match", 19, 0)} if stack_only else
              {"compile-nesting-limit": ("compile", 18, 400), "search-state-limit": ("search", 18, 0),
               "match-state-limit": ("match", 18, 0), "iterate-state-limit": ("iterate", 18, 0),
               "format-state-limit": ("search", 18, 0), "replace-state-limit": ("replace", 18, 0)})
    repaired = []
    unchanged = []
    enriched = []
    original_values = {case[0]: value for case, value in zip(inputs, before_values, strict=True)}
    for case, old, new, old_value, new_value in zip(inputs, before_rows, after_rows, before_values, after_values, strict=True):
        name = case[0]
        if name not in phases:
            payload = new_value
            if "preceding_compile" in new_value:
                if (name != "invalid-no-except-search" or
                        new_value["preceding_compile"] != original_values["ordinary-no-except"]):
                    raise ValueError(f"Unexpected preceding compiled-object observation: {name}")
                payload = {key: value for key, value in new_value.items() if key != "preceding_compile"}
                enriched.append({"case_id": name, "preceding_compile": new_value["preceding_compile"]})
            else:
                unchanged.append(name)
            if old[1] != new[1] or old_value != payload:
                raise ValueError(f"Unrelated normal/no_except/error behavior changed: {name}")
            continue
        phase, code, position = phases[name]
        if old[1] != "compile_error" or old_value != {"code": code, "position": position}:
            raise ValueError(f"Original source-defined counterexample was not reproduced: {name}")
        expected = {"schema": "boostregexrs.reference-failure.v1", "phase": phase,
                    "kind": "regex_resource", "code": code, "position": position}
        if (new[1] != "reference_failure" or
                any(new_value[key] != value for key, value in expected.items()) or not new_value["message_hex"]):
            raise ValueError(f"Native resource classification still wrong: {name}")
        repaired.append({"case_id": name, **expected})
    if len(repaired) != len(phases) or len(unchanged) + len(enriched) != len(inputs) - len(phases):
        raise ValueError("Resource regression totals do not reconcile")
    return {"schema": "boostregexrs.native-resource-regression.v1", "status": "passed",
            "records": len(inputs), "repaired": repaired, "unchanged": unchanged, "enriched": enriched,
            "execution_complexity_cases": 0 if stack_only else 5, "compile_complexity_cases": 0 if stack_only else 1,
            "execution_stack_cases": int(stack_only),
            "not_executed": ["allocator exhaustion", "catalog failure"] + ([] if stack_only else ["stack block exhaustion"]),
            "scope": "Native reference classification; not Rust resource-threshold equivalence",
            "files": file_records(cases_path, before_path, after_path)}


def verify_no_except_flow(cases_path, before_path, after_path):
    inputs = read_cases(cases_path)
    if inputs != list(no_except_flow_cases()):
        raise ValueError("No-except flow inputs differ from the source-defined probes")
    before_rows, before_values = read_results(before_path, inputs)
    after_rows, after_values = read_results(after_path, inputs)
    before = {row[0]: (row[1], value) for row, value in zip(before_rows, before_values, strict=True)}
    after = {row[0]: (row[1], value) for row, value in zip(after_rows, after_values, strict=True)}
    enriched = []
    unchanged = []
    compiled = {}
    for kind, code in (("resource", 18), ("syntax", 8)):
        name = f"no-except-{kind}-compile"
        old_status, old_value = before[name]
        if old_status != "ok" or old_value["compile_status"] != code or after[name] != before[name]:
            raise ValueError(f"The native no_except compiled object was not preserved: {name}")
        compiled[kind] = old_value
        unchanged.append(name)
        for operation in ("search", "match", "iterate", "format", "replace"):
            name = f"no-except-{kind}-{operation}"
            old_status, old_value = before[name]
            new_status, new_value = after[name]
            if (old_status != "operation_error" or old_value["category"] != "invalid_argument"
                    or old_value["position"] is not None or not old_value["message_hex"]):
                raise ValueError(f"The native invalid-object precondition was not observed: {name}")
            if new_value.get("preceding_compile") != compiled[kind]:
                raise ValueError(f"The later operation lost its returned compilation outcome: {name}")
            payload = {key: value for key, value in new_value.items() if key != "preceding_compile"}
            if new_status != old_status or payload != old_value:
                raise ValueError(f"The actual later operation error changed: {name}")
            enriched.append(name)
    for case in inputs:
        name = case[0]
        if name in enriched or name in unchanged:
            continue
        if after[name] != before[name] or "preceding_compile" in after[name][1]:
            raise ValueError(f"An ordinary valid-object result changed: {name}")
        status, value = after[name]
        if name == "no-except-valid-invalid-policies":
            if status != "operation_error" or value["category"] != "invalid_match_options":
                raise ValueError("The independent invalid-match-policy result was not observed")
        elif status != "ok":
            raise ValueError(f"An ordinary valid no_except operation did not return: {name}")
        unchanged.append(name)
    if len(enriched) != 10 or len(unchanged) != 8:
        raise ValueError("No-except flow totals do not reconcile")
    return {"schema": "boostregexrs.no-except-flow-regression.v1", "status": "passed", "records": len(inputs),
            "enriched": enriched, "unchanged": unchanged, "observed_compiled_objects": compiled,
            "later_native_errors_preserved": 10, "compile_exception_or_position_invented": False,
            "scope": "Native returned compilation and subsequent operation observations; not Rust resource thresholds",
            "files": file_records(cases_path, before_path, after_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cases", "before", "after", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stack-only", action="store_true")
    group.add_argument("--no-except-flow-only", action="store_true")
    args = parser.parse_args()
    if args.no_except_flow_only:
        result = verify_no_except_flow(args.cases, args.before, args.after)
    else:
        result = verify(args.cases, args.before, args.after, stack_only=args.stack_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError("Do not overwrite retained native regression evidence")
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
