#!/usr/bin/env python3
"""Validate and render the paused, dependency-linked development backlog."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "docs/development/tickets"
REPOSITORY = "https://github.com/1298345095/BoostRegexRS"
BRANCH_FILES = REPOSITORY + "/blob/work/root-primary-cloud/"
OPTIONAL_SECTIONS = (
    ("notes", "Detailed notes"),
    ("source_symbols", "Source symbols and mechanism boundaries"),
    ("validation_partitions", "Validation partitions"),
)


def load_records():
    backlog = json.loads((STORE / "backlog.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (ROOT / "docs/development/capability-matrix.json").read_text(encoding="utf-8")
    )
    publication_file = STORE / "published.json"
    published = (
        json.loads(publication_file.read_text(encoding="utf-8"))
        if publication_file.exists()
        else {}
    )
    return backlog, matrix, published


def validate_string_list(ticket, field, *, required=False):
    values = ticket.get(field, [])
    if (
        not isinstance(values, list)
        or (required and not values)
        or not all(isinstance(item, str) and item.strip() for item in values)
    ):
        raise ValueError(f"{ticket['id']}: {field} must be a list of nonempty strings")


def body_sha256(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def validate(backlog, matrix, published):
    tickets = backlog["tickets"]
    by_id = {ticket["id"]: ticket for ticket in tickets}
    if len(by_id) != len(tickets):
        raise ValueError("Duplicate ticket IDs")
    capabilities = {row["id"] for row in matrix["capabilities"]}
    if len(capabilities) != len(matrix["capabilities"]):
        raise ValueError("Duplicate capability IDs")
    owners = {capability: [] for capability in capabilities}
    for ticket in tickets:
        identity = ticket["id"]
        for field in ("title", "workstream", "problem", "current_state", "sizing"):
            if not isinstance(ticket.get(field), str) or not ticket[field].strip():
                raise ValueError(f"{identity}: missing {field}")
        for field in ("deliverables", "acceptance", "source_refs"):
            validate_string_list(ticket, field, required=True)
        for field in ("blocked_by", "capabilities", "external_dependencies"):
            validate_string_list(ticket, field)
        for field, _ in OPTIONAL_SECTIONS:
            validate_string_list(ticket, field)
        if len(ticket["acceptance"]) < 3:
            raise ValueError(f"{identity}: fewer than three acceptance checks")
        if ticket.get("external_dependencies"):
            raise ValueError(f"{identity}: unresolved external dependency names")
        if len(ticket["blocked_by"]) != len(set(ticket["blocked_by"])):
            raise ValueError(f"{identity}: duplicate dependency")
        for blocker in ticket["blocked_by"]:
            if blocker not in by_id or blocker == identity:
                raise ValueError(f"{identity}: invalid blocker {blocker}")
        for capability in ticket["capabilities"]:
            if capability not in owners:
                raise ValueError(f"{identity}: unknown capability {capability}")
            owners[capability].append(identity)
        if len(ticket["capabilities"]) != len(set(ticket["capabilities"])):
            raise ValueError(f"{identity}: duplicate capability ownership")
    missing = sorted(key for key, value in owners.items() if not value)
    if missing:
        raise ValueError("Unowned capability rows: " + ", ".join(missing))
    ordered = []
    remaining = list(by_id)
    while remaining:
        ready = [
            identity
            for identity in remaining
            if set(by_id[identity]["blocked_by"]).issubset(ordered)
        ]
        if not ready:
            raise ValueError("Dependency cycle: " + ", ".join(remaining))
        ordered.extend(ready)
        remaining = [identity for identity in remaining if identity not in ready]
    final = backlog["final_acceptance_ticket"]
    if final not in by_id:
        raise ValueError(f"Unknown final acceptance ticket {final}")
    closure = set()

    def visit(identity):
        if identity in closure:
            return
        closure.add(identity)
        for blocker in by_id[identity]["blocked_by"]:
            visit(blocker)

    visit(final)
    if closure != set(by_id):
        raise ValueError("Tickets outside final gate: " + ", ".join(sorted(set(by_id) - closure)))
    upstream_rows = {key for key in capabilities if key.startswith("upstream_test.")}
    assignments = backlog.get("upstream_file_ownership", [])
    assigned_ids = [item["capability_id"] for item in assignments]
    if len(assigned_ids) != len(set(assigned_ids)) or set(assigned_ids) != upstream_rows:
        raise ValueError("Every upstream file must have exactly one full-file owner")
    for assignment in assignments:
        owner = assignment["applicability_owner_ticket"]
        if owner not in by_id or assignment["capability_id"] not in by_id[owner]["capabilities"]:
            raise ValueError("Upstream owner does not own its capability row")
        if assignment["port_owner_ticket"] != owner or assignment["test_owner_ticket"] != owner:
            raise ValueError("Upstream full-file applicability, port and test ownership diverge")
    seen_numbers = set()
    for identity, record in published.items():
        if identity != "_index" and identity not in by_id:
            raise ValueError(f"Published unknown ticket {identity}")
        number = record["number"]
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise ValueError(f"{identity}: invalid issue number")
        if number in seen_numbers or number == backlog["parent_issue"]:
            raise ValueError("Duplicate or parent publication number")
        seen_numbers.add(number)
        if record["url"] != f"{REPOSITORY}/issues/{number}":
            raise ValueError(f"{identity}: unexpected issue URL")
        if identity == "_index":
            continue
        if not set(by_id[identity]["blocked_by"]).issubset(published):
            raise ValueError(f"{identity}: published before its blockers")
        if any(published[key]["number"] >= number for key in by_id[identity]["blocked_by"]):
            raise ValueError(f"{identity}: blocker issue was not created first")
        expected_body = issue_body(by_id[identity], published)
        expected_hash = body_sha256(expected_body)
        if record["body_sha256"] != expected_hash:
            raise ValueError(f"{identity}: local ticket differs from published body")
    if "_index" in published:
        expected_index = index_body(backlog, published, [by_id[key] for key in ordered], owners)
        if published["_index"]["body_sha256"] != body_sha256(expected_index):
            raise ValueError("Local tracker index differs from its published body")
    return [by_id[identity] for identity in ordered], owners


def issue_link(identity, published):
    if identity in published:
        record = published[identity]
        return f"[#{record['number']}]({record['url']})"
    return f"`{identity}`"


def code_location(value):
    fence = "`"
    while fence in value:
        fence += "`"
    padding = " " if value.startswith("`") or value.endswith("`") else ""
    return f"{fence}{padding}{value}{padding}{fence}"


def is_web_reference(reference):
    return reference.lower().startswith(("https://", "http://"))


def issue_body(ticket, published):
    blockers = ", ".join(issue_link(key, published) for key in ticket["blocked_by"])
    if not blockers:
        blockers = "None (specified and unblocked; implementation remains paused)."
    lines = [
        "Part of #2. Implementation is paused at the user's request; this ticket records remaining work.",
        "",
        f"**Ticket:** `{ticket['id']}` · **Workstream:** {ticket['workstream']}",
        "",
        f"**Blocked by:** {blockers}",
        "",
        "## Outcome and reason",
        "",
        ticket["problem"],
        "",
        "## Starting state",
        "",
        ticket["current_state"],
        "",
        "Published source baseline: `1b0149efb649bcec7b5d6c4c0be2f7e403189cea`. "
        "Paused implementation sources are preserved separately in the "
        f"[checkpoint]({BRANCH_FILES}docs/development/tickets/checkpoint/README.md). "
        "Restore them in an isolated checkout when resuming; an archive is not validation evidence.",
        "",
        "## Deliverable",
        "",
        *[f"- {item}" for item in ticket["deliverables"]],
        "",
        "## Acceptance",
        "",
        *[f"- [ ] {item}" for item in ticket["acceptance"]],
        "",
        "## Source contracts and evidence",
        "",
    ]
    if any(not is_web_reference(ref) for ref in ticket["source_refs"]):
        lines.extend(
            [
                "Non-web references below are repository or checkpoint locations, displayed "
                "as code. Resolve repository-relative paths from the restored checkout root. "
                "Some paused sources exist only inside checkpoint archives; use "
                "`docs/development/tickets/checkpoint/README.md` and its manifests to locate them.",
                "",
            ]
        )
    for reference in ticket["source_refs"]:
        if is_web_reference(reference):
            lines.append(f"- {reference}")
        else:
            lines.append(f"- {code_location(reference)}")
    for field, title in OPTIONAL_SECTIONS:
        values = ticket.get(field, [])
        if values:
            lines.extend(["", f"## {title}", ""])
            lines.extend(
                f"- {code_location(value) if field == 'source_symbols' else value}"
                for value in values
            )
    lines.extend(["", "## Capability ownership", ""])
    if ticket["capabilities"]:
        lines.extend(f"- `{capability}`" for capability in ticket["capabilities"])
    else:
        lines.append("Cross-cutting prerequisite for the explicitly linked dependent capabilities.")
    lines.extend(
        [
            "",
            "## Size and completion rule",
            "",
            ticket["sizing"],
            "",
            "The reference contract is Boost.Regex **1.89.0**, ICU4C **77.1**, Unicode "
            "**16.0.0** and CLDR **47**, with complete unfiltered ICU data. Data upgrades are "
            "explicit; a toolchain update must not change character behavior. The standalone "
            "library's default configuration must provide the full promised capability set, "
            "including Unicode, wide input and locale support. A reduced configuration must "
            "be explicit and separately documented and verified.",
            "",
            "Read the relevant pinned implementation sources and derive the complete mechanisms "
            "and invariants before changing code. Keep the runtime on stable Rust with only the "
            "OS API boundary allowed by ADR-0002 and no C/C++ or ICU library backend. Preserve "
            "original input-unit positions and all captures. Do not use input-specific answer "
            "tables, blanket input prenormalization, skipped inputs, weakened gates or unapproved "
            "compatibility exceptions. Source-defined FCD and IDENTICAL normalization remain "
            "part of their respective mechanisms.",
            "",
            "Run real, independent tests for the implemented behavior and retain reproducible "
            "commands, full results, exit statuses and source/binary/data/tool identities. "
            "Record passes, differences, approved exceptions, expected rejections, reference "
            "errors and uncovered work separately; preserve failed runs. Finite passing cases "
            "do not prove arbitrary-input correctness. Update the public API documentation and "
            "execute the relevant examples for every implemented or changed public behavior.",
            "",
            "Retain source/data licenses and publish authored tools and durable evidence outside "
            "target. When implementation resumes, use scoped, verified English commits on an "
            "independent branch. Update the "
            "capability matrix with exact evidence, not ticket closure alone. Do not close the "
            "parent, merge main, release, or integrate librime-rs. If a source/contract conflict "
            "requires a new decision, report it without silently changing the contract.",
            "",
            "Implementation and implementation-test execution remain paused until the user "
            "resumes them. Ticket publication, readiness labels and dependency completion "
            "do not resume development.",
            "",
        ]
    )
    return "\n".join(lines)


def verification_counts(ordered, owners, published):
    """Summarize a backlog that has already passed validate()."""
    return {
        "tickets": len(ordered),
        "dependency_edges": sum(len(ticket["blocked_by"]) for ticket in ordered),
        "final_gate_reachable_tickets": len(ordered),
        "capability_rows": len(owners),
        "capability_ownership_assignments": sum(len(value) for value in owners.values()),
        "shared_capability_rows": sum(len(value) > 1 for value in owners.values()),
        "upstream_test_rows": sum(key.startswith("upstream_test.") for key in owners),
        "published_ticket_body_hashes_verified": sum(
            ticket["id"] in published for ticket in ordered
        ),
    }


def readme_body(backlog, published, ordered, owners):
    verification = verification_counts(ordered, owners, published)
    counts = Counter(ticket["workstream"] for ticket in ordered)
    ready = [ticket for ticket in ordered if not ticket["blocked_by"]]
    index_lines = (
        [f"Backlog index issue: {issue_link('_index', published)}.", ""]
        if "_index" in published
        else []
    )
    lines = [
        "# Remaining development tickets",
        "",
        "**Implementation is paused by the user.** This backlog was authored with `to-tickets` "
        "after stopping implementation and test work. Readiness labels describe specification "
        "and dependency readiness; they do not resume development.",
        "",
        f"Parent: [#{backlog['parent_issue']}]"
        f"({REPOSITORY}/issues/{backlog['parent_issue']}), left open and unchanged. "
        "The full-library acceptance contract remains ADR-0001 through ADR-0005; "
        "librime-rs integration, release publication and merging main remain outside this task.",
        "",
        *index_lines,
        f"The backlog contains **{len(ordered)} bounded tickets**, with **{len(ready)} currently "
        f"unblocked**. All **{len(owners)} capability rows** have ticket ownership. "
        "Ownership does not promote implementation or validation status.",
        "",
        "## Dependency and coverage verification",
        "",
        "The validator resolved every dependency, rejected cycles and confirmed that every "
        "ticket is included in the prerequisite closure of final acceptance ticket "
        f"{issue_link(backlog['final_acceptance_ticket'], published)}.",
        "",
        "| Check | Verified count |",
        "| --- | ---: |",
        f"| Explicit dependency edges | {verification['dependency_edges']} |",
        f"| Tickets connected to the final gate | {len(ordered)} / {len(ordered)} |",
        f"| Capability rows with owners | {len(owners)} / {len(owners)} |",
        f"| Upstream test rows with owners | {verification['upstream_test_rows']} |",
        f"| Capability-to-ticket assignments | {verification['capability_ownership_assignments']} |",
        f"| Capability rows shared by multiple tickets | {verification['shared_capability_rows']} |",
        f"| Published ticket bodies matching exact SHA-256 | {verification['published_ticket_body_hashes_verified']} |",
        "",
        "The [paused checkpoint](checkpoint/README.md) preserves 629 existing source/data files "
        "over commit `1b0149ef`. Root PRIMARY and IDENTICAL have committed reference evidence. "
        "The current byte and locale work is a separate unfinished checkpoint, including an "
        "unbuilt FCD correction and two preserved differences. Six native research-crate jobs "
        "passed 19 tests each; full-library platform and performance acceptance is still open.",
        "",
        "## Workstreams",
        "",
        "| Workstream | Tickets |",
        "| --- | ---: |",
        *[f"| {name} | {count} |" for name, count in counts.items()],
        "",
        "## Ready frontier after the user resumes",
        "",
        *[f"- {issue_link(ticket['id'], published)} `{ticket['id']}` — {ticket['title']}" for ticket in ready],
        "",
        "## Dependency-ordered tickets",
        "",
        "Dependencies are explicit `Blocked by` links in every issue. The connected GitHub "
        "toolset does not expose native dependency mutations and `gh` is unavailable, so this "
        "uses the documented repository fallback rather than claiming native dependency edges.",
        "",
        "| ID | Ticket | Blocked by |",
        "| --- | --- | --- |",
    ]
    for ticket in ordered:
        blockers = ", ".join(issue_link(key, published) for key in ticket["blocked_by"]) or "None"
        title = f"[{ticket['title']}](issues/{ticket['id']}.md)"
        lines.append(f"| {ticket['id']} {issue_link(ticket['id'], published)} | {title} | {blockers} |")
    lines.extend(
        [
            "",
            "## Reproduce the backlog audit",
            "",
            "```sh",
            "python3 -B tools/dev/ticket_backlog.py check",
            "python3 -B tools/dev/ticket_backlog.py render",
            "```",
            "",
            "The audit rejects missing/duplicate IDs, unknown or cyclic dependencies, unresolved "
            "dependency names, unowned capability rows and tickets that cannot reach the final "
            "acceptance gate. Publication IDs are recorded in `published.json`; it also verifies "
            "that blocker issues were created first and their exact rendered UTF-8 body hashes "
            f"still match. [Coverage](coverage.md) maps all {len(owners)} rows "
            "without changing their prior status.",
            "",
            "Each ticket includes the checkpoint state, source contracts, implementation and "
            "independent verification deliverables, binary acceptance criteria and a bounded "
            "scope. Broad input migration uses expand, per-encoding migration, then contract. "
            "If a new mechanism is discovered beyond a ticket's bounded scope, add a linked "
            "follow-up before closure; never drop the remaining requirement.",
            "",
        ]
    )
    return "\n".join(lines)


def render(backlog, matrix, published, ordered, owners):
    issue_dir = STORE / "issues"
    issue_dir.mkdir(exist_ok=True)
    for ticket in ordered:
        (issue_dir / f"{ticket['id']}.md").write_text(
            f"# [{ticket['id']}] {ticket['title']}\n\n" + issue_body(ticket, published),
            encoding="utf-8",
        )
    (STORE / "README.md").write_text(
        readme_body(backlog, published, ordered, owners), encoding="utf-8"
    )
    coverage_lines = [
        "# Capability-to-ticket ownership",
        "",
        "The status column is the unchanged capability-matrix snapshot at ticket creation. "
        "Tickets record remaining implementation, integration or acceptance work; none is a pass.",
        "",
        "| Capability | Existing status | Responsible tickets |",
        "| --- | --- | --- |",
    ]
    coverage = []
    for row in matrix["capabilities"]:
        identities = sorted(set(owners[row["id"]]))
        coverage.append({"capability": row["id"], "existing_status": row["status"], "tickets": identities})
        links = ", ".join(f"[{key}](issues/{key}.md) {issue_link(key, published)}" for key in identities)
        coverage_lines.append(f"| `{row['id']}` | {row['status']} | {links} |")
    (STORE / "coverage.md").write_text("\n".join(coverage_lines) + "\n", encoding="utf-8")
    (STORE / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    if len([key for key in published if not key.startswith("_")]) == len(ordered):
        (STORE / "index.md").write_text(index_body(backlog, published, ordered, owners), encoding="utf-8")


def index_body(backlog, published, ordered, owners):
    """Render the tracker index without depending on its own issue number."""
    if any(ticket["id"] not in published for ticket in ordered):
        raise ValueError("Publish every child ticket before the index")
    counts = Counter(ticket["workstream"] for ticket in ordered)
    ready = [ticket for ticket in ordered if not ticket["blocked_by"]]
    edges = sum(len(ticket["blocked_by"]) for ticket in ordered)
    lines = [
        "Part of #2. **Implementation is paused at the user's request.** This index records the "
        "remaining work using `to-tickets`; publishing tickets does not resume implementation.",
        "",
        f"The backlog contains **{len(ordered)} bounded tickets**, owns all **{len(owners)} existing "
        f"capability rows**, and has **{edges} explicit dependency links**. All tickets reach "
        f"the final acceptance gate {issue_link(backlog['final_acceptance_ticket'], published)}. "
        "Each of the 73 upstream source files has one full-file applicability, port and test owner.",
        "",
        "## Contract and current boundary",
        "",
        "The complete standalone pure Rust Boost.Regex 1.89.0 contract remains unchanged: "
        "ICU4C 77.1 / Unicode 16.0.0 / CLDR 47 data, stable Rust, full default capability, "
        "all captures and original positions, ADR errors/resources/sharing, six actual native "
        "targets, per-workload time/memory limits, public documentation and clean-checkout acceptance. "
        "Only ADR-approved compatibility exceptions apply. Main merge, release publication and "
        "librime-rs integration remain outside the work.",
        "",
        "Root PRIMARY/IDENTICAL research evidence is retained as an existing prerequisite. "
        "The byte engine and locale work are unfinished checkpoints, including two preserved "
        "locale full-key differences and an unbuilt/untested FCD repair. Six native research "
        "jobs passed 19 tests each; they do not establish whole-library or performance acceptance. "
        "Sonar's actual remote quality gate remains an explicit outstanding requirement.",
        "",
        f"Repository index: [README]({BRANCH_FILES}docs/development/tickets/README.md). "
        f"Full capability ownership: [coverage]({BRANCH_FILES}docs/development/tickets/coverage.md). "
        f"Paused source/evidence: [checkpoint]({BRANCH_FILES}docs/development/tickets/checkpoint/README.md). "
        f"Persistent continuation: [handoff]({BRANCH_FILES}docs/development/handoff.md).",
        "",
        "## Workstreams",
        "",
        "| Workstream | Tickets |",
        "| --- | ---: |",
        *[f"| {name} | {count} |" for name, count in counts.items()],
        "",
        "## Unblocked after the user resumes",
        "",
        "`ready-for-agent` describes specification and dependency readiness only; the pause still applies.",
        "",
        *[f"- {issue_link(ticket['id'], published)} `{ticket['id']}` — {ticket['title']}" for ticket in ready],
        "",
        "## Dependency-ordered ticket list",
        "",
        "Each ticket contains its current checkpoint, source contracts, public behavior, scope, "
        "binary acceptance checklist and `Blocked by` issue links. Blockers were created first. "
        "The repository's documented text-link fallback is used because native dependency "
        "mutation is not exposed by the connected toolset. Parent #2 is open and unchanged; "
        "its older continuation text is superseded by the user's latest pause.",
        "",
    ]
    lines += [f"- [ ] {issue_link(ticket['id'], published)} **{ticket['id']}** — {ticket['title']}"
              for ticket in ordered]
    lines += [
        "", "## Reproduce the backlog audit", "", "```sh",
        "python3 -B tools/dev/assemble_ticket_backlog.py",
        "python3 -B tools/dev/ticket_backlog.py check",
        "python3 -B tools/dev/ticket_backlog.py render", "```", "",
        "The audit rejects missing ownership, unknown/cyclic dependencies, isolated tickets, "
        "duplicate publication IDs and any rendered ticket body that differs from its recorded "
        "publication hash. Ticket closure alone never promotes a capability to passed. A newly "
        "discovered mechanism or optimization needs a bounded linked blocker; the final gate "
        "stays open until the complete accepted contract is satisfied.", "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "render", "payload", "index-payload"))
    parser.add_argument("--id", dest="identity")
    args = parser.parse_args()
    backlog, matrix, published = load_records()
    ordered, owners = validate(backlog, matrix, published)
    if args.command == "render":
        render(backlog, matrix, published, ordered, owners)
    if args.command == "index-payload":
        body = index_body(backlog, published, ordered, owners)
        print(json.dumps({"id": "_index", "title": "Remaining development ticket index — implementation paused",
                          "body": body, "body_sha256": body_sha256(body), "labels": []}))
        return
    if args.command == "payload":
        ticket = next(ticket for ticket in ordered if ticket["id"] == args.identity)
        if not set(ticket["blocked_by"]).issubset(published):
            raise ValueError("Cannot publish before blockers have issue numbers")
        body = issue_body(ticket, published)
        print(json.dumps({
            "id": ticket["id"],
            "title": f"[{ticket['id']}] {ticket['title']}",
            "body": body,
            "body_sha256": body_sha256(body),
            "labels": [] if ticket["blocked_by"] else ["ready-for-agent"],
        }))
        return
    print(json.dumps({
        **verification_counts(ordered, owners, published),
        "unblocked": [ticket["id"] for ticket in ordered if not ticket["blocked_by"]],
        "published": len([key for key in published if not key.startswith("_")]),
        "dependency_graph": "acyclic; every ticket reaches final acceptance",
        "implementation_state": "paused",
    }))


if __name__ == "__main__":
    main()
