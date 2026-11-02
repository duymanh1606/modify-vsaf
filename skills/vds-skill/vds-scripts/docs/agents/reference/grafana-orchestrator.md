<!-- diátaxis: reference -->

# Grafana Orchestrator

> Grafana logs and metrics operations — query logs, fetch dashboards, check alerts.

## Scope

- **Does:** Query logs via Loki, fetch dashboards, check alert status, export panel data.
- **Does NOT:** Manage Grafana users, replace Grafana UI, or create new dashboards.
- **Primary users:** AI agents (log analysis), operators (incident response), SRE.

## CLI Entry

```bash
# Via unified router
vds-cli grafana --help

# Direct entry
vds-cli grafana --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `logs` | Query logs via Loki | `--query`, `--from`, `--to` |
| `dashboard` | Fetch dashboard JSON | `--uid` |
| `alert` | Check alert status | `--state` |
| `panel` | Export panel data | `--dashboard`, `--panel` |

## Common Workflows

### Workflow: Investigate Production Incident

1. Query error logs: `vds-cli grafana logs --query '{app="api"} |= "ERROR"'`
2. Narrow time window: `--from 2026-04-22T10:00:00Z --to 2026-04-22T11:00:00Z`
3. Check related alerts: `vds-cli grafana alert --state firing`
4. Export panel metrics for correlation

## Related

- **Orchestrators:** [elastic](elastic-orchestrator.md), [db-query](db-query-orchestrator.md), [metabase](metabase-orchestrator.md)
- **Confluence:** [WHO Grafana](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
