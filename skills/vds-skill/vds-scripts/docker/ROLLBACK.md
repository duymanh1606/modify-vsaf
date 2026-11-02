# VDS Infrastructure Rollback Guide

> **Current spec**: `ecosystem-infrastructure-evolution` v2.15.20 at vds-scripts master `afb95f70`. The historical version references in this document (v2.15.3, v2.15.6, v2.15.9, v2.15.10, v2.15.12) are intentional — they document phase-specific rollback scenarios. v2.15.17–v2.15.20 introduced: `vds_scheduler_reports:/opt/reports` named volume (v2.15.19); `mcp_server` Typer wrap with `serve` sub-command (v2.15.19); `EcosystemReportRun.id` ORM-layer `Mapped[Optional[str]]` for server-default UUID generation (v2.15.20). See `ADR.md` for the current architectural state.

## Overview

This document describes rollback procedures for Phases P0–P6 (ecosystem-infrastructure-evolution, post-P7 alignment 2026-04-27). Rollback may be needed if:
- Critical services fail to start after migration
- Data integrity issues are discovered
- Performance degradation exceeds acceptable thresholds

## Pre-Migration Safety

Before running P0 migration:
1. Take `pg_dump` snapshots of production databases
2. Document current working configuration
3. Schedule maintenance window

## Container Cycling Conventions (v2.15.9+)

**Compose-managed paths are canonical. Direct `docker` commands bypass compose state and create invisible drift.**

| Operation | Canonical (use this) | Avoid (creates drift) |
|---|---|---|
| Restart a service | `docker compose -f docker-compose.infra.yml -f docker-compose.services.yml -f docker-compose.cli.yml --profile <p> restart <service>` | `docker restart <container_name>` |
| Re-create after config change | `docker compose ... up -d --force-recreate <service>` | `docker stop <name> && docker start <name>` |
| Stop a service cleanly | `docker compose ... stop <service>` | `docker stop <name>` |
| Remove a service | `docker compose ... rm -f <service>` | `docker rm -f <name>` |
| Postgres DDL fix-up (e.g. `ALTER DATABASE ... RESET search_path`) | Encode in `docker/infrastructure/init-schemas.sql` so fresh deploys pick it up | `docker exec vds-postgres psql -c 'ALTER ...'` |
| One-shot DB migration | `docker compose ... run --rm --no-deps <orchestrator-service> /opt/venv/bin/alembic -c /app/<svc>_orchestrator/alembic.ini upgrade head` (v2.15.10+ canonical; uses the existing service container, no separate migrate service block) | Ad-hoc `docker exec ... alembic upgrade head`; persistent `*-migrate` service blocks (Sub-shape 3B retired in v2.15.10) |
| PgBouncer admin runtime commands (RELOAD, RECONNECT, PAUSE, RESUME) | `docker exec` IS acceptable — these are transient runtime state, not config | n/a |
| Read-only diagnostics (`SHOW POOLS`, `pg_tables`, log tails) | `docker exec` IS acceptable — read-only | n/a |

**Why this matters:**
- `docker restart <name>` doesn't update compose's notion of when the service was last cycled. A `docker compose ps` shows confusing state.
- `docker exec ... ALTER DATABASE` mutations are invisible to a fresh redeploy. Operators who reprovision from clean compose state lose the fix-up. Validators (verify-infra-topology) can't see the gap.
- `docker rm -f` orphans named volumes if the operator was relying on compose to clean them up.

**Service-name rule:** compose commands use service-key names (e.g., `pgbouncer`, `memory-api`). `docker` commands use container_name labels (e.g., `vds-pgbouncer`, `vds-memory-api`). Mixing them produces "service depends on undefined service" errors. See `docker-compose.infra.yml:154` for the canonical mapping (`pgbouncer:` service-key, `container_name: vds-pgbouncer`).

**P8-related rollback case:**
- `ALTER DATABASE vds_platform RESET search_path` (F20 fix from v2.15.6) is now encoded in `docker/infrastructure/init-schemas.sql` (v2.15.9). Operators rebuilding from clean compose state automatically get the fix; no manual `docker exec` step needed.

## Phase Coverage Map

The §Overview claims rollback procedures for Phases P0–P6. Coverage is structured as:

| Phase | Section | Notes |
|---|---|---|
| P0 — Shared infra + audit/memory/pdf migration | §Scenario 1 (Full Rollback) | The only phase with destructive infra changes; full rollback via legacy compose restore + `pg_restore`. |
| P1 — scheduler + multi-agent containers | §Scenario 2 (Partial Rollback) | Additive only; rollback = stop the new containers, no data restore needed. |
| P2 — progress + db-query optional services | §Scenario 2 (Partial Rollback) | Additive only; same as P1. |
| P3 — Compose cleanup + Makefile + skill | No-op-with-rationale | Documentation/structural cleanup only; no runtime artifacts to roll back. Re-add of legacy compose files is covered under §Scenario 1. |
| P4 — Alembic + Legacy Retirement | §Phase P4 — Alembic Migration Standardization Rollback | Explicit alembic version revert procedures. |
| P5 — Infrastructure Consistency & Migration Standardization | §Phase P5 — Infrastructure Consistency & Migration Standardization Rollback | Helper-module backout + per-service env.py revert. |
| P6 — Validation Hardening | §Phase P6 — Validation Hardening Rollback | Test-only phase; rollback = revert pytest suites if regression detected. |
| P7 — Doc Alignment & ADR Mirror Closure | No-op-with-rationale | Docs-only phase (docker/ADR.md → routing manifest, SKILL.md cleanup, ROLLBACK §P4–P6 added, MIGRATION.md/.env.template `REDIS_TOOL_DISCOVERY_DB=9`). No runtime artifacts to roll back; revert via `git revert` of the merge commit if needed. |
| P8 — Connection Pool Hardening | §Phase P8 — Connection Pool Hardening Rollback (v2.15.3 session-mode) | Tier 1.5 PgBouncer container; env-flip + container removal (no Postgres restart since max_connections stays at 500). |

P0–P3 do not have dedicated `## Phase P<N> Rollback` headers because their rollback content is structurally subsumed by Scenarios 1/2; the table above is the authoritative routing.

## Rollback Scenarios

### Scenario 1: Full Rollback (Pre-Migration State)

Use this when rolling back the entire P0 migration.

#### Steps

1. **Stop all new services**
```bash
# Stop P0 services
docker compose -f docker/docker-compose.infra.yml down
docker compose -f docker/docker-compose.services.yml down
# CLI containers (docker-compose.cli.yml) have restart: "no" and exit on their
# own; a separate `down` is only needed if a CLI invocation is still running.
```

2. **Restore legacy compose files from git history** (v2.15.12+: `docker/legacy/`
   directory removed per no-fallback directive — recover from git instead)
```bash
# Find the last commit that contained the legacy compose files (just before
# v2.15.12 removal):
git log --diff-filter=D --name-only --pretty=format: -- 'docker/legacy/*' | head -5

# Checkout the legacy compose files from that SHA into a scratch dir:
LEGACY_SHA="<paste-sha-from-above>"
git show "${LEGACY_SHA}:docker/legacy/audit_orchestrator-docker-compose.yml" \
    > audit_orchestrator/docker-compose.yml
git show "${LEGACY_SHA}:docker/legacy/memory_orchestrator-compose.yaml" \
    > memory_orchestrator/compose.yaml
git show "${LEGACY_SHA}:docker/legacy/memory_orchestrator-compose.prod.yaml" \
    > memory_orchestrator/compose.prod.yaml
git show "${LEGACY_SHA}:docker/legacy/pdf_orchestrator-docker-compose.yml" \
    > pdf_orchestrator/docker-compose.yml
```

3. **Restart legacy infrastructure**
```bash
# Start legacy services
cd audit_orchestrator && docker compose up -d postgres
cd ../memory_orchestrator && docker compose up -d postgres redis
cd ../pdf_orchestrator && docker compose up -d redis
```

4. **Restore database from snapshots**
```bash
# Restore audit state
docker exec -i vds-audit-postgres pg_restore -U vds_audit -d vds_audit_checkpoints < backups/pre-p0-audit.dump

# Restore memory
docker exec -i vds-ai-memory-postgres-1 pg_restore -U vds_user -d vds_memory < backups/pre-p0-memory.dump
```

5. **Verify rollback**
```bash
# Check services are running
docker ps

# Test connectivity
psql -h localhost -p 5434 -U vds_audit -d vds_audit_checkpoints -c "SELECT 1"
psql -h localhost -p 5432 -U vds_user -d vds_memory -c "SELECT 1"
```

### Scenario 2: Partial Rollback (Individual Orchestrator)

Use this when only one orchestrator fails and others are healthy.

#### Audit Orchestrator Rollback

```bash
# 1. Stop audit orchestrator
docker compose -f docker/docker-compose.services.yml stop audit-orchestrator

# 2. Restore audit compose from git history (v2.15.12+: docker/legacy/ removed)
LEGACY_SHA="$(git log --diff-filter=D --name-only --pretty=format:%H -- 'docker/legacy/*' | head -1)"
git show "${LEGACY_SHA}:docker/legacy/audit_orchestrator-docker-compose.yml" > audit_orchestrator/docker-compose.yml

# 3. Start legacy audit infrastructure
cd audit_orchestrator
docker compose up -d audit-postgres

# 4. Start audit orchestrator
docker compose up -d

# 5. Verify
curl localhost:5434/health || docker logs vds-audit-postgres
```

#### Memory Orchestrator Rollback

```bash
# 1. Stop memory services
docker compose -f docker/docker-compose.services.yml stop memory-api memory-worker

# 2. Restore memory compose from git history (v2.15.12+: docker/legacy/ removed)
LEGACY_SHA="$(git log --diff-filter=D --name-only --pretty=format:%H -- 'docker/legacy/*' | head -1)"
git show "${LEGACY_SHA}:docker/legacy/memory_orchestrator-compose.yaml"      > memory_orchestrator/compose.yaml
git show "${LEGACY_SHA}:docker/legacy/memory_orchestrator-compose.prod.yaml" > memory_orchestrator/compose.prod.yaml

# 3. Start legacy memory infrastructure
cd memory_orchestrator
docker compose up -d postgres redis

# 4. Verify database connection
docker exec vds-memory-postgres psql -U vds_user -d vds_memory -c "SELECT 1"
```

#### PDF Orchestrator Rollback

```bash
# 1. Stop pdf orchestrator
docker compose -f docker/docker-compose.services.yml stop pdf-orchestrator

# 2. Restore pdf compose
git checkout HEAD~1 -- pdf_orchestrator/docker-compose.yml
git checkout HEAD~1 -- pdf_orchestrator/docker-compose.prod.yml

# 3. Start legacy pdf infrastructure
cd pdf_orchestrator
docker compose up -d redis

# 4. Start pdf orchestrator
docker compose up -d
```

## Downtime Estimation

| Operation | Estimated Downtime |
|-----------|------------------|
| Shared infra startup | 30-60 seconds |
| Schema migration | 2-5 minutes |
| Orchestrator restart | 1-2 minutes per service |
| **Total (full rollback)** | **15-30 minutes** |
| **Total (single orchestrator)** | **5-10 minutes** |

## Data Safety

### Backup Verification

Before migration, verify backups are valid:

```bash
# Test audit backup
docker exec -i vds-audit-postgres pg_restore -U vds_audit -d vds_audit_checkpoints --list < backups/pre-p0-audit.dump | head -20

# Test memory backup
docker exec -i vds-memory-postgres pg_restore -U vds_user -d vds_memory --list < backups/pre-p0-memory.dump | head -20
```

### Point-in-Time Recovery

If data corruption occurs after migration:

```bash
# Stop writing to databases
docker compose stop

# Restore from backup
docker exec -i vds-postgres psql -U postgres -d vds_platform < backups/pre-p0-audit.sql
```

## Monitoring During Rollback

Watch these indicators:

```bash
# Service health
watch docker ps

# Database connections
docker exec vds-postgres psql -U postgres -d vds_platform -c "SELECT count(*) FROM pg_stat_activity"

# Error logs
docker logs -f vds-audit-orchestrator
docker logs -f vds-memory-api
```

## Emergency Contacts

| Service | Contact |
|---------|---------|
| Audit Orchestrator | Platform Team |
| Memory Orchestrator | Platform Team |
| PDF Orchestrator | Platform Team |
| PostgreSQL (Shared) | Platform Team |
| Redis (Shared) | Platform Team |

## Post-Rollback Actions

1. **Document the incident**
   - Create incident report
   - Note time of rollback
   - Document root cause

2. **Notify stakeholders**
   - Alert affected teams
   - Provide ETA for resolution

3. **Plan fix**
   - Identify root cause
   - Create fix in isolated branch
   - Test thoroughly before redeployment

## Phase P4 — Alembic Migration Standardization Rollback

Use this when rolling back P4 schema standardization and Alembic adoption.

### Steps

1. **Stop affected services**
```bash
# Stop orchestrators that use alembic
docker compose -f docker/docker-compose.services.yml stop audit-orchestrator progress-report-orchestrator scheduler-orchestrator
docker compose -f docker/docker-compose.services.yml stop memory-api memory-worker
```

2. **Alembic schema rollback**
```bash
# v2.15.10+: migrate containers retired; use the orchestrator service via `docker compose run --rm`
COMPOSE_FILES="-f docker/docker-compose.infra.yml -f docker/docker-compose.services.yml -f docker/docker-compose.cli.yml"

# Downgrade audit schema to base (pre-P4 state). audit + progress images have
# ENTRYPOINT — use --entrypoint override; memory image has no ENTRYPOINT.
docker compose $COMPOSE_FILES --profile audit run --rm --no-deps \
    --entrypoint /opt/venv/bin/alembic audit-orchestrator \
    -c /app/audit_orchestrator/alembic.ini downgrade base

# Downgrade progress schema to base
docker compose $COMPOSE_FILES --profile progress run --rm --no-deps \
    --entrypoint /opt/venv/bin/alembic progress-report-orchestrator \
    -c /app/progress_report_orchestrator/alembic.ini downgrade base

# Downgrade scheduler schema to base (scheduler runs migrations in entrypoint;
# downgrade still requires explicit alembic invocation if needed)
docker compose $COMPOSE_FILES --profile full run --rm --no-deps \
    --entrypoint /opt/venv/bin/alembic scheduler-orchestrator \
    -c /app/scheduler_orchestrator/alembic.ini downgrade base

# WARNING: WP-5.1 schema-drop-safe caveat applies here.
# Pre-P5 versions had 0001.downgrade() with "DROP SCHEMA CASCADE"
# If rolling back to pre-P5 commits, transaction may abort with error:
# "ERROR: cannot drop schema sched because other objects in same schema
#  depend on it (alembic_version)"
# See ADR-INF-11 in design.md for the full pattern explanation.
```

3. **Manual schema teardown (full rollback only)**
```bash
# If alembic downgrade failed due to schema-drop-safe pattern:
docker exec vds-postgres psql -U postgres -d vds_platform -c "DROP SCHEMA audit_state CASCADE;"
docker exec vds-postgres psql -U postgres -d vds_platform -c "DROP SCHEMA progress CASCADE;"
docker exec vds-postgres psql -U postgres -d vds_platform -c "DROP SCHEMA sched CASCADE;"

# Re-init schemas (creates schema + role + DBOS grants only, no tables)
docker cp docker/init-schemas.sql vds-postgres:/tmp/
docker exec vds-postgres psql -U postgres -d vds_platform -f /tmp/init-schemas.sql
```

4. **Revert P4 commits**
```bash
# P4 merge commit and follow-on commits
git revert -m 1 de362279  # P4 merge
git revert 29463e47       # P4 live-deploy follow-up
git revert c1a3585d       # ADR-INF-11 simplification
git revert 7e86db0c       # Additional P4 follow-ups
git revert 6d1035e4       # Additional P4 follow-ups
```

5. **Restore from pg_dump snapshots**
```bash
# Restore pre-P0 database snapshots (if available in docker/backups/)
docker exec -i vds-postgres pg_restore -U postgres -d vds_platform < docker/backups/pre-p0-audit.dump
docker exec -i vds-postgres pg_restore -U postgres -d vds_platform < docker/backups/pre-p0-progress.dump

# Verify schemas restored
docker exec vds-postgres psql -U postgres -d vds_platform -c "\dn" | grep -E "audit_state|progress"
```

6. **Verify rollback**
```bash
# Check services are running
docker ps | grep -E "audit-orchestrator|progress|memory"

# Test audit connectivity
docker exec vds-postgres psql -U postgres -d vds_platform -c "SELECT COUNT(*) FROM audit_state.checkpoints;"

# Verify alembic_version tables are gone
docker exec vds-postgres psql -U postgres -d vds_platform -c "SELECT version_num FROM audit_state.alembic_version;" 2>&1 | grep -i "does not exist"
```

## Phase P5 — Infrastructure Consistency & Migration Standardization Rollback

Use this when rolling back P5's env.py DRY refactor, migrate-tier relocation, and validator hardening.

### Steps

1. **Stop affected services**
```bash
# Stop all services that depend on the refactored env.py files
docker compose -f docker/docker-compose.services.yml stop \
  audit-orchestrator progress-report-orchestrator scheduler-orchestrator \
  memory-api memory-worker
```

2. **Revert env.py inline boilerplate**
```bash
# Restore inline env.py from pre-P5 state (before helper-import refactor)
git checkout 2f8ec72c^ -- \
  memory_orchestrator/alembic/env.py \
  audit_orchestrator/alembic/env.py \
  progress_report_orchestrator/alembic/env.py \
  scheduler_orchestrator/alembic/env.py
```

3. **Revert migrate-tier relocation**
```bash
# Move memory-migrate service back to services.yml (from cli.yml)
git checkout 7f9751b4^ -- \
  docker/docker-compose.services.yml \
  docker/docker-compose.cli.yml \
  Makefile \
  docker/ADR.md
```

4. **Revert workspace dependency** (optional; `vds-platform-core` can remain)
```bash
# If removing the helper module entirely
git checkout 2f8ec72c^ -- */pyproject.toml
```

5. **Revert sanity validator extensions**
```bash
# Restore pre-P5 validator scripts (drops 4 new sanity checks)
git checkout 7b2afcde^ -- \
  scripts/verify-infra-topology.py \
  .gpt-5.4/specs/ecosystem-infrastructure-evolution/scripts/verify-spec-sanity.py
```

6. **Full P5 merge revert** (alternative to steps 2-5)
```bash
# Single-shot revert of P5 merge commit
git revert -m 1 b95b586b

# Also revert post-merge follow-up fixups
git revert e8de66d2
git revert 921c95a9
```

7. **Database schema considerations**
```bash
# CRITICAL: Do NOT run "alembic downgrade base" against scheduler post-P5-revert
# Reason: pre-P5 0001.downgrade() contains "DROP SCHEMA sched CASCADE"
# while alembic_version lives in the sched schema → transaction abort
#
# Instead, use one of:
# a) Restore from pg_dump snapshot (safest)
docker exec -i vds-postgres pg_restore -U postgres -d vds_platform < docker/backups/pre-p5-scheduler.dump

# b) Manual schema drop + re-init
docker exec vds-postgres psql -U postgres -d vds_platform -c "DROP SCHEMA sched CASCADE;"
docker cp docker/init-schemas.sql vds-postgres:/tmp/
docker exec vds-postgres psql -U postgres -d vds_platform -f /tmp/init-schemas.sql
```

8. **Verify rollback**
```bash
# Check services restart cleanly
docker compose -f docker/docker-compose.services.yml up -d
docker ps | grep -E "orchestrator|memory"

# Verify env.py is no longer importing from vds_platform_core
grep -l "vds_platform_core.alembic.runtime" */alembic/env.py 2>/dev/null | wc -l
# Expected output: 0

# Check migrate-tier service location
docker compose -f docker/docker-compose.services.yml config | grep -A5 "memory-migrate"
```

## Phase P6 — Validation Hardening Rollback

Use this when rolling back P6's preventive tests, operator documentation, and skill updates.

### Steps

1. **Revert P6 test additions** (low risk; no production code)
```bash
# P6 added prevention tests only; reverting removes test coverage but no functional code
git revert -m 1 8d7bed32

# Post-merge follow-up fixups
git revert 1569c1a9  # Audit Dockerfile vds_cli wiring
git revert 8ab4d5b9  # Smoke deploy RUNBOOK_STEPS sync
```

2. **Revert skill v1.7.17** (if needed)
```bash
# In WHO-project/vds-skills repo:
cd WHO-project/vds-skills
git revert 92fcc7b  # infrastructure-evolution-skill v1.7.1 commit

# Re-sync skill catalog
./scripts/worktree_uv.sh run --project vds_cli vds-cli skills sync --agent claude
```

3. **Verify rollback**
```bash
# Run test suite to confirm no P5 regressions from test removal
cd WHO-project/vds-scripts
make test

# Verify test files removed
find . -name "test_dockerfile_correctness.py" -o -name "test_makefile_loadouts.py" 2>/dev/null | wc -l
# Expected output: 0

# Confirm DEPLOYMENT-RUNBOOK.md no longer has "Common Deploy Gotchas"
grep -n "Common Deploy Gotchas" docker/DEPLOYMENT-RUNBOOK.md | wc -l
# Expected output: 0
```

4. **Restart services** (P6 changed no runtime code)
```bash
# Services should restart without issues
docker compose -f docker/docker-compose.services.yml restart

# Verify topology is still valid (P5 validators unaffected)
make verify
# Expected: 35/35 PASS (pre-P6 count)
```

### P6 Rollback Notes

- **Low risk**: P6 contains only tests, documentation, and skill metadata. No orchestrator runtime code changed.
- **No database migration needed**: P6 did not add or modify any schema migrations.
- **Skill sync**: If you reverted the skill in vds-skills, re-run skills sync to propagate the older version to local catalog.
- **Test coverage**: Reverting P6 tests removes prevention guards for deploy-time bugs (Dockerfile correctness, Makefile loadouts, scheduler downgrade). Document the decision to rollback.

## Phase P8 — Connection Pool Hardening Rollback (v2.15.3 session-mode topology)

P8 introduces the Tier 1.5 PgBouncer container (`vds-pgbouncer`) with `pool_mode=session` global default and per-database stanzas (`vds_audit`, `vds_memory`, `vds_progress`, `vds_sched`). All services route through it via single `VDS_<SVC>_DSN` env vars. **`max_connections` stays at 500** (session mode is 1:1 client:backend; multiplexing not claimed).

### P8 First-Time Deploy Prerequisites (MUST run before first `up -d`)

The PgBouncer container requires `docker/infrastructure/pgbouncer/userlist.txt` to exist as a regular file (a stub is committed; replace with real password hashes BEFORE first `up -d`). Without this step, Docker's bind-mount semantics auto-create the source path as a directory, breaking PgBouncer with `auth_file: not a regular file`.

**Recommended (single-command path)**: run the helper script:
```bash
bash scripts/init-pgbouncer-userlist.sh
```
The script handles all of steps 0a–0e below (env validation, role creation, userlist generation, line-count sanity check, skip-worktree mark). Then jump straight to step 0f.

**Manual path (operator preference)**:

```bash
# 0a. Set PGBOUNCER_ADMIN_PASSWORD in ~/.vds/.env (replace the placeholder default
#     PGBOUNCER_ADMIN_PASSWORD=pgbouncer_admin_secret_change_me with a real value).

# 0b. Create the 3 PgBouncer-level users in Postgres (one-time, idempotent):
docker exec vds-postgres psql -U postgres -v pw="$PGBOUNCER_ADMIN_PASSWORD" -c "
  DO \$\$ BEGIN
    CREATE USER pgbouncer_admin WITH PASSWORD :'pw';
    CREATE USER pgbouncer_stats WITH PASSWORD :'pw';
    CREATE USER pgbouncer_auth  WITH PASSWORD :'pw';
    GRANT pg_read_all_settings TO pgbouncer_stats;
  EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
"

# 0c. Generate the real userlist.txt from pg_shadow:
docker exec vds-postgres psql -U postgres -t -A -c "
  SELECT '\"' || usename || '\" \"' || passwd || '\"'
  FROM pg_shadow
  WHERE usename IN ('postgres','pgbouncer_admin','pgbouncer_stats','pgbouncer_auth')
    AND passwd IS NOT NULL
" > docker/infrastructure/pgbouncer/userlist.txt

# 0d. Verify the file is non-empty + has 4 lines:
wc -l docker/infrastructure/pgbouncer/userlist.txt   # expected: 4

# 0e. Mark the file as locally-skipped so future modifications stay out of git:
git update-index --skip-worktree docker/infrastructure/pgbouncer/userlist.txt

# 0f. Now bring up vds-pgbouncer:
docker compose -f docker/docker-compose.infra.yml --profile infra up -d vds-pgbouncer

# 0g. Confirm healthcheck passes:
docker compose -f docker/docker-compose.infra.yml exec vds-pgbouncer \
  psql -h 127.0.0.1 -p 5432 -U pgbouncer_admin -d pgbouncer -tAc 'SHOW VERSION;'
```

Once these prerequisites are in place, services can be restarted to route through the pooler.

### Rollback Steps

Because `max_connections` is unchanged, P8 rollback does **not** require a Postgres restart and is a low-risk procedure.

```bash
# 1. Bulk-flip service DSNs from PgBouncer back to direct Postgres in ~/.vds/.env:
#    VDS_<SVC>_DSN=postgresql://...@vds-pgbouncer:6432/vds_<svc>
#    →
#    VDS_<SVC>_DSN=postgresql://...@vds-postgres:5432/vds_platform?options=-c%20search_path%3D<schema>%2Cpublic
#
#    Restore the original P0–P7 DSN format with vds-postgres:5432 host
#    + ?options=search_path query parameter for schema pinning.

# 2. Restart all services with new env values (no postgres restart needed).
# IMPORTANT: Compose service names are HYPHENATED (audit-orchestrator, NOT
# audit_orchestrator). Verify the active set via `docker compose ... config --services`.
docker compose -f docker/docker-compose.infra.yml \
               -f docker/docker-compose.services.yml \
               -f docker/docker-compose.cli.yml \
               --profile full up -d --no-deps \
               audit-orchestrator memory-api memory-worker \
               progress-report-orchestrator scheduler-orchestrator

# 3. Confirm services are connected to direct Postgres (not PgBouncer):
docker exec vds-memory-api env | grep VDS_MEMORY_DB_DSN
# Expected: vds-postgres:5432, NOT vds-pgbouncer:6432

# 4. Remove the PgBouncer container:
docker compose -f docker/docker-compose.infra.yml stop vds-pgbouncer
docker compose -f docker/docker-compose.infra.yml rm -f vds-pgbouncer
# Then remove the `vds-pgbouncer` service block from docker-compose.infra.yml
# (or keep the block + revert env files; the unused container won't hurt).

# 5. Verify infra:
make verify
# Expected: 35/35 PASS (pre-P8 count; the 6 P8 checks become irrelevant)
```

### P8 Rollback Notes

- **No `max_connections` change to revert**: v2.15.3 keeps `max_connections=500`. No Postgres restart needed during rollback. Compare to the v2.15.2 transaction-mode plan (deleted) which would have required ordered max_connections-restart-then-env-flip-then-pooler-removal.
- **No `_postmaster` GUC changes**: v2.15.3 doesn't touch `max_connections`, `shared_buffers`, or any other postmaster-level GUC. Just env values + container removal.
- **No service code rollback**: v2.15.3 introduced **zero service code changes** (only env values changed). DBOS config, asyncpg config, helper module, alembic env.py — all unchanged from P0–P7.
- **Userlist + pgbouncer.ini cleanup** (optional): if rolling back permanently, also remove `docker/infrastructure/pgbouncer/` directory and the `.gitignore` entry for `userlist.txt`.
- **Skill catalog rollback** (optional): the v1.7.17 (infrastructure-evolution), v1.0.6 (scheduler), v2.9.0 (mem0-deploy), v23.1.0 (audit-orchestrator) skill bumps are docs-only. Revert via `git revert` of the skill commits in vds-skills repo if desired.
