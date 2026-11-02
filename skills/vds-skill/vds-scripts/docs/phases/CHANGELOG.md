# Phase Changelog Archive

Extracted from AGENTS.md lines 1-66.

## Phase 225 — Pluggable Embedding + Per-Agent Provider Config (DEPLOYED 2026-05-02)

Merged to vds-scripts master at `41798074` (W1-W7 fast-forward chain on top of `b9d7a08f`); companion vds-skills `vds-ai-memory-skill` v3.10.0 at `027fb85`. Spec `.gpt-5.4/specs/vds-ai-memory/` v20.6.1.

**Scope** (FR-225.1..23 + FR-226.1..15 + NFR-225.1..15 + NFR-226.1..4 — 50 spec items):

- **Track-A — Pluggable embedding SDK** hoisted from `memory_orchestrator/.../embedding_service.py` into `vds_agent_core.llm.embedding`: `EmbeddingClient` Protocol + 9-provider registry (`ollama`, `openai`, `cohere`, `voyage`, `mistral`, `jina`, `litellm`, `local`, `hash`) + `EmbeddingSettings(BaseSettings)` factory + auto-routing from `<provider>/<model>` strings. Default provider Ollama (host-native, Metal GPU on macOS); cloud failover via OpenAI matryoshka built-in.
- **Track-B — Per-agent provider config** via 3-layer cascade (defaults → orchestrator subclass → agent runtime). `LLMSettings.for_agent(agent_id)` + `EmbeddingSettings.for_agent(agent_id)` factories. Per-agent overrides via env (`VDS_AGENT_<ID>_EMBED__*`), API (`AgentRegistrationRequest`), or programmatic (`overrides=...`). Credential-reference indirection (`${env:VAR_NAME}`) with NFR-225.12 allowlist.
- **W4 deploy hygiene**: `memory_orchestrator/Dockerfile` drops the bge-m3 sentence-transformers bake; `pyproject.toml [embeddings]` drops `sentence-transformers`; `docker-compose.services.yml` adds `VDS_AGENT_CORE_EMBED__*` defaults + `extra_hosts: ['host.docker.internal:host-gateway']` for Linux portability.
- **W7 dedup consolidation**: `vds_agent_core.security.credentials` (NEW) consolidates two divergent regex implementations into a single canonical sanitizer covering Bearer / `sk-` / `hf_` prefixes plus URL query params (`?api_key=...`) plus JSON body fields (`"api_key":"..."`).

**ADRs landed**: ADR-98 (embedding hoisted to vds_agent_core; default Ollama), ADR-99 (registry-based provider routing + LiteLLM-style auto-routing), ADR-100 (3-layer cascading settings).

**Operational impact**:

- Image size: `vds-memory:1.0.0` **27.6 GB → 10.4 GB** (62% reduction; ML stack moved to host Ollama).
- Build time: ≤ 2m 39s on warm BuildKit cache (target was ≤ 5 min).
- Container Ollama round-trip: 1024-dim verified live via `host.docker.internal:11434`.
- `vds-cli memory` subcommand surface intact (19 commands; 0 regressions).
- 277 new Phase 225 tests + 1163 vds_agent_core total tests; ~99% Phase 225 surface coverage.

**Operator action required for cloud failover**:

- For OpenAI: set `VDS_AGENT_CORE_EMBED__PROVIDER=openai`, `MODEL_STANDARD=text-embedding-3-large`, `DIMENSION=1024` (matryoshka), root `OPENAI_API_KEY`.
- For dev hosts without Ollama: set `VDS_AGENT_CORE_EMBED__FAIL_OPEN=true` (fall back to `HashEmbeddingClient`).
- For per-agent provider mixing: see `vds_agent_core/docs/embedding.md` §Per-Agent Provider Config.

**W8 post-merge fix**: `service/api/v1/embedding.py` `re-embed` + `embedding_status` endpoints fixed to read provider/model/dimension via `embedding_service._settings.*` instead of the W4-deleted `_provider`/`_model`/`_dimension` attributes (would have AttributeError'd in production on the first non-dry-run re-embed call).

**Out of scope** (deferred): Phase 227 per-agent operator tooling stub (FR-227.1..6, trigger-gated); Phase 221 (VAMI-031 WebSocket subprotocol), Phase 222 (VAMI-032 mem0 v3 cloud entity-scope migration) — both PROPOSED stubs awaiting trigger conditions per spec.

---

# AGENTS.md — VDS Scripts Workspace

> Live validation 2026-04-28: **2,610+ tests, 0 failures** across 5 packages. Scheduler at `a1b2c3d4e5f8` (Phase 2 columns live). 10/10 Docker healthy.

Operational rules for `WHO-project/vds-scripts`.

Merged mainline runtime baseline is Phase 171 implemented (schema contract hardening, startup gating, gradual dispatch ramp-up, and dispatch observability all merged into the current mainline runtime).
Phase 168 fixes dispatch state finalization reliability:
- **Atomic `finalize_dispatch_run()`**: single-transaction store method replaces N+1 separate DB ops — run, lanes, and events written atomically with full rollback on failure.
- **`_finalization_store` preservation**: saved before the dispatch loop; survives mid-run `_dispatch_store` nulling at degradation time so finalization always writes.
- **Resilient wrapper**: `_finalize_dispatch_run()` retries up to 3 times (2s, 4s backoff); final failure logs at `error` level — no silent swallow.
- **Schema fix**: `_claim_resumable_dispatch_lanes()` now sets `status = 'running', claimed_at = NOW()` (not `'claimed'`); stale-claim recovery added to CTE WHERE.
- **`doctor repair-dispatch`**: new subcommand force-closes stuck runs via `finalize_dispatch_run()` with `termination_reason='force_closed_by_doctor'`; uses `started_at` staleness (no `updated_at` column).
- **Parent finalization**: `workflow-projects` parent path replaced bare `except Exception: warning` with `_finalize_dispatch_run()` retry wrapper.
Phase 171 adds gradual dispatch ramp-up for safer startup behavior:
- **Gradual capacity scaling**: `_fill_capacity()` starts with `ramp_up_slots` capacity instead of `max_concurrent`, increasing by `ramp_up_slots` every `ramp_up_interval` seconds until `max_concurrent` is reached.
- **CLI params**: `--ramp-up-slots` (min=0, default=0) and `--ramp-up-interval` (min=1, default=30). `ramp_up_slots=0` preserves Phase 170 behavior.
- **Ramp-up tick placement**: fires on both job completion and poll timeout — capacity grows on schedule even when all active slots are running.
- **Safer default stagger**: `submission_stagger_ms` default raised from 100ms to 200ms for safer burst behavior.
- **Logging**: `dispatch_ramp_up_capacity_increased` structured log event on each capacity bump with `new_capacity` and `max_concurrent`.
- **Tests**: 23 new tests in `test_dispatch_ramp_up_phase171.py`.
Phase 170 hardens the audit-state schema contract for DB-native dispatch:
- **Schema contract**: `_DISPATCH_SCHEMA_CONTRACT` defines 7 dispatch tables + `dispatch_lanes.claimed_at` as blocking contract items; evaluated during every `PostgresStateStore.__init__`.
- **Safe additive repair**: missing `dispatch_lanes.claimed_at` is repaired with `ALTER TABLE … ADD COLUMN IF NOT EXISTS … TIMESTAMPTZ` before dispatch can proceed; idempotent and safe to run repeatedly.
- **Startup gating**: `dispatch_schema_gate(store)` raises `DispatchSchemaIncompatibleError` for `incompatible_blocking` or `unreachable` — hard fail before any dispatch state is created.
- **Resume/parent-dispatch gate**: same gate applied to the resume claim path (`_claim_resumable_dispatch_lanes`) and `workflow-projects` parent dispatch startup independently.
- **`doctor schema` command**: `vds-cli audit doctor schema [--json]` reads `_schema_compat_result` with no extra DB round-trip; JSON includes `status`, `dispatch_safe`, `db_reachable`, `missing_tables`, `violations`, `repaired_items`, and `remediation`; exits 0/1/2.
- **`doctor repair-dispatch` pre-check**: schema compatibility validated before repair begins; `incompatible_blocking` or `unreachable` exits 2 with `schema_compatibility.blocking_reasons` in JSON.
Phase 169 adds dispatch observability:
- **Dispatch event contract**: DDL widened to 9 event types (adding `lane_closed_by_doctor`, `dispatch_doctor_repair`); `_DISPATCH_SCHEMA_CONTRACT` entry for `event_type` column.
- **Heartbeat**: `heartbeat_at` column on `dispatch_runs`, written every 10 completions; `dispatch_run_status` VIEW includes heartbeat; `update_dispatch_run_heartbeat()` store method.
- **Utilization persistence**: `run_summary["utilization"]` populated from `_DispatchUtilizationTracker.summary()` and persisted to `dispatch_runs.metadata_json`.
- **Progress log**: `dispatch_progress_summary` fires at 50-completion or 300-second boundary with `completed_total`, `pending_remaining`, `active_slots`, `slot_utilization_pct`.
- **Dead-run detection**: `vds-cli audit doctor dispatch-status --dead-threshold-seconds N` flags `potentially_dead` runs; heartbeat age formatting in table output.
- **Tests**: 20+ new tests across 5 test files.
Phase 167 adds dynamic late-binding profile assignment (`rows_per_shard==1` only), profile-agnostic `dispatch_job_id`, pre-dispatch row exclusion via shared `_build_instruction_analysis_text` helper, time-weighted utilization telemetry (`_DispatchUtilizationTracker`), and full regression verification.
Phase 166 adds route-aware provider failure classification (`ROUTE_PROVIDER_UNAVAILABLE`), failover-only strategy for provider-route credential gaps (skip same-provider retry, go directly to cross-profile failover), truthful synthesis fallback telemetry via `SynthesisFallbackCause` enum, prompt-level retry/failover counters in `resilience_summary`, and structured warnings for unclassified 400-class provider errors.
Phase 165 adds consolidated tmux runner tooling, dashboarding, script archival, and explicit manual continuation guidance on top of the merged Phase 164 runtime.
Phase 164 adds structured outcome interpretation and exclusion tracking to the dispatch and summary surfaces:
- **DispatchOutcomeClassification enum**: structured outcome interpretation replacing ad-hoc string matching — classifies every dispatch result into a canonical category for downstream consumers.
- **Exclusion tracking**: `workflow-summary.json` now records explicit exclusion metadata and aggregated exclusion summaries for scope, readiness, analysis-excluded, profile-unavailable, and checklist-parseability paths so zero-work and degraded outcomes stay operator-visible.
- **Timeout diagnostics**: dispatch summary includes `timeout_kind` (hard/soft/provider) and `partial_rows_count` for rows that started evaluation but did not complete.
- **Zero-work reason classification**: when a workflow-project run completes with no evaluated rows, the summary includes a structured `zero_work_reason` field explaining why (no repos in scope, all rows excluded, provider unavailability, etc.).
Post-Phase 164 fixes (merged to mainline):
- **Sharded merge checklist propagation**: `merged_rows_payload` now spreads `**row.row_data` as the base dict in both `_load_and_merge_runs` and `_merge_row_sharded_repo_runs`, ensuring full checklist fields (requirement_text, score_breakdown, evidence_refs, provenance) flow through to `_materialize_project_repo_report_dirs`. This enables `audit-checklist.json` materialization and full 5-section Confluence reports (checklist_core + checklist_details) for `--from-db-runs` and row-sharded merge paths.
- **Incremental upload sidecars**: `_materialize_project_repo_report_dirs` now writes `audit-checklist.delta.json` and `audit-checklist.meta.json` alongside `audit-checklist.json`, enabling `--incremental-upload` section-level patching instead of full page rewrites for materialized reports.
- **Row patching for model compatibility**: Materialization patches rows with default `provenance` and `score_breakdown.raw_score` when legacy DB rows lack these fields, preventing `AuditChecklist` validation failures.
Phase 163 is consolidated into the mainline baseline.
Phase 162 fixes the Confluence probe consistency mismatch between doctor diagnostics and workflow startup auto-offline behavior, and adds:
- **Shared Confluence connectivity contract**: `confluence_connectivity.py` extracts endpoint probing into a reusable helper shared by doctor and workflow startup.
- **Endpoint-set `any_reachable` policy**: startup uses the same multi-endpoint probe as doctor; false offline activation is eliminated when any configured endpoint is reachable.
- **Improved startup diagnostics**: structured logs include `decision_basis`, `any_reachable`, `internal_reachable`, `reachable_endpoints`, `endpoint_count`; misleading LAN/WiFi guidance removed.
- **DDL hygiene**: `space_key` column added to `CREATE TABLE published_pages` DDL for self-documenting schema.
Phase 161 preserves the Phase 160 dispatch model and practical concurrency optimization, and adds:
- **Manual verification isolation**: real-service verification stays under explicit `tests/verification/` opt-in surfaces.
- **PDF test-surface recovery**: default collection no longer probes Docker, Redis, or internet at collection time.
- **Runtime hardening**: package-path timeout fallback, non-targeted row skip for single-row shards, deferred upload retry, unevaluable-row pre-filter, and 1200s single-row shard timeout default.
- **Confluence SDK call minimization**: `space_key` persistence and session caching, verified-parent dedup, and retry compounding capped per logical operation.
Phase 160 still delivers practical concurrency optimization on the Phase 158 dispatch substrate:
- **Checklist pre-cache**: Parent serializes checklist to disk; children read via `VDS_AUDIT_CANONICAL_CHECKLIST_JSON` env var (0 child Confluence calls).
- **Single-row shards**: `--rows-per-shard 1` dispatches 1 row per job for true row-level backfill via existing `FIRST_COMPLETED + _fill_capacity` loop.
- **Per-profile timeout**: `~/.vds/config/profile-timeouts.yaml` + `VDS_AUDIT_PROFILE_TIMEOUT_{PROFILE}` env var overrides.
- **Submission stagger**: `--submission-stagger-ms 100` prevents thundering herd on multi-slot fills.
- **Risk mitigations**: Per-row failure counter (R9, max 3 profiles before skip), dynamic resume limit (R7, scales with job count).
Phase 159 RowQueue rewrite deferred — existing dispatch loop is architecturally sufficient with Phase 160 changes.

