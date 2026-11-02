<!-- diátaxis: reference -->
# Backup & Restore

## What Gets Backed Up

| Store | Criticality | Backup Method | Recovery Point |
|-------|-------------|---------------|----------------|
| **PostgreSQL** | **CRITICAL** | `pg_dump --schema=<s>` per schema, custom format | Per-backup |
| **Redis** | Medium | `BGSAVE` → RDB file | Point-in-time at backup |
| **Qdrant** | Medium | Snapshot API (`POST /snapshots`) | Point-in-time at backup |
| **Logs** | Low | Rotated (10MB × 3 per container) | Ephemeral |
| **Celery** | Low | Re-enqueued from scheduler | Ephemeral |

## Backup

```bash
# Full backup (PostgreSQL + Redis + Qdrant)
bash scripts/backup.sh

# Single schema only
bash scripts/backup.sh --schema memory

# Skip Redis/Qdrant (DB-only)
bash scripts/backup.sh --no-redis --no-qdrant
```

Backups land in `docker/backups/<YYYY-MM-DDTHHMMSS>/` with:
- `audit_state.dump`, `memory.dump`, `sched.dump`, `progress.dump`, `dbos.dump`
- `schema_ddl.sql` (DDL-only, no data — for DR schema reconstruction)
- `redis-dump.rdb`
- `manifest.txt`

Retention: keep last 7 daily; script warns at > 14.

## Restore

### PostgreSQL — Full Schema Restore

```bash
# 1. Stop dependent services
docker compose -p vds-platform --profile full stop

# 2. Restore a single schema (example: memory)
BACKUP_DIR=docker/backups/<timestamp>
docker exec -i vds-postgres pg_restore -U postgres -d vds_platform \
  --schema=memory --clean --if-exists --no-owner --no-acl \
  < "$BACKUP_DIR/memory.dump"

# 3. Restore all schemas
for f in "$BACKUP_DIR"/*.dump; do
  schema=$(basename "$f" .dump)
  docker exec -i vds-postgres pg_restore -U postgres -d vds_platform \
    --schema="$schema" --clean --if-exists --no-owner --no-acl < "$f"
done

# 4. Run alembic to ensure version stamps match
# (entrypoint auto-migrates on restart, or run explicitly)
docker compose -p vds-platform \
  -f docker/docker-compose.infra.yml \
  -f docker/docker-compose.services.yml \
  -f docker/docker-compose.cli.yml \
  --profile memory run --rm --no-deps memory-api \
  /opt/venv/bin/alembic -c /app/memory_orchestrator/alembic.ini upgrade head

# 5. Restart services
docker compose -p vds-platform --profile memory --profile scheduler up -d
```

### PostgreSQL — Point-in-Time Recovery (PITR)

Advanced: `scheduler_orchestrator/scripts/dr/pitr-drill.sh` for WAL-based recovery.
See that script for detailed instructions.

### Redis

```bash
# 1. Stop memory-worker (Celery)
docker compose -p vds-platform stop memory-worker

# 2. Copy RDB into Redis data volume
docker cp docker/backups/<timestamp>/redis-dump.rdb vds-redis:/data/dump.rdb
docker exec vds-redis redis-cli SHUTDOWN NOSAVE

# 3. Restart Redis (reads dump.rdb on start)
docker compose -p vds-platform up -d redis
docker compose -p vds-platform up -d memory-worker
```

### Qdrant

Qdrant snapshots are stored inside the Qdrant storage directory. Recovery:

```bash
# 1. List snapshots
curl http://localhost:6335/snapshots

# 2. Restore from snapshot (via Qdrant UI or API)
# See: https://qdrant.tech/documentation/concepts/snapshots/
```

## Machine Migration

To move the entire VDS stack to new hardware:

```bash
# On OLD machine:
bash scripts/backup.sh
tar czf vds-backup-$(date '+%Y%m%d').tar.gz docker/backups/<latest>/

# Copy the tarball to NEW machine:
scp vds-backup-*.tar.gz user@new-host:/tmp/

# On NEW machine:
cd /path/to/vds-scripts
tar xzf /tmp/vds-backup-*.tar.gz
cp docker/infrastructure/.env.template ~/.vds/.env
# Edit ~/.vds/.env with correct credentials
bash scripts/deploy-bootstrap.sh

# Restore data:
# Stop services first, then follow the PostgreSQL restore steps above
# for each .dump file in the extracted backup directory.
```

## Scheduling

For automated daily backups, add a cron job or use the `/schedule` command:

```bash
# Daily at 2:17 AM (off-minute to avoid fleet-wide stampede)
17 2 * * * cd /path/to/vds-scripts && bash scripts/backup.sh >> docker/backups/backup.log 2>&1
```
