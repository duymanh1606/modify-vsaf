<!-- diátaxis: reference -->

# Excel Orchestrator

> Excel file processing and report generation.

## Scope

- **Does:** Read/write Excel files, format cells, generate reports from templates, and convert between formats.
- **Does NOT:** Replace Excel UI, edit complex formulas, or manage Excel add-ins.
- **Primary users:** AI agents (report generation), operators (data export), finance teams.

## CLI Entry

```bash
# Via unified router
vds-cli excel --help

# Direct entry
vds-cli excel --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `read` | Read Excel file | `--input`, `--sheet` |
| `write` | Write Excel file | `--output`, `--data` |
| `template` | Generate from template | `--template`, `--data`, `--output` |
| `convert` | Convert to CSV/JSON | `--input`, `--format` |

## Common Workflows

### Workflow: Generate Report from Template

1. Prepare data as JSON
2. Run `vds-cli excel template --template report.xlsx --data data.json --output report-filled.xlsx`
3. Review and distribute

## Related

- **Orchestrators:** [google-sheets](google-sheets-orchestrator.md), [pdf](pdf-orchestrator.md)
- **Confluence:** [WHO Excel](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
