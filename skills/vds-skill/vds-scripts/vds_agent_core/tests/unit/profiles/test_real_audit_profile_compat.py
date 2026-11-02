"""Phase 225 W3 — FR-225.22 + FR-226.13 H-10 lock: real audit-profile YAML round-trip.

Anchors the spec's H-10 back-compat hold by exercising the real
``~/.vds/audit.profiles.yaml`` (when available). Skips when absent so the
suite stays deterministic on dev machines.

Two anchor cases:
- Profile WITHOUT embedding block => EmbeddingSettings constructs with defaults.
- Profile WITH synthetic embedding block via tmp file => correct dispatch
  through EMBEDDING_PROVIDERS registry.
"""

from __future__ import annotations

import os
import shutil
import textwrap
from pathlib import Path

import pytest
from vds_agent_core.profiles import (
    apply_runtime_profile,
    build_embedding_settings_for_profile,
    list_runtime_profile_names,
)

REAL_PROFILE_PATH = Path("~/.vds/audit.profiles.yaml").expanduser()


def _scrub_embed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("VDS_AGENT_CORE_EMBED__") or key.startswith("VDS_AUDIT_EMBEDDING__"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def real_profile_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy real audit profile to tmp and re-route the profile env var."""
    if not REAL_PROFILE_PATH.exists():
        pytest.skip(f"{REAL_PROFILE_PATH} not present (dev box)")
    target = tmp_path / "audit.profiles.yaml"
    shutil.copy(REAL_PROFILE_PATH, target)
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(target))
    return target


def test_synthetic_profile_no_embedding_block_uses_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Profile without embedding block => Layer 1 fall-through to defaults."""
    _scrub_embed_env(monkeypatch)
    yaml_file = tmp_path / "synthetic.yaml"
    yaml_file.write_text(
        textwrap.dedent(
            """
            profiles:
              no-embedding:
                env:
                  FOO: bar
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    settings = build_embedding_settings_for_profile("no-embedding")
    assert settings.provider == "ollama"
    assert settings.model_standard == "bge-m3"
    assert settings.dimension == 1024


def test_synthetic_profile_with_embedding_dispatches_through_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Synthetic profile with embedding block dispatches through EMBEDDING_PROVIDERS."""
    _scrub_embed_env(monkeypatch)
    yaml_file = tmp_path / "synthetic.yaml"
    yaml_file.write_text(
        textwrap.dedent(
            """
            profiles:
              hash-embedding:
                model:
                  embedding:
                    type: hash
                    dimension: 1024
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", str(yaml_file))
    settings = build_embedding_settings_for_profile("hash-embedding")
    assert settings.provider == "hash"
    assert settings.dimension == 1024
    # build_client must succeed against the registered factory.
    client = settings.build_client()
    assert client.provider_name == "hash"


def test_real_profiles_back_compat_baseline(
    real_profile_copy: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real audit profiles must continue to load + build embedding settings."""
    _scrub_embed_env(monkeypatch)
    names = list_runtime_profile_names()
    assert names, "expected at least one profile in real audit.profiles.yaml"
    # Sample the first 5 (cheap subset) to keep wall-clock low.
    for name in names[:5]:
        # apply_runtime_profile w/ default parse_embedding=False is the
        # back-compat baseline: it must not raise on real profiles.
        apply_runtime_profile(name, force_override=True)
        # build_embedding_settings_for_profile must also succeed (Layer 1
        # fall-through when no embedding block is present).
        settings = build_embedding_settings_for_profile(name)
        assert settings.provider  # populated string
        assert settings.dimension > 0


def test_real_profiles_parse_embedding_no_break(
    real_profile_copy: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """parse_embedding=True on real profiles (none have type=) must still pass."""
    _scrub_embed_env(monkeypatch)
    names = list_runtime_profile_names()
    for name in names[:5]:
        # Sufficient: no exception. Real profiles use the legacy 3-field
        # embedding block (or none); parse_embedding=True is forward-compatible.
        apply_runtime_profile(name, force_override=True, parse_embedding=True)
