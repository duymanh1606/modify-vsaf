<!-- diátaxis: how-to -->

# How to apply the Phase 3 alembic migration

> Operator runbook to bring the live `sched.ecosystem_report_runs` schema into
> alignment with the Phase 3 collector code merged at `412b067b`.

**Time budget**: ≤ 10 minutes. **Risk**: low (additive migration; reversible).

## Why

Phase 3 of the ecosystem-daily-report (`edr-phase3/intelligent-watchdog`,
merged at `412b067bcbb44c466cf62f5f62a11d0888090848` on 2026-04-30) added
five new collectors and a Slack delivery step. Their results are persisted
to **new columns** on `sched.ecosystem_report_runs`:

- `llm_summary` (JSONB) — LLM provider/model token totals + USD cost
- `dora_summary` (JSONB) — deploy frequency, lead time, CFR, time-to-restore
- `trend_summary` (JSONB) — z-scores + sparklines + trend directions
- `security_summary` (JSONB) — placeholder for SecurityAdvisoryCollector
- `slack_delivered` (boolean), `slack_delivered_at` (timestamptz)

Plus a new table `sched.ecosystem_report_archive` with a GIN-indexed
`full_report` JSONB column for historical search.

The migration file shipped at `412b067b` (revision `b2c3d4e5f8a9`,
down-revision `a1b2c3d4e5f8`) but the live database still points at
the Phase 2 head. **Until you run `alembic upgrade head`**, the cron
that fires at 06:00 UTC will hand the SQLAlchemy model rows containing
the Phase 3 columns to a database that does not have those columns,
which leads to either persistence failure or silent loss of Phase 3 data
depending on driver behavior.

## When

After the Phase 3 merge has landed on master (verify with
`git log --oneline 412b067b -1`) and **before** you rely on persisted
Phase 3 reports — i.e. before the next 06:00 UTC cron fire, or before
the next manual `vds-cli scheduler schedules trigger-now ecosystem-daily-report`.

## Prerequisites

- `~/.vds/.env` populated (Postgres DSN, `VDS_SCHEDULER_ENABLED=true`).
- Working tree at master `412b067b` or later.
- Postgres 16 healthy (`docker ps | grep postgres` shows the
  `vds-postgres` container with status `healthy`).

## Steps

### 1. Apply the migration

```bash
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh run --project scheduler_orchestrator alembic upgrade head
```

Expected output:

```
INFO  [alembic.runtime.migration] Running upgrade a1b2c3d4e5f8 -> b2c3d4e5f8a9, add_phase3_report_columns
```

### 2. Verify the scheduler service is running

```bash
docker ps | grep scheduler                      # vds-scheduler container healthy
vds-cli scheduler schedules show ecosystem-daily-report
```

The schedule should be listed with status `active` (not `paused`) and a
`next_run` timestamp set to the next 06:00 UTC. If `Status: paused`, run
`vds-cli scheduler schedules resume ecosystem-daily-report`.

### 3. Trigger one workflow run for verification

Don't wait for 06:00 UTC; force one fire so you can confirm the new
schema is being written through:

```bash
vds-cli scheduler schedules trigger-now ecosystem-daily-report
```

Then check the workflow result:

```bash
vds-cli scheduler workflows list --status SUCCESS --limit 1
```

A new `reports/ecosystem/<today>-ecosystem-report.md` file should also
appear in the worktree.

### 4. Confirm the new row populates Phase 3 columns

```bash
vds-cli ecosystem report history --days 1
```

The latest row should show non-NULL `dora_summary`, `trend_summary`,
`llm_summary`, `slack_delivered`, `slack_delivered_at`. NULL or
`[unavailable]` payloads are *also* acceptable — what matters is that
the cron successfully wrote through the migrated schema rather than
crashing on `column does not exist`.

> Caveat: `llm_summary` will report `[unavailable]` until the Phase 4
> producer-wiring task lands (see the spec's "Phase 4 Followup — JSONL
> Producer Wiring" note). This is graceful degradation per AC-P3.9, not
> a regression.

## Verification

You will know the migration worked when:

- `alembic current` shows `b2c3d4e5f8a9 (head)`.
- `psql ... -c "\d sched.ecosystem_report_runs"` lists the six new
  columns above.
- `psql ... -c "\d sched.ecosystem_report_archive"` shows the new
  archive table with a GIN index on `full_report`.
- A fresh row from `vds-cli ecosystem report history --days 1` is
  written without error after step 3.

## Rollback

If you need to revert (for example, a downstream consumer is not yet
ready for the new columns):

```bash
# 1. Pause the schedule so the next cron does not crash on the
#    pre-Phase-3 schema.
vds-cli scheduler schedules pause ecosystem-daily-report

# 2. Downgrade.
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh run --project scheduler_orchestrator alembic downgrade -1
```

`alembic downgrade -1` reverts to `a1b2c3d4e5f8` (Phase 2 head), drops
the six Phase 3 columns and the `ecosystem_report_archive` table.
**Do not resume the schedule** until either you re-apply the migration
or you check out a pre-`412b067b` master tip whose model code matches
the Phase 2 schema.

## See also

- Spec post-merge runbook: `.gpt-5.4/specs/ecosystem-daily-report/tasks.md`
  → "Post-Merge Operator Runbook"
- DORA bootstrap criterion: `.gpt-5.4/specs/ecosystem-daily-report/design.md`
  → "Bootstrap criterion (verdict locked 2026-04-30, Lane Alpha)"
- Existing daily-report runbook: `docs/agents/how-to/run-ecosystem-daily-report.md`
