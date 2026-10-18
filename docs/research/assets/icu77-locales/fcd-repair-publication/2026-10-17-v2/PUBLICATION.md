# Publication boundaries

These groups describe build dependencies and review boundaries. Git staging,
commit identifiers and exact staged-snapshot validation are owned by the parent
implementation task. The U01 research tests do not establish complete locale or
regex acceptance.

| Group | Required contents | Dependency and evidence |
| --- | --- | --- |
| A: cursor/data prerequisite | `rust/src/{data77,cursor77,ce77,numeric77}.rs`, the A root-only `lib.rs` wiring, six historical input/cursor fixtures and full flag bitmap | Independent tree `ebc3cedc41a75fac73f805e0d99d38570433c8dd`; 21 tests, format and Clippy pass |
| Fixed locale data | `data/locales/scripts.bin`, all 129 `owner-*.bin`, all 432 `settings-*.bin`, schemas/provenance and the corresponding inventory/export tooling | 1,869,884 binary bytes total. Generic library compiles against this fixed data; `catalog.json` is regeneration/provenance metadata, not a Rust runtime parser dependency |
| B: generic settings/writer | `rust/src/{settings77,levels77}.rs`, generic `lib.rs` and `main.rs`, `tests/locale_mechanisms.rs`, `README.md`, `NOTICE.md`, `LOCALE-MECHANISMS.md` | Depends on A plus fixed locale data. P2 tests also require settings 0002, 0406 and 0422, already in the complete setting set |
| B: full FCD regression | `tests/fcd_replay.rs`; `tests/data/fcd77/{inputs-u16.tsv,native-cursor.tsv,native-flags.bin,native-keys-ces.tsv,provenance.json}` | Depends on generic `Collator77`, settings 0001 and owner 0043. Replaces the A historical-only working fixture subset. Complete working suite: 31 tests |
| Reproduction tools | `tests/{refresh_fcd_fixtures,verify_fcd_repair,record_fcd_environments,package_fcd_evidence}.py`; native trace/oracle sources and existing shared modules listed below | All authored sources must be published; transient build directories contain downloaded tools and compiled outputs only |
| Execution evidence | This directory's `raw.tar.xz`, `manifest.json`, `summary.json`, `verification.json` and documentation | One compressed copy of all new raw evidence. Leave expanded `docs/research/assets/icu77-locales/fcd-repair/` execution directories unstaged |

Paths in the table without a repository prefix are relative to
`tools/icu-probe/primary/`. The existing root data and NFD binaries remain
required throughout. Individual binary data identities are in the executed
Rust summary inside the archive.

## Reproduction tool dependencies

- `refresh_fcd_fixtures.py` imports `export/data_format.py` and
  `export/generate.py`. Its native mode builds `export/trace-fcd.cpp`,
  `export/trace-locale.cpp` and `oracle.cpp` against the fixed development
  environment. Historical-only extraction uses no compiler or native cache.
- `verify_fcd_repair.py` additionally uses `compare.py`,
  `tools/icu-probe/cloud/rust_toolchain.py`, `prepare.py` and the checked-in
  compiler/doc launchers. It requires the five retained native history files
  below and full frozen FCD fixtures.
- The environment recorder and packager import the same fixture helper. The
  packager delegates deterministic compression and per-file verification to
  `primary/archive_evidence.py` and references the existing checkpoint metadata.
- `extract_locale_fixtures.py` and `locale_cases.py` are further locale research
  tooling. They are not compile or execution dependencies of this completed
  U01 regression; a completed passing locale sweep is still required before
  that extractor can publish its planned golden fixture set.

## Retained historical inputs

The generator needs both
`diagnostics/fo-search-fcd-cursor/input-u16.tsv` and
`diagnostics/fo-search-fcd-reduced/input-u16.tsv`. The verifier additionally
reads these five original native files, relative to
`docs/research/assets/icu77-locales/`:

- `diagnostics/fo-search-fcd-22721fc2/expected-keys.tsv`
- `diagnostics/fo-search-fcd-22721fc2/native-ces.tsv`
- `diagnostics/fo-search-fcd-cursor/native-fcd.tsv`
- `diagnostics/fo-search-fcd-reduced/native-fcd.tsv`
- `diagnostics/fcd-unit-flags/native-fcd-flags.bin`

Their checkpoint copies and original identities must remain available. The old
failed run already has one complete checkpoint archive and should not be
published again as thousands of expanded files.

## Large files

`native-keys-ces.tsv` is 4,245,313 bytes and `data/locales/catalog.json` is
7,582,825 bytes. They exceed the checkpoint's earlier 2 MiB transport chunk
size. Publication must preserve the exact tested bytes and supply any required
reassembly before tests or generation run; dropping either file silently is not
a reproducible publication. The full key fixture is a direct compile-time test
dependency. Any transport-driven fixture format change requires corresponding
harness updates and fresh applicable validation.

The compact raw evidence archive is only 530,072 bytes and needs no splitting.
