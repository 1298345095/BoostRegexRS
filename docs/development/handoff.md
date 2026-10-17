# Persistent development handoff

Updated: 2026-10-17. Tracking: [issue #2](https://github.com/1298345095/BoostRegexRS/issues/2).

## Active authorization and completion condition

Continue to the complete standalone pure Rust Boost.Regex 1.89.0 library under
ADR-0001 through ADR-0005. The user explicitly expanded the former PRIMARY-only
stage on 2026-10-17. After each verified scoped commit, select the next ready
capability and continue. Only complete capability, six-target, performance,
memory and documentation acceptance can close the overall task. Do not merge
main, publish a release, or integrate librime-rs.

Use the requested Stop That Shit skill: direct implementation, evidence-driven
fixes, no speculative defenses, no weakened tests/gates, no repeated approval
questions. Suitable crates are authorized if behavior and fixed data remain
compatible. Every commit title and body must be English.

## Repository and existing evidence

- Working branch: `work/root-primary-cloud`; draft PR #1.
- Baseline delivery: `b71b31e1345d4453273ba529574eea348c654613`.
- Tested PRIMARY source: `9e57799d39c7610bfb6a93b1e7f8a51205e5b4a7`.
- PRIMARY: 1,160,181 valid full keys, 11 expected invalid-input rejections,
  28,108 CE64 records; Linux local and clean Actions evidence passed.
- Historical Windows evidence under `docs/research/assets/icu-probe` is immutable.
- The 145 ICU4X IDENTICAL differences and original empty IDENTICAL crashes remain
  historical evidence. An independently fixed implementation does not rewrite them.

## Current work and ownership

- Root: full capability tracking, tracked tool launchers, regex reference/API/engine.
- `rust_primary`: root IDENTICAL writers and Rust regression tests.
- `spec_review`: fixed Unicode16 NFD export, IDENTICAL oracle and differential runner.
- `standards_review`: actual SonarCloud findings, source fixes and CI configuration.

Agents share the working tree; coordinate path ownership. Root creates commits
and updates GitHub. The environment has no `gh` executable; the connected GitHub
API performs the same authorized issue/ref operations without inventing credentials.
Issue #2 uses the canonical `ready-for-agent` label.

## Reproduction and artifact locations

```sh
python3 -B tools/dev/cargo.py test --locked
python3 -B tools/dev/update_capabilities.py
python3 -B tools/icu-probe/cloud/run.py --jobs 6
```

All authored scripts, minimized regressions, data generators and durable evidence
belong in tracked `tools/`, `tests/`, `src/` or `docs/` paths. `target` may retain
downloaded tool/source caches and compiled products. New test runs save reviewable
evidence outside target; large raw evidence may be compressed with the reproduction
script and digest tracked alongside it. Preserve earlier target evidence in place.

## Current external issue

SonarCloud check 117383130668 failed New Code Security Rating (E versus A).
Eight annotations report CLI-controlled file/argv operations; review each actual
trust boundary. Do not impose unusable path restrictions or suppress genuine
findings to pass. SonarCloud HTTP API and the project/PR UI currently return
CloudFront 403; opening the UI and one refresh both failed before authentication.
GitHub check evidence remains readable. Record this as unresolved external access,
not a passing gate. Continue independent implementation.

## Next actions

1. Verify/commit the tracked launcher and inventory slice, preserving concurrent edits.
2. Run IDENTICAL full-key comparisons and minimize/fix every concrete difference.
3. Build the native regex oracle and implement byte search/capture APIs against it;
   then continue all grammar, API, trait and platform rows in the capability matrix.
4. Configure six native targets and fixed performance/memory workloads, retaining
   unverified status until actual results exist.
