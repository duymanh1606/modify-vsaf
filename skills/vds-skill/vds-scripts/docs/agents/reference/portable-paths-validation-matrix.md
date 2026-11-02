<!-- diátaxis: reference -->

# Portable path/config validation matrix

This reference turns the Phase 2 portability spec into an executable validation posture.
It records what should be validated natively on the host, what can be validated in
Docker-based Ubuntu/Linux, and what must remain Windows-oriented simulation unless a
real Windows environment is available.

## Verification lanes

| Lane | Purpose | Environment | Evidence type |
| --- | --- | --- | --- |
| macOS native | Confirm the host development environment uses the shared helper and respects overrides | Current macOS host | Focused tests + manual CLI smoke |
| Ubuntu/Linux via Docker | Confirm the helper and focused tests behave in real Linux userspace | Docker container on current host | Scripted test run |
| Windows-oriented simulation | Confirm Windows path/env semantics are modeled correctly in code/docs/tests | Non-Windows host | Contract tests + documented examples |
| Windows native (future) | Confirm behavior on real Windows filesystem/shell/env | Real Windows host or CI runner | Deferred unless available |

## Current Phase 2 evidence contract

When reporting portability status, classify each result as one of:

- `native-macos`
- `docker-ubuntu`
- `windows-simulated`
- `windows-native`
- `deferred`

Do not collapse these into one generic “cross-platform verified” claim.

## Recommended checks by lane

### 1. macOS native

Run on the active development host.

Recommended checks:
- `uv run --project vds_cli_common pytest vds_cli_common/tests/test_paths.py vds_cli_common/tests/test_env.py`
- `PYTHONPATH=audit_orchestrator/src:vds_cli_common/src:bitbucket_orchestrator/src:confluence_orchestrator/src:sonarqube_orchestrator/src:google_sheets_orchestrator/src:excel_orchestrator/src:git_orchestrator/src:vds_cli/src:spec_orchestrator/src ./scripts/worktree_uv.sh run --project audit_orchestrator pytest audit_orchestrator/tests/test_paths_config_phase2.py audit_orchestrator/tests/test_cli_paths_phase2.py audit_orchestrator/tests/unit/scripts/test_verify_phase124_handoff.py`
- optional smoke: `./scripts/worktree_uv.sh run --project vds_cli vds-cli env status`

Expected evidence:
- shared helper tests pass
- audit orchestrator focused path/log/report tests pass
- no host-specific absolute paths are required for the focused path/config workflow

### 2. Ubuntu/Linux via Docker

Use a Linux container because it exercises real Linux path behavior while reusing the mounted worktree.

Recommended command:
- `./scripts/verification/phase2_portable_paths_ubuntu_docker.sh`
- underlying compose asset: `docker/compose.phase2-verification.yml`

Expected evidence:
- Linux container test run passes through the supported script entrypoint
- explicit `VDS_CONFIG_DIR`, `VDS_CACHE_DIR`, `VDS_LOG_DIR`, and `VDS_ENV_FILE` overrides work
- the container uses its own verification environment path rather than depending on the mounted host `.venv`
- the Docker lane uses an explicit container-local uv cache and verbose/frozen setup for reproducible troubleshooting
- no hidden dependency on macOS-only paths remains in the focused verification set

Limits:
- this is Linux verification, not Windows verification
- Docker Desktop mount behavior is still host-mediated and should not be confused with a fully independent machine

### 3. Windows-oriented simulation / contract validation

Use this lane on macOS/Linux hosts when no real Windows runner is available.

Recommended evidence:
- focused unit tests around helper precedence and path handling
- documented Windows override examples in `portable-paths-and-config.md`
- command/reference surfaces that avoid hardcoded POSIX-only assumptions
- placeholder-based repo-cache/report-root examples instead of claiming native Windows execution

Expected evidence:
- Windows-specific separators and override semantics are accounted for in docs and helper contract
- path/env model does not assume POSIX shell expansion as the only setup path

Limits:
- this is not proof of native PowerShell/CMD behavior
- this is not proof of native Windows filesystem edge cases

### 4. Windows native (future lane)

Use only when a real Windows host or CI runner is available.

Recommended future checks:
- run the focused Phase 2 pytest suite on Windows
- verify `VDS_CONFIG_DIR`, `VDS_CACHE_DIR`, `VDS_LOG_DIR`, `VDS_ENV_FILE` from PowerShell
- verify path rendering and shell examples against real Windows defaults

Status for current host-driven Phase 2 work:
- `deferred`

## Validation matrix

| Check | macOS native | Docker Ubuntu | Windows simulated | Windows native |
| --- | --- | --- | --- | --- |
| Shared helper precedence tests | Yes | Yes | Yes | Deferred |
| Audit report/log default tests | Yes | Yes | Yes | Deferred |
| CLI/bootstrap smoke | Yes | Optional | Docs/examples only | Deferred |
| Native filesystem semantics | Yes | Yes | No | Deferred |
| Native shell semantics | Yes | Yes (bash) | No | Deferred |
| PowerShell/CMD semantics | No | No | Partial docs/contracts | Deferred |

## Reporting template

Use this structure when recording Phase 2 evidence:

- `native-macos`: what commands/tests ran, pass/fail, notes
- `docker-ubuntu`: image used, commands/tests ran, pass/fail, notes
- `windows-simulated`: tests/docs/contracts exercised, pass/fail, notes
- `windows-native`: `deferred` unless a real environment was used

Current implementation evidence:
- `docs/phases/phase2-portable-paths/verification-evidence-2026-03-23.md`

## Decision rule for Phase 2 closure

Phase 2 can claim:
- native macOS validation
- Docker-based Ubuntu/Linux validation
- Windows-oriented simulation/contract validation

Phase 2 should **not** claim:
- native Windows verification

unless an actual Windows host/CI lane produced evidence.
