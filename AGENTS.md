## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the canonical labels `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: root `GLOSSARY.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Command execution

Show the concrete command before execution. Set a finite wall-clock timeout
appropriate to the operation and keep long commands observable with logs and
progress updates. In the Linux development shell, use GNU `timeout`, for example:

```sh
timeout --signal=TERM --kill-after=5s 20s git status --short
timeout --signal=TERM --kill-after=10s 300s python3 -B tools/dev/cargo.py test --locked
```

Exit 124 means the deadline expired; 137 means forced termination. Preserve the
output and diagnose the cause before retrying. A timeout is never a passing test.
Use the platform's equivalent deadline for native CI commands. Keep commits
scoped to one verified change; GitHub Issues own task descriptions and status.
