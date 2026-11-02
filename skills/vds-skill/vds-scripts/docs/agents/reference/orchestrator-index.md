<!-- diátaxis: reference -->

# Orchestrator Index

> Quick-reference for all 28 VDS orchestrators.

## Core Platform

| Orchestrator | Purpose | CLI Entry | Doc |
|-------------|---------|-----------|-----|
| audit | Audit execution and reporting | `vds-cli audit` | [audit-triage-playbook](audit-triage-playbook.md) |
| bitbucket | Bitbucket operations | `vds-cli bitbucket-cli` | [cli-commands](cli-commands.md) |
| brd | Business requirements documents | `vds-cli brd` | [brd-orchestrator](brd-orchestrator.md) |
| circular-dependency | Circular dependency detection | `vds-cli circular-dependency` | [circular-dependency-orchestrator](circular-dependency-orchestrator.md) |
| confluence | Confluence operations | `vds-cli confluence-cli` | [cli-commands](cli-commands.md) |
| db-query | Database query operations | `vds-cli db-query` | [db-query-orchestrator](db-query-orchestrator.md) |
| diagrams | Diagram generation | `vds-cli diagrams` | [diagrams-orchestrator](diagrams-orchestrator.md) |
| elastic | Elasticsearch operations | `vds-cli elastic` | [elastic-orchestrator](elastic-orchestrator.md) |
| evolution | Ecosystem evolution loop | `vds-cli evolution` | [evolution-orchestrator](evolution-orchestrator.md) |
| excel | Excel processing | `vds-cli excel` | [excel-orchestrator](excel-orchestrator.md) |
| git | Git repository operations | `vds-cli git-orchestrator` | [cli-commands](cli-commands.md) |
| google-sheets | Google Sheets integration | `vds-cli google-sheets` | [google-sheets-orchestrator](google-sheets-orchestrator.md) |
| grafana | Grafana logs and metrics | `vds-cli grafana` | [grafana-orchestrator](grafana-orchestrator.md) |
| hexagonal | Hexagonal compliance | `vds-cli hexagonal` | [hexagonal-orchestrator](hexagonal-orchestrator.md) |
| intellij | IntelliJ plugin operations | `vds-cli intellij` | [intellij-orchestrator](intellij-orchestrator.md) |
| jira | JIRA operations | `vds-cli jira-cli` | [cli-commands](cli-commands.md) |
| links | Link validation | `vds-cli links` | [links-orchestrator](links-orchestrator.md) |
| lsp | Language server protocol | `vds-cli lsp` | [lsp-orchestrator](lsp-orchestrator.md) |
| markdown | Markdown processing | `vds-cli markdown` | [markdown-orchestrator](markdown-orchestrator.md) |
| mcp | MCP router and tools | `vds-cli mcp-server` | [mcp-orchestrator](mcp-orchestrator.md) |
| memory | Memory search and storage | `vds-cli memory` | [memory-orchestrator](memory-orchestrator.md) |
| metabase | Metabase analytics | `vds-cli metabase` | [metabase-orchestrator](metabase-orchestrator.md) |
| multi-agent | Multi-agent coordination | `vds-cli multi-agent` | [multi-agent-orchestrator](multi-agent-orchestrator.md) |
| openapi | OpenAPI schema operations | `vds-cli openapi` | [openapi-orchestrator](openapi-orchestrator.md) |
| pdf | PDF generation | `vds-cli pdf` | [pdf-orchestrator](pdf-orchestrator.md) |
| progress | Progress reporting | `vds-cli progress` | [progress-orchestrator](progress-orchestrator.md) |
| public-interface | Public API analysis | `vds-cli public-interface` | [public-interface-orchestrator](public-interface-orchestrator.md) |
| research | Research and evidence | `vds-cli research` | [research-orchestrator](research-orchestrator.md) |
| schema | Schema conversion | `vds-cli schema-convert` | [schema-orchestrator](schema-orchestrator.md) |
| sonarqube | SonarQube integration | `vds-cli sonarqube` | [sonarqube-orchestrator](sonarqube-orchestrator.md) |
| spec | Spec creation | `vds-cli spec` | [spec-orchestrator](spec-orchestrator.md) |
| structure | Code structure analysis | `vds-cli structure` | [structure-orchestrator](structure-orchestrator.md) |
| tasks | Task management | `vds-cli tasks` | [tasks-orchestrator](tasks-orchestrator.md) |

## By Category

### Audit & Reporting
- [audit](audit-triage-playbook.md), [progress](progress-orchestrator.md), [spec](spec-orchestrator.md)

### Data & Analytics
- [db-query](db-query-orchestrator.md), [elastic](elastic-orchestrator.md), [grafana](grafana-orchestrator.md), [metabase](metabase-orchestrator.md), [google-sheets](google-sheets-orchestrator.md), [excel](excel-orchestrator.md)

### Code Quality
- [circular-dependency](circular-dependency-orchestrator.md), [hexagonal](hexagonal-orchestrator.md), [sonarqube](sonarqube-orchestrator.md), [structure](structure-orchestrator.md), [public-interface](public-interface-orchestrator.md), [intellij](intellij-orchestrator.md), [lsp](lsp-orchestrator.md)

### Documentation
- [confluence](cli-commands.md), [markdown](markdown-orchestrator.md), [pdf](pdf-orchestrator.md), [diagrams](diagrams-orchestrator.md), [brd](brd-orchestrator.md)

### Research & Intelligence
- [research](research-orchestrator.md), [memory](memory-orchestrator.md), [mcp](mcp-orchestrator.md)

### DevOps
- [git](cli-commands.md), [bitbucket](cli-commands.md), [jira](cli-commands.md), [links](links-orchestrator.md), [openapi](openapi-orchestrator.md), [schema](schema-orchestrator.md)

### Coordination
- [tasks](tasks-orchestrator.md), [multi-agent](multi-agent-orchestrator.md), [evolution](evolution-orchestrator.md)

## Related

- [Orchestrator Architecture](orchestrator-architecture.md)
- [CLI Commands Reference](cli-commands.md)
- [CLI Help Matrix](cli-help-matrix.md)
- [Skills Reference](skills-reference.md)
