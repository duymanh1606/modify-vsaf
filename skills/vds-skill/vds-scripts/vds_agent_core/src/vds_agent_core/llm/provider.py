"""LLM client abstraction — Protocol + LiteLLM-backed default.

This is NOT a copy of audit_orchestrator/llm/provider.py. It defines a
clean LLMClient Protocol with a LiteLLM-backed default implementation.
The audit provider (Codex OAuth, native Anthropic SDK) stays in audit.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from vds_agent_core.config import LLMRuntimeConfig

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """Generic LLM client contract. All providers satisfy this."""

    async def chat(self, messages: list[dict], *, model: str, **kwargs: Any) -> str: ...

    async def chat_json(self, messages: list[dict], *, model: str, schema: type[T], **kwargs: Any) -> T: ...


class LiteLLMClient:
    """Default LLMClient backed by litellm (optional dep).

    Install: pip install vds-agent-core[litellm]
    """

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    async def chat(self, messages: list[dict], *, model: str, **kwargs: Any) -> str:
        try:
            import litellm
        except ImportError as e:
            raise ImportError("Install vds-agent-core[litellm] for LLM support") from e
        response = await litellm.acompletion(model=model, messages=messages, **kwargs)
        return response.choices[0].message.content or ""  # type: ignore[union-attr]

    async def chat_json(self, messages: list[dict], *, model: str, schema: type[T], **kwargs: Any) -> T:
        try:
            import litellm
        except ImportError as e:
            raise ImportError("Install vds-agent-core[litellm] for LLM support") from e
        response = await litellm.acompletion(model=model, messages=messages, response_format=schema, **kwargs)
        content: str = response.choices[0].message.content or ""  # type: ignore[union-attr]
        return schema.model_validate_json(content)


class HttpxDirectClient:
    """Minimal LLMClient using httpx directly — OpenAI-compatible endpoints only.

    This is the base implementation when litellm is not installed.
    """

    def __init__(self, *, base_url: str = "https://api.openai.com/v1", api_key: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def chat(self, messages: list[dict], *, model: str, **kwargs: Any) -> str:
        import httpx

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {"model": model, "messages": messages, "temperature": 0.0, **kwargs}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"] or ""

    async def chat_json(self, messages: list[dict], *, model: str, schema: type[T], **kwargs: Any) -> T:
        content = await self.chat(messages, model=model, **kwargs)
        # Strip markdown fences if present
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return schema.model_validate_json(content)


class LLMSettings(LLMRuntimeConfig):
    """Config-backed factory for LLMClient instances.

    Inherits BaseSettings — loads from env vars and ~/.vds/.env automatically.
    """

    @classmethod
    def for_agent(
        cls,
        agent_id: str,
        *,
        profile: str | None = None,
        api_settings: Any = None,
        overrides: dict[str, Any] | None = None,
    ) -> LLMSettings:
        """Build per-agent LLM settings via the 3-layer cascade (FR-226.1).

        Resolution precedence (highest -> lowest):
            1. ``overrides`` -- programmatic kwargs (tests/replays).
            2. ``api_settings.llm_settings`` -- Agent model from Redis/API.
            3. ``VDS_AGENT_<AGENT_ID>_LLM__*`` env vars.
            4. ``cls()`` defaults (env file + orchestrator subclass prefix).

        Path B wins over Path A on conflict (FR-226.7); a structured WARN log
        records the disagreement. Settings construction is side-effect-free
        (FR-226.11) -- no I/O is performed here.

        Args:
            agent_id: Agent identifier (sanitized internally).
            profile: Reserved for W3 profile YAML lookup; accepted now but
                full enforcement (NFR-225.13 allowed_agents) lands in W3.
            api_settings: Object with an optional ``llm_settings: dict`` field
                (typically the Agent model loaded from Redis).
            overrides: Programmatic field overrides.

        Returns:
            New ``LLMSettings`` instance with the resolved field values.
        """
        from vds_agent_core.llm._cascade import resolve_for_agent

        return resolve_for_agent(
            cls,
            agent_id,
            kind="llm",
            env_prefix_template="VDS_AGENT_{sanitized}_LLM__",
            api_attr="llm_settings",
            profile=profile,
            api_settings=api_settings,
            overrides=overrides,
        )

    def build_client(self) -> LLMClient:
        """Build an LLMClient. Uses LiteLLM if installed, falls back to httpx."""
        try:
            import litellm  # availability probe
        except ImportError:
            return HttpxDirectClient(
                base_url=self.base_url or "https://api.openai.com/v1",
                api_key=self.api_key,
            )
        return LiteLLMClient(settings=self)

    def select_model(self, tier: str = "standard") -> str:
        """Select model by tier name. Returns provider/model format for LiteLLM."""
        models = {
            "simple": self.model_simple,
            "standard": self.model_standard,
            "complex": self.model_complex,
        }
        return models.get(tier, self.model_standard)

    def build_pydantic_ai_model(self, tier: str = "standard") -> Any:
        """Build a pydantic-ai OpenAIChatModel backed by LiteLLMProvider.

        Requires pydantic-ai with LiteLLM support. Model strings must use
        LiteLLM's provider/model format: 'openai/gpt-4o', 'anthropic/claude-opus-4-5'.

        Works with LiteLLM proxy endpoints too (point base_url at the proxy).
        """
        try:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.litellm import LiteLLMProvider
        except ImportError as e:
            raise ImportError("Install vds-agent-core[litellm] and pydantic-ai for build_pydantic_ai_model()") from e
        return OpenAIChatModel(
            self.select_model(tier),  # must be "provider/model" format
            provider=LiteLLMProvider(api_base=self.base_url, api_key=self.api_key),
        )
