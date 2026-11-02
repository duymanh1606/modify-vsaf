<!-- diátaxis: reference -->

# Multi-Agent Orchestrator

> Coordinate multiple AI agents for complex parallel tasks.

## Scope

- **Does:** Dispatch tasks to agent teams, aggregate results, manage conflicts, and track team progress.
- **Does NOT:** Replace individual agent decision-making, guarantee consensus, or manage human teams.
- **Primary users:** AI agents (team coordination), human leads (oversight), complex task runners.

## CLI Entry

```bash
# Via unified router
vds-cli multi-agent --help

# Direct entry
vds-cli multi-agent --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `dispatch` | Dispatch task to agents | `--task`, `--agents`, `--strategy` |
| `aggregate` | Aggregate agent results | `--run-id`, `--method` |
| `resolve` | Resolve conflicts | `--run-id`, `--strategy` |
| `status` | Check team status | `--run-id` |

## Common Workflows

### Workflow: Parallel Code Review

1. Dispatch review tasks: `vds-cli multi-agent dispatch --task "review PR #123" --agents reviewer-1,reviewer-2,reviewer-3`
2. Wait for completion
3. Aggregate results: `vds-cli multi-agent aggregate --run-id <id> --method consensus`
4. Resolve conflicts if reviewers disagree

## Related

- **Orchestrators:** [audit](audit-triage-playbook.md), [evolution](evolution-orchestrator.md), [tasks](tasks-orchestrator.md)
- **Confluence:** [WHO Multi-Agent](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
