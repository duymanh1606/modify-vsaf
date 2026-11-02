"""Phase 225 W5.3 — cloud-switch dimension-mismatch guardrail.

Verifies FR-225.16(c) first-deploy dimension guard rejects an OpenAI
text-embedding-3-large + DIMENSION=3072 combination because 3072 is neither
the provider default (1536) nor the Qdrant baseline (1024).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from vds_agent_core.llm.embedding import ConfigError, EmbeddingSettings


def test_cloud_switch_dimension_mismatch_raises() -> None:
    """W5.3: PROVIDER=openai + MODEL=text-embedding-3-large + DIMENSION=3072
    (different from Qdrant's 1024 baseline) MUST raise ConfigError per
    FR-225.16(c) first-deploy guard.
    """
    with pytest.raises((ConfigError, ValidationError), match=r"Dimension|dimension"):
        EmbeddingSettings(
            provider="openai",
            model_standard="text-embedding-3-large",
            dimension=3072,
        )
