<!-- diátaxis: how-to -->

# Research → Spec → Audit Workflow

> Combine the research, spec, and audit orchestrators to gather evidence, formalize requirements, and validate implementation.

## Prerequisites

- `vds-scripts` cloned and bootstrapped (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` passes
- Target repo(s) accessible via Bitbucket
- `~/.vds/.env` contains `VDS_USERNAME`, `VDS_PASSWORD`, and `OPENAI_API_KEY`

## Workflow Overview

```
research (gather evidence)
    ↓
spec (create/validate spec)
    ↓
audit (execute validation)
```

## Step 1: Gather Evidence with Research

Run a targeted research query to collect evidence for the feature or gap you need to address.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli research search "hexagonal architecture compliance patterns"
```

Expected output:

```
[research] Query: hexagonal architecture compliance patterns
[research] Sources found: 12
[research] Top result: https://example.com/hexagonal-guide
[research] Evidence saved to: /tmp/vds-research-evidence-<timestamp>.json
```

Score the evidence quality before proceeding:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli research score --evidence /tmp/vds-research-evidence-<timestamp>.json
```

Expected output:

```
[score] Total evidence items: 12
[score] High quality: 8
[score] Medium quality: 3
[score] Low quality: 1
[score] Average score: 0.78
```

## Step 2: Create or Validate a Spec

Use the spec orchestrator to create a new spec from the research evidence.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli spec create hexagonal-compliance --evidence /tmp/vds-research-evidence-<timestamp>.json
```

Expected output:

```
[spec] Created: .gpt-5.4/specs/hexagonal-compliance/requirements.md
[spec] Created: .gpt-5.4/specs/hexagonal-compliance/design.md
[spec] Created: .gpt-5.4/specs/hexagonal-compliance/tasks.md
[spec] Next: run validation
```

Validate the spec triplet:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli spec validate --spec-dir .gpt-5.4/specs/hexagonal-compliance
```

Expected output:

```
[validate] requirements.md: PASS
[validate] design.md: PASS
[validate] tasks.md: PASS
[validate] 3/3 files valid
```

Run alignment checks:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli spec check-alignment --spec-dir .gpt-5.4/specs/hexagonal-compliance
```

## Step 3: Execute Audit Validation

Run the audit orchestrator against the target repo using the validated spec.

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit run --repo vds-scripts --scope full --spec hexagonal-compliance
```

Expected output:

```
[audit] Profile: default
[audit] Scope: full
[audit] Spec: hexagonal-compliance
[audit] Rules: 47
[audit] Violations: 3
[audit] Report: /tmp/vds-audit-report-<timestamp>.json
```

Generate a consolidated report:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli research report --evidence /tmp/vds-research-evidence-<timestamp>.json \
  --audit /tmp/vds-audit-report-<timestamp>.json
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `research search` returns zero results | MCP router unavailable or Tavily quota exhausted | Run `vds-cli research health` to diagnose |
| `spec validate` fails with missing FR | requirements.md has gaps | Add missing functional requirements and re-run |
| `audit run` fails with `--spec not found` | Spec name mismatch | Use exact spec directory name, or omit `--spec` for default |
| `check-alignment` reports drift | Design and tasks are out of sync | Run `vds-cli spec consolidate` then re-check |
