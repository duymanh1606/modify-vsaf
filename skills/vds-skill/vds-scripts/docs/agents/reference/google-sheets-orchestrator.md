<!-- diátaxis: reference -->

# Google Sheets Orchestrator

> Google Sheets integration for VDS data export and reporting.

## Scope

- **Does:** Read/write sheets, sync data from databases, generate reports, and manage sheet permissions.
- **Does NOT:** Replace Google Sheets UI, manage Google Workspace, or handle OAuth setup.
- **Primary users:** AI agents (report generation), operators (data sync), teams needing shared dashboards.

## CLI Entry

```bash
# Via unified router
vds-cli google-sheets --help

# Direct entry
vds-cli google-sheets --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `sync` | Sync data to sheet | `--sheet-id`, `--data`, `--range` |
| `read` | Read sheet data | `--sheet-id`, `--range` |
| `export` | Export to sheet | `--sheet-id`, `--input`, `--range` |
| `clear` | Clear sheet range | `--sheet-id`, `--range` |

## Common Workflows

### Workflow: Sync Database Query to Sheet

1. Run database query: `vds-cli db-query query --sql "SELECT * FROM metrics" --format json`
2. Sync to sheet: `vds-cli google-sheets sync --sheet-id <id> --data results.json --range A1`
3. Share sheet with team

## Related

- **Orchestrators:** [excel](excel-orchestrator.md), [db-query](db-query-orchestrator.md), [metabase](metabase-orchestrator.md)
- **Confluence:** [WHO Google Sheets](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
