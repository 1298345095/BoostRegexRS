# U01 FCD recovery and complete-key evidence, generation 2

The recovered implementation passes the recorded FCD cursor and full-key
comparisons. This collection preserves the independent A prerequisite and B
generic-library executions. It does not mark the complete library, all locales,
all settings or release acceptance as finished.

## Results

| Check | Actual result |
| --- | --- |
| A staged snapshot `ebc3cedc41a75fac73f805e0d99d38570433c8dd` | 21 Rust tests pass; direct rustfmt and all-target Clippy with warnings denied pass |
| B working generic library | 31 Rust tests pass; direct rustfmt, all-target Clippy with warnings denied, and release build pass |
| Native UTF-16 FCD flags | All 65,536 bytes agree |
| Native forward/backward/forward cursor traces | 26,858 rows across 1,436 inputs agree, including original UTF-16 offsets |
| Complete raw ICU and Boost-wrapped keys | 11,484 ordinary passes; 4 separate ADR-0005 empty IDENTICAL exceptions |
| Differences / unsupported / reference errors | 0 / 0 / 0 |
| Complete CE64 sequence comparisons | 11,488 rows pass; 5,744 independently generated sequences, each checked at two strengths |
| Runtime linkage | Rust candidate has no ICU, Boost or C++ standard-library dependency |

The four profiles are root with normalization OFF/ON and Faroese search
(`fo@collation=search`) with normalization OFF/ON. Each profile has 1,436 PRIMARY
comparisons and 1,435 ordinary IDENTICAL comparisons plus one approved empty
exception. Original input order is passed to the implementation unchanged.

The settings boundary regressions reject missing split ranges and inconsistent
range/table suffixes before sorting, while retaining legitimate unused zero
table slots. They derive unused leads from the fixed ICU script metadata.
The existing locale mechanism tests also load all 129 exported tailoring owners
and all 432 exported setting profiles. For every profile carrying reordering,
they regenerate its table and split ranges from the public reorder codes. These
finite mechanism checks do not replace U02/U03's complete configuration sweeps.

## Fixed identities

- Reference: official Boost.Regex 1.89.0, ICU4C 77.1, Unicode 16.0.0, CLDR 47.
- Rust: stable 1.99.1, from the recorded 2026-10-15 stable channel manifest.
- Fresh Rust candidate: 1,659,856 bytes, SHA-256
  `3fbe753614aba5fbd346fcdc0002f0a278859bfe3dc8e8657e3de89a9fc2afb4`.
- Native fixture provenance: SHA-256
  `6af09e17465bbd6e58791e0eb16c5be8264ae420d87bf4b0f9762e86ad45bf77`.
- Archive: 530,072 bytes, SHA-256
  `a840ceead8d62ecb578baa6cda759755801741489af48dc8d35001fe299b78fe`.

The archive contains all 125 collected files, totaling 29,076,685 uncompressed
file bytes. `manifest.json` identifies every member. `verification.json` records
the completed archive and per-file digest checks. The native environment
manifest was copied with its exact execution-provenance digest, so that metadata
is retained independently of the transient reference installation.

## Corpus and coverage limits

Generation revision 2 is explicit because workspace maintenance pruned the
unpublished revision-1 generator, generated inputs and execution caches. The
six historical inputs survived and are read directly from their archived
UTF-16 files. There is no claim that newly generated rows reproduce lost bytes.

| Source-defined class | Rows |
| --- | ---: |
| Exact historical failures and reductions | 6 |
| Empty, NUL, embedded NUL and merge controls | 4 |
| 381 supplementary boundary points with two combining marks | 762 |
| Tibetan fast-mask cases | 128 |
| Context/combining-order combinations | 24 |
| SplitMix64 inputs, seed `0x0042494355464344` | 512 |
| Total | 1,436 |

There are 1,409 distinct UTF-16 sequences. The generated fragment set includes
composed/decomposed accents, prefixes, contractions, supplementary combining
marks, Han, Hangul, supplementary symbols, NUL and U+FFFE. Input selection uses
the fixed ICU77 FCD ranges and the documented seed, with no host Unicode
database or reference-key-driven selection.

This FCD corpus produces PRIMARY keys of 1–27 bytes and IDENTICAL keys of
5–79 bytes. It supplies no fresh 99/100/101-byte native boundary comparisons.
Existing root regression tests still run separately, including ASCII lengths
97, 98, 99, 100, 101, 4,096 and 10,000, Greek compression, and complete
IDENTICAL fixtures. This distinction avoids attributing unrelated coverage to
the new FCD corpus.

## Historical failures remain failures

The old candidate `22721fc23f6ff811b27291234871a4e230833c653dde5a59900437b69093d5a5`
was recorded as a 1,642,720-byte binary. Its bytes were not included in the
checkpoint and the old runtime path no longer exists. The current verification
records `preserved_failed_candidate: null`; no substitute binary was created.
Its original mismatching keys, CE traces, inputs and identity records survive.
Fresh native results agree with the preserved native keys, CE traces, cursor
traces and flag bitmap.

The complete old locale run is already retained in
`docs/development/tickets/checkpoint/locale-failed-run/`: 21,677 files,
2,482,952,994 uncompressed bytes, archived SHA-256
`420e9a99cd2f08aa0920a77cc4c796f484099ca5466fd85d0e60584fd68e4d97`.
Its original status remains `differences_or_incomplete`, with 451 of 538
configurations completed and two mismatches. This collection references that
archive without copying its expanded data or counting it as a passing rerun.

The first historical fixture recovery attempt also remains in the archive with
`failure.json`: two NFD input orders were reconstructed incorrectly and caught
by offline comparison before Rust execution. The corrected generation imports
the archived inputs verbatim. Original run logs and summaries were not edited.

A's `execution-environments.json` is explicitly a post-execution supplement
for the Clippy overrides supplied by its execution owner. It includes exact tool
digests and does not claim to capture unknown inherited environment variables.

## Reproduce

From a clean checkout with Rust stable available, the frozen tests need no
native reference runtime:

```sh
timeout --signal=TERM --kill-after=5s 180s cargo test --locked --manifest-path tools/icu-probe/primary/rust/Cargo.toml
```

On Linux x64, rebuild the fixed development reference environment and choose
fresh output directories for new evidence:

```sh
timeout --signal=TERM --kill-after=5s 1800s python3 -B tools/icu-probe/cloud/prepare.py --cache target/research/icu77-cloud --jobs 4
timeout --signal=TERM --kill-after=5s 420s python3 -B tools/icu-probe/primary/rust/tests/refresh_fcd_fixtures.py --cache target/research/icu77-cloud --update-fixtures --output docs/research/assets/icu77-locales/fcd-repair/native-new
timeout --signal=TERM --kill-after=5s 600s python3 -B tools/icu-probe/primary/rust/tests/verify_fcd_repair.py --cache target/research/icu77-cloud --output docs/research/assets/icu77-locales/fcd-repair/rust-new
```

The preparation recipe enables both shared and static ICU libraries. The native
trace tools and Boost oracle are development tools. The final command installs
the recorded official stable toolchain if required and records actual compiler,
source, data and executable identities. Every child command has a deadline and
separate saved outputs. These commands require the explicitly retained history
inputs and five native history files listed by the generator and verifier.

To inspect the already recorded archive, verify it before extraction:

```sh
timeout --signal=TERM --kill-after=5s 60s python3 -B tools/icu-probe/primary/archive_evidence.py --verify docs/research/assets/icu77-locales/fcd-repair-publication/2026-10-17-v2
```

`package_fcd_evidence.py` reproduces collection and deterministic compression
from the expanded execution records; it performs no implementation test.
Track the compact publication directory and required frozen fixtures/tool
sources. Expanded raw execution directories remain outside the publication.

The algorithm source map is
[LOCALE-MECHANISMS.md](../../../../../../tools/icu-probe/primary/rust/LOCALE-MECHANISMS.md).
All-locale sweeps, complete setting combinations, production regex integration,
six-platform release verification and performance/memory acceptance remain
separate work. The new execution evidence here is Linux x64 only.
