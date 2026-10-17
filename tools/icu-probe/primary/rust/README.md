# Pure Rust ICU77 root PRIMARY prototype

This standalone Cargo package computes the complete root PRIMARY sort key from
the input. It uses the full development-time export of official ICU4C 77.1 root
collation data, fixed to Unicode 16.0.0 and CLDR 47.0. There are no Cargo
dependencies, build scripts, FFI calls, native library links, runtime reference
program calls, or known-input-to-key answer tables. The checked-in data file is
embedded in the CLI executable; `--data` can select an independently regenerated
copy for reproducibility checks.

The prototype is isolated from the root crate and does not define the regex
library's public API. Its scope is root PRIMARY with the actual default root
settings: normalization OFF, numeric OFF, non-shifted alternate handling, case
level OFF, and no reordering. It does not implement IDENTICAL or other locales.
It does not change `getloc`, the default-locale contract, or the empty IDENTICAL
exception in ADR-0005. An empty PRIMARY key remains the single zero element.

## Build and run

Use Rust stable. The cloud run records its exact compiler separately; choosing a
new stable compiler does not update the embedded Unicode data. From the root of
the repository, on a machine with stable installed by rustup:

```sh
export CARGO_TARGET_DIR="$PWD/target/research/icu77-cloud/build/primary"
cargo +stable build --locked --release --manifest-path tools/icu-probe/primary/rust/Cargo.toml
cargo +stable test --locked --manifest-path tools/icu-probe/primary/rust/Cargo.toml
cargo +stable fmt --manifest-path tools/icu-probe/primary/rust/Cargo.toml -- --check
cargo +stable clippy --locked --all-targets --manifest-path tools/icu-probe/primary/rust/Cargo.toml -- -D warnings

target/research/icu77-cloud/build/primary/release/icu77-root-primary \
  --data tools/icu-probe/primary/data/root-icu77.bin \
  < tools/icu-probe/reference/cases.tsv
```

See the [PRIMARY harness](../README.md) for the project-local official dependency
build, data regeneration, oracle comparison, and actual cloud toolchain command.
The fixed table format and source hashes are documented in
[FORMAT.md](../data/FORMAT.md) and [root-icu77.json](../data/root-icu77.json).

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
| default / `primary_utf8` | Valid UTF-8, with NUL and original combining-mark order | CLI reports `ERROR:INVALID_UTF8` for invalid byte encoding |
| `--input-format u32` / `primary_u32` | Comma-separated eight-digit Unicode scalar values | `ERROR:INVALID_UTF32` for a surrogate or a value above U+10FFFF, matching Boost's checked conversion |
| `--input-format u16` / `primary_utf16` | Comma-separated four-digit UTF-16 units with paired surrogates | `ERROR:INVALID_UTF16` for an unpaired unit; this is the checked UTF-16 adapter used by the Boost oracle |
| `--input-format u16 --icu-utf16-only` / `primary_icu_utf16` | Arbitrary UTF-16 units | Separate raw ICU input diagnostic; unpaired surrogates keep their original values and are never changed to U+FFFD |

For u32/u16, the header's second column is `u32_hex`/`u16_hex`. Malformed hex has
a separate `ERROR:INVALID_*_HEX` code. A reached CE32 tag outside implemented
runtime semantics reports `ERROR:UNSUPPORTED_CE32`; incompatible or damaged data
reports `ERROR:DATA_ERROR`. These are not compatible keys or passing cases.

The explicit raw ICU UTF-16 diagnostic is not a Boost adapter compatibility
claim. Its second output column still applies the byte-to-u32 convention, but
the original Boost checked input path rejects unpaired surrogates before it
reaches the collator. Keep that diagnostic output separate from Boost results.

## Implementation

`data77.rs` validates and reads the versioned, little-endian data export. It
performs range lookup for CE32 and FCD16, indexes full CE32/CE64 expansion tables,
and constructs context tries from every exported UCharsTrie entry. It also loads
the Jamo mappings and the full 256-entry primary compressibility table. FCD16 is
used for contraction blocking; it does not normalize or rewrite input.

`ce77.rs` follows the ordinary forward ICU77 iterator. It supports simple CEs,
long primary/secondary CEs, Latin expansions, CE32/CE64 expansions, prefixes,
longest contractions, discontiguous contractions, the skipped-mark buffer,
numeric-OFF digit mappings, explicit-length NUL input, Hangul, offset primaries,
and implicit weights. Valid supplementary pairs are decoded before lookup. The
full CE64 sequence is retained before PRIMARY encoding. The code keeps the
end-of-input CE distinct from primary ignorables and U+FFFE's merge separator.

Decoded code-point cursors and trie node IDs replace ICU's UTF-16 pointer and
packed UCharsTrie state. In particular, the last accepted context node replaces
ICU's replay of the accepted suffix. The separate skipped-mark cursor retains
the source behavior of emitting a contraction before its skipped combining
marks and allowing those marks to participate in later matching. Prefix lookup
continues to use the real input cursor, as in the original iterator.

`key77.rs` ports the PRIMARY portion of ICU77's writer. It tests the exported
compressibility flag before omitting repeated lead bytes, emits `03` or `ff` on
the relevant transitions, and observes the special merge/end boundaries.
Completing a compressed primary run at end of input does not append an extra
compression terminator. `boost_key` then applies Boost's return convention.

The library APIs take a `trace` boolean. `--trace` writes a JSON object for each
row to stderr, including CE64 values, the sentinel, CE32 branches, contraction
events, full ICU bytes, and Boost elements. Normal TSV stdout is unchanged.
`input_position_cp` in these events is the internal real-input cursor after
lookup/matching, not a regex match position. No trace vectors are allocated when
tracing is disabled.

```sh
printf 'case_id\tutf8_hex\nnonfcd\t61cc95cc80\n' | \
  target/research/icu77-cloud/build/primary/release/icu77-root-primary --trace
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

The external harness supplies the decisive full-key oracle checks: the existing
corpora, directed context and compression cases, generated cases with fixed
randomness, and all Unicode scalar single-character inputs. Counts and hashes
belong to its result reports; the presence of a Rust test or a matching sort
order alone does not establish complete key compatibility. The historical 145
IDENTICAL ordering differences remain a later-stage regression target.

The current implementation buffers the input code points and complete CEs, and
builds a lookup representation when loading data. It has no performance or
memory acceptance claim. IDENTICAL, FCD normalization ON, numeric collation,
other locale data/settings, full regex behavior, and the six-platform release
gates remain future work.
