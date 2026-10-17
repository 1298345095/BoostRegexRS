# Planning provenance and review decisions

The user paused implementation on 2026-10-17 and requested the remaining work
as tickets using `to-tickets`. These five draft files preserve the independent
lane analyses. They are planning inputs, **not the canonical execution backlog**:
some retain unresolved lane placeholders, stale checkpoint wording or proposals
which the final review changed. Read `../backlog.json`, `../issues/` and the
published GitHub issues for the reviewed requirements.

## Reproduce the reviewed backlog

```sh
python3 -B tools/dev/assemble_ticket_backlog.py
python3 -B tools/dev/ticket_backlog.py check
python3 -B tools/dev/ticket_backlog.py render
```

The assembly contains explicit cross-lane dependency mappings and reviewed
overrides. It does not run, test or edit the library. The audit checks all 406
existing capability rows without changing their status. The 73 upstream source
files each have one full-file applicability/port/test owner in V04–V10; narrower
mechanism tickets may also own specific assertions from the same file.

## Accepted review changes

- Preserve root PRIMARY/IDENTICAL as existing research prerequisites; remaining
  tickets integrate and verify them in the production library rather than
  reopening their completed implementation stages.
- Keep byte grammar/VM work split by source-defined mechanism and public
  behavior. Every slice has independent reference partitions, complete observable
  results and its own implementation/documentation/evidence obligations.
- Expand the generic input/rules seam first, migrate each input representation,
  then contract duplicate ownership. Native-wide expansion uses deterministic
  custom rules before platform providers, avoiding a wide-input/backend cycle.
- Split Darwin and Windows C rules from their C++ standard-library backends.
  Add explicit custom locale lifecycle and syntax/escape/numeric extension
  hooks. Byte and native-wide POSIX-equivalent APIs have separate delivery scopes.
- The Unicode traits facade precedes UTF adapters. Its callable length operation
  distinguishes terminator-based length from NUL-preserving explicit ranges.
  UTF-32 regex inputs retain their own source-defined domain instead of borrowing
  sort-key decoder rejection rules. Locale parsing preserves native accepted
  partial parsing, truncation and fallback. Error positions are required where
  the source/API exposes them; no nonexistent probe position evidence is invented.
- U01 owns the known UTF-16 FCD cursor/replay repair; U02 owns all-owner scalar,
  context and CE/key acceptance; U03 owns the 538-configuration settings matrix.
  Boost combining-sequence and line behavior follows its fixed source helpers,
  not a replacement modern grapheme algorithm.
- Fold draft U27 into V15 and V21–V26, and draft U28 into V36. Their Unicode
  operation, malformed-input, sharing, full-output and performance obligations
  remain explicit; there is no duplicate six-platform acceptance system.
- Native reference setup P03–P08 precedes platform providers and locale defaults.
  Whole-library platform acceptance follows complete package assembly. This
  avoids depending on a final package CI gate to implement a prerequisite.
- Freeze measurement protocol V27 before full package completion. Actual host
  suitability must be measured; no paid host or presumed missing infrastructure
  is invented as a product requirement. Each workload retains the ADR thresholds.
- Sonar work consists of actual connection/authority discovery, issue-specific
  fixes/dispositions and the exact-candidate remote gate. V38 supplies reproducible
  whole-library local/CI checks; it does not require a paid feature or a forced
  Rust-capable Sonar migration. V43 reruns those checks on the final candidate.
- Each feature owns its public documentation/examples. V40 audits the assembled
  documentation and executes examples; missing substantial work becomes a
  bounded blocker rather than an unbounded final documentation rewrite.

## Publication and pause

The user's request authorizes ticket creation and ordinary sizing/order choices.
The skill's granularity review was performed through explicit scope, dependency
and independent review checks; no additional approval gate is introduced. GitHub
Issues are the repository's canonical tracker. The connected toolset has issue
creation but no native dependency mutation, and `gh` is unavailable. Every issue
therefore uses the repository's documented `Blocked by: #...` fallback and is
created after its blockers. Unblocked tickets receive `ready-for-agent`.

Parent issue #2 is left open and unchanged. The latest pause overrides its older
automatic-continuation text. Neither the readiness label nor finishing this
planning task authorizes restarting implementation. The source/evidence
checkpoint is preservation, not a verified implementation commit.
