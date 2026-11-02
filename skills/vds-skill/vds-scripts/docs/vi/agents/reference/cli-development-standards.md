<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# CLI Development Standards

Current CLI development standards are defined by the WHO workspace implementation.

## Use These Sources

- [cli-development-skill](../../../../vds-skills/skills/cli-development-skill/SKILL.md)
- [vds_cli README](../../../vds_cli/README.md)
- [Scripts workspace guide](../../README.md)

## Required Patterns

- Use `uv` and workspace packages.
- Route shared commands through `vds-cli` where appropriate.
- Keep JSON output and tests aligned with package entrypoints.
