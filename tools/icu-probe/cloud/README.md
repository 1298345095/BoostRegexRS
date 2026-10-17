# Reproducible ICU77 cloud reference and root PRIMARY prototype

The unified runner prepares the official native reference, replays the existing
evidence, regenerates the fixed ICU77 data, and verifies the pure Rust **root
PRIMARY complete sort-key prototype**. It has been executed successfully on
Ubuntu 24.04.3 LTS, Linux x86-64, with GCC 13.3.0. Actual environment identities
and test results are recorded for each run.

This is the stage defined by [the cloud handoff](../../../docs/research/cloud-handoff.md).
IDENTICAL, other locales, the complete regex engine, six-platform release
acceptance, performance/memory acceptance, and `librime-rs` integration remain
outside this stage.

## Run from a clean checkout

Use a checkout containing this stage, and run the commands from the repository
root. On Ubuntu 24.04 x86-64, install the development prerequisites if necessary:

```sh
sudo apt-get update
sudo apt-get install --yes --no-install-recommends \
  build-essential ca-certificates curl git python3 xz-utils zlib1g-dev

python3 -B tools/icu-probe/cloud/run.py --jobs 6
```

Python 3.12 or newer, a C/C++ compiler and linker, GNU Make, Git, and HTTPS
downloads are required. Allow several GiB of project-local disk space for the
full source releases, compiler, build products, and exhaustive raw evidence.
The download endpoints include Boost's official archive server, GitHub release
assets, Rust's official distribution server, and the Cargo registry used by the
locked historical candidate.

**An existing Rust installation is not required.** The default command downloads
and installs the official dated stable toolchain inside the project, including
Cargo, the standard library, rustfmt, and Clippy. The recorded channel is
`2026-10-15`, with `rustc 1.99.1`. Its official channel manifest and component
checksums are verified. This date reproduces the measured toolchain; it does not
establish a permanent minimum supported Rust version.

All dependencies and generated large files default to
`target/research/icu77-cloud`. No historical `D:/` or `C:/` location, Windows DLL,
consumer checkout, system ICU installation, or pre-existing `target` cache is
needed. The scripts do not install their downloaded dependencies system-wide.

Native preparation prints each literal command and its deadline before launch.
Downloads have a 660-second deadline, ICU configuration and installation 180
seconds each, the ICU build 1,200 seconds, and reference compilation 300 seconds.
A command's `.log` contains raw stdout, `.stderr.log` contains raw stderr, and
`.process.json` records argv, elapsed time, actual exit code and timeout status.
The process group is terminated on timeout so spawned compilers cannot keep the
command alive. Timeout status 124 is a failed run; retain the logs before retrying.
On POSIX hosts, an external SIGTERM/SIGINT is forwarded to every active native
process group, including concurrent downloads. Their records identify the
interrupting signal separately from an internal timeout (SIGTERM status 143).
Cancellation cannot unwind a child launch before registration: the signal handler
records intent, and normal control flow registers, stops and reaps the child,
writes its process record, then unregisters it before propagating cancellation.

To intentionally save a new, reviewable small-evidence snapshot as well:

```sh
python3 -B tools/icu-probe/cloud/run.py --jobs 6 \
  --snapshot docs/research/assets/icu77-cloud
```

The snapshot destination is separate from the preserved historical Windows
evidence in `docs/research/assets/icu-probe`. Ordinary local runs can omit
`--snapshot`; their complete evidence remains under `target/`.

### Options

| Option | Effect |
| --- | --- |
| `--cache DIRECTORY` | Select another project-local dependency and output directory. |
| `--jobs N` | Set ICU's native build parallelism; the local command above uses 6 and CI uses 3. |
| `--snapshot DIRECTORY` | Write the selected small evidence to an explicit new snapshot destination. |
| `--system-rust` | Optionally use an already installed stable compiler, Cargo, rustfmt, and Clippy, recording their actual identity. |
| `--skip-all-scalars` | Run a shorter diagnostic without the scalar sweep; a successful result is labelled `diagnostic_passed`, not a full-stage completion. |

## What the unified command executes

1. **Prepare and identify the reference.** Download official Boost 1.89.0 and
   ICU4C 77.1 source archives, verify their pinned digests against the official
   checksum publications, and build ICU with its complete, unfiltered release
   data. The runtime verifies ICU 77.1, Unicode 16.0, CLDR 47, and ICU data 77.1.
   The environment manifest includes the OS, compiler identities, original data
   file, installed libraries, and source/archive hashes.
2. **Rebuild and replay the existing probes.** Regenerate the 1,114,112-record
   `codepoints.bin`, both submitted sorting corpora, locale/name observations,
   original empty-input diagnostics, and ADR-0005 valid-pointer expectations.
   Rebuild the locked ICU4X 2.0 candidate and compare its nine adapted fields and
   ordering signs. Compare valid Windows/cloud reference keys element by element
   while preserving the original platform-specific error markers.
3. **Check the fixed-data generation chain.** Run
   `primary/export/generate.py --check`. The exporter verifies exact source/data
   bytes and installed-library identities, runs two independent export
   processes, checks their deterministic output, and compares the result with
   the checked-in Rust data. `--check` does not replace that tracked data.
4. **Verify complete PRIMARY keys.** Build the separate pure Rust prototype and
   compare both complete ICU bytes and Boost's exposed u32 sequences. Inputs
   include the historical corpora, all Unicode scalar single characters,
   Hangul syllables and their Jamo sequences, data-derived contexts and their
   fallback/interruption paths, combining sequences, Han, supplementary planes,
   empty/NUL/ignorable inputs, compression transitions, the 99/100/101-byte Boost
   buffer boundaries, long keys, and fixed-seed generated strings. Checked UTF-16
   and UTF-32 input rejections are counted separately from valid keys.
5. **Audit full collation elements.** Compare the original and Rust CE64
   sequences for the directed and context corpora, including primary-ignorable
   elements and the final sentinel. This catches iterator differences that a
   PRIMARY key alone could hide.
6. **Run the verification gates.** Execute the Python comparator and process
   isolation regressions, root/Cargo package tests, rustfmt checks, and Clippy
   with `--all-targets -- -D warnings` for both research packages. Check whitespace
   errors, inspect the Rust executable's native linkage, and verify that the
   PRIMARY package has no runtime Cargo dependencies.

The new Rust prototype calculates keys from input and fixed collation data. Its
runtime does not load ICU/Boost or launch the reference programs. No global NFD
preprocessing is introduced. The reference retains the actual root default
settings, and `getloc` continues to report the process default locale as required
by ADR-0005.

For source formats, algorithms, and direct diagnostic commands, see the
[data generator](../primary/export/README.md),
[Rust prototype](../primary/rust/README.md), and
[reference tools](../reference/README.md).

## Result and error semantics

The main result is `target/research/icu77-cloud/cloud-summary.json`.
`stage_status: passed` with `coverage_profile: full_recorded_suite` describes
completion of this recorded PRIMARY stage. The unified command also requires
the data, CE, test, formatting, and lint checks to complete successfully. A
failure or incomplete PRIMARY reference makes the stage non-passing; build and
protocol failures stop execution and retain their logs.

| Result | Meaning |
| --- | --- |
| `passed` key count | Both complete raw ICU bytes and complete Boost u32 elements matched for a valid input. |
| `mismatched` | A valid comparison exposed a candidate difference. |
| `unsupported` | The candidate did not provide the requested covered behavior; this is not a pass. |
| `reference_error` | The original reference failed; no compatible key is invented. |
| `rejected_as_expected` | Independently checked invalid input was rejected with the same input-format error; this is separate from a valid-key pass. |
| Unresolved reference signal range | A native failure occurred for a batch but did not reproduce in its subdivisions; the original event remains non-passing evidence. |

The old candidate still has **145 IDENTICAL ordering differences**. Its baseline
also has **230 comparison pairs affected by original empty IDENTICAL failures**.
Those historical results are preserved and reported by the unified runner;
PRIMARY stage success does not claim that they were repaired. Running
`cloud/replay.py` alone consequently returns 1 for the recorded old-candidate
replay. The valid-pointer empty IDENTICAL expectations remain separate from the
original crashing reference and from any future Rust IDENTICAL implementation.

Linux reference signals retain their actual `ERROR:SIGNAL_N` identity; Windows
retains `ERROR:ACCESS_VIOLATION`. PRIMARY normally runs each whole corpus in one
reference subprocess. On a native signal only, the harness bisects input ranges,
retains failed batches' exact stdout/stderr, and continues collecting neighboring
keys. Ordinary nonzero exits and malformed output are execution errors and are
not recursively retried.

## Evidence layout

Paths below the default cache:

| Path | Contents |
| --- | --- |
| `environment-manifest.json` | Official native-source checksums, full-data identity, OS/compiler/build and installed-library identities. |
| `rust-toolchain-manifest.json` | Dated stable manifest, verified component URLs/digests, actual compiler and Cargo versions. |
| `reference-build-manifest.json` | Reference source and executable hashes, compile commands and local-library verification. |
| `reference/` | Both original corpora, regenerated codepoint files, full keys, settings, original empty diagnostics and manifests. |
| `replay/` | Old ICU4X candidate outputs, per-corpus comparison summaries, and Windows/cloud comparison evidence. |
| `primary/cases/` | Exact directed, context, generated, scalar, UTF-16 and UTF-32 inputs plus generation identity. |
| `primary/` | Full original/candidate keys, ordering evidence, CE traces/audits, per-group and aggregate summaries, and any isolation evidence. |
| `validation/` | Test, format, Clippy, dependency and native-linkage checks. |
| `logs/` | Dependency, reference, candidate, data-generation and CE-audit build/run logs. |
| `cloud-summary.json` | Aggregate stage status, coverage, actual counts, and remaining scope. |

Large files remain reproducible from the commands above. Each selected snapshot
records hashes for omitted exhaustive files and preserves small complete-key
examples. Historical paths and hashes identify their original runs; a new run
does not require the current source files to have historical tool-source hashes.

## GitHub Actions

[The workflow](../../../.github/workflows/icu77-root-primary.yml) uses
`ubuntu-24.04`, read-only repository permissions, and the same full command with
`--jobs 3`. It is configured for manual dispatch, pushes to
`work/root-primary-cloud`, and relevant pull-request changes. Checkout and
artifact-upload actions are pinned to full commit SHAs. The job has a 45-minute
timeout.

Each run uploads its complete `reference/`, `replay/`, `primary/`, `validation/`,
and `logs/` evidence, top-level manifests and stage summary, plus a small snapshot
under `target/`. Upload is attempted even when an earlier step fails. Source
trees, download archives, native/Rust installations, Cargo caches, and compiled
build caches are excluded. Inspect the specific Actions run and its artifact for
that runner's actual status and environment identity.

The recorded final [PR run](https://github.com/1298345095/BoostRegexRS/actions/runs/39027271124)
and [push run](https://github.com/1298345095/BoostRegexRS/actions/runs/39027211113)
both passed on `9e57799d39c7610bfb6a93b1e7f8a51205e5b4a7`, including the CLI
hexadecimal-protocol regression. The final artifact contains 197 files and its
SHA256 was verified after download. The [run record](../../../docs/research/assets/icu77-cloud/github-actions/run-record.json)
and [result report](../../../docs/research/root-primary-cloud-results.md#独立审查协议修复与干净-ci)
retain exact source/environment identities and distinguish the initial local
10-test snapshot from the final 11-test Rust package result.

The historical PowerShell/MSVC commands remain documented at the
[probe entry point](../README.md#historical-windowsmsvc-probe).
