"""W7 v20.6.1 regression tests for canonical credential sanitization.

Locks the `vds_agent_core.security.credentials` consolidation against the
specific leak vectors flagged by the W7 logic agent (B-2 + HIGH-1) and the
dedup auditor (D-2 — pattern divergence between embedding.py and models.py).
"""

from __future__ import annotations

import pytest
from vds_agent_core.security.credentials import (
    RAW_CREDENTIAL_PREFIXES,
    looks_like_raw_credential,
    sanitize_text,
)


class TestSanitizeText:
    """``sanitize_text`` is the single source of truth for credential redaction."""

    def test_none_input_returns_empty(self) -> None:
        assert sanitize_text(None) == ""

    def test_empty_input_returns_empty(self) -> None:
        assert sanitize_text("") == ""

    def test_bearer_token_redacted(self) -> None:
        assert "[REDACTED]" in sanitize_text("Authorization: Bearer abc123def")
        assert "abc123def" not in sanitize_text("Authorization: Bearer abc123def")

    def test_bearer_case_insensitive(self) -> None:
        assert "secret" not in sanitize_text("BEARER secret-token-xyz")
        assert "secret" not in sanitize_text("bearer secret-token-xyz")

    def test_sk_token_redacted(self) -> None:
        result = sanitize_text("invalid token sk-1234567890abcdef provided")
        assert "sk-1234567890abcdef" not in result
        assert "[REDACTED]" in result

    def test_hf_token_redacted(self) -> None:
        result = sanitize_text("HuggingFace key hf_LEAK1234 was rejected")
        assert "hf_LEAK1234" not in result
        assert "[REDACTED]" in result

    def test_url_query_param_api_key_redacted(self) -> None:
        """W7 logic-HIGH-1 fix: tokens in URL query params must be redacted."""
        url = "https://api.example.com/v1/embeddings?api_key=sk-leaky-key&model=foo"
        result = sanitize_text(url)
        assert "sk-leaky-key" not in result
        # The query param structure is preserved with redaction
        assert "api_key=[REDACTED]" in result

    def test_url_query_param_token_redacted(self) -> None:
        url = "https://api.example.com/v1/foo?token=abcdef123&other=keep"
        result = sanitize_text(url)
        assert "abcdef123" not in result
        assert "token=[REDACTED]" in result
        # Non-secret query params survive
        assert "other=keep" in result

    def test_url_query_param_secret_redacted(self) -> None:
        url = "https://api.example.com?secret=topsecret&access_key=akey"
        result = sanitize_text(url)
        assert "topsecret" not in result
        assert "akey" not in result

    def test_json_body_api_key_redacted(self) -> None:
        """W7 logic-B-2 fix: token in JSON error body must be redacted."""
        body = '{"error": {"message": "invalid", "api_key": "sk-leak123"}}'
        result = sanitize_text(body)
        assert "sk-leak123" not in result

    def test_json_body_token_field_redacted(self) -> None:
        body = '{"meta": {"token": "raw-secret-value"}}'
        result = sanitize_text(body)
        assert "raw-secret-value" not in result
        # Pattern preserves whitespace between colon and quote.
        assert "[REDACTED]" in result
        assert '"token"' in result

    def test_idempotent(self) -> None:
        """Sanitizing already-redacted text is a no-op."""
        once = sanitize_text("Bearer sk-foo123")
        twice = sanitize_text(once)
        assert once == twice

    def test_multiple_tokens_in_one_string(self) -> None:
        text = "tried Bearer abc, then sk-def, finally hf_ghi"
        result = sanitize_text(text)
        assert "abc" not in result
        assert "sk-def" not in result
        assert "hf_ghi" not in result
        assert result.count("[REDACTED]") == 3


class TestLooksLikeRawCredential:
    """Validator-side contract: reject raw credentials at API ingestion."""

    @pytest.mark.parametrize(
        "value",
        [
            "sk-test-1234567890",
            "hf_TOKEN_123456",
            "Bearer abc-def-ghi",
            "bearer lowercase-also-rejected",
            "BEARER UPPERCASE",
        ],
    )
    def test_raw_credentials_match(self, value: str) -> None:
        assert looks_like_raw_credential(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            "${env:OPENAI_API_KEY}",
            "${env:HF_TOKEN}",
            "skylar",  # ``sk`` prefix without dash
            "hf-not-underscore",
            "hello world",
            "",
            None,
            42,
            {"api_key": "sk-foo"},  # not a string
            ["sk-foo"],
        ],
    )
    def test_non_credentials_pass(self, value: object) -> None:
        assert looks_like_raw_credential(value) is False

    def test_raw_credential_prefixes_constant_complete(self) -> None:
        """The constant must enumerate every prefix the regex catches."""
        assert RAW_CREDENTIAL_PREFIXES == ("sk-", "hf_", "Bearer ")
