from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from vds_cli_common.env import (
    DEFAULT_AUDIT_ENV_DEFAULTS,
    ensure_shared_env,
    load_shared_env,
    render_shared_env_exports,
)
from vds_cli_common.paths import get_shared_env_path


def _write_env(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _worktree_uv_script() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "worktree_uv.sh"


def test_load_shared_env_first_file_wins_when_keys_overlap(tmp_path: Path, monkeypatch) -> None:
    primary = tmp_path / "primary.env"
    fallback = tmp_path / "fallback.env"
    _write_env(primary, "TOKEN=from-primary\nPRIMARY_ONLY=1\n")
    _write_env(fallback, "TOKEN=from-fallback\nFALLBACK_ONLY=1\n")

    monkeypatch.delenv("TOKEN", raising=False)
    monkeypatch.delenv("PRIMARY_ONLY", raising=False)
    monkeypatch.delenv("FALLBACK_ONLY", raising=False)

    merged = load_shared_env(path=primary, extra_paths=(fallback,))

    assert merged["TOKEN"] == "from-primary"
    assert merged["PRIMARY_ONLY"] == "1"
    assert merged["FALLBACK_ONLY"] == "1"
    assert "TOKEN" in merged
    assert "PRIMARY_ONLY" in merged
    assert "FALLBACK_ONLY" in merged


def test_load_shared_env_does_not_override_existing_environ_by_default(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / "shared.env"
    _write_env(env_file, "TOKEN=from-file\n")

    monkeypatch.setenv("TOKEN", "from-shell")
    load_shared_env(path=env_file)

    assert os.environ["TOKEN"] == "from-shell"


def test_load_shared_env_override_true_updates_existing_environ(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / "shared.env"
    _write_env(env_file, "TOKEN=from-file\n")

    monkeypatch.setenv("TOKEN", "from-shell")
    load_shared_env(path=env_file, override=True)

    assert os.environ["TOKEN"] == "from-file"


def test_ensure_shared_env_creates_file_with_required_defaults(tmp_path: Path) -> None:
    env_file = tmp_path / ".vds" / ".env"
    created = ensure_shared_env(path=env_file)

    assert created == env_file
    content = env_file.read_text(encoding="utf-8")
    for key, value in DEFAULT_AUDIT_ENV_DEFAULTS:
        assert f"{key}={value}" in content


def test_ensure_shared_env_appends_missing_defaults_without_overwriting(tmp_path: Path) -> None:
    env_file = tmp_path / ".vds" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    _write_env(env_file, "VDS_AUDIT_STATE_DSN=postgresql://custom/db\nTOKEN=kept\n")

    ensure_shared_env(path=env_file)

    values = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    assert values["VDS_AUDIT_STATE_DSN"] == "postgresql://custom/db"
    assert values["TOKEN"] == "kept"
    for key, _ in DEFAULT_AUDIT_ENV_DEFAULTS:
        assert key in values


def test_get_shared_env_path_uses_override(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "envs" / "shared.env"
    monkeypatch.setenv("VDS_ENV_FILE", str(override))

    assert get_shared_env_path() == override.resolve()


def test_load_shared_env_uses_runtime_env_file_override_without_stale_defaults(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "portable" / ".env"
    override.parent.mkdir(parents=True, exist_ok=True)
    _write_env(override, "TOKEN=from-runtime-override\n")

    monkeypatch.setenv("VDS_ENV_FILE", str(override))
    monkeypatch.delenv("TOKEN", raising=False)

    merged = load_shared_env()

    assert merged["TOKEN"] == "from-runtime-override"
    assert os.environ["TOKEN"] == "from-runtime-override"


def test_render_shared_env_exports_only_emits_missing_values(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / "shared.env"
    _write_env(env_file, "TOKEN=from-file\nSPACE_VALUE=hello world\n")

    monkeypatch.setenv("TOKEN", "from-shell")
    exports = render_shared_env_exports(path=env_file)

    assert "TOKEN=from-file" not in exports
    assert "export SPACE_VALUE='hello world'" in exports


def test_render_shared_env_exports_override_true_emits_existing_values(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / "shared.env"
    _write_env(env_file, "TOKEN=from-file\n")

    monkeypatch.setenv("TOKEN", "from-shell")
    exports = render_shared_env_exports(path=env_file, override=True, ensure_defaults=False)

    assert exports == "export TOKEN=from-file"


@pytest.mark.integration
@pytest.mark.slow
def test_worktree_uv_bootstraps_shared_env_for_python_entrypoint(tmp_path: Path) -> None:
    env_file = tmp_path / "shared.env"
    _write_env(env_file, "VDS_AUDIT_STATE_DSN=postgresql://from-file/state\n")

    script = _worktree_uv_script()
    result = subprocess.run(
        [
            str(script),
            "run",
            "--project",
            "audit_orchestrator",
            "python",
            "-c",
            "import os; print(os.getenv('VDS_AUDIT_STATE_DSN') or '')",
        ],
        cwd=script.parent.parent,
        env={
            "HOME": os.environ["HOME"],
            "PATH": os.environ["PATH"],
            "VDS_ENV_FILE": str(env_file),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "postgresql://from-file/state"


@pytest.mark.integration
@pytest.mark.slow
def test_worktree_uv_preserves_explicit_state_dsn_over_shared_env(tmp_path: Path) -> None:
    env_file = tmp_path / "shared.env"
    _write_env(env_file, "VDS_AUDIT_STATE_DSN=postgresql://from-file/state\n")

    script = _worktree_uv_script()
    result = subprocess.run(
        [
            str(script),
            "run",
            "--project",
            "audit_orchestrator",
            "python",
            "-c",
            "import os; print(os.getenv('VDS_AUDIT_STATE_DSN') or '')",
        ],
        cwd=script.parent.parent,
        env={
            "HOME": os.environ["HOME"],
            "PATH": os.environ["PATH"],
            "VDS_ENV_FILE": str(env_file),
            "VDS_AUDIT_STATE_DSN": "postgresql://from-shell/state",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "postgresql://from-shell/state"


@pytest.mark.integration
@pytest.mark.slow
def test_worktree_uv_bootstraps_shared_env_from_external_cwd(tmp_path: Path) -> None:
    env_file = tmp_path / "shared.env"
    _write_env(env_file, "VDS_AUDIT_STATE_DSN=postgresql://from-file/state\n")

    script = _worktree_uv_script()
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir()
    result = subprocess.run(
        [
            str(script),
            "run",
            "--project",
            "audit_orchestrator",
            "python",
            "-c",
            "import os; print(os.getenv('VDS_AUDIT_STATE_DSN') or '')",
        ],
        cwd=outside_cwd,
        env={
            "HOME": os.environ["HOME"],
            "PATH": os.environ["PATH"],
            "VDS_ENV_FILE": str(env_file),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "postgresql://from-file/state"
