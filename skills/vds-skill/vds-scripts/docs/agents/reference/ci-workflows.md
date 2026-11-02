<!-- diátaxis: reference -->
# VDS CI/CD Workflows — Operational Contract

> Continuous Integration pipeline contract for WHO-project/vds-scripts.

## Overview

All CI runs on `ubuntu-latest` via GitHub Actions. Jobs are split by concern: lint/type/test gate, doc quality gate, Confluence evidence, scheduler health, and Confluence sync on push.

## Workflow Catalog

| File | Name | Trigger | Purpose |
|------|------|---------|---------|
| `lint-and-test.yml` | Lint, Type, Test & Standardize | Push | `uv sync`, `pytest`, `ruff check`, `mypy` |
| `docs-quality.yml` | Docs Quality Gate | `docs/**` PR paths | `score_all_docs()` + `validate_docs()` |
| `docs-confluence-evidence.yml` | Docs Confluence Evidence Log | Schedule | Daily snapshot of freshness + quality scores |
| `chaos-smoke.yml` | Chaos Smoke — Scheduler Orchestrator | Manual | Chaos & resilience testing, scheduler restart validation |
| `scheduler-load-smoke.yml` | Scheduler Load Smoke (1-min) | Push | 60-second `/health` smoke in stub mode |
| `confluence-sync.yml` | Confluence Sync | Push | Sync docs to Confluence on `docs/**` changes |

### Lint, Type, Test & Standardize

- **Trigger**: Every push
- **Steps**:
  1. Checkout
  2. `uv sync --all-packages`
  3. `pytest` (unit + integration)
  4. `ruff check --fix`
  5. `mypy` strict mode
- **Failure**: Blocks PR merge via branch protection

### Docs Quality Gate

- **Trigger**: PR touching `docs/**` or `vds_cli/src/vds_cli/docs_cmd.py`
- **Checks**:
  - `score_all_docs(Path('.'))` — average must be ≥ 0.6
  - `validate_docs(..., check_vi=True, check_diataxis=True, cross_repo=True, check_orchestrators=True, check_skills=True)` — zero issues
- **Failure**: Annotates PR with `::error::` markers

### Docs Confluence Evidence Log

- **Trigger**: Daily cron (UTC 06:00)
- **Output**: JSONL in `docs/.confluence-evidence/` — one line per doc with score and timestamp
- **Monitoring**: Viewed via `vds-cli docs quality-score --format json`

### Chaos Smoke

- **Trigger**: Manual (`workflow_dispatch`)
- **Scope**: Restart scheduler containers, verify DBOS re-registration, check event-bus recovery
- **Duration**: ~5 minutes per run
- **On failure**: Open incident in `scheduler_orchestrator/docs/runbooks/`

### Scheduler Load Smoke

- **Trigger**: Push
- **Scope**: FastAPI `/health` endpoint, no DB required
- **Timeout**: 60 seconds
- **On failure**: Blocks PR (treated as critical path)

### Confluence Sync

- **Trigger**: Push to `main`
- **Scope**: Syncs `docs/agents/reference/` and selected how-tos to Confluence space
- **Requires**: `CONFLUENCE_INTERNAL_TOKEN` in repository secrets
- **Dry-run**: `vds-cli docs confluence-sync --dry-run`

## Alert Matrix

| Workflow | On Failure | Owner |
|----------|-----------|-------|
| lint-and-test | PR blocked, Slack #builds | Feature author |
| docs-quality | PR annotated, merge blocked | Docs maintainer |
| docs-confluence-evidence | Incident log in `docs/.confluence-evidence/` | Ops rotation |
| chaos-smoke | Severity-1 if scheduler down > 2 min | Scheduler on-call |
| scheduler-load-smoke | PR blocked | Feature author |
| confluence-sync | Silent failure (log only) | Docs automation |

## Key Files Watched

```
docs/**                          — docs-quality, confluence-sync
vds_cli/src/vds_cli/docs*        — docs-quality
.github/workflows/*.yml          — lint-and-test (self-protect)
scheduler_orchestrator/**        — scheduler-load-smoke, chaos-smoke
docker/**                        — lint-and-test (Dockerfile lint)
```

## Caveats

- `confluence-sync.yml` runs on **every push to main**, not just doc changes; this is intentional for drift detection.
- `chaos-smoke.yml` is **manual only**; automated chaos runs violate SLO during business hours.
- `docs-quality.yml` skips on pushes (not PRs) to avoid noise on automated commit batches.

## See Also

- [infrastructure-v2.15](infrastructure-v2.15.md) — Container and healthcheck patterns
- [ecosystem-daily-report](ecosystem-daily-report.md) — Daily metrics and health monitoring
- `.github/workflows/` in repo root — Live workflow definitions
