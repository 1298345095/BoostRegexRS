#!/usr/bin/env python3
"""Generate bounded inputs for native compile/execution error classification.

These are inputs, not candidate-derived expected answers. The nesting probe
crosses basic_regex_parser.hpp::parse_all's fixed 400-level guard. Execution
probes exercise perl_matcher_non_recursive.hpp's independent state/recursion
guards without changing Boost's resource macros or the production reference.
"""

import argparse
import csv
from pathlib import Path

from protocol import HEADER


def cases():
    def row(name, operation, pattern, subject=b"", syntax=0, flags=0, replacement=b""):
        return [name, operation, str(syntax), str(flags), pattern.hex(), subject.hex(), replacement.hex()]

    yield row("ordinary-compile-error", "compile", b"(")
    yield row("ordinary-no-except", "compile", b"(", syntax=1 << 18)
    nested = b"(" * 401 + b"a" + b")" * 401
    yield row("compile-nesting-limit", "compile", nested)
    yield row("compile-nesting-no-except", "compile", nested, syntax=1 << 18)
    yield row("compile-backtracking-pattern", "compile", b"^(a+)+$")
    for operation in ("search", "match", "iterate", "format", "replace"):
        yield row(operation + "-state-limit", operation, b"^(a+)+$", b"a" * 32 + b"b",
                  replacement=b"<$&>")
    yield row("invalid-no-except-search", "search", b"(", b"a", syntax=1 << 18)
    yield row("invalid-match-policies", "search", b"(a)", b"a", flags=(1 << 17) | (1 << 19))


def stack_cases():
    # Three captured groups retained across a simple linear repetition cross
    # the default 1,024 x 4,096-byte matcher stack-block budget. This does not
    # reduce any Boost limit and stays below the v1 TSV field-size limit.
    yield ["match-stack-limit", "match", "0", "0", b"^(((a)))*$".hex(), (b"a" * 60000).hex(), ""]


def no_except_flow_cases():
    """Keep returned invalid objects and subsequent API calls independently observable."""
    operations = ("search", "match", "iterate", "format", "replace")
    for name, pattern in (("resource", b"(" * 401 + b"a" + b")" * 401), ("syntax", b"(")):
        yield [f"no-except-{name}-compile", "compile", "262144", "0", pattern.hex(), "", ""]
        for operation in operations:
            yield [f"no-except-{name}-{operation}", operation, "262144", "0",
                   pattern.hex(), b"a".hex(), b"<$&>".hex()]
    for operation in operations:
        yield [f"no-except-valid-{operation}", operation, "262144", "0",
               b"(a)".hex(), b"zaa!".hex(), b"<$1>".hex()]
    yield ["no-except-valid-invalid-policies", "search", "262144", str((1 << 17) | (1 << 19)),
           b"(a)".hex(), b"a".hex(), ""]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stack-only", action="store_true", help="emit the separate linear stack-block probe")
    group.add_argument("--no-except-flow-only", action="store_true", help="emit compile-return and later-operation probes")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.no_except_flow_only:
        rows = list(no_except_flow_cases())
    elif args.stack_only:
        rows = list(stack_cases())
    else:
        rows = list(cases())
    with args.output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)
    print(f"Wrote {len(rows)} source-defined error probes to {args.output}")


if __name__ == "__main__":
    main()
