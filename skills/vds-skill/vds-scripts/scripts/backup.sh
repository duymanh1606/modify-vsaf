#!/usr/bin/env bash
# =============================================================================
# VDS Backup Script
# =============================================================================
# Phase: ecosystem-infrastructure-evolution v2.16.0
#
# Dumps all VDS schemas + Redis RDB + Qdrant snapshot to docker/backups/.
# Timestamped directories prevent overwrites.
#
# Usage:
#   bash scripts/backup.sh                    # full backup
#   bash scripts/backup.sh --schema memory    # single schema only
#   bash scripts/backup.sh --no-redis         # skip Redis
#   bash scripts/backup.sh --no-qdrant        # skip Qdrant
#
# Restore: see docs/agents/reference/backup-restore.md
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[BACKUP]${NC} $(date '+%H:%M:%S') $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$REPO_ROOT/docker/backups"
TIMESTAMP=$(date '+%Y-%m-%dT%H%M%S')
RUN_DIR="$BACKUP_DIR/$TIMESTAMP"
mkdir -p "$RUN_DIR"

SCHEMA_FILTER=""
for arg in "$@"; do
  case "$arg" in
    --schema) SCHEMA_FILTER="next" ;;
    --no-redis) SKIP_REDIS=true ;;
    --no-qdrant) SKIP_QDRANT=true ;;
    *)
      if [ "$SCHEMA_FILTER" = "next" ]; then
        SCHEMA_FILTER="$arg"
      fi
      ;;
  esac
done
SKIP_REDIS=${SKIP_REDIS:-false}
SKIP_QDRANT=${SKIP_QDRANT:-false}

log "VDS Backup — $TIMESTAMP → $RUN_DIR"

# ── Verify containers are running ─────────────────────────────────────────────
CONTAINER="vds-postgres"
docker ps --format '{{.Names}}' | grep -q "$CONTAINER" || {
  warn "$CONTAINER not running — schema backups skipped"
  SKIP_DB=true
}
SKIP_DB=${SKIP_DB:-false}

# ── Per-schema pg_dump ───────────────────────────────────────────────────────
if ! $SKIP_DB; then
  SCHEMAS=("audit_state" "memory" "sched" "progress" "dbos")
  for schema in "${SCHEMAS[@]}"; do
    if [ -n "$SCHEMA_FILTER" ] && [ "$SCHEMA_FILTER" != "--schema" ] && [ "$schema" != "${2:-}" ]; then
      continue
    fi
    output="$RUN_DIR/${schema}.dump"
    log "  Dumping $schema..."
    docker exec "$CONTAINER" pg_dump -U postgres -d vds_platform \
      --schema="$schema" --format=custom --no-owner --no-acl \
      -f "/tmp/${schema}.dump" 2>&1 | tail -1
    docker cp "$CONTAINER:/tmp/${schema}.dump" "$output" 2>/dev/null
    docker exec "$CONTAINER" rm -f "/tmp/${schema}.dump"
    size=$(du -h "$output" | cut -f1)
    log "    $schema → $output ($size)"
  done
  # Full DB dump (roles + schema definitions without data, for DR)
  log "  Dumping schema-only (DDL)..."
  docker exec "$CONTAINER" pg_dump -U postgres -d vds_platform \
    --schema-only --no-owner --no-acl \
    -f "/tmp/schema_ddl.sql"
  docker cp "$CONTAINER:/tmp/schema_ddl.sql" "$RUN_DIR/schema_ddl.sql"
  docker exec "$CONTAINER" rm -f "/tmp/schema_ddl.sql"
  log "    DDL → $RUN_DIR/schema_ddl.sql"
fi

# ── Redis RDB ─────────────────────────────────────────────────────────────────
if ! $SKIP_REDIS; then
  log "Triggering Redis BGSAVE..."
  docker exec vds-redis redis-cli BGSAVE 2>/dev/null || warn "Redis BGSAVE failed"
  if docker ps --format '{{.Names}}' | grep -q "vds-redis"; then
    docker cp "vds-redis:/data/dump.rdb" "$RUN_DIR/redis-dump.rdb" 2>/dev/null || warn "Redis RDB copy failed"
    log "  Redis → $RUN_DIR/redis-dump.rdb"
  fi
fi

# ── Qdrant snapshot ───────────────────────────────────────────────────────────
if ! $SKIP_QDRANT; then
  if docker ps --format '{{.Names}}' | grep -q "vds-qdrant"; then
    log "Creating Qdrant snapshot..."
    curl -s -X POST "http://localhost:6335/snapshots" \
      -H "Content-Type: application/json" \
      -d '{}' > /dev/null 2>&1 || warn "Qdrant snapshot API failed"
    log "  Qdrant snapshot triggered (check Qdrant UI for status)"
  fi
fi

# ── Manifest ──────────────────────────────────────────────────────────────────
cat > "$RUN_DIR/manifest.txt" <<EOF
VDS Backup — $TIMESTAMP
Host: $(hostname)
Schemas: ${SCHEMAS[*]}
Redis: $($SKIP_REDIS && echo "skipped" || echo "included")
Qdrant: $($SKIP_QDRANT && echo "skipped" || echo "included")
EOF

# ── Retention ─────────────────────────────────────────────────────────────────
# Keep last 7 daily backups; warn if > 14 exist
BACKUP_COUNT=$(ls -1d "$BACKUP_DIR"/*/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -gt 14 ]; then
  warn "$BACKUP_COUNT backups exist — consider pruning with: rm -rf $BACKUP_DIR/<old-timestamp>"
fi

log "Backup complete — $RUN_DIR"
echo ""
