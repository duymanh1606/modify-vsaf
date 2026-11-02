# Target-State Documentation Automation Scripts

## Overview

Automation scripts for generating, validating, and managing target-state documentation across all VDS Insurance Platform services.

## Scripts

### 1. generate_diagrams.sh
Generate component, sequence, and use case diagrams for services using VDS Diagram Generator.

### 2. validate_diagrams.sh
Validate existing PlantUML and Mermaid diagrams for syntax errors.

### 3. validate_markdown.sh
Validate markdown files against VDS documentation standards.

### 4. sync_confluence.sh
Upload documentation and diagrams to Confluence.

### 5. validate_brd_coverage.sh
Validate BRD coverage for completed services.

### 6. multi_agent_coordinator.py
Python script for coordinating multi-agent execution with task queue and file locking.

## UV Contract

All scripts in this directory route Python tool invocations through the
worktree-safe wrapper stack. See [`../README.md`](../README.md#uv-contract--canonical-usage)
for the full contract. Key points specific to this directory:

### Sourcing the helper

Every script sources `scripts/vds_sh_helpers.sh` (one level up):

```/dev/null/target-state-automation-source.sh#L1-2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../vds_sh_helpers.sh"
```

### Standard invocation pattern

```/dev/null/target-state-automation-run.sh#L1-5
# Run a vds_cli command
vds_uv_run_package vds_cli vds-cli <subcommand> [args...]

# Run a markdown_orchestrator command (note the -- separator)
vds_uv_run_package markdown_orchestrator -- vds-cli markdown <subcommand> [args...]
```

Do **not** use `uv run --project <path>` or a monorepo-relative `cd` before
`uv run`. Both patterns break in worktrees and alternate checkouts.

### Intentional exception — validate_markdown.sh

`validate_markdown.sh` uses an editable install (`uv pip install -e .`) for
local-dev iteration on `markdown_orchestrator` source. This is documented in
the script header. Do not migrate it to the standard wrapper pattern without
evaluating whether editable-install semantics are still required.

### Backward-compatible helper — docs_root.sh

`docs_root.sh` is now a shim that delegates to `vds_sh_helpers.sh`. Existing
scripts that source it continue to work. New scripts should source
`../vds_sh_helpers.sh` directly.

## Configuration

All scripts use environment variables from the shared VDS env/config layer.

- `VDS_INSURANCE_DOCS_ROOT` overrides the documentation root.
- Without the override, scripts prefer `WHO-project/insurance-document` and then fall back to the first `*-project/insurance-document` match.
- `AGENT_ID` sets the coordination lock identity (default: `markdown-agent-01`).

## Dependencies

- PlantUML CLI (latest version)
- markdownlint-cli2 (npm package)
- Bash 4.0+
- Python 3.14+ preferred for integrated `vds-scripts` workspace usage
- VDS-AI-Memory service running

## Version

**Automation Scripts Version**: 1.0
**Created**: 2025-01-06
**Author**: OpenCode Agent
**Status**: Draft - Ready for Implementation
