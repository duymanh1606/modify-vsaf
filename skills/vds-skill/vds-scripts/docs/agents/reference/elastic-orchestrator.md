<!-- diátaxis: reference -->

# Elasticsearch Orchestrator

> Elasticsearch operations via Kibana proxy — query indices, inspect mappings, run aggregations.

## Scope

- **Does:** Query ES indices, inspect mappings, run aggregations, export results, and manage index aliases.
- **Does NOT:** Manage cluster topology, replace Kibana UI, or handle index lifecycle policies.
- **Primary users:** AI agents (log analysis), operators (metric queries), SRE (incident response).

## CLI Entry

```bash
# Via unified router
vds-cli elastic --help

# Direct entry
vds-cli elastic --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `query` | Run ES query | `--index`, `--query`, `--format` |
| `mapping` | Inspect index mapping | `--index` |
| `aggregate` | Run aggregation | `--index`, `--agg` |
| `alias` | Manage index aliases | `--action`, `--alias` |

## Common Workflows

### Workflow: Query Application Logs

1. Run `vds-cli elastic query --index app-logs-* --query '{"match": {"level": "ERROR"}}'`
2. Filter by time range: add `--from 2026-04-01 --to 2026-04-22`
3. Export results: `--format json --output errors.json`

### Workflow: Inspect Index Mapping

1. Run `vds-cli elastic mapping --index my-index`
2. Review field types and analyzers
3. Compare with expected schema

## Related

- **Orchestrators:** [grafana](grafana-orchestrator.md), [db-query](db-query-orchestrator.md), [metabase](metabase-orchestrator.md)
- **Confluence:** [WHO Elastic](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
