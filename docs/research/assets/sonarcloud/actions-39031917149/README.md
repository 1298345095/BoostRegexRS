# Sonar server observation from GitHub Actions

Collected at **2026-10-17 12:17:16 UTC** by
[run 39031917149](https://github.com/1298345095/BoostRegexRS/actions/runs/39031917149),
workflow source commit `023fb66412a1c0324f072abf47b0dea7ad0608c3`.

The original downloaded artifact is retained as `evidence.zip`:

- Artifact ID: `12100333987`.
- Original name: `sonar-evidence-39031917149-1`.
- Bytes: `26063`.
- SHA256: `d75345738fa0fc0f42ebbfb3ac2635e77902a0f1902423aa1ce6e1988fbf6f75`.
- The five adjacent JSON files are its exact extracted contents.

The GitHub responses identify source commit
`ecca4f8d007f7dc0eb71c19316a67542f25a6653` and check `117391738137`.
That check **failed** the New Code Security Rating condition.

Both Sonar HTTP requests returned **200** from the Actions runner. The issues
response contains all **89** open issues reported by its pagination metadata
(page 1, page size 500), including **18 security findings** with complete flows.
The live Sonar gate response remains **ERROR**. Its other conditions passed.

The Sonar responses describe the live PR and do not return an associated commit
identifier. They are marked `live_pr_unpinned`, with
`associated_commit_verified: false`. They must not be relabeled as an analysis
of the older commit merely because the GitHub check request selected that commit.

The earlier CloudFront 403 observations remain historical network evidence. This
successful read from Actions resolves the read-access problem; it does not prove
issue-management permission, or change any issue status. Tokens and temporary
artifact download URLs are not included in this directory.
