from __future__ import annotations

from pathlib import Path

from vds_cli_common import paths


def test_get_vds_config_root_prefers_env_override(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "custom-config"
    monkeypatch.setenv("VDS_CONFIG_DIR", str(override))

    assert paths.get_vds_config_root() == override.resolve()


def test_get_default_env_paths_only_include_shared_env_path(monkeypatch, tmp_path: Path) -> None:
    config_root = tmp_path / ".vds"

    monkeypatch.delenv("VDS_ENV_FILE", raising=False)
    monkeypatch.delenv("VDS_CONFIG_DIR", raising=False)
    monkeypatch.setattr(paths, "_default_vds_home", lambda: config_root)

    env_paths = paths.get_default_env_paths()

    assert len(env_paths) == 1
    assert env_paths[0] == config_root / ".env"


def test_get_vds_data_root_uses_vds_home_default(monkeypatch, tmp_path: Path) -> None:
    config_root = tmp_path / ".vds"

    monkeypatch.delenv("VDS_DATA_DIR", raising=False)
    monkeypatch.delenv("VDS_CONFIG_DIR", raising=False)
    monkeypatch.setattr(paths, "_default_vds_home", lambda: config_root)

    assert paths.get_vds_data_root() == config_root / "data"


def test_get_vds_log_root_uses_vds_home_logs_default(monkeypatch, tmp_path: Path) -> None:
    config_root = tmp_path / ".vds"

    monkeypatch.delenv("VDS_LOG_DIR", raising=False)
    monkeypatch.delenv("VDS_CONFIG_DIR", raising=False)
    monkeypatch.setattr(paths, "_default_vds_home", lambda: config_root)

    assert paths.get_vds_log_root() == config_root / "logs"


def test_get_vds_config_root_uses_vds_home_default_when_no_override(monkeypatch, tmp_path: Path) -> None:
    config_root = tmp_path / ".vds"

    monkeypatch.delenv("VDS_CONFIG_DIR", raising=False)
    monkeypatch.setattr(paths, "_default_vds_home", lambda: config_root)

    assert paths.get_vds_config_root() == config_root


def test_get_shared_env_path_prefers_env_file_override(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "config" / "custom.env"
    monkeypatch.setenv("VDS_ENV_FILE", str(override))

    assert paths.get_shared_env_path() == override.resolve()
