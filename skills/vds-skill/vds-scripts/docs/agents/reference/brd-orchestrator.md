<!-- diátaxis: reference -->

# BRD Orchestrator

> Business Requirements Document generation and validation.

## Scope

- **Does:** Generate BRDs from specs, validate requirements completeness, track sign-offs, and export to PDF/Confluence.
- **Does NOT:** Write requirements from scratch, replace product management tools, or make business decisions.
- **Primary users:** AI agents (doc generation), product owners, business analysts.

## CLI Entry

```bash
# Via unified router
vds-cli brd --help

# Direct entry
vds-cli brd --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `generate` | Generate BRD from spec | `--spec`, `--output` |
| `validate` | Validate completeness | `--input` |
| `track` | Track sign-offs | `--brd-id`, `--status` |
| `export` | Export to PDF/Confluence | `--input`, `--format` |

## Common Workflows

### Workflow: Generate BRD from Spec

1. Ensure spec is validated: `vds-cli spec validate .gpt-5.4/specs/my-spec`
2. Run `vds-cli brd generate --spec .gpt-5.4/specs/my-spec --output brd.md`
3. Review generated BRD
4. Export: `vds-cli brd export --input brd.md --format pdf`

## Related

- **Orchestrators:** [spec](spec-orchestrator.md), [pdf](pdf-orchestrator.md), [confluence](cli-commands.md)
- **Confluence:** [WHO BRD](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
