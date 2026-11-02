<!-- diátaxis: reference -->
# VDS Infrastructure v2.15.x — Operator Reference

> Consolidated delta from v2.14 → v2.15.x (PgBouncer dual-DSN, healthchecks, container cycling, init-schemas).

## Overview

Phase *v2.15.x* introduces PgBouncer fronting for all PostgreSQL access, per-stanza `search_path` pinning, and container-health probe standardization. Prior v2.14.x connected apps directly to `vds-postgres:5432` and relied on per-app URL `?options=search_path` fragments.

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **PgBouncer** | `docker/infrastructure/pgbouncer/` | 1:1 session-mode pool per schema (`vds_audit`, `vds_memory`, `vds_progress`, `vds_sched`) |
| **PostgreSQL** | `docker/infrastructure/init-schemas.sql` | Shared `vds_platform` database with schema-per-module (search_path + `connect_query`) |
| **Healthcheck scripts** | `docker/backends/*/healthcheck.sh` | Standardized `HEALTHCHECK` pattern for orchestrator containers |
| **Container cycling** | Orchestrator Dockerfiles | Boot-time idempotency: schema init only if `IF NOT EXISTS`; migration drift detection |

## PgBouncer Stanzas

```ini
[databases]
vds_audit    = host=vds-postgres port=5432 dbname=vds_platform connect_query='SET search_path TO audit_state, public' pool_size=40
vds_memory   = host=vds-postgres port=5432 dbname=vds_platform connect_query='SET search_path TO memory, public' pool_size=40
vds_progress = host=vds-postgres port=5432 dbname=vds_platform connect_query='SET search_path TO progress, public' pool_size=40
vds_sched    = host=vds-postgres port=5432 dbname=vds_platform connect_query='SET search_path TO sched, public' pool_size=40
```

> **Note**: `options=` is **not** a valid per-stanza key in PgBouncer ≥1.24. Use `connect_query` for `search_path` pinning.

## Healthcheck Pattern

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/app/healthcheck.sh"]
```

Each `healthcheck.sh` must:
1. Validate DSN connectivity (PgBouncer or direct)
2. Check schema ownership (`SELECT current_schema()`)
3. Exit `0` = healthy, non-zero = unhealthy → Docker restarts container

## Migration Guide (v2.14 → v2.15)

1. **Update DSNs**: Replace direct postgres ports with PgBouncer stanzas
2. **Remove `search_path` from URLs**: PgBouncer `connect_query` handles this
3. **Restart containers**: PgBouncer must be up before apps connect
4. **Validate `pool_size`**: Monitor `cl_waiting` via `SHOW POOLS`

## Operational Notes

- **Session mode** (1:1 client:backend) is mandatory for `scheduler_orchestrator` (DBOS LISTEN/NOTIFY) and `audit_orchestrator` (advisory locks).
- **Transaction mode** override may be trialed for `memory_orchestrator` stanzas if `cl_waiting > 0` for 90 days.
- **Container cycling**: Boot is idempotent (`IF NOT EXISTS`). Migrations run via Alembic after healthcheck passes.

## Caveats

- PgBouncer `connect_query` runs **once per backend** at startup, not per client session.
- Changing `search_path` mid-session requires a reconnect (or explicit `SET search_path`).
- `userlist.txt` (pgbouncer auth) is generated from `.env.template`; do not commit real credentials.

## See Also

- [ecosystem-daily-report](ecosystem-daily-report.md) — Health metrics and daily snapshot
- [env-git-helper](env-git-helper.md) — Credential helper for container lifecycle
- `docker/infrastructure/pgbouncer/pgbouncer.ini` — Live config
- `docker/infrastructure/init-schemas.sql` — Schema bootstrap
