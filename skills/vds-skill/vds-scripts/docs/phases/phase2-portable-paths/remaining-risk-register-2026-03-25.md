# Phase 2 remaining risk register

Date: 2026-03-25
Status: maintained
Scope: WHO ecosystem alignment Phase 2 portable path/config closure posture

This note records the remaining risks after the Phase 2 portable path/config work reached a closure-ready state.
It distinguishes maintained-surface risks from historical/generated artifacts and from explicitly deferred validation lanes.

## Risk classification

| Risk class | Status | Meaning |
| --- | --- | --- |
| Maintained portability defect | none currently confirmed | A current code/doc/help surface still violates the active Phase 2 contract |
| Environment/profile readiness | present but non-blocking | A live probe depends on missing local service/profile config rather than a path defect |
| Historical/generated artifact drift | present | Old reports, summaries, generated files, or archived artifacts still contain host-specific examples |
| Native Windows verification gap | explicitly deferred | Contract/simulation coverage exists, but no native Windows host/CI evidence exists |
| Non-core package/platform variance | present but bounded | Package-specific platform logic exists outside the core shared path/config contract |

## Current maintained-surface assessment

Current conclusion:
- no confirmed maintained Phase 2 path/config defects remain in the core shared-helper lane after rebasing onto latest `master` and rerunning focused verification
- maintained docs, guides, skills, and help surfaces now consistently advertise the explicit-override-plus-user-home-VDS contract
- direct executable discovery for AI agents improved materially through the verified help matrix and direct-help fixes

## Remaining risks by category

### 1. Native Windows verification remains deferred

Status: deferred by design

What is true now:
- Windows-oriented simulation/contract coverage exists
- path semantics and naming guidance explicitly account for Windows-oriented environments
- the spec and validation matrix explicitly distinguish `windows-simulated` from `windows-native`

What is still missing:
- real Windows host or CI execution
- PowerShell/CMD validation evidence
- native filesystem/path semantics proof on Windows itself

Current impact:
- Phase 2 must not claim native Windows verification
- this is a truthful-claims boundary, not a known Unix-like runtime defect

### 2. Environment/profile readiness remains a live-probe variable

Status: present but non-blocking

Observed example:
- `vds-cli audit --json-only doctor profile-availability --profiles zai-openai --mode active` still reports `profile_not_found` in the local runtime

Interpretation:
- this is a local profile readiness/configuration issue
- it is not evidence of a shared path/config regression

Current impact:
- bounded live verification should continue to distinguish environment readiness failures from portability failures

### 3. Historical and generated artifacts still contain host-specific paths

Status: present

Observed examples include:
- old phase summaries and implementation reports with `/Users/...` paths
- generated JSON artifacts and validation outputs containing historical local file paths
- archived or compatibility materials that still mention direct `~/.vds/...` examples without the newer `<config-root>` abstraction language

Interpretation:
- these artifacts are not the maintained Phase 2 source of truth
- they should not be used to contradict the maintained closure claim set

Current impact:
- low risk to runtime correctness
- moderate risk to human readers if historical artifacts are mistaken for current guidance

Recommended handling:
- treat cleanup as opportunistic follow-up rather than a Phase 2 closure blocker

### 4. Non-core package/platform variance still exists

Status: present but bounded

Observed examples include:
- package-specific platform logic in `vds_hooks`
- WSL/Windows path conversion helpers in `lsp_orchestrator`
- package-local installer/platform settings outside the core shared helper model

Interpretation:
- these are not currently confirmed violations of the Phase 2 core shared path/config contract
- they represent adjacent platform behavior that may need separate modernization later

Current impact:
- low risk to the core Phase 2 closure packet
- medium follow-up value for future platform hardening work

### 5. Direct executable naming remains a documentation hazard without the help matrix

Status: mitigated in maintained docs

What changed:
- `vds-task` compatibility alias was added
- `vds-diagrams` and `vds-cli schema-convert` now expose structured Typer help surfaces
- `docs/agents/reference/cli-help-matrix.md` now records routed families, direct executable names, and verified `--help` status

Residual risk:
- future packages can still drift if direct executable names change without docs updates

Recommended handling:
- treat `--help` verification and the CLI help matrix as maintained alignment surfaces

## Live verification summary backing this register

After rebasing onto latest `master`, the following remained live-verified:
- `vds-cli env status`
- `vds-cli status`
- `vds-cli doctor`
- `vds-cli jira-cli --json-only projects`
- `vds-cli bitbucket-cli --json-only projects`
- `vds-cli bitbucket-cli --json-only repositories WHO --limit 5`
- `vds-cli confluence-cli search --server internal --cql "type=page" --limit 1`
- `vds-cli elastic --json-only ping`
- `vds-cli sonarqube --json-only ping`
- `vds-cli grafana --json-only health`
- `vds-cli git list --match "*vds*"`
- direct help surfaces including `vds-task`, `vds-diagrams`, `vds-schema-convert`, `vds-cli mcp-server`, and `vds-subagent-stop-hook`

## Risk posture for closure

Phase 2 remains closure-ready under this truthful claim set:
- native macOS validation passed
- Docker-based Ubuntu/Linux validation passed through the supported compose lane
- Windows-oriented simulation/contract validation exists
- native Windows remains explicitly deferred
- no confirmed maintained core shared-helper portability defect remains open

## Recommended next actions

1. Keep this register linked from the closure handoff packet.
2. Treat native Windows as the primary explicit future validation gap.
3. Treat historical/generated artifact cleanup as opportunistic, not blocking.
4. Keep the CLI help matrix maintained whenever direct executable names or help surfaces change.
