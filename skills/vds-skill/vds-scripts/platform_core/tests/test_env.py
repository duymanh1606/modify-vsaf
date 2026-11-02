"""Tests for vds_platform_core.env — TSK-7.12b."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import vds_platform_core.env as _env_mod
from vds_platform_core.env import DEFAULT_ENV_PATHS

if TYPE_CHECKING:
    import pytest


def test_default_env_paths_is_tuple() -> None:
    """DEFAULT_ENV_PATHS is a non-empty tuple of Path objects."""
    assert isinstance(DEFAULT_ENV_PATHS, tuple)
    assert len(DEFAULT_ENV_PATHS) == 1
    assert isinstance(DEFAULT_ENV_PATHS[0], Path)


def test_default_env_paths_default_is_vds_dot_env() -> None:
    """Without env overrides, path is ~/.vds/.env."""
    path = (
        _env_mod._vds_env_path.__wrapped__()
        if hasattr(_env_mod._vds_env_path, "__wrapped__")
        else _env_mod._vds_env_path()
    )
    assert path == Path.home() / ".vds" / ".env"


def test_vds_env_file_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """VDS_ENV_FILE env var is honoured."""
    custom = tmp_path / "custom.env"
    monkeypatch.setenv("VDS_ENV_FILE", str(custom))
    assert _env_mod._vds_env_path() == custom.resolve()


def test_vds_config_dir_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """VDS_CONFIG_DIR env var shifts the root directory."""
    monkeypatch.delenv("VDS_ENV_FILE", raising=False)
    monkeypatch.setenv("VDS_CONFIG_DIR", str(tmp_path))
    assert _env_mod._vds_env_path() == tmp_path.resolve() / ".env"


def test_vds_env_file_takes_precedence_over_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """VDS_ENV_FILE wins over VDS_CONFIG_DIR when both are set."""
    custom = tmp_path / "direct.env"
    monkeypatch.setenv("VDS_ENV_FILE", str(custom))
    monkeypatch.setenv("VDS_CONFIG_DIR", str(tmp_path / "other"))
    assert _env_mod._vds_env_path() == custom.resolve()


def test_default_env_paths_exported_in_all() -> None:
    """DEFAULT_ENV_PATHS is listed in __all__."""
    assert "DEFAULT_ENV_PATHS" in _env_mod.__all__
