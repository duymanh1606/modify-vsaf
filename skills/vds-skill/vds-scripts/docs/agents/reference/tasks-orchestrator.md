<!-- diátaxis: reference -->

# Tasks Orchestrator

> Manage and track tasks across VDS phases and work packages.

## Scope

- **Does:** Create tasks, update status, track completion, generate task reports.
- **Does NOT:** Replace Jira for complex project management, auto-assign tasks.
- **Primary users:** AI agents (task tracking), human leads (progress review).

## CLI Entry

```bash
# Via unified router
vds-cli tasks --help

# Direct entry
vds-cli tasks --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `list` | List active tasks | `--phase`, `--status` |
| `create` | Create new task | `--title`, `--owner` |
| `update` | Update task status | `--id`, `--status` |
| `report` | Generate task report | `--format` |

## Common Workflows

### Workflow: Track Phase Tasks

1. Run `vds-cli tasks list --phase 174` to see active tasks
2. Update task status: `vds-cli tasks update --id ORCH-001 --status in_progress`
3. Mark complete: `vds-cli tasks update --id ORCH-001 --status completed`
4. Generate report: `vds-cli tasks report --phase 174`

## Related

- **Orchestrators:** [spec](spec-orchestrator.md), [progress](progress-orchestrator.md), [audit](audit-triage-playbook.md)
- **Skills:** [cli-development-skill](../../../../vds-skills/skills/cli-development-skill/SKILL.md)
- **Confluence:** [WHO Tasks](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
