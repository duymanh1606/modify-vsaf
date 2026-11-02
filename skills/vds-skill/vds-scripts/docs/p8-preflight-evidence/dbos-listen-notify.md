# DBOS LISTEN/NOTIFY Pre-flight Evidence (TSK-8.0.1)

**Date**: 2026-04-27
**Purpose**: Verify that `scheduler_orchestrator` (DBOS) LISTEN/NOTIFY usage is preserved under the v2.15.3 PgBouncer topology.

## Verdict

✅ **Scheduler routes through PgBouncer in session mode; LISTEN/NOTIFY works natively; no per-service exception needed.**

Session-mode pooling preserves LISTEN/NOTIFY across the COMMIT boundary because it is 1:1 client:backend — the backend stays held for the lifetime of the client's connection. Scheduler routes via `VDS_SCHEDULER_DATABASE_URL=postgresql://postgres:.../vds-pgbouncer:6432/vds_sched` — single uniform DSN, same as every other service.

## Evidence

### DBOS dependency pin

`scheduler_orchestrator/pyproject.toml`: `dbos>=2.19.0,<3` (verified via `uv.lock`).

### Active LISTEN/NOTIFY usage in scheduler_orchestrator

DBOS isn't *just configured* with `use_listen_notify=True` (the default) — the code actively uses Postgres LISTEN/NOTIFY for the event bus + chain triggers + dispatcher loop. Not theoretical, observed:

| File | Line | Usage |
|---|---|---|
| `src/vds_scheduler_orchestrator/app.py` | 313 | `WS /api/v1/events/stream — live push via Postgres LISTEN/NOTIFY` |
| `src/vds_scheduler_orchestrator/cli.py` | 779 | `pushes events in real time via Postgres LISTEN/NOTIFY. Replaces polling` |
| `chains/triggers.py` | 395, 546, 554 | Dispatcher LISTEN loop is the core trigger mechanism |
| `db/models.py` | 93 | `fires pg_notify('event_bus', event_id::text). The dispatcher's LISTEN loop` |
| `events/bus.py` | 6 | `TSK-3.2: subscribe() — LISTEN loop and handler registry` |
| `events/dispatcher.py` | (15 matches) | LISTEN loop implementation |

### DBOSConfig snippet (app.py ~135-145)

```python
dbos_cfg: DBOSConfig = {
    "name": "vds-scheduler-orchestrator",
    # DBOS uses this as both system and application database.
    # system_database_url → where dbos.* system tables live.
    "system_database_url": cfg.vds_scheduler_database_url,
    # application_version from DBOS_APP_VERSION env var (deploy-time) — ADR-7
    "application_version": cfg.dbos_app_version,
}
```

**Note**: the config sets *only* `system_database_url`; `application_database_url` is left unset and inherits the system URL per DBOS defaults. Spec `design.md §9.5` is consistent with this minimal-config shape.

## Conclusion

`scheduler_orchestrator` connects through PgBouncer at `vds-pgbouncer:6432/vds_sched` in **session mode**. LISTEN/NOTIFY works correctly because session-mode pooling holds the backend per-client for the lifetime of the connection — no premature COMMIT-time release. Single uniform DSN; no per-service exception list. See `topology-decision-session-mode.md` for the full v2.15.3 resolution rationale.

## References

- DBOS docs: https://docs.dbos.dev/python/tutorials/database-connection (states "session mode, not in transaction mode")
- PgBouncer issue: https://github.com/pgbouncer/pgbouncer/issues/655 (LISTEN in tx mode — open)
- Spec: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-13 topology table
