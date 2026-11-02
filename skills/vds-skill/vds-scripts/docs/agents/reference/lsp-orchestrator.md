<!-- diátaxis: reference -->

# LSP Orchestrator

> Language Server Protocol operations for code intelligence.

## Scope

- **Does:** Manage LSP servers, query symbols, navigate to definitions, and get hover information.
- **Does NOT:** Replace IDE features, manage server lifecycles beyond VDS scope, or handle LSP extensions.
- **Primary users:** AI agents (code analysis), developers (navigation), tooling teams.

## CLI Entry

```bash
# Via unified router
vds-cli lsp --help

# Direct entry
vds-cli lsp --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `symbol` | Query workspace symbols | `--query` |
| `navigate` | Navigate to definition | `--file`, `--line`, `--column` |
| `hover` | Get hover information | `--file`, `--line`, `--column` |
| `server` | Manage LSP server | `--action`, `--language` |

## Common Workflows

### Workflow: Find Symbol Definition

1. Run `vds-cli lsp symbol --query "MyClass"`
2. Get file/line/column from results
3. Navigate: `vds-cli lsp navigate --file path.py --line 10 --column 5`

## Related

- **Orchestrators:** [intellij](intellij-orchestrator.md), [code-review](code-review-graph-skill.md), [structure](structure-orchestrator.md)
- **Confluence:** [WHO LSP](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
