# VDS Ecosystem Infrastructure

Centralized Docker Compose infrastructure for all VDS orchestrators.

## Overview

This directory contains shared infrastructure services that all VDS orchestrators use:

- **PostgreSQL + pgvector**: Shared database server with schema isolation
- **Redis**: Shared cache server with logical DB separation
- **Qdrant**: VDS-internal vector store for mem0

## Architecture

### Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     VDS Internal Network                      │
│                      (vds-internal)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  postgres   │  │   redis     │  │   qdrant    │        │
│  │  :5432      │  │   :6379     │  │  :6333-34   │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                 │                 │                │
│         │    ┌────────────┼────────────┐   │                │
│         │    │            │            │   │                │
│         ▼    ▼            ▼            ▼   ▼                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  audit   │ │  memory  │ │   pdf    │ │ scheduler│       │
│  │  state   │ │   API    │ │          │ │          │       │
│  │  schema  │ │  worker  │ │  DB 7    │ │  sched   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Port Allocation

| Port | Service | Notes |
|------|---------|-------|
| 5432 | vds-postgres | Shared PostgreSQL server |
| 6379 | vds-redis | Shared Redis server |
| 6432 | vds-pgbouncer | PgBouncer connection pooler (P8, ADR-INF-13) |
| 6333-34 | vds-grepai-qdrant | Existing grepai instance |
| 6335-36 | vds-qdrant | VDS-internal mem0 instance |

### Schema Separation (PostgreSQL)

| Schema | Owner | Purpose |
|--------|-------|---------|
| audit_state | vds_audit_app | Audit orchestrator state |
| memory | vds_memory_app | Memory orchestrator state |
| sched | vds_scheduler_app | Scheduler orchestrator state |
| progress | vds_progress_app | Progress report state |
| dbos | vds_sched_runtime | DBOS system tables |

## Schema Ownership Boundary (post P4 v2.11.1)

Schema bootstrap is split into two ownership tiers:

| Layer | Owner | When it runs | Manages |
|---|---|---|---|
| **Postgres container init** | `docker/infrastructure/init-schemas.sql` | Once, at first postgres container startup | Schemas (`audit_state`, `memory`, `sched`, `progress`, `dbos`), roles (`vds_audit_app`, `vds_memory_app`, ...), DBOS CREATE grant |
| **Per-service migration** | `<service>_orchestrator/alembic/` | Each service's `<service>-migrate` compose service (`make run-<service>-migrate` or `compose up`) | Tables, indexes, functions, views in that service's schema |

**Why two tiers**: schemas + roles are a one-time concern (postgres-cluster-level); tables evolve continuously per service. Splitting ensures `init-schemas.sql` is never a moving target and per-service Alembic envs are never blocked on cross-service coordination.

See ADR-INF-11 in `docker/ADR.md` for full rationale.

### Redis Logical DB Separation

| DB | Consumer | Purpose |
|----|----------|---------|
| 0 | Celery | Message broker |
| 1 | memory | Cache, sweeper |
| 2 | memory | Session store, ai_memory_service |
| 3 | memory | Analytics, tracker, search |
| 4 | memory | Search cache |
| 5 | memory | Rate limiting |
| 6 | multi-agent | Agent state, progress dashboard |
| 7 | pdf | Session cache |
| 8 | scheduler | Scheduler state |
| 9 | memory | Tool discovery (`REDIS_TOOL_DISCOVERY_DB`; was DB 6, moved 2026-04-25 to free DB 6 for multi-agent — see ADR-INF-9) |

## Quick Start

### Project Identity

Both compose files declare `name: vds-platform`, so they form a single
Compose project regardless of which directory `docker compose` is invoked
from. The Makefile also passes `-p vds-platform` for defense in depth. See
the project memory rule `reference_compose_project_identity_anchor.md`.

### Three-Tier File Structure (v2.10.0)

```
docker/docker-compose.infra.yml      Tier 1: postgres + redis + qdrant
docker/docker-compose.services.yml   Tier 2: 4 long-running services
docker/docker-compose.cli.yml        Tier 3: 6 CLI containers
```

Per **ADR-INF-10**, services and CLI containers split into two operational
patterns. `up -d` for Tier 2 (daemons stay running). `run --rm` for Tier 3
(one-shot per invocation; not visible in `docker ps -a` until invoked).

### Preferred entry: Makefile

```bash
make help              # list all targets

# Tier 2 — long-running services (`up -d`)
make up-infra          # postgres + redis + qdrant
make up-memory         # + memory-api + memory-worker
make up-scheduler      # + scheduler (needs VDS_SCHEDULER_ENABLED=true)
make up-multi-agent    # + multi-agent
make up-services       # all 4 long-running

# Tier 3 — CLI containers (`run --rm`; override ARGS per invocation)
make run-audit ARGS="workflow run --project X"
make run-pdf ARGS="merge a.pdf b.pdf -o c.pdf"
make run-progress ARGS="generate --project X"
make run-db-query ARGS="query --connection prod -q 'SELECT 1'"
make run-vds-cli ARGS="<service> <command>"

# Build / lifecycle
make build-cli         # pre-build all 6 CLI images
make verify            # 26/26 topology check
make status            # show running containers
make down              # stop everything
```

### Direct compose (advanced — skip the Makefile)

Always pass `-p vds-platform` and load all relevant tier files:

```bash
# Tier 2 — long-running
docker compose -p vds-platform \
               -f docker/docker-compose.infra.yml \
               -f docker/docker-compose.services.yml \
               --profile memory up -d

# Tier 3 — CLI invocation
docker compose -p vds-platform \
               -f docker/docker-compose.infra.yml \
               -f docker/docker-compose.cli.yml \
               --profile audit run --rm audit-orchestrator workflow run --project X
```

## Legacy Per-Orchestrator Compose Files (REMOVED v2.15.12)

Pre-v2.0.0, each orchestrator had its own `docker-compose.yml` for standalone
development. They were retired to `docker/legacy/` in P3 + P4 WP-4.0 as a
one-release-cycle rollback path; that directory was REMOVED in v2.15.12 per
the no-legacy / no-fallback directive (P0–P8 stable for >1 month; rollback
risk no longer warrants standing files in the repo). If a pre-P0 rollback
is ever needed, recover the legacy compose files from git history — see
`docker/ROLLBACK.md` §Scenario 1 step 2 for the canonical `git show` recipe.

## Dockerfile ENTRYPOINT Pattern (intentional asymmetry per image purpose)

Two Dockerfile patterns coexist by design — they track image purpose:

**CLI-tool images** (audit-orchestrator, progress-report-orchestrator, db-query-orchestrator, mcp-server, vds-cli):
```dockerfile
ENTRYPOINT ["/opt/venv/bin/vds-<svc>"]
CMD ["--help"]
```
This makes `docker run vds-<svc>:tag <subcommand>` invoke `vds-<svc> <subcommand>` directly — the natural CLI-tool contract. Default `--help` so a no-arg run prints usage. Operator-CLI containers (Tier 3) follow this pattern.

**HTTP-service images** (memory-api, memory-worker, multi-agent-orchestrator):
```dockerfile
CMD ["/opt/venv/bin/python", "-m", "uvicorn", ...]
```
No ENTRYPOINT — the service-startup command is set via CMD only. This lets `docker compose run --rm <service> <other-command>` work without `--entrypoint` override (e.g., for one-shot maintenance like alembic migrations).

**Mixed: scheduler-orchestrator** uses a startup shell-script entrypoint that handles its DBOS-specific bootstrap (env validation + alembic-on-startup + uvicorn). Different from both other patterns because DBOS adds an init phase no other service needs.

**Operator implication**: post-v2.15.10, `docker compose run --rm <service>` for migrations needs `--entrypoint /opt/venv/bin/alembic` ONLY for CLI-tool images (audit/progress); HTTP-service images accept alembic as direct command. See `references/alembic-migrations.md` in `infrastructure-evolution-skill` for the per-service canonical recipes.

This asymmetry was reviewed in v2.15.14 standardization audit and classified LEAVE-WITH-RATIONALE: collapsing CLI tools to no-ENTRYPOINT would lose the natural `docker run vds-<svc> <cmd>` UX; collapsing HTTP services to ENTRYPOINT-bound would force every operator-invoked one-shot to carry `--entrypoint` overrides. The current pattern is the local optimum.

## Healthcheck Location Pattern (intentional asymmetry per image ownership)

Healthcheck definitions split across 3 surfaces by image ownership — NOT inconsistency:

**Tier 1 upstream images** (postgres, redis, qdrant, pgbouncer): healthcheck is **defined in `docker-compose.infra.yml`** because we cannot modify upstream Dockerfiles. The compose `healthcheck:` block is the only knob available. Cadence: `interval=10s, timeout=5s, retries=5`.

**Tier 2 VDS-owned service images** (memory-api, memory-worker, multi-agent-orchestrator): healthcheck is **defined in each service's Dockerfile** via `HEALTHCHECK CMD` directive. Rationale: the check rides with the image — any compose-file refactor leaves the check intact, and `docker run vds-memory:1.0.0` (without compose) still gets a valid healthcheck. Cadence varies per service-startup characteristics (memory-api: `interval=30s, timeout=10s, start_period=10s`; multi-agent: same with `start_period=15s`).

**scheduler-orchestrator**: healthcheck in **compose** (because its DBOS bootstrap requires `start_period=60s` — longer than the Dockerfile-default; compose lets us override per-deploy without rebuilding the image).

**Tier 3 CLI containers**: NO healthcheck. They `restart: "no"` + `exit 0` after their subcommand completes. A long-lived healthcheck on a one-shot container would never converge. (vds-cli is a partial exception: its Dockerfile defines a HEALTHCHECK for `docker ps` status display only, but `restart: "no"` means it never triggers restart logic.)

**Verification**: `docker inspect vds-memory-api --format '{{json .Config.Healthcheck}}'` confirms Tier 2 services have Dockerfile-defined checks active at runtime; `docker compose ... config | grep healthcheck` confirms Tier 1 + scheduler have compose-defined checks.

This pattern was reviewed in v2.15.15 infrastructure-layer audit and classified LEAVE-WITH-RATIONALE: each location tracks the image-ownership boundary, which is what determines whether the check should ride-with-the-image (VDS-owned) or be deploy-time-overridable (upstream + DBOS bootstrap).

## Resource Limits (DEFERRED to performance-tuning pass — v2.15.15 I1)

VDS service containers currently lack explicit `mem_limit` / `cpus` constraints. Default Docker behavior: containers can consume all host resources, with no enforcement.

**Why DEFERRED rather than STANDARDIZED in v2.15.15**: setting `mem_limit` requires knowing each service's working-set ceiling. Memory-api specifically includes mem0 + sentence-transformers + entity-linking (heavy ML stack) — capping below the actual working set causes OOMKill cycles, which is operationally worse than no cap. Capping above the actual working set defeats the purpose.

**Right path**: gather working-set data via `docker stats` over a representative workload (1 week minimum), then set `mem_limit` to observed-peak × 1.3 (30% headroom). v2.15.15 audit flagged this as STANDARDIZE candidate but **the implementer chose to defer** rather than guess at limits.

**Tracked**: revisit when working-set data is available; expected to land in a v2.16.x performance-tuning pass.

## Named Volumes (post v2.15.19)

| Volume | Mount point | Purpose | Owner |
|---|---|---|---|
| `vds_postgres_data` | postgres:/var/lib/postgresql/data | Postgres data dir | shared |
| `vds_redis_data` | redis:/data | Redis AOF + RDB | shared |
| `vds_qdrant_data` | qdrant:/qdrant/storage | Qdrant vector storage | shared |
| `vds_scheduler_reports` | scheduler-orchestrator:/opt/reports | Daily ecosystem-report markdown output (v2.15.19) | scheduler |

The `vds_scheduler_reports` named volume was added in v2.15.19 to fix an H4 carry-forward bug where the scheduler-orchestrator container could not `mkdir(/opt/reports/ecosystem)` because `/opt` was root-owned read-only for the scheduler user (uid=999). The Dockerfile now `mkdir -p /opt/reports && chown scheduler:scheduler /opt/reports` so future fresh volumes initialize with correct ownership.

## MCP Server Entry (post v2.15.19)

`mcp_server` is wrapped in Typer for help-output consistency with the other 42+ routers. Two invocation forms work:

| Form | Behavior |
|---|---|
| `vds-mcp-server` | Default: starts FastMCP over stdio (callback handler — no sub-command needed) |
| `vds-mcp-server serve` | Explicit: starts FastMCP over stdio (Typer sub-command) |
| `vds-mcp-server --help` | Rich-styled help with `serve` sub-command listed |

The Typer wrap was added in v2.15.19 (M9) to close the help-output drift identified during the live-CLI feature-acceptance audit; bare `vds-mcp-server` behavior is preserved (no operator-script breakage).

## Operator Hygiene (post v2.15.22)

### `~/.vds/.env` file permissions — REQUIRED

The operator env file contains LLM API keys, Confluence/Bitbucket credentials, PgBouncer admin passwords, and JWT secrets. It MUST be owner-only readable:

```bash
chmod 600 ~/.vds/.env
ls -l ~/.vds/.env  # should show: -rw-------
```

If `ls -l` shows `-rw-r--r--` (644), other users on the same machine can read your secrets. Fix immediately.

### Backup rotation policy

`~/.vds/.env` updates that operators perform during version bumps may produce backup files (`.env.bak.<timestamp>`, `.env.backup-<timestamp>`). These accumulate quickly:

- **Recommended**: keep at most 3 most-recent backups inline; tarball older ones quarterly
- **One-shot prune**: `tar czf ~/.vds/.env-backups-$(date +%Y%m%d).tar.gz ~/.vds/.env.bak.* && rm ~/.vds/.env.bak.*`
- v2.15.14 produced one such tarball (`~/.vds/.env-backups-pruned-20260428.tar.gz`); use it as the rotation reference.

### Logs retention policy

`~/.vds/logs/` accumulates daily JSONL audit-runtime logs (~50-100 MB/day for active workloads). Without rotation:

- 1 month → ~3 GB
- 6 months → ~18 GB (will exceed iCloud quota)

Recommended approaches:
- Add `logrotate` config: rotate weekly, compress, retain 4 weeks
- Or `find ~/.vds/logs -name '*.jsonl' -mtime +30 -delete` cron monthly
- Or rsync to external NAS/object storage

### Cache disk usage

`~/.vds/cache/` (DSPy/LLM artifact cache) can grow into hundreds of GB on heavy LLM users. Periodically check with `du -sh ~/.vds/cache/`. Cleanup is operator-decision; the cache is rebuildable.

## Environment Variables

### Environment File Loading Order

Docker Compose loads environment variables in the following priority order:

1. **~/.vds/.env** (highest priority for user credentials)
   - User-level credentials and global configuration
   - Automatically loaded via `env_file: ${HOME}/.vds/.env`
   - Contains: `VDS_POSTGRES_PASSWORD`, `VDS_USERNAME`, `BITBUCKET_ACCESS_TOKEN`, etc.

2. **docker/infrastructure/.env**
   - Infrastructure-specific configuration
   - Copy from template: `cp docker/infrastructure/.env.template docker/infrastructure/.env`

3. **Shell environment variables**
   - Set via `${VAR:-default}` syntax in compose files
   - Can be overridden: `VDS_POSTGRES_PASSWORD=secret docker compose ...`

4. **docker compose -e overrides** (highest priority)
   - Inline overrides: `docker compose -e VAR=value up -d`

### Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| VDS_POSTGRES_PASSWORD | vds_postgres_secret | PostgreSQL postgres user password |
| PGBOUNCER_ADMIN_PASSWORD | (required) | PgBouncer admin user password (P8) |
| PGBOUNCER_STATS_PASSWORD | (required) | PgBouncer stats user password (P8) |
| PGBOUNCER_AUTH_PASSWORD | (required) | PgBouncer auth user password (P8) |
| REDIS_CELERY_BROKER_DB | 0 | Redis DB for Celery broker |
| REDIS_MEMORY_CACHE_DB | 1 | Redis DB for memory cache |
| REDIS_SESSION_STORE_DB | 2 | Redis DB for session store |
| REDIS_ANALYTICS_DB | 3 | Redis DB for analytics |
| REDIS_SEARCH_CACHE_DB | 4 | Redis DB for search cache |
| REDIS_RATE_LIMITING_DB | 5 | Redis DB for rate limiting |
| REDIS_TOOL_DISCOVERY_DB | 9 | Redis DB for memory tool discovery (DB 6 reserved for multi-agent state) |
| QDRANT_HOST | localhost | Qdrant host |
| QDRANT_PORT | 6335 | Qdrant HTTP port |

### Setup

Copy `docker/infrastructure/.env.template` to `docker/infrastructure/.env` and customize:

```bash
cp docker/infrastructure/.env.template docker/infrastructure/.env
```

Or ensure `~/.vds/.env` contains the required P0 infrastructure variables:

## Verification

Run the topology verification script:

```bash
python scripts/verify-infra-topology.py --profile infra
```

Expected output:
```
✓ docker_available: Docker is available
✓ container_running:vds-postgres: Container vds-postgres is running
✓ container_running:vds-redis: Container vds-redis is running
✓ container_running:vds-qdrant: Container vds-qdrant is running
✓ schema_exists:audit_state: Schema audit_state exists
✓ schema_exists:memory: Schema memory exists
...
```

## Migration Guide

See [MIGRATION.md](MIGRATION.md) for detailed migration instructions from standalone to shared infrastructure.

## Architecture Decision Records

See [ADR.md](ADR.md) for the full list of ADRs governing this infrastructure.
