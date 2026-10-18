# Boost.Regex engine differential reference

Development reference: official Boost.Regex 1.89.0, C++17, explicitly selected
`cpp_regex_traits<char>` with the classic C locale, and capture-history support
compiled in. This byte reference accepts arbitrary bytes including NUL. It is
separate from the ICU sort-key reference and is never a Rust runtime backend.

## Fresh native reference reproduction (V01)

On a clean Linux checkout with Python 3.12+, `curl`, GNU Make and a C/C++ compiler:

```sh
timeout --signal=TERM --kill-after=10s 2400s \
  python3 -B tools/regex-oracle/build_reference.py \
    --cache target/research/regex-reference-fresh \
    --output docs/research/assets/regex-engine/reference-fresh --jobs 4
```

Both destinations must be new. No files from a previous `target` directory are
required. The recipe downloads official Boost 1.89.0 and ICU4C 77.1 and checks
their archives against the pinned and officially published digests in
`tools/icu-probe/cloud/prepare.py`. Before compilation, every extracted file is
hashed and compared with its archive member. Complete compressed source-file
manifests are retained; the upstream source patch set is empty.

The ICU build uses the complete, unfiltered `icudt77l.dat` from the source
release. It removes ICU data/filter overrides and uses project-local libraries.
The actual reference checks Boost 1.89.0, ICU 77.1, Unicode 16.0.0 and CLDR 47.
The evidence includes compiler/linker and executable identities, resolved runtime
library hashes, flags, OS/libc, literal commands, both output streams and each
exit status. All commands use the bounded helper in `cloud/prepare.py`; their
argv and deadlines are also printed while running.

`summary.json` records the outcome. `raw-run.tar.xz` preserves the build logs,
source-file manifests, complete smoke inputs/results, runtime settings and
original empty-input process outcome. It contains no compiled libraries or
executables. Each retry writes a separate directory and keeps any failed run.

The smoke covers compile errors/positions, search, match, every indexed capture
and repeated-capture history, iteration, format, replace, arbitrary byte input,
NUL in input/output and true-empty input. The key smoke records complete PRIMARY
and IDENTICAL bytes/u32 sequences for ASCII, combining input, non-FCD input, Han,
Hangul, supplementary characters, NUL and a long key. Original empty IDENTICAL
and the ADR-0005 valid-pointer expectation are separate subprocess observations.
Passing this smoke validates reference reproduction; it is not a Rust comparison
or whole-library acceptance.

### The six native build recipes

The full Linux entry point above runs on the native host architecture. The other
native hosts first use the same source-verification entry point:

```sh
python -B tools/regex-oracle/build_reference.py --sources-only \
  --cache target/research/regex-reference-fresh \
  --output docs/research/assets/regex-engine/reference-sources
```

`--sources-only` reports `verified_official_sources_only`, never a successful
reference build. Use a native developer shell for the architecture in the table.
`CACHE` below is the absolute path of the newly prepared cache. For every native
step, use `prepare.run_logged(argv, cwd=..., log=..., timeout=...)` with literal
argv, the deadlines below and a new log name. This is the same bounded command
runner used by the Linux entry point.

| Native target | ICU build recipe | Reference compiler | Validation ticket |
| --- | --- | --- | --- |
| Linux x86-64 glibc | `source/configure`, GNU Make; automatic entry point above | native GCC/Clang, C++17 | V23 |
| Linux ARM64 glibc | same configure/Make recipe on native ARM64 | native GCC/Clang, C++17 | V24 |
| macOS Intel | `source/runConfigureICU MacOSX`, GNU Make on Intel | native Apple Clang, C++17 | V25 |
| macOS ARM64 | same MacOSX recipe on Apple Silicon | native Apple Clang, C++17 | V26 |
| Windows x64 MSVC | `msbuild source/allinone/allinone.sln /p:Configuration=Release /p:Platform=x64 /m:4` | native MSVC `/std:c++17 /EHsc /O2 /MD` | V21 |
| Windows ARM64 MSVC | same solution with `/p:Platform=ARM64`, in an ARM64 developer shell | native MSVC `/std:c++17 /EHsc /O2 /MD` | V22 |

Unix configuration uses an out-of-source `CACHE/build/icu` directory and these
arguments for both Linux and macOS:

```text
--prefix=CACHE/install/icu --enable-shared --enable-static
--disable-tests --disable-samples --with-data-packaging=library
```

Set `CC`/`CXX` to the native compiler, `CFLAGS`/`CXXFLAGS` to `-O2 -fPIC`, and
`TMPDIR` to `CACHE/build/tmp`; remove `ICU_DATA`, `ICU_DATA_FILTER_FILE`,
`CPPFLAGS` and `LDFLAGS`. Run configuration (180 seconds), `make -j 4` (1,200
seconds) and `make install` (180 seconds). On macOS the configure command is
`sh CACHE/deps/icu/source/runConfigureICU MacOSX` followed by those arguments.
The Windows solution has explicit x64 and ARM64 configurations in ICU77's
shipped solution; use a 1,200-second MSBuild deadline. It emits the full data DLL
with common/i18n libraries in `bin64`/`lib64` or `binARM64`/`libARM64` under the
extracted ICU directory. Do not substitute an arbitrary system ICU.

Build `oracle.cpp` with the verified Boost include directory and
`BOOST_REGEX_NO_LIB`; capture history is defined in the source. Build
`../icu-probe/primary/oracle.cpp` with the same Boost plus ICU include directory
and `icui18n`, `icuuc`, `icudata`. Unix uses the local library directory and an
explicit rpath. MSVC uses `icuin.lib`, `icuuc.lib`, `icudt.lib` from the matching
architecture directory and places/loads the corresponding DLLs with the native
executable. Each reference compile has a 300-second deadline. Preserve the
actual loaded library identities on that host, then run the same inputs and
checks in `smoke.py` with a 20-second process deadline.

The recipe describes all six builds; native execution and full platform
acceptance are separate evidence. A Linux build never marks Windows or macOS
verified. The Linux runner records runtime paths with `ldd`; macOS and Windows
must record their actual native loaded modules in their V21-V26 artifacts.

## Protocol

Input is TSV with exactly this header:

```text
case_id	operation	syntax	match	pattern_hex	input_hex	format_hex
```

Flags use unsigned decimal Boost bit values. Byte sequences use strict even-width
hexadecimal; an empty field means an empty byte sequence. Operations are `compile`,
`search`, `match`, `iterate`, `format`, and `replace`. Default flags are zero.

Output header is `case_id\tstatus\tresult`. `result` is JSON. Successful compile
records `mark_count` and `compile_status`. Search/match/iterate record `mark_count`
and a `matches` array. Each match includes its original byte `range`, `partial`,
all indexed `groups` (unmatched groups are null), `histories`, `prefix`, and
`suffix`. Histories are requested only with `match_extra` (524288); otherwise each
history is empty. Replacement and formatting also record `output_hex`.

Ordinary compile errors record the actual Boost error `code` and original pattern
byte `position`. With `no_except`, the successful compile API call instead records
the invalid object's actual `compile_status` and `mark_count`; no missing error
position is invented. A resource code (12, 15, 18, or 19) is a non-pass reference
observation, including when it is reported through `compile_status`.

For a noncompile operation, a returned nonzero compiled-object status is also
retained as `preceding_compile`, with exactly `mark_count` and `compile_status`.
The requested operation still executes. For example, `no_except` can return
status 18 and the later matcher can throw `invalid_argument`; the row retains
the real `operation_error` and its message, together with the preceding status.
There is no invented compilation exception or error position. The common row
writer retains this outcome for later successful results and failures alike.
Successful compilation and compilation exceptions do not add this field.
The validator requires the corresponding `no_except` input flag, exact integer
fields and a nonzero preceding status. Ordinary nonresource preceding outcomes
are compared along with the later operation-error category and position.

The current native oracle preserves typed reference failures with this exact
versioned envelope:

```json
{"schema":"boostregexrs.reference-failure.v1","phase":"search","kind":"regex_resource","code":18,"position":0,"message_hex":"426f6f7374"}
```

The illustrative message above encodes `Boost`; real observations preserve the
complete original message. Its row status is `reference_failure`. `phase`
identifies the native API that
failed: `compile`, `search`, `match`, `iterate`, `format`, or `replace`; adapter
serialization failures use `serialize`. For example, a search that fails before
formatting retains phase `search`, and failures inside `boost::regex_replace`
retain phase `replace`. `kind` distinguishes `regex_resource`, other runtime
`regex` errors, `allocation`, container `capacity`, and plain C++ `runtime`
failures. Native `boost::regex_error` code/position are preserved exactly; other
exception types use null for both fields because they do not expose those Boost
properties. All messages remain as raw byte hex.

Boost uses `regex_error` for compilation and execution resource limits. Plain
`std::runtime_error` can instead indicate a traits/catalog problem. These types
must not automatically become ordinary syntax rejections or resource successes.
The strict validator rejects missing fields, a resource code with the wrong
kind, and a phase unrelated to the requested operation. The comparator keeps
reference resource/error observations separate and never passes them because a
candidate also exhausts its independently specified budget.

Historical v1 artifacts precede this envelope: they can contain execution
resource errors labeled `compile_error`, or message-only
`reference_resource_error` rows. Their original bytes and original metadata are
retained. The comparator recognizes resource codes and preserves historical
resource labels as non-pass observations; those old rows do not acquire modern
phase/code evidence retroactively. A historical noncompile `no_except` row with
`operation_error` category `invalid_argument` and no `preceding_compile` is
specifically unverified (`reference_error`): it cannot distinguish an ordinary
invalid compiled object from one rejected by a resource guard. This rule does
not reclassify ordinary match-policy errors or rows without `no_except`.
`protocol_error` and process failures remain
distinct from ordinary results and must never become empty `matches` arrays.
The bounded generator and original/corrected native verification are
`resource_cases.py` and `verify_resource_errors.py`; `--stack-only` selects the
separate linear stack-block probe, and `--no-except-flow-only` selects the
returned compilation plus subsequent-operation probes.

`oracle --metadata` records the reference configuration and the current
`reference_failure_schema` and `preceding_compile_outcome` support. Native platform traits,
locale combinations and Unicode entry points will have their own explicit
configurations and evidence; passing classic byte cases does not mark them passed.

Authored source, corpus generators, minimized cases and comparison scripts are
tracked here or under `tests/`. Build products go under `target`; evidence is
saved under `docs/research/assets/regex-engine/`.
