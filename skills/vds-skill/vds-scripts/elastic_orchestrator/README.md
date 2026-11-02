# VDS Elastic Orchestrator

VDS Elasticsearch orchestrator via Kibana Console Proxy.

## Overview

This orchestrator provides CLI and programmatic access to the VDS Elasticsearch cluster through Kibana's Console Proxy API. Direct Elasticsearch access (port 9200) is not available in the VDS environment, so all operations are routed through Kibana.

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic CLI │ --> │  Kibana Console  │ --> │  Elasticsearch   │
│  or Python API   │     │  Proxy API       │     │  Cluster (8.x)   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │
        │                        │ POST /api/console/proxy
        │                        │   ?path=<es_path>&method=<method>
        │                        │
        └── HTTPS ──────────────→│
            Host: log.digital.vn
            IP: 10.207.56.26
```

### Key Constraints

- **No Direct ES Access**: Port 9200 is not exposed externally
- **Kibana Console Proxy**: All ES operations via `/api/console/proxy`
- **DNS Resolution**: `log.digital.vn` resolves to unreachable public IP; must use internal IP with `Host` header
- **Authentication**: Basic auth only (no API key support via Kibana)
- **User Permissions**: `dev` user has `viewer` role - can search but cannot perform cluster monitoring operations

## Installation

```bash
cd WHO-project/vds-scripts/elastic_orchestrator

# Install dependencies with uv
uv sync

# Install with dev dependencies
uv sync --group dev
```

## Configuration

### Environment Variables

Add these to the shared VDS env file:

```bash
# Required - Kibana Proxy Settings
VDS_ELASTIC_KIBANA_URL="log.digital.vn"   # Hostname for Host header
VDS_ELASTIC_KIBANA_IP="10.207.56.26"      # Internal IP for connection
VDS_ELASTIC_USER="dev"                     # Username for basic auth
VDS_ELASTIC_PASSWORD="your-password"       # Password for basic auth

# Optional - Timeouts & Retry
VDS_ELASTIC_CONNECT_TIMEOUT="10"           # Connection timeout (seconds)
VDS_ELASTIC_REQUEST_TIMEOUT="30"           # Read timeout (seconds)
VDS_ELASTIC_MAX_RETRIES="3"                # Max retry attempts for 502/503/504
VDS_ELASTIC_RETRY_BACKOFF="1.0"            # Exponential backoff multiplier
VDS_ELASTIC_VERIFY_CERTS="false"           # SSL verification (false for self-signed)

# Optional - Search Defaults
VDS_ELASTIC_DEFAULT_INDEX="*"              # Default index pattern
VDS_ELASTIC_DEFAULT_TIME_FIELD="@timestamp" # Default time field
VDS_ELASTIC_DEFAULT_SIZE="10"              # Default result size
```

## CLI Usage

### Global Options

```bash
# JSON-only mode (compact JSON, no decoration - ideal for scripting)
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic --json-only search --index "logs-*"
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic --json-only count

# Structured logs to stderr
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic --structured-logs search --index "logs-*"

# Show version
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic --version
```

### Via Direct Script

```bash
# Test connectivity
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic ping

# Check Kibana status
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic kibana-status

# Show current user and roles
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic user-info

# Search documents
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic search --index "logs-*" --size 5
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic search --query '{"match": {"message": "error"}}'
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic search --qs "level:ERROR AND timeout"

# Search with time range
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic search \
    --index "logs-*" \
    --start "2025-01-15T00:00:00Z" \
    --end "2025-01-16T00:00:00Z" \
    --time-field "@timestamp"

# Count documents
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic count --index "logs-*"
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic count --qs "level:ERROR"

# Export large datasets (scroll-based)
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic export --index "logs-*" -o export.ndjson
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic export --qs "level:ERROR" --max 10000 -o errors.ndjson
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic export --index "logs-*" --source-only -o data.ndjson
```

### Via vds-cli Router

```bash
# After vds-cli integration
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic -- ping
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic -- search --index "logs-*"
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic -- count
```

## Audit Correlation Integration (Phase 68c)

Use `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit doctor correlation` to generate deterministic Elastic/Kibana query templates
for one audit run, then execute the emitted `vds-elastic` command.

```bash
# Generate runtime + Grafana + Elastic correlation templates
./scripts/worktree_uv.sh run --project audit_orchestrator \
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --json-only doctor correlation \
  --since 30m \
  --service "<SERVICE_NAME>" \
  --audit-id "<THREAD_OR_REQUEST_ID>" \
  --run-health

# Direct Elastic command shape generated by doctor correlation
./scripts/worktree_uv.sh run --project elastic_orchestrator \
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic --json-only search \
  --index "*" \
  --qs "(service_name:\"<SERVICE_NAME>\" OR service.name:\"<SERVICE_NAME>\") AND (level:ERROR OR log.level:ERROR OR severity_text:ERROR) AND (audit_id:\"<THREAD_OR_REQUEST_ID>\" OR request_id:\"<THREAD_OR_REQUEST_ID>\" OR trace_id:\"<THREAD_OR_REQUEST_ID>\" OR trace.id:\"<THREAD_OR_REQUEST_ID>\")" \
  --start "<START_ISO_UTC>" \
  --end "<END_ISO_UTC>" \
  --size 200 \
  --sort "@timestamp:desc"
```

Keep Kibana/Elastic credentials in the shared VDS env file using `VDS_ELASTIC_*` keys.

### Admin Commands (require monitor privilege)

These commands may fail with 403 for users with `viewer` role:

```bash
# Cluster info
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic info

# Cluster health
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic health

# List indices
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic indices --pattern "logs-*"

# List aliases
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic aliases --pattern "logs*"
```

## Python API Usage

```python
from vds_elastic_orchestrator import load_settings, KibanaElasticsearchClient

# Load settings from environment
settings = load_settings()

# Use as context manager
with KibanaElasticsearchClient(settings) as client:
    # Test connectivity
    if client.ping():
        print("Connected to Elasticsearch")
    
    # Search documents
    result = client.search(
        index="logs-*",
        query={"match": {"message": "error"}},
        size=10,
    )
    print(f"Found {result['hits']['total']['value']} documents")
    
    # Count documents
    count = client.count(index="logs-*")
    print(f"Total documents: {count['count']:,}")
    
    # Get user info
    user = client.user_info()
    print(f"Authenticated as: {user['username']}")
    print(f"Roles: {', '.join(user['roles'])}")

    # Get single document by ID
    doc = client.get_document("logs-2025.01.15", "doc123")
    print(f"Document found: {doc['found']}")

    # Multi-get documents
    docs = client.mget(index="logs", ids=["doc1", "doc2", "doc3"])
    for d in docs["docs"]:
        print(f"  {d['_id']}: found={d['found']}")

    # Field capabilities
    caps = client.field_caps(index="logs-*", fields=["message", "@timestamp"])
    for field, info in caps["fields"].items():
        print(f"  {field}: {list(info.keys())}")

    # Multi-search (batch queries)
    results = client.msearch([
        ({"index": "logs-*"}, {"query": {"match": {"level": "ERROR"}}}),
        ({"index": "metrics-*"}, {"query": {"range": {"value": {"gt": 100}}}}),
    ])
    for i, resp in enumerate(results["responses"]):
        print(f"  Query {i}: {resp['hits']['total']['value']} hits")
```

### Deep Pagination (Large Datasets)

For retrieving large result sets beyond the 10,000 document limit:

```python
from vds_elastic_orchestrator import load_settings, KibanaElasticsearchClient

settings = load_settings()

with KibanaElasticsearchClient(settings) as client:
    # Option 1: search_after for keyset pagination
    result = client.search(
        index="logs-*",
        size=1000,
        sort=[{"@timestamp": "asc"}, {"_id": "asc"}],
    )
    
    while result["hits"]["hits"]:
        for doc in result["hits"]["hits"]:
            process(doc)
        
        # Get last document's sort values for next page
        last_hit = result["hits"]["hits"][-1]
        result = client.search(
            index="logs-*",
            size=1000,
            sort=[{"@timestamp": "asc"}, {"_id": "asc"}],
            search_after=last_hit["sort"],
        )
    
    # Option 2: Scroll API for point-in-time snapshots
    result = client.scroll_search(index="logs-*", size=1000)
    scroll_id = result["_scroll_id"]
    
    try:
        while result["hits"]["hits"]:
            for doc in result["hits"]["hits"]:
                process(doc)
            result = client.scroll(scroll_id)
            scroll_id = result["_scroll_id"]
    finally:
        client.clear_scroll(scroll_id)
    
    # Option 3: scan() helper - simplest approach
    for doc in client.scan(index="logs-*", size=1000):
        process(doc)
        # Automatically handles scroll management and cleanup
```

## Permission Limitations

The `dev` user has limited permissions (`viewer` role):

| Operation | Status | Notes |
|-----------|--------|-------|
| `search` | ✅ Works | Can search all indices |
| `count` | ✅ Works | Can count documents |
| `ping` | ✅ Works | Can test connectivity |
| `user-info` | ✅ Works | Can view own user info |
| `kibana-status` | ✅ Works | Can view Kibana status |
| `export` | ✅ Works | Scroll-based export to ndjson |
| `info` | ⚠️ May fail | Requires `monitor` privilege |
| `health` | ⚠️ May fail | Requires `monitor` privilege |
| `indices` | ⚠️ May fail | Requires `monitor` privilege |
| `aliases` | ⚠️ May fail | Requires `monitor` privilege |

When a permission error occurs, the CLI displays helpful information:

```
✗ Error: Permission denied for cluster health
  Hint: Required roles: monitoring_user, superuser. Current role 'viewer' may not have this permission.
```

## Curl Examples

For debugging, you can use curl directly with Kibana Console Proxy:

```bash
# Base URL and auth
KIBANA_IP="10.207.56.26"
KIBANA_HOST="log.digital.vn"
AUTH="dev:your-password"

# Search via console proxy
curl -k -X POST "https://${KIBANA_IP}/api/console/proxy?path=%2Flogs-*%2F_search&method=POST" \
    -H "Host: ${KIBANA_HOST}" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -u "${AUTH}" \
    -d '{"size": 1, "query": {"match_all": {}}}'

# Count documents
curl -k -X POST "https://${KIBANA_IP}/api/console/proxy?path=%2F*%2F_count&method=POST" \
    -H "Host: ${KIBANA_HOST}" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -u "${AUTH}" \
    -d '{}'

# Kibana status
curl -k -X GET "https://${KIBANA_IP}/api/status" \
    -H "Host: ${KIBANA_HOST}" \
    -u "${AUTH}"
```

## Error Handling

The orchestrator provides specific error types for different scenarios:

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| `ElasticAuthError` | 401 | Invalid credentials |
| `ElasticPermissionError` | 403 | Insufficient privileges |
| `ElasticQueryError` | 400 | Invalid query syntax |
| `ElasticTransportError` | - | Network/connection issues |
| `ElasticTimeoutError` | - | Request timeout |
| `ElasticRetryError` | 502/503/504 | All retry attempts failed |
| `ElasticResponseError` | 4xx/5xx | Other HTTP errors |

## Retry Logic

The client automatically retries transient errors with exponential backoff:

- **Retryable status codes**: 502, 503, 504
- **Non-retryable**: 401, 403, 404, 400, 500
- **Default max retries**: 3
- **Backoff multiplier**: 1.0 (exponential: 1s, 2s, 4s, ...)

Configure via environment variables:

```bash
VDS_ELASTIC_MAX_RETRIES="5"
VDS_ELASTIC_RETRY_BACKOFF="2.0"
```

## Development

### Running Tests

```bash
cd elastic_orchestrator

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=vds_elastic_orchestrator

# Run specific test file
uv run pytest tests/test_client.py -v
```

### Linting and Formatting

```bash
# Check linting
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/
```

## Project Structure

```
elastic_orchestrator/
├── pyproject.toml              # Package configuration
├── README.md                   # This file
├── src/
│   └── vds_elastic_orchestrator/
│       ├── __init__.py         # Package exports
│       ├── cli.py              # Typer CLI commands
│       ├── client.py           # KibanaElasticsearchClient
│       ├── config.py           # ElasticSettings (pydantic-settings)
│       ├── errors.py           # Error hierarchy
│       └── py.typed            # PEP 561 type marker
└── tests/
    ├── conftest.py             # Pytest fixtures
    ├── test_client.py          # Client tests
    ├── test_config.py          # Config tests
    └── test_errors.py          # Error hierarchy tests
```

## Troubleshooting

### Connection Refused

If you see "Connection refused" errors:

1. Verify you're on the VDS internal network or VPN
2. Check the Kibana IP is correct: `ping 10.207.56.26`
3. Verify credentials in the shared VDS env file

### SSL Certificate Errors

The VDS Kibana uses self-signed certificates. By default, SSL verification is disabled (`VDS_ELASTIC_VERIFY_CERTS=false`).

### Permission Denied (403)

For `viewer` role users, certain operations like cluster health and indices listing are not available. Use `user-info` to check your current roles:

```bash
uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic user-info
```

### Timeout Errors

For large queries, increase the timeout:

```bash
VDS_ELASTIC_REQUEST_TIMEOUT="60" uv run ./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic search --index "logs-*" --size 1000
```

## Related Documentation

- [VDS Scripts Overview](../docs/README.md)
- [Spec: elastic-orchestrator](../../.kiro/specs/elastic-orchestrator/)
- [Bitbucket Orchestrator](../bitbucket_orchestrator/) (reference pattern)
- [Confluence Orchestrator](../confluence_orchestrator/) (reference pattern)
