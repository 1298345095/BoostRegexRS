# ICU77 data and algorithm attribution

This directory contains generated data from the official ICU4C 77.1 source
release, with Unicode 16.0.0 and CLDR 47. The complete ICU release license is
preserved verbatim as [LICENSE-ICU.txt](LICENSE-ICU.txt). That license includes
the Unicode license, historical ICU/IBM notices, data notices, and the other
third-party notices shipped with the release.

ICU source files used to implement the collation-element iterator, implicit
weights, primary compression, and data access carry these upstream notices:

> © 2016 and later: Unicode, Inc. and others.

> Copyright (C) 2010-2016, International Business Machines Corporation and
> others. All Rights Reserved.

The exact year ranges vary by upstream file; the source hashes in
[root-icu77.json](root-icu77.json) identify those files without replacing their
individual notices. The full upstream source remains available through the
verified release archive.

## Fixed source

- Release: <https://github.com/unicode-org/icu/releases/tag/release-77-1>
- Source archive:
  <https://github.com/unicode-org/icu/releases/download/release-77-1/icu4c-77_1-src.tgz>
- Published SHA-512 manifest:
  <https://github.com/unicode-org/icu/releases/download/release-77-1/SHASUM512.txt>
- Archive SHA-512:
  `a47d6d9c327d037a05ea43d1d1a06b2fd757cc02a94f7c1a238f35cfc3dfd4ab78d0612790f3a3cca0292c77412a9c2c15c8f24b718f79a857e007e66f07e7cd`.

Source identities are checked against the archive during regeneration. The
official digest is verified; detached signatures are not verified.

## Mappings and algorithms used

| Upstream source under `icu4c/source/` | Use in this prototype |
| --- | --- |
| `data/in/icudt77l.dat` | Complete, unfiltered ICU release data, including canonical closure mappings |
| `i18n/collationdata.h`, `collationroot.*`, `collationdatareader.cpp` | Root CE32/CE/context/Jamo/compression tables and their identity |
| `i18n/collation.h`, `collation.cpp` | CE32 tags, CE construction, offset and implicit primaries |
| `i18n/collationiterator.*`, `utf16collationiterator.*` | Ordinary UTF-16 iteration, prefixes, contractions, expansions, Hangul, discontiguous matching |
| `i18n/collationkeys.cpp` | PRIMARY byte compression and termination |
| `i18n/collationsettings.*`, `rulebasedcollator.cpp` | Effective root options and sort-key dispatch |
| `common/normalizer2impl.*`, `data/in/nfc.nrm` | FCD16 leading/trailing combining-class data for context matching |
| `common/ucharstrie*`, `common/unicode/ucharstrie.h` | Complete enumeration of ICU context tries |

The fixed branch source can be reviewed at
<https://github.com/unicode-org/icu/tree/release-77-1/icu4c/source>.

Boost's byte-to-u32 and terminal-zero wrapping behavior is independently
implemented from Boost.Regex 1.89.0's `boost/regex/v5/icu.hpp`; the verified
Boost source and BSL-1.0 license remain in the development dependency cache.
No Boost C++ implementation is linked into the Rust executable.

## Changes and scope

The exporter converts the full CE32 and FCD16 lookup mappings to sorted,
constant-value ranges and serializes original CE32/CE/context/Jamo values.
It also enumerates each reachable context trie into UTF-16 keys to permit an
independent Rust trie representation. It does not discard canonical closure
data, substitute ICU4X's reduced collation data, or generate an input-to-key
answer table. All 256 primary-compression flags are copied from the actual root
data.

The Rust code transcribes the algorithms needed for root PRIMARY into safe
Rust and uses the generated static data. Ordinary root input is not uniformly
NFD-normalized. IDENTICAL and locale tailoring remain separate later phases;
the inclusion of all weight bits in the data does not imply those features
have been implemented. These are research tools, isolated from the root
library's public API.
