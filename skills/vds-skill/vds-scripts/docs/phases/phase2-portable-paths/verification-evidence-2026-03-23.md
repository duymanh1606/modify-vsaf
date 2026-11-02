# Phase 2 portability verification evidence

Date: 2026-03-24
Status: validated and closure-ready
Scope: WHO ecosystem alignment Phase 2 portable path/config work

This note records the actual verification evidence produced during the current Phase 2 implementation pass.
It follows the validation lanes defined in `docs/agents/reference/portable-paths-validation-matrix.md`.

## Evidence summary

| Lane | Status | Notes |
| --- | --- | --- |
| `native-macos` | pass | Focused Phase 2 helper/audit tests passed on the active macOS host |
| `docker-ubuntu` | pass | Compose-based Ubuntu verification now passes end-to-end in real Linux userspace using the supported verification script and the focused Phase 2 test packs |
| `windows-simulated` | pass | Covered by helper/docs/contracts and placeholder-based path examples |
| `windows-native` | deferred | No real Windows host or CI runner used in this phase |

## 1. Native macOS evidence

Focused host-native commands run successfully during the implementation pass.

Validated areas:
- shared helper precedence and user-home VDS default behavior
- `vds_cli` shared env loading behavior
- `audit_orchestrator` config/report/log default behavior
- Phase 124 handoff command-pack portability expectations

Observed result:
- focused Phase 2 host-native test pack passed

## 2. Docker Ubuntu evidence

Compose-based verification command:
- `docker compose -f docker/compose.phase2-verification.yml run --rm phase2-ubuntu-verifier`

Observed result:
- the Ubuntu/Linux lane successfully exercised the mounted worktree in real Linux userspace and exposed real portability issues that were then fixed
- after those fixes, later reruns no longer failed on the original path-layout bugs
- the supported compose-based verification script now passes end-to-end with the focused Linux Phase 2 verification packs
- latest successful Linux results from the supported lane:
  - `vds_cli_common/tests/test_paths.py` + `vds_cli_common/tests/test_env.py`: `15 passed`
  - `audit_orchestrator/tests/test_paths_config_phase2.py` + `audit_orchestrator/tests/unit/scripts/test_verify_phase124_handoff.py`: `4 passed`
  - `audit_orchestrator/tests/test_cli_paths_phase2.py`: `2 passed`

Important findings during verification:
- the first Ubuntu compose runs exposed a real portability bug in `audit_orchestrator/scripts/verify_phase124_handoff.py`
- the script assumed a host-specific workspace layout and monorepo-relative command path posture
- the bug was fixed by resolving workspace roots and script-path prefixes dynamically so the helper works in:
  - monorepo root layout
  - direct `vds-scripts` worktree layout
  - compose-mounted `/workspace` layout
- an additional operational issue appeared when the container tried to reuse the mounted host `.venv`
- the compose verification lane was updated to use `UV_PROJECT_ENVIRONMENT=/tmp/phase2-uv-env` so Linux verification uses a container-local environment instead of mutating or depending on the mounted host environment
- the Docker lane was further updated to use `UV_CACHE_DIR=/tmp/phase2-uv-cache`, `UV_HTTP_TIMEOUT=120`, `UV_LINK_MODE=copy`, and a persistent compose volume for the uv cache so Linux verification is easier to debug and less dependent on repeated cold-start bootstrap
- the supported compose command was narrowed to the focused Phase 2 Linux verification packs so the lane proves the path/config work directly instead of spending most runtime on unrelated full-project dependency setup

Current interpretation:
- this lane now provides a passing `docker-ubuntu` result for the focused Phase 2 portability scope
- the remaining caveat is operational rather than functional: the original full-project audit environment bootstrap was much heavier than needed for the actual Phase 2 path/config assertions
- the supported verification lane now uses the focused real-Linux checks that directly prove the Phase 2 portability behavior

Those fixes are part of the Phase 2 evidence because they were discovered by the Linux verification lane, not by the original host-only test pass.

## 3. Windows-simulated evidence

Current Windows-oriented evidence comes from:
- shared helper/tests that validate override precedence and path/config behavior without assuming POSIX shell-only setup
- docs and references that explicitly document Windows-oriented env/path override usage
- placeholder-based repo-cache/report-root command examples instead of hardcoded POSIX-only examples
- explicit spec/docs language distinguishing simulation from native Windows verification

This lane supports a claim of `windows-simulated`, not `windows-native`.

## 4. Deferred Windows-native evidence

Not executed in this phase.

Required future environments for true Windows-native validation:
- Windows CI runner
- Windows VM
- or an operator-run Windows host with PowerShell/CMD validation evidence

## 5. Live CLI verification refresh (2026-03-24)

A fresh bounded live-verification sweep was rerun from the active Phase 2 worktree using package-direct `uv run --project ...` entrypoints so each CLI was exercised from its owning package environment.

Commands exercised in this refresh included:
- `vds-cli env status`
- `vds-cli audit --json-only doctor profile-availability --profiles zai-openai --mode active`
- `vds-cli elastic --json-only ping`
- `vds-cli jira-cli --json-only projects`
- `vds-cli jira-cli search "project = CBDC ORDER BY updated DESC" --limit 3 --json-only`
- `vds-cli bitbucket-cli --json-only projects`
- `vds-cli bitbucket-cli --json-only repositories WHO --limit 5`
- `vds-cli confluence-cli search --server internal --cql "type=page" --limit 1`
- `vds-cli git list --match "*vds*"`

Observed results:
- `vds-cli env status` succeeded and resolved the shared env file from the active VDS config root
- `vds-cli jira-cli --json-only projects` succeeded and returned authenticated project data
- `vds-cli jira-cli search "project = CBDC ORDER BY updated DESC" --limit 3 --json-only` succeeded as a real authenticated JQL call; in this bounded run it returned `0` issues rather than a transport or auth failure
- `vds-cli bitbucket-cli --json-only projects` succeeded and returned authenticated project data
- `vds-cli bitbucket-cli --json-only repositories WHO --limit 5` succeeded and returned repository data including `vds-scripts` and `vds-skills`
- `vds-cli confluence-cli search --server internal --cql "type=page" --limit 1` succeeded and returned a real page result
- `vds-cli elastic --json-only ping` succeeded in the current runtime and returned a healthy structured response including Kibana connection details
- `vds-cli git list --match "*vds*"` succeeded and listed the expected WHO/insurance VDS repositories from the active manifest routing path
- `vds-cli audit --json-only doctor profile-availability --profiles zai-openai --mode active` still reports `profile_not_found` for the local runtime profiles file rather than exposing a path-contract defect

Current interpretation of the refresh:
- no new maintained Phase 2 path/config regressions were found in the bounded live probes
- the active runtime now proves the friendly `~/.vds` default end to end because `vds-cli`, JIRA, Bitbucket, Confluence, Elastic, and routed Git all executed successfully against the active shared environment on the current Unix-like host
- the remaining observed non-successful probe in this bounded pass is limited to local audit profile readiness rather than a portable-path implementation defect
- this refresh strengthens the closure claim that the maintained path/config work is functioning end to end in real CLI usage, not only in focused test packs

Additional CLI-surface verification after the refresh found and fixed two operator-facing anomalies in the active worktree:
- `vds-subagent-stop-hook --help` originally emitted a `RuntimeWarning: coroutine 'main' was never awaited` because `vds_hooks/src/vds_hooks/scripts/subagent_stop.py` contained a corrupted duplicated tail; the trailing corruption was removed and the help surface now runs cleanly
- `vds-cli mcp-server --help` originally did not emit a usable help surface because the entrypoint lacked explicit help handling; after adding a minimal help path, a missing `sys` import surfaced and was fixed; the command now prints a clean usage/help message

Interpretation of these follow-up fixes:
- they were real CLI-surface defects discovered by the continued live verification sweep rather than path-contract regressions
- both defects are now fixed and reverified in the active Phase 2 worktree
- the later JIRA `search --json-only` inconsistency was also narrowed to CLI option placement, patched so command-local `--json-only` is accepted, and reverified with a real authenticated JQL search call

## Decision

Current Phase 2 work can honestly claim:
- native macOS validation
- Docker-based Ubuntu/Linux validation through the supported compose verification lane
- Windows-oriented simulation/contract validation

Current Phase 2 work must not claim:
- native Windows verification

until a real Windows execution environment is used.
