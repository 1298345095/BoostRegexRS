# ICU77 locale mechanisms

This source map was written before implementing the generalized locale path.
The reference is the verified official ICU4C 77.1 source archive used by the
cloud reference environment, with its complete Unicode 16.0 / CLDR 47 data.
All paths below are relative to the archive's `source/i18n/` directory. The
source license and archive identity remain in [NOTICE.md](NOTICE.md) and the
[fixed data provenance](../data/NOTICE.md).

## Data and iteration invariants

| Mechanism | ICU77 source | Required behavior |
| --- | --- | --- |
| Top data and base | `collationiterator.h`, `CollationIterator::nextCE`; `collationiterator.cpp`, `appendCEsFromCE32` | Resolve a top-level fallback into the base, then retain that data owner for CE32 expansions, CE64 expansions, contexts, Jamo mappings and offset data. Packed indexes are never rebased or interpreted in a different owner's arrays. |
| Prefixes | `getCE32FromPrefix`, `appendCEsFromCE32` | Look behind through the real character cursor, restore it by character count, and retain the longest trie value. A transient skipped-mark buffer is not the prefix input. |
| Contractions | `nextCE32FromContraction`, `nextCE32FromDiscontiguousContraction` | Preserve the last trie value and unmatched lookahead; honor `CONTRACT_SINGLE_CP_NO_MATCH`, `CONTRACT_NEXT_CCC` and `CONTRACT_TRAILING_CCC`. Equal or decreasing canonical combining classes block discontiguous matching. |
| Skipped marks | End of `nextCE32FromDiscontiguousContraction` | Append the matched CE using its owner. Re-resolve each skipped mark from top data with base fallback; nested contractions can replace the remaining skipped-mark buffer. |
| Published-data CE tags | `appendCEsFromCE32`; `collation.h` | Implement simple, long-primary, long-secondary, Latin expansion, expansion32, expansion64, prefix, contraction, digit, NUL, Hangul, surrogate, offset and implicit mappings. Builder-only and reserved tags are explicit data errors if reached; they are not published tailoring mechanisms. |
| Numeric collation | `appendNumericCEs`, `appendNumericSegmentCEs` | Gather decimal values from DIGIT CE32s via the real cursor and top lookup. Remove leading zeroes while retaining one zero, encode at most 254 digits per segment, use all three dense small-number forms and the large-number pair/exponent form, trim trailing `00` pairs, and decrement the last pair. Numeric primary bytes are not compressible. |
| Input widths | `utf16collationiterator.cpp`; Boost `unicode_iterator.hpp` | Checked UTF-32 and UTF-16 adapters reject malformed input using original input-unit positions. NUL is retained for explicit lengths. Raw ICU UTF-16 diagnostics remain separately named. |

## FCD checking

`FCDUTF16CollationIterator` in `utf16collationiterator.{h,cpp}` has three cursor
modes: forward checking, backward checking, and traversal of a known segment.
A known segment can refer to original text or to its local NFD buffer. Switching
direction and restoring prefix lookbehind must preserve this distinction.

The Rust cursor follows `nextSegment`, `previousSegment`, `switchToForward` and
`switchToBackward`. Its fast guards inspect the original UTF-16 units before
decoding a surrogate pair, as ICU does. BMP non-surrogate flags come from the
exact fixed FCD16 values. Each lead surrogate's L flag is true if any scalar in
its 1,024-code-point block has a nonzero leading CCC; its T flag is true if any
scalar in that block has either nonzero CCC. Every trail surrogate has L=true
and T=false. The lead flags are derived from fixed ICU77 data, never from test
keys. All 65,536 flag bytes are compared with the native `CollationFCD` fixture.

The guard deliberately does not substitute a supplementary scalar's trailing
CCC when checking the UTF-16 unit immediately before a BMP combining mark.
That would change backward segment boundaries. The native forward/backward/
forward traces for `é + U+1D165 + U+0323/U+0327` show this observable distinction:
turning around can normalize a different local segment. Cursor regression tests
compare each returned code point and its corresponding original UTF-16 offset,
including both complete failures and their reductions.

The fast Tibetan guard is `(unit & 0xff01) == 0x0f01`, equivalent to ICU's
`(c & 0x1fff01) == 0x0f01` for a UTF-16 unit. Its false positives only trigger
segment inspection. Canonical decomposition occurs after an actual FCD failure
or for the exact composite-vowel FCD16 values `0x8182` and `0x8184`.
Forward segment checking stops before a following leading-CCC-zero character
or after a trailing-CCC-zero character; backward checking uses the corresponding
opposite boundaries.

Discontiguous contractions retain ICU's `lookAhead` and `sinceMatch` counts.
When no skipped-mark buffer is active, replay resets the trie, drives the real
cursor backward by `lookAhead`, replays the accepted suffix, and advances over
the two examined non-starters. A saved trie node alone cannot replace these
cursor operations: they can switch direction and change the local FCD segment.
Nested skipped-buffer matching instead restores the saved trie state, then
replaces consumed marks with newly skipped marks and resumes from that buffer's
beginning. Prefix lookbehind always traverses and restores the real cursor.

Default root normalization remains OFF. IDENTICAL's full canonical decomposition
still occurs independently, after CE iteration, only for its final BOCSU level.
FCD cursor positions are internal diagnostics, not regex input-unit offsets.

## Settings and complete key writing

The effective settings are separate from tailoring defaults. ICU's public
`Collator::createInstance` first loads the tailoring, then applies locale keyword
overrides in `coll.cpp::setAttributesFromKeywords`. A finite locale inventory is
evidence about those requests, not a replacement for locale parsing or fallback.

`collationsettings.h` defines the fixed bit fields: FCD, numeric, shifted,
max-variable, upper-first, case-first, case-level, backwards-secondary and
strength. Valid strength values are PRIMARY, SECONDARY, TERTIARY, QUATERNARY and
IDENTICAL. Case level is independent of strength. Reserved alternate-handling
values are not silently treated as another supported setting.

`collationkeys.cpp::writeSortKeyUpToQuaternary` defines the full writer:

1. A variable primary is shifted to quaternary; all following primary-ignorable
   CEs are skipped until a nonzero primary is reached. Shifted primaries at or
   above lead byte `0x1b` receive the escape byte `0x1b`.
2. Test primary compressibility before reordering. Compare reordered primaries
   when opening/closing primary runs. Merge and end sentinels have their distinct
   compression behavior.
3. Secondary weights use 33-weight compression. Backwards secondary reverses
   complete bytes within U+FFFE-delimited segments, with reverse weight-byte
   emission before reversal and the previous secondary controlling compression.
4. Case level ignores primary ignorables at PRIMARY strength, and secondary
   ignorables otherwise. Lower-first uses the 7-weight nibble encoding and may
   omit an all-common level; upper-first uses the 13-weight encoding. Pack two
   case nibbles into one byte only when appending the finished level.
5. Tertiary selects the actual case mask. No-case, lower-first and upper-first
   use distinct compression ranges and weight transformations. Upper-first
   preserves the artificial uppercase bits of tertiary-only CEs.
6. Quaternary uses 113-weight compression. Only the non-shifted all-common case
   is omitted. It retains above-common weights and merge behavior.
7. End-of-input finalizes each selected level; level separators replace the
   temporary sentinel byte. IDENTICAL appends the existing fixed NFD/BOCSU tail.
   ICU's final zero and Boost's one-byte-per-u32 wrapping remain unchanged.

## Reordering and variable groups

The complete mechanism needs `numScripts`, `scriptsIndex`, and `scriptStarts`
from `collationdata.h`, in addition to effective reordered settings. Existing
reorder-code lists or their outputs alone cannot compute a new requested order.

`collationdata.cpp::makeReorderRanges` covers special groups left at the low end,
reserved ranges before/after Latin, equivalent-script duplicate rejection,
`USCRIPT_UNKNOWN` as the others marker, scripts moved to the high end, remaining
scripts, the Latin retry when ranges no longer fit, and explicit overflow.
`addLowScriptRange` and `addHighScriptRange` preserve partial lead-byte ranges.

`collationsettings.cpp::setReordering` creates the 256-byte table and retains
split ranges. `reorderEx` compares the primary rounded with `0xffff` against
exclusive `(limit, signed-offset)` pairs. Primary weights outside the final
reordered range stay unchanged. Variable-top values come from actual script
group limits before reordering.

`aliasReordering` clears the unused minimum when no lead byte is split, while
`setReordering` may retain its final full range limit. Table/range equivalence
therefore compares that minimum only when split ranges exist. A zero table byte
alone is not a sufficient validity test: root `Zzzz-Latn` wraps the unused
reserved-after-Latin lead `0x60` to zero without any split range. The loader
retains this actual ICU table, and the regression recomputes it from its codes.

The checked reordering constructor validates the retained representation before
any primary is processed. Boundaries must increase, the last boundary must agree
with the aligned minimum, partial boundaries must explain zero table slots on
used leads, and the remaining table suffix must agree with the signed offsets
and unchanged tail. Without retained split ranges, used leads cannot map to
zero. Unused full leads are derived from the two reserved script intervals in
the fixed `scriptsIndex`/`scriptStarts` data; they are not inferred from a
particular locale or accepted solely because a supplied table contains zero.
This preserves legitimate unused slots while rejecting the missing-range state
that would otherwise index an empty range list during ordinary root collation.

## Locale data schemas

All locale files are tightly packed little-endian bytes. Each starts with its
eight-byte magic, `u32 schema = 1`, then six `u32` version components
`[77, 1, 16, 0, 47, 0]`. Readers reject trailing data or incompatible versions.
Each array starts with a `u32` element count.

| Magic | Fields after the shared header |
| --- | --- |
| `BRSSET77` | `options:u32`, `variableTop:u32`, `reorderCodes:i32[]`, `reorderTable:u8[]` of length 0 or 256, `minHighNoReorder:u32`, `reorderRanges:u32[]` |
| `BRSSCR77` | `numScripts:u32`, `scriptsIndex:u16[]`, `scriptStarts:u16[]` |
| `BRSOWN77` | `numericPrimary:u32`, CE32 ranges `(endInclusive:u32, ce32:u32)[]`, `ce32s:u32[]`, `ces:u64[]`, raw contexts `u16[]`, 67 Jamo CE32s `u32[]`, 256 compressibility flags `u8[]`, decoded contexts |

Decoded contexts use the original `BRSPRI77` encoding: count, then each
`index:u32`, `defaultCE32:u32`, entry count, and each entry's `u16[]` key followed
by its `ce32:u32`. Prefix keys retain the original reverse-code-point trie order.
Owners share fixed root FCD data; they do not duplicate it in `BRSOWN77`.
Unlike the root table, published owners may have empty CE32, CE64 or context
arrays. The catalog records the explicit root base and each file's digest.

## Independent validation boundary

The implementation is checked against exported settings, owner tables and an
independent ICU/Boost reference. Mechanism tests cover source-defined compression
and segmentation boundaries, owner fallback with nested contexts, numeric
254-digit boundaries, FCD direction changes, case/secondary combinations and
split-byte reordering. Existing root PRIMARY and IDENTICAL suites remain
regressions. Complete byte sequences and Boost u32 sequences are compared;
errors, approved empty-input exceptions and uncovered requests are separate.
Finite test results do not establish a mathematical proof for arbitrary input.

Custom rule parsing, locale ID canonicalization and fallback, character
classification, the regex engine and platform default locale discovery have
their own observable contracts. Implementing this writer does not by itself
complete those contracts or the repository's full release acceptance.
