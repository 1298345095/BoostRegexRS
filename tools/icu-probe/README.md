# ICU compatibility research probe

Run from PowerShell 7 on Windows x64 with Visual Studio C++ build tools, `gh`,
Rust stable and Python available:

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
The top-level runner returns 1 for observed mismatches or incomplete reference
coverage. This is distinct from a failed build or malformed comparison input.
Even exit 0 proves only the recorded codepoint fields and finite ordering corpus;
the candidate has no full sort-key output.

The Python comparator requires every expected row and rejects duplicate, missing,
or malformed rows. `ERROR:ACCESS_VIOLATION` reference keys are recorded as
`reference_error`, never a Rust mismatch or a pass. Its regression checks are:

```text
python -B -X utf8 -m unittest discover -s tools/icu-probe -p test_compare_ordering.py
```

See [reference details](reference/README.md) and [Rust candidate details](rust/README.md).

Two follow-up probes preserve the initial corpus and results:

- `pwsh -NoProfile -File tools/icu-probe/reference/run-empty-keys.ps1` reuses the
  reference cache and exports valid-pointer empty-input keys for the approved
  exception in ADR-0005. These are expected values, not a Rust implementation pass.
- `pwsh -NoProfile -File tools/icu-probe/run-non-fcd.ps1` reuses the previously
  built reference and candidate executables with a separate 13-string corpus.
  It records executable hashes. The recorded run has 145 IDENTICAL ordering
  differences out of 1,560 comparisons and returns 1. Full sort-key output is
  still unavailable in the Rust candidate.
