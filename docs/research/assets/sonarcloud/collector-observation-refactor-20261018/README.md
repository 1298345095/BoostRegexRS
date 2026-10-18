# Preserve collector behavior while separating one check observation

The observation in [Actions run 39087060008](https://github.com/1298345095/BoostRegexRS/actions/runs/39087060008)
reported `python:S3776` on `completed_check` (issue
`AaFMpz_DDyq7mXZU9k76`) and `python:S1192` on the repeated
`sonar-issues.json` filename (issue `AaFMpz_DDyq7mXZU9k75`).

The source change extracts one observation into `observe_check`: request with
the remaining network deadline, preserve the full response, record receipt,
reject an unusable response, then select the newest matching check and record
its identity. `completed_check` retains the before/after deadline checks,
completion decision, wait progress, error classification and final trace
write. `ISSUES_FILE` names the unchanged filename in the query and its
before/after metadata boundary. No query, evidence schema or gate is changed.

The modified collector SHA-256 is
`397f40b5ea9600dbad9b26b4e020aa33b1721df66d6a30b6252dadc33cb359c1`.
The baseline is the published collector at `c96d00fa1d3a0a03cbe7a45386da44f12550aed7`;
its existing 19-test verification is retained in the earlier source review.

## Actual verification

On 2026-10-18 UTC, the complete existing quality suite ran **19 tests**, all
passed, exit **0**, in 0.051 seconds as reported by unittest. The actual
[tests.log](tests.log) includes the test names and process output. These checks
cover literal CLI arguments, caller-selected output paths, retained failures,
wait deadlines including a completed response arriving too late, exact check
selection, bracketing metadata, fresh output directories, and origin-bound
credentials through redirects. The source whitespace check also exited 0.

```sh
timeout --signal=TERM --kill-after=5s 60s python3 -B -m unittest discover -s tools/quality -p 'test_*.py' -v
timeout --signal=TERM --kill-after=5s 20s git diff --check -- tools/quality/collect_sonar_evidence.py
```

The local verification does not claim a later Sonar issue disposition or a
passing gate. The retained server observation predates this source change and
continues to report a failed security gate.

