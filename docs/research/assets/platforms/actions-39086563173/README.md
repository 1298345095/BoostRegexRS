# Six native targets: ICU77 research-crate revision B

The existing [Native Rust collation checks run 39086563173](https://github.com/1298345095/BoostRegexRS/actions/runs/39086563173)
completed successfully on all six ADR-0002 targets on **2026-10-18 UTC**.
Each target executed the same **31 Rust tests**, with **0 failed, ignored,
measured or filtered tests**, and all **11 recorded commands** returned 0.
The separate doctest command succeeded but contained **0 tests**.

This evidence belongs to the committed collation research crate at:

- Commit: `c4a161c0650b4b5433f5c437692cde3f5cb42a4d`.
- Tree: `26265ca903614a2b32fe5e928d1a543b7dd036d1`.
- Crate: `tools/icu-probe/primary/rust/Cargo.toml`.
- Data: ICU4C **77.1**, Unicode **16.0.0**, CLDR **47**.

The commit identifies revision B used in the collation work. The later
revision C wrapping-reorder correction, the root byte regex engine and its
formatter were not tested by this run. Full-library six-platform acceptance
remains open; every archived summary explicitly records
`full_library_platform_acceptance: not_established_by_this_workflow`.

## Actual environments and results

The [retained GitHub job metadata](github-jobs.json) records six completed,
successful native jobs, all for this exact commit and run attempt 1. They
started between 01:27:40 and 01:27:45 UTC and finished between 01:27:58 and
01:28:41 UTC. Each ZIP contains its raw environment and command records.

| Target | Runner | Observed system/runtime | Native tests | Input identities |
| --- | --- | --- | ---: | --- |
| `x86_64-pc-windows-msvc` | `windows-2025` | Windows Server 2025, build 10.0.26100 | 31 passed | 565 exact + 36 CRLF text |
| `aarch64-pc-windows-msvc` | `windows-11-arm` | Windows 11, build 10.0.26200 | 31 passed | 565 exact + 36 CRLF text |
| `x86_64-unknown-linux-gnu` | `ubuntu-24.04` | Linux 6.17.0-1022-azure, glibc 2.39 | 31 passed | 601 exact |
| `aarch64-unknown-linux-gnu` | `ubuntu-24.04-arm` | Linux 6.17.0-1022-azure, glibc 2.39 | 31 passed | 601 exact |
| `x86_64-apple-darwin` | `macos-15-intel` | macOS 15.7.9, Darwin 24.6.0 | 31 passed | 601 exact |
| `aarch64-apple-darwin` | `macos-15` | macOS 15.7.9, Darwin 24.6.0 | 31 passed | 601 exact |

All six used Rust stable **1.99.1** (`58cf8f9c3`, 2026-10-13), full compiler
commit `58cf8f9c35b355199727627d07ae34a4e2846d67`, LLVM **23.1.1**, and Cargo
**1.99.1** (`5f94df478`, 2026-08-27). The compiler host equals the requested
target. A separately compiled program was actually executed and reported the
expected architecture, operating system and 64-bit pointer size. The Windows
targets use the MSVC ABI; no separate C++ compiler-version measurement was
performed in this workflow.

| Target | Recorded image version | Python |
| --- | --- | --- |
| Windows x64 | `20261007.264.1` | 3.12.10 |
| Windows ARM64 | `20261013.183.4` | 3.13.16 |
| Linux x64 | `20261012.334.1` | 3.12.3 |
| Linux ARM64 | `20261012.149.1` | 3.12.3 |
| macOS Intel | `20260824.0482.1` | 3.14.7 |
| macOS ARM64 | `20260907.0337.1` | 3.14.7 |

The workflow selected `stable-<target>` at execution time. These recorded
versions identify the actual runs; rerunning the stable selector later does
not automatically reproduce that compiler build.

## What ran

The [collector at the tested commit](https://github.com/1298345095/BoostRegexRS/blob/c4a161c0650b4b5433f5c437692cde3f5cb42a4d/tools/ci/native_rust.py)
records two Git identity commands, Rust/Cargo version commands, host-probe
compilation and execution, then `cargo fmt --check`, Clippy with
`--locked --all-targets -- -D warnings`, executable tests with
`--locked --all-targets`, doctests, and documentation with `--locked --no-deps`.
Every Cargo command names the research crate explicitly. Each subprocess has
a 900-second deadline; the [workflow](https://github.com/1298345095/BoostRegexRS/blob/c4a161c0650b4b5433f5c437692cde3f5cb42a4d/.github/workflows/native-rust.yml)
has a 30-minute job deadline. No process error or timeout was reported.

The seven executable-test harness totals were **5 + 0 + 3 + 1 + 6 + 7 + 9 = 31**
on each platform. This is 31 distinct named tests repeated on six native
targets, rather than 186 distinct coverage cases.

| Test group | Tests per target | Recorded behavior exercised |
| --- | ---: | --- |
| Library unit tests | 5 | FCD fast flags and original UTF-16 cursor traces; settings/range validation |
| CLI binary unit-test harness | 0 | No unit tests in this harness |
| `cli` | 3 | Embedded data without reference environment, input-error continuation and signed-field rejection |
| `fcd_replay` | 1 | Retained full-key and CE fixtures with FCD enabled and disabled |
| `locale_mechanisms` | 6 | Published tailoring owners load; all strengths, numeric/FCD position errors and exported reordering settings |
| `root_identical` | 7 | NFD and CE-input separation, complete key levels, BOCSU boundaries and checked input positions |
| `root_primary` | 9 | Input adapters, contractions, prefixes, Hangul/expansions, complete primary compression, empty and long keys |

The tests replay the committed fixtures, including complete key and collation
element observations generated earlier. No Boost/ICU reference executable was
run by these 11 commands. This is therefore native Rust regression evidence,
not a fresh six-platform Boost differential experiment. Successful documentation
generation is recorded separately from the empty doctest run.

## Preserved archives and source identity

The original ZIPs were downloaded on 2026-10-18 UTC. Each contains **34 members**:
one summary plus stdout, stderr and a process record for each of 11 commands.
[artifact-source.json](artifact-source.json) retains the official artifact
metadata, download times, original archive sizes and SHA-256 values, and every
member's size and SHA-256. Archive hashes match the recorded GitHub digests;
all ZIP CRCs and member hashes were verified. Temporary download URLs were not
saved.

| Original ZIP | GitHub artifact ID | Bytes |
| --- | ---: | ---: |
| [x86_64-pc-windows-msvc.zip](x86_64-pc-windows-msvc.zip) | 12120499585 | 37,636 |
| [aarch64-pc-windows-msvc.zip](aarch64-pc-windows-msvc.zip) | 12121460082 | 37,803 |
| [x86_64-unknown-linux-gnu.zip](x86_64-unknown-linux-gnu.zip) | 12121062191 | 37,771 |
| [aarch64-unknown-linux-gnu.zip](aarch64-unknown-linux-gnu.zip) | 12120124871 | 37,849 |
| [x86_64-apple-darwin.zip](x86_64-apple-darwin.zip) | 12120773739 | 37,527 |
| [aarch64-apple-darwin.zip](aarch64-apple-darwin.zip) | 12120389741 | 37,580 |

Each summary records **601 source/data input identities**: the crate manifests,
collector and host probe, all research-crate source/test files, and the frozen
primary data directory. The [original input reconciliation](input-verification.json)
is retained unchanged. All four Unix runs match the fixed commit's Git blobs
for all 601 paths. Both Windows runs match 565 blobs exactly. The remaining
36 paths are the explicitly listed text files: replacing each Git blob's LF
with CRLF produces exactly the recorded byte count and SHA-256. The binary
tables match without any transformation.

The Windows records have their own original hashes. They were not rewritten
to match Unix records, and their source-byte identities must not be described
as identical across all six platforms. The verifier applies the one observed
text transformation only to those retained paths; an unlisted mismatch fails.

## Reproduce the evidence checks

From a checkout containing this report, the six ZIPs and the fixed Git commit,
run the following Linux/GNU-timeout command. It needs Python 3.9 or newer and
Git; it reads archived members directly and writes no files.

```sh
timeout --signal=TERM --kill-after=5s 60s python3 -B docs/research/assets/platforms/actions-39086563173/verify_inputs.py
```

This command was actually run on 2026-10-18 UTC and returned **0**. It verified
all six archives and **204 members**, reproduced the per-platform input counts
above, and confirmed 31 executable tests, zero doctests and 11 successful
commands for each target. This was an archive replay, with no new native test
execution.

The script checks the six GitHub job identities/statuses, archive/member
digests and CRCs, exact commit/tree outputs, command records, native host and
compiler identities, the seven test totals and the zero-doctest result. It
loads the 601 scoped Git blobs with one `git cat-file --batch` process and
reconciles each platform manifest and the existing input verification record.
Each Git subprocess has its own 20-second timeout. A missing object or any
mismatch raises an error and returns a nonzero exit status; there is no
fallback that marks an unavailable check as passed.

If a shallow checkout lacks the recorded commit, obtain that historical object
first, then rerun the verification command:

```sh
timeout --signal=TERM --kill-after=5s 60s git fetch --no-tags origin c4a161c0650b4b5433f5c437692cde3f5cb42a4d
```

This replay verifies the retained observations. It does not build or execute
Rust, launch CI, or replace the original archives with newly produced results.
Any later native run should retain a separate run directory and its actual
toolchain, source and data identities.

## Remaining acceptance

The complete public regex library, later collation revisions, native
Boost/ICU differential execution on all six platforms, complete locale/API
coverage, meaningful doctest examples and the ADR-0003 performance/memory
thresholds remain separate work. These logs contain ordinary command elapsed
times, not matched-workload Boost performance or memory measurements. No
release or full-library completion follows from this research-crate result.
