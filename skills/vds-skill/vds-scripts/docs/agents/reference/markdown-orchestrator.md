<!-- diátaxis: reference -->

# Markdown Orchestrator

> Markdown formatting and validation for VDS documentation.

## Scope

- **Does:** Format markdown files with consistent wrapping, validate markdown syntax, and check staged or specified files for formatting compliance.
- **Does NOT:** Render markdown to HTML or validate link targets (use [links-orchestrator](links-orchestrator.md) for that).
- **Primary users:** AI agents (doc hygiene), developers (pre-commit checks).

## CLI Entry

```bash
# Via unified router
vds-cli markdown --help

# Direct entry
vds-cli markdown --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `check` | Check markdown formatting; exit non-zero if changes needed | `--staged`, `--wrap` |
| `format` | Format markdown files in place | `--staged`, `--wrap` |
| `version` | Show orchestrator version | — |

## Workflow Examples

```bash
# Check all tracked markdown files
vds-cli markdown check

# Check specific files
vds-cli markdown check docs/*.md README.md

# Check staged files only
vds-cli markdown check --staged

# Format with custom wrap width
vds-cli markdown format --wrap 100

# Format staged files
vds-cli markdown format --staged
```

## Related

- **Orchestrators:** [links](links-orchestrator.md), [pdf](pdf-orchestrator.md)
- **Confluence:** [WHO Markdown](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
