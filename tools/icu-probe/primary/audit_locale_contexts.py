#!/usr/bin/env python3
"""Inventory source-reachable context inputs before running the owner oracle.

This audit checks every decoded exported context entry. Its output contains no
sort keys and cannot count as native/candidate compatibility evidence.
"""

import argparse
import json
from pathlib import Path
import tempfile

from run_locales import PRIMARY, contexts, identity, owner_context_report, read_data, read_owner, save


def audit(directory, output):
    catalog_path = directory / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    output.mkdir(parents=True, exist_ok=False)
    owners = []
    with tempfile.TemporaryDirectory(prefix="context-audit-", dir=output) as temporary:
        path = Path(temporary) / "contexts.json"
        for item in catalog["owner_files"]:
            owner = item["id"]
            source = PRIMARY / "data/root-icu77.bin" if owner == 0 else directory / item["file"]
            data = read_data(source) if owner == 0 else read_owner(source)
            if data["sha256"] != item["sha256"]:
                raise ValueError(f"Owner {owner} differs from frozen catalog")
            report = owner_context_report(data)
            save(path, report)
            expected = {(entry["index"], n) for entry in report["contexts"] for n in range(len(entry["entries"]))}
            actual, count = set(), 0
            for name, _ in contexts(path):
                category, label = name.split("/", 1)
                if category == "context":
                    _, index, entry, _ = label.split("-")
                    actual.add((int(index), int(entry)))
                count += 1
            owners.append({"owner": owner, "source": identity(source), "context_tries": len(report["contexts"]),
                           "context_entries": len(expected), "generated_context_inputs": count,
                           "indirect_triggers": sum("indirect_tag" in row for row in report["triggers"]),
                           "uncovered": sorted(expected - actual), "unexpected": sorted(actual - expected)})
    result = {"schema": "boostregexrs.icu77-context-source-coverage.v1",
              "status": "passed" if all(not row["uncovered"] and not row["unexpected"] for row in owners) else "incomplete",
              "scope": "source reachability preflight only; no key/CE comparison was performed",
              "catalog": identity(catalog_path), "owners": owners,
              "sources": [identity(Path(__file__)), identity(PRIMARY / "run_locales.py"),
                          identity(PRIMARY / "generate_cases.py"), identity(PRIMARY / "export/data_format.py")]}
    save(output / "summary.json", result)
    print(json.dumps({"status": result["status"], "owners": len(owners),
                      "context_entries": sum(row["context_entries"] for row in owners),
                      "generated_context_inputs": sum(row["generated_context_inputs"] for row in owners),
                      "uncovered": [row for row in owners if row["uncovered"] or row["unexpected"]]}))
    return int(result["status"] != "passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-directory", type=Path, default=PRIMARY / "data/locales")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return audit(args.data_directory.resolve(), args.output.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
