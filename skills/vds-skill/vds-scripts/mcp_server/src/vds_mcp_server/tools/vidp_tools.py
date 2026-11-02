"""VIDP tools for MCP server.

Thin wrappers around ``vds-cli vidp ...`` so the VIDP gateway is reachable
from any MCP client that talks to the ``vds-orchestrator`` server.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register_vidp_tools(mcp: FastMCP, execute_cli: Callable[..., Any]) -> None:
    """Register VIDP tools with the MCP server."""

    @mcp.tool()
    async def vidp_trigger(workflow: str, payload: Any | None = None) -> str:
        """Trigger a VIDP third-party action by workflow UUID or alias.

        Maps to ``POST /third-party/v2/start/{workflow_id}``.

        Args:
            workflow: VIDP workflow UUID (e.g. ``4afa9a1d-d36c-441a-b2fd-ba9612a854c1``)
                OR a friendly alias defined in ``~/.vds/vidp-workflows.json``
                (e.g. ``build-jenkins-by-job-name``). Aliases are case-insensitive.
            payload: Optional JSON payload. Any JSON-serialisable object;
                does not need to start with ``tenantToken``.

        Returns:
            JSON string with endpoint, alias used (if any), workflowId, request
            payload, and full response.
        """
        args: list[str] = ["vidp", "trigger", workflow]
        if payload is not None:
            args.extend(["--payload", json.dumps(payload)])
        result = await execute_cli(*args)
        if result["returncode"] != 0:
            return f"Error: {result['stderr'] or result['stdout']}"
        return result["stdout"]

    @mcp.tool()
    async def vidp_status(job_id: str, raw: bool = False) -> str:
        """Get full workflow/stage detail for a VIDP job.

        Maps to ``GET /third-party/v2/status/{job_id}?full=true``.

        Args:
            job_id: VIDP job id.
            raw: If true, return only the raw VIDP response.

        Returns:
            JSON string with normalized job state and the raw VIDP response.
        """
        args: list[str] = ["vidp", "status", job_id]
        if raw:
            args.append("--raw")
        result = await execute_cli(*args)
        if result["returncode"] != 0:
            return f"Error: {result['stderr'] or result['stdout']}"
        return result["stdout"]
