"""HTTP client for the VIDP third-party gateway."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx
from vds_platform_core.http.errors import map_http_error

if TYPE_CHECKING:
    from vds_vidp_orchestrator.config import VidpSettings


class VidpClient:
    """Thin synchronous client around the two VIDP endpoints we expose."""

    def __init__(self, settings: VidpSettings) -> None:
        self.settings = settings
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.settings.normalized_base_url,
                headers={"Accept": "application/json", **self.settings.auth_header},
                timeout=self.settings.timeout_seconds,
            )
        return self._client

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        response = client.request(method, path, json=json_body)
        try:
            data: Any = response.json()
        except ValueError:
            data = {"raw": response.text}

        if not response.is_success:
            raise map_http_error(response.status_code, data, service="vidp")
        return data if isinstance(data, dict) else {"data": data}

    def trigger(self, workflow_id: str, payload: Any | None = None) -> dict[str, Any]:
        """Trigger a third-party action by workflow id.

        Mirrors ``POST /third-party/v2/start/{workflowId}``.
        """
        body = payload if payload is not None else {}
        path = f"third-party/v2/start/{quote(workflow_id, safe='')}"
        return self._request("POST", path, json_body=body)

    def status(self, job_id: str) -> dict[str, Any]:
        """Fetch full workflow/stage status for a VIDP job.

        Mirrors ``GET /third-party/v2/status/{jobId}?full=true``.
        """
        path = f"third-party/v2/status/{quote(job_id, safe='')}?full=true"
        return self._request("GET", path)

    @staticmethod
    def normalize_status(raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten the nested status response into the shape the original MCP returned."""
        data = raw.get("data") or {}
        workflows_raw = data.get("workflows") or []
        workflows = []
        for wf in workflows_raw:
            steps = (wf or {}).get("steps") or {}
            stages_raw = steps.get("stages") or []
            workflows.append(
                {
                    "name": (wf or {}).get("name"),
                    "status": (wf or {}).get("status"),
                    "stepStatus": steps.get("status"),
                    "stages": [
                        {"name": (s or {}).get("name"), "status": (s or {}).get("status")}
                        for s in stages_raw
                    ],
                }
            )
        return {
            "jobName": data.get("name"),
            "jobStatus": data.get("status"),
            "workflows": workflows,
        }

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> VidpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


__all__ = ["VidpClient"]
