# Sonar observation after the completed c96d00fa check

This is the original artifact from [Actions run 39087060008](https://github.com/1298345095/BoostRegexRS/actions/runs/39087060008), collected for commit
`c96d00fa1d3a0a03cbe7a45386da44f12550aed7`. GitHub issue
[#18](https://github.com/1298345095/BoostRegexRS/issues/18) owns the ongoing source
repairs and issue dispositions; this directory records one immutable observation.

## Observed result

The collector completed successfully. The **Sonar check failed**, and the live
quality-gate response is **ERROR**: new-code security rating **5 (E)** exceeds
the threshold **1 (A)**. Reliability and maintainability were both 1;
duplication was 0.3% against 3%; reviewed security hotspots were 100%.

There are **161 unique issues**, including **24 security issues**. Compared with
the [previous 115-issue observation](../actions-39081773775/README.md), 86 complete
issue objects are unchanged, 27 retained objects changed, 48 keys were added and
2 historical keys are absent. Absence is not a resolved disposition. The
previous source ledger remains the review basis for unchanged findings; the
changed/new source review remains in progress.

The additional security finding reports the explicit `--extra-requests` file
read in `inventory_locales.py`. Its actual caller authority must be reviewed
before any source fix or service disposition. No source/test exclusion, rule
suppression, path restriction or gate relaxation was applied.

## Check timing and attribution

The wait trace contains 11 saved check observations. It selected check
`117555886894` for the exact requested SHA, waited 55.922 seconds, and observed
completion before requesting the issue inventory.

| Observation | UTC |
| --- | --- |
| Sonar check started | 2026-10-18 01:35:47 |
| Sonar check completed with failure | 2026-10-18 01:36:33 |
| Wait finished after observing completion | 2026-10-18 01:36:41.146189 |
| Collector wrote its final summary | 2026-10-18 01:36:47.703811 |

The before/after PR metadata both identify commit `c96d00fa`. The before/after
project task metadata both identify successful analysis
`f9017ea1-3cdb-43e6-b3d9-ad906cc6bf92` for PR 1, with an empty task queue. These
are bracketing observations around a **live PR query**, not an immutable
analysis selector on that query. The archive therefore correctly retains
`live_pr_unpinned`, `associated_commit_verified: false`, and
`sonar_analysis_binding: not_established`. The exact GitHub check identity is
established separately.

No Sonar token was supplied. All requested read APIs returned HTTP 200, but
public read access does not establish issue-management authority. The four
saved rule responses still do not provide full explanatory descriptions, and
S6549 was not included in those four requests.

## Retained bytes and verification

[artifact-source.json](artifact-source.json) records artifact ID
`12120334038`, the retrieval time, the official API source, and every ZIP member.
The original [raw.zip](raw.zip) is **95,514 bytes**, with SHA-256
`72681cadd9e74fe6f99aeadc475a925f9a6b837c778fc3fc5ea5a3e124cdd096`,
matching GitHub's published digest. All **26 members** pass their recorded
size/hash checks and ZIP CRC verification. The temporary download URL is not
retained.

The following bounded command reads members directly, checks the failed
conclusion and stated scope, and reconciles every key against the previous
observation. Its actual output is retained in [verification.log](verification.log).

```sh
timeout --signal=TERM --kill-after=5s 20s python3 -B - <<'PY'
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

root = Path("docs/research/assets/sonarcloud/actions-39087060008")
record = json.loads((root / "artifact-source.json").read_text())
raw = (root / "raw.zip").read_bytes()
assert len(raw) == record["bytes"]
assert hashlib.sha256(raw).hexdigest() == record["sha256"]
assert record["github_digest"] == "sha256:" + record["sha256"]
with ZipFile(root / "raw.zip") as archive:
    assert archive.testzip() is None
    assert set(archive.namelist()) == {item["path"] for item in record["members"]}
    for item in record["members"]:
        body = archive.read(item["path"])
        assert len(body) == item["bytes"]
        assert hashlib.sha256(body).hexdigest() == item["sha256"]
    summary = json.loads(archive.read("summary.json"))
    wait = json.loads(archive.read("github-check-wait.json"))
    issues = json.loads(archive.read("sonar-issues.json"))["payload"]
    gate = json.loads(archive.read("sonar-quality-gate.json"))["payload"]["projectStatus"]
    assert wait["selected_check"]["head_sha"] == record["head_sha"]
    assert wait["status"] == "completed"
    assert wait["selected_check"]["conclusion"] == summary["quality_gate_conclusion"] == "failure"
    assert summary["sonar_associated_commit_verified"] is False
    assert gate["status"] == "ERROR"
    for phase in ("before", "after"):
        metadata = json.loads(archive.read(f"sonar-pull-requests-{phase}.json"))["payload"]
        pr = next(item for item in metadata["pullRequests"] if item["key"] == "1")
        assert pr["commit"]["sha"] == record["head_sha"]
new = {item["key"]: item for item in issues["issues"]}
assert len(new) == len(issues["issues"]) == issues["paging"]["total"] == 161
assert sum(item["rule"].startswith("pythonsecurity:") for item in new.values()) == 24
with ZipFile(root.parent / "actions-39081773775/raw.zip") as archive:
    old_rows = json.loads(archive.read("sonar-issues.json"))["payload"]["issues"]
old = {item["key"]: item for item in old_rows}
unchanged = {key for key in old.keys() & new.keys() if old[key] == new[key]}
counts = (len(unchanged), len(old.keys() & new.keys() - unchanged),
          len(new.keys() - old.keys()), len(old.keys() - new.keys()))
assert counts == (86, 27, 48, 2)
print("Artifact digest, ZIP CRC and all 26 member hashes verified.")
print("Completed check: exact requested SHA; conclusion failure; live PR inventory remains unpinned.")
print("161 unique issues, 24 security issues; delta 86 unchanged / 27 changed / 48 added / 2 absent.")
PY
```

