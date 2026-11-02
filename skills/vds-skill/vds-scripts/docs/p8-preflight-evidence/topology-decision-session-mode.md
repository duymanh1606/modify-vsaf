# P8 Topology Decision — Session-Mode Uniform (TSK-8.0.4 / Wave 1 Addendum)

**Date**: 2026-04-27
**Purpose**: Document the topology decision after Wave 1 pre-flight surfaced a NEW HIGH BLOCKER (audit_orchestrator runtime session-scoped advisory locks) and the team's preference for "consistent setup across ecosystem".

## Resolution

**Chosen topology**: PgBouncer session-mode global default + per-database stanzas with `connect_query`.

This supersedes the Options A/B/C analysis at the bottom of `alembic-and-runtime-advisory-locks.md`. None of those options were chosen — instead, a 4th option emerged from follow-up research: **session-mode-uniform** is the simplest topology that satisfies every hard constraint with zero exceptions and zero service-code changes.

## Why session mode

Session mode is the canonical answer to all 4 of VDS's hard constraints:

| Constraint | Session-mode behavior |
|---|---|
| DBOS LISTEN/NOTIFY (scheduler event bus) | ✅ Works — session held per-client; LISTEN survives `COMMIT` |
| audit_orchestrator session-scoped advisory locks | ✅ Works — `pg_try_advisory_lock` + multi-transaction span supported |
| asyncpg `statement_cache_size=512` | ✅ Works — full cache benefit; same as direct DSN |
| alembic `pg_try_advisory_xact_lock` | ✅ Works — tx-scoped is a strict subset of what session mode permits |

Plus all the secondary tx-mode foot-guns evaporate: WITH HOLD cursors, server-side cursors, temp tables, `application_name` visibility, query cancellation race, blanket `SET` rules — all just work.

## What we forfeit by NOT using transaction mode

- **Multiplexing**: session mode is 1:1 client:backend. Transaction mode would let ~20 clients share a single backend across transactions — a 5-20× client fan-out per backend.
- **Lower max_connections budget**: tx-mode could justify dropping `max_connections` from 500 to ~150-200 (multiplexing absorbs the difference). Session mode keeps it at 500.

These costs are acceptable at VDS scale (5 services × in-app pool ~30 = ~150 sustained backends; well within 500 with ~70% headroom).

## Future R12 escalation path

When measurement shows benefit, *individual stanzas* can be promoted to `pool_mode=transaction` via per-database override (one config-line change per stanza). Trigger condition: `SHOW POOLS` shows sustained `cl_waiting>0` on memory or progress stanzas after 90 days of production observation. Audit + sched stanzas remain session-mode permanently per their session-scoped state requirements.

This converts the "should we use transaction mode?" question from an architecture decision (made in spec, hard to reverse) into an operational one (made post-deploy with measurement, reversible per-stanza).

## What changed in v2.15.3 vs v2.15.2

| Change | Impact |
|---|---|
| Pool mode `transaction` → `session` | Eliminates 4 tx-mode hard constraints; 6 secondary caveats irrelevant |
| Dropped `_DIRECT_DSN` parallel env vars | Single `VDS_<SVC>_DSN` per service; no parallel scaffolding |
| `max_connections` retune 500→200 deleted | Stays at 500; 70% headroom in v2.15.3 |
| `resolve_database_url(direct: bool = False)` flag | Not added; existing helper API works unchanged |
| DBOS dual-pool config | Not added; existing `system_database_url`-only config works unchanged |
| WP-8.3 (alembic-migrate → DIRECT_DSN) | Deleted; alembic routes through pooler same as services |
| WP-8.5 (max_connections retune) | Deleted |
| Multi-skill refactor | 5 mandatory skill bumps → 4 (progress-report no longer needs env-var change) |
| Rollback ordering | Simplified — no Postgres restart required |

## References

- Spec: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-13 v2.15.3
- Predecessor evidence: `dbos-listen-notify.md`, `alembic-and-runtime-advisory-locks.md`, `pgvector-set-local-audit.md`
- Research transcript IDs: a0182d2bbf9cec6df (initial), af7c71a11326c0d03 (deep), a0e3d69364a42cdf6 (implementation-ready), ac8dd55aea05c00e1 (consistent-topology re-research)
- Authoritative sources: pgbouncer.org/config.html, pgbouncer.org/features.html, pgbouncer.org/faq.html, jpcamara.com/2023/04/12/pgbouncer-is-useful.html
