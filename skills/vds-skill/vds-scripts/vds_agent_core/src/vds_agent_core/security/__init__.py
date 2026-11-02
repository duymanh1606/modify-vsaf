"""Security primitives shared across vds_agent_core consumers."""

from vds_agent_core.security.credentials import (
    RAW_CREDENTIAL_PREFIXES,
    looks_like_raw_credential,
    sanitize_text,
)

__all__ = [
    "RAW_CREDENTIAL_PREFIXES",
    "looks_like_raw_credential",
    "sanitize_text",
]
