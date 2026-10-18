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
in the files that adapt them. `bocsu.cpp` and `bocsu.h` carry the 2001-2014 IBM
notice, which is retained in `bocsu77.rs`.

Fixed upstream sources:

- [`collationiterator.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationiterator.cpp): forward CE32 expansion, prefix/contraction lookup, discontiguous contraction matching, and skipped state.
- [`utf16collationiterator.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/utf16collationiterator.cpp) and [`collationfcd.h`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationfcd.h): explicit-length UTF-16 cursor semantics, supplementary decoding and the bidirectional FCD segment iterator.
- [`collation.h`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collation.h): CE32 tags, CE conversion, constants, Hangul Jamo indices, and sentinel. Its historical IBM copyright is 2010-2015.
- [`collation.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collation.cpp): three-byte offset primaries and implicit primary construction.
- [`collationkeys.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationkeys.cpp) and [`collationkeys.h`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationkeys.h): PRIMARY, SECONDARY, CASE, TERTIARY and QUATERNARY writers, all published settings, common-weight compression, and level boundaries.
- [`collationsettings.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationsettings.cpp), [`collationsettings.h`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationsettings.h) and [`collationdata.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationdata.cpp): effective setting bits, full script/group range allocation, equivalent-script handling, split-byte reordering and variable group boundaries. These files retain the 2012-2015 IBM notice in `settings77.rs`.
- [`rulebasedcollator.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/rulebasedcollator.cpp): the independent canonical-decomposition step for the IDENTICAL tail after CE-based levels.
- [`bocsu.cpp`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/bocsu.cpp) and [`bocsu.h`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/bocsu.h): signed difference encoding, script/Han recentering, and merge separators.
- [`boost/regex/v5/icu.hpp`](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/icu.hpp): the observed transform/transform_primary input/output convention. Boost source remains under its Boost Software License 1.0 in the verified development dependency.

The changes are a language and data-representation adaptation: safe Rust
collections replace pointers, the UTF-16 cursor is represented as decoded code
points, decoded context trie nodes replace packed UCharsTrie storage and state,
and checked data/input errors replace unreachable or unsupported native paths.
Contraction matching retains the native cursor's backward/forward replay and
direction changes; cached trie nodes do not replace that cursor operation.
The original root wrappers retain their default settings. The generic path also
adapts the FCD iterator, numeric collation, tailoring/base ownership and the
complete published setting-dependent key writer, as mapped in
[LOCALE-MECHANISMS.md](LOCALE-MECHANISMS.md).
Trace collection, binary-data validation, the streaming CLI, and regression
tests are new code. No ICU4X collation implementation or data is used in this
crate. Default-root CE input retains its original canonical order; explicit FCD
checking uses only source-defined local failing segments. The IDENTICAL final level
uses complete canonical mappings and combining classes exported from the same
ICU77 data. Safe Rust expansion and stable nonstarter sorting replace the
native normalization service for that final level.

The generated binary holds complete character/context mappings from the fixed
ICU source data; it does not contain the test oracle's string-to-key answers.
