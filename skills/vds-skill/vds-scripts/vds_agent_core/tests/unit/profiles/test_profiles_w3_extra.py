"""Phase 225 W3 extra coverage — credential allowlist, auth helper edges,
embedding-block parser branches, and one-shot resolution log.

Targets uncovered branches in profiles.py W3 surface (added by db760e14
and 5e956598).
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path

import pytest
import structlog
from vds_agent_core.profiles import (
    ProfileValidationError,
    _get_env_credential_allowlist,
    _maybe_log_embedding_resolution,
    _reset_embedding_resolution_log,
    apply_runtime_profile,
    is_agent_allowed_for_profile,
)


def _write_profile(tmp_path: Path, body: str) -> Path:
    yaml_file = tmp_path / "profiles.yaml"
    yaml_file.write_text(textwrap.dedent(body), encoding="utf-8")
    return yaml_file


def _scrub_embed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for key in list(os.environ):
        if key.startswith("VDS_AGENT_CORE_EMBED__") or key.startswith("VDS_AUDIT_EMBEDDING__"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def configure_structlog_for_caplog() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.KeyValueRenderer(key_order=["event"]),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


# ---------------------------------------------------------------------------
# _get_env_credential_allowlist branches
# ---------------------------------------------------------------------------


class TestCredentialAllowlistBuilder:
    def test_default_allowlist_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST", raising=False)
        out = _get_env_credential_allowlist()
        assert "OPENAI_API_KEY" in out
        assert "DATABASE_URL" not in out

    def test_default_allowlist_when_env_blank(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST", "   ")
        out = _get_env_credential_allowlist()
        assert "OPENAI_API_KEY" in out

    def test_malformed_json_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NFR-225.12: typo in JSON does not narrow the allowlist."""
        monkeypatch.setenv("VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST", "{ not valid json")
        out = _get_env_credential_allowlist()
        assert "OPENAI_API_KEY" in out

    def test_non_list_payload_falls_back_to_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST",
            '{"key": "not a list"}',
        )
        out = _get_env_credential_allowlist()
        assert "OPENAI_API_KEY" in out

    def test_extension_unions_with_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Operator-supplied extras union with compile-time defaults."""
        monkeypatch.setenv(
            "VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST",
            '["MY_OWN_KEY"]',
        )
        out = _get_env_credential_allowlist()
        assert "MY_OWN_KEY" in out
        assert "OPENAI_API_KEY" in out  # defaults still present

    def test_extension_filters_non_strings_and_blanks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST",
            '["GOOD", "", "  ", 123, null]',
        )
        out = _get_env_credential_allowlist()
        assert "GOOD" in out
        assert "" not in out
        assert "  " not in out


# ---------------------------------------------------------------------------
# is_agent_allowed_for_profile — uncovered edges
# ---------------------------------------------------------------------------


class TestIsAgentAllowedExtra:
    def test_double_star_matches_any(self) -> None:
        """fnmatch '**' acts like '*' (any chars)."""
        profiles = {"p": {"allowed_agents": ["**"]}}
        assert is_agent_allowed_for_profile("p", "anything-here", profiles=profiles) is True

    def test_question_mark_pattern(self) -> None:
        profiles = {"p": {"allowed_agents": ["a?"]}}
        assert is_agent_allowed_for_profile("p", "ab", profiles=profiles) is True
        assert is_agent_allowed_for_profile("p", "abc", profiles=profiles) is False

    def test_non_string_pattern_skipped(self) -> None:
        """Non-string list items are silently skipped (continue)."""
        profiles = {"p": {"allowed_agents": [123, None, "real-*"]}}
        assert is_agent_allowed_for_profile("p", "real-1", profiles=profiles) is True
        assert is_agent_allowed_for_profile("p", "fake-1", profiles=profiles) is False

    def test_default_profile_path_loaded_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """profiles=None + no real file => empty profiles_map => unknown profile -> True."""
        # Point env to a non-existent file so resolve_runtime_profiles_path returns
        # a path with .exists() == False.
        nonexistent = tmp_path / "does-not-exist.yaml"
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(nonexistent))
        # Unknown profile w/ no profile file => True (deferred error path).
        assert is_agent_allowed_for_profile("nonexistent-profile", "any", profiles=None) is True

    def test_yaml_file_with_non_dict_root_treated_as_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """YAML file whose root is a scalar => treated as empty profiles map."""
        yaml_file = _write_profile(tmp_path, "just-a-string")
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        # Unknown profile -> True (deferred-error contract).
        assert is_agent_allowed_for_profile("any", "agent", profiles=None) is True

    def test_profiles_section_non_dict_treated_as_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`profiles:` key whose value is a list/scalar => treated as empty map."""
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles: not-a-dict
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        assert is_agent_allowed_for_profile("any", "agent", profiles=None) is True


# ---------------------------------------------------------------------------
# parse_embedding=True — branch coverage on each field type
# ---------------------------------------------------------------------------


class TestEmbeddingBlockParserExtra:
    def test_unknown_legacy_keys_raise_value_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Embedding block with truly unknown key raises ValueError (not ProfileValidationError)."""
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              bad-keys:
                model:
                  embedding:
                    type: ollama
                    truly_unknown_key: foo
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ValueError, match=r"invalid model.embedding keys"):
            apply_runtime_profile("bad-keys", force_override=True, parse_embedding=True)

    def test_blank_type_string_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              blank:
                model:
                  embedding:
                    type: "   "
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ProfileValidationError, match=r"invalid model.embedding.type"):
            apply_runtime_profile("blank", force_override=True, parse_embedding=True)

    def test_non_string_type_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              non-str-type:
                model:
                  embedding:
                    type: 42
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ProfileValidationError, match=r"invalid model.embedding.type"):
            apply_runtime_profile("non-str-type", force_override=True, parse_embedding=True)

    def test_non_int_dimension_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              bad-dim:
                model:
                  embedding:
                    type: ollama
                    dimension: not-an-int
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ProfileValidationError, match=r"invalid model.embedding.dimension"):
            apply_runtime_profile("bad-dim", force_override=True, parse_embedding=True)

    def test_zero_dimension_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              zero-dim:
                model:
                  embedding:
                    type: ollama
                    dimension: 0
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ProfileValidationError, match=r"invalid model.embedding.dimension"):
            apply_runtime_profile("zero-dim", force_override=True, parse_embedding=True)

    def test_fail_open_boolean_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              fopen:
                model:
                  embedding:
                    type: ollama
                    fail_open: true
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        apply_runtime_profile("fopen", force_override=True, parse_embedding=True)
        import os

        assert os.environ["VDS_AGENT_CORE_EMBED__FAIL_OPEN"] == "true"

    def test_cache_ttl_seconds_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              cache-ttl:
                model:
                  embedding:
                    type: ollama
                    cache_ttl_seconds: 3600
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        apply_runtime_profile("cache-ttl", force_override=True, parse_embedding=True)
        import os

        assert os.environ["VDS_AGENT_CORE_EMBED__CACHE_TTL_SECONDS"] == "3600"

    def test_cache_ttl_negative_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              bad-ttl:
                model:
                  embedding:
                    type: ollama
                    cache_ttl_seconds: -5
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ProfileValidationError, match=r"cache_ttl_seconds"):
            apply_runtime_profile("bad-ttl", force_override=True, parse_embedding=True)

    def test_cache_ttl_non_int_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              non-int-ttl:
                model:
                  embedding:
                    type: ollama
                    cache_ttl_seconds: "abc"
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ProfileValidationError, match=r"cache_ttl_seconds"):
            apply_runtime_profile("non-int-ttl", force_override=True, parse_embedding=True)

    def test_timeout_seconds_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              tmt:
                model:
                  embedding:
                    type: ollama
                    timeout_seconds: 15.5
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        apply_runtime_profile("tmt", force_override=True, parse_embedding=True)
        import os

        assert os.environ["VDS_AGENT_CORE_EMBED__TIMEOUT_SECONDS"] == "15.5"

    def test_timeout_seconds_zero_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              bad-tmt:
                model:
                  embedding:
                    type: ollama
                    timeout_seconds: 0
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ProfileValidationError, match=r"timeout_seconds"):
            apply_runtime_profile("bad-tmt", force_override=True, parse_embedding=True)

    def test_timeout_seconds_non_numeric_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              bad-tmt:
                model:
                  embedding:
                    type: ollama
                    timeout_seconds: "not-a-float"
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        with pytest.raises(ProfileValidationError, match=r"timeout_seconds"):
            apply_runtime_profile("bad-tmt", force_override=True, parse_embedding=True)

    def test_model_simple_complex_keys_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """W3-tolerated keys for tier-specific models."""
        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              tiers:
                model:
                  embedding:
                    type: ollama
                    model_simple: bge-simple
                    model_standard: bge-std
                    model_complex: bge-complex
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
        apply_runtime_profile("tiers", force_override=True, parse_embedding=True)
        import os

        assert os.environ["VDS_AGENT_CORE_EMBED__MODEL_SIMPLE"] == "bge-simple"
        assert os.environ["VDS_AGENT_CORE_EMBED__MODEL_COMPLEX"] == "bge-complex"


# ---------------------------------------------------------------------------
# _maybe_log_embedding_resolution — one-shot lock semantics
# ---------------------------------------------------------------------------


class TestEmbeddingResolutionLog:
    def test_no_log_when_env_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        _reset_embedding_resolution_log()
        monkeypatch.delenv("VDS_AGENT_CORE__LOG_RESOLUTION", raising=False)
        with caplog.at_level(logging.INFO):
            _maybe_log_embedding_resolution("any-profile")
        assert all(
            "profile_embedding_resolved" not in rec.getMessage() for rec in caplog.records
        )

    def test_log_emitted_once_when_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        _reset_embedding_resolution_log()
        monkeypatch.setenv("VDS_AGENT_CORE__LOG_RESOLUTION", "true")
        with caplog.at_level(logging.INFO):
            _maybe_log_embedding_resolution("p1")
            _maybe_log_embedding_resolution("p1")  # second call: silent
        events = [
            rec.getMessage()
            for rec in caplog.records
            if "profile_embedding_resolved" in rec.getMessage()
        ]
        assert len(events) == 1

    def test_log_separate_profiles(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        _reset_embedding_resolution_log()
        monkeypatch.setenv("VDS_AGENT_CORE__LOG_RESOLUTION", "true")
        with caplog.at_level(logging.INFO):
            _maybe_log_embedding_resolution("p1")
            _maybe_log_embedding_resolution("p2")
        events = [
            rec.getMessage()
            for rec in caplog.records
            if "profile_embedding_resolved" in rec.getMessage()
        ]
        assert len(events) == 2


# ---------------------------------------------------------------------------
# build_embedding_settings_for_profile — config_hooks branches
# ---------------------------------------------------------------------------


class TestBuildEmbeddingSettingsConfigHooks:
    def test_config_hooks_reset_and_restore_called(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """config_hooks.reset_config() + set_config(previous) fire on the W3 path."""
        from unittest.mock import MagicMock

        from vds_agent_core.profiles import build_embedding_settings_for_profile

        _scrub_embed_env(monkeypatch)
        yaml_file = _write_profile(
            tmp_path,
            """
            profiles:
              hooked:
                model:
                  embedding:
                    type: hash
                    dimension: 1024
            """,
        )
        monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))

        # ConfigHooks is a Protocol; duck-type a minimal implementation.
        class _FakeConfigHooks:
            def __init__(self) -> None:
                self.get_config = MagicMock(return_value=object())
                self.set_config = MagicMock()
                self.reset_config = MagicMock()

        hooks = _FakeConfigHooks()
        settings = build_embedding_settings_for_profile("hooked", config_hooks=hooks)
        assert settings.provider == "hash"
        # reset_config must have been invoked under the W3 happy path.
        hooks.reset_config.assert_called_once()
        # set_config must have been called with the previously-snapshotted config.
        hooks.set_config.assert_called_once()
        # The argument passed to set_config matches what get_config returned.
        sentinel_config = hooks.get_config.return_value
        hooks.set_config.assert_called_with(sentinel_config)
