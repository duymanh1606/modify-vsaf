<!-- diátaxis: how-to -->

# Troubleshooting Guide

## Quick Diagnostic

```bash
# Run the doctor command
vds-cli doctor
```

## CLI Failures

### `vds-cli: command not found`

**Cause:** Not in PATH or not installed.

**Fix:**
```bash
# Verify uv sync completed
uv sync

# Check PATH includes .venv/bin
which vds-cli || echo "Not in PATH"
```

### `uv sync` fails with resolution error

**Cause:** Dependency conflict or outdated lock file.

**Fix:**
```bash
# Update lock file
uv lock

# If still failing, clear cache
uv cache clean
uv sync
```

### Orchestrator command returns nothing

**Cause:** Orchestrator not registered or entry point missing.

**Fix:**
```bash
# Check orchestrator registration
vds-cli --help | grep <orchestrator>

# Verify entry point
which vds-<orchestrator>
```

## Test Failures

### `pytest` fails with DB connection error

**Cause:** Postgres or Redis not running.

**Fix:**
```bash
# Start services
docker compose up -d postgres redis

# Verify
docker compose ps
```

### Mock assertion fails

**Cause:** Mock not configured for the right module path.

**Fix:**
```python
# Correct: patch where the function is USED
@patch("my_module.external_api_call")
def test_something(mock_api):
    ...
```

## Sync Failures

### Confluence sync fails with 401

**Cause:** Token expired or incorrect.

**Fix:**
```bash
# Verify token
echo $INTERNAL_CONFLUENCE_TOKEN | head -c 20

# Regenerate in Confluence → Account Settings → Personal Access Tokens
# Update ~/.vds/.env
```

### Bitbucket operations timeout

**Cause:** Network issue or incorrect base URL.

**Fix:**
```bash
# Verify connectivity
curl -I $VDS_BITBUCKET_HTTP_BASE

# Check base URL in ~/.vds/.env
grep BITBUCKET ~/.vds/.env
```

## Phase 225 Embedding (Post 2026-04-26)

### Container won't start: Ollama unreachable

**Cause:** Memory orchestrator cannot reach local Ollama service (default at `host.docker.internal:11434`).

**Fix:**
```bash
# Check if Ollama is running on host
curl -I http://host.docker.internal:11434/api/tags

# If 404/timeout, start Ollama or switch to cloud provider
# Switch to OpenAI (example)
cat ~/.vds/.env | grep -E "VDS_AGENT_CORE_EMBED__"

# Update for OpenAI
cat >> ~/.vds/.env <<'EOF'
VDS_AGENT_CORE_EMBED__PROVIDER=openai
VDS_AGENT_CORE_EMBED__BASE_URL=https://api.openai.com/v1
VDS_AGENT_CORE_EMBED__API_KEY=sk-...
VDS_AGENT_CORE_EMBED__MODEL_STANDARD=text-embedding-3-large
VDS_AGENT_CORE_EMBED__DIMENSION=1024
EOF

# Restart memory orchestrator
docker compose -p vds-platform restart memory-api memory-worker
```

### Dimension mismatch on cloud switch

**Cause:** Switching embedding providers without dimension validation enabled.

**Fix:**
```bash
# Verify current Qdrant collection dimension
vds-cli memory admin list-collections

# If switching models and dimension changes are required:
# 1. Stop memory orchestrator
docker compose -p vds-platform stop memory-api memory-worker

# 2. Drop existing collection (destructive!)
vds-cli memory admin drop-collection --collection vds_memories --confirm

# 3. Update ~/.vds/.env with new dimension
# (see Phase 225 Embedding section above)

# 4. Verify dimension configuration
vds-cli doctor  # should show no warnings about dimension verification
```

**Prevention:** Always check provider dimension defaults before switching.
- Ollama/bge-m3: 1024 (default VDS baseline)
- OpenAI/text-embedding-3-small: 1536 (no truncation)
- OpenAI/text-embedding-3-large: 3072 (truncate to 1024 with matryoshka)

### Image size larger than expected (clear stale layers)

**Cause:** Docker build cache contains stale embedding/ML layers from previous provider (sentence-transformers, etc.).

**Fix:**
```bash
# Clean Docker build cache (affects all projects)
docker builder prune -a

# Or rebuild memory-api image from scratch
docker compose -p vds-platform build --no-cache memory-api memory-worker

# Verify Phase 225 image is lean (should be ~10 GB, not 27+ GB)
docker images vds-memory-api --format 'table {{.Repository}}\t{{.Size}}'
```

## Environment Issues

### `~/.vds/.env` not loading

**Cause:** File permissions or wrong location.

**Fix:**
```bash
# Verify file exists and is readable
ls -la ~/.vds/.env

# Check env loading
vds-cli env status
```

### Docker services not starting

**Cause:** Port conflicts or missing images.

**Fix:**
```bash
# Check port usage
lsof -i :5432  # Postgres
lsof -i :6379  # Redis

# Pull images
docker compose pull
```

## Escalation Path

| Severity | Channel | Information to Provide |
|----------|---------|----------------------|
| Minor | Fix yourself using this guide | — |
| Moderate | Ask in team Slack | Command, error output, `vds-cli doctor` |
| Critical | File incident | All of the above + timeline, impact |

## See Also

- [Common Errors](../reference/common-errors.md)
- [Configuration Reference](../reference/configuration-reference.md)
