#!/usr/bin/env python3
"""Regenerate focused IDENTICAL regressions with the fixed development oracle."""

import argparse
import csv
import io
import os
from pathlib import Path
import subprocess
import sys


PRIMARY = Path(__file__).resolve().parents[2]
REPO = PRIMARY.parents[2]
sys.path.insert(0, str(PRIMARY))
from generate_cases import identical_directed  # noqa: E402


def main():
    cache = REPO / "target/research/icu77-cloud"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, default=cache / "build/identical/oracle")
    parser.add_argument("--icu-lib", type=Path, default=cache / "install/icu/lib")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data/identical.tsv")
    args = parser.parse_args()
    cases = [(name, text) for name, text in identical_directed()
             if name.startswith(("identical_common/", "bocsu_boundary/", "identical_nfd/"))]
    payload = "case_id\tutf8_hex\n" + "".join(
        f"{name}\t{text.encode('utf-8').hex()}\n" for name, text in cases)
    env = dict(os.environ, LD_LIBRARY_PATH=str(args.icu_lib.resolve()))
    env.pop("ICU_DATA", None)
    result = subprocess.run([str(args.oracle.resolve()), "--strength", "identical",
                             "--approved-empty-exception"], input=payload, text=True,
                            capture_output=True, env=env, check=True)
    reference = list(csv.DictReader(io.StringIO(result.stdout), delimiter="\t"))
    if [row["case_id"] for row in reference] != [name for name, _ in cases]:
        raise ValueError("Oracle omitted, duplicated, or reordered fixture rows")
    if any("ERROR:" in row["raw_icu_hex"] or "ERROR:" in row["boost_u32_hex"] for row in reference):
        raise ValueError("Reference error while generating IDENTICAL fixtures")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("case_id", "utf8_hex", "raw_icu_hex", "boost_u32_hex"))
        for (_, text), row in zip(cases, reference, strict=True):
            writer.writerow((row["case_id"], text.encode("utf-8").hex(),
                             row["raw_icu_hex"], row["boost_u32_hex"]))
    print(f"Saved {len(cases)} official ICU77/Boost.Regex 1.89.0 IDENTICAL fixtures to {args.output}")


if __name__ == "__main__":
    main()
