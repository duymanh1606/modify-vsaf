# VDS Infrastructure ADRs — Operator Routing Manifest

> **Spec authoritative**. The canonical decision text for each ADR-INF-N lives at:
> `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §7 ADRs.
>
> This file is a tiered routing manifest:
> - **INF-1..7**: 3-6 line operator-facing pointer + spec link (no restated content).
> - **INF-8..12**: pointer + extended operator content (postmortems, regression tests,
>   downgrade pattern, REDIS DB supersession, Tier 3 sub-shape table) that is
>   directly load-bearing during incident response. The size budget reflects this
>   intentional inline-when-load-bearing policy rather than full mirroring.
>
> Last sync: master@5f0c97b4 (post-v2.15.17, 2026-04-28).

## ADR-INF-1 — Schema-per-Domain over Database-per-Service

**Status**: Accepted (P0) | **Spec**: `design.md` §ADR-INF-1

Single shared Postgres instance with per-service schema isolation (`audit_state`, `memory`, `sched`, `progress`, `dbos`). Each service gets a dedicated schema + role. Simpler to operate than 5 separate database instances.

→ Full rationale, consequences, rejected alternatives: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-1

## ADR-INF-2 — Redis Logical DB over Multiple Redis Instances

**Status**: Accepted (P0) | **Spec**: `design.md` §ADR-INF-2

Single Redis instance with logical DB separation (DBs 0–9). Each consumer gets a dedicated DB number. Redis natively supports 16 logical databases; one instance is simpler to operate.

→ Full rationale, consequences, rejected alternatives: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-2

## ADR-INF-3 — Profile-Based Compose over Directory-Per-Service

**Status**: Accepted (P0) | **Spec**: `design.md` §ADR-INF-3

Docker Compose profiles (`--profile <name>`) for selective service activation instead of per-service compose directories. Standard Docker Compose mechanism; operators learn profile names instead of navigating directory trees.

→ Full rationale, consequences, rejected alternatives: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-3

## ADR-INF-4 — Host-Only Policy for vds-skills and git

**Status**: Accepted (P0) | **Spec**: `design.md` §ADR-INF-4

Skills sync, memory operations, and git operations run on host only — never in containers. These interact with iCloud-synced paths, SSH keys, and git state that don't map cleanly into container filesystems.

→ Full rationale, consequences, rejected alternatives: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-4

## ADR-INF-5 — Qdrant Instance Separation

**Status**: Accepted (P0) | **Spec**: `design.md` §ADR-INF-5

Separate Qdrant instances for grepai (ports 6333/6334) and VDS memory (ports 6335/6336). Different version requirements and collection schemas; port offset avoids collision.

→ Full rationale, consequences, rejected alternatives: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-5

## ADR-INF-6 — Celery Broker DB Explicit Assignment

**Status**: Accepted (P0) | **Spec**: `design.md` §ADR-INF-6

Celery broker explicitly assigned to Redis DB 0 via `CELERY_BROKER_URL` with `/0` suffix. Prevents accidental DB collision when multiple Redis consumers are added.

→ Full rationale, consequences, rejected alternatives: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-6

## ADR-INF-7 — Compose Project Identity Anchor

**Status**: Accepted (P2) | **Spec**: `design.md` §ADR-INF-7

All three compose files declare `name: vds-platform`. CLI invocations use `-p vds-platform` for defense in depth. Ensures containers, networks, and volumes belong to one Compose project regardless of which `-f` flags are passed or which directory the command runs from.

→ Full rationale, consequences, rejected alternatives: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-7

## ADR-INF-8 — `python3` for stdlib-only verification (not `vds-cli`/`uv`)

**Status**: Accepted (v2.8.0 — operator-facing verification path stabilized)

**Date**: 2026-04-25 | **Spec**: `design.md` §ADR-INF-8

### Decision

`scripts/verify-infra-topology.py` is invoked as bare `python3 scripts/verify-infra-topology.py` from the Makefile, the `infrastructure-evolution-skill/scripts/verify.sh` wrapper, and the operator docs. It is NOT routed through `vds-cli` and is NOT wrapped in `uv run --project vds_cli`.

### Rationale

- The script imports only Python stdlib (`argparse`, `json`, `subprocess`, `sys`, `dataclasses`, `typing`) — zero third-party deps.
- `uv run` adds 60-650ms cold-start overhead per invocation; `uv run --project` additionally couples the script to a workspace lockfile that can drift, breaking the verify path during incident response (the exact moment we need it most).
- `vds-cli` is reserved for orchestrator commands that need project deps; pulling stdlib utilities into the router dilutes that boundary.
- Using `python3` (not bare `python`) avoids the macOS / minimal-Linux ambiguity where `python` may point at python2 or be absent.
- Aligns with VDS rule `feedback_hooks_no_uv_for_stdlib.md` (stdlib hooks use `python3`, not `uv run`).

### Consequences

- The script is callable from any environment with a Python 3.10+ interpreter — including broken venvs and bare hosts during cutover or post-incident recovery.
- Trade-off: loss of `vds-cli --help` central discovery for the verify command; compensated by `make verify` (Makefile target) and the skill wrapper `infrastructure-evolution-skill/scripts/verify.sh`.
- New stdlib-only verification scripts in this repo SHOULD follow the same `python3 scripts/<name>.py` invocation pattern.

## ADR-INF-9 — Resolve Redis DB 6 double-booking: tool discovery moves to DB 9

**Status**: Accepted (v2.4.0 — supersedes the DB 6 assignment in ADR-INF-6)

**Date**: 2026-04-25 | **Spec**: `design.md` §ADR-INF-9

### Decision

`memory_orchestrator`'s `REDIS_TOOL_DISCOVERY_DB` defaults to **9** (not 6). DB 6 is reserved exclusively for `multi_agent_orchestrator` agent state. The "9+ reserved for future services" range is now formally allocated starting at 9.

### Rationale

- ADR-INF-6 reassigned `redis_tool_discovery_db` from DB 0 (Celery collision) to DB 6 to satisfy `requirements.md`'s "must be reassigned to DB 5 or higher".
- That wording was satisfied but landed on the DB this design assigned to multi-agent agent state, recreating exactly the silent-collision risk ADR-INF-6 was meant to eliminate.
- Without explicit key-prefix isolation guarantees, dual-tenancy in DB 6 is unsafe for two unrelated services.
- DB 9 is the next free slot per the FR-3 allocation table; tool discovery is "not yet wired" in production, so no data migration is required.

### Consequences

- One-line compose env change: `REDIS_TOOL_DISCOVERY_DB: ${REDIS_TOOL_DISCOVERY_DB:-9}`.
- One-line `memory_orchestrator/src/.../config.py` field default change.
- FR-3 design table extended to formally include DB 9.
- ADR-INF-6 remains historically accurate (it documents the DB 0 → DB 6 move); this ADR supersedes only the destination.

## ADR-INF-10 — Service vs CLI Container Patterns

**Status**: Accepted (v2.8.0 — Tier-2 split codified during three-tier compose rollout)

**Date**: 2026-04-25 | **Spec**: `design.md` §ADR-INF-10

### Decision

Tier-2 compose entries split into two patterns based on whether the orchestrator's runtime is a daemon or a one-shot command:

| Pattern | Examples | `restart` | HEALTHCHECK | Operational invocation |
|---|---|---|---|---|
| **Long-running service** | memory-api, memory-worker, scheduler, multi-agent | `unless-stopped` | HTTP/port probe | `up -d` → `docker ps` shows `Up X minutes (healthy)` |
| **On-demand CLI** | audit, pdf, progress, db-query | `"no"` | none | `docker compose -p vds-platform run --rm <service> <subcommand>` |

### Rationale

- Earlier rollout iterations applied `restart: unless-stopped` uniformly to all Tier-2 entries; this caused audit/pdf/progress/db-query to perpetually restart-loop after each clean exit (CLI runs `--help`, exits 0, daemon restarts it, repeat).
- The fix is NOT to grow a `serve` mode for each CLI — that is feature work, not infra plumbing.
- Instead, acknowledge that the FR-4 services divide into two patterns and configure each correctly at the compose layer.

### Consequences

- A healthy `vds-platform` project's `docker ps` shows 4 long-running services + 4 exited CLI containers. The `Exited (0)` state is **normal**, not a failure signal.
- Operators MUST invoke CLI containers via `docker compose -p vds-platform run --rm <service> <subcommand>` rather than `up -d`. Documented in `MIGRATION.md` and `infrastructure-evolution-skill`.
- If audit or pdf grow a daemon mode in the future (e.g., a job-queue dispatcher), reclassifying them is a one-line compose change (`restart: "no"` → `restart: unless-stopped`) plus a CMD update.
- `verify-infra-topology.py` profile checks treat CLI profiles (progress, db-query, audit-when-CLI, pdf-when-CLI) as "infra-only expected running" — only the shared infra needs to be up; the CLI profile's container exiting is expected.

#### Tier 3 Sub-Shapes (simplified v2.15.10)

Only **3A — Operator-CLI** remains active. Operators invoke CLI containers via
`docker compose run --rm <service> <subcommand>` (or `make run-<service> ARGS=...`).

| Sub-shape | Invoked by | Examples | Where |
|---|---|---|---|
| **3A — Operator-CLI** | Human operator | `audit`, `pdf`, `progress`, `db-query`, `vds-cli`, `mcp-server` | `docker-compose.cli.yml` |
| **3B — Auto-init one-shot** | *(retired v2.15.10)* | — | — |

Pre-v2.15.10, `memory-migrate` was a Tier 3B auto-init container that ran
`alembic upgrade head` before the main service started. The entire sub-shape
was retired when ADR-INF-10 adopted the single-tier deploy model: each
long-running service's entrypoint runs alembic before exec'ing uvicorn,
eliminating cross-file `depends_on` and the two-tier privilege model.

`make up-<service>` loads only `docker-compose.services.yml`. The CLI file
(`docker-compose.cli.yml`) is loaded only for explicit operator-CLI invocations
(`make run-audit`, etc.).


## ADR-INF-11 — Alembic Migration Standard

**Status**: Accepted (P4 v2.11.1; simplified P5 WP-5.1 at `c1a3585d`)

**Date**: 2026-04-25 (P4); 2026-04-26 (P5 WP-5.1 simplification) | **Spec**: `design.md` §ADR-INF-11

### Decision

All DB-backed VDS orchestrators MUST use Alembic for schema migrations. Each
service owns its own `alembic.ini` + `alembic/env.py` + `alembic/versions/`
tree. There is **no** monorepo-wide single Alembic environment. Schema/role
bootstrap (one-time at postgres container init) lives in
`docker/infrastructure/init-schemas.sql`; per-service table CREATE/ALTER
ownership belongs to that service's Alembic env.

Services in scope (post P5 WP-5.1):

| Service | Alembic env | Version table |
|---|---|---|
| memory_orchestrator | `memory_orchestrator/alembic/` | `memory.alembic_version` |
| audit_orchestrator | `audit_orchestrator/alembic/` | `audit_state.alembic_version` |
| progress_report_orchestrator | `progress_report_orchestrator/alembic/` | `progress.alembic_version` |
| scheduler_orchestrator | `scheduler_orchestrator/alembic/` | `sched.alembic_version` |

**Rule for new services**: always use `version_table_schema="<service-schema>"` in env.py
(in-schema is the single policy; the former scheduler-in-public exception was a doc
artifact — `c1a3585d` removed it).

### Rationale

1. **Industry-standard for FastAPI + SQLAlchemy 2.0 + Postgres (2026)** — same operational vocabulary as the broader Python ecosystem.
2. **Already proven on master** — memory phase197 (`f4c91c8d`) and scheduler (pre-spec); P4 extends to audit + progress.
3. **Autogenerate prevents missing-table bugs** — phase196 found 4 ORM tables with no matching migration, causing prod 500s; `alembic revision --autogenerate` would have caught these at PR time.
4. **`op.execute()` retains raw-SQL flexibility** for pgvector HNSW, GIN expression indexes, views, complex CHECK constraints.
5. **Per-service ownership** matches ADR-INF-1 (schema-per-domain); each env owns ONLY its own schema.
6. **No JVM/Go runtime added** (vs Flyway, Atlas, golang-migrate) — Alembic is Python-native, ships in `pip`.

### Canonical env.py pattern (6 design choices)

```python
# (1) include_name imported from a sibling module — NOT inline in env.py
from vds_<service>_orchestrator.db.alembic_filters import include_name
from vds_<service>_orchestrator.service.models.database import Base

target_metadata = Base.metadata  # (3) for autogenerate

context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_name=include_name,                  # (1) schema filter
    include_schemas=True,                       # (2) cross-schema awareness
    version_table_schema="<service-schema>",    # (4) in-schema policy (ADR-INF-11)
    # (5) DSN from DATABASE_URL env var (set by <svc>-migrate compose service);
    #     strip `?options=...` before passing to asyncpg engine.
    # (6) search_path via DSN options + DB-level ALTER — NEVER inline SET.
)
```

### `version_table_schema` Policy (simplified at P5 WP-5.1 / `c1a3585d`)

All services use in-schema placement: `memory.alembic_version`, `audit_state.alembic_version`,
`progress.alembic_version`, `sched.alembic_version`. The earlier "scheduler in-public exception"
was a doc artifact — scheduler's DSN `search_path=sched,public` causes Alembic's unqualified
`CREATE TABLE alembic_version` to land in `sched` regardless; the prior ADR-INF-11 §Dual Policy
table was stale. Live-state verification at `c1a3585d` confirmed all 4 services are in-schema.

**Rule for new services**: always use `version_table_schema="<service-schema>"` in env.py.

### SA2.0 Implicit-TX Gotcha (postmortem from `566217e5`, 2026-04-25)

**Symptom**: `alembic_version` table never persisted; `alembic current` returned empty; every migrate run re-applied all migrations (idempotent so harmless, but operationally confusing).

**Root cause**: `run_migrations_online()` contained `connection.execute(text("SET search_path TO memory, public"))` BEFORE `context.configure()`. Under SQLAlchemy 2.0+, this opens an *implicit transaction* that doesn't auto-commit before Alembic begins its own version-table tx, wrapping the version-table CREATE/INSERT in a phantom rollback path.

**Fix**: removed the explicit `SET search_path` connection statement. The DSN already carries `?options=-c search_path=<schema>,public` and `ALTER DATABASE vds_platform SET search_path TO <schema>, public` is set as DB default — both work without opening an in-tx SET.

**Rule**: NEVER call `connection.execute(text("SET ..."))` inside `run_migrations_online()` before `context.configure()`. Use DSN options + DB-level ALTER for search_path setup.

### Search-Path Policy (WP-4.3)

Every DSN for pgvector-using services MUST include `public` in search_path so the `vector_l2_ops` HNSW operator class is visible. Without it, migration 0003 (memory) failed with `operator class "vector_l2_ops" does not exist for access method "hnsw"`.

Pattern (URL-encoded): `?options=-c%20search_path%3D<schema>%2Cpublic`. Optionally also: `ALTER DATABASE vds_platform SET search_path TO <schema>, public` for the DB-level default.

### `init-schemas.sql` Ownership Boundary (WP-4.4)

`docker/infrastructure/init-schemas.sql` runs ONCE at postgres container init. It owns **schemas + roles + DBOS CREATE grant ONLY** — never tables. Tables are owned by per-service Alembic envs. This separation guarantees a clean rollback path: dropping a schema doesn't strand orphan migration state in another service's `alembic_version` table.

### `include_name` Location Standard (WP-4.8)

**Canonical**: imported from `<service>/db/alembic_filters.py` module. Rationale: testable in isolation; reusable across online + offline `configure()` blocks; cleaner separation of filter logic from env wiring.

Inline-in-env.py (legacy phase197 pattern in memory) was migrated to the canonical module in WP-4.8.

### Compose-service pattern (HISTORICAL — retired v2.15.10 / ADR-INF-10)

> ⚠️ **RETIRED in v2.15.10.** Migrations are now an explicit operator step:
> `docker compose run --rm --no-deps --entrypoint /opt/venv/bin/alembic <service> -c <path>/alembic.ini upgrade head`.
> The `<service>-migrate` auto-init container pattern below is historical
> only. Post-P8 DSNs route through PgBouncer (e.g., `@vds-pgbouncer:6432/vds_memory`),
> not `postgres:5432` with `?options=search_path`.

```yaml
# ⚠️ HISTORICAL — do not use
<service>-migrate:
  profiles: ["<service>", "full"]
  build: { context: ../, dockerfile: <service>_orchestrator/Dockerfile }
  image: vds-<service>:${VERSION:-1.0.0}
  container_name: vds-<service>-migrate
  depends_on: { postgres: { condition: service_healthy } }
  environment:
    DATABASE_URL: postgresql://postgres:${VDS_POSTGRES_PASSWORD}@postgres:5432/vds_platform?options=-c%20search_path%3D<schema>%2Cpublic
  restart: "no"
  command: [/opt/venv/bin/alembic, -c, /app/<service>_orchestrator/alembic.ini, upgrade, head]

# ⚠️ HISTORICAL — do not use
<service>-orchestrator:
  depends_on:
    <service>-migrate: { condition: service_completed_successfully }
```

### Schema-Drop-Safe Downgrade Pattern (P5 WP-5.1)

**Problem**: A `0001` migration that creates a service-owned schema and whose original
`downgrade()` does `DROP SCHEMA <schema> CASCADE` will wipe `<schema>.alembic_version`
mid-transaction. Alembic deletes the version row AFTER running `downgrade()` — if the
version table is gone, that step fails and the downgrade aborts with inconsistent state.

**Concrete instance**: `scheduler_orchestrator/alembic/versions/0001_create_sched_schema.py`.
Live `sched.alembic_version` lands in `sched` (in-schema policy above). Running
`alembic downgrade base` with the original `DROP SCHEMA sched CASCADE` would abort.

**Canonical fix** (P5 WP-5.1): make `0001.downgrade()` an intentional no-op:

```python
def downgrade() -> None:
    """Intentional no-op. Do NOT DROP SCHEMA <schema> CASCADE here.

    alembic_version lives in this schema; alembic deletes the version row
    AFTER running downgrade(), so any DROP TABLE/SCHEMA here would cause
    that deletion to fail. Operators wanting full schema teardown must run:
        DROP SCHEMA sched CASCADE;
    manually OUTSIDE alembic, then re-init with: alembic upgrade head.

    By the time alembic reaches 0001.downgrade(), all >=0002 revisions have
    already dropped their own domain tables via their own downgrade() methods.
    """
    # Nothing to drop here — alembic manages <schema>.alembic_version itself.
```

**Post-downgrade state**: `sched` schema persists holding only the now-empty
`alembic_version` table (zero rows). This is intentional — alembic deleted the
version row as part of its own internal cleanup. Full schema teardown is a manual
operator step outside alembic.

**Regression test**: `scheduler_orchestrator/tests/test_alembic_downgrade.py` — runs
`upgrade head` → `downgrade base` → `upgrade head` cycle via testcontainers and
asserts `sched.alembic_version` is populated/empty/repopulated at each phase.

**References**: spec design.md §ADR-INF-11 §Schema-Drop-Safe Downgrade Pattern;
TSK-5.1.1..TSK-5.1.7.

### Idempotence Requirement

Initial squash migrations subsuming pre-Alembic raw SQL (e.g., audit's WP-4.1, progress's WP-4.7) MUST use idempotence guards (`CREATE TABLE IF NOT EXISTS`, `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$`).

Cutover sequence: `alembic stamp 0001` (mark live schema as already-at-revision-N without re-running DDL) → subsequent `alembic upgrade head` is a no-op.

### Consequences

- Audit's 10+ phase-numbered raw SQL files retired to `audit_orchestrator/legacy/migrations/` with a README pointing at the squash migration.
- Audit's `state/store.py:BOOTSTRAP_SQL` (~2500 LOC inline) deleted.
- Audit's `init_schema()` stubbed to `RuntimeError`; production callers swapped to programmatic `alembic upgrade head`.
- Audit's `_run_with_schema_autorepair()` deleted (drift-recovery wrapper now unnecessary by construction).
- Progress's inline `_TABLES` dict + `init_schema()` deleted; CLI startup no longer auto-bootstraps.
~~- New `audit-migrate` and `progress-migrate` Tier-3 CLI compose services (one-shot `alembic upgrade head`, downstream services use `depends_on: { condition: service_completed_successfully }`).~~|
- Migrations run as explicit operator steps (`docker compose run --rm --no-deps <service> --entrypoint /opt/venv/bin/alembic <service> -c <path>/alembic.ini upgrade head`) — no auto-init one-shot services. (v2.15.10 / ADR-INF-10)
- `verify-infra-topology.py` extension (WP-4.6) checks `<schema>.alembic_version` per managed schema.

### Rejected alternatives

- **Flyway / Atlas / golang-migrate** — JVM/Go runtime overhead for no Python-native gain.
- **yoyo-migrations** — smaller community, no autogenerate.
- **Hand-rolled `run_migrations.py`** — phase196 demonstrated the failure mode (4 missing tables undetected until prod 500s); 440-LOC tech debt rejected by phase197.
- **Single monorepo Alembic env** — breaks ADR-INF-1 schema-per-domain ownership; forces cross-service coordination on every migration.

### References

- Alembic tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Reference impl: `memory_orchestrator/alembic/env.py` (phase197 / `f4c91c8d` + `566217e5`)
- Sibling reference: `scheduler_orchestrator/alembic/env.py` (pre-spec; now in-schema per c1a3585d)
- Historical compose pattern (retired v2.15.10): `docker/docker-compose.cli.yml` `audit-migrate` / `progress-migrate` (commit `5655bfe8`); `memory-migrate` (P5 WP-5.3 — originally at commit `3630ae9d` in `docker-compose.services.yml`)
- Spec: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-11 (full text)

## ADR-INF-12 — DRY Alembic env.py via `vds_platform_core.alembic.runtime`

**Status**: Accepted (P5 WP-5.2 — implemented at commit `2f8ec72c`) | **Spec**: `design.md` §ADR-INF-12

All 4 DB-backed services (memory, audit, progress, scheduler) import their Alembic
env.py runtime from `vds_platform_core.alembic.runtime`. Each service's `env.py` is
~25-44 LOC of declarative configuration; the helper module is the single source of
truth for psycopg-v3 dialect dispatch, asyncpg-aware DSN parsing, version_table_schema
defaulting, and the SA2.0 implicit-tx safety contract.

### Operator implications

1. **Where the runtime logic lives**: `platform_core/src/vds_platform_core/alembic/runtime.py`. Debug Alembic failures here, not per-service `env.py` files.
2. **Adding a new DB-backed service**: copy the canonical 25-44 LOC env.py shape from `scheduler_orchestrator/alembic/env.py`. See `infrastructure-evolution-skill/references/adding-a-new-service.md` for the 7-step onboarding.
3. **Bug-fix-once propagation**: a fix in `runtime.py` propagates to all 4 services on next deploy. P5 WP-5.2 reduced cumulative env.py LOC from 621 → 330 (–301 LOC).

→ Full rationale, API surface, rejected alternatives, references: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-12

## ADR-INF-13 — PgBouncer Session-Mode Uniform Topology

**Status**: Accepted (P8 WP-8.1–8.6 — deployed at `8948d1cf`, post-deploy fixes through `808ac1fb`) | **Spec**: `design.md` §ADR-INF-13

Single-DSN routing through `vds-pgbouncer:6432` in session mode. Four per-database stanzas (`vds_audit`, `vds_memory`, `vds_progress`, `vds_sched`) each pin `search_path` via `connect_query`. No `_DIRECT_DSN` parallel; all services route uniformly.

### Operator implications

1. **Health**: `docker exec vds-pgbouncer psql -d pgbouncer -U pgbouncer_admin -c 'SHOW POOLS'` (port 6432).
2. **Stanza edits**: require `docker compose restart vds-pgbouncer` to reload `pgbouncer.ini`.
3. **Auth bootstrap**: `bash scripts/init-pgbouncer-userlist.sh` generates `userlist.txt` from live `pg_shadow`.

→ Full rationale, topology rules, R12 escalation gate, operator one-liners, foot-guns: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-13
