# P01: Sonar project access and corrected API routing

The read-only [Actions run 39066906674](https://github.com/1298345095/BoostRegexRS/actions/runs/39066906674)
completed successfully using collector/workflow source
`ce4eb40d352dd4de14dde4e76158338ac492bbc3`. Its observation at
**2026-10-17 20:29:28 UTC** confirms all eight requested Sonar API reads return
HTTP 200 after correcting the organization parameter and API metadata route.
The observed quality gate remains **ERROR**. Collection success does not satisfy
the gate-fix acceptance in [V39 / #38](https://github.com/1298345095/BoostRegexRS/issues/38).

## Original evidence and identities

[raw.zip](raw.zip) is the original GitHub artifact, downloaded again after
workspace maintenance. [artifact-source.json](artifact-source.json) records the
observed artifact metadata and each member's size and SHA-256. The download
matches GitHub's digest; ZIP CRCs and all 11 members were checked. The responses
are kept only inside this ZIP.

| Identity | Observed value |
| --- | --- |
| Repository / PR | `1298345095/BoostRegexRS` / `1` |
| Sonar host | `https://sonarcloud.io` |
| Organization | `1298345095` |
| Project key / name | `1298345095_BoostRegexRS` / `BoostRegexRS` |
| Project UUID | `AaFJiHX62ktK_MXfJsmn` |
| Artifact | `12113801642`, `sonar-evidence-39066906674-1`, 60,836 bytes |
| ZIP SHA-256 | `69561dfa3ef22ec4061c76b0eb94c6a636d7c7b69cc691843da37ebd38112cd9` |

The GitHub check inside the archive is **117391738137**, tied to historical
commit `ecca4f8d007f7dc0eb71c19316a67542f25a6653`. The collector's source commit
is a separate identity. Sonar's PR responses are explicitly
`live_pr_unpinned`, with `associated_commit_verified: false`; they provide no
proof that their analysis corresponds to either commit.

## Observed reads and authority

| Request | Result |
| --- | --- |
| `issues/search`, project above, PR `1` | HTTP 200; all 91 returned issues retained, including 20 `pythonsecurity` issues with their flows |
| `qualitygates/project_status` | HTTP 200; `ERROR`; `new_security_rating` is `5`, failing threshold `1` |
| `authentication/validate` | HTTP 200; `valid: true`, while `sonar_token_supplied: false` |
| `webservices/list` | HTTP 200; server API descriptions retained |
| Four `rules/show` requests with `organization=1298345095` | HTTP 200 for `pythonsecurity:S2083`, `S8701`, `S8705`, and `S8707` |

Security issue counts are **S2083: 2, S8701: 2, S8705: 4, S8707: 12**.
The issue response's project component establishes the organization, project
key, UUID, name and PR association above. These reads do not identify an
authenticated Sonar account. In particular, `valid: true` without a supplied
token is not evidence of issue-management authority.

The installed Sonar skills are readable, but the current session exposes no
callable Sonar tools. A fresh `timeout --kill-after=2s 20s which sonar` check
exited 1 with no output in the recovered checkout. No authenticated Sonar CLI,
account connection, issue write or analysis-management operation was verified.
GitHub artifact access is separate from Sonar account access.

The retained `api/issues` / `do_transition` server description requires
authentication and project **Browse** permission; `falsepositive`, `accept`
and `wontfix` additionally require **Administer Issues**. No transition was
submitted. If review in [V37 / #18](https://github.com/1298345095/BoostRegexRS/issues/18)
establishes an individual false positive, the minimum external operation is for
an authenticated project member with those permissions to apply that specific
reviewed disposition, or expose an authenticated connection with equivalent
authority. Local source fixes can continue without it. No paid feature, Rust
analysis migration, rule suppression or gate change is required by this report.

## Historical failures and recovery limit

The original **400** rule responses (missing `organization`) and **404**
`webservices/show` response from run `39033057246` remain in the existing
[checkpoint](../../../../development/tickets/checkpoint/README.md).
Its `selected-evidence.tar.xz` has SHA-256
`3e454475be840b0d9afb43cda51e8397d530dbc6607c2b80a54b79a7d300c6bb`;
`evidence-manifest.json` identifies all 12 original Sonar files under
`docs/research/assets/sonarcloud/actions-39033057246/`. Their stored sizes and
digests were checked directly in the archive during this recovery. No extra
expanded copy is needed in the published change. The former 89-issue observation
and this 91-issue observation concern changing PR state, not a controlled
commit-to-commit regression comparison.

The [initial investigation](../README.md) retains its earlier CloudFront 403
account and original GitHub check evidence. A later local observation named
`p01-routing-af49df4` and its 403 logs were never uploaded before workspace
maintenance removed the old checkout. Those raw logs could not be recovered;
this report does not recreate them or backdate a replacement. The retained
Actions ZIP supplies the successful routing observation independently.

## Reproduce

From the repository root, verify the retained original without extracting a
second response tree:

```sh
timeout --kill-after=2s 20s python3 -B - <<'PY'
import hashlib
import json
from pathlib import Path
import zipfile

p = Path('docs/research/assets/sonarcloud/actions-39066906674')
m = json.loads((p / 'artifact-source.json').read_text())
raw = (p / 'raw.zip').read_bytes()
assert len(raw) == m['archive_size_bytes'] == 60836
assert hashlib.sha256(raw).hexdigest() == m['archive_sha256']
with zipfile.ZipFile(p / 'raw.zip') as z:
    assert z.testzip() is None
    assert len(z.infolist()) == len(m['members']) == 11
    assert set(z.namelist()) == {r['path'] for r in m['members']}
    for r in m['members']:
        data = z.read(r['path'])
        assert len(data) == r['size']
        assert hashlib.sha256(data).hexdigest() == r['sha256']
    print(z.read('summary.json').decode())
PY
```

For a fresh network observation, choose a new output directory and retain its
exit status and responses, including failures:

```sh
timeout --signal=TERM --kill-after=5s 180s python3 -B tools/quality/collect_sonar_evidence.py \
  --commit ecca4f8d007f7dc0eb71c19316a67542f25a6653 --pull-request 1 \
  --inspect-access --output docs/research/assets/sonarcloud/new-observation
```

The existing `Collect Sonar quality evidence` Actions workflow runs the same
collector from GitHub's network with a 240-second command deadline inside a
five-minute job. Its `commit` input selects the GitHub check; Sonar PR reads
remain live and unpinned. A later observation may legitimately contain different
issues or gate values and must not overwrite this archive.
