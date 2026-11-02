#!/usr/bin/env bash
# =============================================================================
# init-pgbouncer-userlist.sh — Generate userlist.txt for vds-pgbouncer
# =============================================================================
# Codifies the §First-Time Deploy Prerequisites procedure from
# docker/ROLLBACK.md §Phase P8. Run BEFORE first `docker compose up -d
# vds-pgbouncer` so the bind-mount target is a regular file with real
# password hashes (not a directory auto-created by Docker).
#
# Prerequisites:
#   - vds-postgres container running (`docker compose -f docker-compose.infra.yml --profile infra up -d postgres`)
#   - PGBOUNCER_ADMIN_PASSWORD set in ~/.vds/.env (replace the default
#     `pgbouncer_admin_secret_change_me` placeholder with a strong value)
#
# Usage:
#   bash scripts/init-pgbouncer-userlist.sh
#
# Idempotency: safe to run multiple times. CREATE USER fires only when the
# role is absent (NOT EXISTS guard via \gexec); ALTER USER always runs to
# keep the password current. Re-running regenerates userlist.txt with
# whatever pg_shadow currently contains.
#
# F18 fix (v2.15.6): previous version used psql `:'pw'` interpolation INSIDE
# `$$ ... $$` DO blocks, where psql lexer-time substitution does NOT fire
# (the variable becomes literal `:'pw'` text). Result: only `postgres` user
# got created; pgbouncer_admin/stats/auth were silently skipped despite the
# script reporting success. This rewrite uses top-level interpolation +
# \gexec for create-or-update semantics outside any DO block.
# =============================================================================

set -euo pipefail

# --- locate repo root + .env --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
USERLIST_PATH="$REPO_ROOT/docker/infrastructure/pgbouncer/userlist.txt"
ENV_FILE="${HOME}/.vds/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found. Create it from docker/infrastructure/.env.template before running." >&2
    exit 1
fi

# Source env file to pick up PGBOUNCER_ADMIN_PASSWORD + VDS_POSTGRES_PASSWORD
# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

# v2.15.15 (A1/A2): require 3 distinct passwords (admin / stats / auth).
# Pre-v2.15.15, ADMIN_PASSWORD was reused for all 3 roles. Defense-in-depth
# requires per-role credentials so compromise of one role doesn't grant the
# others. If STATS or AUTH passwords are unset, fall back to ADMIN with a
# WARNING (preserves backward compat for in-progress deploys, but flags the
# operator to rotate).
for var in PGBOUNCER_ADMIN_PASSWORD; do
    val="${!var:-}"
    if [[ -z "$val" ]] || [[ "$val" == "pgbouncer_admin_secret_change_me" ]]; then
        echo "ERROR: $var must be set to a real value (not the default placeholder) in $ENV_FILE" >&2
        exit 2
    fi
done

if [[ -z "${PGBOUNCER_STATS_PASSWORD:-}" ]] || [[ "$PGBOUNCER_STATS_PASSWORD" == "pgbouncer_stats_secret_change_me" ]]; then
    echo "WARNING: PGBOUNCER_STATS_PASSWORD unset/default — falling back to ADMIN password (insecure; rotate via openssl rand -hex 16)" >&2
    PGBOUNCER_STATS_PASSWORD="$PGBOUNCER_ADMIN_PASSWORD"
fi
if [[ -z "${PGBOUNCER_AUTH_PASSWORD:-}" ]] || [[ "$PGBOUNCER_AUTH_PASSWORD" == "pgbouncer_auth_secret_change_me" ]]; then
    echo "WARNING: PGBOUNCER_AUTH_PASSWORD unset/default — falling back to ADMIN password (insecure; rotate via openssl rand -hex 16)" >&2
    PGBOUNCER_AUTH_PASSWORD="$PGBOUNCER_ADMIN_PASSWORD"
fi

# --- 1. ensure vds-postgres is running ----------------------------------------
if ! docker ps --format '{{.Names}}' | grep -q '^vds-postgres$'; then
    echo "ERROR: vds-postgres container is not running. Start it first:" >&2
    echo "  docker compose -f docker/docker-compose.infra.yml --profile infra up -d postgres" >&2
    exit 3
fi

# --- 2. create the 3 PgBouncer-level users (idempotent, no DO block) ----------
# psql `:'pw'` substitution works at the top SQL level. Inside `$$ ... $$` DO
# blocks it does NOT fire (the dollar-quoted body is opaque to the psql lexer).
# So we keep CREATE/ALTER outside any DO block: \gexec runs the previous
# query's output as a new query, conditionally firing CREATE USER only when
# the role is absent. Every run also re-fires ALTER USER to keep passwords
# current with whatever ~/.vds/.env now contains (rotation-friendly).
echo "[1/3] Creating PgBouncer roles in vds-postgres (idempotent, per-role passwords)..."
docker exec -i vds-postgres \
    psql -U postgres -v ON_ERROR_STOP=1 \
         -v pw_admin="$PGBOUNCER_ADMIN_PASSWORD" \
         -v pw_stats="$PGBOUNCER_STATS_PASSWORD" \
         -v pw_auth="$PGBOUNCER_AUTH_PASSWORD" <<'SQL'
\set QUIET on

-- pgbouncer_admin: create if absent, then sync password
SELECT format('CREATE USER pgbouncer_admin WITH PASSWORD %L', :'pw_admin')
    WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pgbouncer_admin')
\gexec
ALTER USER pgbouncer_admin WITH PASSWORD :'pw_admin';

-- pgbouncer_stats: create if absent, then sync password + grant pg_read_all_settings
SELECT format('CREATE USER pgbouncer_stats WITH PASSWORD %L', :'pw_stats')
    WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pgbouncer_stats')
\gexec
ALTER USER pgbouncer_stats WITH PASSWORD :'pw_stats';
GRANT pg_read_all_settings TO pgbouncer_stats;

-- pgbouncer_auth: create if absent, then sync password
-- (used as auth_user for SCRAM auth_query against pg_shadow)
SELECT format('CREATE USER pgbouncer_auth WITH PASSWORD %L', :'pw_auth')
    WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pgbouncer_auth')
\gexec
ALTER USER pgbouncer_auth WITH PASSWORD :'pw_auth';

\set QUIET off
SELECT rolname FROM pg_roles WHERE rolname LIKE 'pgbouncer_%' ORDER BY rolname;
SQL

# --- 3. generate userlist.txt from pg_shadow ----------------------------------
echo "[2/3] Generating userlist.txt from pg_shadow..."
docker exec vds-postgres psql -U postgres -t -A -c "
    SELECT '\"' || usename || '\" \"' || passwd || '\"'
    FROM pg_shadow
    WHERE usename IN ('postgres','pgbouncer_admin','pgbouncer_stats','pgbouncer_auth')
      AND passwd IS NOT NULL
    ORDER BY usename
" > "$USERLIST_PATH"

LINE_COUNT="$(wc -l < "$USERLIST_PATH")"
if [[ "$LINE_COUNT" -lt 4 ]]; then
    echo "ERROR: userlist.txt has only $LINE_COUNT lines (expected ≥4 — postgres + 3 pgbouncer users)" >&2
    echo "Inspect: cat $USERLIST_PATH" >&2
    echo "Probable cause: F18-class regression. The 3 pgbouncer_* roles must exist in pg_shadow before this query runs." >&2
    exit 4
fi

echo "[3/3] userlist.txt generated: $LINE_COUNT entries at $USERLIST_PATH"

# --- 4. mark file as locally-skipped so future updates stay out of git --------
if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$REPO_ROOT" update-index --skip-worktree \
        docker/infrastructure/pgbouncer/userlist.txt 2>/dev/null || true
    echo "      (marked file as skip-worktree; future password rotations stay out of git)"
fi

echo
echo "Done. If vds-pgbouncer is already running, reload userlist:"
echo "  docker exec -e PGPASSWORD=\"\$PGBOUNCER_ADMIN_PASSWORD\" vds-pgbouncer \\"
echo "      psql -h 127.0.0.1 -p 6432 -U pgbouncer_admin -d pgbouncer -c 'RELOAD;'"
echo
echo "Otherwise bring up vds-pgbouncer for the first time:"
echo "  docker compose -f docker/docker-compose.infra.yml --profile infra up -d vds-pgbouncer"
echo
echo "Verify health (note: PgBouncer listens on 6432 inside the container in v2.15.5+):"
echo "  docker exec -e PGPASSWORD=\"\$PGBOUNCER_ADMIN_PASSWORD\" vds-pgbouncer \\"
echo "      psql -h 127.0.0.1 -p 6432 -U pgbouncer_admin -d pgbouncer -tAc 'SHOW VERSION;'"
