<!-- diátaxis: reference -->

# Common Errors

## CLI Errors

### `ModuleNotFoundError: No module named 'xxx'`

**Cause:** Dependency not installed or wrong venv.

**Fix:**
```bash
uv sync
source .venv/bin/activate
```

**Prevention:** Always run `uv sync` after pulling changes.

### `subprocess.CalledProcessError: uv run ...`

**Cause:** Orchestrator entry point not installed.

**Fix:**
```bash
# Reinstall orchestrator
cd <orchestrator_dir> && uv pip install -e .
```

**Prevention:** Run `uv sync` from vds-scripts root after any orchestrator changes.

## Validation Errors

### `ValidationError: 1 validation error for Settings`

**Cause:** Missing or invalid environment variable.

**Fix:**
```bash
# Check required vars
vds-cli env status

# Set missing var
export CONFLUENCE_INTERNAL_URL=https://confluence.example.com
```

**Prevention:** Use the annotated `~/.vds/.env` template from [Configuration Reference](../reference/configuration-reference.md).

## Database Errors

### `Connection refused: postgres:5432`

**Cause:** Postgres container not running.

**Fix:**
```bash
docker compose up -d postgres
```

**Prevention:** Add `docker compose ps` to your startup checklist.

### `sqlalchemy.exc.ProgrammingError: relation "xxx" does not exist`

**Cause:** Schema not initialized.

**Fix:**
```bash
# Run migrations (if available)
vds-cli db-query --run-migrations
```

## External API Errors

### `401 Unauthorized: Confluence`

**Cause:** Token invalid or expired.

**Fix:**
```bash
# Generate new token in Confluence UI
# Update ~/.vds/.env
```

**Prevention:** Set a calendar reminder to rotate tokens every 90 days.

### `Connection timeout: SonarQube`

**Cause:** SonarQube server unreachable.

**Fix:**
```bash
# Check connectivity
curl -I $SONARQUBE_URL

# Verify VPN if required
```

## Git Errors

### `fatal: not a git repository`

**Cause:** Running git command outside a repo.

**Fix:**
```bash
cd /path/to/git/repo
# or
vds-cli git worktree-list
```

### `error: pathspec 'branch-name' did not match`

**Cause:** Branch does not exist.

**Fix:**
```bash
# List branches
git branch -a

# Create branch
git checkout -b branch-name
```

## See Also

- [Troubleshooting Guide](../how-to/troubleshooting-guide.md)
- [Configuration Reference](../reference/configuration-reference.md)
