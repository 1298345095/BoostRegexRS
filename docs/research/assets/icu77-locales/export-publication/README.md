# Fixed ICU77 locale data regeneration

These two Linux x86-64 runs independently regenerated the packaged collation
inventory and verified every published owner, setting and catalog byte. The
reference uses official ICU4C 77.1, Unicode 16.0.0 and CLDR 47 from the
[verified native environment](../../regex-engine/v01-20261017T233138Z/README.md).
The complete ICU data package has SHA-256
`310d9b2cb42947fad7f388b09d2ae574e2adeb60ca76abf280438908f20b2d7b`.

| Observation | First export | Final-source export |
| --- | --- | --- |
| Directory | `2026-10-18-01` | `2026-10-18-02` |
| Driver start, UTC | 2026-10-18 00:44:32 | 2026-10-18 00:51:54 |
| Driver exit | 0 | 0 |
| Recorded deadline | 1,200 seconds | 300 seconds |
| Actual driver duration | 8.014 seconds | 9.206 seconds |
| Archived files | 16 | 16 |
| Archive bytes | 248,000 | 248,152 |
| Archive SHA-256 | `c80b6111f0ddac37f2464d6cf542816d59cd21df008c8102665b364447015836` | `e25c05baee0acf6e0b9025f264c2593c9375816db66d798ece9ecc7d14b4ac85` |

Each run launched two independent inventory processes. Both processes and both
runs produced the same 7,582,825-byte catalog, SHA-256
`946426f0192c2cabda121028e11f9cd2dfacbab4e410eb383eea30442e5bb472`.
The two raw inventory JSON files within each run also have identical hashes.
The generator checked its output against the repository data; it did not replace
the frozen root tables or use the host Unicode database.

## Observed coverage

The inventory contains 881 known ICU locales, 143 collation locales and 173
packaged resource bundles. Its 13,982 requests produced 13,979 loaded results and
three `U_MISSING_RESOURCE_ERROR` rejections. The loaded results include the actual
default and fallback warning statuses. Rejections remain separate from successful
loads.

The fixed data contains 130 owners, including the existing root owner, and 432
deduplicated settings. The 129 added owner tables, settings and script metadata
total 1,869,884 binary bytes. The catalog records all request, resource, owner and
setting identities. These observations establish data generation and identity;
arbitrary-input key compatibility is verified by the separate owner,
configuration and FCD execution suites.

The final source differs from the first export only by removal of one redundant
newline at the end of `inventory_locales.py`. The first run's original source
digest and all raw output are retained. The second run records the final source
digest and repeats both native exports and the checked-in-data comparison.

## Reproduce

First build a fresh pinned reference cache using
[the native reference recipe](../../../../../tools/regex-oracle/README.md).
From the repository root, use new output directories:

```sh
timeout --signal=TERM --kill-after=10s 1200s \
  python3 -B tools/icu-probe/primary/export/inventory_locales.py \
    --cache target/research/regex-reference-fresh \
    --output docs/research/assets/icu77-locales/exports/fresh-check \
    --cxx 'c++ -fuse-ld=bfd' --check

timeout --signal=TERM --kill-after=5s 60s \
  python3 -B tools/icu-probe/primary/archive_evidence.py \
    --verify docs/research/assets/icu77-locales/export-publication/2026-10-18-01
timeout --signal=TERM --kill-after=5s 60s \
  python3 -B tools/icu-probe/primary/archive_evidence.py \
    --verify docs/research/assets/icu77-locales/export-publication/2026-10-18-02
```

Each archive retains the summary, literal driver argv and working directory,
deadline, exit status, separate streams, native build log, resource list and both
raw inventories. The adjacent manifest identifies every member by size and
SHA-256; `verification.json` records an actual full archive verification. Expanded
run directories remain local working evidence, so Git carries one compressed copy
of each execution's raw records.
