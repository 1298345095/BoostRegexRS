"""Deterministic root PRIMARY inputs, independent of reference key values.

Unicode facts for context generation come from the fixed ICU77 data export,
never the host Python Unicode database. SplitMix64 fixes the random algorithm.
"""

import argparse
import csv
import json
from pathlib import Path


SEED = 0x0042494355373701
MASK = (1 << 64) - 1


class Random:
    def __init__(self, seed=SEED):
        self.state = seed & MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
        return value ^ (value >> 31)

    def choose(self, values):
        return values[self.next() % len(values)]

    def scalar(self):
        value = self.next() % (0x110000 - 0x800)
        return value if value < 0xD800 else value + 0x800


def write_cases(path, values, kind="utf8"):
    count = 0
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        stream.write(f"case_id\t{kind}_hex\n")
        for identity, value in values:
            if kind == "utf8":
                encoded = value.encode("utf-8").hex()
            else:
                width = 8 if kind == "u32" else 4
                encoded = ",".join(f"{cp:0{width}x}" for cp in value)
            stream.write(f"{identity}\t{encoded}\n")
            count += 1
    return count


def historical():
    probe = Path(__file__).resolve().parents[1]
    for category, filename in (("existing24", probe / "reference/cases.tsv"), ("nonfcd13", probe / "non-fcd-cases.tsv")):
        with filename.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                yield f"{category}/{row['case_id']}", bytes.fromhex(row["utf8_hex"]).decode("utf-8")


def directed():
    yield from historical()
    examples = {
        "empty": "", "nul": "\0", "nuls": "\0" * 16, "nul_edges": "\0a\0b\0",
        "ascii_all": "".join(map(chr, range(128))), "latin1_all": "".join(map(chr, range(256))),
        "primary_ignorables": "\u0300\u0301\u0315\u0327\u200b\u200c\u200d\ufeff\ufe0f",
        "ignorables_between": "\u03b1\u200b\u0301\0\u03b2", "merge": "\u03b1\ufffe\u03b2",
        "merge_repeat": "\ufffe\ufffe", "noncharacter": "\uffff", "noncharacter_mix": "a\uffff\ufffeb",
        "han": "\u3400\u4e00\u9fff\uf900\U00020000\U0002a6df\U00030000\U000323af",
        "han_radicals": "\u2e80\u2f00\u2fd5\u3007\u4e00\u9f8d", "hangul": "\uac00\uac01\ud7a3",
        "supplementary": "\U0001f600\U00010428\U0001d400\U0010ffff", "unassigned": "\u0378\u0379\U00040000",
        "contraction_bengali": "\u09c7\u09be\u09c7\u09d7", "contraction_tamil": "\u0bc6\u0bbe\u0bc7\u0bbe",
        "contraction_kana": "\u304b\u3099\u30ab\u3099", "prefix_latin": "l\u00b7L\u00b7",
        "thai": "\u0e40\u0e01\u0e41\u0e01", "lao": "\u0ec0\u0e81", "tibetan": "\u0f71\u0f72\u0f73\u0f75",
        "expansion": "\u00df\ufb00\ufb01\ufb03\u00e6\u0153\u0149",
        "compress_up": "\u03b1\u03b2\u0430\u0431\u4e00", "compress_down": "\u4e00\u0431\u0430\u03b2\u03b1a",
        "compress_flush": "\u03b1\u03b2a\u0430\u0431\ufffe\u03b1\uffff",
    }
    for identity, value in examples.items():
        yield f"directed/{identity}", value
    marks = ("\u0300", "\u0301", "\u0315", "\u0323", "\u0327", "\u0345", "\u05b0", "\u3099", "\u0f71", "\u0f72")
    for base in ("", "a", "\u00e1", "\u03b1", "\u304b", "\u09c7", "\u1100"):
        for i, first in enumerate(marks):
            for j, second in enumerate(marks):
                yield f"combining/{base.encode('utf-8').hex() or 'leading'}-{i}-{j}", base + first + second
    for length in (0, 1, 2, 3, 31, 32, 33, 97, 98, 99, 100, 101, 127, 128, 129, 254, 255, 256, 1023, 1024, 1025, 4095, 4096, 4097, 10000):
        for label, unit in (("ascii", "a"), ("compressible", "\u03b1"), ("han", "\u4e00"), ("ignorable", "\u0301")):
            yield f"long/{label}-{length}", unit * length
        yield f"long/combining-{length}", "a" + ("\u0315\u0300\u0327" * length) + "b"
    for syllable in range(11172):
        leading, trailing = divmod(syllable, 28)
        leading, vowel = divmod(leading, 21)
        value = chr(0x1100 + leading) + chr(0x1161 + vowel)
        if trailing:
            value += chr(0x11A7 + trailing)
        yield f"hangul_jamo/{syllable:05d}", value


def generated(count, seed=SEED):
    random = Random(seed)
    pools = (
        tuple(range(128)), tuple(range(0x0300, 0x0370)), tuple(range(0x0370, 0x0500)),
        tuple(range(0x0900, 0x1000)), tuple(range(0x3040, 0x3100)), tuple(range(0x1100, 0x1200)),
        (0, 0x00DF, 0x00E1, 0xFB03, 0x200B, 0x200D, 0xFFFE, 0xFFFF, 0x10FFFF, 0x4E00, 0xAC00, 0x1F600),
    )
    for index in range(count):
        mode = index % 4
        length = random.next() % (80 if mode == 3 else 24)
        pool = random.choose(pools)
        if mode == 0:
            values = [random.scalar() for _ in range(length)]
        elif mode == 1:
            values = [random.choose(pool) for _ in range(length)]
        else:
            values = [random.choose(random.choose(pools)) for _ in range(length)]
        yield f"generated/{index:06d}", "".join(map(chr, values))


def contexts(report_path):
    """Exercise every exported prefix/contraction entry, plus interrupted paths.

    Context keys and triggering CE32s are source data, not oracle key samples.
    Prefix trie keys are stored in reverse code-point order by ICU77.
    """
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    table = {item["index"]: item for item in report["contexts"]}
    seen_paths = set()

    def visit(codepoint, ce32, before=(), after=(), trail=()):
        tag = ce32 & 15 if (ce32 & 255) >= 0xC0 else -1
        if tag not in (8, 9):
            return
        index = ce32 >> 13
        if index in trail:
            raise ValueError("Cycle in exported context data")
        context = table[index]
        yield from visit(codepoint, context["default_ce32"], before, after, trail + (index,))
        for entry_index, entry in enumerate(context["entries"]):
            key = tuple(entry["codepoints"])
            left = tuple(reversed(key)) + before if tag == 8 else before
            right = after + key if tag == 9 else after
            sequence = left + (codepoint,) + right
            path = (codepoint, index, entry_index, left, right)
            if path in seen_paths:
                continue
            seen_paths.add(path)
            label = f"{codepoint:06x}-{index}-{entry_index}-{len(seen_paths)}"
            yield f"context/{label}", "".join(map(chr, sequence))
            yield f"context_surrounding/{label}", "a" + "".join(map(chr, sequence)) + "z"
            if tag == 9:
                yield f"context_truncated/{label}", "".join(map(chr, left + (codepoint,) + right[:-1]))
                yield f"context_divergent/{label}", "".join(map(chr, left + (codepoint,) + right[:-1] + (0xFFFF,)))
            else:
                yield f"context_truncated/{label}", "".join(map(chr, left[1:] + (codepoint,) + right))
                yield f"context_divergent/{label}", "".join(map(chr, (0xFFFF,) + left[1:] + (codepoint,) + right))
            if tag == 9 and right:
                for mark_index, mark in enumerate((0x0300, 0x0315, 0x0323, 0x0327, 0x0345, 0, 0x200D)):
                    changed = left + (codepoint, mark) + right
                    yield f"context_interrupted/{label}-{mark_index}", "".join(map(chr, changed))
                # Both blocking and non-blocking decreasing/increasing CCC paths.
                for mark_index, marks in enumerate(((0x0327, 0x0300), (0x0315, 0x0323), (0x0323, 0x0315))):
                    changed = left + (codepoint,) + marks + right
                    yield f"context_multiple_skips/{label}-{mark_index}", "".join(map(chr, changed))
            yield from visit(codepoint, entry["ce32"], left, right, trail + (index,))

    for trigger in report["triggers"]:
        yield from visit(trigger["codepoint"], trigger["ce32"])


def input_boundaries(kind):
    if kind == "u32":
        values = ([0], [], [0x10FFFF], [0xD7FF, 0xE000], [0xD800], [0xDFFF], [0xD800, 0xDC00], [0x110000], [0xFFFFFFFF], [0x61, 0xD800, 0x62])
    else:
        values = ([], [0], [0xD800, 0xDC00], [0xDBFF, 0xDFFF], [0x61, 0, 0x62], [0xD800], [0xDC00], [0xDBFF, 0x61], [0x61, 0xDC00, 0x62], [0xDC00, 0xD800])
    for index, value in enumerate(values):
        yield f"input_{kind}/{index}", value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=20000)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=SEED)
    parser.add_argument("--all-scalars", action="store_true")
    parser.add_argument("--contexts", type=Path)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    counts = {}
    counts["directed"] = write_cases(args.output / "directed.tsv", directed())
    counts["generated"] = write_cases(args.output / "generated.tsv", generated(args.count, args.seed))
    for kind in ("u32", "u16"):
        counts[kind] = write_cases(args.output / f"{kind}.tsv", input_boundaries(kind), kind)
    if args.contexts:
        counts["contexts"] = write_cases(args.output / "contexts.tsv", contexts(args.contexts))
    if args.all_scalars:
        counts["all_scalars"] = write_cases(args.output / "all-scalars.tsv", ((f"scalar/{cp:06x}", chr(cp)) for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF))
    (args.output / "generation.json").write_text(json.dumps({"algorithm": "SplitMix64", "seed": f"0x{args.seed:016x}", "counts": counts, "host_unicode_database_used": False}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
