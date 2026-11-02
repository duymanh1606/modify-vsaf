# VDS CLI - Cross-Platform Python CLI

Cross-platform Python CLI wrapper for VDS Platform operations.

## Installation (uv-native)

```bash
cd WHO-project/vds-scripts
# Optional: prime every project environment (add --frozen or other uv sync flags as needed)
./scripts/bootstrap_uv.sh --frozen

# Or just sync this package when needed
./scripts/worktree_uv.sh sync --project vds_cli
```

> Per the official uv project documentation, `uv run` automatically creates or updates the local `.venv` for the
> requested project when it executes, so no manual `uv pip install -e` is required. Use `uv sync --project vds_cli` (or
> the bootstrap script) only when you want to pre-build the environment ahead of time. (Source:
> [uv docs – The project environment](https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/layout.md#the-project-environment))

## Usage

### Environment Management

```bash
# Load environment (loads from the shared VDS env file)
./scripts/worktree_uv.sh run --project vds_cli vds-cli env load

# Check environment status
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status

# Check system status (orchestrators + environment)
./scripts/worktree_uv.sh run --project vds_cli vds-cli status

# Run actionable diagnostics (router + env files + auth readiness)
./scripts/worktree_uv.sh run --project vds_cli vds-cli doctor
```

### Using Orchestrators

```bash
# JIRA operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "project = NTTC" --limit 20
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue NTTC-123

# Confluence operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search --cql 'space="TDOV" and type=page' --limit 20
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content page 99647801 --expand body.view,version,space
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence -- --json-only crawl-tree "http://confluence.digital.vn/pages/viewpage.action?pageId=88716667" --out /tmp/confluence_evidence --depth 1 --emit-corpus --emit-link-graph

# Bitbucket operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket projects
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repositories INSURANCE
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo get INSURANCE vds-ai-memory
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo create INSURANCE new-repo --yes
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo update INSURANCE vds-ai-memory --description "Updated description" --yes
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo delete INSURANCE old-repo --yes
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket commit-status get INSURANCE vds-ai-memory COMMIT_HASH --limit 20
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket branch-permissions list INSURANCE --repo vds-ai-memory --json-only

# SonarQube operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube ping
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube qualitygate --project ekyc-business

# Git operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli git clone lep
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git status --match "*service*"

# Elasticsearch operations (via Kibana Console Proxy)
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic ping
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic user-info
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic search --index "logs-*" --size 10
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic count --index "logs-*"
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic search --qs "level:ERROR AND timeout"

# Grafana logs operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana health
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana search --index "gw-*" --limit 20

# Diagram generation (C4, sequence, component, use case, mermaid)
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams --project INSURANCE --list
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams --project INSURANCE --service insurance-policy-business
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams --project INSURANCE --c4 --mermaid --use-case
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams --project INSURANCE --hierarchy --export-dsl

# BRD coverage validation
./scripts/worktree_uv.sh run --project vds_cli vds-cli brd -- validate
./scripts/worktree_uv.sh run --project vds_cli vds-cli brd -- validate --root WHO-project/insurance-document --report /tmp/brd_coverage_report.json

# Excel target-state status workbook
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- target-state-status

# Task breakdown management
./scripts/worktree_uv.sh run --project vds_cli vds-cli tasks -- audit
./scripts/worktree_uv.sh run --project vds_cli vds-cli tasks -- refine
./scripts/worktree_uv.sh run --project vds_cli vds-cli tasks -- normalize
./scripts/worktree_uv.sh run --project vds_cli vds-cli tasks -- sync
```

### Help

```bash
# Show main help
./scripts/worktree_uv.sh run --project vds_cli vds-cli --help

# Show command help
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams --help
```

**`vds-cli` is the ONLY valid user-facing entry point.** Direct executables listed in `[project.scripts]` exist only for router binding and must not be invoked by operators. Use `vds-cli <service> --help` for discovery.

## Features

- ✅ **Cross-platform**: Works on Mac, Linux, and Windows
- ✅ **Environment Management**: Automatic loading from the shared VDS env file via `vds_cli_common` (populates `os.environ`)
- ✅ **Unified Interface**: Single CLI for all orchestrators (JIRA, Confluence, Bitbucket, Git, SonarQube, Elastic, Diagrams, Excel, Tasks, PDF)
- ✅ **Strict Router Validation**: `vds-cli` verifies routed entrypoints exist in `[project.scripts]` and their target modules are present under `src/`
- ✅ **Doctor Diagnostics**: `vds-cli doctor` reports concrete recommended actions for missing env/auth and broken routed services
- ✅ **Rich Console Output**: Beautiful tables and formatted output
- ✅ **Type-Safe Configuration**: Full Python type hints and validation
- ✅ **Quality Assured**: 77% test coverage, zero ruff linting issues

## Configuration Precedence

`vds-cli` follows a deterministic precedence model:

1. Existing shell environment variables (`os.environ`)
2. Shared VDS env file (effective config-root `.env`)
3. `WHO-project/vds-scripts/.env` (optional fallback)

`vds-cli env load` and routed commands load values into the current CLI process.  
They do not export values back into your interactive shell session.

## Migration from Bash CLI

The Python CLI (`vds-cli`) replaces the legacy bash wrapper (now removed). The command interface is identical:

**Before (bash)**:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "project = NTTC" 20
```

**After (Python)**:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "project = NTTC" --limit 20
```

All commands work the same way, with improved error handling and cross-platform support.

## Development

### Running Tests

```bash
cd WHO-project/vds-scripts/vds_cli
uv run pytest tests/unit/ -v
uv run pytest tests/verification/ -v  # Requires credentials
```

### Code Quality

```bash
# Lint check
uv run ruff check src/

# Format code
uv run ruff format src/
```

## Requirements

- Python >= 3.11
- uv (for package management)
- Shared VDS env file with credentials

## Dependencies

- **typer** >= 0.20.0 - CLI framework
- **rich** >= 13.7.0 - Console output
- **pydantic** >= 2.12.3 - Data validation
- **pydantic-settings** >= 2.12.0 - Settings management
tings management
nagement
tings management
ntials

## Dependencies

- **typer** >= 0.20.0 - CLI framework
- **rich** >= 13.7.0 - Console output
- **pydantic** >= 2.12.3 - Data validation
- **pydantic-settings** >= 2.12.0 - Settings management
tings management
nagement
tings management
