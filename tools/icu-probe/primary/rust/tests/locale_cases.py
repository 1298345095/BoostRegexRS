#!/usr/bin/env python3
"""Source-defined locale mechanism inputs, independent of candidate/oracle keys.

The fixed scalar literals are test inputs, not a host Unicode property table.
Generated cases use the repository's specified SplitMix64 algorithm and seed.
"""

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys


PRIMARY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PRIMARY))
from generate_cases import Random, SEED, write_cases  # noqa: E402


def profiles():
    """All flag combinations, all case-first values and all variable groups."""
    for normalization, numeric, backwards, case_level, shifted in itertools.product((False, True), repeat=5):
        for case_first in ("no", "lower", "upper"):
            for variable in ("space", "punct", "symbol", "currency"):
                values = {
                    "colAlternate": "shifted" if shifted else "non-ignorable",
                    "colBackwards": "yes" if backwards else "no",
                    "colCaseFirst": case_first,
                    "colCaseLevel": "yes" if case_level else "no",
                    "colNormalization": "yes" if normalization else "no",
                    "colNumeric": "yes" if numeric else "no",
                    "kv": variable,
                }
                identity = (f"fcd{int(normalization)}-num{int(numeric)}-back{int(backwards)}-"
                            f"case{int(case_level)}-{case_first}-shift{int(shifted)}-{variable}")
                yield {"profile_id": identity, "locale": "root@" + ";".join(f"{key}={value}" for key, value in values.items())}
    for index, codes in enumerate((
        "Latn", "Grek-Latn", "Cyrl-Grek-Latn", "Hani-Latn-Grek", "Grek-Latn-Zzzz-Cyrl",
        "Zzzz-Latn", "space-digit-currency-Grek-Latn-Hani", "Arab-Hebr-Latn", "Zzzz",
    )):
        yield {"profile_id": f"reorder-{index:02d}", "locale": f"root@colReorder={codes}"}
    yield {
        "profile_id": "reorder-with-all-flags",
        "locale": ("root@colAlternate=shifted;colBackwards=yes;colCaseFirst=upper;colCaseLevel=yes;"
                   "colNormalization=yes;colNumeric=yes;kv=currency;colReorder=Grek-Latn-Zzzz-Cyrl-digit"),
    }


def directed():
    examples = {
        "empty": "", "nul": "\0", "nuls": "\0\0\0", "nul_edges": "\0a\0b\0",
        "primary_ignorables": "\u0301\u0315\u0327\u200b\ufeff",
        "case_letters": "aAbBcCdD", "titlecase": "\u01c4\u01c5\u01c6\u01c7\u01c8\u01c9",
        "case_greek": "\u1f80\u1f88\u1fb3\u1fbc\u1ff3\u1ffc",
        "case_secondary_ignorable": "\u0301A\u0300a\u200bB\0b",
        "variables": " a-b_c.d,e:f;g!h?i\u00a0j$k€l+m×n÷o",
        "shift_ignore_after": "a-\u0301\u0315\u0327\0 b",
        "shift_adjacent": "a-\u0301$\u0315+\u0327b",
        "shift_merge": "a-\u0301\ufffe$\u0315b",
        "merge": "\u03b1\ufffe\u03b2", "merged_secondaries": "éà\ufffeèá\ufffeöü",
        "merge_repeat": "\ufffe\ufffe", "noncharacters": "\uffff\ufffe\U0010ffff",
        "numeric_boundaries_nul": "1\x0002\x0012\x00003",
        "numeric_ignorables": "12\u0301\u200b34\u00ad56",
        "numeric_non_decimal": "12ⅢⅣ²³④⑤⑩½34",
        "numeric_script_transition": "12\u0663\u0664\u096b\u096c\uff17\uff18\U0001d7d7",
        "prefix_latin": "l·L·l\u0387L\u0387",
        "prefix_nul": "l\0·L\0·", "prefix_fcd": "l\u0315\u0300·ĺ·l·\u0315\u0300",
        "discontiguous": "и\u0327\u0306и\u0315\u0306и\u0301\u0306",
        "tibetan": "\u0f73\u0f75\u0f81\u0f71\u0f72\u0f74\u0f80",
        "fcd_starter_boundary": "é\u0315\u0300a\u0327\u0301",
        "fcd_supplementary": "\U0001d15e\U0001d165\U0001d16e\u0315\u0300",
        "fcd_leading": "\u0315\u0300\u0327é\u0315\u0300",
        "fcd_merge": "é\u0315\u0300\ufffe\u0315\u0300a",
        "fcd_nul": "é\u0315\0\u0300\u0327a",
        "han_hangul_supplementary": "一\U00020000\U00030000각\u1100\u1161\u11a8😀\U0010ffff",
        "compress_up": "αβаб一", "compress_down": "一баβαa", "compress_merge": "αβ\ufffeаб一\ufffea",
        "expansions": "ßæœﬀﬁﬃ¼Ⅷ\uf900",
    }
    for identity, value in examples.items():
        yield "locale/" + identity, value

    # Cross source-defined common-run boundaries for all selected levels.
    lengths = (0, 1, 6, 7, 8, 12, 13, 14, 32, 33, 34, 96, 97, 98, 112, 113, 114, 199, 200, 201)
    for length in lengths:
        for name, value in (
            ("lower_upper", "a" * length + "A"),
            ("upper_lower", "A" + "a" * length),
            ("mixed", "a" * length + "\u01c5"),
            ("below_secondary", "a" * length + "\ufffe"),
            ("above_secondary", "a" * length + "\u0301"),
            ("reverse_segment", "é" + "a" * length + "\ufffe" + "a" * length + "è"),
            ("shifted", "a" * length + "-\u0301$\u0315b"),
            ("quaternary", "あ" * length + "ア"),
        ):
            yield f"compression/{name}-{length}", value

    values = (0, 1, 9, 10, 73, 74, 75, 10233, 10234, 10235, 1042489, 1042490, 1042491, 9999999, 10000000)
    for value in values:
        for zeros in (0, 1, 2, 255):
            yield f"numeric/dense-{value}-zero{zeros}", "0" * zeros + str(value)
    for length in (1, 2, 6, 7, 8, 253, 254, 255, 256, 507, 508, 509):
        for name, value in (
            ("nines", "9" * length),
            ("power", "1" + "0" * (length - 1)),
            ("alternating", ("1029384756" * (length // 10 + 1))[:length]),
            ("zero_segment", "9" * 254 + "0" * length + "1"),
        ):
            yield f"numeric/segment-{name}-{length}", value
    for base in (0x30, 0x660, 0x966, 0xff10, 0x1d7ce):
        for value in values:
            yield f"numeric/script-{base:x}-{value}", "".join(chr(base + int(digit)) for digit in str(value))

    bases = ("", "a", "é", "и", "l·", "L\u0387", "\u0f73", "\u0f75", "\u0f81", "\U0001d15e")
    marks = ("\u0300", "\u0301", "\u0315", "\u0323", "\u0327", "\u0345", "\u0f71", "\U0001d165")
    for base_index, base in enumerate(bases):
        for first, second in itertools.product(range(len(marks)), repeat=2):
            yield f"fcd/context-{base_index}-{first}-{second}", base + marks[first] + marks[second] + "l·и\u0327\u0306"


def generated(count=512, seed=SEED):
    random = Random(seed)
    pool = (
        tuple(map(ord, "aAbB- $€+0123456789\0\ufffe\u01c4\u01c5\u01c6")),
        (0x300, 0x301, 0x315, 0x323, 0x327, 0x345, 0xf71, 0xf73, 0xf75, 0xf81, 0x1d165),
        tuple(map(ord, "l·Lиα一각あア")),
        tuple(range(0x660, 0x66a)) + tuple(range(0x1d7ce, 0x1d7d8)),
    )
    for index in range(count):
        values = [random.choose(random.choose(pool)) for _ in range(random.next() % 64)]
        yield f"locale-generated/{index:06d}", "".join(map(chr, values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated", type=int, default=512)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=SEED)
    args = parser.parse_args()
    if args.generated < 0:
        parser.error("--generated must be nonnegative")
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = list(directed()) + list(generated(args.generated, args.seed))
    if len({identity for identity, _ in inputs}) != len(inputs):
        raise ValueError("duplicate generated case identity")
    case_path = args.output / "cases.tsv"
    count = write_cases(case_path, inputs)
    profile_rows = list(profiles())
    (args.output / "profiles.json").write_text(json.dumps(profile_rows, indent=2) + "\n")
    (args.output / "requests.txt").write_text("".join(row["locale"] + "\n" for row in profile_rows))
    summary = {"schema": "boostregexrs.icu77-locale-mechanism-inputs.v1", "cases": count,
               "directed": count - args.generated, "generated": args.generated, "profiles": len(profile_rows),
               "seed": f"0x{args.seed:016x}", "random_algorithm": "SplitMix64",
               "host_unicode_database_used": False, "reference_keys_used_to_choose_inputs": False,
               "cases_sha256": hashlib.sha256(case_path.read_bytes()).hexdigest()}
    (args.output / "generation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
