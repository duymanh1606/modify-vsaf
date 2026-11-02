from __future__ import annotations

from pathlib import Path

import pytest
from vds_bitbucket_orchestrator.config import load_settings


def write_env(tmp_path: Path, content: str) -> Path:
    """Write a temporary .env file for testing."""
    env_path = tmp_path / ".env"
    env_path.write_text(content)
    return env_path


def clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear runtime environment variables for testing."""
    for key in (
        "VDS_USERNAME",
        "VDS_PASSWORD",
        "BITBUCKET_TOKEN",
        "VDS_BITBUCKET_URL",  # Primary env var (FR-21.1.1)
        "BITBUCKET_BASE_URL",  # Legacy alias
        "VDS_BITBUCKET_HTTP_BASE",  # Legacy alias (git_orchestrator)
        "BITBUCKET_CLOUD_WORKSPACE",
        "BITBUCKET_MODE",
    ):
        monkeypatch.delenv(key, raising=False)


def test_load_settings_explicit_env_path_overrides_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that explicit env_path file values override env vars (override=True)."""
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
VDS_USERNAME=file_user
VDS_PASSWORD=file_pass
BITBUCKET_TOKEN=file_token
BITBUCKET_MODE=server
""".strip(),
    )

    monkeypatch.setenv("VDS_USERNAME", "env_user")
    settings = load_settings(env_path=env_path)

    # When env_path is explicitly provided, load_shared_env uses override=True,
    # so file values take precedence over pre-existing env vars
    assert settings.username == "file_user"
    assert settings.password == "file_pass"
    assert settings.token == "file_token"
    assert settings.mode == "server"


def test_load_settings_strict_requires_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that strict mode requires either basic auth or token."""
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
VDS_USERNAME=file_user
VDS_PASSWORD=file_pass
""".strip(),
    )

    # Should work with basic auth
    settings = load_settings(env_path=env_path, strict=True)
    assert settings.username == "file_user"
    assert settings.password == "file_pass"

    # Should fail with no credentials
    clear_runtime_env(monkeypatch)
    empty_env_path = write_env(tmp_path, "")
    with pytest.raises(ValueError, match="Missing credentials"):
        load_settings(env_path=empty_env_path, strict=True)


def test_cloud_mode_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test cloud mode configuration validation."""
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
BITBUCKET_MODE=cloud
BITBUCKET_CLOUD_WORKSPACE=testworkspace
BITBUCKET_TOKEN=cloud_token
""".strip(),
    )

    settings = load_settings(env_path=env_path, strict=True)
    assert settings.is_cloud_mode
    assert settings.cloud_workspace == "testworkspace"
    assert settings.token == "cloud_token"

    # Test URL generation for cloud mode
    url = settings.get_url()
    assert "testworkspace" in url
    assert "api.bitbucket.org" in url


def test_server_mode_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test server mode configuration validation."""
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
BITBUCKET_MODE=server
BITBUCKET_BASE_URL=https://bitbucket.company.com
VDS_USERNAME=server_user
VDS_PASSWORD=server_pass
""".strip(),
    )

    settings = load_settings(env_path=env_path, strict=True)
    assert settings.is_server_mode
    assert str(settings.base_url) == "https://bitbucket.company.com"
    assert settings.username == "server_user"
    assert settings.password == "server_pass"


def test_auth_kwargs_generation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test authentication kwargs generation for different auth methods."""
    clear_runtime_env(monkeypatch)

    # Test token auth
    token_env_path = write_env(tmp_path, "BITBUCKET_TOKEN=test_token\n")
    settings = load_settings(env_path=token_env_path)
    auth_kwargs = settings.get_auth_kwargs()
    assert auth_kwargs == {"token": "test_token"}

    # Test basic auth — clear env first to remove token from previous call
    clear_runtime_env(monkeypatch)
    basic_env_path = write_env(tmp_path, "VDS_USERNAME=test_user\nVDS_PASSWORD=test_pass\n")
    settings = load_settings(env_path=basic_env_path)
    auth_kwargs = settings.get_auth_kwargs()
    assert auth_kwargs == {"username": "test_user", "password": "test_pass"}


# =============================================================================
# TSK-220: Environment Variable Priority Tests (FR-21.1.1)
# =============================================================================


class TestEnvVarPriority:
    """Test environment variable resolution priority for Bitbucket URL.

    Priority order (FR-21.1.1):
    1. VDS_BITBUCKET_URL (primary - recommended)
    2. BITBUCKET_BASE_URL (legacy alias)
    3. VDS_BITBUCKET_HTTP_BASE (legacy alias - git_orchestrator)
    4. Default: http://bitbucket.digital.vn
    """

    def test_primary_env_var_takes_precedence(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that VDS_BITBUCKET_URL takes precedence over all aliases."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_BITBUCKET_URL=https://primary.bitbucket.com
BITBUCKET_BASE_URL=https://legacy.bitbucket.com
VDS_BITBUCKET_HTTP_BASE=https://git-orchestrator.bitbucket.com
""".strip(),
        )

        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "https://primary.bitbucket.com"

    def test_bitbucket_base_url_fallback(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that BITBUCKET_BASE_URL is used when VDS_BITBUCKET_URL is not set."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
BITBUCKET_BASE_URL=https://legacy.bitbucket.com
VDS_BITBUCKET_HTTP_BASE=https://git-orchestrator.bitbucket.com
""".strip(),
        )

        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "https://legacy.bitbucket.com"

    def test_vds_bitbucket_http_base_fallback(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that VDS_BITBUCKET_HTTP_BASE is used when higher priority vars are not set."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_BITBUCKET_HTTP_BASE=https://git-orchestrator.bitbucket.com
""".strip(),
        )

        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "https://git-orchestrator.bitbucket.com"

    def test_default_value_when_no_env_vars_set(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that default value is used when no env vars are set."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(tmp_path, "")

        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "http://bitbucket.digital.vn"

    def test_explicit_env_path_overrides_runtime_env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that explicit env_path file values override runtime env vars (override=True)."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_BITBUCKET_URL=https://file.bitbucket.com
""".strip(),
        )

        # Set runtime env var — file still wins because override=True
        monkeypatch.setenv("VDS_BITBUCKET_URL", "https://runtime.bitbucket.com")

        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "https://file.bitbucket.com"

    def test_runtime_primary_overrides_file_legacy(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that runtime VDS_BITBUCKET_URL overrides file-based legacy aliases."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
BITBUCKET_BASE_URL=https://file-legacy.bitbucket.com
VDS_BITBUCKET_HTTP_BASE=https://file-git.bitbucket.com
""".strip(),
        )

        # Set runtime primary env var (should take precedence over file-based legacy)
        monkeypatch.setenv("VDS_BITBUCKET_URL", "https://runtime-primary.bitbucket.com")

        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "https://runtime-primary.bitbucket.com"

    def test_all_aliases_work_independently(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that each alias works when set alone."""
        clear_runtime_env(monkeypatch)

        # Test VDS_BITBUCKET_URL alone
        env_path = write_env(tmp_path, "VDS_BITBUCKET_URL=https://primary.test.com\n")
        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "https://primary.test.com"

        # Test BITBUCKET_BASE_URL alone
        clear_runtime_env(monkeypatch)
        env_path = write_env(tmp_path, "BITBUCKET_BASE_URL=https://legacy.test.com\n")
        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "https://legacy.test.com"

        # Test VDS_BITBUCKET_HTTP_BASE alone
        clear_runtime_env(monkeypatch)
        env_path = write_env(tmp_path, "VDS_BITBUCKET_HTTP_BASE=https://git.test.com\n")
        settings = load_settings(env_path=env_path)
        assert str(settings.base_url) == "https://git.test.com"

    def test_backward_compatibility_with_existing_configs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test backward compatibility: existing configs using legacy vars still work."""
        clear_runtime_env(monkeypatch)

        # Simulate existing config using BITBUCKET_BASE_URL (common in bitbucket_orchestrator)
        env_path = write_env(
            tmp_path,
            """
BITBUCKET_BASE_URL=https://bitbucket.company.com
VDS_USERNAME=user
VDS_PASSWORD=pass
BITBUCKET_MODE=server
""".strip(),
        )

        settings = load_settings(env_path=env_path, strict=True)
        assert str(settings.base_url) == "https://bitbucket.company.com"
        assert settings.is_server_mode
        assert settings.username == "user"

    def test_backward_compatibility_with_git_orchestrator_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test backward compatibility: existing configs using VDS_BITBUCKET_HTTP_BASE still work."""
        clear_runtime_env(monkeypatch)

        # Simulate existing config using VDS_BITBUCKET_HTTP_BASE (common in git_orchestrator)
        env_path = write_env(
            tmp_path,
            """
VDS_BITBUCKET_HTTP_BASE=https://bitbucket.digital.vn
VDS_USERNAME=user
VDS_PASSWORD=pass
""".strip(),
        )

        settings = load_settings(env_path=env_path, strict=True)
        assert str(settings.base_url) == "https://bitbucket.digital.vn"
