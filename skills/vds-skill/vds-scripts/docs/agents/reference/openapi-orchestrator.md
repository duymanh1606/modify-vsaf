<!-- diátaxis: reference -->

# OpenAPI Orchestrator

> OpenAPI schema validation, conversion, and client generation.

## Scope

- **Does:** Validate OpenAPI 3.x specs, convert between formats (JSON/YAML), generate client stubs, and extract endpoint documentation.
- **Does NOT:** Design APIs, replace Swagger UI, or manage API gateways.
- **Primary users:** AI agents (API review), developers (client generation), QA (contract testing).

## CLI Entry

```bash
# Via unified router
vds-cli openapi --help

# Direct entry
vds-cli openapi --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `validate` | Validate OpenAPI spec | `--input`, `--strict` |
| `convert` | Convert between JSON/YAML | `--input`, `--output` |
| `generate` | Generate client stub | `--input`, `--language`, `--output` |
| `extract` | Extract endpoint docs | `--input`, `--path` |

## Common Workflows

### Workflow: Validate API Spec

1. Run `vds-cli openapi validate --input api.yaml --strict`
2. Review validation errors
3. Fix issues and re-validate

### Workflow: Generate Python Client

1. Run `vds-cli openapi generate --input api.yaml --language python --output client/`
2. Review generated client code
3. Add to project dependencies

## Related

- **Orchestrators:** [schema](schema-orchestrator.md), [public_interface](public-interface-orchestrator.md)
- **Confluence:** [WHO OpenAPI](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
