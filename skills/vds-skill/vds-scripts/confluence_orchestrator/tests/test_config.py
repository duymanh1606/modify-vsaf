from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from confluence_orchestrator.config import load_settings

if TYPE_CHECKING:
    import pytest


def write_env(tmp_path: Path, content: str) -> Path:
    env_path = tmp_path / ".env"
    env_path.write_text(content)
    return env_path


def clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "VDS_USERNAME",
        "VDS_PASSWORD",
        "INTERNAL_CONFLUENCE_TOKEN",
        "EXTERNAL_CONFLUENCE_TOKEN",
        "CONFLUENCE_DEFAULT_SERVER",
        "CONFLUENCE_INTERNAL_URL",
        "CONFLUENCE_EXTERNAL_URL",
        "CONFLUENCE_EXTERNAL_ALTERNATE_URL",
        "CONFLUENCE_INTERNAL_ALTERNATE_URL",
        "CONFLUENCE_SECONDARY_EXTERNAL_URL",
        "CONFLUENCE_INTERNAL_FALLBACK_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_load_settings_file_overrides_env_when_env_path_provided(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When env_path is given, load_shared_env(override=True) makes file values win over env."""
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
VDS_USERNAME=file_user
VDS_PASSWORD=file_pass
INTERNAL_CONFLUENCE_TOKEN=file_internal
EXTERNAL_CONFLUENCE_TOKEN=file_external
CONFLUENCE_DEFAULT_SERVER=external
""".strip(),
    )

    monkeypatch.setenv("VDS_USERNAME", "env_user")
    settings = load_settings(env_path=env_path)

    assert settings.username == "file_user"
    assert settings.password is not None and settings.password.get_secret_value() == "file_pass"
    assert settings.internal_token is not None and settings.internal_token.get_secret_value() == "file_internal"
    assert settings.default_server == "external"


def test_load_settings_strict_allows_basic_auth(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
VDS_USERNAME=file_user
VDS_PASSWORD=file_pass
""".strip(),
    )

    settings = load_settings(env_path=env_path, strict=True)
    assert settings.username == "file_user"
    assert settings.password is not None and settings.password.get_secret_value() == "file_pass"


def test_url_and_token_resolution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
VDS_USERNAME=user
VDS_PASSWORD=pass
INTERNAL_CONFLUENCE_TOKEN=internal
EXTERNAL_CONFLUENCE_TOKEN=external
CONFLUENCE_INTERNAL_URL=http://internal.example.local
CONFLUENCE_EXTERNAL_URL=http://external.example.local
""".strip(),
    )

    settings = load_settings(env_path=env_path, strict=True)

    assert settings.token_for("internal") == "internal"
    assert settings.token_for("external") == "external"
    assert str(settings.url_for("internal")).rstrip("/") == "http://internal.example.local"
    assert str(settings.url_for("external")).rstrip("/") == "http://external.example.local"


def test_alternate_endpoint_names_are_canonical(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
VDS_USERNAME=user
VDS_PASSWORD=pass
CONFLUENCE_EXTERNAL_ALTERNATE_URL=http://external-alt.example.local
CONFLUENCE_INTERNAL_ALTERNATE_URL=http://internal-alt.example.local
""".strip(),
    )

    settings = load_settings(env_path=env_path, strict=True)

    assert str(settings.external_alternate_url).rstrip("/") == "http://external-alt.example.local"
    assert str(settings.internal_alternate_url).rstrip("/") == "http://internal-alt.example.local"


def test_legacy_fallback_env_names_map_to_alternate_endpoints(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clear_runtime_env(monkeypatch)
    env_path = write_env(
        tmp_path,
        """
VDS_USERNAME=user
VDS_PASSWORD=pass
CONFLUENCE_SECONDARY_EXTERNAL_URL=http://external-legacy.example.local
CONFLUENCE_INTERNAL_FALLBACK_URL=http://internal-legacy.example.local
""".strip(),
    )

    settings = load_settings(env_path=env_path, strict=True)

    assert str(settings.external_alternate_url).rstrip("/") == "http://external-legacy.example.local"
    assert str(settings.internal_alternate_url).rstrip("/") == "http://internal-legacy.example.local"
