# Fixed ICU77 root IDENTICAL complete-key results

Date: 2026-10-17. This is a separate result from the historical
[root PRIMARY delivery](root-primary-cloud-results.md). The implementation is
still the independent research crate; full library, locale and six-platform
acceptance continue under [ADR-0001](../adr/0001-boost-regex-behavioral-compatibility.md)
and [ADR-0003](../adr/0003-resource-contract-and-release-acceptance.md).

## Observed result

The full root IDENTICAL differential run completed on Linux x86-64 at
**2026-10-17 11:41:21 UTC**, with exit status **0**. It compared the entire ICU
byte sequence, including its final terminator, and the entire Boost u32 return
sequence. The recorded result is `passed_for_recorded_inputs`, with
`full_recorded_suite` coverage and no unrun groups.
[Run summary](assets/icu77-identical/runs/2026-10-17T114006Z-xz/summary.json)

| Input group | Records | Original nonempty keys passed | Approved empty keys passed | Expected invalid-input rejections |
| --- | ---: | ---: | ---: | ---: |
| Directed, historical, long and Hangul sequences | 12,229 | 12,222 | 7 | 0 |
| Fixed-seed generated strings | 20,000 | 19,313 | 687 | 0 |
| Exported contexts and interruption variants | 16,046 | 16,046 | 0 | 0 |
| Checked UTF-32 boundaries | 10 | 3 | 1 | 6 |
| Checked UTF-16 boundaries | 10 | 4 | 1 | 5 |
| Every Unicode scalar as a single-character input | 1,112,064 | 1,112,064 | 0 | 0 |
| **Total** | **1,160,359** | **1,159,652** | **696** | **11** |

All groups recorded zero key differences, zero unsupported records and zero
reference errors in their valid-key/expected-rejection comparisons. The total
number of valid key records is **1,160,348**. These are records, not a claim that
every string is distinct; empty and other strings occur in more than one group.
The **three original empty-reference crashes are separate observations**, as
described below. Their errors are not hidden in the zero-error comparison total.
[Run summary](assets/icu77-identical/runs/2026-10-17T114006Z-xz/summary.json)

An additional 48,272 adjacent ICU comparison signs agreed with the candidate's
key ordering. These checks use the same inputs and do not add accepted key
records. Complete key lengths ranged from 5 to 60,323 bytes. Generated inputs
included 106 keys of length 99, 80 of length 100 and 107 of length 101, exercising
the actual Boost buffer boundary. The archive contains each group's complete
summary and raw outputs.
[Archive manifest](assets/icu77-identical/runs/2026-10-17T114006Z-xz/manifest.json)

## Implementation and fixed data

The CE iterator consumes the original input with root normalization **OFF**.
The existing PRIMARY writer remains in use, followed by ICU77-compatible
secondary, tertiary and quaternary levels. Only the final IDENTICAL level applies
recursive canonical decomposition and canonical ordering, then BOCSU encoding.
This avoids treating a globally pre-normalized input as the original collation
input. The implementation and regression fixtures are in
[the research crate](../../tools/icu-probe/primary/rust/README.md).

The algorithm follows the fixed ICU4C 77.1 source, including
[collationkeys.cpp](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationkeys.cpp),
[rulebasedcollator.cpp](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/rulebasedcollator.cpp),
[bocsu.cpp](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/bocsu.cpp)
and the recursively processed decomposition contract of
[normalizer2.h](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/common/unicode/normalizer2.h).
Official archive hashes, extracted source checks and installed library identities
are retained in the [NFD provenance manifest](../../tools/icu-probe/primary/data/root-icu77-nfd.json).
Checksum verification is recorded separately from detached-signature verification;
the latter was not performed.

The original complete CE blob is unchanged. A separate `BRSNFD77` version-1
blob supplies the full Unicode 16 canonical decomposition mappings and combining
classes. It includes all algorithmic Hangul decompositions as explicit mappings,
13,253 mappings containing 36,567 scalars, and 590 merged CCC ranges covering
the full code-point domain. The longest scalar decomposition contains four
scalars. No host Python Unicode table is used.
[Binary format](../../tools/icu-probe/primary/data/FORMAT.md)

| Data artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Existing root CE data | 751,804 | `7aefc773d90fc2006c236720cd4e9220720efb33c7b8274ffeb24b494de3034e` |
| New Unicode16 NFD data | 255,286 | `45c59eca6b851ea843c8088343742f1ac706ca4bb657c807a981e1c708a337de` |

The NFD exporter runs two independent exports and requires identical binary and
runtime metadata. A further `generate_nfd.py --check` succeeded against the
checked-in blob. Runtime metadata verifies ICU **77.1**, Unicode **16.0.0**, CLDR
**47.0**, ICU data **77.1**, and root IDENTICAL private options **0xf010**.
The oracle separately checks effective public settings: IDENTICAL strength,
normalization/numeric/case-level/case-first/French-secondary OFF and alternate
handling NON-IGNORABLE.
[NFD generation evidence](assets/icu77-identical/nfd-check-manifest.json)

The Rust implementation uses stable Rust and fixed embedded data; its runtime
does not call the native reference, ICU or a known-input answer table. The full
run explicitly removed the native ICU library path from the candidate environment
and pointed `ICU_DATA` to an absent directory. Its candidate executable SHA256
was `ba5fb0517733dda68628ec8902101feae0c16b9f6443ecaa22d532d88553d64d`;
the development-only native oracle SHA256 was
`6ba31c2517220b02bcd6b0f745f1cdd40814e81be28a3d383a81595f30fa32c6`.
The run summary records Python 3.12.14, Linux 6.18.55 x86-64/glibc 2.39 and
source-file identities. Compiler and fixed dependency provenance reuse the
[recorded official toolchain](assets/icu77-cloud/primary/rust-toolchain-manifest.json)
and [prepared environment](assets/icu77-cloud/environment-manifest.json).

## Empty input remains an explicit exception

The runner first called unmodified Boost `transform` on empty input through
UTF-8, checked UTF-16 and checked UTF-32 entry paths. All three processes actually
terminated with **SIGSEGV**, return code **-11**. Original stdout, stderr,
per-attempt metadata and isolated signal rows are preserved under
`original-empty/` inside the full archive. The original-reference error count is
**3**.
[Original process records](assets/icu77-identical/runs/2026-10-17T114006Z-xz/summary.json)

For the 696 genuinely empty input records, the separate approved expectation
uses ICU77 with a valid pointer and length zero, then applies Boost's byte-per-u32
return convention. Its raw key is `01,01,01,01,00`; the returned u32 sequence is
`00000001,00000001,00000001,00000001`. These rows alone increment
`approved_exception_passed`. The runner preserves `expectation-origins.tsv` for
every group. Nonempty valid rows invoke the actual Boost `transform`; malformed
input is checked and counted separately.
[ADR-0005](../adr/0005-icu-locale-query-and-empty-sort-key.md)

The strict comparator has explicit regressions proving that an original
reference error remains an error even when empty-exception accounting is enabled,
and that the exception cannot be enabled for PRIMARY. The Python comparator and
reference-process suite passed **18 tests**. The Rust lane separately passed
**19 tests**, formatting and Clippy, with 167 complete native key fixtures.
[Comparator tests](../../tools/icu-probe/primary/test_compare.py),
[Rust tests](../../tools/icu-probe/primary/rust/tests/root_identical.rs)

## Historical non-FCD differences

The new run contains the same 13 non-FCD inputs as the preserved Windows
experiment. Their complete keys agree with those historical root keys. All
78 unordered root input pairs now agree, including the **18 root pairs** that
previously differed with ICU4X. This correspondence is calculated from saved
outputs without another candidate execution.
[Derived summary](assets/icu77-identical/historical-nonfcd/summary.json),
[complete key table](assets/icu77-identical/historical-nonfcd/keys.tsv),
[78-pair table](assets/icu77-identical/historical-nonfcd/pairs.tsv)

The historical ICU4X files continue to report **145 IDENTICAL differences**.
The root result addresses 18 of those pair records; the remaining **127
non-root pair records** are outside this root-only run. No historical file or
historical count has been rewritten. The derived 13-key/78-pair figures do not
increase the new run's input totals.

The separately authorized replay of the earlier 2,048-input PRIMARY review is
also preserved in full, with its original binaries' identities, keys and CE
traces. It remains a distinct new replay of that diagnostic, not recovered raw
data from the earlier in-memory execution, and contributes no records to the
main PRIMARY, CE or IDENTICAL counts. The newly tracked portable generator was
checked to reproduce both archived input files byte-for-byte, without rerunning
the collators.
[Review replay archive](assets/icu77-identical/primary-review-contexts-2048/manifest.json),
[generator verification](assets/icu77-identical/review-context-generator-verification.json)

## Reproduction and preservation

From the repository root:

```sh
python3 -B tools/icu-probe/cloud/prepare.py --jobs 6
python3 -B tools/icu-probe/primary/export/generate.py --check
python3 -B tools/icu-probe/primary/export/generate_nfd.py --check
python3 -B tools/icu-probe/primary/run_identical.py
```

New runs default to a fresh dated directory under
`docs/research/assets/icu77-identical/runs/`; compiled products and downloaded
dependencies remain under `target`. The first run's original directory,
`target/research/icu77-cloud/identical/`, is retained unchanged. Its complete
raw contents are additionally saved in the checked-in compressed archive parts.
The parts reconstruct the original 23,509,336-byte XZ stream exactly; their
[manifest](assets/icu77-identical/runs/2026-10-17T114006Z-xz/raw.tar.xz.parts/manifest.json)
records both the individual part hashes and the complete stream identity.
Use the [tracked archiver](../../tools/icu-probe/primary/archive_evidence.py)
to verify every archived file without extracting it:

```sh
mkdir -p target
python3 -B tools/dev/split_artifact.py join \
  --manifest docs/research/assets/icu77-identical/runs/2026-10-17T114006Z-xz/raw.tar.xz.parts/manifest.json \
  --output target/icu77-identical-recorded.tar.xz
python3 -B tools/icu-probe/primary/archive_evidence.py --verify \
  docs/research/assets/icu77-identical/runs/2026-10-17T114006Z-xz \
  --archive target/icu77-identical-recorded.tar.xz
```

The source/evidence inventory and extraction instructions are in the
[asset README](assets/icu77-identical/README.md). The recorded first run used
`run_identical.py --skip-build` after the reference and stable Rust binaries
were separately built; their exact SHA256 identities are in its summary.
The default output-location change was made after that run and does not alter
input generation, key computation or comparison rules.

## Remaining acceptance

This result establishes agreement for the recorded root IDENTICAL inputs on
Linux x86-64. A full scalar sweep covers single-scalar inputs; finite generated
and context suites do not prove agreement for every possible string. Additional
locale data/settings, alias and fallback behavior, public-library integration,
all regex capabilities, the other five native targets and the required
performance/memory measurements remain open work in the
[capability matrix](../development/capability-matrix.md). The library's `getloc`
contract and the existing PRIMARY evidence are not changed by this stage.
