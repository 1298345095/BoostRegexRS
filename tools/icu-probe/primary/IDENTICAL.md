# Fixed ICU77 root IDENTICAL differential suite

The independent root IDENTICAL implementation uses the existing full CE data
and an additional fixed Unicode 16 NFD table. Its CE iterator consumes the
original input with root normalization OFF. The subsequent secondary/tertiary/
quaternary output and final NFD/BOCSU level follow ICU4C 77.1. The CLI adds
`--strength identical`; its default remains PRIMARY.

## Reproduce

From a clean checkout with the native prerequisites described in
[cloud/README.md](../cloud/README.md):

```sh
python3 -B tools/icu-probe/cloud/prepare.py --jobs 6
python3 -B tools/icu-probe/primary/export/generate.py --check
python3 -B tools/icu-probe/primary/export/generate_nfd.py --check
python3 -B tools/icu-probe/primary/run_identical.py
```

The runner uses the project-local recorded official stable compiler by default;
`--system-rust` selects an already installed stable. `--cache DIRECTORY` selects
prepared native dependencies, `--output DIRECTORY` selects independent evidence,
and `--candidate PATH --skip-build` reuses explicitly identified binaries for
diagnosis. `--skip-all-scalars` labels the resulting coverage as a shorter
diagnostic. The default generated count is 20,000 with fixed SplitMix64 seed
`0x0042494355373701`.

The native and Rust executables are built under `CACHE/build/identical/`. New
keys, inputs, settings, per-row expectation origins and process evidence default
to a fresh dated directory under `docs/research/assets/icu77-identical/runs/`.
`--output` can explicitly choose another location. The original PRIMARY directory
is preserved. Source and executable SHA256 values identify each run. Native tools
are development-only; the Rust candidate runs without an ICU library path and
with absent ICU data.

Archive a completed raw run for version control without changing its files:

```sh
python3 -B tools/icu-probe/primary/archive_evidence.py \
  --source RUN_DIRECTORY --output NEW_ARCHIVE_DIRECTORY
python3 -B tools/icu-probe/primary/archive_evidence.py \
  --verify NEW_ARCHIVE_DIRECTORY
```

The archive contains every raw file. Its manifest records each file's SHA256 and
byte count; creation also decompresses and checks every archived file. The first
recorded IDENTICAL run remains at `target/research/icu77-cloud/identical/` and is
preserved in full by the checked-in compressed archive linked in
[the result report](../../../docs/research/root-identical-results.md).

## Original compatibility and the approved empty exception

`oracle.cpp --strength identical` calls the unmodified Boost traits. The runner
first executes empty UTF-8, checked UTF-16 and checked UTF-32 inputs through
that original path and preserves their real signal/error/return records under
`original-empty/`.

For the suite's expected keys, `--approved-empty-exception` changes only empty
IDENTICAL input: it obtains ICU bytes from a valid sentinel address with length
zero and applies Boost's documented byte-per-u32 convention. These rows are
labelled `adr0005_valid_pointer_empty` in `expectation-origins.tsv`; other valid
rows call the actual Boost `transform` and are labelled `original_boost_call`.
The output file is named `expected-keys.tsv` to make this mixed expectation
source explicit. The original failures are never rewritten.

The strict comparator compares both complete raw ICU bytes and every Boost u32
element. `passed` counts original nonempty key agreement;
`approved_exception_passed` counts successful ADR-0005 empty expectations;
`rejected_as_expected` counts invalid input rejection. Differences, unsupported
input, reference errors, missing/reordered rows and malformed oracle keys cannot
become passes. Counts describe records; repeated strings can appear in multiple
groups. Adjacent ICU ordering is a supplementary check.

## Coverage

The suite includes the original 24 inputs and 13 non-FCD inputs, all existing
directed/long/Hangul inputs, all exported context entries and interruption
variants, fixed-seed generated strings, checked UTF-16/UTF-32 boundaries, and
all Unicode scalar single-character inputs. Additional directed inputs exercise
secondary common-run count 33, tertiary common-run count 97, BOCSU positive and
negative 1/2/3/4-byte transitions, U+FFFE merge resets and recursive canonical
decomposition. These boundaries derive from fixed `collationkeys.h` and
`bocsu.h`, not from inferred sample-key patterns.

The main result is `RUN_DIRECTORY/summary.json`. A full suite requires
`status: passed_for_recorded_inputs`, `coverage_profile: full_recorded_suite`
and no `groups_not_run`. Each group retains its exact inputs, original/candidate
outputs, source identities and process records. This suite evaluates root
IDENTICAL; other locale data/settings and the regex library's full acceptance
are verified separately.

The recorded full run passed 1,159,652 original nonempty keys, 696 approved empty
expectations, and 11 expected invalid-input rejections. Its three original empty
Boost calls each terminated with SIGSEGV and are separate reference errors. The
historical non-FCD comparison is derived without another execution:

```sh
python3 -B tools/icu-probe/primary/historical_identical.py \
  --run-directory RUN_DIRECTORY --output NEW_DERIVED_DIRECTORY
```

For the independent 2,048-input PRIMARY context review, the portable input
generator preserves the exact seed and random-call order:

```sh
python3 -B tools/icu-probe/primary/generate_review_contexts.py \
  --contexts CONTEXT_REPORT.json --output NEW_INPUT_DIRECTORY
```

It regenerates both UTF-8 and UTF-16 inputs byte-for-byte. The archived original
review script, binaries' identities, complete keys and CE traces remain separate
historical evidence; regenerating its inputs adds no acceptance records to the
main PRIMARY or IDENTICAL suites.
