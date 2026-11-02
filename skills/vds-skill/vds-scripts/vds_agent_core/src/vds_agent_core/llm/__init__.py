"""LLM and embedding client abstractions."""

from vds_agent_core.llm.cache import (
    AnalysisCache,
    CacheEntry,
    CacheStats,
    EmbeddingCache,
    LLMResponseCache,
)
from vds_agent_core.llm.embedding import (
    EMBEDDING_PROVIDERS,
    PROVIDER_DEFAULTS,
    ConfigError,
    EmbeddingClient,
    EmbeddingProviderError,
    EmbeddingRuntimeConfig,
    EmbeddingSettings,
    HashEmbeddingClient,
    LiteLLMEmbeddingClient,
    LocalEmbeddingClient,
    OllamaEmbeddingClient,
    OpenAIEmbeddingClient,
    register_provider,
)
from vds_agent_core.llm.provider import (
    HttpxDirectClient,
    LiteLLMClient,
    LLMClient,
    LLMSettings,
)

__all__ = [
    "EMBEDDING_PROVIDERS",
    "PROVIDER_DEFAULTS",
    "AnalysisCache",
    "CacheEntry",
    "CacheStats",
    "ConfigError",
    "EmbeddingCache",
    "EmbeddingClient",
    "EmbeddingProviderError",
    "EmbeddingRuntimeConfig",
    "EmbeddingSettings",
    "HashEmbeddingClient",
    "HttpxDirectClient",
    "LLMClient",
    "LLMResponseCache",
    "LLMSettings",
    "LiteLLMClient",
    "LiteLLMEmbeddingClient",
    "LocalEmbeddingClient",
    "OllamaEmbeddingClient",
    "OpenAIEmbeddingClient",
    "register_provider",
]
