# VDS Infrastructure Migration Guide

## Overview

This guide describes how to migrate VDS orchestrators from standalone infrastructure to the shared infrastructure model.

## Before You Start

### Prerequisites

1. Docker and Docker Compose installed
2. Access to the VDS monorepo
3. Understanding of current orchestrator configuration

### Pre-Migration Checklist

- [ ] Backup any existing data
- [ ] Note current environment variables
- [ ] Identify port conflicts
- [ ] Review schema requirements

## Migration Steps

### Step 1: Stop Existing Services

First, stop any running standalone services:

```bash
# Stop standalone infrastructure (legacy compose files retired in P3/P4 WP-4.0,
# directory `docker/legacy/` REMOVED in v2.15.12 per no-legacy directive). If
# you still have legacy compose files in their original locations, run:
docker compose -f audit_orchestrator/docker-compose.yml down 2>/dev/null || true
docker compose -f memory_orchestrator/compose.yaml down 2>/dev/null || true
docker compose -f pdf_orchestrator/docker-compose.yml down 2>/dev/null || true
# If those files are also gone, recover from git history (see ROLLBACK.md §Scenario 1).
```

### Step 2: Start Shared Infrastructure

```bash
# Start shared infrastructure
docker compose -f docker/docker-compose.infra.yml --profile infra up -d

# Verify all services are healthy
docker ps | grep vds-
```

Expected containers:
- `vds-postgres`
- `vds-redis`
- `vds-qdrant`
- `vds-pgbouncer` (P8, ADR-INF-13)

### Step 3: Update Environment Variables

Update your environment configuration to use the shared infrastructure. Docker Compose automatically loads `~/.vds/.env` for all services.

**Option A: Use ~/.vds/.env (Recommended)**

Ensure your `~/.vds/.env` contains the P0 infrastructure variables:

```bash
# Add these to ~/.vds/.env if not already present
VDS_POSTGRES_PASSWORD=vds_postgres_secret
REDIS_CELERY_BROKER_DB=0
REDIS_MEMORY_CACHE_DB=1
REDIS_SESSION_STORE_DB=2
REDIS_ANALYTICS_DB=3
REDIS_SEARCH_CACHE_DB=4
REDIS_RATE_LIMITING_DB=5
REDIS_TOOL_DISCOVERY_DB=9
QDRANT_HOST=localhost
QDRANT_PORT=6335
```

**Option B: Use docker/infrastructure/.env**

```bash
# Copy the template
cp docker/infrastructure/.env.template docker/infrastructure/.env

# Edit with your actual credentials
nano docker/infrastructure/.env
```

**Environment File Loading Order:**

1. `~/.vds/.env` (user credentials, highest priority)
2. `docker/infrastructure/.env`
3. Shell environment variables
4. `docker compose -e VAR=value` overrides

Key changes:

| Old Variable | New Variable | Notes |
|--------------|--------------|-------|
| `VDS_AUDIT_STATE_DSN` | `VDS_AUDIT_STATE_DSN` | Update host to `vds-pgbouncer:6432` |
| `DATABASE_URL` | `DATABASE_URL` | Update to use PgBouncer stanza (e.g., `/vds_memory`) |
| `REDIS_URL` | `REDIS_URL` | Update host to `redis:6379` |

### Step 4: Update Docker Compose Files

> The "Replace:" blocks below show illustrative LEGACY configs (image tags
> reflect what was in operators' standalone compose files at cutover —
> historical state, not the target). The shared infra now uses
> `pgvector/pgvector:0.8.2-pg18` per spec v2.10.4; pull from
> `docker/docker-compose.infra.yml` rather than re-pinning here.

#### For Orchestrators Using Standalone Postgres

Replace:

```yaml
postgres:
  image: pgvector/pgvector:0.8.1-pg18
  ports:
    - "5434:5432"
```

With:

```yaml
networks:
  vds:
    external: true
    name: vds-internal
```

#### For Orchestrators Using Standalone Redis

Replace:

```yaml
redis:
  image: redis:8.6.2-alpine
  ports:
    - "6379:6379"
```

With:

```yaml
networks:
  vds:
    external: true
    name: vds-internal
```

#### Update DSN References

Old format:
```yaml
DATABASE_URL: postgresql://vds_user:vds_password@postgres:5432/vds_database
```

New format (post-P8 — routes through PgBouncer stanzas):
```yaml
DATABASE_URL: postgresql://postgres:${VDS_POSTGRES_PASSWORD}@vds-pgbouncer:6432/vds_memory
```

### Step 5: Verify Migration

Run the verification script:

```bash
python scripts/verify-infra-topology.py --profile infra
```

All checks should pass. If any fail, check the troubleshooting section.

### Step 6: Start Your Orchestrator

Pick the right pattern for your orchestrator type (per ADR-INF-10):

```bash
# Long-running service (Tier 2; e.g., memory, scheduler, multi-agent)
make up-memory          # or up-scheduler / up-multi-agent / up-services

# CLI container (Tier 3; audit, pdf, progress, db-query — one-shot, exits 0)
make run-audit ARGS="workflow run --project <name>"
make run-pdf   ARGS="merge a.pdf b.pdf -o c.pdf"
# Equivalent direct compose form for CLI:
docker compose -p vds-platform \
  -f docker/docker-compose.infra.yml \
  -f docker/docker-compose.cli.yml \
  --profile audit run --rm audit-orchestrator workflow run --project <name>
```

> Note: audit/pdf/progress/db-query moved from `docker-compose.services.yml`
> to `docker-compose.cli.yml` in v2.10.0 (ADR-INF-10). Earlier instructions
> using `--profile audit up -d` against `services.yml` will fail to find
> the audit-orchestrator service.

### Step 7 — Data Migration (legacy → shared schemas)

This section was added in v2.0.0 of the spec after rollout exposed the gap. It covers
restoring `pg_dump` snapshots taken in TSK-0.1.5 into the shared `vds_platform` cluster
under the correct schemas.

#### 7.1 — Take pre-cutover snapshots (TSK-0.1.5)

```bash
mkdir -p docker/backups

# Memory (legacy ai-memory-postgres on 5432, user vds_user, db vds_memory + vds_scheduler)
docker exec vds-ai-memory-postgres-1 pg_dump -U vds_user -d vds_memory    -F c -f /tmp/pre-p0-memory.dump
docker exec vds-ai-memory-postgres-1 pg_dump -U vds_user -d vds_scheduler -F c -f /tmp/pre-p0-scheduler.dump
docker cp vds-ai-memory-postgres-1:/tmp/pre-p0-memory.dump    docker/backups/
docker cp vds-ai-memory-postgres-1:/tmp/pre-p0-scheduler.dump docker/backups/

# Audit (legacy audit-postgres on 5434, user vds_audit, db vds_audit_checkpoints + vds_progress)
docker exec vds-audit-postgres pg_dump -U vds_audit -d vds_audit_checkpoints -F c -f /tmp/pre-p0-audit.dump
docker exec vds-audit-postgres pg_dump -U vds_audit -d vds_progress           -F c -f /tmp/pre-p0-progress.dump
docker cp vds-audit-postgres:/tmp/pre-p0-audit.dump    docker/backups/
docker cp vds-audit-postgres:/tmp/pre-p0-progress.dump docker/backups/
```

#### 7.2 — Restore into shared schemas (RECOMMENDED: pg_restore + ALTER SET SCHEMA)

The legacy dumps store tables in the `public` schema. The shared cluster expects
each domain in its own schema (`audit_state`, `memory`, `sched`, `progress`).

**Recommended approach** (verified working in 2026-04-25 rollout): use `pg_restore`
to load the binary dump directly into `vds_platform.public`, then `ALTER ... SET SCHEMA`
each relation to its target schema. This bypasses two pitfalls that `sed`-based
rewriting hits:

- PG18 `\restrict` mode in `psql -f` blocks dump replay through pipes.
- Literal `s/public\./<target>./g` corrupts SQL when `public.` appears inside
  COMMENTs, CHECK constraints, or function bodies (real-world example: a column
  comment containing `"if cloud event-poll times out then mem0_status reaches
  local..."` triggered a `syntax error at or near "if"` during memory restore).

```bash
# Copy dumps into the new shared postgres container
for d in pre-p0-memory.dump pre-p0-scheduler.dump pre-p0-progress.dump pre-p0-audit.dump; do
  docker cp docker/backups/$d vds-postgres:/tmp/$d
done

# Restore each dump into vds_platform.public, then move to target schema.
# Tables move one-by-one; sequences owned by tables auto-follow; partitioned
# tables (relkind='p') need explicit handling.
docker exec -i vds-postgres bash <<'BASH'
set -e
for pair in "memory:memory" "sched:scheduler" "progress:progress" "audit_state:audit"; do
  TARGET_SCHEMA=$(echo $pair | cut -d: -f1)
  DUMP_NAME=$(echo $pair | cut -d: -f2)
  echo "=== Restoring $DUMP_NAME -> schema:$TARGET_SCHEMA ==="

  # Restore directly into vds_platform.public (binary format avoids \restrict)
  pg_restore --no-owner --no-acl --no-comments -U postgres -d vds_platform \
    /tmp/pre-p0-${DUMP_NAME}.dump 2>&1 | tail -3

  # Move all public.* relations to the target schema.
  # Order matters: tables (sequences auto-follow) -> matviews -> views -> partitioned tables
  psql -U postgres -d vds_platform <<SQL
DO \$mig\$
DECLARE r RECORD;
BEGIN
  FOR r IN SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND c.relkind='r'
  LOOP EXECUTE format('ALTER TABLE public.%I SET SCHEMA $TARGET_SCHEMA', r.relname); END LOOP;

  FOR r IN SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND c.relkind='m'
  LOOP EXECUTE format('ALTER MATERIALIZED VIEW public.%I SET SCHEMA $TARGET_SCHEMA', r.relname); END LOOP;

  FOR r IN SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND c.relkind='v'
  LOOP EXECUTE format('ALTER VIEW public.%I SET SCHEMA $TARGET_SCHEMA', r.relname); END LOOP;

  -- Partitioned tables (relkind='p') — same syntax as TABLE
  FOR r IN SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND c.relkind='p'
  LOOP EXECUTE format('ALTER TABLE public.%I SET SCHEMA $TARGET_SCHEMA', r.relname); END LOOP;

  -- Standalone sequences (not owned by a table)
  FOR r IN SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           LEFT JOIN pg_depend d ON d.objid=c.oid AND d.deptype='a'
           WHERE n.nspname='public' AND c.relkind='S' AND d.objid IS NULL
  LOOP EXECUTE format('ALTER SEQUENCE public.%I SET SCHEMA $TARGET_SCHEMA', r.relname); END LOOP;
END
\$mig\$;
SQL
  echo "  Moved $(psql -U postgres -d vds_platform -tAc "SELECT count(*) FROM pg_tables WHERE schemaname='$TARGET_SCHEMA'") tables to $TARGET_SCHEMA"
done
BASH
```

#### 7.3 — Why this approach over sed-rewrite

| Concern | sed-rewrite | pg_restore + SET SCHEMA |
|---|---|---|
| Comments containing `public.` | ❌ corrupted | ✅ untouched |
| PG18 `\restrict` mode | ❌ blocks COPY data | ✅ pg_restore handles binary natively |
| Owned sequences | ⚠️ may break | ✅ auto-follow their table |
| Partitioned tables | ⚠️ requires partition handling | ✅ ALTER TABLE handles natively |
| Function bodies | ❌ may corrupt `$$ ... public. ... $$` | ✅ untouched |
| Speed (large dumps) | One pipe pass | Two phases (restore + ALTER) |

The trade-off: pg_restore + SET SCHEMA requires an empty `public` schema between
each dump (so cross-dump table-name collisions are isolated to one operation).
The script above implicitly enforces this by moving everything out of `public`
before the next pg_restore.

#### 7.4 — Caveats observed during rollout

- **Owned sequences** (`SERIAL` / `IDENTITY`) cannot be moved independently:
  the loop must move TABLEs first, sequences auto-follow.
- **Partitioned tables** have `relkind='p'`, not `'r'` — handle separately.
- **Materialized views** must move after their underlying tables.
- **Cross-dump table-name collisions**: dumps from different legacy DBs may
  contain `alembic_version` or other shared names. The script above handles
  collisions per-dump (each `pg_restore` runs against an empty `public`).

#### 7.4 — Post-restore verification

```bash
# Row counts per migrated schema
docker exec vds-postgres psql -U postgres -d vds_platform -c \
  "SELECT schemaname, relname, n_live_tup AS rows
   FROM pg_stat_user_tables
   WHERE schemaname IN ('audit_state','memory','sched','progress')
   ORDER BY schemaname, relname;"

# Cross-check vs. legacy (start legacy postgres temporarily if needed):
# docker start vds-ai-memory-postgres-1
# docker exec vds-ai-memory-postgres-1 psql -U vds_user -d vds_memory -c \
#   "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname"
# docker stop vds-ai-memory-postgres-1
```

#### 7.5 — When NOT to migrate via dump+restore

For services that store ephemeral state only (Celery brokers, session caches),
data migration is unnecessary — restart the service against the new infra and
let it rebuild state. Examples:

- `memory_orchestrator` Celery broker — Redis DB 0, no persistent state
- `pdf_orchestrator` session cache — Redis DB 7, regenerated per request
- Memory cache (Redis DBs 1-5) — pure caches, regenerable

For mem0 vector data, the legacy `vds-ai-memory-qdrant-1` volume is preserved on
disk; copy it into the new `vds_qdrant_data` volume rather than dump-and-restore.

#### 7.6 — Rollback procedure

If migration fails or causes regressions:

```bash
# 1. Stop new shared infra
make down

# 2. Restart legacy stacks (volumes preserved their data)
docker start vds-ai-memory-postgres-1 vds-ai-memory-redis-1 vds-ai-memory-qdrant-1 \
             vds-ai-memory-api-1 vds-ai-memory-worker-1
docker start vds-audit-postgres
```

Full rollback documentation: `docker/ROLLBACK.md`.

## Per-Orchestrator Migration Notes

### Audit Orchestrator

1. The `audit-postgres` service is removed
2. Update `VDS_AUDIT_STATE_DSN` and `VDS_AUDIT_LANGGRAPH__POSTGRES_DSN`
3. Ensure `audit_state` schema exists (created by `init-schemas.sql`)

### Memory Orchestrator

1. Remove standalone `postgres` and `redis` services
2. Update `DATABASE_URL` to include `search_path=memory`
3. Redis connections now use `vds-redis:6379`

### PDF Orchestrator

1. Remove standalone `redis` service
2. PDF uses Redis DB 7: `redis://vds-redis:6379/7`
3. No PostgreSQL dependency

### Scheduler Orchestrator

1. Uses `sched` schema
2. Redis DB 8 for scheduler state

## Post-P5 Deploy Gotchas (P6 WP-6.5)

Three real deploy-time bugs were discovered during P5 live validation that should be understood before cutover:

1. **Makefile target loadout incompleteness** — `make up-services` and `make up-scheduler` may fail if Compose files are not fully loaded. Full details and prevention tests: `scheduler_orchestrator/DEPLOYMENT-RUNBOOK.md §Common Deploy Gotchas`.

2. **Dockerfile workspace-dep wiring lag** — Services that depend on workspace packages (e.g., `vds-platform-core`) must COPY those packages into the Docker build context. Full details and prevention tests: `scheduler_orchestrator/DEPLOYMENT-RUNBOOK.md §Common Deploy Gotchas`.

3. **Cross-profile depends_on** — The scheduler service depends on memory-api, which lives in a different Compose profile. Running `make up-scheduler` requires activating both profiles. Full details: `scheduler_orchestrator/DEPLOYMENT-RUNBOOK.md §Common Deploy Gotchas`.

Prevention tests (P6 WP-6.1, WP-6.2) will be added to the CI pipeline to catch regressions.

## Troubleshooting

### Container Won't Start

Check logs:
```bash
docker logs vds-postgres
docker logs vds-redis
docker logs vds-qdrant
```

### Connection Refused

1. Verify container is running: `docker ps | grep vds-`
2. Check health status: `docker inspect --format='{{.State.Health.Status}}' vds-postgres`
3. Wait for healthy status before connecting

### Schema Not Found

```bash
docker exec vds-postgres psql -U postgres -d vds_platform -c "\dn"
```

Should show:
- audit_state
- memory
- sched
- progress
- dbos

### Redis DB Not Reachable

```bash
docker exec vds-redis redis-cli -p 6379 -n 7 ping
```

Replace `7` with your DB number.

## Rollback

To rollback to standalone infrastructure:

1. Stop all services
2. Restart standalone infrastructure
3. Update environment variables back to old values
4. Restore from backup if needed

## Post-Migration

After successful migration:

1. Update documentation
2. Update CI/CD pipelines
3. Update runbooks
4. Train team members
