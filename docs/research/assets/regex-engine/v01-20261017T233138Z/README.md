# V01: fresh Linux native reference and complete-result smoke

This run completed the native reference build and smoke defined by
[V01 / issue #8](https://github.com/1298345095/BoostRegexRS/issues/8).
The clean native build used commit
`fb159eeb4583727cc70db4b9e53f8329fd25d8b8`; its original evidence is retained
unchanged in [summary.json](summary.json) and [raw-run.tar.xz](raw-run.tar.xz).
The reporting-only metadata locator correction is verified separately below.
No Rust candidate comparison, whole-library acceptance or additional native
platform acceptance is claimed by this artifact.

## Actual environment and execution

| Item | Observed value |
| --- | --- |
| Host | Ubuntu 24.04.3 LTS, Linux x86-64, glibc 2.39 |
| C / C++ compiler | GCC / G++ 13.3.0, Ubuntu `13.3.0-6ubuntu2~24.04` |
| Linker | GNU ld / GNU Binutils for Ubuntu 2.42 |
| Reference dialect | C++17 |
| Boost | Official 1.89.0 |
| ICU | Official ICU4C 77.1 |
| Character data | Unicode 16.0.0, CLDR 47; runtime reports CLDR `47.0` |
| Upstream source patches | None |
| ICU configuration | Shared and static; full release data; tests/samples disabled for this dependency build |
| Native run start / finish | 2026-10-17 23:31:57.277052 UTC / 23:36:07.116744 UTC |
| Native run elapsed | 249.84 seconds; outer deadline 2,400 seconds |
| ICU `make -j 4` elapsed | 135.32 seconds; process deadline 1,200 seconds |
| Native runner result | Exit 0, `passed_reference_reproduction` |

The entry point created a new cache and required a clean checkout. Its recorded
`git status` output is empty and its recorded `git rev-parse HEAD` matches the
commit above. Both source archives and the complete extracted source trees were
checked before native compilation. No previous target cache was reused.

The ICU build uses `-O2 -fPIC`, `--enable-shared`, `--enable-static`,
`--disable-tests`, `--disable-samples` and `--with-data-packaging=library`.
The runner removes ICU data/filter overrides and inherited `CPPFLAGS`/`LDFLAGS`.
Reference builds use `-std=c++17 -O2 -Wall -Wextra -pedantic`, the verified Boost
headers, and the newly installed ICU include/library directories. The sort-key
executable has an explicit rpath to that ICU prefix. Full commands and actual
compiler/linker/executable/runtime-library hashes are retained in the manifest
and the raw process records.

Installed static libraries are also available for subsequent development data
generation: `libicui18n.a` (9,067,020 bytes), `libicuuc.a` (4,319,074 bytes) and
`libicudata.a` (31,896,412 bytes). These development dependencies do not become a
Rust library runtime backend.

## Source and data identity

| Source | Official archive and published digest |
| --- | --- |
| Boost 1.89.0 | [Archive](https://archives.boost.io/release/1.89.0/source/boost_1_89_0.tar.bz2), [SHA-256 publication](https://archives.boost.io/release/1.89.0/source/boost_1_89_0.tar.bz2.json) |
| ICU4C 77.1 | [Archive](https://github.com/unicode-org/icu/releases/download/release-77-1/icu4c-77_1-src.tgz), [SHA-512 publication](https://github.com/unicode-org/icu/releases/download/release-77-1/SHASUM512.txt) |

The downloaded archive digests match both the committed pins and the official
publications:

```text
Boost archive SHA-256:
85a33fa22621b4f314f8e85e1a5e2a9363d22e4f4992925d4bb3bc631b5a0c7a

ICU archive SHA-512:
a47d6d9c327d037a05ea43d1d1a06b2fd757cc02a94f7c1a238f35cfc3dfd4ab78d0612790f3a3cca0292c77412a9c2c15c8f24b718f79a857e007e66f07e7cd
```

The authoritative manifest also records archive sizes, each downloaded checksum publication's
SHA-256 and the fact that detached signatures were not verified.

| Extracted source | Complete entries | Compressed source-file manifest SHA-256 |
| --- | ---: | --- |
| Boost | 84,369 | `8bb01b3a59407e1a2ce50cf9e6bff960a1f5ff4329951b371980b59b1f59eec5` |
| ICU | 2,461 | `cf869b447eeb9c4356ca21f0e6ed44ba8ae8b22f0b7160627640c830ef0352b6` |

Every archive file/link was compared with the extracted tree. The compressed
TSV manifests preserve the path, kind, byte length and SHA-256 of every entry;
unexpected or modified source files are rejected. The extractor's own marker
is excluded from upstream content identity. Both upstream patch sets are empty.

The complete `icudt77l.dat` is 31,895,376 bytes, SHA-256
`310d9b2cb42947fad7f388b09d2ae574e2adeb60ca76abf280438908f20b2d7b`.
The build uses this unfiltered source-release package. Runtime checks verify the
ICU, data, Unicode and CLDR versions, and `ldd` confirms that the actual sort-key
process resolves all three ICU libraries from the new prefix.

## Complete-result smoke

| Family | Observed result | Retained coverage |
| --- | --- | --- |
| Byte reference | 13 rows: 12 `ok`, one expected `compile_error` | Compile, search, match, iteration, format and replacement; original byte ranges, all indexed captures and capture histories, prefix/suffix and output bytes |
| Successful compilation | Empty: `mark_count=0`, `compile_status=0`; capture pattern: `mark_count=2`, `compile_status=0` | Exact complete compilation payloads |
| Compile rejection | `code=8`, `position=1` for `(` | Actual Boost error category and original pattern byte position |
| Arbitrary bytes / NUL | Valid complete rows | Invalid UTF-8 byte as byte input; embedded NUL in pattern/input and replacement output |
| Empty / partial / iteration | Valid complete rows | True-empty input, empty iteration progress, no match and partial-match extent |
| Repeated captures | All three captures `[0,1]`, `[1,2]`, `[2,3]` retained for group 1 | `match_extra` with `(a\|b)+` on `aba` |
| Root PRIMARY | 9 complete keys | ASCII, NUL, combining input, Han, Hangul, supplementary character, non-FCD input, a 101-character key case and true empty |
| Root IDENTICAL, nonempty | 8 complete keys | The same nonempty families |
| Original true-empty IDENTICAL | **Reference error: SIGSEGV, returncode -11** | Separate bounded original Boost call; its stdout/stderr/process outcome are retained |
| ADR-0005 empty IDENTICAL | One valid-pointer reference | ICU bytes `01,01,01,01,00`; Boost exposure `00000001,00000001,00000001,00000001` |

The key checks compare each full raw ICU byte sequence with the actual Boost
u32 sequence, including terminator handling. They do not substitute ordering
signs for complete keys. The empty-input exception is applied only in the
separate explicitly requested ADR-0005 call. The original failing call is never
relabeled as a normal passed case. Root normalization remains `UCOL_OFF`.

The audit found 24 managed subprocess records: 23 returned 0 and the original
empty IDENTICAL diagnostic returned -11. No command timed out or failed to
launch. Every record has a finite deadline, literal argument array, working
directory, stdin path where applicable, stdout/stderr paths and actual outcome.
All referenced streams and input files are present in the raw archive.

## Reporting locator correction

The generic dependency preparer left its older locator
`environment.data.runtime_versions_verified_by = "reference/metadata.json"` in
this clean run. The V01 runner actually wrote and verified
`smoke/primary-metadata.json` and `smoke/identical-metadata.json`; both records are
also embedded in the original summary. The old locator does not identify a
file in this run's archive.

The follow-up `write_verified_environment` change checks each real metadata
file against the smoke result that already passed verification, then records
the two actual paths in the emitted environment report. This changes report
generation only. Source acquisition, native compilation and native calls are
unchanged.

[derived-01/environment-derived.json](derived-01/environment-derived.json)
contains the separate corrected environment report. The
[audit](derived-01/audit.json) records its source, the reporting implementation
hash, complete process outcomes and identities rechecked against the actual
native files. It verifies the archive/source-manifest digests, the recorded
clean checkout, stream/input retention, actual compiler/linker/executable/
runtime-library hashes and equality between archived and live smoke metadata.
The original summary, raw archive and native cache manifests remained unchanged.

Focused tests cover spaced `ldd` paths and emitted metadata references, including
rejection of a changed metadata file without writing a successful report:
**2/2 passed**. The actual-run reporting audit also exited 0. No additional native
build is attributed to this reporting-only change.

## V01 acceptance mapping

| Issue #8 acceptance | Evidence / status |
| --- | --- |
| Official source, build/tool/platform/data identities | Checked; original manifest, full source-file manifests and process records; corrected metadata locators separately verified |
| Fresh cache and complete ICU data | Passed on clean `fb159ee`; independent cache and complete release data |
| Actual binaries/runtime libraries and command outcomes | Passed; original hashes rechecked, 24 complete managed process records |
| Bounded complete-schema byte and PRIMARY/IDENTICAL smoke | Passed with the original empty IDENTICAL reference error and approved exception identified separately |
| Six native build recipes | Documented in the tracked tool README; actual additional target gates remain V21-V26 |

This evidence maps to `validation.official_source_identity`. The Linux reference
smoke does not close the complete Linux platform gate, the other five target
gates, Rust compatibility, regex capability coverage, or performance/memory
acceptance. It does not independently test `getloc`; the committed oracle makes
the unchanged Boost calls, and no getloc exception is expanded here. Historical
Windows evidence remains separate. No old, pruned pilot bytes are reconstructed
or cited as retained evidence in this report.

## Reproduction

The actual native command ran from
`/workspace/scratch/4b14d0e6f3a6/BoostRegexRS-v01-fresh`, a detached worktree at the
commit above:

```sh
timeout --signal=TERM --kill-after=10s 2400s \
  python3 -B tools/regex-oracle/build_reference.py \
    --cache target/research/regex-reference-fresh-network \
    --output docs/research/assets/regex-engine/v01-20261017T233138Z \
    --jobs 4
```

Use a clean checkout and new cache/output names for every new reproduction.
Python 3.12+, curl, GNU Make and native C/C++ tools are required. The tracked
[tool README](../../../../../tools/regex-oracle/README.md) describes the native
Linux, macOS and Windows/MSVC build recipes and per-command deadlines. Compiler
and host changes produce their own independently identified evidence.

The actual reporting checks ran from the recovery checkout:

```sh
timeout --signal=TERM --kill-after=5s 20s \
  python3 -B -m unittest discover \
    -s tools/regex-oracle -p test_build_reference.py

timeout --signal=TERM --kill-after=5s 60s \
  python3 -B \
    docs/research/assets/regex-engine/v01-20261017T233138Z/verify_reporting.py \
    --cache /workspace/scratch/4b14d0e6f3a6/BoostRegexRS-v01-fresh/target/research/regex-reference-fresh-network \
    --output docs/research/assets/regex-engine/v01-20261017T233138Z/derived-01
```

The reporting audit targets this exact retained run and its actual native cache;
use a new derived output directory when rerunning it. It does not download or
compile a replacement reference.

The initial sandboxed attempt failed before source acquisition because
`browser-proxy:8889` was unreachable; all four downloads returned curl code 7.
Its independent [failed summary](../v01-20261017T232849Z/summary.json) and raw
archive are retained. The successful attempt used authorized elevated network
access and a different new cache. The failed attempt is not counted as a pass.

## Artifact identity

The original raw archive is 3,547,716 bytes, SHA-256:

```text
bc37153b8e50400db0c25ab7bb6ba0b30d9bc194ebab63dcceabad98e09089b5
```

It contains the raw logs and inputs, both compressed source-file manifests,
official digest publications, environment/reference manifests and ICU configure
records. It contains no compiled libraries or executables. If transport requires
chunking, reconstruct this same archive and verify its full digest before use.
