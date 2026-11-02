<!-- diátaxis: reference -->

# CLI Development Standards

> Standards for building CLI tools in the VDS monorepo.

## Scope

- **Does:** Define Typer patterns, JSON output, error context, and testing standards.
- **Does NOT:** Replace Python best practices or PEP8.

## Standards

### Pattern Selection

1. **Existing CLIs**: Use direct `typer.Typer()` + dedicated `_version_callback()`
2. **New CLIs**: Use `vds_cli_common.make_vds_app()` for shared wiring

### Required Patterns

| Pattern | Required | Purpose |
|---------|----------|---------|
| Direct `typer.Typer()` | ✅ | Canonical existing-CLI pattern |
| `--json-only` | ✅ | Machine-readable output |
| `--json-output` | ✅ | JSON logs via structlog |
| `_emit_json()` | ✅ | Consistent JSON format |
| Error `context` | ✅ | Debugging info |
| `add_completion=False` | ✅ | Cleaner help |

## Commands

```bash
# Validate CLI standards
vds-cli lint cli --json
```

## Related

- [CLI Commands](cli-commands.md)
- [CLI Help Matrix](cli-help-matrix.md)
- [CLI Development Skill](../../../../vds-skills/skills/cli-development-skill/SKILL.md)
