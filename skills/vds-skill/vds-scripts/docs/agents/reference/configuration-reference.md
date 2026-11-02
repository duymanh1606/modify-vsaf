<!-- diátaxis: reference -->

# Configuration Reference

All WHO ecosystem configuration lives in `~/.vds/.env`. This file is loaded automatically by `vds-cli` and all orchestrators.

## Quick Template

```bash
# ~/.vds/.env
# Copy this template and fill in your values

# === Confluence ===
CONFLUENCE_INTERNAL_URL=https://confluence.internal.example.com
CONFLUENCE_EXTERNAL_URL=https://confluence.external.example.com
INTERNAL_CONFLUENCE_TOKEN=your_internal_token
EXTERNAL_CONFLUENCE_TOKEN=your_external_token
CONFLUENCE_USERNAME=your_username
CONFLUENCE_PASSWORD=your_password

# === Bitbucket ===
BITBUCKET_TOKEN=your_bitbucket_token
VDS_BITBUCKET_HTTP_BASE=https://bitbucket.example.com

# === AI Memory ===
VDS_AI_MEMORY_BASE_URL=http://localhost:8000
VDS_AI_MEMORY_API_KEY=your_api_key

# === General ===
VDS_USERNAME=your_username
VDS_PASSWORD=your_password
VDS_SKILLS_SYNC_DIR=/path/to/vds-skills
```

## Environment Variables

### Confluence

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONFLUENCE_INTERNAL_URL` | Yes | — | Internal Confluence base URL |
| `CONFLUENCE_EXTERNAL_URL` | Yes | — | External Confluence base URL |
| `INTERNAL_CONFLUENCE_TOKEN` | Yes* | — | Token for internal Confluence |
| `EXTERNAL_CONFLUENCE_TOKEN` | Yes* | — | Token for external Confluence |
| `CONFLUENCE_USERNAME` | Yes* | — | Username for basic auth |
| `CONFLUENCE_PASSWORD` | Yes* | — | Password for basic auth |
| `CONFLUENCE_RETRY_BACKOFF` | No | 1.0 | Retry backoff initial (seconds) |
| `CONFLUENCE_HTTP_TIMEOUT` | No | 30.0 | HTTP read timeout (seconds) |

*Either token-based or username/password auth is required.

### Bitbucket

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BITBUCKET_TOKEN` | Yes | — | Personal access token |
| `VDS_BITBUCKET_HTTP_BASE` | No | — | Bitbucket server base URL |

### AI Memory

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VDS_AI_MEMORY_BASE_URL` | No | — | Memory service URL |
| `VDS_AI_MEMORY_API_KEY` | No | — | API key for memory service |

### General

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VDS_USERNAME` | No | — | Default username for services |
| `VDS_PASSWORD` | No | — | Default password for services |
| `VDS_SKILLS_SYNC_DIR` | No | — | Path to vds-skills checkout |

## Per-Service Configuration

### Audit Orchestrator
Uses Confluence and Postgres credentials. No additional env vars required.

### Progress Report Orchestrator
Uses Postgres and Redis. Connection strings are configured in the orchestrator's config module.

### Telegram Bridge
Uses the general `VDS_USERNAME`/`VDS_PASSWORD` for authentication with the Telegram bot API. Bot tokens are stored separately in the Telegram configuration.

### Scheduler
Uses Redis for job queue state. Connection configured in `SCHEDULER_REDIS_URL` (if set) or defaults to `redis://localhost:6379`.

### Embedding (Phase 225+)
Pluggable embedding providers (Ollama, OpenAI, Cohere, Voyage, Mistral, Jina, local, hash).
Core prefix: `VDS_AGENT_CORE_EMBED__*`. Per-orchestrator subclasses use custom prefixes (e.g. `VDS_AUDIT_EMBED__*`).
See [Embedding Architecture](../../vds_agent_core/docs/embedding.md) for full provider reference, dimension constraints, and cloud-failover playbooks.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VDS_AGENT_CORE_EMBED__PROVIDER` | No | `ollama` | Provider name (ollama, openai, cohere, voyage, mistral, jina, local, hash) |
| `VDS_AGENT_CORE_EMBED__BASE_URL` | No | — | Provider API endpoint (unused for local/hash) |
| `VDS_AGENT_CORE_EMBED__API_KEY` | No | — | Provider API key (cloud providers only) |
| `VDS_AGENT_CORE_EMBED__MODEL_STANDARD` | No | `bge-m3` | Embedding model name |
| `VDS_AGENT_CORE_EMBED__DIMENSION` | No | 1024 | Vector dimension (validated against provider defaults) |
| `VDS_AGENT_CORE_EMBED__TIMEOUT_SECONDS` | No | 30 | HTTP timeout for provider calls |
| `VDS_AGENT_CORE_EMBED__VERIFY_DIM_AGAINST_QDRANT` | No | `true` | Validate dimension vs live Qdrant collection |

## Troubleshooting Configuration

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `vds-cli` cannot find orchestrators | `VDS_SKILLS_SYNC_DIR` missing | Set to absolute path of vds-skills checkout |
| Confluence sync fails with 401 | Token expired | Regenerate token in Confluence user settings |
| Bitbucket operations fail | `BITBUCKET_TOKEN` missing or invalid | Create token in Bitbucket → Personal Access Tokens |
| AI Memory not connecting | `VDS_AI_MEMORY_BASE_URL` incorrect | Verify service is running: `curl $VDS_AI_MEMORY_BASE_URL/health` |

## Reloading Configuration

`vds-cli` reads `~/.vds/.env` on each invocation. No restart is required after editing.

```bash
# Edit the file
$EDITOR ~/.vds/.env

# Verify it's readable
vds-cli --help
```

## See Also

- [Quick Start](../tutorials/quick-start.md)
- [System Requirements](../reference/system-requirements.md)
- [Confluence Sync Reference](../reference/confluence-sync.md)
