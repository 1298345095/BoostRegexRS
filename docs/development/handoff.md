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

The user clarified the implementation standard at 2026-10-17 12:02 UTC: derive
complete mechanisms from upstream source before implementing them. Do not start
with a weak approximation and accumulate special cases to satisfy tests. Source
maps and invariants guide parser/VM/data work; differential tests independently
verify the resulting semantics.

## Repository and existing evidence

- Working branch: `work/root-primary-cloud`; draft PR #1.
- Baseline delivery: `b71b31e1345d4453273ba529574eea348c654613`.
- Full capability inventory and tracked launchers: `fe62ebf841ed49b3e13f7a43b572acfbcf443be2`.
- Sonar evidence and concrete source fixes: `ad81dffdec4786bad015f309d583e0ec0b6da69e`.
- Root IDENTICAL implementation: `ecca4f8d007f7dc0eb71c19316a67542f25a6653`.
- Complete IDENTICAL evidence: `4ed874eb1e13bc21b1d28d20ef0fb1d3caa28586`.
- Tested PRIMARY source: `9e57799d39c7610bfb6a93b1e7f8a51205e5b4a7`.
- PRIMARY: 1,160,181 valid full keys, 11 expected invalid-input rejections,
  28,108 CE64 records; Linux local and clean Actions evidence passed.
- Historical Windows evidence under `docs/research/assets/icu-probe` is immutable.
- The 145 ICU4X IDENTICAL differences and original empty IDENTICAL crashes remain
  historical evidence. An independently fixed implementation does not rewrite them.
- IDENTICAL: 1,159,652 original nonempty full keys and 696 approved empty keys
  passed; 11 invalid inputs rejected as expected. Three original empty Boost
  calls actually crashed and remain separate reference errors. The 85-file
  archive is fully versioned in exact binary parts with reconstruction commands
  in `docs/research/assets/icu77-identical/README.md`.
- Clean Actions PRIMARY replay on IDENTICAL source `ecca4f8d`: run
  [39031119405](https://github.com/1298345095/BoostRegexRS/actions/runs/39031119405)
  completed successfully. This does not add six-target or full IDENTICAL CI evidence.

## Current work and ownership

- Root: full capability tracking, GitHub delivery, regex reference and independent
  complete-result comparison, Sonar evidence and CI configuration.
- `rust_primary`: complete locale/settings collation mechanisms in `primary/rust`.
- `spec_review`: ICU77 locale/type inventory, data-owner/settings export and oracle.
- `standards_review`: root byte regex parser/VM/API, `src/`, root Cargo and tests.
  Its `byte-engine-architecture.md` records the actual upstream source map and
  required internal-state refactor before broad syntax expansion.

Agents share the working tree; coordinate path ownership. Root creates commits
and updates GitHub. The environment has no `gh` executable; the connected GitHub
API performs the same authorized issue/ref operations without inventing credentials.
Issue #2 uses the canonical `ready-for-agent` label.

## Reproduction and artifact locations

```sh
python3 -B tools/dev/cargo.py test --locked
python3 -B tools/dev/update_capabilities.py
python3 -B tools/icu-probe/cloud/run.py --jobs 6
python3 -B tools/icu-probe/primary/export/generate_nfd.py --check
python3 -B tools/icu-probe/primary/run_identical.py
```

All authored scripts, minimized regressions, data generators and durable evidence
belong in tracked `tools/`, `tests/`, `src/` or `docs/` paths. `target` may retain
downloaded tool/source caches and compiled products. New test runs save reviewable
evidence outside target; large raw evidence may be compressed with the reproduction
script and digest tracked alongside it. Preserve earlier target evidence in place.

## Current external issue

SonarCloud checks 117383130668 and 117391738137 failed New Code Security Rating
(E versus A). The read-only collector is published in `023fb664`.
[Actions run 39031917149](https://github.com/1298345095/BoostRegexRS/actions/runs/39031917149)
obtained HTTP 200 from both Sonar APIs and preserved all 89 open issues, including
18 security findings with their complete flows. Raw artifact and extracted JSON
are under `docs/research/assets/sonarcloud/actions-39031917149/`.

Earlier workspace/browser CloudFront 403 responses remain historical observations;
read access from Actions now works. Two S2083 flows taint JSON *contents* and
incorrectly identify `Path.write_text` as path traversal. Other reported sources
are same-permission developer CLI paths/compiler/Cargo arguments. Review every
actual flow and the server's rule definitions before applying individual issue
dispositions. No issue has been suppressed, accepted or changed yet; the gate
still fails. A read-only access inspection will record credential presence as a
boolean, authentication validity and API/rule definitions. Public read access
does not establish permission to change issues.

The user reports installing SonarQube; the current callable-tool registry exposes
no Sonar operation, and plugin searches returned no available connection. Do not
ask for a repeat installation or invent a connection. Optional SONAR_TOKEN is
sent only to SonarCloud, never included in evidence or logs.

## Next actions

1. Finish source-to-sink Sonar review using the successful Actions evidence and
   actual rule definitions; inspect issue-management access without changing gates.
2. Complete locale/type/settings export and faithful ICU77 settings/iterator
   implementation, followed by complete-key acceptance.
3. Complete the byte parser/VM state mechanisms from the pinned upstream source;
   import applicable original test inputs and independently compare every result
   field. Keep remaining grammar, API and trait rows open until implemented.
4. Configure six native targets and fixed performance/memory workloads, retaining
   unverified status until actual results exist.

The root byte oracle is authored under `tools/regex-oracle/`. Its unchanged-source
upstream collector compiled and emitted 2,382 source cases / 6,258 operation rows;
the fixed-seed generator emitted another 13,954 rows. These are input counts,
not passes. Native-reference assertion validation, strict complete-result schema
checking and the runner are being completed before differential acceptance.
