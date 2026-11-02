from __future__ import annotations

from pathlib import Path

import pytest
from vds_jira_orchestrator.config import JiraSettings, SettingsError, load_settings


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("VDS_USERNAME", "VDS_PASSWORD", "JIRA_TOKEN", "JIRA_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("vds_jira_orchestrator.config.DEFAULT_ENV_PATHS", (), raising=False)
    # Patch load_shared_env in the config module namespace (where load_settings resolves it)
    monkeypatch.setattr("vds_jira_orchestrator.config.load_shared_env", lambda *a, **kw: {}, raising=False)


class TestJiraSettings:
    """Test suite for JiraSettings."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = JiraSettings()
        assert settings.base_url == "http://jira.digital.vn"
        assert settings.username is None
        assert settings.password is None
        assert settings.token is None

    def test_settings_from_dict(self) -> None:
        """Test creating settings from dictionary."""
        data = {
            "VDS_USERNAME": "test_user",
            "VDS_PASSWORD": "test_pass",
            "JIRA_TOKEN": "test_token",
            "JIRA_BASE_URL": "https://jira.test.com",
        }
        settings = JiraSettings.model_validate(data)
        assert settings.username == "test_user"
        assert settings.password == "test_pass"
        assert settings.token == "test_token"
        assert settings.base_url == "https://jira.test.com"

    def test_require_basic_or_token_success_with_token(self) -> None:
        """Test require_basic_or_token with token."""
        settings = JiraSettings(JIRA_TOKEN="test_token")
        settings.require_basic_or_token()  # Should not raise

    def test_require_basic_or_token_success_with_basic(self) -> None:
        """Test require_basic_or_token with username/password."""
        settings = JiraSettings(VDS_USERNAME="test_user", VDS_PASSWORD="test_pass")
        settings.require_basic_or_token()  # Should not raise

    def test_require_basic_or_token_failure(self) -> None:
        """Test require_basic_or_token with no credentials."""
        settings = JiraSettings()
        with pytest.raises(ValueError, match="Missing credentials"):
            settings.require_basic_or_token()


class TestLoadSettings:
    """Test suite for load_settings function."""

    def test_load_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("VDS_USERNAME", "env_user")
        monkeypatch.setenv("VDS_PASSWORD", "env_pass")
        monkeypatch.setenv("JIRA_TOKEN", "env_token")

        settings = load_settings()
        assert settings.username == "env_user"
        assert settings.password == "env_pass"
        assert settings.token == "env_token"

    def test_load_settings_from_file(self, tmp_path: Path) -> None:
        """Test loading settings from .env file."""
        env_content = """
VDS_USERNAME=file_user
VDS_PASSWORD=file_pass
JIRA_TOKEN=file_token
JIRA_BASE_URL=https://jira.file.com
        """.strip()
        env_path = tmp_path / ".env"
        env_path.write_text(env_content)

        settings = load_settings(env_path=env_path)
        assert settings.username == "file_user"
        assert settings.password == "file_pass"
        assert settings.token == "file_token"
        assert settings.base_url == "https://jira.file.com"

    def test_load_settings_with_overrides(self) -> None:
        """Test loading settings with overrides."""
        overrides = {
            "VDS_USERNAME": "override_user",
            "VDS_PASSWORD": "override_pass",
            "JIRA_TOKEN": "override_token",
        }

        settings = load_settings(overrides=overrides)
        assert settings.username == "override_user"
        assert settings.password == "override_pass"
        assert settings.token == "override_token"

    def test_load_settings_strict_success(self) -> None:
        """Test loading settings in strict mode with valid credentials."""
        overrides = {"JIRA_TOKEN": "test_token"}
        settings = load_settings(overrides=overrides, strict=True)
        assert settings.token == "test_token"

    def test_load_settings_strict_failure(self) -> None:
        """Test loading settings in strict mode with invalid credentials."""
        with pytest.raises(SettingsError):
            load_settings(strict=True)

    def test_load_settings_invalid_data(self) -> None:
        """Test loading settings with invalid data."""
        overrides = {"JIRA_BASE_URL": "invalid_url"}  # Invalid URL format
        with pytest.raises(SettingsError):
            load_settings(overrides=overrides)

    def test_env_file_parsing(self, tmp_path: Path) -> None:
        """Test .env file parsing with various formats."""
        env_content = """
# Comment line
VDS_USERNAME = "quoted_user"
VDS_PASSWORD=unquoted_pass
JIRA_TOKEN='single_quotes_token'
EMPTY_VAR=
# Another comment
JIRA_BASE_URL=https://jira.test.com
        """.strip()
        env_path = tmp_path / ".env"
        env_path.write_text(env_content)

        settings = load_settings(env_path=env_path)
        assert settings.username == "quoted_user"
        assert settings.password == "unquoted_pass"
        assert settings.token == "single_quotes_token"
        assert settings.base_url == "https://jira.test.com"

    def test_load_settings_precedence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test settings precedence: overrides > env > file."""
        # Set up file
        env_content = """
VDS_USERNAME=file_user
VDS_PASSWORD=file_pass
JIRA_TOKEN=file_token
        """.strip()
        env_path = tmp_path / ".env"
        env_path.write_text(env_content)

        # Set up environment
        monkeypatch.setenv("VDS_USERNAME", "env_user")
        monkeypatch.setenv("VDS_PASSWORD", "env_pass")

        # Set up overrides
        overrides = {"VDS_USERNAME": "override_user"}

        settings = load_settings(env_path=env_path, overrides=overrides)

        # Override should win
        assert settings.username == "override_user"
        # Environment should be next
        assert settings.password == "env_pass"
        # File should be last
        assert settings.token == "file_token"
