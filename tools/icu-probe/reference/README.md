# Boost / ICU reference probe

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
