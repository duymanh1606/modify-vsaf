"""Credential helpers for VDS orchestrators."""

from __future__ import annotations

import os
from dataclasses import dataclass

from pydantic import SecretStr


def resolve_secret(value: SecretStr | str | None) -> str | None:
    """Unwrap SecretStr to plain str; pass through str; None/empty -> None.

    Idempotent: ``resolve_secret(resolve_secret(x)) == resolve_secret(x)``.
    """
    if value is None:
        return None
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    return value or None


@dataclass
class HeaderAuthResolver:
    """Header-based credential resolver -- default CredentialResolver binding.

    Reads *token_field* from the process environment on each :meth:`resolve`
    call.  *header_name* carries the intended HTTP header (e.g.
    ``"Authorization"``).
    """

    token_field: str
    header_name: str

    def resolve(self) -> str | None:
        """Return the token from env, or ``None`` if absent/empty."""
        return os.getenv(self.token_field) or None


__all__ = ["HeaderAuthResolver", "resolve_secret"]
