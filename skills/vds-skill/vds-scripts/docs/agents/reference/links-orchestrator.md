<!-- diátaxis: reference -->

# Links Orchestrator

> Documentation link validation for VDS ecosystem.

## Scope

- **Does:** Validate link integrity across markdown documentation, detect broken internal/external links, and verify target-state documentation cross-references.
- **Does NOT:** Fix broken links automatically or validate non-markdown content.
- **Primary users:** AI agents (doc quality checks), documentation maintainers.

## CLI Entry

```bash
# Via unified router
vds-cli links --help

# Direct entry
vds-cli links --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `validate` | Validate links in documentation | `--mode`, `--root`, `--max-files`, `--report` |

## Validation Modes

- `target-state` — validate links within target-state documentation tree (default)
- `docs` — validate links across general documentation with configurable file limit

## Workflow Examples

```bash
# Validate target-state links (default)
vds-cli links validate

# Validate general docs with custom root
vds-cli links validate --mode docs --root ./docs --max-files 100

# Write JSON report
vds-cli links validate --report link-report.json

# JSON-only output
vds-cli links --json-only validate --mode target-state
```

## Environment

- `VDS_INSURANCE_DOCS_ROOT` — override default documentation root discovery

## Related

- **Orchestrators:** [structure](structure-orchestrator.md), [brd](brd-orchestrator.md)
- **Confluence:** [WHO Links](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
