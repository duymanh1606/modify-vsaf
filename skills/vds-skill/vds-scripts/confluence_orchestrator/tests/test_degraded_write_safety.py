"""Tests for FR-172 degraded-mode write-safety guard in ConfluenceClient."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from confluence_orchestrator.errors import ConfluenceDegradedWriteError
from confluence_orchestrator.http import (
    _WRITE_OPS,
    ConfluenceClient,
)


def _make_stub_client(*, degraded: bool = False) -> ConfluenceClient:
    """Create a minimal ConfluenceClient without hitting the Atlassian SDK."""
    client = ConfluenceClient.__new__(ConfluenceClient)
    client._log = MagicMock()
    client._client = MagicMock()
    client._settings = MagicMock()
    client._server = "internal"
    client._max_retries = 0
    client._retry_backoff_factor = 0.0
    client._retry_max_wait = 30.0
    client._create_params = set()
    client._update_params = set()
    client._degraded = degraded
    return client


# ---------------------------------------------------------------------------
# _WRITE_OPS constant sanity checks
# ---------------------------------------------------------------------------


def test_write_ops_constant_contains_expected_operations() -> None:
    expected = {
        "create_page",
        "update_page",
        "delete_page",
        "upload_attachment",
        "update_attachment",
        "delete_attachment",
        "add_attachment",
        "add_comment",
    }
    assert expected == _WRITE_OPS


def test_write_ops_is_frozenset() -> None:
    assert isinstance(_WRITE_OPS, frozenset)


# ---------------------------------------------------------------------------
# ConfluenceDegradedWriteError
# ---------------------------------------------------------------------------


def test_degraded_write_error_message_contains_operation() -> None:
    exc = ConfluenceDegradedWriteError("create_page My Title")
    assert "create_page My Title" in str(exc)


def test_degraded_write_error_stores_operation_attribute() -> None:
    exc = ConfluenceDegradedWriteError("update_page 123")
    assert exc.operation == "update_page 123"


def test_degraded_write_error_is_runtime_error() -> None:
    exc = ConfluenceDegradedWriteError("add_attachment file.pdf")
    assert isinstance(exc, RuntimeError)


# ---------------------------------------------------------------------------
# ConfluenceClient.is_degraded / mark_degraded
# ---------------------------------------------------------------------------


def test_is_degraded_false_by_default() -> None:
    client = _make_stub_client(degraded=False)
    assert client.is_degraded is False


def test_mark_degraded_sets_flag() -> None:
    client = _make_stub_client(degraded=False)
    client.mark_degraded()
    assert client.is_degraded is True


# ---------------------------------------------------------------------------
# Write-safety guard in _with_retry()
# ---------------------------------------------------------------------------


def test_write_op_on_degraded_client_raises_without_calling_operation() -> None:
    client = _make_stub_client(degraded=True)
    called = {"count": 0}

    def operation():
        called["count"] += 1
        return {"id": "1"}

    with pytest.raises(ConfluenceDegradedWriteError):
        client._with_retry(operation, "create_page My Page")

    assert called["count"] == 0, "Operation must not be invoked when client is degraded"


def test_write_op_error_includes_operation_name() -> None:
    client = _make_stub_client(degraded=True)

    with pytest.raises(ConfluenceDegradedWriteError) as exc_info:
        client._with_retry(lambda: None, "update_page 99")

    assert "update_page 99" in str(exc_info.value)


def test_all_write_ops_blocked_when_degraded() -> None:
    client = _make_stub_client(degraded=True)
    for op in _WRITE_OPS:
        # Use operation name with extra context (space-separated), as callers do.
        operation_name = f"{op} some-arg"
        with pytest.raises(ConfluenceDegradedWriteError, match=op):
            client._with_retry(lambda: None, operation_name)


def test_read_op_on_degraded_client_executes_normally() -> None:
    client = _make_stub_client(degraded=True)
    called = {"count": 0}

    def operation():
        called["count"] += 1
        return {"results": []}

    result = client._with_retry(operation, "get_page 123")
    assert result == {"results": []}
    assert called["count"] == 1


def test_non_degraded_client_executes_write_normally() -> None:
    client = _make_stub_client(degraded=False)
    called = {"count": 0}

    def operation():
        called["count"] += 1
        return {"id": "created"}

    result = client._with_retry(operation, "create_page A New Page")
    assert result == {"id": "created"}
    assert called["count"] == 1


def test_cql_search_not_in_write_ops() -> None:
    """Verify read-path operations are not in _WRITE_OPS."""
    read_ops = {"get_page", "search_cql", "cql_advanced", "get_space", "get_child_pages"}
    assert not read_ops.intersection(_WRITE_OPS)


# ---------------------------------------------------------------------------
# delete_page guard (bypasses _with_retry)
# ---------------------------------------------------------------------------


def test_delete_page_on_degraded_client_raises() -> None:
    client = _make_stub_client(degraded=True)
    with pytest.raises(ConfluenceDegradedWriteError) as exc_info:
        client.delete_page("page-123")
    assert "delete_page" in str(exc_info.value)
    assert "page-123" in str(exc_info.value)


def test_delete_page_on_non_degraded_client_calls_sdk() -> None:
    client = _make_stub_client(degraded=False)
    client._client.remove_page = MagicMock(return_value=None)
    client.delete_page("page-456")
    client._client.remove_page.assert_called_once_with(page_id="page-456")
