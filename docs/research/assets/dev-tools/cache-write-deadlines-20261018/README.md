# Concurrent cache records and finite command deadlines

Two overlapping Cargo wrappers previously used the same
`rust-toolchain-manifest.json.tmp` path. One renamed that temporary file first;
the other failed with `FileNotFoundError` before Cargo tests could start. The
original invocation, traceback and exit 1 remain in the separate formatter
name-index evidence, under `full-tests-01`. The later serial `full-tests-02`
passed 54 tests; it does not replace that failed observation.

`prepare.write_json` now serializes the record first, creates a unique temporary
file in the destination directory, closes it and atomically replaces the
destination. Each invocation cleans up only its own temporary file. Callers
continue to choose their destination, including paths outside the checkout.
Concurrent writers have last-published-record semantics; there is no merge or
claim to retain several observations in one cache filename. Run evidence still
uses distinct directories.

The same helper also rejects nonfinite or nonpositive command deadlines and
termination grace periods before creating output files or launching a process.
Its existing process-group termination and cancellation lifecycle is unchanged.

## Actual results

| Retained execution | Result |
| --- | --- |
| `before/cache-writes` | Exit 1: a synchronized pair reproduces the shared temporary failure; failed publication leaves the old temporary file |
| `before/deadlines` | Exit 1: invalid budgets are not rejected by the required finite-positive contract |
| `after/tests` | Exit 0: all 10 tests pass, none skipped |
| `wrapper-overlap/cargo-0` | Actual simultaneous Cargo wrapper, exit 0 |
| `wrapper-overlap/cargo-1` | Actual simultaneous Cargo wrapper, exit 0 |

The concurrent regression holds two writers at the publication boundary before
allowing both real renames. It checks that both calls finish, the destination is
one complete UTF-8 JSON record, and no temporary file remains. Separate tests
exercise serialization and rename failures while preserving the previous record.
The deadline regressions reject NaN, both infinities, zero and negative values
for both timeout parameters. Existing tests actually launch and terminate child
processes, descendants ignoring TERM, parallel workers and controllers interrupted
during launch.

Both wrapper commands reported Rust `1.99.1 (58cf8f9c3 2026-10-13)` and Cargo
`1.99.1 (5f94df478 2026-08-27)`. These executions validate the repaired shared
cache path; they are not another regex test or native reference run.

The fixed `prepare.py` SHA-256 is
`55001945c51948912c9fbab5b15441b7dc99f69ac150be7b56148281d2197a89`.
Source identities, snapshots, literal argv, deadlines, both streams and actual
exit status are retained for each regression observation. The original formatter
failure is preserved in its original evidence group rather than copied here.

## Reproduce and verify

From the repository root:

```sh
timeout --signal=TERM --kill-after=5s 90s python3 -B -m unittest discover -s tools/icu-probe/cloud -p 'test_*.py' -v
timeout --signal=TERM --kill-after=5s 45s python3 -B tools/dev/cargo.py --version
timeout --signal=TERM --kill-after=5s 30s python3 -B tools/icu-probe/primary/archive_evidence.py --verify docs/research/assets/dev-tools/cache-write-deadlines-20261018/retained
```

The two original wrapper process records preserve the simultaneous invocations
and their independent logs. They reused the already verified toolchain cache.
The deterministic concurrent regression does not require a Rust download.

Publish this report and the four files under `retained`; its manifest and full
member verification retain the raw evidence without duplicating expanded source
and log directories in Git.
