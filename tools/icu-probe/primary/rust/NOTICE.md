# Algorithm provenance and modifications

This research crate contains a Rust adaptation of algorithms from the official
ICU4C 77.1 source release. The complete applicable Unicode/ICU license is retained
in [LICENSE-ICU.txt](../data/LICENSE-ICU.txt); the data export's provenance and
license notes are in the adjacent [data directory](../data/).

The original ICU files carry the following notices, preserved in the adapted
source files as well:

> © 2016 and later: Unicode, Inc. and others.
>
> Copyright (C) 2010-2014, International Business Machines Corporation and others.
> All Rights Reserved.

`collation.h` also carries the 2010-2015 IBM notice; `collationkeys.cpp` carries
the 2012-2015 IBM notice. The corresponding ranges and reservation are retained
in the files that adapt them.

Fixed upstream sources:

- [`collationiterator.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationiterator.cpp): forward CE32 expansion, prefix/contraction lookup, discontiguous contraction matching, and skipped state.
- [`utf16collationiterator.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/utf16collationiterator.cpp): explicit-length UTF-16 cursor semantics and supplementary decoding.
- [`collation.h`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collation.h): CE32 tags, CE conversion, constants, Hangul Jamo indices, and sentinel. Its historical IBM copyright is 2010-2015.
- [`collation.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collation.cpp): three-byte offset primaries and implicit primary construction.
- [`collationkeys.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationkeys.cpp): the non-shifted, unreordered PRIMARY writer and compression boundaries.
- [`boost/regex/v5/icu.hpp`](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/icu.hpp): the observed transform_primary input/output convention. Boost source remains under its Boost Software License 1.0 in the verified development dependency.

The changes are a language and data-representation adaptation: safe Rust
collections replace pointers, the UTF-16 cursor is represented as decoded code
points, decoded context trie nodes replace packed UCharsTrie state and replay,
and checked data/input errors replace unreachable or unsupported native paths.
Only root PRIMARY settings are accepted. The FCD iterator, numeric ON,
tailoring/base fallback, other writer levels, and IDENTICAL are not ported.
Trace collection, binary-data validation, the streaming CLI, and regression
tests are new code. No ICU4X collation implementation or data is used in this
crate, and no source algorithm normalizes the input in advance.

The generated binary holds complete character/context mappings from the fixed
ICU source data; it does not contain the test oracle's string-to-key answers.
