<!-- diátaxis: reference -->

# Schema Orchestrator

> Convert markdown schemas to Prisma, TypeORM, PlantUML, Mermaid, SQL DDL, JSON Schema.

## Scope

- **Does:** Convert schema definitions between formats, validate against standards, generate migration scripts, and produce ER diagrams.
- **Does NOT:** Design schemas from scratch, replace ORM tooling, or manage database migrations.
- **Primary users:** AI agents (code generation), developers (schema conversion), DBAs.

## CLI Entry

```bash
# Via unified router
vds-cli schema --help

# Direct entry
vds-cli schema-convert --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `convert` | Convert schema format | `--input`, `--output`, `--target` |
| `validate` | Validate schema | `--input`, `--standard` |
| `generate` | Generate code from schema | `--input`, `--language`, `--output` |
| `diagram` | Generate ER diagram | `--input`, `--format` |

## Common Workflows

### Workflow: Markdown to Prisma

1. Define schema in markdown with frontmatter
2. Run `vds-cli schema-convert convert --input schema.md --target prisma --output schema.prisma`
3. Review generated Prisma schema
4. Run `prisma validate` to verify

### Workflow: Generate ER Diagram

1. Run `vds-cli schema-convert diagram --input schema.md --format mermaid`
2. Render with mermaid-cli or embed in docs

## Related

- **Orchestrators:** [openapi](openapi-orchestrator.md), [diagrams](diagrams-orchestrator.md), [db-query](db-query-orchestrator.md)
- **Confluence:** [WHO Schema](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
