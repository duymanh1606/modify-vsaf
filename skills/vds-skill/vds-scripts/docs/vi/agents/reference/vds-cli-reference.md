<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# VDS CLI Reference

`vds-cli` is the unified router for workspace orchestrators.

## Primary Source

- [vds_cli README](../../../vds_cli/README.md)

## Common Entry Points

- `vds-cli env status`
- `vds-cli status`
- `vds-cli doctor`
- `vds-cli jira ...`
- `vds-cli confluence ...`
- `vds-cli bitbucket ...`
- `vds-cli git ...`
- `vds-cli openapi ...`
- `vds-cli spec ...`
- `vds-cli schema ...`
- `vds-cli diagrams ...`
- `vds-cli google-sheets ...`

Direct package executables may use different names than the routed `vds-cli` subcommands. **Direct executables are internal implementation detail — always use `vds-cli`.**

As of the current Phase 2 lane, `vds-schema-convert --help` and `vds-cli diagrams --help` now expose structured Typer-based discovery surfaces rather than ad hoc manual output, which makes them safer entrypoints for AI-agent command discovery.

For command-family routing, start with `vds-scripts-skill`. For deep specialist workflows, route to the corresponding specialist skill.
For shared env/config/cache path behavior, see `portable-paths-and-config.md`.
For the verified routed command inventory, see `cli-help-matrix.md`.
