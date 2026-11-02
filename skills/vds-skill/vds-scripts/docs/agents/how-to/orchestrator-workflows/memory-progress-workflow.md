<!-- diátaxis: how-to -->

# Memory → Progress Tracking Workflow

> Store observations in VDS AI Memory, recall prior context, and generate progress reports to track phase completion.

## Prerequisites

- `vds-scripts` cloned and bootstrapped (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` passes
- `~/.vds/.env` contains memory backend credentials (Postgres DSN or local file path)

## Workflow Overview

```
memory store (save observations)
    ↓
memory recall (retrieve context)
    ↓
progress report (track completion)
```

## Step 1: Store Observations in Memory

Save key observations after each work session so they are available to future agents.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli memory store --tag "phase174,spec,fr-3" \
  --content "FR-3 requires multi-step workflow guides combining 2+ orchestrators"
```

Expected output:

```
[memory] Stored observation: obs-20260422-001
[memory] Tags: phase174, spec, fr-3
[memory] Content length: 72 characters
[memory] Timestamp: 2026-04-22T08:00:00Z
```

Store multiple observations from a batch session:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli memory store --tag "phase174,audit" \
  --content "Audit run completed with 3 violations in hexagonal-compliance rules"
```

## Step 2: Recall Prior Context

Before starting a new session, search memory for relevant prior work.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli memory search "phase174 workflow guides"
```

Expected output:

```
[memory] Query: phase174 workflow guides
[memory] Results: 2
[memory] obs-20260422-001 — phase174, spec, fr-3
[memory] obs-20260422-002 — phase174, audit
[memory] Retrieved in 0.12s
```

Recall with tag filter for narrower scope:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli memory search "fr-3" --tag spec
```

## Step 3: Generate Progress Reports

Create a progress report from stored observations and current audit state.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli progress report --phase 174 --format markdown
```

Expected output:

```
[progress] Phase: 174
[progress] Spec items: 8/12 complete
[progress] Audit violations: 3 open
[progress] Report: /tmp/vds-progress-phase174.md
```

Generate a consolidated report across multiple phases:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli progress report --phase 174,175,176 --format json
```

Track phase completion with checklist integration:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli progress checklist --phase 174 --update-status
```

Expected output:

```
[checklist] Phase: 174
[checklist] Items: 12
[checklist] Completed: 8
[checklist] Blocked: 1
[checklist] Not started: 3
[checklist] State saved to: checklist-progress.state
```

## Automation Tips

Add to your shell profile or agent hook to auto-store after each command:

```bash
vds_memory_store() {
  local tag="$1"
  local content="$2"
  ./scripts/worktree_uv.sh run --project vds_cli \
    vds-cli memory store --tag "$tag" --content "$content"
}
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `memory store` fails with auth error | Missing DSN or credentials | Check `~/.vds/.env` for `VDS_MEMORY_DSN` or local path |
| `memory search` returns empty | No matching tags or content | Broaden query or check stored tags with `memory list` |
| `progress report` shows stale data | State file not updated | Run `vds-cli progress checklist --update-status` first |
| `progress checklist` blocked item | Missing dependency or material | Check `blocked_by_materials` flag in checklist state |
| Memory operations are slow | Large observation corpus | Add `--limit 50` to search or prune old observations |
