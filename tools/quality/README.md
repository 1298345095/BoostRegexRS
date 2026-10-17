# Quality evidence and developer-tool checks

The SonarCloud quality gate remains authoritative. Collect its actual GitHub
check and annotations for a specific commit with:

```sh
python3 -B tools/quality/collect_sonar_evidence.py \
  --commit b71b31e1345d4453273ba529574eea348c654613 --pull-request 1
```

The default destination is `docs/research/assets/sonarcloud/<commit>/`, so the
evidence can be committed. Optional `GITHUB_TOKEN` and `SONAR_TOKEN` values are
read from the environment and never included in saved responses. Collection
does not change issues, scanner configuration, or the gate conclusion. Use
`--github-only` when SonarCloud is unavailable; the output marks those API
requests as `not_requested`.

GitHub check responses are pinned to `--commit`. Sonar's optional PR API requests
return the live PR state without a commit/analysis identifier. Those responses
are explicitly marked `live_pr_unpinned` and `associated_commit_verified: false`;
they must not be attributed to the historical commit named by the directory.

The `Collect Sonar quality evidence` Actions workflow runs the same read-only
collector from GitHub's runner network when its workflow or collector changes.
The collection command has a 240-second deadline within the five-minute job;
partial responses are uploaded even when collection fails or times out.
Select an existing analyzed commit with
its `commit` dispatch input. Its automatic development-branch run uses the
recorded IDENTICAL source commit. It uses only read permissions, with an optional
repository `SONAR_TOKEN` sent exclusively to SonarCloud. An absent token still
allows a public API attempt. The workflow uploads the complete responses; retain
those artifacts in this repository before their stated 14-day expiry. A successful
collection job does not override a failed `SonarCloud Code Analysis` gate.

`--inspect-access` also preserves the server's authentication-validity boolean,
web API descriptions and the definitions of the four reported security rules.
Rule requests include the observed organization key `1298345095`;
API metadata comes from `webservices/list`.
The summary records only whether `SONAR_TOKEN` was supplied. Neither a successful
public read nor a valid authentication response is treated as proof of permission
to change issue status. This inspection does not submit issue transitions.

Run the developer CLI boundary regressions with:

```sh
python3 -B -m unittest discover -s tools/quality -p 'test_*.py'
python3 -B -m unittest discover -s tools/icu-probe -p 'test_compare_ordering.py'
```

These tests exercise literal argument forwarding, developer-selected paths
outside the checkout, and propagation of a failed child process. CLI paths and
compiler selection are deliberate capabilities of the invoking developer;
corpus values do not choose output filenames or commands. A hosted service
accepting untrusted jobs would need its own process and filesystem boundary.

## Sonar analysis configuration

`.sonarcloud.properties` records UTF-8, Python 3.12, and the C++17 dialect used
by the reference builds. It contains no rule suppressions, source exclusions,
or gate-threshold changes. Sonar's automatic analysis reads this file from the
default branch; adding it to a pull request alone does not activate the settings.
Automatic analysis also does not support Rust or coverage reports. Rust checks
therefore continue to run in Cargo/CI. Full Rust Sonar analysis requires an
explicit migration to CI-based analysis with the project's Sonar credentials
and automatic analysis disabled, not a competing second scanner.

Sources: [automatic analysis](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/automatic-analysis),
[individual false-positive handling](https://docs.sonarsource.com/sonarqube-cloud/appendices/frequently-asked-questions).
