# Sonar observation after the collector source repair

The original artifact from [Actions run 39115858519](https://github.com/1298345095/BoostRegexRS/actions/runs/39115858519)
records the completed check for commit `4a6f01bc04b487e593cd5a7679d931289af73a04`.
The collector succeeded; the **Sonar check failed**. Issue
[#18](https://github.com/1298345095/BoostRegexRS/issues/18) remains the live tracker.

## Observed result and source delta

The inventory contains **159 unique issues: 135 code smells and 24 security
issues**. Its quality-gate response is `ERROR`: new-code security rating is
**5 (E)** against the required **1 (A)**. Reliability and maintainability are
both 1, duplicated lines are 0.3% against 3%, and reviewed hotspots are 100%.

Compared with the [previous 161-issue observation](../actions-39087060008/README.md),
all 159 retained issue objects are identical, no new key appears, and these two
keys are absent:

| Historical issue key | Rule and source repair |
| --- | --- |
| `AaFMpz_DDyq7mXZU9k75` | `python:S1192`, repeated issue artifact filename |
| `AaFMpz_DDyq7mXZU9k76` | `python:S3776`, complexity of the completed-check loop |

Both findings concern the collector repair in
[992bfc3c](https://github.com/1298345095/BoostRegexRS/commit/992bfc3c4f90c33cbc202954065200796d70cfa5).
Their absence is consistent with that source change; it does not identify a
service-side issue disposition. The 24 security findings remain in this response.
The existing 91/115-issue source ledgers and the ongoing changed/new-source review
remain applicable; this report does not duplicate those individual assessments.

## Timing and attribution

The collector saved 11 check observations over 56.456 seconds, within its
150-second deadline. It selected exact-SHA check `117641582514`, which started
at `2026-10-18T09:34:32Z` and completed with failure at `09:35:24Z`. The collector
observed completion at `09:35:27.675566Z`, before its subsequent issue requests;
its summary was written at `09:35:33.302969Z`.

Both bracketing PR responses identify the requested commit. Both project-task
responses identify successful analysis `2211683d-1748-44bd-8bb6-51c5c2df8d75`,
PR 1 and an empty queue. These observations bracket a mutable live-PR query;
the API request itself does not select an immutable analysis. The retained
`live_pr_unpinned`, `sonar_associated_commit_verified: false` and
`sonar_analysis_binding: not_established` therefore remain accurate. The exact
GitHub check identity is established separately.

No Sonar token was supplied. Public read requests returned HTTP 200 and the
authentication response says `valid: true`; those responses do not establish
issue-management permission. No remote issue disposition or gate setting changed.

## Retained bytes and reproduction

[artifact-source.json](artifact-source.json) records official artifact ID
`12131979660`, retrieval time, GitHub digest and all member identities. The
unchanged [raw.zip](raw.zip) is **94,765 bytes**, SHA-256
`b6b5f7abf49ac3ee39dcc8e931edfa1792279186425baebcda40250e9916ce62`.
All 26 ZIP members passed size/hash and CRC checks. The temporary download URL
is not retained. The original verification output is [verification.log](verification.log).

The following command rechecks the complete artifact and full-object delta
without querying the mutable service or extracting the ZIP:

```sh
timeout --signal=TERM --kill-after=5s 20s python3 -B - <<'PY'
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

root = Path('docs/research/assets/sonarcloud/actions-39115858519')
record = json.loads((root / 'artifact-source.json').read_text())
raw = (root / 'raw.zip').read_bytes()
assert len(raw) == record['bytes'] == 94765
assert hashlib.sha256(raw).hexdigest() == record['sha256']
assert record['github_digest'] == 'sha256:' + record['sha256']
with ZipFile(root / 'raw.zip') as archive:
    assert archive.testzip() is None
    assert len(archive.namelist()) == len(record['members']) == 26
    assert set(archive.namelist()) == {item['path'] for item in record['members']}
    for item in record['members']:
        content = archive.read(item['path'])
        assert len(content) == item['bytes']
        assert hashlib.sha256(content).hexdigest() == item['sha256']
    summary = json.loads(archive.read('summary.json'))
    wait = json.loads(archive.read('github-check-wait.json'))
    assert wait['selected_check']['head_sha'] == record['head_sha']
    assert wait['status'] == summary['check_status'] == 'completed'
    assert wait['selected_check']['conclusion'] == summary['quality_gate_conclusion'] == 'failure'
    assert summary['sonar_associated_commit_verified'] is False
    assert summary['sonar_token_supplied'] is False
    rows = json.loads(archive.read('sonar-issues.json'))['payload']
    current = {item['key']: item for item in rows['issues']}
    assert len(current) == len(rows['issues']) == rows['paging']['total'] == 159
    assert sum(item['rule'].startswith('pythonsecurity:') for item in current.values()) == 24
    gate = json.loads(archive.read('sonar-quality-gate.json'))['payload']['projectStatus']
    assert gate['status'] == 'ERROR'
with ZipFile(root.parent / 'actions-39087060008/raw.zip') as archive:
    previous = {item['key']: item for item in json.loads(archive.read('sonar-issues.json'))['payload']['issues']}
assert current.keys() <= previous.keys()
assert all(value == previous[key] for key, value in current.items())
assert previous.keys() - current.keys() == {'AaFMpz_DDyq7mXZU9k75', 'AaFMpz_DDyq7mXZU9k76'}
print('26 member hashes and ZIP CRC verified; 159 unchanged issues, two absent collector findings.')
print('Exact GitHub check failed; live PR inventory remains unpinned; security findings: 24.')
PY
```
