"""macOS LaunchAgent service manager for watch-agents sync daemon."""

from __future__ import annotations

import contextlib
import os
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from vds_cli_common.paths import get_vds_log_root

LABEL = "com.vds.watch-agents"


@dataclass(frozen=True)
class ServicePaths:
    """Resolved paths for the LaunchAgent service."""

    plist: Path
    stdout_log: Path
    stderr_log: Path
    vds_cli_bin: Path
    project_dir: Path
    repo_root: Path


class ServiceError(RuntimeError):
    """Error during LaunchAgent service management."""


def _find_vds_cli() -> Path:
    """Locate the ``vds-cli`` binary on PATH or standard install locations.

    Prefers the PATH-resolved, tool-installed binary (Phase 173 FR-11) so the
    daemon does NOT trigger a workspace-wide ``uv run --project`` resolve on
    every start. The workspace resolve drags URL-pinned wheels from unrelated
    members (e.g. ``en-core-web-sm`` via ``memory_orchestrator`` and
    ``pdf_orchestrator``) into the critical path and times out on
    LAN-restricted networks.

    Install with: ``uv tool install --editable ~/.claude/vds-scripts/vds_cli``.
    """
    which = shutil.which("vds-cli")
    if which:
        return Path(which).resolve()
    for candidate in (
        Path.home() / ".local" / "bin" / "vds-cli",
        Path("/usr/local/bin/vds-cli"),
        Path("/opt/homebrew/bin/vds-cli"),
    ):
        if candidate.exists():
            return candidate.resolve()
    raise ServiceError(
        "Cannot find 'vds-cli' binary. Install with: uv tool install --editable ~/.claude/vds-scripts/vds_cli"
    )


def _resolve_project_dir() -> Path:
    """Resolve the vds_cli project directory from this module's location."""
    # This file lives at: <project_dir>/src/vds_cli/sync_service.py
    src_dir = Path(__file__).resolve().parent.parent  # src/
    project_dir = src_dir.parent  # vds_cli/
    if not (project_dir / "pyproject.toml").exists():
        raise ServiceError(f"Cannot resolve vds_cli project dir from {__file__}")
    return project_dir


def _resolve_repo_root(project_dir: Path) -> Path:
    """Walk up from project dir to find repo root (contains AGENTS.md)."""
    candidate = project_dir
    for _ in range(10):
        if (candidate / "AGENTS.md").exists():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    raise ServiceError(f"Cannot find repo root (AGENTS.md) walking up from {project_dir}")


def resolve_paths(*, repo_root: Path | None = None) -> ServicePaths:
    """Build all service-related paths."""
    vds_cli_bin = _find_vds_cli()
    project_dir = _resolve_project_dir()
    if repo_root is None:
        repo_root = _resolve_repo_root(project_dir)

    log_dir = get_vds_log_root()
    return ServicePaths(
        plist=Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist",
        stdout_log=log_dir / "watch-agents.stdout.log",
        stderr_log=log_dir / "watch-agents.stderr.log",
        vds_cli_bin=vds_cli_bin,
        project_dir=project_dir,
        repo_root=repo_root,
    )


def build_plist(paths: ServicePaths) -> dict:
    """Build the LaunchAgent plist dictionary.

    Invokes the tool-installed ``vds-cli`` binary directly (Phase 173 FR-11)
    instead of ``uv run --project``. This avoids workspace-wide lock resolution
    on every restart — a workspace resolve pulls URL-pinned wheels (e.g.
    ``en-core-web-sm``) from unrelated members and blows up on LAN-restricted
    networks, which is what caused the ``SyncFileLock`` flap storm observed
    before FR-11 alignment.

    ``ThrottleInterval`` is pinned to ``reconcile_interval_seconds`` (300s) in
    ``docs_sync.py`` — restart cadence matches the inner loop's cadence, so a
    restart storm cannot outpace a single reconcile cycle.
    """
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(paths.vds_cli_bin),
            "docs",
            "watch-agents",
            "--repo-root",
            str(paths.repo_root),
        ],
        "WorkingDirectory": str(paths.repo_root),
        "RunAtLoad": True,
        "KeepAlive": {
            "SuccessfulExit": False,  # restart on non-zero exit
        },
        "ThrottleInterval": 300,  # aligns with reconcile_interval_seconds in docs_sync.py
        "StandardOutPath": str(paths.stdout_log),
        "StandardErrorPath": str(paths.stderr_log),
        "EnvironmentVariables": {
            "PATH": f"{paths.vds_cli_bin.parent}:/usr/local/bin:/usr/bin:/bin",
            "HOME": str(Path.home()),
        },
    }


def install(*, repo_root: Path | None = None, force: bool = False) -> ServicePaths:
    """Install and load the LaunchAgent.

    Returns the resolved paths for caller diagnostics.
    """
    if sys.platform != "darwin":
        raise ServiceError("LaunchAgent install is only supported on macOS.")

    paths = resolve_paths(repo_root=repo_root)

    if paths.plist.exists() and not force:
        raise ServiceError(f"Service already installed at {paths.plist}. Use --force to overwrite.")

    # Unload existing if overwriting
    if paths.plist.exists():
        _launchctl("bootout", ignore_errors=True)

    # Ensure directories exist
    paths.plist.parent.mkdir(parents=True, exist_ok=True)
    paths.stdout_log.parent.mkdir(parents=True, exist_ok=True)

    # Write plist
    plist_data = build_plist(paths)
    with open(paths.plist, "wb") as fh:
        plistlib.dump(plist_data, fh)

    # Load service
    _launchctl("bootstrap")

    return paths


def uninstall() -> Path:
    """Unload and remove the LaunchAgent. Returns the plist path that was removed."""
    if sys.platform != "darwin":
        raise ServiceError("LaunchAgent uninstall is only supported on macOS.")

    paths = resolve_paths()

    if not paths.plist.exists():
        raise ServiceError(f"Service not installed (no plist at {paths.plist}).")

    _launchctl("bootout", ignore_errors=True)
    paths.plist.unlink(missing_ok=True)

    return paths.plist


@dataclass(frozen=True)
class ServiceStatus:
    """Diagnostic snapshot of the LaunchAgent service."""

    installed: bool
    plist_path: Path
    running: bool
    pid: int | None
    exit_code: int | None
    label: str = LABEL


def status() -> ServiceStatus:
    """Query the current service state."""
    if sys.platform != "darwin":
        raise ServiceError("LaunchAgent status is only supported on macOS.")

    paths = resolve_paths()
    installed = paths.plist.exists()

    if not installed:
        return ServiceStatus(
            installed=False,
            plist_path=paths.plist,
            running=False,
            pid=None,
            exit_code=None,
        )

    running, pid, exit_code = _query_launchctl()
    return ServiceStatus(
        installed=True,
        plist_path=paths.plist,
        running=running,
        pid=pid,
        exit_code=exit_code,
    )


def _launchctl(action: str, *, ignore_errors: bool = False) -> None:
    """Run launchctl bootstrap/bootout for the user domain."""
    uid = os.getuid()
    domain_target = f"gui/{uid}"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"

    if action == "bootstrap":
        cmd = ["launchctl", "bootstrap", domain_target, str(plist_path)]
    elif action == "bootout":
        cmd = ["launchctl", "bootout", f"{domain_target}/{LABEL}"]
    else:
        raise ServiceError(f"Unknown launchctl action: {action}")

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        if not ignore_errors:
            raise ServiceError(f"launchctl {action} failed (exit {exc.returncode}): {exc.stderr.strip()}") from exc


def _query_launchctl() -> tuple[bool, int | None, int | None]:
    """Query launchctl for service state. Returns (running, pid, exit_code)."""
    uid = os.getuid()
    service_target = f"gui/{uid}/{LABEL}"

    try:
        result = subprocess.run(
            ["launchctl", "print", service_target],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, None, None

    if result.returncode != 0:
        return False, None, None

    output = result.stdout
    pid: int | None = None
    exit_code: int | None = None
    running = False

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("pid = "):
            try:
                pid = int(stripped.split("=", 1)[1].strip())
                running = True
            except ValueError:
                pass
        elif stripped.startswith("last exit code ="):
            with contextlib.suppress(ValueError):
                exit_code = int(stripped.split("=", 1)[1].strip())

    return running, pid, exit_code
