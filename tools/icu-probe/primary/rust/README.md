# Pure Rust ICU77 collation prototype

This standalone Cargo package computes complete sort keys from the input and
explicit ICU77 collation data/settings. It uses development-time exports of the
official ICU4C 77.1 root and packaged tailoring data, fixed to Unicode 16.0.0 and
CLDR 47.0. There are no Cargo
dependencies, build scripts, FFI calls, native library links, runtime reference
program calls, or known-input-to-key answer tables. Root collation and canonical
decomposition data are embedded in the CLI; `--data` and `--nfd-data` can select
independently regenerated versions. `--owner` loads a published tailoring against
the same root, and `--settings` supplies its effective settings.

The prototype is isolated from the root crate and does not define the regex
library's public API. The generic path implements published ICU77 CE mechanisms
and all five strengths, numeric collation, on-demand FCD checking, shifted
alternate handling, variable groups, case level/first, backwards secondary and
script reordering. Runtime locale ID parsing, resource fallback and process
default discovery are separate work: the diagnostic catalog's enumerated
request results are not a runtime locale resolver. The CLI accepts explicit
owner/settings files so that these mechanisms can be tested independently.

With no settings file, the default remains root PRIMARY: normalization OFF,
numeric OFF, non-shifted, case level/first OFF, forward secondary, no reordering.
IDENTICAL adds a separate NFD/BOCSU tail after CE iteration. FCD checking, when
enabled explicitly, normalizes only a failing local segment while traversing
the original input. Root-default empty PRIMARY returns `[0]`; empty IDENTICAL
returns ICU bytes `[1, 1, 1, 1, 0]` and Boost elements `[1, 1, 1, 1]`, using the
ADR-0005 valid-pointer exception. Other settings may change the empty key's
selected levels. The exception applies only to a genuinely zero-length input,
and never to a nonempty string of ignorable characters.

## Build and run

Use Rust stable. The cloud run records its exact compiler separately; choosing a
new stable compiler does not update the embedded Unicode data. From the root of
the repository, on a machine with stable installed by rustup:

```sh
export CARGO_TARGET_DIR="$PWD/target/research/icu77-cloud/build/locales-rust"
export CARGO_INCREMENTAL=0
cargo +stable build --locked --release --manifest-path tools/icu-probe/primary/rust/Cargo.toml
cargo +stable test --locked --manifest-path tools/icu-probe/primary/rust/Cargo.toml
cargo +stable fmt --manifest-path tools/icu-probe/primary/rust/Cargo.toml -- --check
cargo +stable clippy --locked --all-targets --manifest-path tools/icu-probe/primary/rust/Cargo.toml -- -D warnings

target/research/icu77-cloud/build/locales-rust/release/icu77-root-primary \
  --data tools/icu-probe/primary/data/root-icu77.bin \
  --strength identical \
  --nfd-data tools/icu-probe/primary/data/root-icu77-nfd.bin \
  < tools/icu-probe/reference/cases.tsv
```

See the [PRIMARY harness](../README.md) for the project-local official dependency
build, data regeneration, oracle comparison, and actual cloud toolchain command.
The fixed table format and source hashes are documented in
[FORMAT.md](../data/FORMAT.md) and [root-icu77.json](../data/root-icu77.json).
The additional NFD export and source identity are recorded in
[root-icu77-nfd.json](../data/root-icu77-nfd.json). The separate owner, settings and
script exports are indexed in [locales/catalog.json](../data/locales/catalog.json).
The source map and binary schemas are in [LOCALE-MECHANISMS.md](LOCALE-MECHANISMS.md).
The tracked project-local
toolchain launcher also accepts these Cargo commands:

```sh
export CARGO_TARGET_DIR="$PWD/target/research/icu77-cloud/build/locales-rust"
export CARGO_INCREMENTAL=0
python3 -B tools/dev/cargo.py test --locked --manifest-path tools/icu-probe/primary/rust/Cargo.toml
```

The fixed cloud compiler is stable 1.99.1; `CARGO_INCREMENTAL=0` and this isolated
target directory avoid reusing artifacts from the previous frozen milestones.
Their original binaries and recorded outputs stay in their original locations.

`RootPrimary::new(Data77)` retains the
original PRIMARY-only library interface and needs only the collation data.
`RootCollator::new(Data77, NfdData77)` provides both `primary_*` and `identical_*`
methods and checks the fixed default root settings before accepting the data.
The generic `Collator77::new(Arc<Data77>, Arc<NfdData77>, Settings77)` exposes
`sort_key_utf8`, `sort_key_u32`, `sort_key_utf16` and the separate raw-ICU
`sort_key_icu_utf16` diagnostic. Shared data is immutable; each collation call
owns its cursor/CE state. `settings_mut()` applies explicit caller changes.

`Settings77` has typed strength, case-first and max-variable controls plus the
other boolean attributes. `ScriptGroups77::make_reordering` computes a requested
script/group sequence from the complete script metadata. Numeric code `103`
alone or an empty list disables reordering; `set_reordering(..., &[-1], defaults)`
restores that tailoring's defaults. Duplicate/equivalent scripts and misplaced
default/others markers return `INVALID_SETTINGS` without replacing the previous
effective settings.

The CLI accepts `--strength primary|secondary|tertiary|quaternary|identical`.
Without an explicit strength, a settings file retains its exported strength;
without a settings file, PRIMARY is the default. For example, the frozen catalog
maps Danish to owner 22 and settings 9:

```sh
target/research/icu77-cloud/build/locales-rust/release/icu77-root-primary \
  --owner tools/icu-probe/primary/data/locales/owner-0022.bin \
  --settings tools/icu-probe/primary/data/locales/settings-0009.bin \
  --strength identical < tools/icu-probe/reference/cases.tsv
```

The stdin/stdout protocol streams one row at a time. Valid input rows produce a
complete key; invalid input and unsupported mappings produce explicit error
rows and processing continues. Failures to load data, malformed TSV structure,
or invalid command-line arguments exit with status 2. Per-row errors do not
change the process status; the comparison harness determines their outcome.

Input defaults to `case_id<TAB>utf8_hex`, with continuous hexadecimal bytes and an
optional first header row. Empty hex is an empty string and `00` is an embedded
NUL. Output always has this header:

```text
case_id	raw_icu_hex	boost_u32_hex
```

Both output sequences use commas: `raw_icu_hex` contains two-digit bytes including
the final `00`; `boost_u32_hex` contains eight-digit u32 values. Every byte is
promoted to one u32. A final terminator is removed only when the raw key has more
than one byte, so `[00]` stays `[00000000]`.

## Input domains

| Option / library method | Accepted input | Rejection or special scope |
|---|---|---|
| default / `sort_key_utf8` | Valid UTF-8, with NUL and original combining-mark order | CLI reports `ERROR:INVALID_UTF8` for invalid byte encoding |
| `--input-format u32` / `sort_key_u32` | Comma-separated eight-digit Unicode scalar values | `ERROR:INVALID_UTF32` for a surrogate or a value above U+10FFFF, matching Boost's checked conversion |
| `--input-format u16` / `sort_key_utf16` | Comma-separated four-digit UTF-16 units with paired surrogates | `ERROR:INVALID_UTF16` for an unpaired unit; this is the checked UTF-16 adapter used by the Boost oracle |
| `--input-format u16 --icu-utf16-only` / `sort_key_icu_utf16` | Arbitrary UTF-16 units | Separate raw ICU input diagnostic; unpaired surrogates keep their original values and are never changed to U+FFFD |

For u32/u16, the header's second column is `u32_hex`/`u16_hex`. Malformed hex has
a separate `ERROR:INVALID_*_HEX` code. A reached CE32 tag outside implemented
runtime semantics reports `ERROR:UNSUPPORTED_CE32`; incompatible or damaged data
reports `ERROR:DATA_ERROR`. These are not compatible keys or passing cases.
Root wrapper methods retain their corresponding `primary_*`/`identical_*`
names and the same checked input domains.

The explicit raw ICU UTF-16 diagnostic is not a Boost adapter compatibility
claim. Its second output column still applies the byte-to-u32 convention, but
the original Boost checked input path rejects unpaired surrogates before it
reaches the collator. Keep that diagnostic output separate from Boost results.

## Implementation

`data77.rs` validates and reads the versioned, little-endian data export. It
performs range lookup for CE32 and FCD16, indexes full CE32/CE64 expansion tables,
and constructs context tries from every exported UCharsTrie entry. It also loads
the Jamo mappings and the full 256-entry primary compressibility table. A
tailoring's CE32 indexes always refer to that owner, including Jamo arrays which
ICU may physically share with root. A fallback switches to root before expanding
the resulting CE32. FCD16 remains shared with root for every packaged owner.

`ce77.rs` follows the ordinary forward ICU77 iterator. It supports simple CEs,
long primary/secondary CEs, Latin expansions, CE32/CE64 expansions, prefixes,
longest contractions, discontiguous contractions, the skipped-mark buffer,
decimal digit mappings, explicit-length NUL input, Hangul, offset primaries,
and implicit weights. Valid supplementary pairs are decoded before lookup. The
full CE64 sequence is retained before encoding the requested strength. The code keeps the
end-of-input CE distinct from primary ignorables and U+FFFE's merge separator.

Decoded code-point storage and trie node IDs replace ICU's UTF-16 pointers and
packed UCharsTrie state. Fast FCD guards still inspect the original UTF-16
units, including conservative lead-surrogate flags and trail-surrogate flags.
Discontiguous matching replays the accepted suffix through the real cursor,
because changing direction can change a local FCD segment; a cached trie node
alone is insufficient. The separate skipped-mark cursor retains
the source behavior of emitting a contraction before its skipped combining
marks and allowing those marks to participate in later matching. Prefix lookup
continues to use the real input cursor, as in the original iterator.
`numeric77.rs` implements decimal run collection, leading-zero handling, all
dense small-number forms, 254-digit segmentation and the large-number pair
encoding. `cursor77.rs` implements both directions of the FCD iterator, including
segment boundaries, local normalized buffers and prefix direction changes.

`key77.rs` ports the default-root portions of ICU77's writer. PRIMARY tests the exported
compressibility flag before omitting repeated lead bytes, emits `03` or `ff` on
the relevant transitions, and observes the special merge/end boundaries.
Completing a compressed primary run at end of input does not append an extra
compression terminator. For IDENTICAL, the writer also encodes the forward
SECONDARY level, TERTIARY with the default case-bit mask, and the non-shifted
QUATERNARY level. It compresses common weights in runs of 33, 97, and 113,
respectively, and preserves the sentinel and merge-separator rules on each level.
Default root has no separate CASE level. `boost_key` applies Boost's return
convention after every requested level has been written.

`levels77.rs` implements the complete settings-dependent writer used by
`Collator77`. It adds backwards-secondary segment reversal, separate case levels,
all tertiary case masks/weight transformations, shifted primary/quaternary
handling and script reordering. `settings77.rs` reads the effective options and
ports the full ICU77 script range allocation and split-byte reordering algorithm.
The earlier root writer remains available to its original wrapper APIs and tests.

`nfd77.rs` reads the separate BRSNFD77 export: all recursive canonical mappings
(including Hangul) and canonical combining classes from the fixed Unicode16
data. It expands mappings and stably reorders nonstarters between starters.
For default root this happens only for the IDENTICAL tail, after CE iteration.
The optional FCD cursor uses the same fixed mappings for a failing local segment.
Compatibility decompositions are excluded. `bocsu77.rs` then performs ICU's
signed difference encoding, script/Han recentering, and U+FFFE reset. Its negative
division uses Rust's Euclidean quotient/remainder to match ICU's `NEGDIVMOD`.

The library APIs take a `trace` boolean. `--trace` writes a JSON object for each
row to stderr, including CE64 values, the sentinel, CE32 branches, contraction
events, full ICU bytes, and Boost elements. IDENTICAL traces additionally include
`nfd_u32_hex`, the exact canonical sequence passed to BOCSU; PRIMARY records it
as `null`; the intermediate strengths also have no IDENTICAL tail. Normal TSV stdout is unchanged.
`input_position_cp` in these events is the internal real-input cursor after
lookup/matching, not a regex match position. No trace vectors are allocated when
tracing is disabled.

```sh
printf 'case_id\tutf8_hex\nnonfcd\t61cc95cc80\n' | \
  target/research/icu77-cloud/build/locales-rust/release/icu77-root-primary \
    --strength identical --trace
```

## Verification boundaries

The Rust regression tests include source-checked byte sequences for both
compression directions, merge termination, prefix selection, blocked and
unblocked Cyrillic contractions, and the skipped CE order. A CE trace regression
for `a + U+0315 + U+0300` prevents accidental pre-NFD even though its PRIMARY key
alone would not reveal that change. Tests also cover empty/NUL/ignorable input,
Hangul/Jamo, expansions, Han, supplementary encoding, exact invalid-input
positions, the 99/100/101-byte Boost buffer boundary, longer keys, incompatible
data, and a standalone executable with the environment cleared.

The IDENTICAL regressions add 167 complete oracle fixtures covering secondary
and tertiary compression boundaries, positive and negative BOCSU length
transitions, Han recentering, merge resets, and non-FCD input. Additional tests
check the approved empty key, embedded NUL, recursive and stable canonical
decomposition, Hangul, preservation of compatibility characters, input positions,
data versions/settings, and unchanged PRIMARY results. The fixture refresh tool
uses only the fixed development oracle and writes the checked-in test file:

```sh
python3 -B tools/icu-probe/primary/rust/tests/refresh_identical_fixtures.py
```

Locale mechanism tests additionally load every published owner, recompute every
exported reorder table and split range from its public script codes, verify
default resets and equivalent-script errors, and retain the original root key
fixtures under the generic writer. The independent source-defined input generator
is separate from every key implementation:

```sh
python3 -B tools/icu-probe/primary/rust/tests/locale_cases.py \
  --output docs/research/assets/icu77-locales/mechanism-cases
```

It supplies 1,019 directed inputs, 512 generated inputs with seed
`0x0042494355373701`, all 384 finite attribute combinations and 10 additional
reorder configurations. It uses neither a host Unicode database nor reference
keys to choose inputs. The full locale harness compares complete raw ICU bytes
and Boost u32 sequences and retains each configuration's effective reference
metadata. Its result report records actual tested counts and remaining gaps.

`tests/locale_fixtures.rs` replays 938 complete native fixtures selected from the
fully passed 538-configuration, two-strength, three-input-width run. The selected
244 owner/settings/strength groups cover the source-defined setting interactions;
they supplement the complete matrix rather than replace it. Both `Collator77`
and the CLI with explicit root, owner and settings files must reproduce every
raw ICU byte and Boost element. The CLI test clears its environment and keeps
long input/output streams flowing concurrently. Fixture provenance is recorded
in `tests/data/locales-v2.json`; the extractor uses only independent native
`expected-keys.tsv` rows, never candidate output. The wrapping-order regression
also checks all five strengths and rejects corrupted imported tables/ranges.

The external harness supplies the decisive full-key oracle checks: the existing
corpora, directed context and compression cases, generated cases with fixed
randomness, and all Unicode scalar single-character inputs. Counts and hashes
belong to its result reports; the presence of a Rust test or a matching sort
order alone does not establish complete key compatibility. `run_identical.py`
keeps original empty-input reference failures separate from the approved
exception expectations. Historical ICU4X comparisons remain historical evidence;
the new Rust implementation is checked using its own full-key output.

The current implementation buffers the input code points and complete CEs, and
builds a lookup representation when loading data. It has no performance or
memory acceptance claim. Locale ID parsing/resource fallback, custom rule
tailoring, process default locale discovery, full regex behavior and the
six-platform release gates have separate acceptance work. Finite differential
coverage does not prove the algorithm for every possible input string.
