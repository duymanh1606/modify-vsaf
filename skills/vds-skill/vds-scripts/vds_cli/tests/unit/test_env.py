"""Unit tests for environment management."""

import os
from pathlib import Path

from vds_cli.env import VDSSettings, load_environment
from vds_cli_common.paths import get_shared_env_path


def test_vds_settings_instantiation() -> None:
    """Test VDSSettings can be instantiated."""
    # Note: This test verifies the class can be instantiated
    # Actual values depend on environment and ~/.vds/.env file
    settings = VDSSettings()
    assert isinstance(settings, VDSSettings)
    # Verify all expected attributes exist
    assert hasattr(settings, "vds_username")
    assert hasattr(settings, "vds_password")
    assert hasattr(settings, "bitbucket_access_token")
    assert hasattr(settings, "internal_confluence_token")
    assert hasattr(settings, "external_confluence_token")


def test_vds_settings_with_env_file(mock_env_file: Path, mock_home_dir: Path) -> None:
    """Test VDSSettings can load from environment file."""
    # Note: pydantic-settings reads from both env file and environment variables
    # This test verifies the class can be instantiated with a file present
    settings = VDSSettings()
    assert isinstance(settings, VDSSettings)
    # Values may come from file or environment - just verify structure
    assert hasattr(settings, "vds_username")


def test_load_environment() -> None:
    """Test load_environment function."""
    settings = load_environment()
    assert isinstance(settings, VDSSettings)
    assert hasattr(settings, "vds_username")


def test_load_environment_returns_settings() -> None:
    """Test load_environment returns VDSSettings instance."""
    settings = load_environment()
    assert isinstance(settings, VDSSettings)
    # Verify it has all expected attributes
    assert hasattr(settings, "vds_username")
    assert hasattr(settings, "bitbucket_access_token")


def test_shared_env_path_available() -> None:
    """Test shared env path helper returns a Path."""
    path = get_shared_env_path()
    assert isinstance(path, Path)
    assert path.name == ".env"


def test_load_environment_prefers_existing_shell_environment(tmp_path: Path, monkeypatch) -> None:
    """Shell environment should win over values loaded from the shared env file."""
    env_file = tmp_path / "config" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("VDS_USERNAME=from-file\n", encoding="utf-8")

    monkeypatch.setenv("VDS_ENV_FILE", str(env_file))
    monkeypatch.setenv("VDS_USERNAME", "from-shell")

    settings = load_environment()

    assert settings.vds_username == "from-shell"
    assert os.environ["VDS_USERNAME"] == "from-shell"


def test_load_environment_uses_shared_env_file_override(tmp_path: Path, monkeypatch) -> None:
    """Configured shared env file should feed VDS settings when shell values are absent."""
    env_file = tmp_path / "portable-config" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("VDS_USERNAME=portable-user\nVDS_PASSWORD=portable-pass\n", encoding="utf-8")

    monkeypatch.setenv("VDS_ENV_FILE", str(env_file))
    monkeypatch.delenv("VDS_USERNAME", raising=False)
    monkeypatch.delenv("VDS_PASSWORD", raising=False)

    settings = load_environment()

    assert settings.vds_username == "portable-user"
    assert settings.vds_password == "portable-pass"
