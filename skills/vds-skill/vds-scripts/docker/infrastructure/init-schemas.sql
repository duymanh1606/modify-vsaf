-- =============================================================================
-- VDS Shared Infrastructure — Schema Initialization
-- =============================================================================
-- Phase: ecosystem-infrastructure-evolution P0
-- Created: 2026-04-25
--
-- This script creates schemas and roles for all VDS orchestrators.
-- It is idempotent — safe to run multiple times.
--
-- Schemas:
--   - audit_state: audit_orchestrator (LangGraph checkpoints + audit state)
--   - memory: memory_orchestrator (mem0, evolution, analytics)
--   - sched: scheduler_orchestrator (DBOS schedules, events, chains)
--   - progress: progress_report_orchestrator (report state)
--   - dbos: scheduler_orchestrator (DBOS system tables)
-- =============================================================================

-- =============================================================================
-- OWNERSHIP BOUNDARY (per ADR-INF-11, P4 v2.11.1)
-- =============================================================================
-- This file owns: schemas + roles + DBOS CREATE grant ONLY.
-- This file does NOT own: tables, indexes, functions, views, ENUMs, etc.
--
-- Per-service tables are owned by per-service Alembic environments:
--   - audit_state.* tables  -> audit_orchestrator/alembic/versions/
--   - memory.* tables       -> memory_orchestrator/alembic/versions/
--   - sched.* tables        -> scheduler_orchestrator/alembic/versions/
--   - progress.* tables     -> progress_report_orchestrator/alembic/versions/
--   - dbos.* tables         -> DBOS framework (system tables; CREATE granted to vds_sched_runtime)
--
-- This script runs ONCE at postgres container init (Docker entrypoint
-- /docker-entrypoint-initdb.d/01-schemas.sql); it does NOT re-run on
-- subsequent container restarts. Schema/role changes require a fresh
-- volume init (rare; coordinate with operator).
--
-- Adding tables here would create a divergent source-of-truth from the
-- per-service Alembic envs. DO NOT add CREATE TABLE statements to this file.
-- =============================================================================

-- v2.0.17 N.55: pre-install uuid-ossp extension so DBOS bootstrap (which issues
-- `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` at first launch) does NOT require
-- SUPERUSER privileges on every fresh container start. Pre-installing here lets
-- the future v2.0.18 least-privilege DSN switch (vds_sched_runtime) work; today
-- DBOS bootstrap runs as `postgres` superuser so `CREATE EXTENSION` succeeds
-- regardless, but pre-installing makes the privilege contract explicit and
-- forward-compatible.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS audit_state;
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS sched;
CREATE SCHEMA IF NOT EXISTS progress;
CREATE SCHEMA IF NOT EXISTS dbos;

-- Create roles (passwords are set via environment variables at runtime)
-- Note: In production, passwords should be managed via Docker secrets or vault

-- Role: audit_orchestrator application user
DO $$
BEGIN
    CREATE ROLE vds_audit_app WITH LOGIN;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

-- Role: memory_orchestrator application user
DO $$
BEGIN
    CREATE ROLE vds_memory_app WITH LOGIN;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

-- Role: scheduler_orchestrator application user
DO $$
BEGIN
    CREATE ROLE vds_scheduler_app WITH LOGIN;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

-- Role: DBOS scheduler runtime user
DO $$
BEGIN
    CREATE ROLE vds_sched_runtime WITH LOGIN;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

-- Role: progress_report_orchestrator application user
DO $$
BEGIN
    CREATE ROLE vds_progress_app WITH LOGIN;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

-- v2.0.17 N.52: Role passwords for least-privilege DSN switch.
-- Without these ALTER ROLE statements, the roles exist with LOGIN but no
-- password — peer/trust auth via `docker exec psql -U <role>` works, but
-- TCP connections from other containers (the canonical deployment path)
-- fail with "password authentication failed". The passwords below are
-- DEFAULT DEV PASSWORDS for the local shared-infra bring-up. Operators MUST
-- rotate them via a separate post-init step in production:
--
--   docker exec vds-postgres psql -U postgres -c \
--     "ALTER ROLE vds_scheduler_app WITH PASSWORD '<production-secret>';"
--
-- and update the compose DATABASE_URL accordingly. The ecosystem-scheduling
-- spec (TSK-N.52 carryover) tracks the cross-orchestrator coordination
-- needed to migrate the canonical DSN from `postgres` superuser to
-- least-privilege role for all 4 schema owners.
ALTER ROLE vds_audit_app     WITH PASSWORD 'dev_audit_pw';
ALTER ROLE vds_memory_app    WITH PASSWORD 'dev_memory_pw';
ALTER ROLE vds_scheduler_app WITH PASSWORD 'dev_scheduler_app_pw';
ALTER ROLE vds_sched_runtime WITH PASSWORD 'dev_sched_runtime_pw';
ALTER ROLE vds_progress_app  WITH PASSWORD 'dev_progress_pw';

-- v2.0.17 N.52: vds_sched_runtime needs database-level CREATE for DBOS
-- bootstrap (DBOS issues `CREATE SCHEMA "dbos"` without IF NOT EXISTS, which
-- requires db-level CREATE even when the schema already exists).
GRANT CREATE ON DATABASE vds_platform TO vds_sched_runtime;

-- Grant schema usage
GRANT USAGE ON SCHEMA audit_state TO vds_audit_app;
GRANT USAGE ON SCHEMA memory TO vds_memory_app;
GRANT USAGE ON SCHEMA sched TO vds_scheduler_app, vds_sched_runtime;
GRANT USAGE ON SCHEMA progress TO vds_progress_app;
GRANT USAGE ON SCHEMA dbos TO vds_sched_runtime;

-- Grant CREATE privilege on dbos schema for DBOS system tables
GRANT USAGE, CREATE ON SCHEMA dbos TO vds_sched_runtime;

-- Grant ALL privileges on each schema to its owner role
GRANT ALL PRIVILEGES ON SCHEMA audit_state TO vds_audit_app;
GRANT ALL PRIVILEGES ON SCHEMA memory TO vds_memory_app;
GRANT ALL PRIVILEGES ON SCHEMA sched TO vds_scheduler_app, vds_sched_runtime;
GRANT ALL PRIVILEGES ON SCHEMA progress TO vds_progress_app;
GRANT ALL PRIVILEGES ON SCHEMA dbos TO vds_sched_runtime;

-- Default privileges so future tables are auto-granted
ALTER DEFAULT PRIVILEGES IN SCHEMA audit_state GRANT ALL ON TABLES TO vds_audit_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit_state GRANT ALL ON SEQUENCES TO vds_audit_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT ALL ON TABLES TO vds_memory_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA memory GRANT ALL ON SEQUENCES TO vds_memory_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA sched GRANT ALL ON TABLES TO vds_scheduler_app, vds_sched_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA sched GRANT ALL ON SEQUENCES TO vds_scheduler_app, vds_sched_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA progress GRANT ALL ON TABLES TO vds_progress_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA progress GRANT ALL ON SEQUENCES TO vds_progress_app;

-- Note: dbos schema uses USAGE, CREATE (not ALL) since DBOS manages its own objects

-- =============================================================================
-- v2.15.9 (P8 follow-up F20 close): no database-level search_path override
-- =============================================================================
-- Pre-P8, this database had `search_path = 'memory, public'` set at the database
-- level (a P0-leftover from when vds_platform was the memory-only DB). Post-P8,
-- search_path pinning happens in two places:
--   1. PgBouncer per-stanza `connect_query='SET search_path TO <schema>, public'`
--      (fires on backend SPAWN — see docker/infrastructure/pgbouncer/pgbouncer.ini)
--   2. Per-application connect-time SQL (SQLAlchemy `connect` event listener,
--      psycopg helper wrapper) for unqualified-DML resilience across PgBouncer
--      backend reuse — see references/connection-pooling.md F21/D1 caveats
--
-- A database-level default would silently override the per-stanza connect_query
-- value after `server_reset_query=DISCARD ALL` resets session state between
-- client checkouts in session mode (originally caught as F20 in v2.15.6 audit).
-- This RESET ensures fresh deploys never regress to the legacy default. The
-- statement is a no-op when search_path is already unset, so it's safe to
-- run on every fresh init.
ALTER DATABASE vds_platform RESET search_path;
