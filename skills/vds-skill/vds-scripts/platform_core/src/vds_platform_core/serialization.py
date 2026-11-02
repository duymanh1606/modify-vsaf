"""Safe model serialization for secret-bearing Pydantic settings (FR-6.2).

Provides :func:`safe_dump` — a helper that accepts any Pydantic model and returns
a plain dict with every ``SecretStr`` value replaced by ``"***"`` so that settings
snapshots can be logged without leaking credentials.

Usage::

    from vds_platform_core.serialization import safe_dump

    # Anywhere you log or serialize a Pydantic model:
    logger.info("config_snapshot", config=safe_dump(settings))

    # Also available as a mixin for settings classes:
    from vds_platform_core.serialization import SafeDumpMixin
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

__all__ = ["SafeDumpMixin", "safe_dump"]


# -----------------------------------------------------------------------
# Sentinel class name — matching by type would require importing pydantic
# at runtime which may not be available in all consumers.
# -----------------------------------------------------------------------
_SECRET_STR_CLASS = "SecretStr"


def safe_dump(model: BaseModel) -> dict[str, Any]:
    """Dump a Pydantic model to a plain dict, redacting all SecretStr fields.

    Works regardless of Pydantic version by walking the output tree and
    replacing any value whose class name is ``SecretStr`` with ``"***"``.

    Args:
        model: Any Pydantic model instance.

    Returns:
        Dictionary representation with all secret values replaced by ``"***"``.
    """
    raw = model.model_dump()
    return _redact_secrets(raw)


def _redact_secrets(value: Any) -> Any:
    """Recursively replace SecretStr instances with ``"***"``."""
    if isinstance(value, dict):
        return {k: _redact_secrets(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    # Match by class name so no runtime pydantic import is needed.
    if getattr(value, "__class__", None) and value.__class__.__name__ == _SECRET_STR_CLASS:
        return "***"
    return value


class SafeDumpMixin(BaseModel):
    """Pydantic mixin that adds a ``safe_dump`` method identical to ``model_dump``
    but with all ``SecretStr`` fields replaced by ``"***"``.

    Inherit from this instead of ``BaseModel`` when you want the convenience
    method on the model itself::

        class MySettings(SafeDumpMixin):
            api_key: SecretStr = Field(default="")
            host: str = "localhost"

        settings = MySettings(api_key="s3cr3t", host="prod")
        assert settings.safe_dump()["api_key"] == "***"
        assert settings.safe_dump()["host"] == "prod"
    """

    def safe_dump(self) -> dict[str, Any]:  # type: ignore[override]
        """Return a dict with all ``SecretStr`` fields replaced by ``"***"``."""
        return safe_dump(self)
