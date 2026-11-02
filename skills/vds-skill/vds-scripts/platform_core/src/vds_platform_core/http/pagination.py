"""Generic async paginator — platform_core.http.pagination (TSK-7.17)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vds_platform_core.protocols import HTTPClient


async def paginate(
    client: HTTPClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    page_param: str = "page",
    size_param: str = "page_size",
    page_size: int = 100,
    items_extractor: Callable[[dict[str, Any]], list[dict[str, Any]]] = lambda r: r.get("items", []),
    next_extractor: Callable[[dict[str, Any]], str | None] | None = None,
    max_pages: int = 10000,
) -> AsyncIterator[dict[str, Any]]:
    """Async generator that pages through an HTTP resource.

    Two styles:
    - Page-number (default): increments ``page_param`` each call until
      ``items_extractor`` returns an empty list.
    - Cursor-based: if ``next_extractor`` is provided, follows its returned
      URL/token until it returns ``None``.

    Raises RuntimeError after ``max_pages`` iterations (runaway API guard).
    """
    base_params: dict[str, Any] = dict(params or {})
    page_count = 0
    current_url: str | None = url

    if next_extractor is not None:
        # --- Cursor-based pagination ---
        while current_url is not None:
            if page_count >= max_pages:
                raise RuntimeError(f"paginate: max_pages={max_pages} exceeded on {url!r}")
            response: dict[str, Any] = await client.get(current_url, params=base_params)
            for item in items_extractor(response):
                yield item
            current_url = next_extractor(response)
            page_count += 1
    else:
        # --- Page-number pagination ---
        page = 1
        while True:
            if page_count >= max_pages:
                raise RuntimeError(f"paginate: max_pages={max_pages} exceeded on {url!r}")
            req_params = {**base_params, page_param: page, size_param: page_size}
            response = await client.get(url, params=req_params)
            items = items_extractor(response)
            if not items:
                break
            for item in items:
                yield item
            page += 1
            page_count += 1


__all__ = ["paginate"]
