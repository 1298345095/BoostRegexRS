# Fixed ICU77 root-data generation

This is a development-only C++/Python toolchain. The Rust prototype reads the
checked-in `../data/root-icu77.bin` and does not load ICU, launch these programs,
or require a C++ compiler.

## Reproduce

From the repository root on the cloud Linux environment, first prepare the
official release dependencies using the cloud entry point described in
`../../cloud/README.md`. It installs the full, unfiltered ICU4C 77.1 release
data in `target/research/icu77-cloud/install/icu`; no historical Windows path is
used by this generator. Then run:

```sh
python3 -B tools/icu-probe/primary/export/generate.py
python3 -B tools/icu-probe/primary/export/generate.py --check
```

`--cache DIR` selects a different project-local prepared environment;
`--output-directory DIR` selects a generated-data destination. The default
destination is the tracked `tools/icu-probe/primary/data` directory. `--check`
compiles and generates into the cache, compares the output with the existing
data and checks the preserved ICU license, and never replaces the tracked
output. A mismatch or missing prerequisite returns a nonzero exit code.

Each invocation performs the following checks:

1. Independently hashes the official source archive and compares its SHA-512
   with both the pinned digest and the downloaded official checksum manifest.
2. Compares all listed algorithm/data source files with their exact bytes in
   that verified archive, including the complete `icudt77l.dat`.
3. Checks the installed ICU library hashes against the prepared environment
   manifest. The runtime environment points to those libraries and does not
   inherit an `ICU_DATA` override.
4. Compiles `export-root.cpp` and `trace-root.cpp` with C++17, optimization,
   `-Wall -Wextra -Werror`, and the same fixed private/public ICU headers.
5. Runs two separate exporter processes, requiring byte-identical data and
   runtime metadata. Both processes verify ICU 77.1, Unicode 16.0.0, CLDR 47,
   ICU data 77.1, root locale identity, and root PRIMARY options.
6. Parses the generated binary independently in Python, checking ranges,
   versions, lengths, raw/decoded context defaults, and exact end-of-file.

The generator records the source URLs and digests, source-file SHA-256 values,
generator identities, compiler, installed-library hashes, table counts,
effective public attributes, and output SHA-256 in `../data/root-icu77.json`.
Build logs, both independent outputs, a generation manifest, and a readable
context report remain in `target/research/icu77-cloud/build/primary-export/`.
The generator does not query sort keys or consume the regression corpus.

## Format and actual exported data

See [the binary schema](../data/FORMAT.md) and [source/license notice](../data/NOTICE.md).
The initial official Linux build generates 751,804 bytes, with SHA-256
`7aefc773d90fc2006c236720cd4e9220720efb33c7b8274ffeb24b494de3034e`.

| Section | Elements |
| --- | ---: |
| CE32 ranges covering U+0000 through U+10FFFF | 85,290 |
| Original CE32 table | 6,145 |
| Original 64-bit CE table | 2,023 |
| Raw context UTF-16 units | 4,603 |
| Jamo CE32s | 67 |
| Primary-compression flags | 256 |
| FCD16 ranges covering the complete code-point domain | 1,036 |
| Decoded context tries | 77 |
| Decoded context entries | 1,147 |

The real root PRIMARY options word is `0x10`; variable top is `0x0bffffff`
and numeric primary is `0x10000000`. Normalization, numeric collation, case
level, case first, and French secondary are OFF; alternate handling is
non-ignorable; reordering is empty. Strength alone is changed to PRIMARY.

To regenerate the readable context report without ICU:

```sh
python3 -B tools/icu-probe/primary/export/data_format.py \
  tools/icu-probe/primary/data/root-icu77.bin \
  --contexts-output target/research/icu77-cloud/build/root-contexts.json
```

This JSON includes every root prefix/contraction trigger code point, its
original CE32 tag and flags, every default CE32, and the exact UTF-16 plus
decoded code-point sequences in each context entry. Prefix keys are in the
trie's original reverse-code-point order. Entries can refer to nested
contexts. The report is for data-derived coverage and diagnostics; it contains
no reference keys for test inputs.

## 64-bit collation-element diagnostic

```sh
LD_LIBRARY_PATH="$PWD/target/research/icu77-cloud/install/icu/lib" \
  target/research/icu77-cloud/build/primary-export/trace-root \
  --utf16 0061,0315,0300
```

The input is a comma-separated list of one-to-four-digit hexadecimal UTF-16
units. `--utf16 ''` represents an empty sequence, and `0000` is an actual NUL
unit. The explicit length is retained. Valid surrogate pairs are decoded by
ICU; lone surrogate units are preserved for direct ICU diagnostics. This tool
does not claim that arbitrary UTF-16 has passed Boost's separate UTF-32 input
conversion contract.

The JSON output includes each decoded code point's original CE32/FCD16 lookup
and every complete 64-bit CE from the ordinary `UTF16CollationIterator`, with
the corresponding primary weight and UTF-16 offset after iteration. Expansion
or contraction CEs may share an offset. The final no-CE sentinel is explicitly
marked and retained. This is the root normalization-OFF, numeric-OFF path used
for the prototype, with no uniform decomposition of the input. The trace is a
diagnostic reference, not an input to Rust key generation.

`trace-root --batch-utf16` accepts `case_id<TAB>u16_hex` rows on stdin and emits
`case_id<TAB>ces64_hex`, including the sentinel in each sequence. The independent
finite-corpus CE audit uses this mode alongside Rust's `--trace` output:

```sh
python3 -B tools/icu-probe/primary/export/compare_ce_traces.py \
  --cases target/research/icu77-cloud/primary/cases/contexts.tsv \
  --candidate target/research/icu77-cloud/build/primary/release/icu77-root-primary \
  --output-directory target/research/icu77-cloud/primary/ce-audit-contexts
```

The audit compares complete CE64 sequences, including primary-ignorable CEs and
the end sentinel. It reports missing/duplicate/malformed evidence as errors;
candidate failures are separate from differences and passes. Input, reference
CEs, candidate keys and traces, executable/data identities, and summary remain
in the output directory. This diagnostic helps catch context-iteration mistakes
that PRIMARY alone could hide; it does not implement or accept IDENTICAL keys.
