# Frozen B owner and effective-settings acceptance

Date: 2026-10-18. These are the completed U02/U03 differential runs of candidate
B, SHA256 `3fbe753614aba5fbd346fcdc0002f0a278859bfe3dc8e8657e3de89a9fc2afb4`,
1,659,856 bytes. The candidate's actual build, 31 Rust tests, source identities
and initial FCD regression remain in the
[FCD repair publication](../../fcd-repair-publication/2026-10-17-v2/README.md).
No C source change or later test run is attributed to these immutable B results.

## Complete results

| Suite | Declared coverage | Ordinary complete keys | Separate classifications | Differences / unsupported / in-scope reference errors |
| --- | --- | ---: | --- | --- |
| [owners](owners/summary.json) | All 130 owners, PRIMARY and IDENTICAL: 260 groups | 8,837,528 | 520 ADR-0005 actual-empty IDENTICAL keys | 0 / 0 / 0 |
| [CE diagnostics](ce/summary.json) | All 130 owners, 335,482 complete CE64 sequences | 670,834 PRIMARY/IDENTICAL keys | 130 ADR-0005 actual-empty keys | 0 / 0 / 0 |
| [effective configurations](configurations/summary.json) | All 538 distinct owner/settings configurations × 2 strengths × 3 input widths: 3,228 groups | 5,041,060 | 11,836 expected invalid-input rejections; 30,128 ADR-0005 actual-empty keys | 0 / 0 / 0 |
| [intermediate strengths](intermediate/summary.json) | All 538 effective configurations; SECONDARY, TERTIARY and QUATERNARY | 2,530,752 direct ICU keys | These strengths are retained CLI diagnostics, not Boost transform APIs | 0 / 0 / 0 |

Every ordinary PRIMARY/IDENTICAL pass compares both the complete raw ICU byte
sequence, including its final zero, and the actual Boost u32 return vector.
Each byte becomes one u32; only the final zero is removed when length exceeds
one. Sorting signs are not the acceptance criterion. Direct CE diagnostics
compare full CE64 sequences; the reference explicitly appends the end sentinel
that ICU's internal CE diagnostic omits.

All 130 owner coverage records, with source-data hashes, are inside the owners
archive at `inputs/owner-NNNN-utf8.coverage.json`. They list all 3,426 context
tables and 18,059 exported entries, per-entry coverage, base ownership and
owner-relative Jamo values. Root uses its full scalar domain; other owners use
every non-fallback scalar plus fallback range endpoints. Every owner includes
11,172 decomposed Hangul/Jamo inputs. Context fixtures include complete,
truncated, diverging, interrupted and multiple-skipped-mark inputs. The CE
suite adds 87,392 nested cases and retains each owner's context inventory and
raw diagnostics. Source-derived generators do not use expected keys to select
inputs.

The owners verifier records actual raw key lengths 99, 100 and 101 occurring
261, 383 and 258 times respectively. Longer keys, supplementary characters,
NUL, empty strings and compression boundaries remain in complete input/output
files. The common configuration corpus additionally covers leading zeros,
numeric dense thresholds and 254-digit segmentation, backward secondary,
case-level/first interactions, shifted variables, reordered split ranges and
all three checked input widths. Malformed UTF-8/16/32 inputs remain explicit
rejections, compared by their rejection labels. This matrix does not
differentially compare invalid-input error positions.

The full packaged data inventory has 13,982 requests, 13,979 loaded requests,
130 owners including root, 432 effective settings files and 538 distinct
owner/settings configurations. The three native private requests
`@collation=private-unihan`, `ja@collation=private-kana` and
`zh@collation=private-pinyin` remain `U_MISSING_RESOURCE_ERROR`; none is
substituted by a successful root key. The complete independently reproduced
exports are retained in the [export publication](../../export-publication/README.md).
Enumerated request metadata does not implement runtime locale resolution.

ADR-0005 applies only to actual-empty IDENTICAL input, using the separate
valid-address reference and the normal Boost wrapping convention. Original
reference diagnostics and historical Windows failures remain separate. A
nonempty ignorable input or internal zero in an output key is not silently
reclassified as that exception.

## Source, data and execution identity

The runtime is pure Rust; B runs set `ICU_DATA` to an intentionally absent path
and remove the native loader path. The fixed reference is official Boost.Regex
1.89.0, ICU4C 77.1, Unicode 16.0.0 and CLDR 47 on Linux x86-64/glibc. Rust is
stable 1.99.1 (`58cf8f9c35b355199727627d07ae34a4e2846d67`, LLVM 23.1.1).
The original summaries retain exact compiler manifests, source and executable
digests, native libraries, complete extracted-source inventories, effective
reference settings and each input identity. All compared identities remained
unchanged during the recorded runs. Full data and imported-algorithm provenance
is in [NOTICE.md](../../../../../../tools/icu-probe/primary/data/NOTICE.md).

The 938-row golden selection was extracted only after the complete 3,228-group
configuration run and its verifier passed. It uses independent native
`expected-keys.tsv` rows from 244 selected owner/settings/strength groups. Its
source, input, catalog and reference hashes are recorded in
[locales-v2.json](../../../../../../tools/icu-probe/primary/rust/tests/data/locales-v2.json).
The subsequent C Rust API/CLI execution of those goldens is reported in the
[C correction collection](../../settings-acceptance/reorder-publication-c-v1-20261018/README.md).

## Archives and exact reproduction

| Package | Files | Uncompressed file bytes | Archive bytes | Original SHA256 |
| --- | ---: | ---: | ---: | --- |
| owners | 2,497 | 4,728,457,651 | 59,258,468 | `bc3e736f4bae1e59e6d49e6ce1a34e8b220d2726d1a93fd0365aa09fc84dbcc8` |
| CE | 3,007 | 666,740,003 | 9,859,096 | `a6defb923a143fb8ed6c1e4c12aa5224c486d1ad2ee5253a66f74ecb6f294728` |
| configurations | 29,078 | 8,815,486,270 | 42,217,452 | `f9f7ff66b042f6aa6b950c9eaed99389512ad035e28532582f6ad160be8364c7` |
| intermediate | 7,549 | 2,346,934,156 | 26,598,808 | `0a9c035f3546903938a6607f212b51724ea4c46ee0948dd2eca7f8c73924fae1` |

All four archives have completed full-member verification. Each summary is the
unchanged original summary; archive creation did not replace a failed run with
a passing one. Git contains transport parts for owners, configurations and
intermediate, preserving each original archive byte. CE fits in one archive.
Expanded raw directories and unsplit copies are not duplicated in Git.

To reconstruct one of the three split archives, replace `owners` with the
desired package and choose an unused output filename. The existing splitter
verifies each part and the complete original hash; the archive verifier then
checks every recorded member:

```sh
timeout --signal=TERM --kill-after=5s 60s python3 -B tools/dev/split_artifact.py join \
  --manifest docs/research/assets/icu77-locales/acceptance-publication/2026-10-18-v1/owners/raw.tar.xz.parts/manifest.json \
  --output /tmp/boostregexrs-icu77-owners-b.tar.xz
timeout --signal=TERM --kill-after=5s 180s python3 -B tools/icu-probe/primary/archive_evidence.py \
  --verify docs/research/assets/icu77-locales/acceptance-publication/2026-10-18-v1/owners \
  --archive /tmp/boostregexrs-icu77-owners-b.tar.xz
timeout --signal=TERM --kill-after=5s 180s python3 -B tools/icu-probe/primary/archive_evidence.py \
  --verify docs/research/assets/icu77-locales/acceptance-publication/2026-10-18-v1/ce
```

The exact owner, configuration and CE command arrays are under
`execution.command` in their summaries; the intermediate array is `command`.
They run `run_locales.py --phase owners`, `run_locales.py --phase configurations`,
`run_locale_ce.py`, and `settings-probe/run.py --mode intermediate` respectively.
All use the same frozen B executable and its recorded candidate provenance.
Paths to the reference cache, executable and new output directory are explicit
arguments; no historical Windows drive is a cloud dependency. Per-process
deadlines are 180 seconds, and full process receipts are archived. For a new
source build, follow the [prototype commands](../../../../../../tools/icu-probe/primary/rust/README.md)
and preserve the resulting new candidate identity in a new run directory.

These results cover packaged owners and effective configurations. Arbitrary
locale parsing/default discovery, resource aliases and fallback, custom rules,
full regex integration, six-target full-library validation and performance or
memory thresholds are not established by these probe runs. Arbitrary script
setter inputs belong to the separately retained C correction. The original
historical missing failed executable remains an open retention condition;
the archived evidence does not manufacture a replacement.
