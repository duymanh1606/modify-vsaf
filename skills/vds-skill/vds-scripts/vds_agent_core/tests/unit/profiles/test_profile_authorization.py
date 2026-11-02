"""Phase 225 W3 — NFR-225.13: profile authorization via allowed_agents globs.

The W3 helper ``is_agent_allowed_for_profile`` returns True for back-compat
(no ``allowed_agents`` field) and uses :mod:`fnmatch` for glob matching when
the field is present. Gate enforcement at ``for_agent()`` is deferred to
Phase 227 per spec v20.6.1 §FR-227.*.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from vds_agent_core.profiles import (
    ProfileValidationError,
    is_agent_allowed_for_profile,
)


def _write_profile(tmp_path: Path, body: str) -> Path:
    yaml_file = tmp_path / "profiles.yaml"
    yaml_file.write_text(textwrap.dedent(body), encoding="utf-8")
    return yaml_file


def test_no_allowed_agents_field_is_back_compat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Profile without allowed_agents field => any agent allowed (back-compat)."""
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          unguarded:
            env:
              FOO: bar
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    assert is_agent_allowed_for_profile("unguarded", "any-agent-id") is True
    assert is_agent_allowed_for_profile("unguarded", "memory-search") is True


def test_allowed_agents_glob_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """allowed_agents: ['audit-*'] matches audit-prefixed agent_ids."""
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          audit-prod:
            allowed_agents: ["audit-*"]
            env:
              FOO: bar
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    assert is_agent_allowed_for_profile("audit-prod", "audit-evaluator") is True
    assert is_agent_allowed_for_profile("audit-prod", "audit-row") is True


def test_allowed_agents_glob_rejects_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """allowed_agents glob rejects agent_ids that don't match."""
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          audit-prod:
            allowed_agents: ["audit-*"]
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    assert is_agent_allowed_for_profile("audit-prod", "memory-search") is False
    assert is_agent_allowed_for_profile("audit-prod", "scheduler-tick") is False


def test_single_char_glob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """fnmatch '?' matches single char only."""
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          single-char:
            allowed_agents: ["agent-?"]
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    assert is_agent_allowed_for_profile("single-char", "agent-1") is True
    assert is_agent_allowed_for_profile("single-char", "agent-12") is False


def test_multiple_patterns_match_independently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multiple patterns match independently (any pattern => allow)."""
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          multi:
            allowed_agents: ["audit-*", "scheduler-*"]
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    assert is_agent_allowed_for_profile("multi", "audit-row") is True
    assert is_agent_allowed_for_profile("multi", "scheduler-tick") is True
    assert is_agent_allowed_for_profile("multi", "memory-search") is False


def test_invalid_allowed_agents_type_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-list allowed_agents raises ProfileValidationError."""
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          bad:
            allowed_agents: "not-a-list"
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    with pytest.raises(ProfileValidationError, match=r"invalid allowed_agents"):
        is_agent_allowed_for_profile("bad", "agent-x")


def test_unknown_profile_returns_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown profile => True (defer to caller for clearer error path)."""
    yaml_file = _write_profile(
        tmp_path,
        """
        profiles:
          known:
            env:
              FOO: bar
        """,
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    assert is_agent_allowed_for_profile("does-not-exist", "any-agent") is True


def test_inline_profiles_dict_parameter(tmp_path: Path) -> None:
    """Caller may pass a pre-loaded profiles dict to skip disk IO."""
    profiles = {
        "p1": {"allowed_agents": ["worker-*"]},
        "p2": {"env": {"FOO": "bar"}},
    }
    assert is_agent_allowed_for_profile("p1", "worker-1", profiles=profiles) is True
    assert is_agent_allowed_for_profile("p1", "agent-x", profiles=profiles) is False
    assert is_agent_allowed_for_profile("p2", "agent-x", profiles=profiles) is True
