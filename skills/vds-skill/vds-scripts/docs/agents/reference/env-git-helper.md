<!-- diátaxis: reference -->

# Env Git Helper Reference

> Canonical git credential helper (`git-credential-vds`) — install, verify, lifecycle.

## Summary

| Property | Value |
|----------|-------|
| Binary name | `git-credential-vds` |
| Install path | `~/.vds/bin/git-credential-vds` |
| State file | `~/.vds/.git-credential-helper-cooldown.json` |
| Legacy state | `~/.vds/.git_helper_state.json` |
| Source module | `vds_cli.env_git_helper` |
| Asset source | `vds_cli/assets/git-credential-helper.py` |

## Table of Contents

- [Quick Reference](#quick-reference)
- [Installation](#installation)
- [Verification](#verification)
- [Removal](#removal)
- [Status](#status)
- [State Management](#state-management)
- [Environment](#environment)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Spec References](#spec-references)

## Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `vds-cli env install-git-helper` | Install canonical helper and clean legacy artifacts | `vds-cli env install-git-helper` |
| `vds-cli env install-git-helper --force` | Force install, bypass signature check | `vds-cli env install-git-helper --force` |
| `vds-cli env verify-git-helper` | Verify installed state and git config | `vds-cli env verify-git-helper` |
| `vds-cli env verify-git-helper --reset-cooldown` | Verify and clear cooldown state | `vds-cli env verify-git-helper --reset-cooldown` |
| `vds-cli env remove-git-helper` | Uninstall helper and unset git config | `vds-cli env remove-git-helper` |
| `vds-cli env remove-git-helper --purge` | Uninstall and delete cooldown state file | `vds-cli env remove-git-helper --purge` |
| `vds-cli env status` | Show env and helper status | `vds-cli env status` |
| `vds-cli env load` | Load shared VDS environment from `~/.vds/.env` | `vds-cli env load` |
| `vds-cli doctor` | Full diagnostic including helper status | `vds-cli doctor` |

## Installation

```bash
vds-cli env install-git-helper
```

Installs the canonical git credential helper from the bundled asset
`vds_cli/assets/git-credential-helper.py`.

**Actions performed:**

1. Creates `~/.vds/bin/` with mode `0o700` (AC-23.7).
2. Writes the helper to `~/.vds/bin/git-credential-vds` with mode `0o700` (AC-23.7).
3. Runs `git config --global credential.helper <absolute-path>` with `shell=False` (AC-23.8).
4. Removes legacy pre-FR-24 artifacts after signature verification (AC-24.4 / AC-24.6).
5. Migrates legacy state file if present and the new path is free (AC-24.5).
6. Runs a self-probe: simulates an allowlist-miss `get` request and expects exit `0` with no output (AC-23.2(d)).

**Flags:**

- `--force`: Override the AC-24.6 signature check and remove legacy artifacts unconditionally.

**Result fields:**

| Field | Meaning |
|-------|---------|
| `target` | Path to installed binary |
| `removed` | Legacy artifacts deleted |
| `preserved` | Legacy artifacts kept (signature mismatch) |
| `migrated_state` | New state file path if migration occurred |
| `probe_ok` | Self-probe passed |

## Verification

```bash
vds-cli env verify-git-helper
```

Returns exit code `0` if all checks pass, `1` otherwise.

**Checks performed:**

| Check | Detail |
|-------|--------|
| Helper file | `~/.vds/bin/git-credential-vds` exists |
| Executable | Mode has `+x` bits (verified via `st_mode & 0o111`) |
| Git config | `credential.helper` is set to the installed absolute path or ends with `git-credential-vds` |
| Cooldown reset | Only when `--reset-cooldown` is passed |

**Flags:**

- `--reset-cooldown`: Truncate the cooldown state file to `{"failures": [], "cooldown_until": 0}` and set mode `0o600`.

## Removal

```bash
vds-cli env remove-git-helper
```

Idempotent — safe when nothing is installed (AC-23.4).

**Actions performed:**

1. Deletes `~/.vds/bin/git-credential-vds` if it exists.
2. Unsets `git config --global credential.helper` (best-effort, no failure on missing config).
3. With `--purge`, also deletes the cooldown state file.

**Flags:**

- `--purge`: Also delete `~/.vds/.git-credential-helper-cooldown.json`.

**Result fields:**

| Field | Meaning |
|-------|---------|
| `deleted_binary` | Binary was present and removed |
| `deleted_state` | State file was present and removed (only with `--purge`) |

## Status

There is no dedicated CLI subcommand for helper status. The helper state is surfaced through:

- `vds-cli env status` — shows "Git credential helper: ✅ Installed" or missing/broken.
- `vds-cli doctor` — includes helper status in the diagnostic table.

**States:**

| State | Meaning | Remediation |
|-------|---------|-------------|
| `installed` | Binary exists and is executable | None |
| `missing` | Binary not found | Run `vds-cli env install-git-helper` |
| `broken` | Binary exists but lacks executable bits | Re-run `vds-cli env install-git-helper` to repair mode |

## State Management

**Current state file:** `~/.vds/.git-credential-helper-cooldown.json`

The helper itself (not the installer) reads and writes this file to implement cooldown/lockout prevention (FR-21). The file is human-inspectable JSON with keys `failures` and `cooldown_until`. Mode is `0o600`.

**Legacy migration (AC-24.5):**

- Legacy path: `~/.vds/.git_helper_state.json`
- Migration occurs during `install()` only if the new path does not already exist.
- If the new path already exists, the legacy file is deleted (best-effort) and migration is skipped.

**Legacy artifact cleanup (AC-24.4 / AC-24.6):**

During install, the following pre-FR-24 artifacts are inspected and removed if their content matches the signature (`VDS_USERNAME` and `def cmd_get`):

- `~/.vds/git_credential_helper.py`
- `~/.vds/git_credential_helper.py.bak`
- `/tmp/git_credential_helper_v2.py`

Files that do not match the signature are preserved with a warning unless `--force` is used.

## Environment

| Variable / Constant | Default | Purpose |
|---------------------|---------|---------|
| `VDS_DIR` | `.vds` | Directory name under `$HOME` for VDS state |
| `INSTALLED_BINARY_NAME` | `git-credential-vds` | Name of the installed binary |
| `SIGNATURE_MARKERS` | `("VDS_USERNAME", "def cmd_get")` | Markers for legacy content verification |

The installer uses these module-level mode constants:

- `INSTALLED_MODE = 0o700`
- `DIR_MODE = 0o700`
- `STATE_MODE = 0o600`

## Security

| AC | Requirement | Implementation |
|----|-------------|----------------|
| AC-23.2(a) | Bundle canonical helper from asset | `resources.files("vds_cli").joinpath("assets/git-credential-helper.py")` |
| AC-23.2(d) | Self-probe on install | Allowlist-miss `get` → expects exit `0` and empty stdout |
| AC-23.7 | File modes | Binary `0o700`, parent dir `0o700`, state file `0o600` |
| AC-23.8 | Subprocess safety | All `subprocess.run` calls use `shell=False` with list args |
| AC-24.4 | Legacy artifact cleanup | Installer removes known pre-FR-24 filenames after signature check |
| AC-24.5 | State migration | Legacy `~/.vds/.git_helper_state.json` → new cooldown JSON path |
| AC-24.6 | Signature check | Legacy files are preserved if they do not contain both `VDS_USERNAME` and `def cmd_get` |

Additional runtime security properties of the helper asset itself:

- AC-20.5: Emits ONLY `username=` and `password=` lines to stdout; no stderr except the AC-21.6 cooldown countdown carve-out.
- AC-21.7: State file is written with mode `0o600`.
- AC-25.1: The helper uses stdlib-only imports so it can run when git invokes it outside the vds-scripts venv.

## Troubleshooting

**Install fails with permission error**
→ Check that `$HOME` is writable and that `~/.vds` is not owned by root.

**Verify fails on "Executable"**
→ The binary may have lost its mode bits. Re-run `vds-cli env install-git-helper`.

**Verify fails on "Git config"**
→ The `credential.helper` global config may point to a different path. Run install again or manually run `git config --global credential.helper ~/.vds/bin/git-credential-vds`.

**Self-probe fails during install**
→ The probe simulates an allowlist-miss (host not in `bitbucket.digital.vn` allowlist) and expects exit `0` with no output. If it fails, check that the binary was written correctly and is executable.

**Legacy state not migrated**
→ Migration only runs if the new state file `~/.vds/.git-credential-helper-cooldown.json` does not already exist. If it exists, the legacy file is deleted instead.

**Binary not invoked by git**
→ Ensure `git config --global credential.helper` points to the absolute path of `~/.vds/bin/git-credential-vds`. The installer sets this automatically.

## Spec References

- who-ecosystem-alignment Phase 5 v0.7.0 — FR-23 (env lifecycle), FR-24 (single canonical artifact), FR-25 (logic non-overlap policy)
- FR-20 / FR-21: Host-filtered emission and lockout-prevention cooldown state file (implemented in the helper asset)
- TSK-5.27: Lifecycle test coverage in `vds_cli/tests/test_env_git_helper_lifecycle.py`
