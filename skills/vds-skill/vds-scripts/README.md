# VDS Scripts & Orchestrator Ecosystem

**Centralized Automation Platform for Viettel Digital Services**

This repository contains the `vds-cli` and a collection of specialized orchestrators designed to automate the software development lifecycle, from documentation management to infrastructure verification.

`WHO-project` is the canonical VDS ecosystem for both reusable skills and routed scripts. Within that model, this repository is the authoritative scripts workspace, while the companion `WHO-project/vds-skills/` repository is the authoritative skills catalog.

## 🚀 Quick Start

Ensure you have the VDS CLI installed and configured.
For the canonical human + AI-agent install/bootstrap flow, start with `docs/agents/how-to/install-and-bootstrap-who-scripts-and-skills.md`.

```bash
# Install dependencies in the current worktree
./scripts/worktree_uv.sh sync

# Verify installation
./scripts/worktree_uv.sh run --project vds_cli vds-cli --version

# Check environment status
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status
```

---

## 📦 Available Orchestrators

The platform is modularized into specialized orchestrators, each handling a specific domain.

### Core Utilities

| Orchestrator | Command | Description |
|--------------|---------|-------------|
| **[Task Orchestrator](./task_orchestrator/README.md)** | `vds-cli tasks --` | Manage, refine, and audit service task breakdowns and project plans. |
| **[Excel Orchestrator](./excel_orchestrator/README.md)** | `vds-cli excel --` | Read, write, and format Excel reports (used by Task Orchestrator). |
| **[Git Orchestrator](./git_orchestrator/README.md)** | `vds-cli git --` | Repository management, cloning, and syncing across projects. |
| **[OpenAPI Orchestrator](./openapi_orchestrator/README.md)** | `vds-cli openapi --` | Validate, merge, and manage OpenAPI 3.x specifications. |

### Documentation & Knowledge

| Orchestrator | Command | Description |
|--------------|---------|-------------|
| **[Markdown Orchestrator](./markdown_orchestrator/README.md)** | `uv run --project markdown_orchestrator vds-markdown ...` | Format, lint, and validate Markdown documentation (direct CLI). |
| **[PDF Orchestrator](./pdf_orchestrator/README.md)** | `vds-cli pdf --` | Generate high-fidelity PDFs from markdown sources. |
| **[Diagram Generator](./diagram_generator/README.md)** | `vds-cli diagrams --` | Generate C4, Sequence, and ER diagrams from code/text. |
| **[BRD Orchestrator](./brd_orchestrator/README.md)** | `vds-cli brd --` | Validate requirement coverage against Business Requirements Documents. |
| **[Schema Converter](./schema_converter/README.md)** | `vds-cli schema --` | Convert between SQL, Prisma, JSON Schema, and Markdown. |

### Integration & Infrastructure

| Orchestrator | Command | Description |
|--------------|---------|-------------|
| **[Jira Orchestrator](./jira_orchestrator/README.md)** | `vds-cli jira` | Interact with Jira API for ticket management. |
| **[Confluence Orchestrator](./confluence_orchestrator/README.md)** | `vds-cli confluence` | Publish documentation to Confluence pages. |
| **[Bitbucket Orchestrator](./bitbucket_orchestrator/README.md)** | `vds-cli bitbucket` | Manage PRs, repositories, and branch permissions. |
| **[Elastic Orchestrator](./elastic_orchestrator/README.md)** | `vds-cli elastic --` | Query and manage Elasticsearch indices. |
| **[DB Query Orchestrator](./db_query_orchestrator/README.md)** | `vds-cli db_query --` | Manage named DB connections and run safe read-only SQL against PostgreSQL, SQL Server, and MariaDB. |
| **[Grafana Orchestrator](./grafana_orchestrator/README.md)** | `vds-cli grafana --` | Query logs and metrics via Grafana Datasource. |
| **[SonarQube Orchestrator](./sonarqube_orchestrator/README.md)** | `vds-cli sonarqube --` | Trigger scans and check quality gates. |

### Ecosystem Scheduling

| Orchestrator | Command | Description |
|--------------|---------|-------------|
| **[Scheduler Orchestrator](./scheduler_orchestrator/README.md)** | `vds-cli scheduler --` | Durable cron/interval/one-shot schedule management, event-bus dispatch, chain triggers, and DBOS workflow orchestration. Requires `VDS_SCHEDULER_ENABLED=true`. |

### Developer Experience

| Orchestrator | Command | Description |
|--------------|---------|-------------|
| **[IntelliJ Orchestrator](./intellij_orchestrator/README.md)** | `vds-cli intellij --` | Automate workspace setup and run configurations. |
| **[Links Orchestrator](./links_orchestrator/README.md)** | `vds-cli links --` | Validate relative and absolute links across documentation. |
| **[Structure Orchestrator](./structure_orchestrator/README.md)** | `vds-cli structure --` | Enforce repository folder structure and naming conventions. |

---

## 🛠️ Development Standards

All orchestrators should follow the `vds-cli` routed command model and shared environment-loading pattern used in `vds_cli_common`.

### Key Requirements
1.  **Structure**: Must follow `src/vds_[name]_orchestrator/cli.py` pattern.
2.  **Configuration**: Keep secrets in `VDS_ENV_FILE` or `<config-root>/.env`; `<config-root>` resolves from `VDS_CONFIG_DIR` when set, otherwise from the friendly user-home VDS default (`~/.vds` on Unix-like systems). Keep non-sensitive extraction tuning in `<config-root>/config/extract-docs.toml`.
3.  **Testing**: Minimum 80% unit test coverage.
4.  **CLI**: Expose commands via `typer` for integration into `vds-cli`.
5.  **Audit Runtime Contract (current merged baseline)**: `vds-audit` workflow/analyze/ad-hoc consume evidence from Postgres chunks only (no runtime disk evidence ingestion path). Use `vds-audit prepare --project <PROJECT_STORAGE_KEY>` to run the deterministic prep sequence (`parse-registry -> sync repos -> extract-docs`), then confirm `state readiness` reports `ready=true`, `docs_chunk_ready=true`, and `code_chunk_ready=true`.

### Creating a New Orchestrator

1.  Copy the structure from an existing module (e.g., `task_orchestrator`).
2.  Implement the logic in `src/`.
3.  Register the module in `vds_cli/src/vds_cli/router.py`.
4.  Add the command group in `vds_cli/src/vds_cli/cli.py`.
5.  Add entry to this README.

---

## 🤝 Contributing

1.  Create a feature branch `feature/enhance-[orchestrator]`.
2.  Ensure tests pass: `uv run pytest`.
3.  Submit a PR via `vds bitbucket pr create`.
