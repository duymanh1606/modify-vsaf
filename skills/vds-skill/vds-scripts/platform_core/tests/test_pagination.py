"""Tests for platform_core.http.pagination — TSK-7.17."""

from __future__ import annotations

from typing import Any

import pytest
from vds_platform_core.http.pagination import paginate


# ---------------------------------------------------------------------------
# Minimal HTTPClient stub — returns pre-canned responses in order
# ---------------------------------------------------------------------------
class _StubClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._iter = iter(responses)
        self.calls: list[dict[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"url": url, **kwargs})
        return next(self._iter)  # type: ignore[arg-type]

    async def post(self, url: str, **kwargs: Any) -> dict[str, Any]:  # pragma: no cover
        return {}

    async def aclose(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Page-number style
# ---------------------------------------------------------------------------
class TestPageNumberPagination:
    @pytest.mark.asyncio
    async def test_yields_all_items_across_pages(self) -> None:
        client = _StubClient(
            [
                {"items": [{"id": 1}, {"id": 2}]},
                {"items": [{"id": 3}]},
                {"items": []},
            ]
        )
        results = [item async for item in paginate(client, "/things")]
        assert [r["id"] for r in results] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_empty_first_page_yields_nothing(self) -> None:
        client = _StubClient([{"items": []}])
        results = [item async for item in paginate(client, "/empty")]
        assert results == []

    @pytest.mark.asyncio
    async def test_page_and_size_params_sent(self) -> None:
        client = _StubClient(
            [
                {"items": [{"id": 1}]},
                {"items": []},
            ]
        )
        async for _ in paginate(client, "/x", page_param="p", size_param="sz", page_size=5):
            pass
        first_params = client.calls[0]["params"]
        assert first_params["p"] == 1
        assert first_params["sz"] == 5
        assert client.calls[1]["params"]["p"] == 2

    @pytest.mark.asyncio
    async def test_custom_items_extractor(self) -> None:
        client = _StubClient(
            [
                {"results": [{"n": "a"}, {"n": "b"}]},
                {"results": []},
            ]
        )
        results = [item async for item in paginate(client, "/r", items_extractor=lambda r: r.get("results", []))]
        assert [r["n"] for r in results] == ["a", "b"]

    @pytest.mark.asyncio
    async def test_max_pages_guard_fires(self) -> None:
        # Returns a non-empty page every time — should hit max_pages=2
        client = _StubClient([{"items": [{"id": i}]} for i in range(10)])
        with pytest.raises(RuntimeError, match="max_pages=2"):
            async for _ in paginate(client, "/inf", max_pages=2):
                pass


# ---------------------------------------------------------------------------
# Cursor-based style
# ---------------------------------------------------------------------------
class TestCursorPagination:
    @pytest.mark.asyncio
    async def test_cursor_yields_items_until_none(self) -> None:
        client = _StubClient(
            [
                {"items": [{"id": 1}], "next": "/things?cursor=2"},
                {"items": [{"id": 2}], "next": "/things?cursor=3"},
                {"items": [{"id": 3}], "next": None},
            ]
        )
        results = [
            item
            async for item in paginate(
                client,
                "/things",
                next_extractor=lambda r: r.get("next"),
            )
        ]
        assert [r["id"] for r in results] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_cursor_follows_next_url(self) -> None:
        client = _StubClient(
            [
                {"items": [{"id": 1}], "cursor": "tok1"},
                {"items": [{"id": 2}], "cursor": None},
            ]
        )
        async for _ in paginate(
            client,
            "/start",
            next_extractor=lambda r: f"/next?cursor={r['cursor']}" if r["cursor"] else None,
        ):
            pass
        assert client.calls[0]["url"] == "/start"
        assert client.calls[1]["url"] == "/next?cursor=tok1"

    @pytest.mark.asyncio
    async def test_cursor_max_pages_guard_fires(self) -> None:
        # Always returns a next link
        client = _StubClient([{"items": [{"id": i}], "next": f"/p{i + 1}"} for i in range(10)])
        with pytest.raises(RuntimeError, match="max_pages=3"):
            async for _ in paginate(
                client,
                "/start",
                next_extractor=lambda r: r.get("next"),
                max_pages=3,
            ):
                pass

    @pytest.mark.asyncio
    async def test_async_for_pattern(self) -> None:
        """Verify the typical async for usage pattern works end-to-end."""
        client = _StubClient(
            [
                {"items": [{"x": 1}, {"x": 2}]},
                {"items": []},
            ]
        )
        collected: list[dict[str, Any]] = []
        async for item in paginate(client, "/api/resources"):
            collected.append(item)
        assert len(collected) == 2
        assert collected[0]["x"] == 1
