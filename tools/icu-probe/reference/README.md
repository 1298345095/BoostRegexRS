# Boost / ICU reference probe

## Linux cloud reference

From a clean checkout on Linux with Python 3.12+, `curl`, GCC or Clang, and GNU
Make available:

```sh
python3 tools/icu-probe/cloud/prepare.py --jobs 6
python3 tools/icu-probe/cloud/reference.py
```

Both commands accept `--cache DIRECTORY`; the default is the project-local
`target/research/icu77-cloud`. `reference.py` also accepts `--output DIRECTORY`.
The preparation command downloads the **official complete source archives** for
Boost 1.89.0 and ICU4C 77.1, verifies the archive against both the published
checksum manifest and the digest pinned in the script, and extracts them to
`deps/boost_1_89_0` and `deps/icu`. ICU is built in `build/icu` and installed to
`install/icu`, with shared/static libraries and the full, unfiltered release data.
Boost.Regex's ICU traits are used from the verified external headers; no Boost
binary library is necessary for this probe.

The official checksum sources are:

- <https://archives.boost.io/release/1.89.0/source/boost_1_89_0.tar.bz2.json>
- <https://github.com/unicode-org/icu/releases/download/release-77-1/SHASUM512.txt>

The actual compiler, OS, libc, source/archive digests, complete-data identity,
build arguments and installed library digests are written to
`environment-manifest.json`. Build logs are under `logs/`. No system install,
persistent environment modification, historical drive path, or cached Windows
binary is required. `TMPDIR` is local to the cache. Native executions use only
the local ICU library directory and remove `ICU_DATA` overrides; `ldd` output is
checked and saved to establish which ICU libraries actually loaded. The locale
environment is inherited and recorded, so `getloc()` continues to query the
actual process default as required by ADR-0005.

The reference runner builds all three existing probes and writes fresh outputs:

| Path below `target/research/icu77-cloud/reference/` | Content |
| --- | --- |
| `baseline/` | The submitted 24-case corpus, full keys, rebuilt `codepoints.bin`, locale/name evidence and runtime metadata |
| `non-fcd/` | The separate submitted 13-case non-FCD corpus and full original reference keys |
| `empty-diagnostics.json` | Original empty-input calls in separate processes, including actual signal/exit status |
| `empty-keys/` | Valid-pointer empty-key expectations for ADR-0005 and constructed-collator normalization settings |
| `manifest.json` | Per-file identities, runtime versions, reference result/error counts, and build/source provenance |

On Linux, **every original Boost transform runs in a child process**. Signals
are recorded as `ERROR:SIGNAL_<number>` (for example `ERROR:SIGNAL_11` for the
observed SIGSEGV); nonzero child exits and C++ exceptions have separate `ERROR:`
markers. Core dumps are disabled for those child processes. The parent continues
collecting evidence without resuming a damaged process or inventing a key.
Windows retains the existing MSVC SEH handler and its
`ERROR:ACCESS_VIOLATION` marker. `reference.py` exits successfully when evidence
collection succeeds even if that evidence contains original-reference errors;
the comparison runner reports such rows as `reference_error`, separately from
Rust differences and missing coverage.

Once the locked ICU4X candidate is built at
`target/research/icu77-cloud/build/candidate/release/icu4x-compat-probe`, replay it
and compare the new original reference with the preserved Windows evidence:

```sh
python3 -B tools/icu-probe/cloud/replay.py
```

This writes `replay/baseline`, `replay/non-fcd`, and
`replay/cross-platform-summary.json` under the cache. Its expected exit code is
**1** for the recorded run: the existing ICU4X candidate still has 145 IDENTICAL
ordering differences, and the baseline still has 230 pairs affected by the
original empty-input reference failure. This command separately reports valid
full-reference-key equality between platforms, error categories, codepoint file
identity, and the default-locale query behavior. Add
`--snapshot docs/research/assets/icu77-cloud` only when intentionally refreshing
the separate cloud evidence snapshot. Large reproducible binaries/data remain
under `target/` and are represented by size and digest in the manifests.

All cloud results are separate from the historical Windows evidence in
`docs/research/assets/icu-probe`. The archived Windows paths/hashes identify that
past run and are not dependencies of these commands. The native tools and
dependencies are exclusively development references/data generators; they are
never linked to the pure Rust sorting-key prototype.

## Windows reference

Run from PowerShell 7 on Windows x64 with MSVC tools and GitHub CLI available:

```powershell
pwsh -NoProfile -File tools/icu-probe/reference/run.ps1
```

Optional arguments are `-BoostRoot`, `-OutputDirectory`, and `-CacheDirectory`.
Defaults use the supplied official Boost 1.89.0 checkout and the project-local
`target/research/icu-probe/reference/` cache. `-AddressSanitizer` builds the
diagnostic executables with MSVC AddressSanitizer; use a separate output directory
to preserve the normal-run evidence.

The script downloads the official ICU 77.1 Windows x64 MSVC 2022 release archive,
license, and SHA-512 manifest. It verifies the archive against that manifest.
Detached signatures are not verified. It extracts the dependency only into the
project cache, invokes MSVC through `Launch-VsDevShell.ps1`, and adds ICU's DLL
directory only to the launched process environments. No system installation or
persistent PATH change is made. The reference program requires runtime ICU 77.1,
Unicode 16.0, and CLDR 47; an unexpected version fails the run.

## Outputs

- `metadata.json`: runtime versions, default ICU locale, compiler, record count.
- `manifest.json`: source URLs, verified archive SHA-512, SHA-256 hashes of
  reference sources, Boost version/ICU trait headers, loaded-release DLL files,
  executable files, and outputs.
- `codepoints.bin`: 1,114,112 records, in code-point order from 0 to `0x10ffff`,
  including surrogate code points. Each record is ten little-endian `u32` values:
  code point, `u_tolower`, `u_toupper`, default `u_foldCase`, `u_charType`,
  `u_isblank != 0`, `u_isspace != 0`, `u_digit` for radix 10, 16, and 36. A digit
  result of -1 is stored as `0xffffffff`. This tests underlying ICU semantics;
  passing it does not establish full Boost trait compatibility.
- `sortkeys.tsv`: header `locale`, `case_id`, `primary`, `identical`; each key is
  the complete Boost `vector<UChar32>` encoded as comma-separated eight-digit
  hexadecimal `u32` values. A native access violation is represented as
  `ERROR:ACCESS_VIOLATION`, which is a reference error and must not be interpreted
  as an empty key or a Rust compatibility pass.
- `locales.tsv`: requested locale, first `imbue` return, `getloc`, second `imbue`
  return. An ICU root locale has the empty ICU locale name.
- `names.tsv`: representative Boost `lookup_collatename` inputs and full results.
  An empty result indicates lookup failure. This is not exhaustive name testing.
- `empty-diagnostics.json`: separate-process evidence for the empty-input boundary.
- `stdout.log` / `stderr.log`: captured main-program output.

`cases.tsv` is shared with the Rust candidate. It uses the header `case_id` and
`utf8_hex`; explicit hexadecimal bytes preserve empty input, embedded NUL, and
non-ASCII input. It includes an ASCII input long enough to exceed Boost's
100-byte local key buffer. The main program calls the actual unmodified Boost
traits for every key. Its narrowly scoped native exception handler permits the
remaining cases to be exported after a reference access violation.

## Observed empty-input boundary

With the official Windows x64 ICU 77.1 release, an empty Boost PRIMARY transform
returns `[0]`. An empty IDENTICAL transform causes a native access violation.
The caller provides a valid empty iterator range (`&sentinel, &sentinel`), and
Boost's `do_transform` passes `nullptr, 0` to ICU after UTF-16 conversion.

The isolated diagnostic reproduces the access violation with a direct ICU
IDENTICAL `getSortKey(nullptr, 0, ...)` call. Passing a valid pointer and length
zero directly to ICU succeeds and yields `[1, 1, 1, 1, 0]`, including ICU's
terminator. The latter is diagnostic evidence only and is not substituted for
the unavailable Boost result. Decisions about handling this boundary belong to
the project's compatibility policy.

The reference uses ICU's C++ API and is a test-only native dependency. It does not
establish that the Rust library may depend on ICU. Boost source remains external
under BSL-1.0; ICU remains external under its included Unicode license. No library
source or binaries are vendored into tracked files.

Official source and asset provenance:

- <https://github.com/unicode-org/icu/releases/tag/release-77-1>
- <https://github.com/unicode-org/icu/blob/release-77-1/icu4c/source/i18n/rulebasedcollator.cpp>
- <https://github.com/boostorg/regex/blob/boost-1.89.0/include/boost/regex/v5/icu.hpp>
