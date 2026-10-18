#!/usr/bin/env python3
"""Deterministic byte-regex cases, independent of either engine's answers."""

import argparse
import csv
from pathlib import Path


HEADER = ("case_id", "operation", "syntax", "match", "pattern_hex", "input_hex", "format_hex")
DEFAULT_SEED = 0x0042525352454731


class SplitMix64:
    """Specified integer PRNG; results do not depend on Python's random module."""

    def __init__(self, seed):
        self.state = seed

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & ((1 << 64) - 1)
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & ((1 << 64) - 1)
        return value ^ (value >> 31)

    def pick(self, values):
        return values[self.next() % len(values)]


def case(identifier, operation, pattern, text=b"", syntax=0, flags=0, replacement=b""):
    return (identifier, operation, syntax, flags, pattern.hex(), text.hex(), replacement.hex())


def directed():
    # Each family deliberately exercises competing matches and capture states.
    families = {
        "literal": [b"", b"a", b"ab", b"a\x00b", b"\xff", b"\xc3\xa9"],
        "alternation": [b"a|ab", b"ab|a", b"(a)|(b)", b"(?:a|)b", b"(a|aa)*"],
        "repeat": [b"a*", b"a+", b"a?", b"a*?", b"a+?", b"a??", b"a{0}",
                   b"a{1,3}", b"(ab){1,3}?", b"(a?)*", b"(a*)*b", b"(a|b)+"],
        "capture": [b"((a)(b)?)", b"(a(b)?)+", b"(?<name>a+)(b)?", b"(?P<name>a+)",
                    b"(?|(a)|(b))(c)", b"(a)\\1", b"(?<n>a)\\k<n>"],
        "assertion": [b"^a$", b"\\Aa\\z", b"a\\Z", b"\\b(a)\\b", b"\\B", b"\\G.",
                      b"a(?=b)", b"a(?!b)", b"(?<=a)b", b"(?<!a)b", b"(?=(a+))a"],
        "set": [b".", b"[a-c]", b"[^a]", b"[]a]", b"[-a]", b"[[:alpha:]]+",
                b"[[:digit:]]+", b"[[:word:]]+", b"\\d+", b"\\D", b"\\w+", b"\\s+",
                b"\\h", b"\\v", b"[[.ae.]]", b"[[=a=]]"],
        "option": [b"(?i)a", b"(?i:a)(?-i:B)", b"(?s).", b"(?-s).", b"(?m)^a$",
                   b"(?x) a # comment\n b", b"\\Qa.b\\E"],
        "extended": [b"(?>a*)a", b"a*+a", b"a{1,3}+a", b"(a)?(?(1)b|c)",
                     b"(?(?=a)a|b)", b"a\\Kb", b"(a(?1)?b)", b"a(*FAIL)|b",
                     b"a(*SKIP)(*F)|b", b"a(*COMMIT)b|ac"],
    }
    texts = [b"", b"a", b"b", b"ab", b"aa", b"aab", b"aba", b"aaab", b"ac",
             b"abc", b"Aab", b"a b", b"1a2", b"\n", b"a\n", b"\na\n", b"\r\n",
             b"\x00", b"a\x00b", b"\xff", b"\xc3\xa9"]
    for family, patterns in families.items():
        for pindex, pattern in enumerate(patterns):
            for tindex, text in enumerate(texts):
                for operation in ("search", "match"):
                    yield case(f"directed/{family}/{pindex}/{tindex}/{operation}", operation, pattern, text)
    # Every byte is admitted, including malformed UTF-8 and NUL, under literal syntax.
    for byte in range(256):
        pattern = bytes([byte])
        for operation in ("search", "match"):
            yield case(f"bytes/{byte:02x}/{operation}", operation, pattern, b"!" + pattern + b"!", syntax=2)
    invalid = [b"[", b"(", b")", b"\\", b"*", b"+", b"?", b"a**", b"a{", b"a{2,1}",
               b"a{999999999999999999999}", b"[z-a]", b"[[:unknown:]]", b"(?z)", b"(?<>",
               b"\\1", b"(a)\\2", b"(?<=a*)", b"(?P>x)", b"(*UNKNOWN)", b"a++?", b"(?"]
    for index, pattern in enumerate(invalid):
        yield case(f"compile/errors/{index}", "compile", pattern)
        for operation in ("compile", "search", "match", "iterate", "format", "replace"):
            yield case(f"no-except/{index}/{operation}", operation, pattern, b"ab",
                       syntax=1 << 18, replacement=b"<$0>")
    syntax_values = [0, 2, 1 | (1 << 21) | (1 << 16), (1 << 8) | (1 << 9) | (1 << 16) | (1 << 21),
                     1 | (1 << 21) | (1 << 12) | (1 << 11), (1 << 20), (1 << 22), (1 << 24)]
    for index, syntax in enumerate(syntax_values):
        for pindex, pattern in enumerate([b"a+", b"a\\+", b"(a)", b"\\(a\\)", b"a|b", b"a\\|b", b""]):
            yield case(f"syntax/{index}/{pindex}", "search", pattern, b"aa(a)b", syntax=syntax)
    match_bits = [0, *[1 << bit for bit in range(21) if bit not in (8, 9)]]
    # match_prev_avail needs an explicit prior iterator; it is exercised by the
    # search-from/iterator suite instead of an invalid begin-iterator invocation.
    for index, flags in enumerate(match_bits):
        for pindex, (pattern, text) in enumerate([(b"^a$", b"a"), (b"a|aa", b"aa"),
                                                (b"a*", b"ba"), (b"abc", b"ab"), (b"(a)+", b"aaa")]):
            yield case(f"flags/{index}/{pindex}", "search", pattern, text, flags=flags)
    combinations = [(1 << 16) | (1 << 17), (1 << 17) | (1 << 19),
                    (1 << 16) | (1 << 17) | (1 << 19),
                    (1 << 10) | (1 << 17), (1 << 10) | (1 << 19), 1 << 17,
                    (1 << 18) | (1 << 19)]
    for findex, flags in enumerate(combinations):
        for pindex, pattern in enumerate([b"a+", b"(a)+", b"a(*COMMIT)b|ac"]):
            for operation in ("search", "match", "iterate", "format", "replace"):
                yield case(f"flag-combinations/{findex}/{pindex}/{operation}", operation,
                           pattern, b"ac", flags=flags, replacement=b"$1/$0")
    for index, (pattern, text) in enumerate([(b"a*", b"aab"), (b"a*|b", b"b"), (b".*?", b"ab"),
                                            (b"(a)+", b"aa aa"), (b"\\b", b"ab cd"), (b"", b"\x00\xff")]):
        yield case(f"iteration/{index}", "iterate", pattern, text)
        yield case(f"iteration-extra/{index}", "iterate", pattern, text, flags=1 << 19)
    formats = [b"<$0>", b"$&/$1/$2", b"$`|$'", b"${name}", b"\\U$1\\E", b"\\u$1", b"$$",
               b"\\1-&", b"(?1yes:no)", b"$+", b"\\x{00}", b"\x00"]
    for index, replacement in enumerate(formats):
        for findex, flags in enumerate([0, 1 << 24, 1 << 25, 1 << 26, 1 << 27, 1 << 29]):
            for operation in ("format", "replace"):
                yield case(f"format/{index}/{findex}/{operation}", operation, b"(?<name>a+)(b)?",
                           b"-aab aa-", flags=flags, replacement=replacement)


def generated(count, seed):
    rng = SplitMix64(seed)

    def expression(depth):
        atom = rng.pick([b"a", b"b", b".", b"[ab]", b"[^a]", b"\\d", b"\\w", b"\\x00"])
        if depth and rng.next() % 4 == 0:
            atom = b"(" + expression(depth - 1) + b")"
        atom += rng.pick([b"", b"", b"?", b"*", b"+", b"{1,3}", b"*?", b"+?", b"?+"])
        if depth and rng.next() % 3 == 0:
            atom += rng.pick([b"", b"|"]) + expression(depth - 1)
        return atom

    for index in range(count):
        pattern = expression(2)
        text = bytes(rng.pick(b"ab01 \n\x00\xff") for _ in range(rng.next() % 13))
        flags = rng.pick([0, 0, 0, 1 << 13, 1 << 17, 1 << 19])
        operation = rng.pick(["search", "match"])
        yield case(f"generated/{index}", operation, pattern, text, flags=flags)


def write_cases(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated-count", type=int, default=10000)
    parser.add_argument("--seed", type=lambda text: int(text, 0), default=DEFAULT_SEED)
    args = parser.parse_args()
    if args.generated_count < 0:
        parser.error("--generated-count must be non-negative")
    write_cases(args.output, [*directed(), *generated(args.generated_count, args.seed)])


if __name__ == "__main__":
    main()
