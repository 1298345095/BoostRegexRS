# ICU77 reordering correction and retained acceptance

Date: 2026-10-18. Scope: U03's explicit settings API, script range calculation,
complete key output and native differential tools. This collection retains the
actual executions; creating an archive did not rerun a candidate or change an
original result. The standalone regex library and arbitrary locale ID resolver
remain separate acceptance work.

## Mechanism and source boundary

Candidate B's imported-table validator rejected three valid long native script
orders. The reduced order is `[120, 180, 177, 135, 82, 159, 78, 20, 28]` with
input `a`. ICU77's `setReordering` uses unsigned eight-bit table arithmetic: this
order maps lead `0xfd` to `0xff` and lead `0xfe` to zero. Its retained split
ranges are `fe000002` and `ff00ff02`. A rule that forbids zero on every used
whole-byte lead rejects a real native representation. Retained ranges alone
also omit the table prefix below the first split and cannot validate that prefix.

Candidate C's `Reordering77::from_icu` regenerates the complete representation
from the supplied integer codes and the fixed `scriptsIndex`/`scriptStarts`
metadata, then compares every table byte and retained range. It accepts the
native zero minimum when `aliasReordering` has no split ranges. No locale
profile, text input or expected key participates in validation. Required ranges
and corrupted table bytes still fail before key writing. The CE iterator, FCD
cursor, numeric encoding and level writers did not change in this correction.

The pinned mechanisms are ICU4C 77.1
[`CollationData::makeReorderRanges`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationdata.cpp)
and [`CollationSettings::setReordering`, `aliasReordering`, `reorderEx`](https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/collationsettings.cpp).
The source map is [LOCALE-MECHANISMS.md](../../../../../../tools/icu-probe/primary/rust/LOCALE-MECHANISMS.md).
Fixed data and licenses remain in the [data provenance](../../../../../../tools/icu-probe/primary/data/NOTICE.md).

## Actual results and classifications

| Execution | Complete observed comparison | Result |
| --- | --- | --- |
| C root reorder setters | 46,463 rows: 214 singleton codes, all 45,796 ordered pairs, 48 outside-code cases, 384 fixed-seed longer orders and 21 controls | 45,752 `U_ZERO_ERROR`, 676 `U_ILLEGAL_ARGUMENT_ERROR`, 35 `U_BUFFER_OVERFLOW_ERROR`; all statuses match |
| Before/after state | 92,926 before-state PRIMARY/IDENTICAL keys and 232,315 after-state keys across all five strengths | All 325,241 full sequences match; all 711 failed setters preserve state |
| Public Boost internal-NUL cases | All 31 unusual rows expressed as actual `colReorder` locale requests | 62 full ICU keys and 62 actual Boost u32 vectors match; both processes exit 0 |
| Public Boost locale reset | `am` → `am@colReorder=Grek-Latn` → `am` | Six nonempty PRIMARY/IDENTICAL keys match direct fixed ICU; ordinary destruction completes, process exits 0 |
| Frozen C regression before golden integration | 33 Rust tests, format, Clippy with warnings denied, release build and linkage | Pass; no ICU/Boost/libstdc++ runtime dependency |
| C golden integration | All 938 independently extracted native rows through both `Collator77` and the external owner/settings CLI, 244 groups per entrance | 1,876 complete raw-key and Boost-vector checks pass; full crate has 35 passed, 0 failed, 0 ignored tests |

The root setter generator uses SplitMix64 seed `0x554f3352454f5244`. It derives
codes and input coverage from pinned script metadata, not reference keys or a
host Unicode database. This finite matrix does not cover every possible long
permutation. `INT32_MIN`, outside ICU77's safe reorder-code arithmetic domain,
remains explicitly unverified. All 538 exported effective configurations,
compression/numeric limits, three input widths and 99/100/101-byte boundaries
belong to the separate [frozen B suites](../../acceptance-publication/2026-10-18-v1/README.md).
Those executions are not relabeled as C executions.

The original C root run's driver exited 1 because its comparison code assumed
that a raw key cannot contain an internal NUL. Its native and Rust processes
had both already exited 0 and emitted all rows. The original summary,
traceback/driver observation, input and output files remain unchanged inside
`reorder`. `verify_reorder_run.py` performed a new evidence-only comparison,
retained all 31 unusual-byte observations and completed with exit 0 after the
public Boost experiment established the actual full-vector behavior. Removing
the mistaken harness assumption did not remove any input, byte, length, status
or before/after-state check.

The direct ICU `am` → explicit `[14, 25]` → DEFAULT diagnostic remains a
**reference error**: it writes its keys, then dies with signal 11 on normal
destruction. `CollationSettings::copyReorderingFrom` aliases the default
collator's non-owned reorder pointer while leaving the destination's old owned
capacity, and the destructor subsequently frees that aliased storage. The
original executable and raw failure are retained in
[default-reset-retained-v1-20261018](../default-reset-retained-v1-20261018/summary.json).
Boost's [`icu_regex_traits::imbue`](https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/icu.hpp)
constructs fresh private collators; it exposes no public DEFAULT setter on the
existing owned ICU buffer. The separate public Boost reset experiment above
therefore succeeds without bypassing destruction or modifying the official
source. No additional compatibility exception is claimed.

The original B failure and its actual executables remain in
[reorder-failure-retained-v1-20261018](../reorder-failure-retained-v1-20261018/summary.json).
The older Windows evidence and ADR-0005 remain unchanged. Empty-input approved
keys are reported separately from ordinary comparisons; an internal NUL in a
nonempty key is not an ADR-0005 exception.

## Frozen identities

| Item | SHA256 |
| --- | --- |
| C `rust/src/settings77.rs` | `2a31b5e93689803ce2e8759ce0860da69542ca1b58c624cb33e11feac9f4f657` |
| C original settings probe, 639,800 bytes | `78ce0dee563a738ddc58fb82c6d085bd84917a0fd97822748c59dd6ce1f1ad8a` |
| C settings probe with diagnostic Boost fields, 643,928 bytes | `9cbe2d53a454d241b0937c6891023166395bfc01a2511126daeaff0e4ee6c49d` |
| Native settings reference | `f7d034c8d40bf8a2d0d0a5681dae0f483176f17d30353b5e1147297e20bf6f8d` |
| Native public Boost reorder experiment | `e04ecdc7deab52760cc2379356a7d5b5441a05de598a13c0ce8a6b1ef0ee1286` |
| Native public Boost reset experiment | `699c659ae4bd89c4a9f925ec9e329140bbc5e1bf475e5864c931f3b76ca17ba5` |
| 938-row native fixture | `760533a8fee8408ad8c1bc9a953d8c661e242d88006cc671f8f2f45269d6bc0a` |

The Linux x86-64 development reference uses official Boost.Regex 1.89.0,
ICU4C 77.1, Unicode 16.0.0 and CLDR 47, GCC 13.3 and glibc 2.39. Rust is stable
1.99.1 (`58cf8f9c35b355199727627d07ae34a4e2846d67`, 2026-10-13), installed from
the 2026-10-15 stable manifest SHA256
`fb152be80975c194aa5fc684b2aec3a6e14e2b855efe2faa4e5f8ae6e590f463`.
Build summaries retain exact compiler, native archive/library, runtime source,
fixture and executable identities. The extra Boost-field driver changes only
diagnostic output, and both C builds record the identical runtime source hashes.

## Retained files and reproduction

| Package | Members | Archive bytes | Original archive SHA256 |
| --- | ---: | ---: | --- |
| [reorder](reorder/manifest.json) | 233 | 3,274,992 | `994c2c7b093fa21234a9de94c9f16d7188a0c16e8ff971202e7c4626c244987d` |
| [boost-scope](boost-scope/manifest.json) | 65 | 16,501,756 | `ecd7418c59d4db6452dea01645076175dfb4df77700b7fd1b1ee7025134b40cf` |
| [goldens](goldens/manifest.json) | 37 | 1,463,072 | `a2066b1d014132ebe97bec44cc1b279146f8de47b7880ac53bb328ecd4f8e7ee` |

Each package contains original run directories under `runs/`, source snapshots,
actual selected binaries, licenses, a file manifest and a completed archive
verification. The shared native settings executable is already retained in the
B failure package. The golden test CLI hash was first recorded at retention
after the completed Cargo test; that timing is explicit in the collection.
Expanded run folders and unfragmented split archives are not duplicate Git
deliverables. The Boost scope archive is represented by two transport parts;
reassembly preserves every original archive byte.

From the repository root, after selecting an unused output filename:

```sh
timeout --signal=TERM --kill-after=5s 60s python3 -B tools/dev/split_artifact.py join \
  --manifest docs/research/assets/icu77-locales/settings-acceptance/reorder-publication-c-v1-20261018/boost-scope/raw.tar.xz.parts/manifest.json \
  --output /tmp/boostregexrs-icu77-boost-scope-c.tar.xz
timeout --signal=TERM --kill-after=5s 180s python3 -B tools/icu-probe/primary/archive_evidence.py \
  --verify docs/research/assets/icu77-locales/settings-acceptance/reorder-publication-c-v1-20261018/boost-scope \
  --archive /tmp/boostregexrs-icu77-boost-scope-c.tar.xz
timeout --signal=TERM --kill-after=5s 180s python3 -B tools/icu-probe/primary/archive_evidence.py \
  --verify docs/research/assets/icu77-locales/settings-acceptance/reorder-publication-c-v1-20261018/reorder
timeout --signal=TERM --kill-after=5s 180s python3 -B tools/icu-probe/primary/archive_evidence.py \
  --verify docs/research/assets/icu77-locales/settings-acceptance/reorder-publication-c-v1-20261018/goldens
```

The [settings tools README](../../../../../../tools/icu-probe/primary/settings-probe/README.md)
gives fresh build and execution commands. Original command arrays, per-process
deadlines, stdout, stderr and terminal statuses remain in each archived run.
`package_evidence.py --group reorder|boost-scope|goldens --output NEW_DIRECTORY`
reproduces collection from those unchanged expanded directories. Tests compare
keys derived from supplied inputs; no reference process is a runtime backend.

Still outside this result are locale ID parsing/resource fallback, arbitrary
custom rules, process default discovery, regex integration, full-library native
platform acceptance, and performance/memory thresholds. U01's missing older
historical failed executable remains recorded in its own evidence and is not
reconstructed or claimed present by this collection.
