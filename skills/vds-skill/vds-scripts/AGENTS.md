# AGENTS.md — VDS Scripts Workspace

> Python automation workspace for VDS orchestrators and routed CLI commands.

## Scope

- Repository: `WHO-project/vds-scripts`
- Primary responsibilities:
  - `vds-cli` routed command surface
  - audit/spec/task/progress/research/evolution orchestrators
  - shared runtime and environment contracts
- This file is Tier-0 operator contract (keep concise). Deep command catalogs and phase details live in docs references.

## Repo Boundary

This repo holds **runtime Python only** — CLI entry points, orchestrators, MCP
servers, platform abstractions, agent-core libraries, evolution loops.
Claude-Code-facing artifacts (skills, hook plugins, sync machinery, governance
docs) live in `WHO-project/vds-skills/`.

Canonical rules: `who-ecosystem-alignment` Phase 4 FR-8 (Repo purpose) and FR-9
(Direction of dependency: skills may reference vds-scripts entry points;
vds-scripts must build, test, and run with **zero** vds-skills artifacts
present). FR-11 forbids `.claude/skills/<name>/` directories here. FR-12
forbids new hook packages here (canonical hook surface is
`vds-skills/plugins/vds-hooks-*/`).

## Quick Start

```bash
cd WHO-project/vds-scripts

# CLI router — unified entry point for all operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status
./scripts/worktree_uv.sh run --project vds_cli vds-cli status
./scripts/worktree_uv.sh run --project vds_cli vds-cli doctor

# Specialist services (all route through vds-cli)
./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli spec --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli evolution --help
```

## Unified Routing Contract

**`vds-cli` is the single canonical entry point** for all user-facing orchestrator operations.

- All commands route through `./scripts/worktree_uv.sh run --project vds_cli vds-cli <service> <command> [args]`.
- `pyproject.toml [project.scripts]` are router implementation detail — not user-facing contracts.
- Internal scripts (e.g., `vds-evolution`) are backend mechanisms invoked by the router, not directly by users.

## Rules

- Use `./scripts/worktree_uv.sh run --project vds_cli vds-cli ...` for worktree-safe Python execution.
- Runtime is Postgres-first. Do not add filesystem fallback for audit state or evidence.
- Use VDS SDK surfaces for Confluence/Bitbucket operations.
- Keep phase history and long command narratives out of AGENTS.md.

### Testing Rules

- Tests must mock all external services (Confluence, Bitbucket, LLM providers, HTTP endpoints).
- Control env vars with `monkeypatch.setenv` / `delenv`; do not read real local credentials.
- Prefer focused tests for changed modules during development; run broad suites at merge gates.

### Phase Numbering & Branch Naming

Phase numbers are **per-spec local** structural labels, not monorepo-global tags. The same number can mean different things in different specs (e.g., `## Phase 219` in `vds-ai-memory` ≠ `## Phase 219` in `ecosystem-scheduling`). To prevent silent branch-namespace collisions when sessions run in parallel, new phase branches MUST use the prefix `<spec-prefix>-phase<N>`:

- `vai-phase219` — vds-ai-memory (`vai`)
- `eco-phase5` — ecosystem-infrastructure-evolution (`eco`)
- `audit-phase6` — audit-orchestrator (`audit`)
- `core-phase172` — vds-agent-core-alignment (`core`)

Commit messages retain the narrative `phase<N>` form for readability. Existing un-prefixed branches (e.g., `phase218`, `phase219/...`) are grandfathered; the prefix rule applies prospectively. When starting a new phase, check the spec's `requirements.md` for the next free phase number within that spec, then `git branch -a | grep <spec-prefix>-phase<N>` before creating the branch — collision is now diagnosable by name.

### Active Spec Sync

vds-ai-memory: **1547 tests**, spec v20.22.0 (Phase 228/229/230/231 Finalized, Phase 232 Blocked — dedup never ran, max_groups=10, embed degraded)

### Containerization Policy

| Command Category                | Runtime                         | Examples                                                                       |
| ------------------------------- | ------------------------------- | ------------------------------------------------------------------------------ |
| **Host-only** (never in Docker) | Host filesystem                 | `vds-cli skills sync`, `git commit/rebase`, `vds-cli spec create`              |
| **Host-only**                   | Host credentials/env            | `vds-cli memory store/search`, `./scripts/worktree_uv.sh`                      |
| **Container-eligible**          | Docker                          | `vds-cli audit workflow`, `vds-cli research search`, `vds-cli confluence sync` |
| **Hybrid**                      | Container (read) + Host (write) | `vds-cli progress report` (read DB, write reports), `vds-cli pdf convert`      |

`vds-skills` remains container-free. Skill sync must run on host.

### Scheduler Architecture (Single-Scheduler Operator Note, post-2026-04-24)

The VDS ecosystem now has **one** periodic-task scheduler: **`scheduler_orchestrator`** (DBOS-backed, in `scheduler_orchestrator/`). Celery Beat was retired by ADR-14 on 2026-04-24 (commit `a0ba4179`); audit trail at `scheduler_orchestrator/CLOSURE-v2.0.18.md` (Phase 0 of `.gpt-5.4/specs/vds-scheduler/`).

| Concern                                  | Owner                                                                | Notes                                                                                                                                                                                                                                                                    |
| ---------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| All periodic schedules (cron + interval) | `scheduler_orchestrator` (DBOS)                                      | Includes the 6 ex-Celery-Beat memory-evolution tasks (`memory.evolution.{dispatch,sweep,replay-dlq}`, `mem0.{resolve-pending-ids,repush-stalled,repush-local-only}`) plus audit drift scans, chain triggers, event-bus dispatch, and scheduled agent-step workflows      |
| Ad-hoc Celery task dispatch              | Celery worker in `memory_orchestrator/` (worker only — beat retired) | The worker plumbing (`memory_evolution/celery_app.py` + `celery_entrypoint.py`) is intentionally retained per `scheduler_orchestrator/CLOSURE-v2.0.18.md` §Scope Clarification, for explicit `.delay()` / `.send_task()` dispatch from production code. Not a scheduler. |
| Kill switch                              | `VDS_SCHEDULER_ENABLED=false` (default)                              | Disables `scheduler_orchestrator` completely. Celery worker dispatch is unaffected.                                                                                                                                                                                      |

**Kill-switch rule**: `VDS_SCHEDULER_ENABLED=false` (the default in `~/.vds/.env`) keeps `scheduler_orchestrator` dormant. Set `VDS_SCHEDULER_ENABLED=true` only when the scheduler service is intentionally started; this activates 7+ DBOS schedules (6 ex-Celery memory-evolution + `evolution.auto-promote` + the autoscaler tick).

- **Ecosystem Daily Report** (`ecosystem.daily.report`): Runs at 06:00 UTC daily on `ops-default` queue. Collects git activity, scheduler health, event bus metrics, queue depths. Writes Markdown to `reports/ecosystem/`, persists to `sched.ecosystem_report_runs`, publishes `ecosystem.daily.completed`/`.failed` events. Config: `VDS_ECOSYSTEM_DAILY__*` env vars. Spec: `.gpt-5.4/specs/ecosystem-daily-report/`.

**What is NOT a scheduler anymore**: Celery Beat (container removed from the legacy mem0-deploy stack; the unified `docker/docker-compose.services.yml` is beat-free by design; `beat_schedule` is empty `{}`). Tests asserting Celery Beat schedule registrations were updated in v2.0.10 to assert post-retirement empty state. The legacy compose files were retired to `docker/legacy/` in P3 + P4 WP-4.0; that directory was removed in spec v2.15.12 per the no-legacy directive — recover via git history if rollback is ever needed.

## Entry Points

All services route through a single entry:

```bash
vds-cli <service> <command> [args]
```

**Core service families** (non-exhaustive):

- `vds-cli audit ...` — Audit operations (repo, project, multi-project)
- `vds-cli spec ...` — Spec lifecycle (create, validate, consolidate)
- `vds-cli tasks ...` — Task orchestrator
- `vds-cli progress ...` — Progress reports
- `vds-cli research ...` — Research orchestrator
- `vds-cli memory ...` — Memory operations
- `vds-cli evolution ...` — Evolution loop
- `vds-cli confluence ...` — Confluence operations
- `vds-cli bitbucket ...` — Bitbucket operations
- `vds-cli git ...` — Git orchestrator
- `vds-cli jira ...` — JIRA operations
- `vds-cli db-query ...` — Database queries
- `vds-cli grafana ...` — Grafana operations
- `vds-cli sonarqube ...` — SonarQube operations
- `vds-cli lsp ...` — LSP operations
- `vds-cli elastic ...` — Elasticsearch operations
- `vds-cli pdf ...` — PDF generation
- `vds-cli diagrams ...` — Diagram generation
- `vds-cli schema ...` — Schema conversion
- `vds-cli excel ...` — Excel operations
- `vds-cli google-sheets ...` — Google Sheets operations
- `vds-cli circular-dependency ...` — Circular dependency analysis
- `vds-cli openapi ...` — OpenAPI operations
- `vds-cli links ...` — Link validation
- `vds-cli structure ...` — Structure validation
- `vds-cli brd ...` — BRD coverage
- `vds-cli intellij ...` — IntelliJ operations
- `vds-cli metabase ...` — Metabase operations
- `vds-cli hexagonal ...` — Hexagonal compliance
- `vds-cli markdown ...` — Markdown operations
- `vds-cli mcp ...` — MCP server operations
- `vds-cli multi-agent ...` — Multi-agent operations
- `vds-cli public-interface ...` — Public interface boundary
- `vds-cli scheduler ...` — Ecosystem scheduler (schedule/event/chain ops); requires `VDS_SCHEDULER_ENABLED=true`
- `vds-cli telegram ...` — Telegram bridge ops (DISABLED 2026-04-30 — aiogram pydantic conflict; restore when aiogram >=3.28.0). Bridge code present at `telegram_bridge/`, 102 tests pass offline.

## Search & Navigation

- Start with `rg` for exact symbols and strings.
- Use `sg` / structural search for pattern-level code exploration.
- For large-scope understanding, prefer graphify/gitnexus before broad file scans.
- Phase truth and runtime baselines are maintained in docs references (below), not inline here.

## Code

### Critical Path Symbols

Before changing a symbol, run impact analysis:

- `gitnexus_impact({target: "SymbolName", direction: "upstream"})`

Before committing, run scope detection:

- `gitnexus_detect_changes({scope: "staged"})`

For unknown flows, start with:

- `gitnexus_query({query: "concept"})`
- `gitnexus_context({name: "symbol"})`

### GitNexus Guardrails

- Treat HIGH/CRITICAL impact results as explicit risk gates and surface them before continuing edits.
- Never perform symbol renames via plain find/replace; use graph-aware rename workflows.
- Re-index intentionally after significant code changes:
  - `npx gitnexus analyze`
  - `npx gitnexus analyze --embeddings` (when embeddings are in use)

## Validation Gates (last verified: 2026-05-04 (Phase 14 post-merge))

| Package                                      | Passed     | Failed | Skipped | Gate                                                                                                                                               |
| -------------------------------------------- | ---------- | ------ | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| spec_orchestrator                            | 14         | 0      | 0       | GREEN                                                                                                                                              |
| scheduler_orchestrator                       | 1,454      | 0      | 3       | GREEN (+2 from FR-14.2 cache fix)                                                                                                                  |
| vds_agent_core                               | 932        | 0      | 0       | GREEN (+6 from FR-14.1 + FR-14.5 forward-ref fixes)                                                                                                |
| memory_orchestrator (Phase 225 surface)      | 8          | 0      | 0       | GREEN                                                                                                                                              |
| multi_agent_orchestrator (Phase 225 surface) | 49         | 0      | 0       | GREEN                                                                                                                                              |
| audit_orchestrator (profile-focused subset)  | 121        | 15     | 24      | DEGRADED — pre-existing Python 3.14 forward-ref + config_hooks bugs (FR-14.1/14.5 reduced GAP cascade, full audit suite 8,290 PASS still DEGRADED) |
| progress_report_orchestrator                 | 452        | 1      | 0       | DEGRADED — pre-existing alembic env_py schema-name assertion                                                                                       |
| telegram_bridge                              | 102+       | 0      | 0       | GREEN                                                                                                                                              |
| vds_cli (ecosystem)                          | 286        | 0      | 5       | GREEN                                                                                                                                              |
| **Phase 14 surface total**                   | **1,477+** | **0**  | **8**   | GREEN (+8 from Phase 14 fixes)                                                                                                                     |

- Scheduler Alembic: `a1b2c3d4e5f8` (Phase 2 golden-signals columns live)
- Memory/Progress/Audit Alembic: AT_HEAD
- Docker: 10/10 containers healthy; worker + API same image digest
- Live CLI smoke: 6/6 pass (spec validate, scheduler help, trigger-now, db-query, onboarding-funnel, freshness)
- Phase 231 deploy: vds-memory:1.0.0 image **10.4 GB** (62% reduction from 27.6 GB pre-Phase-225); all 7 health layers healthy; doctor embedding fallback OLLAMA_BASE_URL → BASE_URL deployed; VDS_MEMORY_TIMEOUT_SECONDS=300 set; entrypoint.sh alembic upgrade head verified

## Docs

- CLI command reference: `docs/agents/reference/cli-commands.md`
- Ecosystem report: `docs/agents/reference/ecosystem-daily-report.md`
- Skills commands: `docs/agents/reference/skills-commands.md`
- Infrastructure v2.15: `docs/agents/reference/infrastructure-v2.15.md`
- CI workflows: `docs/agents/reference/ci-workflows.md`
- Ecosystem index: `ECOSYSTEM-DOCS.md`
- Ecosystem changelog: `ECOSYSTEM-CHANGELOG.md`
- Environment git-helper: `docs/agents/reference/env-git-helper.md`
- Phase archive: `docs/phases/CHANGELOG.md`
- Script authoring contract: `scripts/README.md`
- Worktree wrapper contract (Phase 220.V): `scripts/README.md` §Worktree Wrapper Scripts (`worktree-add.sh` / `worktree-remove.sh` are canonical for vds-scripts; bare `git worktree` is fallback only)
- Telegram Bridge reference: `telegram_bridge/skill_content/references/README.md`
- Root router: `../AGENTS.md`
- Ecosystem alignment: `ECOSYSTEM_ALIGNMENT.md` (openspace hook analysis)
- Canonical spec: `.gpt-5.4/specs/ARCHIVE/who-project-documentation-enhancement/` (ARCHIVED — Phases 177→179 + post-merge updates merged)

### Comprehensive Docs (Phase 180)

- Introduction: `docs/agents/explanation/who-ecosystem-introduction.md`
- Quick Start: `docs/agents/tutorials/quick-start.md`
- Configuration: `docs/agents/reference/configuration-reference.md`
- Troubleshooting: `docs/agents/how-to/troubleshooting-guide.md`
- Architecture: `docs/agents/explanation/system-architecture.md`
- Tips & Tricks: `docs/agents/how-to/tips-and-tricks.md`
- See all: `ECOSYSTEM-DOCS.md`

### Symlink Handling

- `CLAUDE.md` in this repo is a symlink → `AGENTS.md`.
- On filesystems where `core.symlinks=false`, the validator reports:
  `CLAUDE.md is not a symlink to AGENTS.md (ERROR)`.
- Fix: enable Git symlinks (`git config --global core.symlinks true`) or re-clone.

## Ngôn ngữ / Language

- [English](./AGENTS.md)
- [Tiếng Việt](./AGENTS.vi.md)

## Confluence Documentation

- [WHO-Project Ecosystem Documentation](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
  ecosystem: **41 tests**, spec v2.16.0 (Phase 0/8 Finalized; v2.16.0 deploy-portability extension applied)
