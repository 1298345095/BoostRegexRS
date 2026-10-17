# ICU compatibility research probe

## Cloud Linux: complete root PRIMARY stage

The current stage provides a reproducible official Boost 1.89.0 / ICU4C 77.1
reference and a separate pure Rust **root PRIMARY complete sort-key prototype**.
It fixes Unicode 16.0.0 and CLDR 47, and has been exercised on Ubuntu 24.04
x86-64. From a clean checkout with the prerequisites in the
[cloud instructions](cloud/README.md):

```sh
python3 -B tools/icu-probe/cloud/run.py --jobs 6
```

The default command downloads a verified official Rust stable toolchain into
the project, so a system Rust installation is optional. It also downloads and
builds the official native dependencies, regenerates missing reference data,
replays both submitted corpora, checks deterministic ICU77 data generation,
compares full PRIMARY keys and CE sequences, and runs tests, formatting and lint
checks. There is no historical Windows drive or consumer-checkout dependency.

Results default to `target/research/icu77-cloud/`; the aggregate result is
`cloud-summary.json`. To intentionally refresh the separate small cloud
evidence snapshot:

```sh
python3 -B tools/icu-probe/cloud/run.py --jobs 6 \
  --snapshot docs/research/assets/icu77-cloud
```

The cloud snapshot is distinct from the original Windows evidence under
`docs/research/assets/icu-probe`. The original ICU4X candidate's 145 IDENTICAL
ordering differences and original empty IDENTICAL reference errors remain in
the replay results. The new prototype's PRIMARY success does not establish
IDENTICAL, other locales, the complete regex engine, or release performance.

See the [cloud entry point](cloud/README.md) for prerequisites, exact versions,
result/error semantics, complete output layout, and GitHub Actions configuration;
the [Rust PRIMARY prototype](primary/rust/README.md) and
[fixed-data generator](primary/export/README.md) describe the implementation.

## Historical Windows/MSVC probe

The commands below reproduce the earlier ICU4X candidate investigation on
PowerShell 7 / Windows x64 with Visual Studio C++ build tools, `gh`, Rust stable,
and Python. They remain available separately from the cloud PRIMARY stage.

```powershell
pwsh -NoProfile -File tools/icu-probe/run.ps1 -BoostRoot D:\NewProgram\librime-rs\target\regex-oracle-cache\boost_1_89_0
```

The reference script downloads the official ICU 77.1 archive into local
`target/research/icu-probe/reference`, verifies its published SHA512, and compiles
against the supplied Boost tree. The Rust candidate is a standalone locked Cargo
project. The root crate has no ICU dependency. No consumer sources are modified.

Results and build artifacts remain under `target/research/icu-probe`. Selected
small evidence files from the recorded run are in
`docs/research/assets/icu-probe`; see the [results report](../../docs/research/icu-probe-results.md).
This historical PowerShell runner returns 1 for observed mismatches or incomplete reference
coverage. This is distinct from a failed build or malformed comparison input.
Even exit 0 proves only the recorded codepoint fields and finite ordering corpus;
the candidate has no full sort-key output.

The Python comparator requires every expected row and rejects duplicate, missing,
or malformed rows. `ERROR:ACCESS_VIOLATION` and cloud `ERROR:SIGNAL_N` reference keys are recorded as
`reference_error`, never a Rust mismatch or a pass. Its regression checks are:

```text
python -B -X utf8 -m unittest discover -s tools/icu-probe -p test_compare_ordering.py
```

See [reference details](reference/README.md) and
[historical ICU4X candidate details](rust/README.md).

Two follow-up probes preserve the initial corpus and results:

- `pwsh -NoProfile -File tools/icu-probe/reference/run-empty-keys.ps1` reuses the
  reference cache and exports valid-pointer empty-input keys for the approved
  exception in ADR-0005. These are expected values, not a Rust implementation pass.
- `pwsh -NoProfile -File tools/icu-probe/run-non-fcd.ps1` reuses the previously
  built reference and candidate executables with a separate 13-string corpus.
  It records executable hashes. The recorded run has 145 IDENTICAL ordering
  differences out of 1,560 comparisons and returns 1. Full sort-key output is
  still unavailable in the Rust candidate.
