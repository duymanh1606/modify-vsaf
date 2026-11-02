"""Auth middleware: inject CredentialResolver into HTTPClient headers."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vds_platform_core.protocols import CredentialResolver, HTTPClient


class _AuthWrappedClient:
    def __init__(self, client: HTTPClient, resolver: CredentialResolver, header_name: str) -> None:
        self._client, self._resolver, self._header_name = client, resolver, header_name

    def _inject(self, kw: dict[str, Any]) -> dict[str, Any]:
        if (token := self._resolver.resolve()) is None:
            return kw
        headers: dict[str, str] = dict(kw.get("headers") or {})
        headers.setdefault(self._header_name, token)
        return {**kw, "headers": headers}

    async def get(self, url: str, **kw: Any) -> Any:
        return await self._client.get(url, **self._inject(kw))

    async def post(self, url: str, **kw: Any) -> Any:
        return await self._client.post(url, **self._inject(kw))

    async def aclose(self) -> None:
        await self._client.aclose()


def with_auth(client: HTTPClient, resolver: CredentialResolver, *, header_name: str = "Authorization") -> HTTPClient:
    """Return *client* wrapped to inject *resolver*'s credential as a request header."""
    return _AuthWrappedClient(client, resolver, header_name)  # type: ignore[return-value]
