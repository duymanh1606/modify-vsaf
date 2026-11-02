"""Phase 225 W3 — NFR-225.12: ${env:VAR} credential resolver allowlist.

Verifies that the new ``${env:VAR}`` credential scheme refuses non-allowlisted
env-var names and that the bare ``${VAR}`` legacy syntax remains gate-free.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from vds_agent_core.profiles import (
    CredentialResolutionError,
    apply_runtime_profile,
)


def _write_profile(
    tmp_path: Path,
    *,
    env_value: str,
) -> Path:
    yaml_content = textwrap.dedent(
        f"""
        profiles:
          test-profile:
            env:
              EMBED_TEST_KEY: "{env_value}"
        """
    )
    yaml_file = tmp_path / "profiles.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")
    return yaml_file


def test_env_scheme_resolves_allowlisted_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """${env:OPENAI_API_KEY} resolves to the env value when set + allowlisted."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-test-key")
    monkeypatch.setenv(
        "VDS_AUDIT_RUNTIME_PROFILES_FILE",
        str(_write_profile(tmp_path, env_value="${env:OPENAI_API_KEY}")),
    )
    monkeypatch.delenv("EMBED_TEST_KEY", raising=False)
    apply_runtime_profile("test-profile", force_override=True)
    import os

    assert os.environ["EMBED_TEST_KEY"] == "sk-fake-test-key"


def test_env_scheme_rejects_non_allowlisted_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """${env:NOT_ALLOWED_VAR} raises CredentialResolutionError."""
    monkeypatch.setenv("NOT_ALLOWED_VAR", "shouldnt-leak")
    monkeypatch.setenv(
        "VDS_AUDIT_RUNTIME_PROFILES_FILE",
        str(_write_profile(tmp_path, env_value="${env:NOT_ALLOWED_VAR}")),
    )
    with pytest.raises(
        CredentialResolutionError,
        match=r"env var 'NOT_ALLOWED_VAR' is not in the credential allowlist",
    ):
        apply_runtime_profile("test-profile", force_override=True)


def test_env_scheme_rejects_database_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DATABASE_URL is not on the default allowlist (data exfiltration vector)."""
    monkeypatch.setenv("DATABASE_URL", "postgres://fake")
    monkeypatch.setenv(
        "VDS_AUDIT_RUNTIME_PROFILES_FILE",
        str(_write_profile(tmp_path, env_value="${env:DATABASE_URL}")),
    )
    with pytest.raises(CredentialResolutionError, match=r"DATABASE_URL"):
        apply_runtime_profile("test-profile", force_override=True)


def test_env_scheme_rejects_ssh_auth_sock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SSH_AUTH_SOCK is not on the default allowlist."""
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/fake.sock")
    monkeypatch.setenv(
        "VDS_AUDIT_RUNTIME_PROFILES_FILE",
        str(_write_profile(tmp_path, env_value="${env:SSH_AUTH_SOCK}")),
    )
    with pytest.raises(CredentialResolutionError, match=r"SSH_AUTH_SOCK"):
        apply_runtime_profile("test-profile", force_override=True)


def test_env_scheme_operator_extension_via_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operators may extend the allowlist via VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST."""
    monkeypatch.setenv("MY_CUSTOM_KEY", "custom-secret")
    monkeypatch.setenv(
        "VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST",
        '["MY_CUSTOM_KEY"]',
    )
    monkeypatch.setenv(
        "VDS_AUDIT_RUNTIME_PROFILES_FILE",
        str(_write_profile(tmp_path, env_value="${env:MY_CUSTOM_KEY}")),
    )
    monkeypatch.delenv("EMBED_TEST_KEY", raising=False)
    apply_runtime_profile("test-profile", force_override=True)
    import os

    assert os.environ["EMBED_TEST_KEY"] == "custom-secret"


def test_legacy_env_ref_does_not_trigger_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plain ${VAR} (no env: scheme) is unaffected by the allowlist (back-compat)."""
    monkeypatch.setenv("PLAIN_REF_VAR", "plain-value")
    monkeypatch.setenv(
        "VDS_AUDIT_RUNTIME_PROFILES_FILE",
        str(_write_profile(tmp_path, env_value="${PLAIN_REF_VAR}")),
    )
    monkeypatch.delenv("EMBED_TEST_KEY", raising=False)
    apply_runtime_profile("test-profile", force_override=True)
    import os

    assert os.environ["EMBED_TEST_KEY"] == "plain-value"


def test_env_scheme_unset_var_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Allowlisted but unset env var raises ValueError (clear error)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv(
        "VDS_AUDIT_RUNTIME_PROFILES_FILE",
        str(_write_profile(tmp_path, env_value="${env:OPENAI_API_KEY}")),
    )
    with pytest.raises(ValueError, match=r"requires environment variable 'OPENAI_API_KEY'"):
        apply_runtime_profile("test-profile", force_override=True)
