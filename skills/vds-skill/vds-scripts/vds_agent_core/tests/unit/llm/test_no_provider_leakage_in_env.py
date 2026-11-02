"""No per-provider env vars leak into the namespace (NFR-225.8).

The embedding namespace must remain provider-agnostic — no
`VDS_AGENT_CORE_EMBED__OLLAMA_*` / `_OPENAI_*` keys.
"""

from __future__ import annotations

import re
from pathlib import Path

import vds_agent_core.llm.embedding as embedding_module


def _load_source() -> str:
    return Path(embedding_module.__file__).read_text(encoding="utf-8")


def test_no_per_provider_env_prefix_in_source() -> None:
    src = _load_source()
    matches = re.findall(
        r'env_prefix\s*=\s*"VDS_AGENT_CORE_EMBED__(?:OLLAMA|OPENAI|COHERE|VOYAGE|MISTRAL|JINA|HUGGINGFACE)',
        src,
    )
    assert matches == [], f"Per-provider env_prefix leak: {matches}"


def test_no_per_provider_field_env_in_source() -> None:
    src = _load_source()
    matches = re.findall(
        r'Field\([^)]*"VDS_AGENT_CORE_EMBED__(?:OLLAMA|OPENAI|COHERE|VOYAGE|MISTRAL|JINA|HUGGINGFACE)',
        src,
    )
    assert matches == [], f"Per-provider Field env leak: {matches}"
