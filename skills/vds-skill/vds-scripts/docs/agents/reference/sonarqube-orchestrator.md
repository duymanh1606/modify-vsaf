<!-- diátaxis: reference -->

# SonarQube Orchestrator

> SonarQube code quality scanning and issue management for VDS repositories.

## Scope

- **Does:** Query SonarQube projects, list issues and hotspots, run health checks, and export quality metrics.
- **Does NOT:** Execute scans (requires Maven or sonar-scanner in PATH), manage SonarQube server configuration.
- **Primary users:** AI agents (quality gate checks), developers (issue triage).

## CLI Entry

```bash
# Via unified router
vds-cli sonarqube --help

# Direct entry
vds-cli sonarqube --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `ping` | Test connectivity and authentication | — |
| `projects` | List accessible SonarQube projects | `--query`, `--limit` |
| `issues` | List issues for a project | `--project`, `--status`, `--severity` |
| `hotspots` | List security hotspots | `--project`, `--status` |
| `measures` | Get quality measures for a project | `--project`, `--metrics` |

## Workflow Examples

```bash
# Health check
vds-cli sonarqube ping

# List projects
vds-cli sonarqube projects --limit 50

# List open issues for a project
vds-cli sonarqube issues list --project ekyc-business --status OPEN

# List high-severity issues
vds-cli sonarqube issues list --project ekyc-business --severity CRITICAL,BLOCKER

# Get quality measures
vds-cli sonarqube measures --project ekyc-business --metrics coverage,bugs,vulnerabilities

# JSON-only output
vds-cli sonarqube --json-only ping
```

## Configuration

Requires `VDS_SONAR_TOKEN` or `VDS_SONAR_USER`/`VDS_SONAR_PASSWORD` in `~/.vds/.env`.

## Related

- **Orchestrators:** [grafana](grafana-orchestrator.md), [elastic](elastic-orchestrator.md)
- **Confluence:** [WHO SonarQube](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
