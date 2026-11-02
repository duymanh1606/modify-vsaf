<!-- diátaxis: reference -->
# Migration Playbook

Canonical migration commands for each orchestrator. All use the standard Compose
merge pattern from ADR-INF-10 v2.15.10:

```bash
docker compose -p vds-platform \
               -f docker/docker-compose.infra.yml \
               -f docker/docker-compose.services.yml \
               -f docker/docker-compose.cli.yml \
               --profile <profile> \
               run --rm --no-deps ...
```

## Auto-Migrate Entrypoints

| Service | Auto-Upgrade | Method |
|---------|-------------|--------|
| **scheduler** | YES | entrypoint.sh with advisory lock + two-DSN |
| **memory** | YES (v2.16.0+) | entrypoint.sh with advisory lock + two-DSN |

These containers run `alembic upgrade head` on start via entrypoint. No explicit
operator action needed.

## Explicit Migration Commands

Services with ENTRYPOINT set on their primary command require `--entrypoint`
override to run alembic.

### Audit

```bash
docker compose -p vds-platform \
    -f docker/docker-compose.infra.yml \
    -f docker/docker-compose.services.yml \
    -f docker/docker-compose.cli.yml \
    --profile audit \
    run --rm --no-deps --entrypoint /opt/venv/bin/alembic audit-orchestrator \
    -c /app/audit_orchestrator/alembic.ini upgrade head
```

### Progress Report

```bash
docker compose -p vds-platform \
    -f docker/docker-compose.infra.yml \
    -f docker/docker-compose.services.yml \
    -f docker/docker-compose.cli.yml \
    --profile progress \
    run --rm --no-deps --entrypoint /opt/venv/bin/alembic progress-report-orchestrator \
    -c /app/progress_report_orchestrator/alembic.ini upgrade head
```

## Profiles

| Profile | Services |
|---------|----------|
| audit | audit-orchestrator |
| pdf | pdf-orchestrator |
| progress | progress-report-orchestrator |
| db-query | db-query-orchestrator |
| vds-cli | unified router |
| mcp-server | MCP bridge |
| cli | all of the above |

## Two-DSN Model

For production deployments, set `MIGRATION_DATABASE_URL` to a superuser DSN for
DDL during alembic. The runtime uses `DATABASE_URL` (least-privilege). If
`MIGRATION_DATABASE_URL` is unset, entrypoints fall back to `DATABASE_URL`.
