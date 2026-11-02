# PgBouncer `search_path` Empirical Probe (post-deploy)

**Date**: 2026-04-30
**Probe context**: live `vds-platform` deployment, master @ `a9d342b5`, PgBouncer 1.25.1, postgres 18 (pgvector/pgvector:0.8.2-pg18)
**Spec reference**: ecosystem-infrastructure-evolution FR-15, ADR-INF-13

## Why this document exists

Spec FR-15 prescribes per-stanza `connect_query='SET search_path TO <schema>, public'` to pin the search_path "at backend startup time." The FR-9 `verify-infra-topology` gate verifies *declarations* (stanzas exist, pool_mode=session, etc.) but explicitly defers runtime correctness: "this verifies declarations only; per-stanza connect_query search_path correctness needs a per-stanza psql probe." This document is that per-stanza probe.

## Method

Connections were issued through each of the four PgBouncer stanzas (`vds_audit`, `vds_memory`, `vds_progress`, `vds_sched`) with the auth_query-resolved credentials in `~/.vds/.env`. For each stanza:

1. Force a fresh backend via `RECONNECT <stanza>` issued to the pgbouncer admin DB.
2. Open a new client session through the stanza.
3. Capture `current_database()`, `current_user`, `current_schema()`, `current_setting('search_path')`.
4. Issue a no-op `SELECT 1` and release the session.
5. Open a *second* client session against the same backend (recycled from the pool).
6. Capture the same four values.

For the `vds_memory` stanza only, additionally probe `pgvector` extension visibility: `SELECT extname FROM pg_extension WHERE extname='vector';` plus `SELECT '[1,2,3]'::vector;`.

## Per-stanza results

Each stanza was probed in two states: **fresh** (first client on a brand-new backend post-RECONNECT) and **recycled** (second client on the same backend after the first client released it).

### `vds_audit`
| state | current_database | current_user | current_schema | search_path |
|---|---|---|---|---|
| fresh | `vds_platform` | `postgres` | `audit_state` | `audit_state, public` |
| recycled | `vds_platform` | `postgres` | `public` | `"$user", public` |

### `vds_memory`
| state | current_database | current_user | current_schema | search_path |
|---|---|---|---|---|
| fresh | `vds_platform` | `postgres` | `memory` | `memory, public` |
| recycled | `vds_platform` | `postgres` | `public` | `"$user", public` |

pgvector extension probe (recycled state):
- `extname` row returned: `vector` (extension is installed in `public`).
- `'[1,2,3]'::vector` parses successfully.

The pgvector type resolves on recycled backends *only because* `public` remains in the cluster default `search_path`. If `public` were removed from defaults, `vector_l2_ops` would become invisible on recycled backends.

### `vds_progress`
| state | current_database | current_user | current_schema | search_path |
|---|---|---|---|---|
| fresh | `vds_platform` | `postgres` | `progress` | `progress, public` |
| recycled | `vds_platform` | `postgres` | `public` | `"$user", public` |

### `vds_sched`
| state | current_database | current_user | current_schema | search_path |
|---|---|---|---|---|
| fresh | `vds_platform` | `postgres` | `sched` | `sched, public` |
| recycled | `vds_platform` | `postgres` | `public` | `"$user", public` |

## Pool-mode confirmation (`SHOW POOLS`, `SHOW STATS_TOTALS`)

All four app stanzas confirmed `pool_mode=session`. Live activity at probe time:

| stanza | cl_active | sv_active | sv_idle |
|---|---|---|---|
| `vds_audit` | 0 | 0 | 1 |
| `vds_memory` | 9 | 9 | 0 |
| `vds_progress` | 0 | 0 | 1 |
| `vds_sched` | 6 | 6 | 0 |

`SHOW STATS_TOTALS` shows traffic on all four stanzas. `vds_sched` is busiest (9588 transactions); `vds_memory` second (239 transactions, 1192 queries).

## Root cause of the recycled-state regression

PgBouncer's `connect_query` runs **once per backend at backend startup**. When a client session ends, PgBouncer issues `server_reset_query` (default: `DISCARD ALL`) before returning the backend to the pool. `DISCARD ALL` resets `search_path` to the cluster default (`"$user", public`). When PgBouncer assigns that recycled backend to a new client, **it does not re-run `connect_query`** — it assumes the backend is in a clean baseline state.

The net effect: only the *first* client of each backend sees the stanza-specific `search_path`. Every subsequent client on a recycled backend inherits the cluster default until the next `RECONNECT` or backend rotation.

## Verdict

| Property | Status |
|---|---|
| Per-stanza `connect_query` syntactically applied | ✅ Yes (verified on fresh backends) |
| Per-stanza `search_path` pinning persists across session releases | ❌ No (wiped by `DISCARD ALL`) |
| pgvector visibility from `vds_memory` | ✅ Yes (incidentally — `public` in cluster default search_path) |
| `pool_mode=session` for all stanzas | ✅ Yes |

## Production blast radius

VDS application code schema-qualifies all table references (e.g. `audit_state.checkpoints`, not just `checkpoints`) per Phase 220 review. Production correctness is therefore independent of `search_path` pinning. The `connect_query` mechanism is **best-effort defense-in-depth**, not a hard guarantee.

Code paths that rely on unqualified-name resolution would be at risk on the second-or-later assignment of any backend. A grep pattern to find such risk surface:

```
rg "(?<![\w.])(checkpoints|memories|memory_fragments|knowledge_documents|workflow_state|workflows|reports|cron_schedules)(?![\w.])" \
  audit_orchestrator/ memory_orchestrator/ progress_report_orchestrator/ scheduler_orchestrator/
```

False positives are expected (string literals, comments); manual triage required.

## Recommendations

1. **Update spec FR-15 and ADR-INF-13** to describe `connect_query` as best-effort defense-in-depth, not a persistent pin. The actual contract is: "fresh backends start with the stanza search_path; recycled backends inherit cluster defaults; production correctness comes from schema-qualification."
2. **Do NOT remove `DISCARD ALL` from `server_reset_query`** — it is the standard reset-to-baseline mechanism for session-pooled backends and protects against far worse leakage (prepared statements, advisory locks, SET LOCAL residue). The bug is upstream PgBouncer's choice to skip `connect_query` on recycle, not our reset query.
3. **PgBouncer `track_extra_parameters` does not apply** because clients do not issue `SET search_path` — the pinning was supposed to happen at the pooler. Tracking client-issued SETs cannot recover values the client never set.
4. **Future R12 (per-stanza tx-mode promotion)** is unaffected by this finding — transaction mode releases backends per-transaction, so the `connect_query`-vs-recycle gap manifests at a different cadence but with the same root cause and same mitigation (schema qualification).

## Artifacts

- Probe commands and raw output: collected during W1-B research wave 2026-04-30 by Lane B teammate.
- pgbouncer.ini (probed config): `docker/infrastructure/pgbouncer/pgbouncer.ini` at master @ `a9d342b5`.
- init-schemas.sql (role-schema mapping): `docker/infrastructure/init-schemas.sql`.
