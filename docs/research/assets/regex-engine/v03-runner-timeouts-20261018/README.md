# Finite deadlines for the byte reference collector

The collector now rejects nonfinite and nonpositive timeout values at both its
CLI and imported `run` entrance, before reading inputs, creating an evidence
directory, or starting a process. This corrects the finite-deadline requirement
in `AGENTS.md`; it does not change regex semantics or comparison classifications.

The previous `timeout <= 0` check accepted NaN and positive infinity. A shared
`positive_timeout` parser now checks `math.isfinite` as well as positivity.
The tests cover `nan`, `inf`, `-inf`, `1e309`, zero and a negative value at both
entrances. A real sleeping child is separately stopped by a 0.2-second deadline;
its process record and both streams are checked.

## Actual results

| Retained execution | Actual result |
| --- | --- |
| `before/tests` | Exit 1: both entrance tests fail for the invalid budgets; the actual child timeout test passes |
| `after/targeted` | Exit 0: all three timeout tests pass |
| `after/protocol-suite` | Exit 1: aggregate discovery selects a different module named `run` |
| `after-import-fix/protocol-suite` | Exit 0: all 30 tests pass after loading the intended runner by its file path |

The aggregate discovery failure is a test import defect, preserved separately
from the original timeout defect. Only the test import changed after the first
successful targeted run. The runner's repaired bytes stayed unchanged.

The archived records include the exact commands, deadlines, elapsed times, exit
statuses, separate output streams, and source snapshots for each observation.
These are Python tool tests on the recorded Linux environment, not a new native
Boost or Rust compatibility sweep. Existing native V03 evidence is unchanged.

| Final source | SHA-256 |
| --- | --- |
| `tools/regex-oracle/run.py` | `4855f0f2b21bb65e0cdfc6cdb7c209d68c4cd28db11903ba1deb6afaaf70095b` |
| `tools/regex-oracle/test_runner_timeouts.py` | `da01336eaeb33afa446002971ad1d8f011dbcb6d0b13dca5a59c6d044516f173` |

Independent Spec and Standards review cover the final source and these retained
receipts. This collector correction does not complete V03's remaining named
queries, immutable attribution contract or observations before iteration errors.

## Reproduce and verify

From the repository root:

```sh
timeout --signal=TERM --kill-after=5s 60s python3 -B -m unittest discover -s tools/regex-oracle -p test_runner_timeouts.py -v
timeout --signal=TERM --kill-after=5s 60s python3 -B -m unittest discover -s tools/regex-oracle -p 'test_*.py' -v
timeout --signal=TERM --kill-after=5s 30s python3 -B tools/icu-probe/primary/archive_evidence.py --verify docs/research/assets/regex-engine/v03-runner-timeouts-20261018/retained
```

The [archive manifest](retained/manifest.json) identifies every preserved byte;
the [verification record](retained/verification.json) records full member checks.
Publish this report and the four `retained` files. Expanded local observations
are retained for investigation but are not a second Git copy of the archive.
