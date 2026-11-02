#!/usr/bin/env bash
# =============================================================================
# VDS Deploy-from-Scratch Bootstrap
# =============================================================================
# Phase: ecosystem-infrastructure-evolution v2.16.0
#
# Single-command deploy for a fresh machine. Handles:
#   1. Prerequisite checks (docker, compose plugin)
#   2. ~/.vds/.env creation from template (interactive: prompts for secrets)
#   3. docker/.env → ~/.vds/.env symlink
#   4. PgBouncer userlist.txt generation
#   5. Image builds (all orchestrators)
#   6. Infra bring-up (postgres, redis, qdrant, pgbouncer)
#   7. Wait for health
#   8. Explicit alembic migrations (audit, progress — memory + scheduler auto-migrate)
#   9. Service bring-up
#  10. Smoke test
#
# Usage:
#   bash scripts/deploy-bootstrap.sh              # guided (prompts for secrets)
#   bash scripts/deploy-bootstrap.sh --non-interactive  # CI mode (pre-existing .env)
#
# Environment:
#   VDS_DEPLOY_SKIP_BUILD=1     skip image builds
#   VDS_DEPLOY_SKIP_MIGRATE=1   skip explicit migrations
#   VDS_DEPLOY_SKIP_SMOKE=1     skip smoke test
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[DEPLOY]${NC} $(date '+%H:%M:%S') $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"
INTERACTIVE=true
[[ "${1:-}" == "--non-interactive" ]] && INTERACTIVE=false

log "VDS Deploy Bootstrap — $(date '+%Y-%m-%d')"
log "Repo root: $REPO_ROOT"

# ── 1. Prerequisites ─────────────────────────────────────────────────────────
log "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || err "docker not found — install Docker first"
docker compose version >/dev/null 2>&1 || err "docker compose plugin not found"
docker info >/dev/null 2>&1 || err "docker daemon not running — start Docker first"

# ── 2. ~/.vds/.env ────────────────────────────────────────────────────────────
log "Setting up ~/.vds/.env..."
if [ ! -f "$HOME/.vds/.env" ]; then
  if [ -f "$DOCKER_DIR/infrastructure/.env.template" ]; then
    cp "$DOCKER_DIR/infrastructure/.env.template" "$HOME/.vds/.env"
    chmod 600 "$HOME/.vds/.env"
    log "Created ~/.vds/.env from template"
    if $INTERACTIVE; then
      echo ""
      warn "Default secrets detected in ~/.vds/.env."
      warn "Run: bash scripts/rotate-secrets.sh   (to regenerate all credentials)"
      echo ""
    fi
  else
    err "No .env.template found at $DOCKER_DIR/infrastructure/.env.template"
  fi
else
  log "~/.vds/.env already exists — skipping"
fi

# ── 3. docker/.env symlink ────────────────────────────────────────────────────
log "Setting up docker/.env → ~/.vds/.env symlink..."
if [ ! -L "$DOCKER_DIR/.env" ] || [ "$(readlink "$DOCKER_DIR/.env")" != "$HOME/.vds/.env" ]; then
  rm -f "$DOCKER_DIR/.env"
  ln -sf "$HOME/.vds/.env" "$DOCKER_DIR/.env"
  log "Symlinked docker/.env → ~/.vds/.env"
else
  log "docker/.env symlink already correct"
fi

# Source env for compose variable interpolation
set -a; source "$HOME/.vds/.env"; set +a

# ── 4. PgBouncer userlist ─────────────────────────────────────────────────────
log "Initializing PgBouncer userlist.txt..."
USERLIST="$DOCKER_DIR/infrastructure/pgbouncer/userlist.txt"
if [ ! -f "$USERLIST" ] || [ "$(wc -l < "$USERLIST")" -lt 3 ]; then
  bash "$SCRIPT_DIR/init-pgbouncer-userlist.sh" 2>/dev/null || {
    warn "init-pgbouncer-userlist.sh failed — generating minimal userlist"
    cat > "$USERLIST" <<EOF
"pgbouncer_admin" "${PGBOUNCER_ADMIN_PASSWORD:-pgbouncer_admin_secret_change_me}"
"pgbouncer_stats" "${PGBOUNCER_STATS_PASSWORD:-pgbouncer_stats_secret_change_me}"
"pgbouncer_auth"  "${PGBOUNCER_AUTH_PASSWORD:-pgbouncer_auth_secret_change_me}"
"postgres"        "${VDS_POSTGRES_PASSWORD:-vds_postgres_secret}"
EOF
  }
  log "userlist.txt created"
else
  log "userlist.txt already populated — skipping"
fi

# ── 5. Build images ───────────────────────────────────────────────────────────
if [ "${VDS_DEPLOY_SKIP_BUILD:-0}" = "1" ]; then
  log "Skipping builds (VDS_DEPLOY_SKIP_BUILD=1)"
else
  log "Building orchestrator images..."
  docker compose -p vds-platform \
    -f "$DOCKER_DIR/docker-compose.infra.yml" \
    -f "$DOCKER_DIR/docker-compose.services.yml" \
    -f "$DOCKER_DIR/docker-compose.cli.yml" \
    --profile full build --parallel 2>&1 | tail -3
  log "Builds complete"
fi

# ── 6. Infra bring-up ─────────────────────────────────────────────────────────
log "Starting shared infrastructure..."
docker compose -p vds-platform \
  -f "$DOCKER_DIR/docker-compose.infra.yml" \
  up -d --wait 2>&1 | tail -5

# Verify
for svc in vds-postgres vds-redis vds-qdrant vds-pgbouncer; do
  if docker ps --format '{{.Names}}' | grep -q "$svc"; then
    log "  $svc — RUNNING"
  else
    err "  $svc — NOT RUNNING — check docker logs $svc"
  fi
done

# ── 7. Health wait ────────────────────────────────────────────────────────────
log "Waiting for all infra services healthy..."
ATTEMPTS=0; MAX_ATTEMPTS=60
while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
  UNHEALTHY=$(docker ps --filter "name=vds-" --format '{{.Names}} {{.Status}}' | grep -v "healthy" || true)
  if [ -z "$UNHEALTHY" ]; then
    log "All services healthy"
    break
  fi
  ATTEMPTS=$((ATTEMPTS + 1))
  sleep 2
done
if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
  err "Services did not become healthy within 120s"
fi

# ── 8. Explicit alembic migrations ────────────────────────────────────────────
if [ "${VDS_DEPLOY_SKIP_MIGRATE:-0}" = "1" ]; then
  log "Skipping explicit migrations (VDS_DEPLOY_SKIP_MIGRATE=1)"
else
  log "Running explicit alembic migrations (audit, progress)..."
  for orch in audit progress; do
    svc="$orch-orchestrator"
    ini="/app/${orch}_orchestrator/alembic.ini"
    log "  Migrating $orch..."
    docker compose -p vds-platform \
      -f "$DOCKER_DIR/docker-compose.infra.yml" \
      -f "$DOCKER_DIR/docker-compose.services.yml" \
      -f "$DOCKER_DIR/docker-compose.cli.yml" \
      --profile "$orch" \
      run --rm --no-deps --entrypoint /opt/venv/bin/alembic "$svc" \
      -c "$ini" upgrade head 2>&1 | tail -2 || warn "  $orch migration failed — may already be up-to-date"
  done
  log "Explicit migrations complete"
fi
# Memory + Scheduler auto-migrate via their entrypoint.sh — no action needed here

# ── 9. Service bring-up ───────────────────────────────────────────────────────
log "Starting platform services..."
docker compose -p vds-platform \
  -f "$DOCKER_DIR/docker-compose.infra.yml" \
  -f "$DOCKER_DIR/docker-compose.services.yml" \
  -f "$DOCKER_DIR/docker-compose.cli.yml" \
  --profile memory --profile scheduler --profile multi-agent \
  up -d --wait 2>&1 | tail -5

# ── 10. Smoke test ────────────────────────────────────────────────────────────
if [ "${VDS_DEPLOY_SKIP_SMOKE:-0}" = "1" ]; then
  log "Skipping smoke test (VDS_DEPLOY_SKIP_SMOKE=1)"
else
  log "Smoke testing endpoints..."
  for endpoint in \
    "http://localhost:8000/health memory-api" \
    "http://localhost:8005/health scheduler" \
    "http://localhost:8003/health multi-agent"; do
    url="${endpoint% *}"; name="${endpoint##* }"
    if curl -sf "$url" >/dev/null 2>&1; then
      log "  $name — OK ($url)"
    else
      warn "  $name — UNREACHABLE ($url)"
    fi
  done
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
log "Deploy complete."
log "  Services:  memory-api (8000) | scheduler (8005) | multi-agent (8003)"
log "  Infra:     postgres (5432) | redis (6379) | qdrant (6335) | pgbouncer (6432)"
log "  Logs:      docker compose -p vds-platform logs -f <service>"
log "  Stop:      docker compose -p vds-platform --profile full down"
echo ""
