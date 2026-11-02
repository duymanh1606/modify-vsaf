<!-- diátaxis: reference -->

# Progress Orchestrator

> Report and visualize progress across VDS phases and audit lanes.

## Scope

- **Does:** Generate progress reports, track completion metrics, visualize phase status.
- **Does NOT:** Execute audits, modify task state directly.
- **Primary users:** Human leads (status review), AI agents (self-reporting).

## CLI Entry

```bash
# Via unified router
vds-cli progress --help

# Direct entry
vds-cli progress --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `report` | Generate progress report | `--phase`, `--lane` |
| `summary` | One-line status summary | `--format` |
| `visualize` | ASCII or HTML timeline | `--output` |

## Common Workflows

### Workflow: Phase Progress Check

1. Run `vds-cli progress report --phase 174`
2. Review completion percentages per wave
3. Identify blocked tasks
4. Export for standup: `vds-cli progress summary --format markdown`

## Related

- **Orchestrators:** [tasks](tasks-orchestrator.md), [audit](audit-triage-playbook.md), [spec](spec-orchestrator.md)
- **Confluence:** [WHO Progress](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
