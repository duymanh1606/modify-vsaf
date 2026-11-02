"""Unit tests for macOS LaunchAgent service manager."""

import plistlib
import sys
from pathlib import Path

import pytest
from vds_cli.sync_service import (
    LABEL,
    ServiceError,
    ServicePaths,
    build_plist,
    status,
)


@pytest.fixture
def mock_paths(tmp_path: Path) -> ServicePaths:
    """Build mock ServicePaths for testing."""
    return ServicePaths(
        plist=tmp_path / "Library" / "LaunchAgents" / f"{LABEL}.plist",
        stdout_log=tmp_path / ".vds" / "logs" / "watch-agents.stdout.log",
        stderr_log=tmp_path / ".vds" / "logs" / "watch-agents.stderr.log",
        vds_cli_bin=Path("/usr/local/bin/vds-cli"),
        project_dir=tmp_path / "vds_cli",
        repo_root=tmp_path / "repo",
    )


def test_build_plist_contains_required_keys(mock_paths: ServicePaths) -> None:
    """Plist must contain all required LaunchAgent keys."""
    plist = build_plist(mock_paths)

    assert plist["Label"] == LABEL
    assert plist["RunAtLoad"] is True
    # FR-11: ThrottleInterval aligns with reconcile_interval_seconds (300s) in docs_sync.py
    assert plist["ThrottleInterval"] == 300
    assert isinstance(plist["ProgramArguments"], list)
    assert plist["WorkingDirectory"] == str(mock_paths.repo_root)
    assert plist["StandardOutPath"] == str(mock_paths.stdout_log)
    assert plist["StandardErrorPath"] == str(mock_paths.stderr_log)


def test_build_plist_program_arguments_invoke_vds_cli_directly(mock_paths: ServicePaths) -> None:
    """ProgramArguments must invoke the vds-cli binary directly (Phase 173 FR-11).

    No ``uv run --project`` wrapper — that would trigger a workspace-wide lock
    resolve on every daemon start and drag URL-pinned wheels from unrelated
    workspace members into the critical path.
    """
    plist = build_plist(mock_paths)
    args = plist["ProgramArguments"]

    # Shape: [<vds-cli>, "docs", "watch-agents", "--repo-root", <repo_root>]
    assert args[0] == str(mock_paths.vds_cli_bin)
    assert "run" not in args, "FR-11: no uv wrapper in ProgramArguments"
    assert "--project" not in args, "FR-11: no uv wrapper in ProgramArguments"
    assert "docs" in args
    assert "watch-agents" in args
    assert "--repo-root" in args
    assert str(mock_paths.repo_root) in args


def test_build_plist_keep_alive_restarts_on_failure(mock_paths: ServicePaths) -> None:
    """KeepAlive must restart only on non-zero exit (not on clean shutdown)."""
    plist = build_plist(mock_paths)

    assert "KeepAlive" in plist
    assert plist["KeepAlive"]["SuccessfulExit"] is False


def test_build_plist_serializes_to_valid_plist_xml(mock_paths: ServicePaths) -> None:
    """Generated plist must be valid Apple plist XML."""
    plist = build_plist(mock_paths)
    xml_bytes = plistlib.dumps(plist)
    roundtrip = plistlib.loads(xml_bytes)
    assert roundtrip["Label"] == LABEL
    assert roundtrip["ProgramArguments"] == plist["ProgramArguments"]


def test_build_plist_environment_includes_vds_cli_parent_on_path(mock_paths: ServicePaths) -> None:
    """PATH in EnvironmentVariables must include the vds-cli binary's parent directory.

    The daemon shells out to ``git`` etc. via subprocess — PATH must contain the
    tool-installed bin dir so that relative binary references still resolve.
    """
    plist = build_plist(mock_paths)
    env = plist["EnvironmentVariables"]
    assert str(mock_paths.vds_cli_bin.parent) in env["PATH"]


def test_service_status_not_installed(tmp_path: Path, monkeypatch) -> None:
    """Status should report not installed when plist does not exist."""
    monkeypatch.setattr(
        "vds_cli.sync_service.resolve_paths",
        lambda **kw: ServicePaths(
            plist=tmp_path / "nonexistent.plist",
            stdout_log=tmp_path / "stdout.log",
            stderr_log=tmp_path / "stderr.log",
            vds_cli_bin=Path("/usr/local/bin/vds-cli"),
            project_dir=tmp_path,
            repo_root=tmp_path,
        ),
    )

    if sys.platform != "darwin":
        pytest.skip("LaunchAgent status only works on macOS")

    st = status()
    assert st.installed is False
    assert st.running is False
    assert st.pid is None


def test_service_status_installed_but_stopped(tmp_path: Path, monkeypatch) -> None:
    """Status should report installed but stopped when plist exists but process is not running."""
    plist_path = tmp_path / f"{LABEL}.plist"
    plist_path.write_text("<plist/>", encoding="utf-8")

    monkeypatch.setattr(
        "vds_cli.sync_service.resolve_paths",
        lambda **kw: ServicePaths(
            plist=plist_path,
            stdout_log=tmp_path / "stdout.log",
            stderr_log=tmp_path / "stderr.log",
            vds_cli_bin=Path("/usr/local/bin/vds-cli"),
            project_dir=tmp_path,
            repo_root=tmp_path,
        ),
    )

    def _mock_query():
        return False, None, 1

    monkeypatch.setattr("vds_cli.sync_service._query_launchctl", _mock_query)

    if sys.platform != "darwin":
        pytest.skip("LaunchAgent status only works on macOS")

    st = status()
    assert st.installed is True
    assert st.running is False
    assert st.exit_code == 1


def test_install_rejects_non_darwin(monkeypatch) -> None:
    """Install must reject non-macOS platforms."""
    monkeypatch.setattr("vds_cli.sync_service.sys.platform", "linux")

    from vds_cli.sync_service import install

    with pytest.raises(ServiceError, match="only supported on macOS"):
        install()


def test_uninstall_rejects_non_darwin(monkeypatch) -> None:
    """Uninstall must reject non-macOS platforms."""
    monkeypatch.setattr("vds_cli.sync_service.sys.platform", "linux")

    from vds_cli.sync_service import uninstall

    with pytest.raises(ServiceError, match="only supported on macOS"):
        uninstall()


def test_label_follows_reverse_dns_convention() -> None:
    """Label must follow reverse-DNS convention for macOS LaunchAgents."""
    parts = LABEL.split(".")
    assert len(parts) >= 3
    assert parts[0] == "com"
