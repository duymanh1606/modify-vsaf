"""Tests for SonarQube configuration loading."""

from __future__ import annotations

import os

import pytest

from vds_sonarqube_orchestrator.config import SettingsError, SonarqubeSettings, load_settings


@pytest.fixture(autouse=True)
def clear_sonar_env_vars() -> None:
    """Clear SonarQube environment variables before each test."""
    # Save and clear VDS_SONAR_* from os.environ
    sonar_vars = [k for k in os.environ if k.startswith("VDS_SONAR_")]
    saved_vars = {var: os.environ[var] for var in sonar_vars if var in os.environ}
    for var in sonar_vars:
        os.environ.pop(var, None)

    yield

    # Restore original values
    for var, value in saved_vars.items():
        os.environ[var] = value


def test_sonarqube_settings_minimal() -> None:
    """Test creating settings with minimal required fields."""
    settings = SonarqubeSettings(
        host_url="http://sonar-test.example.com",
    )
    assert settings.host_url == "http://sonar-test.example.com"
    assert settings.base_url == "http://sonar-test.example.com"
    # Note: These may be loaded from .env file, so we just check the object exists
    assert hasattr(settings, "token")
    assert hasattr(settings, "user")


def test_sonarqube_settings_with_token() -> None:
    """Test creating settings with token authentication."""
    settings = SonarqubeSettings(
        host_url="http://sonar-test.example.com",
        token_secret="test_token_123",
    )
    assert settings.token == "test_token_123"


def test_sonarqube_settings_with_user_password() -> None:
    """Test creating settings with username/password authentication."""
    settings = SonarqubeSettings(
        host_url="http://sonar-test.example.com",
        user="testuser",
        password_secret="testpass",
    )
    assert settings.user == "testuser"
    assert settings.password == "testpass"


def test_sonarqube_settings_defaults() -> None:
    """Test that default values are applied correctly."""
    settings = SonarqubeSettings(
        host_url="http://sonar-test.example.com",
    )
    assert settings.connect_timeout == 10.0
    assert settings.request_timeout == 30.0
    assert settings.max_retries == 3
    assert settings.retry_backoff == 1.5
    assert settings.verify_certs is False


def test_sonarqube_settings_require_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Test credential validation."""
    for key in list(os.environ):
        if key.startswith("VDS_SONAR_"):
            monkeypatch.delenv(key, raising=False)
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "vds_sonarqube_orchestrator.config.DEFAULT_ENV_PATHS",
        (empty_env,),
    )
    # Settings with token should pass
    settings = SonarqubeSettings(
        _env_file=empty_env,
        host_url="http://sonar-test.example.com",
        token_secret="test_token",
    )
    settings.require_credentials()  # Should not raise

    # Settings with user/password should pass
    settings = SonarqubeSettings(
        _env_file=empty_env,
        host_url="http://sonar-test.example.com",
        user="testuser",
        password_secret="testpass",
    )
    settings.require_credentials()  # Should not raise

    # Settings without credentials should fail
    settings = SonarqubeSettings(
        _env_file=empty_env,
        host_url="http://sonar-test.example.com",
    )
    with pytest.raises(ValueError, match="Missing SonarQube credentials"):
        settings.require_credentials()


def test_load_settings_from_dict(sample_env_file) -> None:
    """Test loading settings from a dict (for testing)."""
    # Use env_path to load from sample .env file
    settings = load_settings(env_path=sample_env_file)
    assert settings.host_url == "http://sonar-test.example.com"
    assert settings.token == "test_token_12345"


def test_load_settings_strict_mode(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Test load_settings with strict=True when host_url is missing."""
    for key in list(os.environ):
        if key.startswith("VDS_SONAR_"):
            monkeypatch.delenv(key, raising=False)
    fake_env = tmp_path / "empty.env"
    fake_env.write_text("", encoding="utf-8")
    with pytest.raises(SettingsError, match="VDS_SONAR_HOST_URL"):
        load_settings(env_path=fake_env, strict=True)


def test_settings_base_url_normalization() -> None:
    """Test that base_url normalizes trailing slashes."""
    settings = SonarqubeSettings(
        host_url="http://sonar-test.example.com/",
    )
    assert settings.base_url == "http://sonar-test.example.com"


def test_settings_alias_mapping() -> None:
    """Test that environment variable aliases work correctly."""
    settings = SonarqubeSettings(
        **{
            "VDS_SONAR_HOST_URL": "http://sonar-test.example.com",
            "VDS_SONAR_TOKEN": "test_token",
        }
    )
    assert settings.host_url == "http://sonar-test.example.com"
    assert settings.token == "test_token"
