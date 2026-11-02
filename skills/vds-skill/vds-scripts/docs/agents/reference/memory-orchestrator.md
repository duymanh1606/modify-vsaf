<!-- diátaxis: reference -->

# Memory Orchestrator

> Search, store, and recall cross-session knowledge and observations.

## Scope

- **Does:** Semantic search across memory store, store new observations, recall prior decisions.
- **Does NOT:** Replace git history, store large binary artifacts.
- **Primary users:** AI agents (context retrieval), human operators (decision archaeology).

## CLI Entry

```bash
# Via unified router
vds-cli memory --help

# Direct entry
vds-cli memory --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `search` | Semantic search | `--limit`, `--tool` |
| `store` | Store observation | `--tag`, `--priority` |
| `recall` | Recall by ID or tag | `--id` |
| `health` | Check memory store health | — |

## Common Workflows

### Workflow: Research with Memory Recall

1. Search prior work: `vds-cli memory search "MCP protocol" --limit 5`
2. Review stored observations
3. Store new findings: `vds-cli memory store --tag "mcp-research-2026"`
4. Cross-reference with current task

## Related

- **Orchestrators:** [research](research-orchestrator.md), [audit](audit-triage-playbook.md)
- **Skills:** [memory-orchestrator-skill](../../../../vds-skills/skills/memory-orchestrator-skill/SKILL.md)
- **Confluence:** [WHO Memory](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
