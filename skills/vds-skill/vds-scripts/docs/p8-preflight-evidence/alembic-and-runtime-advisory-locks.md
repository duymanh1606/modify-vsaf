# Alembic + Runtime Advisory-Lock Pre-flight Evidence (TSK-8.0.2)

**Date**: 2026-04-27
**Purpose**: Verify advisory-lock semantics for both alembic migrations and `audit_orchestrator` runtime code under the v2.15.3 PgBouncer topology. **Scope was broadened during pre-flight to include runtime advisory-lock usage in service code** (not in original WP-8.0.2 scope but surfaced naturally during pre-flight).

## Verdict

✅ **Both alembic's transaction-scoped locks AND audit_orchestrator's session-scoped locks are preserved natively under v2.15.3 session-mode topology — no per-service routing exceptions needed.**

## Evidence

### Alembic version pin

`uv.lock` confirms `alembic==1.18.4`.

### Advisory locks in our alembic migrations

| File | Line | Statement | Lock variant |
|---|---|---|---|
| `audit_orchestrator/alembic/versions/0001_initial_audit_state_schema.py` | 1124 | `SELECT pg_try_advisory_xact_lock(v_lock_key) INTO v_acquired;` | **transaction-scoped** |
| `audit_orchestrator/alembic/versions/0001_initial_audit_state_schema.py` | 1158 | `SELECT pg_try_advisory_xact_lock(v_lock_key) INTO v_acquired;` | **transaction-scoped** |

These are released automatically at `COMMIT`/`ROLLBACK`. Alembic 1.18.4 itself does NOT take any session-scoped locks during normal `upgrade head`.

### Advisory locks in audit_orchestrator runtime code

| File | Line | Statement | Lock variant |
|---|---|---|---|
| `audit_orchestrator/src/vds_audit_orchestrator/state/store.py` | 5265 | `SELECT pg_try_advisory_lock(hashtext(%s)) AS acquired` | **session-scoped** |
| `audit_orchestrator/src/vds_audit_orchestrator/state/store.py` | 5279 | `SELECT pg_advisory_unlock(hashtext(%s)) AS released` | **session-scoped** |

These wrap the `acquire_corpus_session_lock(...)` API at line 5285, used to coordinate corpus-refresh sessions across **multiple transactions** with a `stale_threshold_minutes=10` timeout window. The lock is held while the refresh is in flight.

The docstring at line 5229 incorrectly states "Uses non-blocking pg_try_advisory_xact_lock with retry loop" — but the actual SQL is `pg_try_advisory_lock` (without `_xact`). This is a documentation drift (orthogonal to P8 — could file a separate fix).

## v2.15.3 resolution

PgBouncer session-mode topology (per `topology-decision-session-mode.md`) preserves both alembic's transaction-scoped locks AND audit_orchestrator's session-scoped locks natively — no per-service routing exceptions needed. A single `VDS_<SVC>_DSN` per service routes through `vds-pgbouncer:6432`; the 1:1 client:backend binding holds the backend across COMMIT boundaries, so `pg_advisory_lock` / `pg_advisory_unlock` semantics survive end-to-end through the pooler.

## References

- Spec: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-13 topology table
- Topology decision: `topology-decision-session-mode.md`
- Code: `audit_orchestrator/src/vds_audit_orchestrator/state/store.py:5260-5300`
- Issue surfaced: 2026-04-27 P8 Wave 1 pre-flight; not present in earlier 4-lane validation audit (which scoped advisory-lock check to alembic migrations only).
