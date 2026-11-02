"""Lifecycle commands for the canonical git credential helper.

Spec: who-ecosystem-alignment Phase 5 v0.7.0 — FR-23 (vds-cli env lifecycle),
FR-24 (single canonical artifact), AC-23.7 (file modes), AC-23.8 (subprocess
shell=False), AC-24.4/AC-24.5/AC-24.6 (legacy artifact cleanup + signature
check + state migration).

Per FR-25 AC-25.3, this module runs in the vds-scripts venv and freely
reuses third-party + vds-scripts packages. The helper itself
(assets/git-credential-helper.py) has the no-venv constraint, NOT this
module.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
from importlib import resources
from pathlib import Path
from typing import NamedTuple

INSTALLED_BINARY_NAME = "git-credential-vds"
HELPER_SUBDIR = "bin"
VDS_DIR = ".vds"
COOLDOWN_FILE = ".git-credential-helper-cooldown.json"
LEGACY_STATE_FILE = ".git_helper_state.json"
LEGACY_HELPER_FILENAMES = (
    "git_credential_helper.py",
    "git_credential_helper.py.bak",
)
LEGACY_TMP_HELPER = Path("/tmp/git_credential_helper_v2.py")

INSTALLED_MODE = 0o700
DIR_MODE = 0o700
STATE_MODE = 0o600

SIGNATURE_MARKERS = ("VDS_USERNAME", "def cmd_get")


class InstallResult(NamedTuple):
    target: Path
    removed: list[Path]
    preserved: list[Path]
    migrated_state: Path | None
    probe_ok: bool


class VerifyCheck(NamedTuple):
    name: str
    detail: str
    ok: bool


def _home() -> Path:
    return Path.home()


def _installed_path() -> Path:
    return _home() / VDS_DIR / HELPER_SUBDIR / INSTALLED_BINARY_NAME


def _state_path() -> Path:
    return _home() / VDS_DIR / COOLDOWN_FILE


def _legacy_state_path() -> Path:
    return _home() / VDS_DIR / LEGACY_STATE_FILE


def _read_asset() -> str:
    """Read the bundled canonical helper source per AC-23.2(a)."""
    return resources.files("vds_cli").joinpath("assets/git-credential-helper.py").read_text(encoding="utf-8")


def _signature_match(content: str) -> bool:
    """AC-24.6: content matches pre-FR-24 helper signature."""
    return all(marker in content for marker in SIGNATURE_MARKERS)


def _cleanup_legacy_artifacts(*, force: bool = False) -> tuple[list[Path], list[Path]]:
    """Remove pre-FR-24 file artifacts. Returns (removed, preserved)."""
    removed: list[Path] = []
    preserved: list[Path] = []
    candidates: list[Path] = [_home() / VDS_DIR / name for name in LEGACY_HELPER_FILENAMES]
    candidates.append(LEGACY_TMP_HELPER)
    for path in candidates:
        if not path.exists():
            continue
        if not force:
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                preserved.append(path)
                continue
            if not _signature_match(content):
                preserved.append(path)
                continue
        try:
            path.unlink()
            removed.append(path)
        except OSError:
            preserved.append(path)
    return removed, preserved


def _migrate_legacy_state() -> Path | None:
    """AC-24.5: migrate legacy state file if present and new path is free."""
    legacy = _legacy_state_path()
    new = _state_path()
    if not legacy.exists():
        return None
    if new.exists():
        with contextlib.suppress(OSError):
            legacy.unlink()
        return None
    try:
        os.rename(str(legacy), str(new))
        os.chmod(new, STATE_MODE)
        return new
    except OSError:
        return None


def _self_probe() -> bool:
    """AC-23.2(d): stdin-sim allowlist-miss should yield no output, exit 0."""
    target = _installed_path()
    if not target.exists():
        return False
    try:
        result = subprocess.run(
            [str(target.resolve()), "get"],
            input="protocol=https\nhost=allowlist-miss-probe.example\n\n",
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout == ""


def install(*, force: bool = False) -> InstallResult:
    """Install canonical git credential helper.

    AC-23.2(a-e) + AC-23.7 + AC-23.8 + AC-24.4 + AC-24.5 + AC-24.6.
    """
    target = _installed_path()
    target.parent.mkdir(mode=DIR_MODE, parents=True, exist_ok=True)
    os.chmod(target.parent, DIR_MODE)

    asset_content = _read_asset()
    target.write_text(asset_content, encoding="utf-8")
    os.chmod(target, INSTALLED_MODE)

    abs_path = str(target.resolve())
    subprocess.run(
        ["git", "config", "--global", "credential.helper", abs_path],
        check=True,
        shell=False,
    )

    removed, preserved = _cleanup_legacy_artifacts(force=force)
    migrated = _migrate_legacy_state()
    probe_ok = _self_probe()

    return InstallResult(
        target=target,
        removed=removed,
        preserved=preserved,
        migrated_state=migrated,
        probe_ok=probe_ok,
    )


def verify(*, reset_cooldown: bool = False) -> tuple[int, list[VerifyCheck]]:
    """Verify install state. Returns (exit_code, checks). exit 0 iff all pass."""
    checks: list[VerifyCheck] = []
    target = _installed_path()

    file_ok = target.exists()
    checks.append(VerifyCheck("Helper file", str(target), file_ok))

    exec_ok = file_ok and (target.stat().st_mode & 0o111) != 0
    checks.append(
        VerifyCheck(
            "Executable",
            "mode +x" if exec_ok else "missing +x bits",
            exec_ok,
        )
    )

    abs_path = str(target.resolve()) if file_ok else ""
    try:
        result = subprocess.run(
            ["git", "config", "--global", "--get", "credential.helper"],
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
        configured = result.stdout.strip() if result.returncode == 0 else ""
    except OSError:
        configured = ""
    config_ok = bool(configured) and (configured == abs_path or configured.endswith(INSTALLED_BINARY_NAME))
    checks.append(VerifyCheck("Git config", configured or "<unset>", config_ok))

    if reset_cooldown:
        state = _state_path()
        try:
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text(
                json.dumps({"failures": [], "cooldown_until": 0}),
                encoding="utf-8",
            )
            os.chmod(state, STATE_MODE)
            checks.append(VerifyCheck("Cooldown reset", "state cleared", True))
        except OSError as exc:
            checks.append(VerifyCheck("Cooldown reset", f"failed: {exc}", False))

    exit_code = 0 if all(check.ok for check in checks) else 1
    return exit_code, checks


def remove(*, purge: bool = False) -> dict:
    """Uninstall helper. Idempotent — safe when nothing is installed (AC-23.4)."""
    target = _installed_path()
    deleted_binary = False
    if target.exists():
        try:
            target.unlink()
            deleted_binary = True
        except OSError:
            pass

    with contextlib.suppress(OSError):
        subprocess.run(
            ["git", "config", "--global", "--unset", "credential.helper"],
            capture_output=True,
            check=False,
            shell=False,
        )

    deleted_state = False
    if purge:
        state = _state_path()
        if state.exists():
            try:
                state.unlink()
                deleted_state = True
            except OSError:
                pass

    return {"deleted_binary": deleted_binary, "deleted_state": deleted_state}


def status() -> tuple[str, str]:
    """For doctor command. Returns (status_word, remediation_hint)."""
    target = _installed_path()
    if not target.exists():
        return "missing", "run `vds-cli env install-git-helper`"
    if (target.stat().st_mode & 0o111) == 0:
        return "broken", "run `vds-cli env install-git-helper` to repair file mode"
    return "installed", ""


__all__ = [
    "DIR_MODE",
    "INSTALLED_BINARY_NAME",
    "INSTALLED_MODE",
    "STATE_MODE",
    "InstallResult",
    "VerifyCheck",
    "install",
    "remove",
    "status",
    "verify",
]
