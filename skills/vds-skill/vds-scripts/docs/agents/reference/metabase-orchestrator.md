<!-- diátaxis: reference -->

# Metabase Orchestrator

> Metabase analytics and dashboard operations — query questions, export results, inspect collections.

## Scope

- **Does:** Query Metabase questions, export results, inspect collections, and manage dashboard subscriptions.
- **Does NOT:** Build new dashboards, replace Metabase UI, or manage permissions.
- **Primary users:** AI agents (data retrieval), analysts, product managers.

## CLI Entry

```bash
# Via unified router
vds-cli metabase --help

# Direct entry
vds-cli metabase --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `query` | Run Metabase question | `--question-id`, `--format` |
| `export` | Export question results | `--question-id`, `--output` |
| `collection` | List collection contents | `--collection-id` |
| `subscribe` | Manage dashboard subscriptions | `--dashboard-id`, `--action` |

## Common Workflows

### Workflow: Export Weekly Metrics

1. Run `vds-cli metabase query --question-id 123 --format csv`
2. Save output: `--output weekly-metrics.csv`
3. Share with stakeholders

## Related

- **Orchestrators:** [grafana](grafana-orchestrator.md), [elastic](elastic-orchestrator.md), [db-query](db-query-orchestrator.md)
- **Confluence:** [WHO Metabase](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
