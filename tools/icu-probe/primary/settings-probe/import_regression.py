#!/usr/bin/env python3
"""Import exact native fields/keys for the retained minimized reorder failure."""

import argparse
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from run_locales import identity, rows, save, sha256

FIELDS = ("case_id", "status", "implementation_error", "before_codes", "after_codes",
          "before_primary", "before_identical", "primary", "secondary", "tertiary", "quaternary", "identical")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--reduction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inspection = json.loads((args.inspection / "summary.json").read_text())
    reduced = json.loads((args.reduction / "summary.json").read_text())
    if inspection["codes"] != reduced["minimal_codes"] or reduced["status"] != "one_deletion_minimal_counterexample":
        raise ValueError("Inspection and minimized failure do not identify the same code list")
    code_text = ",".join(map(str, reduced["minimal_codes"]))
    selected = None
    for batch in reduced["batches"]:
        directory = args.reduction / batch["path"]
        for case, native in zip(rows(directory / "inputs.tsv", ("case_id", "setup_codes", "request_codes", "u16_hex")),
                                rows(directory / "native.tsv", FIELDS), strict=True):
            if case["request_codes"] == code_text:
                if native["status"] != "U_ZERO_ERROR" or case["u16_hex"] != "0061" or case["setup_codes"] != "~":
                    raise ValueError("Unexpected native regression state")
                if selected and any(native[key] != selected[0][key] for key in FIELDS[1:]):
                    raise ValueError("Repeated native regression rows disagree")
                selected = native, directory / "native.tsv"
    if selected is None:
        raise ValueError("No actual native key output for the minimized code list")
    original_binary = args.inspection / "native-settings.bin"
    if sha256(original_binary) != inspection["native_settings"]["sha256"]:
        raise ValueError("Native settings field bytes changed after inspection")
    args.output.mkdir(parents=True, exist_ok=False)
    binary = args.output / "wrapped-settings.bin"
    keys = args.output / "wrapped-a-keys.tsv"
    shutil.copyfile(original_binary, binary)
    with keys.open("w", encoding="utf-8", newline="") as stream:
        stream.write("strength\traw_icu_hex\n")
        for strength in FIELDS[-5:]:
            stream.write(f"{strength}\t{selected[0][strength]}\n")
    save(args.output / "provenance.json", {"schema": "boostregexrs.icu77-reorder-regression.v1",
         "icu": "77.1", "unicode": "16.0.0", "cldr": "47", "codes": reduced["minimal_codes"], "input_u16": "0061",
         "field_origin": identity(original_binary), "key_origin": identity(selected[1]),
         "key_origin_row": selected[0]["case_id"], "inspection": identity(args.inspection / "summary.json"),
         "reduction": identity(args.reduction / "summary.json"), "importer": identity(Path(__file__)),
         "command": [sys.executable, *sys.argv], "fixtures": [identity(binary), identity(keys)]})
    print(json.dumps({"native_fields": identity(binary), "native_keys": identity(keys)}))


if __name__ == "__main__":
    main()
