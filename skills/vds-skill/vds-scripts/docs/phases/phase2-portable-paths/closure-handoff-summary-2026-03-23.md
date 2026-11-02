# Phase 2 closure handoff summary

Date: 2026-03-24
Phase: WHO ecosystem alignment - Phase 2 portable path/config cleanup
Status: closure-ready

## Purpose

This note is the closure-oriented handoff summary for the active Phase 2 portable-path worktree.
It records what is already implemented, what was validated, what remains intentionally deferred,
and what the next recommended actions are for clean phase closure.

## Worktree

Active implementation lane:

- `WHO-project/worktrees/vds-scripts-phase2-portable-paths`

Primary intent of this lane:

- remove hardcoded machine-specific path assumptions from maintained runtime surfaces,
- establish a shared portable path/config model,
- align maintained docs/help/spec text with the actual implementation state,
- and produce honest validation evidence across supported verification lanes.

## Executive summary

Phase 2 is no longer primarily a migration-design effort.
The shared path/config architecture is already implemented in the active worktree, focused regression
coverage exists, major CLI surfaces were exercised, and portability guidance/evidence docs were added.

This lane is now best treated as a closure-ready implementation and evidence packet:

- maintained validation docs are aligned to the active contract,
- canonical defaults and compatibility behavior are distinguished in maintained guidance,
- validation evidence has been consolidated into maintained closure documents,
- and native Windows claims remain explicitly deferred until a real Windows execution lane exists.

## Implemented core architecture

The active worktree implements the intended shared path/config model through:

- `vds_cli_common/src/vds_cli_common/paths.py`
- `vds_cli_common/src/vds_cli_common/env.py`
- `vds_cli/src/vds_cli/env.py`

Key implemented decisions:

- shared path/config helper lives in `vds_cli_common.paths`,
- the active friendly default uses a user-home VDS root (`~/.vds` on Unix-like systems),
- explicit overrides are supported via:
  - `VDS_CONFIG_DIR`
  - `VDS_CACHE_DIR`
  - `VDS_DATA_DIR`
  - `VDS_LOG_DIR`
  - `VDS_ENV_FILE`
- maintained runtime surfaces use override-first resolution and otherwise fall back to the canonical user-home VDS defaults,
- the shared env file default remains `<config-root>/.env`

## Maintained runtime and doc alignment completed in this lane

The worktree includes broad maintained-surface cleanup so user-facing behavior and guidance now better
match the shared helper contract.

Representative maintained surfaces touched in this lane include:

- `audit_orchestrator/src/vds_audit_orchestrator/config.py`
- `audit_orchestrator/src/vds_audit_orchestrator/cli_impl.py`
- `audit_orchestrator/src/vds_audit_orchestrator/collectors/material_cache.py`
- `audit_orchestrator/src/vds_audit_orchestrator/engine/project_topology.py`
- `audit_orchestrator/src/vds_audit_orchestrator/evidence/loader.py`
- `audit_orchestrator/src/vds_audit_orchestrator/extract_cmds.py`
- `git_orchestrator/src/vds_git_orchestrator/orchestrator.py`
- `confluence_orchestrator/src/confluence_orchestrator/config.py`
- `sonarqube_orchestrator/src/vds_sonarqube_orchestrator/config.py`
- `vds_cli/README.md`
- `docs/agents/reference/portable-paths-and-config.md`
- `docs/agents/reference/portable-paths-validation-matrix.md`

## Focused regression coverage now present

Focused regression tests exist in the active worktree for the shared helper and the main Phase 2
audit/bootstrap path behavior.

Representative tests:

- `vds_cli_common/tests/test_paths.py`
- `vds_cli_common/tests/test_env.py`
- `audit_orchestrator/tests/test_paths_config_phase2.py`
- `audit_orchestrator/tests/test_cli_paths_phase2.py`
- `audit_orchestrator/tests/unit/scripts/test_verify_phase124_handoff.py`

These tests support the claim that the first-wave portability implementation is already in place.
Remaining work is evidence consolidation, not initial test creation.

## Validation evidence summary

Authoritative evidence note:

- `docs/phases/phase2-portable-paths/verification-evidence-2026-03-23.md`

Maintained validation guidance:

- `docs/agents/reference/portable-paths-validation-matrix.md`
- `docs/agents/reference/portable-paths-and-config.md`

### Verified lanes

#### 1. `native-macos`

Status: pass

Phase 2 host-native verification covered:

- shared helper precedence and user-home VDS default behavior,
- shared env loading behavior,
- audit config/report/log default behavior,
- and focused CLI/bootstrap checks.

#### 2. `docker-ubuntu`

Status: pass

The supported Linux verification lane now runs through the compose-based path:

- `docker/compose.phase2-verification.yml`
- supported verification script under `scripts/verification/`

Important outcome:

- the Docker Ubuntu lane found real portability issues,
- those issues were fixed in this worktree,
- and the focused Linux verification packs now pass through the supported compose path.

#### 3. `windows-simulated`

Status: pass

Current Windows-oriented evidence is contract-based rather than native:

- helper precedence/path logic,
- docs and examples using override variables,
- and explicit avoidance of hardcoded POSIX-only examples in maintained guidance.

#### 4. `windows-native`

Status: deferred

No native Windows host or CI runner was used in this phase.
Phase 2 must not claim native Windows verification until a real Windows lane produces evidence.

## Maintained contract interpretation

Maintained Phase 2 surfaces now use one friendly contract.
That contract should be interpreted as:

- explicit env overrides win,
- otherwise config/cache/data/log roots resolve from the canonical user-home VDS defaults,
- the shared env file resolves from `VDS_ENV_FILE` or `<config-root>/.env`,
- maintained docs and examples should advertise only the active override-plus-user-home-VDS contract.

## Notable defects discovered and fixed during live verification

This lane surfaced real code issues, not only doc drift.

Examples fixed during live verification included:

- import-breaking stray token in `audit_orchestrator/src/vds_audit_orchestrator/extract_cmds.py`
- syntax issue in `sonarqube_orchestrator/src/vds_sonarqube_orchestrator/cli.py`
- corrupted trailing fragment in `git_orchestrator/src/vds_git_orchestrator/orchestrator.py`
- missing `get_shared_env_path` import in `elastic_orchestrator/src/vds_elastic_orchestrator/cli.py`, which previously broke the structured config-error path during `vds-cli elastic --json-only ping`
- Jira `projects` raw credential traceback replaced with clean settings-driven CLI error handling in `jira_orchestrator/src/vds_jira_orchestrator/cli.py`
- Bitbucket `projects` silent credential failure replaced with an operator-facing error in `bitbucket_orchestrator/src/vds_bitbucket_orchestrator/cli.py`

These fixes matter for closure because they demonstrate that Phase 2 validation exercised real runtime
entrypoints rather than only static text cleanup.

## Phase 2 spec alignment status

Spec location:

- `.gpt-5.4/specs/who-ecosystem-alignment/`

Current alignment posture:

- the spec reflects that the shared helper architecture is implemented,
- the Phase 2 `TSK-2.2x` / `TSK-2.3x` task block now reads as implemented and closure-ready where that matches the active worktree,
- the validation matrix and evidence template are maintained, executed surfaces rather than hypothetical planning artifacts,
- and native Windows remains explicitly deferred rather than implicitly open-ended.

Spec tasks most relevant to the closure claim set:

- `TSK-2.27`
- `TSK-2.32`
- `TSK-2.33`
- `TSK-2.34`
- `TSK-2.35`

Interpretation of these tasks now:

- implemented in code/docs/evidence,
- closure-ready under the current truthful claim set,
- with future work limited mainly to Windows-native validation or ordinary maintenance.

## CLI verification posture

Exported CLI entrypoints were verified from their owning package environments with `--help` and responded successfully across the active worktree surface, including the routed CLIs, standalone orchestrators, and hook scripts.

Live read-only probes also confirmed the expected distinction between code defects and environment readiness:

- the active shared env path now resolves from `~/.vds/.env` on the current Unix-like host, confirming the friendly `~/.vds` default is live rather than only documented
- `vds-cli env status`, `vds-cli doctor`, and `vds-cli status` all succeed under that active `~/.vds` contract and report healthy shared-auth/bootstrap and router availability state
- `vds-cli jira-cli --json-only projects` succeeds with authenticated data, and `vds-cli jira-cli search "project = CBDC ORDER BY updated DESC" --limit 3 --json-only` succeeds as an authenticated JQL feature probe; in the latest bounded run it returned `0` issues rather than an auth or transport failure
- `vds-cli bitbucket-cli --json-only projects` succeeds with authenticated data, and `vds-cli bitbucket-cli --json-only repositories WHO --limit 5` succeeds with authenticated repository listing output
- `vds-cli confluence-cli search --server internal --cql "type=page" --limit 1` succeeds with authenticated data and returns a real page result
- `vds-cli elastic --json-only ping` succeeds in the current runtime and returns a healthy structured response with Kibana connection details
- `vds-cli sonarqube --json-only ping` succeeds and reports an `up` status with server version data
- `vds-cli grafana --json-only health` succeeds and reports healthy Grafana and datasource status
- `vds-cli git list --match "*vds*"` succeeds through the routed manifest path and lists the expected VDS repositories
- `vds-cli spec validate who-ecosystem-alignment` succeeds, reinforcing that the maintained spec surface remains aligned
- `vds-cli audit --json-only doctor profile-availability --profiles zai-openai --mode active` currently reports `profile_not_found` for the local runtime profiles file rather than exposing a portability defect

Continued one-by-one CLI verification also surfaced two additional operator-facing defects that were fixed during this closure pass:

- `vds-subagent-stop-hook --help` originally emitted a coroutine-not-awaited runtime warning because `vds_hooks/src/vds_hooks/scripts/subagent_stop.py` had a corrupted duplicated tail; that corruption was removed and the help surface now runs cleanly
- `vds-cli mcp-server --help` originally lacked a usable help path; a minimal explicit help surface was added in `mcp_server/src/vds_mcp_server/server.py`, a follow-on missing `sys` import was fixed, and the command now emits clean usage text

This means the remaining live-probe failures are primarily environment/profile readiness issues, not maintained Phase 2 path-contract drift.

## Deferred or future-only items

The Phase 2 portability scope is closure-ready. The remaining items are intentionally outside the current truthful claim set.
A maintained remaining-risk register now lives at `docs/phases/phase2-portable-paths/remaining-risk-register-2026-03-25.md`.

### 1. Native Windows remains deferred

Still required for any stronger claim:

- Windows host or CI execution,
- PowerShell or CMD validation,
- native filesystem/path semantics evidence.

### 2. Optional future polish

Non-blocking follow-up work may still be useful when convenient:

- keep maintained guidance free of accidental machine-specific examples,
- keep maintained surfaces on one explicit-override-plus-user-home-VDS contract,
- and continue normalizing broad docs/help examples when they are touched for unrelated work.

## What is intentionally not required for closure

The following are not blockers for truthful Phase 2 closure:

- removal of all historical references in archived or generated artifacts,
- claiming native Windows verification without a real Windows lane,
- broad new migration work beyond the already-implemented shared helper model.

## Recommended next actions

1. Treat the Phase 2 lane as a completed portability implementation with maintained closure evidence, not a fresh migration pass.
2. Keep `portable-paths-validation-matrix.md` and the evidence note as the maintained closure sources.
3. Re-run targeted validation only if maintained portability surfaces change again.
4. Present closure using this claim set only:
   - native macOS validation,
   - Docker-based Ubuntu/Linux validation,
   - Windows-oriented simulation/contract validation,
   - native Windows deferred.

## Closure-ready claim set

The current lane can truthfully claim:

- core shared path/config migration is implemented,
- maintained runtime/help/docs cleanup is closure-ready,
- focused regression coverage exists,
- native macOS verification passed,
- Docker-based Ubuntu verification passed through the supported compose lane,
- Windows-oriented simulation/contract coverage exists,
- native Windows verification remains deferred.

## Handoff note

Use this document together with:

- `docs/phases/phase2-portable-paths/verification-evidence-2026-03-23.md`
- `docs/agents/reference/portable-paths-validation-matrix.md`
- `.gpt-5.4/specs/who-ecosystem-alignment/tasks.md`

when preparing the final Phase 2 closure statement or handing the lane to the next reviewer.