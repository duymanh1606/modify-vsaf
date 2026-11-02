<!-- diátaxis: how-to -->

<!-- TODO: translate — Vietnamese translation pending -->

# First Audit Run

> Step-by-step guide for running your first repository audit using the WHO-project toolchain.

## Prerequisites

- `vds-scripts` cloned and bootstrapped (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` passes
- Target repo(s) accessible via Bitbucket

## Quick Start

### 1. Discover available audit skills

```bash
cat WHO-project/vds-skills/skills/ | grep audit
```

Expected output includes `audit-orchestrator-skill`.

### 2. Load the audit skill

```bash
cat WHO-project/vds-skills/skills/audit-orchestrator-skill
```

This prints the skill's operational contract, CLI flags, and examples.

### 3. Run a single-repo audit

```bash
vds-cli audit run --repo vds-scripts --scope quick
```

- `--repo`: target repository slug
- `--scope quick`: fast pass (rules + structure, no deep analysis)
- `--scope full`: comprehensive audit (slower, more thorough)

### 4. Review results

Output is written to `audits/<timestamp>-<repo>-<scope>.md`.

```bash
cat audits/$(ls -t audits/ | head -n 1)
```

### 5. Escalate findings

If the audit surfaces issues:

```bash
# Auto-create tickets from findings
vds-cli audit escalate --from audits/<file>.md --tracker jira

# Or export as Confluence table
vds-cli audit export --format confluence --from audits/<file>.md
```

## Common Flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Show what would be audited without running |
| `--rules-only` | Skip code analysis, check rules compliance only |
| `--output-dir` | Custom output directory (default: `audits/`) |
| `--format json` | Machine-readable output instead of markdown |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `audit-orchestrator-skill not found` | Run `vds-cli skills sync --agent claude` to refresh catalog |
| `Permission denied` on Bitbucket | Check `INTERNAL_BITBUCKET_TOKEN` in `~/.vds/.env` |
| Empty audit output | Verify `--repo` slug matches Bitbucket exactly |
| Slow execution | Use `--scope quick` or `--rules-only` for faster feedback |

## Next Steps

- Read the full audit skill: `cat WHO-project/vds-skills/skills/audit-orchestrator-skill`
- Review the audit triage playbook: `docs/agents/reference/audit-triage-playbook.md`
- Run cross-repo audits: `vds-cli audit run --repo-list repos.txt --scope full`
