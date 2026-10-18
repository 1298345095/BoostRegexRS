# Sonar observation from Actions run 39081773775

The collection succeeded, but the quality gate remained **ERROR**. This dated
snapshot contains **115 open issues, including 23 security issues**. It does not
prove that Sonar finished analyzing the collector's source commit before the
issues were read. The timing evidence below identifies that concrete gap.
GitHub [V37 / #18](https://github.com/1298345095/BoostRegexRS/issues/18) owns the
work and acceptance state; this directory contains evidence and source review.

## Provenance and observed results

| Item | Recorded value |
| --- | --- |
| Workflow run | [39081773775](https://github.com/1298345095/BoostRegexRS/actions/runs/39081773775), attempt 1; collect job completed successfully |
| Collector source | `70e9ac1a945d5f2c81f31e3f856e0ec268c5a2a0` |
| Original artifact | `sonar-evidence-39081773775-1`, ID `12118764103`; 66,047 bytes |
| Original ZIP SHA-256 | `e0907573be9b733049bb61507c076afed3b594745ee148f9fb04e33f96cce739` |
| Collector summary time | `2026-10-18T00:10:35.184773+00:00` |
| Historical GitHub check selected by that collector | Commit `ecca4f8d007f7dc0eb71c19316a67542f25a6653`, check `117391738137`, completed with `failure`; all 50 annotations retained |
| Sonar HTTP results | All eight requests returned 200: issues, quality gate, authentication validity, Web API metadata and four security-rule definitions |
| Issue response | Page 1, page size 500, total 115; 115 unique issue keys; 23 `pythonsecurity` issues |
| Gate failure | `new_security_rating = 5`, error threshold 1; the returned gate is `ERROR` |
| Other gate conditions | Returned conditions are `OK`; new duplicated-line density is 0.4 against threshold 3 |
| Authentication | No Sonar token supplied. The anonymous validity response establishes no account identity or issue-management permission |
| Analysis attribution | Live PR 1, `associated_commit_verified: false`; immutable analysis binding not established |

[raw.zip](raw.zip) is the original downloaded artifact, verified against the
GitHub artifact digest. [artifact-source.json](artifact-source.json) records its
download provenance, job results, all 11 member sizes and hashes, and CRC check.
The raw responses remain inside that single ZIP. Its original server expiry was
2026-11-01 00:10:35 UTC; the checked-in bytes do not depend on that expiry.

The existing [91-issue observation](../actions-39066906674/README.md) and the two
independent local observations in the
[earlier review](../v37-triage-fb159eeb/README.md) remain historical evidence.
This successful Actions response does not replace local HTTP 403 responses or
restore the unpublished logs lost during workspace pruning.

## Why this inventory cannot be assigned to commit 70e9ac1

The separate original
[check-runs response](collector-commit-check-runs.json) reports the following
check for the collector source commit:

| Event | Server or collector timestamp (UTC) |
| --- | --- |
| Sonar check `117540157618` started for `70e9ac1a945d5f2c81f31e3f856e0ec268c5a2a0` | 2026-10-18 00:10:29 |
| Collector finished its request sequence and wrote its summary | 2026-10-18 00:10:35.184773 |
| That Sonar check completed, with `failure` | 2026-10-18 00:11:05 |

The issue response was fetched before the collector summary, hence before the
current commit's check completed. The check's `external_id` is empty and its
details URL identifies the live PR dashboard, without an immutable analysis
identifier. An issue's `lastChangeAnalysisUuid` identifies a change associated
with that issue; it does not identify the complete issue-list response. Neither
matching locations nor check timing proves a completed-analysis identity.

The supplemental response's bytes and source URL are in the manifest. Its exact
client retrieval timestamp was not separately recorded; the retained server
timestamps are the evidence used above. It is a separate observation, not a
member added to the original artifact.

The collector improvement prompted by this gap waits for the newest matching
check for the requested SHA and preserves each poll. It also brackets the issue
read with `project_pull_requests/list` and `ce/component`, recording actual
request times, unavailable responses and raw metadata. The saved official
`sonar-web-api.json` supports those Browse-level queries. Its
`project_analyses/search` parameters do not include a pull-request selector;
inventing such a parameter would not solve attribution. These live metadata
queries still do not establish an immutable issue-query binding. Local tests of
the improvement are not a successful subsequent server observation.

## Source review and repair evidence

The [delta ledger](triage-delta.md) reconciles all 115 keys without duplicating
the previous 91-row source review: 86 issue objects are unchanged, 3 retained
objects changed, 26 keys were added and 2 historical keys are absent. Absence
does not prove a code fix or a service-side disposition.

The review found a real error classification defect in the native regex oracle:
Boost's matcher complexity/stack paths construct `boost::regex_error`, while the
adapter currently classifies that type as `compile_error` without considering
whether it was thrown during compilation or execution. The ledger records the
exact upstream source and the correction to the earlier runtime-error
assumption. It requires a separate oracle repair and native regression; no such
repair or result is claimed by this observation.

The separately published literal staged-filename fix is
[`ae7578415d99a9662d4a8832f7958334fc625066`](https://github.com/1298345095/BoostRegexRS/commit/ae7578415d99a9662d4a8832f7958334fc625066).
Its [11-case test record](../v37-triage-fb159eeb/staged-payload-tests.log) covers
literal metacharacters, exact selection, directory/conflict rejection and
staged blob modes in isolated Git repositories. This updates the earlier
ledger's pre-repair finding, but does not claim a Sonar disposition or that this
artifact analyzed that later commit.

The attribution group's
[quality suite record](../v37-triage-fb159eeb/quality-tests-attribution.log)
contains 19 passing local tests, including six new synthetic timing/metadata
tests and the existing redirect, output-preservation and CLI-boundary checks.
The real Actions command limit remains 240 seconds with a 10-second kill grace
inside a five-minute job; the check wait is 150 seconds. These synthetic tests
do not count as native, cross-platform or post-fix Sonar acceptance.

The four rule responses still contain rule identity/metadata rather than full
explanatory descriptions. The new S6549 definition was not among those four
requests. Current source assessments therefore retain that rule-detail limit.
No authenticated issue disposition, rule suppression, exclusion, path jail,
compiler allowlist or quality-gate relaxation was performed.

## Reproduce the evidence checks

Run from the repository root. This reads ZIP members directly and checks every
recorded size/hash, including the separate GitHub response. Both this command
and the delta ledger's reconciliation command passed with exit 0; their exact
commands and results are retained in [verification.log](verification.log).

```sh
timeout --signal=TERM --kill-after=2s 20s python3 -B - <<'PY'
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

root = Path('docs/research/assets/sonarcloud/actions-39081773775')
source = json.loads((root / 'artifact-source.json').read_text())
raw = (root / source['archive']).read_bytes()
assert len(raw) == source['archive_size_bytes']
assert hashlib.sha256(raw).hexdigest() == source['archive_sha256']
assert source['artifact']['digest'] == 'sha256:' + source['archive_sha256']
with ZipFile(root / source['archive']) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist()) == {item['path'] for item in source['members']}
    for item in source['members']:
        body = archive.read(item['path'])
        assert len(body) == item['size']
        assert hashlib.sha256(body).hexdigest() == item['sha256']
for item in source['supplemental_responses']:
    body = (root / item['path']).read_bytes()
    assert len(body) == item['size_bytes']
    assert hashlib.sha256(body).hexdigest() == item['sha256']
print('Original ZIP, 11 members and supplemental GitHub response verified')
PY
```

The delta ledger contains the bounded 115-key reconciliation check. The
[collector guide](../../../../../tools/quality/README.md) documents new
observations and output refusal. Use a new output directory for every
collection. The unresolved gate, unavailable immutable analysis binding,
remaining source repairs and any required authenticated dispositions are
separate remaining acceptance conditions.
