# ICU77 root PRIMARY full-key prototype

This directory implements and tests a pure Rust root PRIMARY sort-key prototype
against official Boost.Regex 1.89.0 and ICU4C 77.1, with Unicode 16.0.0 and CLDR
47 fixed. Both the complete ICU byte sequence and every element of Boost's
exposed `vector<UChar32>` are compared. Sorting signs are an additional check.

The implementation uses complete ICU77 character/context tables and calculates
keys from the input. It does not look up known test strings, use the oracle's
answers as mappings, or normalize the input in advance. The actual root defaults
are retained: normalization OFF, numeric OFF, non-ignorable alternate handling,
case level OFF, and no reordering. C++ and ICU are development-only reference and
data-generation dependencies. The standalone Rust package has no dependencies,
FFI, build script, or calls to reference programs.

See the [Rust implementation and CLI](rust/README.md),
[data generation and CE diagnostics](export/README.md),
[binary format](data/FORMAT.md), and [source/license notice](data/NOTICE.md).
The stage follows the [cloud handoff](../../../docs/research/cloud-handoff.md)
and [implementation plan](../../../docs/research/sort-key-implementation-plan.md).

## Reproduce the complete stage

From a clean checkout on Linux x86-64 with glibc, Python 3.12+, `curl`, `make`,
`cc`, `c++` with C++17 support, and Git available:

```sh
python3 -B tools/icu-probe/cloud/run.py \
  --jobs 6 \
  --snapshot docs/research/assets/icu77-cloud
```

This command completed with exit 0 for the recorded run. It downloads official
Boost and ICU source archives, checks the pinned and published digests, builds
full-data ICU locally, installs the recorded official Rust stable toolchain,
regenerates the missing code-point reference, and replays both historical
corpora. It then runs the data exporter with `--check`, builds both PRIMARY
executables, compares all corpus groups, audits full CE64 traces, and runs Rust
tests, formatting, clippy with warnings denied, and Python harness tests.

Dependencies, compiler components, binaries, complete generated corpora, keys,
and logs stay under `target/research/icu77-cloud`. There is no dependency on the
historical `D:/` or `C:/` paths. The `--snapshot` destination receives compact
new evidence, including source/output identities and representative full keys;
the existing Windows evidence is preserved separately. Choose new `--cache`
and `--snapshot` directories when retaining another independent run.

The default compiler is official stable 1.99.1 from the recorded 2026-10-15
channel manifest. Its component hashes, actual versions, local loader settings,
and linker flags are recorded; this pins the measurement, not an enduring MSRV.
`--system-rust` uses an already installed stable and records that identity.
`--skip-all-scalars` is available for a shorter diagnostic run and labels the
result accordingly; it does not reproduce the full recorded coverage.

### Rerun PRIMARY in an already prepared environment

With a stable `cargo` on PATH, or the local compiler environment prepared by the
cloud entry point:

```sh
python3 -B tools/icu-probe/primary/export/generate.py --check
python3 -B tools/icu-probe/primary/run.py
```

`primary/run.py` defaults to the same cache and writes `CACHE/primary/`. It
builds the C++ oracle and the Rust release executable, rereads contexts from the
fixed binary, and tests every group, including all scalar single-character
inputs. Its options are `--cache DIR`, `--output DIR`, `--count N` for the random
corpus, `--skip-build` for reusing recorded binaries during diagnosis, and
`--skip-all-scalars`. These controls do not replace the complete-stage command's
source preparation, historical replay, CE audit, or validation gates.

The standalone generator supports an explicitly selected seed:

```sh
python3 -B tools/icu-probe/primary/generate_cases.py \
  --output target/research/icu77-cloud/custom-cases \
  --count 20000 --seed 0x0042494355373701 --all-scalars \
  --contexts target/research/icu77-cloud/build/root-contexts.json
```

The context report is produced by the PRIMARY runner or the data export tools.
Random generation uses the specified SplitMix64 algorithm. Context sequences
and combining-class data come from the fixed ICU77 export, with no dependence
on the host Python Unicode database.

## Reference and candidate protocol

Input is a two-column TSV with a header and a nonempty, unique `case_id`. The
runner and comparator require the same IDs, row order, and coverage on both
sides. Empty encoded input is an empty string; it is not a missing row.

| Input mode | Header | Value representation | Checked input boundary |
| --- | --- | --- | --- |
| `utf8`, the default | `case_id<TAB>utf8_hex` | Continuous two-digit byte hex | Valid UTF-8, including NUL |
| `u32` | `case_id<TAB>u32_hex` | Comma-separated eight-digit hex units | Unicode scalars; surrogates and values above U+10FFFF are rejected |
| `u16` | `case_id<TAB>u16_hex` | Comma-separated four-digit hex units | Valid UTF-16 pairs; unpaired surrogates are rejected |

The C++ oracle uses Boost's checked UTF conversion iterators and calls the
unmodified `icu_regex_traits::transform_primary`. Independently, it calls ICU
with a valid address and explicit UTF-16 length to obtain raw bytes. The Rust
candidate uses the corresponding checked input domains. The separately named
Rust `--icu-utf16-only` and C++ CE-trace modes can investigate arbitrary UTF-16
units, but they are not part of the checked Boost adapter pass count.

Both PRIMARY executables write:

```text
case_id	raw_icu_hex	boost_u32_hex
empty	00	00000000
a	2b,00	0000002b
```

`raw_icu_hex` contains every two-digit ICU byte, including its final zero.
`boost_u32_hex` contains every eight-digit u32 element: each byte is promoted
individually, and the final zero is removed only if the raw key has more than
one byte. Empty and entirely primary-ignorable input therefore retain the
single zero. Embedded NUL does not terminate explicit-length input. Primary
lead-byte compression, high/low compression terminators, U+FFFE merge boundaries,
and long keys are observable parts of the compared result.

Invalid encodings use the same typed marker in both key fields:
`ERROR:INVALID_UTF8`, `ERROR:INVALID_UTF16`, or `ERROR:INVALID_UTF32`. The
comparator derives validity independently from the input, so two incorrect
rejections of a valid string cannot count as a pass. Malformed hex or TSV is a
protocol error, distinct from a well-formed encoding of invalid Unicode.
Candidate `ERROR:UNSUPPORTED_CE32` is explicitly uncovered, not a key.

For a selected corpus, complete outputs can be compared directly:

```sh
python3 -B tools/icu-probe/primary/compare.py \
  --cases target/research/icu77-cloud/primary/cases/directed.tsv \
  --reference target/research/icu77-cloud/primary/directed/reference.tsv \
  --candidate target/research/icu77-cloud/primary/directed/candidate.tsv \
  --ordering target/research/icu77-cloud/primary/directed/icu-ordering.tsv \
  --output target/research/icu77-cloud/primary/directed/recheck.json
```

`--input-format utf8|u32|u16` selects the input domain; `--ordering` is optional.
The comparator exits 0 for complete agreement on the recorded inputs, 1 for
differences or incomplete coverage, and 2 for malformed evidence or an invalid
oracle. A raw ICU key inconsistent with the independently obtained Boost key
invalidates the oracle. Missing, duplicate, reordered, extra, or malformed rows
are rejected, and complete long fields are read without truncation.

### Native failures remain reference errors

`reference_process.py` normally streams a corpus through one native subprocess.
If it dies from a signal, the original stdout/stderr is retained and failing
ranges are bisected to isolate individual inputs. An isolated crash produces an
`ERROR:SIGNAL_N` reference row. A batch-only or intermittent crash that disappears
when split remains an unresolved reference failure; successful subranges cannot
erase the original failure. Ordinary nonzero exits, launch failures, and
malformed output stop execution instead of being retried as signal failures.

Results distinguish `passed`, `mismatched`, `unsupported`, `reference_error`,
and `rejected_as_expected`. Native failures never become empty keys or Rust
passes. The historical empty IDENTICAL failures and the separately approved
ADR-0005 expected keys remain outside this PRIMARY result.

## Recorded coverage and results

The [cloud stage summary](../../../docs/research/assets/icu77-cloud/primary/cloud-summary.json)
records **1,160,181 valid complete keys equal on both raw ICU bytes and Boost
u32 elements**, plus **11 expected typed rejections**. There were zero Rust
differences, unsupported inputs, or PRIMARY reference errors.

| Corpus | Valid keys passed | Expected rejections | Coverage |
| --- | ---: | ---: | --- |
| Directed | 12,062 | 0 | Existing 24 and non-FCD 13 cases; ASCII, accents, combining marks, NUL, ignorables, Han, all 11,172 Hangul/Jamo decompositions, supplementary and unassigned characters, compression and long keys |
| Contexts | 16,046 | 0 | Every exported prefix/contraction entry, surrounding text, truncated and divergent paths, interrupted paths, and multiple skipped marks |
| Fixed-seed generated | 20,000 | 0 | Uniform scalar strings and mixed character pools; SplitMix64 seed `0x0042494355373701` |
| All scalar single characters | 1,112,064 | 0 | Every Unicode scalar through U+10FFFF; surrogate values are tested separately |
| UTF-32 boundaries | 4 | 6 | Empty/NUL, scalar boundaries, surrogate values, and values above U+10FFFF |
| UTF-16 boundaries | 5 | 5 | Empty/NUL, valid supplementary pairs, and unpaired units |
| **Total** | **1,160,181** | **11** | **1,160,192 input rows** |

The longest observed raw key has 30,001 bytes. Directed cases explicitly hit
raw key lengths 99, 100, and 101, exercising Boost's stack-buffer and allocation
boundary. Another 48,105 adjacent-input ICU comparisons agree with candidate
key ordering. Independent CE64 audits pass all 28,108 directed/context inputs,
including primary-ignorable CEs and the end sentinel; this checks iteration
details that PRIMARY bytes alone could conceal.

The Rust package's 11 regression/integration tests, formatting check, and
`clippy --all-targets -- -D warnings` pass. The runner executes the candidate
without the ICU library search path and with `ICU_DATA` pointing to an absent
directory; linkage inspection shows no ICU, Boost, or C++ standard library
dependency. Data regeneration with `--check` reproduces the checked-in binary.
Detailed gate logs and identities accompany the new cloud evidence.

The final clean-checkout [GitHub Actions run](https://github.com/1298345095/BoostRegexRS/actions/runs/39027271124)
also passes the complete suite on commit
`9e57799d39c7610bfb6a93b1e7f8a51205e5b4a7`. Its extra CLI regression rejects
signed hexadecimal fields in all three input modes while continuing subsequent
valid rows. The earlier local snapshot records 10 tests; the final
[CI test log](../../../docs/research/assets/icu77-cloud/github-actions/validation/primary-tests.log)
records 11. All six corpus input/reference/candidate file-hash triplets match
the local full-key evidence exactly.

Complete generated inputs, full keys, per-group JSON summaries, process records,
and CE traces are retained under `CACHE/primary/`. Each summary records hashes
of the exact input and outputs. Compact snapshots contain representative full
keys plus identities for regenerating the larger evidence; a summary is not a
replacement for replaying the full corpus.

## Scope and next work

The finite suites and complete single-scalar sweep are strong regression
evidence, not a mathematical proof for every possible string. Full CE64
agreement on the audited corpus is not acceptance of an IDENTICAL key writer.
The historical 145 ICU4X IDENTICAL ordering differences remain a later-stage
regression target and are not reported as fixed here.

IDENTICAL, other locales and their FCD/settings paths, the complete regex
engine, six-platform acceptance, and performance/memory release gates remain
future work. `getloc` retains its existing default-locale contract, and
`librime-rs` integration remains deferred. The prototype currently buffers
decoded input and CEs; this stage makes no performance or memory acceptance
claim.
