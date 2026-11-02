<!-- diátaxis: explanation -->

# Data Flow

## Request Lifecycle

### Audit Command

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as vds-cli
    participant R as Router
    participant O as Audit Orchestrator
    participant PG as Postgres
    participant CONF as Confluence
    participant EXT as External API
    
    U->>CLI: vds-cli audit --repo my-service
    CLI->>CLI: Parse arguments (Typer)
    CLI->>R: Dispatch "audit"
    R->>R: Validate orchestrator exists
    R->>O: uv run vds-audit
    O->>PG: Load checklist config
    O->>EXT: Fetch repo metadata (Bitbucket)
    O->>EXT: Run SonarQube analysis
    O->>PG: Store results
    O->>CONF: Upload evidence (optional)
    O->>R: JSON output
    R->>CLI: Forward output
    CLI->>U: Console output
```

### Confluence Sync Command

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as vds-cli
    participant R as Router
    participant O as Confluence Orchestrator
    participant FS as Filesystem
    participant CONF as Confluence
    
    U->>CLI: vds-cli docs confluence-sync --repo my-service
    CLI->>R: Dispatch "confluence"
    R->>O: uv run vds-confluence-cli
    O->>FS: Read docs/agents/
    O->>FS: Read AGENTS.md, llms.txt
    O->>CONF: Authenticate (token)
    O->>CONF: Upload pages
    O->>O: Generate evidence snapshot
    O->>R: Completion status
    R->>CLI: Forward status
    CLI->>U: Sync report
```

## Error Handling Flow

```mermaid
graph TD
    A[Command Start] --> B{Validation}
    B -->|Valid| C[Orchestrator Run]
    B -->|Invalid| D[Validation Error]
    C -->|Success| E[Result Output]
    C -->|Failure| F{Error Type}
    F -->|Auth| G[Auth Error: Check ~/.vds/.env]
    F -->|Network| H[Network Error: Retry or check connectivity]
    F -->|Not Found| I[Not Found: Verify resource exists]
    F -->|Other| J[Generic Error: See logs]
    D --> K[Exit code 1]
    G --> K
    H --> K
    I --> K
    J --> K
    E --> L[Exit code 0]
```

## Data Transformation Points

### Input Normalization

- Repo names are normalized to lowercase
- Paths are resolved to absolute paths
- Env vars are loaded from `~/.vds/.env` before orchestrator invocation

### Output Formatting

- JSON output: For programmatic consumption
- Table output: For human readability (Rich tables)
- Markdown output: For documentation generation
- Evidence format: Structured JSON for Confluence upload

### Caching

| Cache Key | Store | TTL | Invalidation |
|-----------|-------|-----|-------------|
| Orchestrator metadata | Redis | 1 hour | On version change |
| Confluence page list | Postgres | 4 hours | On sync completion |
| Audit results | Postgres | Permanent | On re-audit |
| AI memory vectors | Qdrant | Permanent | On explicit update |

## Logging Flow

```
Orchestrator → structlog → JSON → Console/File → Optional: Postgres evidence
```

All log entries include:
- Timestamp (ISO 8601)
- Orchestrator name
- Operation
- Status (started/completed/failed)
- Context (repo, checklist, user)

## Data Flow Workflow

Trace the path of a single audit request end-to-end:

```bash
vds-cli audit --repo my-service --checklist security
# CLI parses args, dispatches to Audit Orchestrator via Router
# Orchestrator loads checklist from Postgres
# External APIs (Bitbucket, SonarQube) are invoked
# Results are stored back in Postgres and returned as JSON
```

## See Also

- [Orchestrator Architecture](../reference/orchestrator-architecture.md)
- [System Architecture](../explanation/system-architecture.md)
- [Troubleshooting Guide](../how-to/troubleshooting-guide.md)
