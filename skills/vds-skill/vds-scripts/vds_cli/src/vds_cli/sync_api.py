"""HTTP central-state clients for instruction sync."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class SyncApiError(RuntimeError):
    """Base error for central-state HTTP client failures."""


class SyncApiRevisionConflict(SyncApiError):
    """Raised when optimistic concurrency check fails."""


class SyncApiTransientError(SyncApiError):
    """Raised when HTTP/network failures are transient and retryable."""


@dataclass(frozen=True)
class SyncApiDocument:
    """Canonical document representation returned by central-state API."""

    content: str
    revision: str
    content_hash: str
    source_file: str
    updated_at: str


@dataclass
class SyncApiClient:
    """Generic HTTP client with If-Match/If-None-Match semantics."""

    endpoint: str
    timeout_seconds: int = 10
    auth_token: str | None = None

    def pull_document(self) -> SyncApiDocument | None:
        request = Request(
            self.endpoint,
            headers=self._auth_headers(),
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = self._read_json_response(response)
                if payload is None:
                    return None
                revision = _normalize_revision(
                    etag=response.headers.get("ETag"),
                    payload_revision=payload.get("revision"),
                )
                return _payload_to_document(payload, revision=revision)
        except HTTPError as exc:
            if exc.code == 404:
                return None
            if _is_transient_http_code(exc.code):
                raise SyncApiTransientError(f"Transient HTTP {exc.code} when pulling central document.") from exc
            raise SyncApiError(f"HTTP {exc.code} when pulling central document.") from exc
        except URLError as exc:
            raise SyncApiTransientError(f"Network error pulling central document: {exc.reason}") from exc

    def push_document_if_match(
        self,
        *,
        content: str,
        source_file: str,
        expected_revision: str | None,
    ) -> SyncApiDocument:
        headers = {
            "Content-Type": "application/json",
            **self._auth_headers(),
        }
        if expected_revision is None:
            headers["If-None-Match"] = "*"
        else:
            headers["If-Match"] = _format_etag(expected_revision)

        payload = {
            "content": content,
            "source_file": source_file,
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = self._read_json_response(response)
                if response_payload is None:
                    document = self.pull_document()
                    if document is None:
                        raise SyncApiError(
                            "Central API returned empty PUT response and GET could not load canonical document."
                        ) from None
                    return document
                revision = _normalize_revision(
                    etag=response.headers.get("ETag"),
                    payload_revision=response_payload.get("revision"),
                )
                return _payload_to_document(response_payload, revision=revision)
        except HTTPError as exc:
            if exc.code == 412:
                raise SyncApiRevisionConflict("Central revision mismatch (HTTP 412).") from exc
            if _is_transient_http_code(exc.code):
                raise SyncApiTransientError(f"Transient HTTP {exc.code} when pushing central document.") from exc
            raise SyncApiError(f"HTTP {exc.code} when pushing central document.") from exc
        except URLError as exc:
            raise SyncApiTransientError(f"Network error pushing central document: {exc.reason}") from exc

    def _auth_headers(self) -> dict[str, str]:
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}

    @staticmethod
    def _read_json_response(response) -> dict[str, object] | None:
        raw = response.read()
        if not raw:
            return None
        try:
            loaded = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SyncApiError("Central API returned non-JSON response payload.") from exc
        if not isinstance(loaded, dict):
            raise SyncApiError("Central API payload must be a JSON object.")
        return loaded


@dataclass
class VdsAiMemorySyncApiClient:
    """VDS AI Memory contract adapter (`/api/v1/memories/{memory_id}`)."""

    base_url: str
    memory_id: str
    user_id: str
    session_id: str
    timeout_seconds: int = 10
    auth_token: str | None = None

    def pull_document(self) -> SyncApiDocument | None:
        request = Request(self._memory_url, headers=self._auth_headers(), method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = SyncApiClient._read_json_response(response)
                if payload is None:
                    return None
                return _memory_payload_to_document(payload)
        except HTTPError as exc:
            if exc.code == 404:
                return None
            if _is_transient_http_code(exc.code):
                raise SyncApiTransientError(f"Transient HTTP {exc.code} when pulling VDS AI Memory document.") from exc
            raise SyncApiError(f"HTTP {exc.code} when pulling VDS AI Memory document.") from exc
        except URLError as exc:
            raise SyncApiTransientError(f"Network error pulling VDS AI Memory document: {exc.reason}") from exc

    def push_document_if_match(
        self,
        *,
        content: str,
        source_file: str,
        expected_revision: str | None,
    ) -> SyncApiDocument:
        current = self.pull_document()
        if current is None:
            if expected_revision is not None:
                raise SyncApiRevisionConflict(
                    "Central VDS AI Memory record missing while expected revision was provided."
                )
            return self._create_memory(content=content, source_file=source_file)

        if expected_revision is not None and current.revision != expected_revision:
            raise SyncApiRevisionConflict(
                f"Central revision mismatch (expected={expected_revision}, actual={current.revision})."
            )

        expected_revision_number = _parse_int_revision(expected_revision) if expected_revision is not None else None
        if expected_revision is not None and expected_revision_number is None:
            raise SyncApiError("VDS AI Memory expected revision must be an integer current_version_number.")

        payload = {
            "content": content,
            "metadata": _sync_metadata(
                source_file=source_file,
                content=content,
            ),
            "user_id": self.user_id,
            "session_id": self.session_id,
        }
        headers = {
            "Content-Type": "application/json",
            **self._auth_headers(),
        }
        if expected_revision_number is not None:
            payload["expected_current_version_number"] = expected_revision_number
            headers["If-Match"] = _format_etag(str(expected_revision_number))

        request = Request(
            self._memory_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PATCH",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                patch_payload = SyncApiClient._read_json_response(response)
                if patch_payload is not None:
                    return _memory_payload_to_document(patch_payload)
                refreshed = self.pull_document()
                if refreshed is None:
                    raise SyncApiError("VDS AI Memory patch succeeded but follow-up GET returned empty response.")
                return refreshed
        except HTTPError as exc:
            if exc.code == 409:
                raise SyncApiRevisionConflict("Central revision mismatch (HTTP 409).") from exc
            if _is_transient_http_code(exc.code):
                raise SyncApiTransientError(f"Transient HTTP {exc.code} when pushing VDS AI Memory document.") from exc
            raise SyncApiError(f"HTTP {exc.code} when pushing VDS AI Memory document.") from exc
        except URLError as exc:
            raise SyncApiTransientError(f"Network error pushing VDS AI Memory document: {exc.reason}") from exc

    @property
    def _api_base(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/api/v1"):
            return base
        return f"{base}/api/v1"

    @property
    def _memory_url(self) -> str:
        return f"{self._api_base}/memories/{quote(self.memory_id, safe='')}"

    @property
    def _create_url(self) -> str:
        return f"{self._api_base}/memories"

    def _create_memory(self, *, content: str, source_file: str) -> SyncApiDocument:
        payload = {
            "content": content,
            "category": "reference",
            "importance": "medium",
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": _sync_metadata(source_file=source_file, content=content),
        }
        request = Request(
            self._create_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **self._auth_headers(),
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                create_payload = SyncApiClient._read_json_response(response)
        except HTTPError as exc:
            if _is_transient_http_code(exc.code):
                raise SyncApiTransientError(f"Transient HTTP {exc.code} when creating VDS AI Memory record.") from exc
            raise SyncApiError(f"HTTP {exc.code} when creating VDS AI Memory record.") from exc
        except URLError as exc:
            raise SyncApiTransientError(f"Network error creating VDS AI Memory record: {exc.reason}") from exc

        if create_payload is None:
            raise SyncApiError("VDS AI Memory create response was empty.")
        created_id = create_payload.get("memory_id")
        if not isinstance(created_id, str) or not created_id.strip():
            raise SyncApiError("VDS AI Memory create response missing memory_id.")
        self.memory_id = created_id
        created = self.pull_document()
        if created is None:
            raise SyncApiError("VDS AI Memory create succeeded but follow-up GET failed.")
        return created

    def _auth_headers(self) -> dict[str, str]:
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}


@dataclass
class ConfluencePropertySyncApiClient:
    """Confluence content-property contract adapter."""

    base_url: str
    page_id: str
    property_key: str
    timeout_seconds: int = 10
    auth_token: str | None = None
    username: str | None = None
    password: str | None = None

    def pull_document(self) -> SyncApiDocument | None:
        request = Request(self._property_url, headers=self._auth_headers(), method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = SyncApiClient._read_json_response(response)
                if payload is None:
                    return None
                return _confluence_property_payload_to_document(payload)
        except HTTPError as exc:
            if exc.code == 404:
                return None
            if _is_transient_http_code(exc.code):
                raise SyncApiTransientError(
                    f"Transient HTTP {exc.code} when pulling Confluence sync property."
                ) from exc
            raise SyncApiError(f"HTTP {exc.code} when pulling Confluence sync property.") from exc
        except URLError as exc:
            raise SyncApiTransientError(f"Network error pulling Confluence sync property: {exc.reason}") from exc

    def push_document_if_match(
        self,
        *,
        content: str,
        source_file: str,
        expected_revision: str | None,
    ) -> SyncApiDocument:
        current = self.pull_document()
        if expected_revision is None:
            if current is not None:
                raise SyncApiRevisionConflict(
                    f"Expected empty Confluence property but found revision {current.revision}."
                )
            return self._create_property(content=content, source_file=source_file)

        if current is None:
            raise SyncApiRevisionConflict("Expected existing Confluence property revision but property was missing.")
        if current.revision != expected_revision:
            raise SyncApiRevisionConflict(
                f"Central revision mismatch (expected={expected_revision}, actual={current.revision})."
            )

        next_version = _next_revision_number(current.revision)
        payload = {
            "key": self.property_key,
            "value": _sync_payload_value(
                source_file=source_file,
                content=content,
            ),
            "version": {"number": next_version},
        }
        request = Request(
            self._property_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **self._auth_headers(),
            },
            method="PUT",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = SyncApiClient._read_json_response(response)
                if response_payload is None:
                    refreshed = self.pull_document()
                    if refreshed is None:
                        raise SyncApiError(
                            "Confluence sync property update succeeded but follow-up GET failed."
                        ) from None
                    return refreshed
                return _confluence_property_payload_to_document(response_payload)
        except HTTPError as exc:
            if exc.code in {409, 412}:
                raise SyncApiRevisionConflict("Central revision mismatch from Confluence.") from exc
            if _is_transient_http_code(exc.code):
                raise SyncApiTransientError(
                    f"Transient HTTP {exc.code} when pushing Confluence sync property."
                ) from exc
            raise SyncApiError(f"HTTP {exc.code} when pushing Confluence sync property.") from exc
        except URLError as exc:
            raise SyncApiTransientError(f"Network error pushing Confluence sync property: {exc.reason}") from exc

    @property
    def _property_url(self) -> str:
        return (
            f"{self.base_url.rstrip('/')}/rest/api/content/{quote(self.page_id, safe='')}/property/"
            f"{quote(self.property_key, safe='')}"
        )

    @property
    def _create_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/rest/api/content/{quote(self.page_id, safe='')}/property"

    def _create_property(self, *, content: str, source_file: str) -> SyncApiDocument:
        payload = {
            "key": self.property_key,
            "value": _sync_payload_value(source_file=source_file, content=content),
        }
        request = Request(
            self._create_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **self._auth_headers(),
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = SyncApiClient._read_json_response(response)
        except HTTPError as exc:
            if exc.code in {409, 412}:
                raise SyncApiRevisionConflict("Confluence property create conflict.") from exc
            if _is_transient_http_code(exc.code):
                raise SyncApiTransientError(
                    f"Transient HTTP {exc.code} when creating Confluence sync property."
                ) from exc
            raise SyncApiError(f"HTTP {exc.code} when creating Confluence sync property.") from exc
        except URLError as exc:
            raise SyncApiTransientError(f"Network error creating Confluence sync property: {exc.reason}") from exc

        if response_payload is None:
            refreshed = self.pull_document()
            if refreshed is None:
                raise SyncApiError("Confluence property create succeeded but follow-up GET failed.")
            return refreshed
        return _confluence_property_payload_to_document(response_payload)

    def _auth_headers(self) -> dict[str, str]:
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        if self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode("ascii")
            return {"Authorization": f"Basic {token}"}
        return {}


def _format_etag(revision: str) -> str:
    candidate = revision.strip()
    if candidate.startswith('"') and candidate.endswith('"'):
        return candidate
    return f'"{candidate}"'


def _normalize_revision(*, etag: str | None, payload_revision: object | None) -> str:
    if etag:
        candidate = etag.strip()
        if candidate.startswith("W/"):
            candidate = candidate[2:].strip()
        if candidate.startswith('"') and candidate.endswith('"') and len(candidate) >= 2:
            candidate = candidate[1:-1]
        if candidate:
            return candidate
    if payload_revision is not None:
        value = str(payload_revision).strip()
        if value:
            return value
    raise SyncApiError("Central API response missing revision/ETag.")


def _payload_to_document(payload: dict[str, object], *, revision: str) -> SyncApiDocument:
    content = _first_str(payload, ("content", "document_body", "body"))
    if content is None:
        raise SyncApiError("Central API payload missing content field.")
    content_hash = _first_str(payload, ("content_hash",))
    if content_hash is None:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source_file = _first_str(payload, ("source_file",))
    if source_file is None:
        source_file = "<remote>"
    updated_at = _first_str(payload, ("updated_at",))
    if updated_at is None:
        updated_at = datetime.now(UTC).isoformat()
    return SyncApiDocument(
        content=content,
        revision=revision,
        content_hash=content_hash,
        source_file=source_file,
        updated_at=updated_at,
    )


def _memory_payload_to_document(payload: dict[str, object]) -> SyncApiDocument:
    content = _first_str(payload, ("content",))
    if content is None:
        raise SyncApiError("VDS AI Memory payload missing content field.")

    metadata = payload.get("metadata")
    metadata_dict: dict[str, object] = metadata if isinstance(metadata, dict) else {}

    revision_obj = payload.get("current_version_number")
    if revision_obj is None:
        revision_obj = payload.get("updated_at")
    if revision_obj is None:
        raise SyncApiError("VDS AI Memory payload missing revision field.")
    revision = str(revision_obj)

    source_file = _first_str(metadata_dict, ("sync_source_file",))
    if source_file is None:
        source_file = _first_str(payload, ("source_file",))
    if source_file is None:
        source_file = "<vds-ai-memory>"

    content_hash = _first_str(metadata_dict, ("sync_content_hash",))
    if content_hash is None:
        content_hash = _first_str(payload, ("content_hash",))
    if content_hash is None:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    updated_at = _first_str(payload, ("updated_at",))
    if updated_at is None:
        updated_at = _first_str(metadata_dict, ("sync_updated_at",))
    if updated_at is None:
        updated_at = datetime.now(UTC).isoformat()

    return SyncApiDocument(
        content=content,
        revision=revision,
        content_hash=content_hash,
        source_file=source_file,
        updated_at=updated_at,
    )


def _confluence_property_payload_to_document(payload: dict[str, object]) -> SyncApiDocument:
    value = payload.get("value")
    value_dict: dict[str, object] = value if isinstance(value, dict) else {}

    content = _first_str(value_dict, ("content", "document_body", "body"))
    if content is None and isinstance(value, str):
        content = value
    if content is None:
        raise SyncApiError("Confluence property payload missing content value.")

    version_payload = payload.get("version")
    version_dict: dict[str, object] = version_payload if isinstance(version_payload, dict) else {}
    revision_obj = version_dict.get("number")
    if revision_obj is None:
        raise SyncApiError("Confluence property payload missing version.number.")
    revision = str(revision_obj)

    source_file = _first_str(value_dict, ("source_file",))
    if source_file is None:
        source_file = "<confluence-property>"

    content_hash = _first_str(value_dict, ("content_hash",))
    if content_hash is None:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    updated_at = _first_str(value_dict, ("updated_at",))
    if updated_at is None:
        updated_at = _first_str(version_dict, ("when",))
    if updated_at is None:
        updated_at = datetime.now(UTC).isoformat()

    return SyncApiDocument(
        content=content,
        revision=revision,
        content_hash=content_hash,
        source_file=source_file,
        updated_at=updated_at,
    )


def _sync_metadata(*, source_file: str, content: str) -> dict[str, str]:
    return {
        "sync_source_file": source_file,
        "sync_content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "sync_updated_at": datetime.now(UTC).isoformat(),
    }


def _sync_payload_value(*, source_file: str, content: str) -> dict[str, str]:
    return {
        "content": content,
        "source_file": source_file,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _next_revision_number(revision: str) -> int:
    try:
        return int(revision) + 1
    except ValueError as exc:
        raise SyncApiError(f"Confluence revision is not an integer: {revision}") from exc


def _first_str(payload: dict[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _parse_int_revision(revision: str | None) -> int | None:
    if revision is None:
        return None
    try:
        return int(revision)
    except ValueError:
        return None


def _is_transient_http_code(code: int) -> bool:
    return code in {408, 429} or 500 <= code < 600
