# ICU77 explicit-settings reference tools

These Linux development tools compare the pure Rust `Settings77` and complete
key writers with the fixed official ICU4C 77.1 reference. The native processes
are development references, never a Rust runtime backend. See the
[C correction and actual results](../../../../docs/research/assets/icu77-locales/settings-acceptance/reorder-publication-c-v1-20261018/README.md)
and the [owner/configuration suites](../../../../docs/research/assets/icu77-locales/acceptance-publication/2026-10-18-v1/README.md).

## Build and execute

Prepare the project-local official source/cache and Rust stable toolchain using
the [cloud reference instructions](../../cloud/README.md). `--cache` below is
the verified reference cache containing `install/icu` and `source-manifests`;
`--rust-cache` defaults to `target/research/icu77-cloud`. The native source and
static libraries must be the fixed Boost 1.89.0/ICU77.1 build. Unicode 16.0 and
CLDR 47 data do not follow the host's Unicode version.

Each output directory and its basename must be new; the build keeps a separate
Cargo target named after that basename. The commands record actual versions,
file digests, full output streams, per-process deadlines and terminal statuses.
Choose a different suffix for a subsequent run:

```sh
export ICU_REFERENCE_CACHE="$PWD/target/research/icu77-cloud"
export ICU_REORDER_RESULTS="$PWD/docs/research/assets/icu77-locales/settings-acceptance"
timeout --signal=TERM --kill-after=10s 600s python3 -B tools/icu-probe/primary/settings-probe/build.py \
  --cache "$ICU_REFERENCE_CACHE" --check-library \
  --output "$ICU_REORDER_RESULTS/build-reproduction-01"
timeout --signal=TERM --kill-after=10s 600s python3 -B tools/icu-probe/primary/settings-probe/run.py \
  --build "$ICU_REORDER_RESULTS/build-reproduction-01/summary.json" \
  --mode reorder --profile root \
  --output "$ICU_REORDER_RESULTS/root-reproduction-01"
timeout --signal=TERM --kill-after=5s 300s python3 -B tools/icu-probe/primary/settings-probe/diagnose_boost_reorder.py \
  --cache "$ICU_REFERENCE_CACHE" \
  --build "$ICU_REORDER_RESULTS/build-reproduction-01/summary.json" \
  --root-run "$ICU_REORDER_RESULTS/root-reproduction-01" \
  --output "$ICU_REORDER_RESULTS/boost-reorder-reproduction-01"
timeout --signal=TERM --kill-after=5s 180s python3 -B tools/icu-probe/primary/settings-probe/diagnose_boost_reset.py \
  --cache "$ICU_REFERENCE_CACHE" \
  --output "$ICU_REORDER_RESULTS/boost-reset-reproduction-01"
```

`run.py --mode reorder` generates all declared singleton and ordered code pairs,
outside-code boundaries, source controls and fixed-seed long orders. It compares
native setter status, prior PRIMARY/IDENTICAL keys and all five resulting
strengths, including failed-setter state preservation. `--smoke` is an explicit
diagnostic subset and is never a full acceptance result. The `am` profile also
exercises the original native DEFAULT ownership/destructor failure; that
reference error remains separately retained and is not a passing Boost case.

`run.py --mode intermediate --configurations-run DIRECTORY --candidate CLI
--candidate-provenance SUMMARY` reuses a completed configuration inventory and
compares SECONDARY, TERTIARY and QUATERNARY to direct ICU keys. The full recorded
538-configuration command and inputs are in the owner/configuration report.
Boost exposes PRIMARY and IDENTICAL through its two transform methods; these
intermediate strength checks are direct ICU diagnostics.

## Source and evidence roles

| Tool | Purpose |
| --- | --- |
| `reference.cpp`, `src/main.rs` | Independent native and pure Rust TSV processes; complete keys and setter state |
| `cases.py` | Pinned script-derived input generation; no reference keys used to choose inputs |
| `reduce_reorder.py`, `inspect_reorder.py`, `inspect-reorder.cpp` | Retain reductions and exact native table/range fields |
| `diagnose_boost_reorder.py`, `boost-reorder-keys.cpp` | Verify public Boost locale reachability and real u32 vectors for every internal-NUL observation |
| `diagnose_default_reset.py`, `default-reset.cpp` | Preserve the direct ICU DEFAULT crash with ordinary destruction |
| `diagnose_boost_reset.py`, `boost-locale-reset.cpp` | Check the actual public Boost `imbue` lifecycle independently |
| `verify_reorder_run.py` | Compare already emitted historical C rows after retaining the original harness abort; no native or candidate rerun |
| `import_regression.py` | Import native reduced settings and complete keys into Rust fixtures |
| `retain_failure.py`, `retain_diagnostic.py`, `package_evidence.py` | Retain actual executables, sources and unchanged complete raw records using the shared archive verifier |

The streams preserve embedded NUL bytes as hexadecimal, including a NUL before
the final terminator. Input IDs, full lengths, statuses and every key element
remain comparison fields. No whole-input normalization, input-answer table or
string-terminator shortcut is used to claim compatibility.
