#!/usr/bin/env python3
"""Enumerate settings combinations separately from test strings and their keys."""

from itertools import product


def attribute_requests():
    """All 384 combinations of the seven finite locale attribute domains.

    Strength is deliberately left at its locale default; Boost's two public
    transforms force PRIMARY/IDENTICAL after locale creation. Arbitrary script
    reorder lists are a separate domain, represented by the full script tables.
    """
    keys = ("colalternate", "colbackwards", "colcasefirst", "colcaselevel",
            "colnormalization", "colnumeric", "kv")
    domains = (("non-ignorable", "shifted"), ("no", "yes"), ("no", "lower", "upper"),
               ("no", "yes"), ("no", "yes"), ("no", "yes"),
               ("space", "punct", "symbol", "currency"))
    for values in product(*domains):
        yield "root@" + ";".join(f"{key}={value}" for key, value in zip(keys, values))


def reorder_requests():
    # Diagnostic configurations exercise split leads, Latin reservation, placing
    # groups after OTHERS, and script aliases. The runtime uses the full script
    # metadata and the ICU algorithm for other requested reorder sequences.
    for value in ("Latn", "Grek-Latn", "Hani-Latn", "Arab-Latn", "Zzzz-Latn",
                  "Latn-Zzzz-Hani", "space-punct-symbol-currency-digit-Latn",
                  "digit-Latn", "Tibt-Khmr-Mymr", "Kana-Hani", "Qaai-Latn",
                  "Cyrl-Grek-Latn", "Hani-Latn-Grek", "Grek-Latn-Zzzz-Cyrl",
                  "space-digit-currency-Grek-Latn-Hani", "Arab-Hebr-Latn", "Zzzz"):
        yield "root@colreorder=" + value
    yield ("root@colalternate=shifted;colbackwards=yes;colcasefirst=upper;colcaselevel=yes;"
           "colnormalization=yes;colnumeric=yes;colreorder=Grek-Latn-Zzzz-Cyrl-digit;kv=currency")


def default_requests():
    yield from attribute_requests()
    yield from reorder_requests()
