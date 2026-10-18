# Original native DEFAULT-reset crash

This bundle retains the actual native executable and complete original DEFAULT-reset failure, including return code -11, source, input and output. The observation remains a `reference_error`. Compiler and linkage evidence collected later is explicitly distinguished in the retained summary; it does not replace original execution evidence.

## Stored bytes

The archive and its original manifest are unchanged. The archive is published as two byte-for-byte parts under `parts/` because its Base64 upload exceeded the GitHub connector's observed 16 MiB request-body limit. The original unsplit `raw.tar.gz` is not also committed.

- Original archive: 12,896,245 bytes; SHA-256 `f1e03565e0c38658fc064073d13bd0687b4286cbce8d2712107a1cc046b81c11`.
- Original archive verification: 21 complete members; see [verification.json](verification.json).
- Each part's identity and the combined identity: [parts/manifest.json](parts/manifest.json).

## Reassemble and verify

Run from the repository root. The selected output must not already exist; choose a fresh output name when repeating the recipe.

```sh
timeout --signal=TERM --kill-after=5s 20s mkdir -p target/research/reassembled-evidence
timeout --signal=TERM --kill-after=5s 30s \
  python3 -B tools/dev/split_artifact.py join \
    --manifest docs/research/assets/icu77-locales/settings-acceptance/default-reset-retained-v1-20261018/parts/manifest.json \
    --output target/research/reassembled-evidence/default-reset-20261018.tar.gz
timeout --signal=TERM --kill-after=5s 60s \
  python3 -B tools/icu-probe/primary/archive_evidence.py \
    --verify docs/research/assets/icu77-locales/settings-acceptance/default-reset-retained-v1-20261018 \
    --archive target/research/reassembled-evidence/default-reset-20261018.tar.gz
```

The join checks every part and the full original archive hash. The archive verifier checks every member against the original manifest. Reassembly is transport recovery, not a new native or Rust test run.

