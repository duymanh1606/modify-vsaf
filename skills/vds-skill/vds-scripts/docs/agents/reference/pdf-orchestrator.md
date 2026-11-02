<!-- diátaxis: reference -->

# PDF Orchestrator

> PDF generation from markdown and other formats — convert, apply templates, batch generate.

## Scope

- **Does:** Convert markdown to PDF, apply templates, batch generate documents, and handle Vietnamese text rendering.
- **Does NOT:** Edit existing PDFs, perform OCR, or replace dedicated PDF editors.
- **Primary users:** AI agents (document delivery), operators (report generation), compliance teams.

## CLI Entry

```bash
# Via unified router
vds-cli pdf --help

# Direct entry
vds-cli pdf --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `vds-cli pdf md2pdf` | Markdown to PDF | `--input`, `--output`, `--template` |
| `template` | Apply PDF template | `--template`, `--data` |
| `batch` | Batch generate PDFs | `--input-dir`, `--output-dir` |
| `validate` | Validate PDF output | `--input` |

## Common Workflows

### Workflow: Generate Report from Markdown

1. Write report in markdown with frontmatter
2. Run `vds-cli pdf md2pdf --input report.md --output report.pdf --template corporate`
3. Validate output: `vds-cli pdf validate --input report.pdf`

### Workflow: Batch Generate Invoices

1. Prepare invoice data as JSON files
2. Run `vds-cli pdf batch --input-dir invoices/ --output-dir pdfs/ --template invoice`
3. Review generated PDFs

## Related

- **Orchestrators:** [markdown](markdown-orchestrator.md), [diagrams](diagrams-orchestrator.md), [confluence](cli-commands.md)
- **Confluence:** [WHO PDF](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
