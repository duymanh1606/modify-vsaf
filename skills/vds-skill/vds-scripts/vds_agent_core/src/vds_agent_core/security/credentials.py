"""Canonical credential sanitization + validation (W7 v20.6.1 consolidation).

Phase 225 W7 dedup-D-2 + logic-B-2 + logic-HIGH-1 unified into one module.
Previous Phase 225 implementations had drift between two surfaces:

- ``vds_agent_core/llm/embedding.py::_sanitize_error`` redacted error MESSAGES
  for logging (post-facto). Patterns covered ``Bearer``, ``sk-``, ``hf_``.
- ``multi_agent_orchestrator/.../models.py``
  rejected raw values at API ingestion (pre-facto). Same prefixes, but the
  ``Bearer`` regex was case-sensitive while the sanitizer was not.

Coverage gaps the W7 consolidation closes:

- HTTP response BODY (``exc.response.text``) was not sanitized — OpenAI 401
  responses can echo the token in JSON. Now ``sanitize_text`` is applied to
  the full message + body concatenation at the ``EmbeddingProviderError``
  raise site.
- URL query params (``?api_key=sk-leak``) were not redacted. Added a
  ``QUERY_PARAM_PATTERN`` that catches ``key|token|secret|api_key=...``.
- JSON body keys with raw token values (``"api_key":"sk-..."``) were not
  redacted in JSON-shaped strings. The token-prefix patterns still catch
  the value; consolidating ensures both surfaces apply identical regex.

This module is the single source of truth. Both ``embedding.py`` and the
multi_agent ``models.py`` import from here.
"""

from __future__ import annotations

import re
from typing import Any

# Public: the raw-credential prefix tuple. Used both by the sanitizer
# (to redact occurrences) and by the validator (to reject raw values).
RAW_CREDENTIAL_PREFIXES: tuple[str, ...] = ("sk-", "hf_", "Bearer ")

# Patterns applied in order. Each tuple is (pattern, replacement).
# Order matters: more specific patterns should run before generic ones so
# their match boundaries don't get clipped by a later substitution.
_SANITIZE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Bearer tokens — case-insensitive prefix, greedy across whitespace.
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-./=+]+", re.IGNORECASE), "[REDACTED]"),
    # OpenAI-shaped keys (`sk-...`).
    (re.compile(r"sk-[A-Za-z0-9_\-./=+]+"), "[REDACTED]"),
    # HuggingFace-shaped tokens (`hf_...`).
    (re.compile(r"hf_[A-Za-z0-9_\-./=+]+"), "[REDACTED]"),
    # URL query-string credentials: ?api_key=..., &token=..., &secret=...,
    # &key=.... Stops at `&`, whitespace, `"`, or end-of-string.
    (
        re.compile(
            r"(?P<lead>[?&](?:api_key|token|secret|key|access_key|auth)=)[^&\s\"']+",
            re.IGNORECASE,
        ),
        r"\g<lead>[REDACTED]",
    ),
    # JSON body fields: "api_key":"<value>" / "token":"<value>".
    (
        re.compile(
            r'(?P<lead>"(?:api_key|token|secret|access_key|auth)"\s*:\s*")[^"]+',
            re.IGNORECASE,
        ),
        r"\g<lead>[REDACTED]",
    ),
]

# Validator regex — matches strings that BEGIN with a raw-credential prefix.
# Used by ``looks_like_raw_credential`` and the multi_agent registration
# validator. The trailing `[A-Za-z0-9_\-./=+]+` is identical across the three
# token-prefix patterns above so accept/reject decisions stay symmetric.
_RAW_CREDENTIAL_RE = re.compile(
    r"^(sk-[A-Za-z0-9_\-./=+]+|hf_[A-Za-z0-9_\-./=+]+|Bearer\s+[A-Za-z0-9_\-./=+]+)$",
    re.IGNORECASE,
)


def sanitize_text(text: str | None) -> str:
    """Redact raw credentials from a free-text string before logging.

    Returns the empty string for ``None`` or ``""`` input. Idempotent:
    sanitizing already-redacted text is a no-op.

    Patterns covered (W7 v20.6.1 consolidation):
    - ``Bearer <token>`` (case-insensitive)
    - ``sk-...`` OpenAI-shape
    - ``hf_...`` HuggingFace-shape
    - URL query params: ``?api_key=...``, ``&token=...``, ``&secret=...``
    - JSON body fields: ``"api_key":"..."``, ``"token":"..."``
    """
    if not text:
        return ""
    out = str(text)
    for pattern, replacement in _SANITIZE_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def looks_like_raw_credential(value: Any) -> bool:
    """Return True if ``value`` is a string matching a raw-credential prefix.

    Used by API request validators to reject raw credentials at ingestion.
    Non-string inputs return False (empty / None / dict / int are not
    credential-shaped).
    """
    if not isinstance(value, str):
        return False
    return bool(_RAW_CREDENTIAL_RE.match(value))
