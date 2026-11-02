"""Phase 225 W3 — FR-226.13: model.embedding YAML block parser.

Verifies opt-in embedding-block parsing (parse_embedding=True) plus the
EMBEDDING_PROVIDERS registry validator. Default behavior (parse_embedding=False)
must remain unchanged for FR-225.22 back-compat.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest
from vds_agent_core.profiles import (
    ProfileValidationError,
    apply_runtime_profile,
    build_embedding_settings_for_profile,
)


def _write_profile(tmp_path: Path, body: str) -> Path:
    yaml_file = tmp_path / "profiles.yaml"
    yaml_file.write_text(textwrap.dedent(body), encoding="utf-8")
    return yaml_file


def _scrub_embed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("VDS_AGENT_CORE_EMBED__") or key.startswith("VDS_AUDIT_EMBEDDING__"):
            monkeypatch.delenv(key, raising=False)


def test_parse_embedding_default_false_no_env_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """parse_embedding default False => no VDS_AGENT_CORE_EMBED__ env vars set."""
    _scrub_embed_env(monkeypatch)
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          test:
            model:
              embedding:
                base_url: http://localhost:11434
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    apply_runtime_profile("test", force_override=True)  # parse_embedding default False
    assert "VDS_AGENT_CORE_EMBED__PROVIDER" not in os.environ
    assert "VDS_AGENT_CORE_EMBED__DIMENSION" not in os.environ


def test_parse_embedding_true_sets_provider_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """parse_embedding=True with type=ollama sets VDS_AGENT_CORE_EMBED__PROVIDER."""
    _scrub_embed_env(monkeypatch)
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          test:
            model:
              embedding:
                type: ollama
                model: bge-m3
                dimension: 1024
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    apply_runtime_profile("test", force_override=True, parse_embedding=True)
    assert os.environ["VDS_AGENT_CORE_EMBED__PROVIDER"] == "ollama"
    assert os.environ["VDS_AGENT_CORE_EMBED__MODEL_STANDARD"] == "bge-m3"
    assert os.environ["VDS_AGENT_CORE_EMBED__DIMENSION"] == "1024"


def test_parse_embedding_unknown_type_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown embedding type raises ProfileValidationError naming the registry."""
    _scrub_embed_env(monkeypatch)
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          test:
            model:
              embedding:
                type: bad_provider
                model: foo
                dimension: 1024
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    with pytest.raises(
        ProfileValidationError,
        match=r"Unknown embedding type 'bad_provider'.*registered:",
    ):
        apply_runtime_profile("test", force_override=True, parse_embedding=True)


def test_parse_embedding_invalid_dimension_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative dimension raises ProfileValidationError."""
    _scrub_embed_env(monkeypatch)
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          test:
            model:
              embedding:
                type: ollama
                dimension: -1
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    with pytest.raises(ProfileValidationError, match=r"invalid model.embedding.dimension"):
        apply_runtime_profile("test", force_override=True, parse_embedding=True)


def test_build_embedding_settings_for_profile_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Round-trip: profile YAML -> env vars -> EmbeddingSettings instance."""
    _scrub_embed_env(monkeypatch)
    # ollama defaults: dim 1024, model bge-m3, base_url host.docker.internal:11434
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          rt-test:
            model:
              embedding:
                type: ollama
                model: bge-m3
                dimension: 1024
                base_url: http://localhost:11434
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    settings = build_embedding_settings_for_profile("rt-test")
    assert settings.provider == "ollama"
    assert settings.model_standard == "bge-m3"
    assert settings.dimension == 1024
    assert settings.base_url == "http://localhost:11434"


def test_build_embedding_settings_no_block_uses_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Profile without embedding block falls through to EmbeddingSettings() defaults."""
    _scrub_embed_env(monkeypatch)
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          plain:
            env:
              FOO: bar
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    settings = build_embedding_settings_for_profile("plain")
    # Defaults from EmbeddingRuntimeConfig
    assert settings.provider == "ollama"
    assert settings.model_standard == "bge-m3"
    assert settings.dimension == 1024


def test_parse_embedding_legacy_keys_still_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy base_url/model/api_key keys still set VDS_AUDIT_EMBEDDING__* (back-compat)."""
    _scrub_embed_env(monkeypatch)
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          legacy:
            model:
              embedding:
                base_url: http://localhost:11434
                model: bge-m3
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    apply_runtime_profile("legacy", force_override=True)
    # Legacy env vars remain populated regardless of parse_embedding flag.
    assert os.environ.get("VDS_AUDIT_EMBEDDING__BASE_URL") == "http://localhost:11434"
    assert os.environ.get("VDS_AUDIT_EMBEDDING__MODEL") == "bge-m3"
