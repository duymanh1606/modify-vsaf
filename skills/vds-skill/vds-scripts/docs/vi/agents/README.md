<!-- diátaxis: how-to -->

<!-- TODO: translate — Vietnamese translation pending -->

# VDS Agent Docs

WHO-owned documentation hub for agents working in the VDS monorepo.

## Sections

- [Tutorials](tutorials/index.md)
- [How-to Guides](how-to/index.md)
- [Reference](reference/index.md)
- [Explanation](explanation/index.md)

## Primary Runtime Sources

- [WHO project baseline](../../../AGENTS.md)
- [Monorepo baseline](../../../../AGENTS.md)
- [Centralized audit spec](../../../../.gpt-5.4/specs/audit-orchestrator/tasks.md)
- [Scripts workspace guide](../../README.md)
- [Unified CLI reference](../../../vds_cli/README.md)
- [Audit orchestrator guide](../../../audit_orchestrator/README.md)
- [Skills catalog guide](../../../../WHO-project/vds-skills/README.md)
- [Search tools reference](reference/search-tools.md)
- [Skills reference](reference/skills-reference.md)

## Current Alignment Note

- `WHO-project` is the canonical ecosystem for both reusable skills and routed scripts.
- Use `vds-scripts-skill` as the platform-routing skill for command-family selection and current scripts-capability discovery.
- Use specialist skills for deep workflow/runbook guidance.
- The current authoritative latest-only audit/spec baseline is under the root `.gpt-5.4/specs/audit-orchestrator/` triplet.
- Agent-facing docs must distinguish clearly between merged runtime behavior that exists in code today and remaining implementation work that is still incomplete.
- `workflow-projects` is now present in the merged runtime as the current parent command surface for multi-project orchestration.
- The current parent command is intentionally thin and should be documented that way: it composes `parse-registry`, `prepare`, `state readiness`, `state completeness`, and child `workflow-project` rather than replacing child project execution semantics.
- Phase 131 exposes two separate parent-stage parallelism lanes, both bounded and operator-visible: maximum-parallel project preparation and maximum-parallel project analysis. Docs should keep those separate instead of collapsing them into child `--max-concurrent` repo fan-out.
- Parent manifest/progress-state artifacts in Phase 131 are derived orchestration artifacts for monitoring, recovery scoping, and operator visibility. They are not a replacement for authoritative Postgres-backed readiness, completeness, evidence state, or child terminal artifacts.
- Parent/child recovery semantics must stay explicit in docs: parent orchestration scopes retry/resume at the project level, while child `workflow-project` remains responsible for repo-level dispatch, provider failover, aggregation, and Confluence upload behavior.
- Current runtime caveat: `workflow-projects` is merged and usable for bounded production slices, targeted testing, and operator-visible orchestration, but broad all-project execution should still start from bounded slices and explicit concurrency settings rather than assuming unlimited fan-out.
- Multi-project orchestration must keep per-project artifact isolation and explicit outer concurrency settings; do not document shell fan-out as the preferred path when `workflow-projects` is available.
