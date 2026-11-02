<!-- diátaxis: explanation -->

# Features Overview

The WHO ecosystem provides 37 orchestrators organized by complexity and use case.

## By Complexity

### Basic — Day 1–3

| Feature | Orchestrator | One-Line Description |
|---------|-----------|---------------------|
| Audit code quality | `audit` | Run automated audits on any repository |
| Sync to Confluence | `confluence` | Upload evidence and reports to Confluence |
| Query databases | `db_query` | Run ad-hoc SQL across PostgreSQL, SQL Server, MariaDB |
| Generate diagrams | `diagrams` | Create architecture diagrams from code |
| Run progress reports | `progress` | Generate INSURANCE-AI progress reports |
| Schedule workflows | `scheduler` | Create cron/interval schedules |

### Intermediate — Day 4–7

| Feature | Orchestrator | One-Line Description |
|---------|-----------|---------------------|
| Multi-project audit | `audit` | Audit multiple repos in one command |
| Git worktree management | `git` | Create, lock, repair, retire worktrees |
| Circular dependency analysis | `circular_dependency` | Detect cycle risk across repos |
| ElasticSearch operations | `elastic` | Index and search logs and metrics |
| Hexagonal compliance check | `hexagonal` | Verify clean architecture boundaries |
| SonarQube integration | `sonarqube` | Run quality analysis and view issues |

### Advanced — Day 8+

| Feature | Orchestrator | One-Line Description |
|---------|-----------|---------------------|
| AI-powered research | `research` | Combine local code search with web research |
| Custom skill authoring | `spec` | Create and validate VDS agent skills |
| Multi-agent workflows | `multi_agent` | Coordinate parallel agent teams |
| Telegram integration | `telegram` | Bot-based notification and interaction |
| AI memory management | `memory` | Cross-session knowledge persistence |
| OpenAPI handling | `openapi` | Parse, validate, and generate OpenAPI specs |
| BRD generation | `brd` | Business requirements documents |
| Schema conversion | `schema` | Convert between data schemas |
| MCP server integration | `mcp` | Model Context Protocol server management |
| Claude API workflows | `claude` | Anthropic Claude API orchestration |

## By Functional Area

| Area | Orchestrators |
|------|--------------|
| **Audit & Quality** | audit, sonarqube, hexagonal, public_interface |
| **Documentation** | confluence, markdown, brd, spec, diagrams |
| **Data & Storage** | db_query, elastic, schema, excel, google_sheets, metabase |
| **DevOps & Infra** | git, scheduler, evolution, links, structure |
| **AI & Agents** | memory, research, multi_agent, telegram, claude, mcp, lsp |
| **Integration** | bitbucket, jira, openapi, pdf, intellij |
| **Reporting** | progress, grafana |

## See Also

- [Feature Progression Guide](../tutorials/feature-progression-guide.md) — Day 8–14 learning path
- [Orchestrator Comparison Matrix](../reference/orchestrator-comparison-matrix.md) — Detailed comparison
- [Quick Start](../tutorials/quick-start.md) — Get running in 5 minutes
