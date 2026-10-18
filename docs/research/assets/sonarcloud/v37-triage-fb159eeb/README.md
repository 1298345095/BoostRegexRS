# V37 source review and collector repairs

Review date: 2026-10-17 to 2026-10-18 UTC. Published source baseline:
`fb159eeb4583727cc70db4b9e53f8329fd25d8b8`. GitHub
[#3](https://github.com/1298345095/BoostRegexRS/issues/3) and
[#18](https://github.com/1298345095/BoostRegexRS/issues/18) retain acceptance and
work status; this directory records observations and verification evidence.

## Evidence scope and access

The [issue ledger](ledger.md) covers every one of the **91 original issue keys**,
including all **20 security issues** and all recorded security flow locations,
from the existing [Actions observation](../actions-39066906674/README.md).
Its original ZIP remains the only copy of those raw responses used here:
SHA-256 `69561dfa3ef22ec4061c76b0eb94c6a636d7c7b69cc691843da37ebd38112cd9`.
The ledger gives each issue a source-level assessment; it records no service-side
issue transitions and does not assert that Sonar analyzed the reviewed commit.

| Observation | Actual result | What it establishes |
| --- | --- | --- |
| `actions-39066906674`, collected 2026-10-17 20:29:28 UTC | Eight Sonar API HTTP 200 responses; 91 issues / 20 security issues; gate `ERROR`; no Sonar token supplied | Correct organization and supported API routes worked from Actions. PR responses are `live_pr_unpinned`, with the analyzed commit unverified. |
| [Local attempt 01](../v37-live-fb159eeb-01/github-check-runs.json) | No HTTP response: socket operation rejected by the local sandbox; collector exited 1 after saving the error | A local network restriction, not a server HTTP 403 or account-permission result. |
| [Local attempt 02](../v37-live-fb159eeb-02/summary.json), collected 2026-10-17 23:34:07 UTC | Historical GitHub check read with all 50 annotations; all eight Sonar API requests returned HTTP 403; no Sonar token supplied | The new raw 403 responses are retained independently. This attempt did not obtain a current successful Sonar inventory. |

The installed Sonar skills were consulted, but no callable Sonar connector or
authenticated `sonar` CLI was available in this session. An anonymous
`authentication/validate` result in the successful Actions observation does not
establish an account or issue-management authority. The saved API metadata
requires authentication and project Browse access for issue transitions, plus
Administer Issues for the documented false-positive/acceptance transitions.
No write operation was attempted. If those dispositions remain necessary after
source repair, authenticated project issue-management access is the missing
external capability; a local recommendation cannot substitute for it.

### P01 preservation audit

The existing checkpoint's `evidence-manifest.json` identifies 12 Sonar members
in the selected-evidence archive. Direct archive reads verified their manifest
hashes, including the original rule HTTP 400 responses, unsupported endpoint
HTTP 404 response, failed-check evidence, and original Actions evidence ZIP.
Those members were not expanded into a duplicate tree for this review.

The initial HTTP 403 investigation remains in the historical
[Sonar report](../README.md). No original 403 response body was found among
those checkpoint members. The separate unpublished `p01-routing-af49df4` raw
403 logs were lost during workspace pruning, as the published P01 report
already discloses. Local attempt 02 is new evidence and does not restore those
lost bytes. The routing/access findings are supported, but an unqualified
claim that every historical response was preserved would be false.

## Confirmed source defects

1. **Authorization crossed redirect origins.** Python's default redirect handler
   copied a supplied bearer header to a different host. A network-free synthetic
   request reproduced that behavior; no real credential was used. The collector
   now removes Authorization whenever scheme, hostname or effective port changes,
   including an HTTPS downgrade, while preserving same-origin authentication.
   Seven focused regressions passed; see [redirect-tests.log](redirect-tests.log).
2. **A repeated destination overwrote observation files.** The collector now
   creates its destination exclusively, before reading tokens or making network
   calls. Three regressions preserve original bytes, reject an existing empty
   directory without a request, and retain a failed response in a new destination
   outside the checkout; see [output-tests.log](output-tests.log).
3. **A literal staged filename could select another file.** In an isolated Git
   fixture containing both `item?.txt` and `item1.txt`, the existing
   `tools/dev/staged_git_payload.py --path 'item?.txt'` selected `item1.txt` because
   `--` ends option parsing but does not disable Git pathspec expansion. The
   equivalent `git --literal-pathspecs ls-files --stage -z -- 'item?.txt'` selected
   one exact entry. This defect was reported to the owner of `tools/dev`; no
   repair or independent validation of that file is claimed by this report.

These findings do not justify a checkout-only path policy or a compiler
allowlist. The ledger separately records the actual CLI authority of each
reported path and command flow. All 19 security false-positive recommendations
and the C++ `check_versions` normal-return recommendation remain proposals.
The four archived security-rule responses lack full explanatory rule text;
the other 71 rule definitions were not retrieved by that access probe.

## Verification and reproduction

The redirect change's affected quality suite passed 10 tests, recorded in
[quality-tests-redirect.log](quality-tests-redirect.log). With both collector
repairs, the suite passed **13 tests**, recorded in
[quality-tests-output.log](quality-tests-output.log). These are local worktree
results; review and committed-checkout verification are separate. No C++ native
run, cross-platform result or successful current Sonar reanalysis is implied.

Run the focused and combined tests from the repository root:

```sh
timeout --signal=TERM --kill-after=5s 60s python3 -B -m unittest discover -s tools/quality -p test_sonar_redirects.py -v
timeout --signal=TERM --kill-after=5s 60s python3 -B -m unittest discover -s tools/quality -p test_sonar_output.py -v
timeout --signal=TERM --kill-after=5s 60s python3 -B -m unittest discover -s tools/quality -p 'test_*.py' -v
timeout 20s git diff --check -- tools/quality
```

The exact two local collection commands were:

```sh
timeout --signal=TERM --kill-after=5s 60s python3 -B tools/quality/collect_sonar_evidence.py --commit ecca4f8d007f7dc0eb71c19316a67542f25a6653 --pull-request 1 --inspect-access --output docs/research/assets/sonarcloud/v37-live-fb159eeb-01
timeout --signal=TERM --kill-after=5s 60s env -u GITHUB_TOKEN -u SONAR_TOKEN python3 -B tools/quality/collect_sonar_evidence.py --commit ecca4f8d007f7dc0eb71c19316a67542f25a6653 --pull-request 1 --inspect-access --output docs/research/assets/sonarcloud/v37-live-fb159eeb-02
```

Attempt 02 used approved public network access after the sandbox refusal.
Its saved summary and raw responses establish the completed request sequence;
the process exit status was not separately retained in this evidence bundle.
Use a new output directory for another attempt: these directories are retained
observations and must not be reused. The existing Actions workflow also collects
on collector changes, with a 240-second command deadline in a five-minute job.

The ledger includes a bounded check of all 91 issue keys against the original
ZIP; it passed with no omissions or duplicate rows. Remaining V37 acceptance
depends on a successfully retrieved current inventory tied to its actual
analysis, the other source repairs with behavior checks, complete rule detail
where needed, and any required authenticated issue disposition. The failed
quality gate has not been reclassified or weakened.
