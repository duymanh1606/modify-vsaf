<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# Orchestrator Architecture

The active automation stack is centralized under `WHO-project/vds-scripts`.

## Current Layers

- Workspace root: [WHO project baseline](../../../AGENTS.md)
- Shared scripts guide: [docs README](../../README.md)
- Unified router: [vds_cli README](../../../vds_cli/README.md)
- Audit runtime: [audit_orchestrator README](../../../audit_orchestrator/README.md)
- Skills catalog: [vds-skills README](../../../../vds-skills/README.md)

## Active Operator Surface

- Spec triplet authority stays under `.gpt-5.4/specs/audit-orchestrator/`.
- Repo-owned guidance is rooted in `AGENTS.md`, `WHO-project/vds-scripts/audit_orchestrator/README.md`, `WHO-project/vds-skills/skills/audit-orchestrator-skill/SKILL.md`, and the WHO-owned agent docs under `WHO-project/vds-scripts/docs/agents/`.
- `WHO-project/vds-scripts/audit_orchestrator/src/vds_audit_orchestrator/publishers/system_doc_renderer.py` publishes those guidance sources into the system-doc surface, so README and guide drift is user-facing runtime drift, not cosmetic documentation churn.
- Phase 171 is the active merged mainline baseline for audit control-plane behavior.
- The current runtime is no longer staged in isolated worktrees for these surfaces; mainline now includes Phase 167 dispatch optimization, Phase 168 finalization reliability, Phase 169 dispatch observability, Phase 170 schema contract hardening, and Phase 171 gradual dispatch ramp-up.
- The current `workflow-project` lane continues to emit prepared/running/completed summary updates while preserving final aggregate/readiness publication flow; the Phase 171 baseline incorporates gradual ramp-up for `_fill_capacity()` (Phase 171), contract-driven schema validation, safe additive repair of `dispatch_lanes.claimed_at`, startup gating via `dispatch_schema_gate()`, and `doctor schema` operator inspection (Phase 170), plus heartbeat, utilization persistence, progress summaries, and dead-run detection (Phase 169).
