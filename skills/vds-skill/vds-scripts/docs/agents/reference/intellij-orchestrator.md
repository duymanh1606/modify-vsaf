<!-- diátaxis: reference -->

# IntelliJ Orchestrator

> IntelliJ IDEA plugin operations and project configuration.

## Scope

- **Does:** Manage IDE settings, run inspections, generate run configurations, and sync project structure.
- **Does NOT:** Replace IDE UI, manage licenses, or handle plugin marketplace operations.
- **Primary users:** Developers (IDE automation), DevOps (standardized configs).

## CLI Entry

```bash
# Via unified router
vds-cli intellij --help

# Direct entry
vds-cli intellij --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `inspect` | Run code inspections | `--profile`, `--output` |
| `config` | Generate run configuration | `--type`, `--output` |
| `sync` | Sync project structure | `--path` |

## Common Workflows

### Workflow: Run Inspections in CI

1. Run `vds-cli intellij inspect --profile default --output inspection-results.xml`
2. Parse results for violations
3. Fail build if critical issues found

## Related

- **Orchestrators:** [lsp](lsp-orchestrator.md), [structure](structure-orchestrator.md)
- **Confluence:** [WHO IntelliJ](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
