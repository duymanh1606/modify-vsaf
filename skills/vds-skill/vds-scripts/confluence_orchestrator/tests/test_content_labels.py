"""Unit tests for ContentClient label methods (FR-03).

Tests verify that:
- get_page_labels() extracts 'name' strings from raw SDK result
- set_page_label() delegates cleanly to the HTTP layer
- Edge cases: empty result, non-dict entries in raw response
"""

from __future__ import annotations

from typing import Any

import pytest
from confluence_orchestrator.content import ContentClient


class DummyHttp:
    """Minimal ConfluenceClient stub for label-method tests."""

    def __init__(self) -> None:
        self._labels: dict[str, list[dict[str, Any]]] = {}
        self.get_labels_calls: list[str] = []
        self.set_label_calls: list[tuple[str, str]] = []

    def get_page_labels(self, page_id: str) -> list[dict[str, Any]]:
        self.get_labels_calls.append(page_id)
        return self._labels.get(page_id, [])

    def set_page_label(self, page_id: str, label: str) -> None:
        self.set_label_calls.append((page_id, label))


@pytest.fixture()
def http() -> DummyHttp:
    return DummyHttp()


@pytest.fixture()
def client(http: DummyHttp) -> ContentClient:
    return ContentClient(http)  # type: ignore[arg-type]


class TestGetPageLabels:
    def test_returns_name_strings(self, client: ContentClient, http: DummyHttp) -> None:
        http._labels["42"] = [{"name": "api"}, {"name": "backend"}]
        assert client.get_page_labels("42") == ["api", "backend"]

    def test_empty_result_returns_empty_list(self, client: ContentClient, http: DummyHttp) -> None:
        http._labels["99"] = []
        assert client.get_page_labels("99") == []

    def test_page_with_no_registered_labels_returns_empty(self, client: ContentClient, http: DummyHttp) -> None:
        # Key not in _labels dict — HTTP layer returns []
        assert client.get_page_labels("7") == []

    def test_delegates_to_http_with_correct_page_id(self, client: ContentClient, http: DummyHttp) -> None:
        http._labels["7"] = [{"name": "foo"}]
        client.get_page_labels("7")
        assert http.get_labels_calls == ["7"]

    def test_filters_non_dict_entries(self, client: ContentClient, http: DummyHttp) -> None:
        # Guard against malformed SDK responses
        http._labels["5"] = [{"name": "valid"}, "bad-string", None, 42]  # type: ignore[list-item]
        result = client.get_page_labels("5")
        assert result == ["valid"]

    def test_missing_name_key_returns_empty_string(self, client: ContentClient, http: DummyHttp) -> None:
        http._labels["3"] = [{"id": "x"}, {"name": "labeled"}]
        result = client.get_page_labels("3")
        assert result == ["", "labeled"]

    def test_single_label(self, client: ContentClient, http: DummyHttp) -> None:
        http._labels["1"] = [{"name": "doc"}]
        assert client.get_page_labels("1") == ["doc"]


class TestSetPageLabel:
    def test_delegates_to_http(self, client: ContentClient, http: DummyHttp) -> None:
        client.set_page_label("42", "my-label")
        assert http.set_label_calls == [("42", "my-label")]

    def test_page_id_and_label_forwarded_correctly(self, client: ContentClient, http: DummyHttp) -> None:
        client.set_page_label("page-123", "security")
        assert http.set_label_calls[0] == ("page-123", "security")

    def test_multiple_sequential_calls_all_forwarded(self, client: ContentClient, http: DummyHttp) -> None:
        client.set_page_label("1", "alpha")
        client.set_page_label("1", "beta")
        client.set_page_label("2", "gamma")
        assert http.set_label_calls == [("1", "alpha"), ("1", "beta"), ("2", "gamma")]

    def test_returns_none(self, client: ContentClient, http: DummyHttp) -> None:
        result = client.set_page_label("1", "tag")
        assert result is None
