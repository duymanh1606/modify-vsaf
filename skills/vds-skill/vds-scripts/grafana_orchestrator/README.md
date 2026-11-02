# VDS Grafana Orchestrator

Query Quickwit logs via Grafana Datasource Proxy.

## Overview

The VDS Grafana Orchestrator provides a Python client and CLI for querying logs stored in Quickwit through Grafana's Datasource Proxy API. This approach leverages Grafana's authentication and access control while providing direct access to Quickwit's powerful log search capabilities.

**Key Features:**
- Query Quickwit logs using native REST API or ES-compatible Query DSL
- Automatic retry with exponential backoff for transient errors
- Connection pooling for optimal performance
- Rich CLI with JSON output for scripting and automation
- Full VDS CLI integration for consistent developer experience

## Architecture

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐     ┌──────────────┐
│                 │     │                     │     │                 │     │              │
│  VDS CLI / MCP  │────▶│ Grafana Orchestrator│────▶│   Grafana API   │────▶│   Quickwit   │
│                 │     │                     │     │                 │     │              │
└─────────────────┘     └─────────────────────┘     └────────┬────────┘     └──────────────┘
                                                             │
                                                    ┌────────▼────────┐
                                                    │                 │
                                                    │ Datasource Proxy│
                                                    │  /api/datasources/proxy/uid/{uid}/
                                                    │                 │
                                                    └─────────────────┘
```

**Data Flow:**
1. CLI/Python client sends request to Grafana Orchestrator
2. Orchestrator authenticates with Grafana (Basic Auth or Token)
3. Request is proxied through Grafana's Datasource Proxy API
4. Quickwit processes the query and returns results
5. Results are formatted and returned to the caller

## Quick Start

### Installation

```bash
cd WHO-project/vds-scripts/grafana_orchestrator

# Install dependencies
uv sync --project grafana_orchestrator

# Install with dev dependencies (for testing)
uv sync --project grafana_orchestrator --group dev
```

### Configuration

Add the following variables to the shared VDS env file:

```bash
# Required: Grafana URL
VDS_GRAFANA_URL=http://10.207.58.64:8485/

# Authentication (choose one):
# Option 1: Basic Auth
VDS_GRAFANA_USER=your-username
VDS_GRAFANA_PASSWORD=your-password

# Option 2: Service Account Token
VDS_GRAFANA_TOKEN=your-service-account-token

# Recommended: Default datasource and index
VDS_GRAFANA_DATASOURCE_UID=your-quickwit-datasource-uid
VDS_QUICKWIT_INDEX=otel-logs-v0_7
```

### Verify Setup

```bash
# Check connectivity
./scripts/worktree_uv.sh run --project grafana_orchestrator ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana health

# List available datasources
./scripts/worktree_uv.sh run --project grafana_orchestrator ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana datasources

# List available indexes
./scripts/worktree_uv.sh run --project grafana_orchestrator ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana indexes
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VDS_GRAFANA_URL` | **Yes** | - | Grafana base URL (e.g., `http://10.207.58.64:8485/`) |
| `VDS_GRAFANA_USER` | No* | - | Username for Basic Auth |
| `VDS_GRAFANA_PASSWORD` | No* | - | Password for Basic Auth |
| `VDS_GRAFANA_TOKEN` | No* | - | Service Account Token (alternative to Basic Auth) |
| `VDS_GRAFANA_DATASOURCE_UID` | No | - | Default Quickwit datasource UID (preferred) |
| `VDS_GRAFANA_DATASOURCE_ID` | No | - | Default datasource ID (legacy) |
| `VDS_GRAFANA_DATASOURCE_NAME` | No | - | Default datasource name |
| `VDS_QUICKWIT_INDEX` | No | - | Default Quickwit index pattern (e.g., `otel-logs-v0_7`) |
| `VDS_GRAFANA_CONNECT_TIMEOUT` | No | `10` | Connection timeout in seconds |
| `VDS_GRAFANA_REQUEST_TIMEOUT` | No | `30` | Read/request timeout in seconds |
| `VDS_GRAFANA_MAX_RETRIES` | No | `3` | Max retry attempts for 429/502/503/504 errors |
| `VDS_GRAFANA_RETRY_BACKOFF` | No | `1.0` | Exponential backoff multiplier |
| `VDS_GRAFANA_VERIFY_CERTS` | No | `false` | Verify SSL certificates (false for self-signed) |

> **Note**: *Either `VDS_GRAFANA_TOKEN` OR both `VDS_GRAFANA_USER` and `VDS_GRAFANA_PASSWORD` must be set.

## CLI Commands

### Health Check

Check connectivity to Grafana and Quickwit datasource:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana health
```

**Output:**
```json
{
  "grafana_ok": true,
  "datasource_ok": true,
  "details": {
    "grafana": {"commit": "abc123", "database": "ok", "version": "10.0.0"},
    "datasource_uid": "quickwit-ds",
    "index_count": 5
  }
}
```

### List Datasources

List available Grafana datasources:

```bash
# List Quickwit datasources only (default)
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana datasources

# List all datasources
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana datasources --no-quickwit-only
```

### List Indexes

List available Quickwit indexes:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana indexes
```

### Show Index Fields

Inspect fields in an index (via document sampling):

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana fields --index otel-logs-v0_7
```

### Search Logs (Quickwit REST API)

Search logs using Quickwit's native query syntax:

```bash
# Search all logs in last hour
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana search --index otel-logs-v0_7 --query "*" --since 1h

# Search for errors
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana search --index otel-logs-v0_7 --query "severity_text:ERROR" --limit 50

# Search with time range (Unix timestamps)
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana search --query "service_name:api-gateway" --from 1705320000 --to 1705323600

# Search with various time units
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana search --query "level:ERROR" --since 30m   # last 30 minutes
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana search --query "level:ERROR" --since 1d    # last day
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana search --query "level:ERROR" --since 1w    # last week
```

**Time duration units:** `s` (seconds), `m` (minutes), `h` (hours), `d` (days), `w` (weeks)

### ES-Compatible Search (Query DSL)

Search using Elasticsearch-compatible Query DSL:

```bash
# Simple match query
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana es-search --query '{"query": {"match": {"severity_text": "ERROR"}}}'

# Query with size
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana es-search --query '{"query": {"bool": {"must": [{"match": {"service_name": "api"}}]}}}' --size 100

# Query from file
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana es-search --query-file query.json --size 100
```

### Global Options

```bash
# JSON-only mode (clean output for piping)
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana --json-only search --index otel-logs-v0_7 --query "*"

# Override datasource
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana --datasource my-other-datasource search --query "*"

# Show version
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana --version
```

## VDS CLI Integration

Access Grafana Orchestrator through the unified VDS CLI:

```bash
# Health check
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- health

# List datasources
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- datasources

# List indexes
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- indexes

# Show fields
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- fields --index otel-logs-v0_7

# Search logs
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- search --index otel-logs-v0_7 --query "severity_text:ERROR" --since 1h

# ES-compatible search
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- es-search --query '{"query": {"match": {"severity_text": "ERROR"}}}'

# JSON-only mode
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana -- --json-only search --query "*"
```

> **Note**: Use `--` to separate vds-cli options from grafana subcommand options.

## Audit Correlation Integration (Phase 68c)

For audit-run diagnostics correlation, use `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit doctor correlation` first to generate
deterministic command templates, then execute the emitted Grafana command.

```bash
# Generate templates and preflight checks from audit orchestrator
./scripts/worktree_uv.sh run --project audit_orchestrator \
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --json-only doctor correlation \
  --since 30m \
  --service "<SERVICE_NAME>" \
  --audit-id "<THREAD_OR_REQUEST_ID>" \
  --run-health

# Direct Grafana command shape generated by doctor correlation
./scripts/worktree_uv.sh run --project grafana_orchestrator \
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana --json-only search \
  --query "(service_name:\"<SERVICE_NAME>\" OR service.name:\"<SERVICE_NAME>\") AND (severity_text:ERROR OR severity_text:FATAL OR severity_text:CRITICAL) AND (audit_id:\"<THREAD_OR_REQUEST_ID>\" OR request_id:\"<THREAD_OR_REQUEST_ID>\" OR trace_id:\"<THREAD_OR_REQUEST_ID>\")" \
  --since 30m \
  --limit 200
```

Keep Grafana credentials in the shared VDS env file using `VDS_GRAFANA_*` keys.

## Python API Usage

### Basic Usage

```python
from vds_grafana_orchestrator import QuickwitClient, load_settings

# Load settings from the shared VDS env file
settings = load_settings()

# Use context manager for automatic cleanup
with QuickwitClient(settings) as client:
    # Health check
    health = client.health()
    print(f"Grafana OK: {health['grafana_ok']}")
    print(f"Datasource OK: {health['datasource_ok']}")
    
    # Search logs
    results = client.search(
        index="otel-logs-v0_7",
        query="severity_text:ERROR",
        max_hits=100
    )
    print(f"Found {results['num_hits']} results")
    
    for hit in results["hits"]:
        print(f"  {hit.get('severity_text')}: {hit.get('body')}")
```

### Advanced Search

```python
from vds_grafana_orchestrator import QuickwitClient, load_settings
import time

settings = load_settings()

with QuickwitClient(settings) as client:
    # Search with time range
    now = int(time.time())
    one_hour_ago = now - 3600
    
    results = client.search(
        index="otel-logs-v0_7",
        query="service_name:payment-service AND severity_text:ERROR",
        start_timestamp=one_hour_ago,
        end_timestamp=now,
        max_hits=50,
        sort_by_field="timestamp",
        sort_order="desc"
    )
    
    # Search with context (expand time window around a point)
    context_results = client.search_with_context(
        index="otel-logs-v0_7",
        query="trace_id:abc123",
        at_timestamp=1705320000,
        before_seconds=120,  # 2 minutes before
        after_seconds=120,   # 2 minutes after
    )
```

### ES-Compatible Query DSL

```python
from vds_grafana_orchestrator import QuickwitClient, load_settings

settings = load_settings()

with QuickwitClient(settings) as client:
    # Bool query with must and filter
    results = client.es_search(
        index="otel-logs-v0_7",
        body={
            "query": {
                "bool": {
                    "must": [
                        {"match": {"service_name": "api-gateway"}}
                    ],
                    "filter": [
                        {"range": {"timestamp": {"gte": "now-1h"}}}
                    ]
                }
            }
        },
        size=100
    )
    
    # Access results
    hits = results["hits"]["hits"]
    for hit in hits:
        source = hit["_source"]
        print(f"{source.get('timestamp')}: {source.get('body')}")
```

### Low-Level Grafana Client

```python
from vds_grafana_orchestrator import GrafanaClient, load_settings

settings = load_settings()

with GrafanaClient(settings) as client:
    # Check Grafana health
    health = client.health()
    
    # List all datasources
    datasources = client.datasources()
    
    # List Quickwit datasources only
    quickwit_ds = client.quickwit_datasources()
    
    # Resolve datasource by UID, ID, or name
    ds = client.resolve_datasource(uid="my-datasource-uid")
    ds = client.resolve_datasource(datasource_id=1)
    ds = client.resolve_datasource(name="Quickwit Logs")
    
    # Direct proxy requests
    result = client.proxy_get(
        datasource_uid="my-datasource-uid",
        path="otel-logs-v0_7/search",
        params={"query": "*", "max_hits": 10}
    )
```

### Error Handling

```python
from vds_grafana_orchestrator import (
    QuickwitClient,
    load_settings,
    GrafanaAuthError,
    GrafanaNotFoundError,
    GrafanaTimeoutError,
    GrafanaClientError,
)

settings = load_settings()

try:
    with QuickwitClient(settings) as client:
        results = client.search(index="otel-logs-v0_7", query="*")
except GrafanaAuthError as e:
    print(f"Authentication failed: {e}")
    print("Check VDS_GRAFANA_USER/PASSWORD or VDS_GRAFANA_TOKEN")
except GrafanaNotFoundError as e:
    print(f"Resource not found: {e}")
    print("Check VDS_GRAFANA_DATASOURCE_UID")
except GrafanaTimeoutError as e:
    print(f"Request timed out: {e}")
except GrafanaClientError as e:
    print(f"Client error: {e}")
```

## Troubleshooting

### VPN Required

Grafana is typically hosted on internal networks. Ensure VPN is connected:

```bash
# Test connectivity
curl -I http://10.207.58.64:8485/api/health

# If connection refused or timeout, check VPN
```

### Authentication Issues

**Symptom:** `401 Unauthorized` or `GrafanaAuthError`

**Solutions:**
1. Verify credentials in the shared VDS env file:
   ```bash
   env | grep VDS_GRAFANA
   ```

2. Test credentials manually:
   ```bash
   # Basic Auth
   curl -u "user:password" http://10.207.58.64:8485/api/health
   
   # Token Auth
   curl -H "Authorization: Bearer your-token" http://10.207.58.64:8485/api/health
   ```

3. Ensure you're using either Basic Auth OR Token, not both

### Datasource Not Found

**Symptom:** `404 Not Found` or `GrafanaNotFoundError`

**Solutions:**
1. List available datasources:
   ```bash
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana datasources
   ```

2. Check `VDS_GRAFANA_DATASOURCE_UID` matches an existing datasource

3. If using auto-discovery, ensure at least one Quickwit datasource exists

### Permission Denied

**Symptom:** `403 Forbidden` or `GrafanaPermissionError`

**Solutions:**
1. Verify user has access to the datasource in Grafana UI
2. Check datasource permissions in Grafana > Data Sources > Permissions
3. Ensure the datasource is not restricted to specific teams/orgs

### Connection Timeout

**Symptom:** `GrafanaTimeoutError`

**Solutions:**
1. Check VPN connectivity
2. Increase timeout settings:
   ```bash
   export VDS_GRAFANA_CONNECT_TIMEOUT=30
   export VDS_GRAFANA_REQUEST_TIMEOUT=60
   ```
3. Check if Grafana is under heavy load

### SSL Certificate Errors

**Symptom:** SSL verification failures

**Solutions:**
1. For self-signed certificates (default):
   ```bash
   export VDS_GRAFANA_VERIFY_CERTS=false
   ```
2. For production with valid certs:
   ```bash
   export VDS_GRAFANA_VERIFY_CERTS=true
   ```

### Empty Search Results

**Symptom:** Search returns no hits when data exists

**Solutions:**
1. Verify index name is correct:
   ```bash
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana indexes
   ```
2. Check time range - data may be outside the search window
3. Verify query syntax:
   ```bash
   # Simple wildcard to test
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana search --index otel-logs-v0_7 --query "*" --limit 1
   ```
4. Check field names:
   ```bash
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana fields --index otel-logs-v0_7
   ```

## Development

### Running Tests

```bash
cd WHO-project/vds-scripts/grafana_orchestrator

# Run all tests
./scripts/worktree_uv.sh run --project grafana_orchestrator pytest

# Run with coverage
./scripts/worktree_uv.sh run --project grafana_orchestrator pytest --cov

# Run specific test file
./scripts/worktree_uv.sh run --project grafana_orchestrator pytest tests/test_client.py

# Run verification tests (requires real credentials)
./scripts/worktree_uv.sh run --project grafana_orchestrator pytest -m verification
```

### Linting

```bash
# Check code style
./scripts/worktree_uv.sh run --project grafana_orchestrator ruff check .

# Auto-fix issues
./scripts/worktree_uv.sh run --project grafana_orchestrator ruff check --fix .

# Format code
./scripts/worktree_uv.sh run --project grafana_orchestrator ruff format .
```

### Type Checking

```bash
./scripts/worktree_uv.sh run --project grafana_orchestrator mypy src/vds_grafana_orchestrator
```

## Related Documentation

- [VDS Scripts README](../README.md) - Parent orchestrator documentation
- [Elastic Orchestrator](../elastic_orchestrator/README.md) - Similar pattern for Elasticsearch
- [AGENTS.md](../../../AGENTS.md) - VDS development standards and workflows

## Version

Current version: **0.1.0**

## License

MIT License - See [LICENSE](LICENSE) for details.
.
