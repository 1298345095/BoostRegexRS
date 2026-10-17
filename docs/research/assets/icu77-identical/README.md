# Root IDENTICAL evidence, 2026-10-17

The [result report](../../root-identical-results.md) explains the implementation,
the original empty-reference errors, the approved exception and the remaining
acceptance work. This directory preserves complete raw evidence outside `target`.

## Complete IDENTICAL run

`runs/2026-10-17T114006Z-xz/` contains:

- [summary.json](runs/2026-10-17T114006Z-xz/summary.json): the exact original run
  summary, including effective settings, source and executable identities,
  group totals and the three original empty-reference process records.
- [raw.tar.xz parts](runs/2026-10-17T114006Z-xz/raw.tar.xz.parts/manifest.json): all **85** raw files from the
  completed run, including every input, expected key, candidate key, expectation
  origin, ordering result, stderr file, reference-process record and summary.
- [manifest.json](runs/2026-10-17T114006Z-xz/manifest.json): byte counts and SHA256
  values for every original file and the archive itself.
- [verification.json](runs/2026-10-17T114006Z-xz/verification.json): the completed
  archive check. All files were decompressed and their bytes checked against
  their recorded identities; no collator was rerun for archive verification.

The archive is **23,509,336 bytes**, SHA256
`ac83c1f401ed9b5143f1ff244aab1246ce3ee8d285d55b5b4c504bf5dceade71`.
It uses XZ preset 6 and deterministic tar metadata. An earlier 60,602,657-byte
gzip copy remains local at `target/research/icu77-cloud/identical-gzip-archive/`;
the smaller XZ byte stream is the versioned complete delivery. The upload client
could not send the complete 23.5 MB blob in one request, so it is stored as 12
ordered binary parts. Each part and their unchanged concatenation have recorded
SHA256 values. The source raw directory
remains unchanged at `target/research/icu77-cloud/identical/`.

Verify or extract from the repository root:

```sh
mkdir -p target
python3 -B tools/dev/split_artifact.py join \
  --manifest docs/research/assets/icu77-identical/runs/2026-10-17T114006Z-xz/raw.tar.xz.parts/manifest.json \
  --output target/icu77-identical-recorded.tar.xz
python3 -B tools/icu-probe/primary/archive_evidence.py --verify \
  docs/research/assets/icu77-identical/runs/2026-10-17T114006Z-xz \
  --archive target/icu77-identical-recorded.tar.xz
mkdir -p target/icu77-identical-recorded-run
tar -xJf target/icu77-identical-recorded.tar.xz -C target/icu77-identical-recorded-run
```

Absolute paths inside preserved JSON identify the original workspace. Archive
members use relative paths, so extracted input/output files can be consumed
from any directory. Reproduction uses tracked scripts described in
[IDENTICAL.md](../../../../tools/icu-probe/primary/IDENTICAL.md).

## Independent and derived evidence

- [historical-nonfcd/summary.json](historical-nonfcd/summary.json),
  [keys.tsv](historical-nonfcd/keys.tsv) and [pairs.tsv](historical-nonfcd/pairs.tsv)
  relate the new saved root keys to the preserved 13-input experiment. The 13
  keys and all 78 pairs agree, including its 18 former root differences. These
  are derived observations of existing outputs, not additional accepted inputs.
- [nfd-check-manifest.json](nfd-check-manifest.json) records the successful
  regeneration check of the 255,286-byte Unicode16 NFD blob, verified official
  source identities, exact fixed versions, observed root options and two
  deterministic export processes.
- [local-validation.json](local-validation.json) records actual Python harness
  and NFD-check observations; [candidate-runtime-dependencies.txt](candidate-runtime-dependencies.txt)
  contains actual dependency-tool output for the tested Rust executable.
- [rust-validation-transcript.json](rust-validation-transcript.json) explicitly
  preserves captured tool transcripts for 19 passing Rust tests, formatting and
  Clippy. These transcripts are not represented as original redirected log files.
- [review-context-generator-verification.json](review-context-generator-verification.json)
  confirms byte-identical UTF-8 and UTF-16 regeneration of the separate 2,048-input
  review corpus using the newly tracked portable generator. It reruns no collator.

## Preserved independent PRIMARY review replay

`primary-review-contexts-2048/` contains the complete **11-file** archive of the
separately authorized replay completed at **2026-10-17 11:04:29 UTC**. Its
[summary](primary-review-contexts-2048/summary.json) records that this was a new
replay to preserve the previously reported in-memory diagnostic, using the
original recorded executables. It does not claim to recover the earlier raw
output. All 2,048 complete keys and 2,048 CE traces agreed.

The [raw archive](primary-review-contexts-2048/raw.tar.gz) is **357,971 bytes**,
SHA256 `2b87854dc115f111ac6a538f484446354a49d3d8640c5db3f5c7e722c6418c45`.
Its original `reproduce.py`, input files, complete outputs and traces are all
included. [manifest.json](primary-review-contexts-2048/manifest.json) and
[verification.json](primary-review-contexts-2048/verification.json) verify the
preserved bytes. This diagnostic contributes no records to the main PRIMARY
1,160,181 key count, 28,108 CE count, or the later IDENTICAL totals.
