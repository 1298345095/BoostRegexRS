#!/usr/bin/env python3
"""Generate the portable 2048-input context review diagnostic, without key lookup.

The input algorithm and random-call order reproduce the independent PRIMARY
review. Executable versions and strength are choices of the subsequent runner;
this generator does not claim that a new run restores old binary identities.
"""

import argparse
import json
from pathlib import Path

from compare import sha256
from generate_cases import Random, contexts, write_cases


SEED = 0x5350454352455631
COUNT = 2048
MARKS = (0x300, 0x301, 0x315, 0x323, 0x327, 0x345, 0x5B0, 0xF71, 0xF72, 0x3099)


def values(source):
    base = [value for label, value in contexts(source) if label.startswith("context/")]
    random = Random(SEED)
    marks = tuple(map(chr, MARKS))
    for index in range(COUNT):
        value = random.choose(base)
        if index % 2:
            at = random.next() % (len(value) + 1)
            value = value[:at] + "".join(random.choose(marks) for _ in range(1 + random.next() % 5)) + value[at:]
        else:
            value += random.choose(base) + random.choose(marks) + random.choose(base)
        yield f"spec-{index}", value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contexts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    utf8, utf16 = args.output / "inputs-utf8.tsv", args.output / "inputs-u16.tsv"
    write_cases(utf8, values(args.contexts))

    def encoded():
        for case_id, value in values(args.contexts):
            units = value.encode("utf-16-le")
            yield case_id, [int.from_bytes(units[index:index + 2], "little") for index in range(0, len(units), 2)]

    write_cases(utf16, encoded(), "u16")
    report = {"algorithm": "SplitMix64", "seed": f"0x{SEED:016x}", "count": COUNT,
              "host_unicode_database_used": False, "context_source_sha256": sha256(args.contexts),
              "inputs": {path.name: sha256(path) for path in (utf8, utf16)},
              "generator_sha256": sha256(Path(__file__))}
    (args.output / "generation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
