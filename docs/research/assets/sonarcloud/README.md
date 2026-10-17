# SonarCloud gate investigation, 2026-10-17

The latest observed check for PR #1, commit
`b71b31e1345d4453273ba529574eea348c654613`, is
[check 117383130668](https://github.com/1298345095/BoostRegexRS/runs/117383130668).
Its sole reported failed condition is **Security Rating on New Code E, required
A**. GitHub exposes 50 annotations, including the eight security reports below.
This is separate from the successful ICU77 build/validation workflow.

The GitHub API responses are retained in the commit-named directory. They identify the
commit and check directly; no local test is substituted for the server result.
GitHub annotation titles do not contain rule keys or full taint-flow details.
SonarCloud's API and dashboard both returned a CloudFront HTTP 403 "Request
blocked" response during this investigation, before a login or issue-management
screen could be reached. We cannot infer account permission from that response.
No issue has been marked resolved, accepted, or false positive, and the observed
server gate remains **failed**.

## Eight security reports

Paths below are relative to `tools/icu-probe/`. Locations refer to the analyzed
commit. Each ID can be opened at
`https://sonarcloud.io/project/issues?id=1298345095_BoostRegexRS&issues=<ID>&open=<ID>&pullRequest=1`.

| Issue ID | Location | Report | Traced input boundary |
| --- | --- | --- | --- |
| `AaFJiPCJCiUwZk3hyg8o` | `primary/export/data_format.py:157–159` | Path traversal in `main` | `--contexts-output` explicitly chooses the developer's diagnostic output. Decoded table content becomes JSON values, not paths. |
| `AaFJiPBVCiUwZk3hyg8M` | `primary/compare.py:193` | Path traversal in `main` | `--output` explicitly chooses the parent directory created for the result. No corpus field participates in this path. |
| `AaFJiPBVCiUwZk3hyg8N` | `primary/compare.py:32` | Path traversal in `rows` | Input/reference/candidate paths are explicit CLI inputs or caller-owned test fixtures. The function does not derive filenames from TSV rows. |
| `AaFJiPBVCiUwZk3hyg8O` | `primary/compare.py:194` | Path traversal in `main` | The chosen `--output` receives the comparison result. External temporary directories are a supported development use. |
| `AaFJiPBdCiUwZk3hyg8Q` | `primary/generate_cases.py:187` | Path traversal in `main` | `--output` is a developer-selected directory. Files written beneath it have fixed names; generated case IDs are TSV data. |
| `AaFJiPB2CiUwZk3hyg8Z` | `primary/export/generate.py:75` | Path traversal in `save_json` | The invoking developer selects cache/output directories. Exporter report and binary names are fixed by the tool. |
| `AaFJiPGXCiUwZk3hyg9O` | `cloud/prepare.py:45` | Path traversal in `write_json` | Cache/output paths come from the invoking developer and fixed internal filenames. Downloaded data is not used as an output path. Archive extraction separately uses Python's `data` filter. |
| `AaFJiPGXCiUwZk3hyg9P` | `cloud/prepare.py:147` | Command injection in `run_logged` | The developer chooses the compiler; command arguments are a list passed without a shell. Corpus values never select the executable or arguments. |

All eight reports originate from same-permission developer CLI choices in this
repository. No lower-trust input-to-privileged-operation path was found in the
reported flows. The proposed disposition is individual **false positive**, with
the explanation above, once the full issue details are accessible. No general
path jail, compiler allowlist, `NOSONAR`, or rule exclusion was added.

## Changes and remaining service action

The tools now explicitly document their CLI boundary and pass `shell=False` at
the reported subprocess call. Three focused regressions cover metacharacters
as literal arguments, valid external output paths, and child failure reporting.
Cloud runner/replay filenames use named constants for the duplication reports.
The ordering comparator uses concise digit classes with `re.ASCII`, retaining
the error-marker protocol's rejection of Unicode digits. Local verification:

- CLI boundary regressions: 3 passed; see `cli-boundary-tests.log`.
- Ordering comparator regressions: 9 passed; see `ordering-comparator-tests.log`.

The analysis configuration specifies the actual Python/C++ versions and leaves
all code and gate thresholds in scope. The default-branch limitation and Rust
automatic-analysis gap are documented in `tools/quality/README.md`.

Once SonarCloud is reachable, read the full eight issues, apply only dispositions
supported by their actual flows, and rerun analysis. This service action remains
open; the local changes do not claim that the remote gate has passed.
