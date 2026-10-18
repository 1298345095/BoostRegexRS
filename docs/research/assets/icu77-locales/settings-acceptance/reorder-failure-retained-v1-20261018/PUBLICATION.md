# Original rejected reorder run

This bundle retains the original frozen B failure, including the actual rejected-settings executable, B CLI, native reference, source snapshots, inputs, commands and outputs. Its original `differences_or_incomplete` status is unchanged. Later C results are separate evidence.

## Stored bytes

The archive and its original manifest are unchanged. The archive is published as two byte-for-byte parts under `parts/` because its Base64 upload exceeded the GitHub connector's observed 16 MiB request-body limit. The original unsplit `raw.tar.gz` is not also committed.

- Original archive: 14,276,175 bytes; SHA-256 `43dd9efd39df9cd65c0debbfb74b8d5fd0c1940f5e94c742f5f0072ca25e027d`.
- Original archive verification: 60 complete members; see [verification.json](verification.json).
- Each part's identity and the combined identity: [parts/manifest.json](parts/manifest.json).

## Reassemble and verify

Run from the repository root. The selected output must not already exist; choose a fresh output name when repeating the recipe.

```sh
timeout --signal=TERM --kill-after=5s 20s mkdir -p target/research/reassembled-evidence
timeout --signal=TERM --kill-after=5s 30s \
  python3 -B tools/dev/split_artifact.py join \
    --manifest docs/research/assets/icu77-locales/settings-acceptance/reorder-failure-retained-v1-20261018/parts/manifest.json \
    --output target/research/reassembled-evidence/reorder-failure-20261018.tar.gz
timeout --signal=TERM --kill-after=5s 60s \
  python3 -B tools/icu-probe/primary/archive_evidence.py \
    --verify docs/research/assets/icu77-locales/settings-acceptance/reorder-failure-retained-v1-20261018 \
    --archive target/research/reassembled-evidence/reorder-failure-20261018.tar.gz
```

The join checks every part and the full original archive hash. The archive verifier checks every member against the original manifest. Reassembly is transport recovery, not a new native or Rust test run.

