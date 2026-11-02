<!-- diátaxis: reference -->

# DB Query Orchestrator

> Execute safe read-only SQL queries across Postgres, SQL Server, and MariaDB connections.

## Scope

- **Does:** Run validated read-only SQL, list configured connections, test connectivity, and export results as JSON or TSV.
- **Does NOT:** Execute write operations (INSERT, UPDATE, DELETE, DDL). Does not replace pgAdmin or database IDEs.
- **Primary users:** AI agents (data retrieval), operators (ad-hoc queries), CI pipelines (read-only assertions).

## CLI Entry

```bash
# Via unified router
vds-cli db-query --help

# Direct entry
vds-cli db-query --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `--list-connections` | Discover configured connection aliases from env | `--env` |
| `--test` | Probe a single connection (SELECT 1) | `--conn` |
| `--query` | Execute a read-only SQL query | `--conn`, `--format` |

## Global Flags

| Flag | Description |
|------|-------------|
| `--conn <dbtype>:<alias>` | Connection id (e.g., `postgres:analytics`) |
| `--query "SQL"` | Read-only SQL to execute |
| `--format json|tsv` | Output format (default: json) |
| `--env <path>` | Path to `.env` with `VDS_DB_*` definitions |
| `--test` | Run connectivity probe on `--conn` |
| `--list-connections` | List all discovered connections |
| `--json-only`, `-j` | Output clean JSON only |
| `--quiet`, `-q` | Suppress non-essential output |

## Connection Configuration

Connections are discovered from environment variables using the pattern:
```bash
VDS_DB_POSTGRES_ANALYTICS_URL=jdbc:postgresql://host:5432/dbname
VDS_DB_POSTGRES_ANALYTICS_USER=reader
VDS_DB_POSTGRES_ANALYTICS_PASSWORD=***
```

Or explicitly via `VDS_DB_CONNECTIONS=postgres:analytics,sqlserver:warehouse`.

Supported types: `postgres`, `sqlserver`, `mariadb` (aliases: `postgresql`, `mssql`, `mysql`).

## Query Safety

Only queries starting with `SELECT`, `WITH`, `EXPLAIN`, `SHOW`, or `DESCRIBE` are permitted. Write prefixes (INSERT, UPDATE, DELETE, ALTER, DROP, TRUNCATE, CREATE, MERGE, GRANT, REVOKE) are rejected before execution.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Usage error (unsupported format, missing flags) |
| 3 | Config error (missing env, unknown connection) |
| 4 | Validation error (write query blocked) |
| 5 | General runtime error |

## Workflow Examples

```bash
# List all configured connections
vds-cli db-query --list-connections

# Test connectivity to a specific connection
vds-cli db-query --conn postgres:analytics --test

# Run a read-only query and get JSON results
vds-cli db-query --conn postgres:analytics --query "SELECT COUNT(*) FROM audit_runs"

# Export results as TSV for spreadsheet import
vds-cli db-query --conn sqlserver:warehouse --query "SELECT TOP 10 * FROM logs" --format tsv

# Use a custom env file
vds-cli db-query --env ~/.vds/prod.env --conn mariadb:legacy --query "SHOW TABLES" --json-only
```

## Related

- **Orchestrators:** [grafana](grafana-orchestrator.md), [elastic](elastic-orchestrator.md), [metabase](metabase-orchestrator.md)
- **Skills:** [memory-orchestrator-skill](../../../../vds-skills/skills/memory-orchestrator-skill/SKILL.md)
