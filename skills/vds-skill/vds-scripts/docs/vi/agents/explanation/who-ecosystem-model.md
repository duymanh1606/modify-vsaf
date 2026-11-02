<!-- diátaxis: explanation -->

<!-- TODO: translate — Vietnamese translation pending -->

# WHO Ecosystem Model

`WHO-project` is the canonical VDS ecosystem for both reusable skills and routed scripts.

## Canonical ownership

- Skills live under `WHO-project/vds-skills/skills/`
- Scripts and orchestrators live under `WHO-project/vds-scripts/`
- `.agent/skills/` is a compatibility mirror or symlink path, not an authoring source
- generated `AGENTS.md` surfaces are downstream outputs, not canonical content roots

## Platform versus specialist guidance

Use `vds-scripts-skill` as the **platform-routing skill** when you need to:
- find the correct command family
- understand the current WHO scripts workspace surface
- route a task to the correct specialist skill

Use specialist skills when you need deep workflow guidance, for example:
- `audit-orchestrator-skill` for audit workflow execution and readiness/gating flows
- `llm-analysis-skill` for LLM-backed content evaluation
- `spec-creation-skill` for spec creation and consolidation
- `lsp-skill` for LSP setup and usage
- `circular-dependency-skill` for dependency-cycle analysis

## Current scripts capability layers

- routed command surfaces via `vds-cli`
- standalone workspace capabilities such as markdown, hexagonal, MCP, and multi-agent support
- shared support layers such as `vds_cli_common`

This model keeps the platform skill concise while still covering the full current WHO ecosystem through references and routing aids.
