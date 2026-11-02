"""Error handling for VDS CLIs.

This module provides:
- ExitCodes: Standard exit codes for all VDS CLIs
- ErrorHandler: Unified error handling with suggestions and hints

Usage:
    from vds_cli_common import ErrorHandler, ExitCodes

    handler = ErrorHandler(output_manager, valid_commands=["search", "count"])

    try:
        result = operation()
    except PermissionError:
        handler.handle_permission_error("Access denied", required_role="admin")
"""

from __future__ import annotations

import difflib
from enum import IntEnum
from typing import TYPE_CHECKING, Any, NoReturn

import typer

from vds_cli_common.paths import get_shared_env_path

if TYPE_CHECKING:
    from .output import OutputManager


class ExitCodes(IntEnum):
    """Standard exit codes for all VDS CLIs.

    These codes provide consistent exit status across all CLIs,
    making it easier to handle errors in scripts and automation.
    """

    SUCCESS = 0
    """Operation completed successfully."""

    GENERAL_ERROR = 1
    """Unspecified error occurred."""

    USAGE_ERROR = 2
    """Invalid arguments or bad command."""

    CONFIG_ERROR = 3
    """Missing environment variables or bad configuration."""

    AUTH_ERROR = 4
    """Invalid credentials or expired token."""

    PERMISSION_ERROR = 5
    """403 Forbidden - insufficient rights."""

    NOT_FOUND_ERROR = 6
    """404 Not Found - resource doesn't exist."""

    NETWORK_ERROR = 7
    """Connection failed or timeout."""

    VALIDATION_ERROR = 8
    """Invalid input data."""


class ErrorHandler:
    """Unified error handling for VDS CLIs.

    Provides:
    - Consistent error formatting
    - Typo suggestions for commands
    - Actionable hints for common errors
    - Proper exit codes

    Args:
        output: OutputManager instance for error output
        valid_commands: List of valid commands for typo suggestions
    """

    def __init__(
        self,
        output: OutputManager,
        valid_commands: list[str] | None = None,
    ) -> None:
        """Initialize ErrorHandler.

        Args:
            output: OutputManager for error output
            valid_commands: Optional list of valid commands for suggestions
        """
        self.output = output
        self.valid_commands = valid_commands or []

    def suggest_command(self, typo: str, cutoff: float = 0.6) -> str | None:
        """Suggest a valid command based on fuzzy matching.

        Args:
            typo: The mistyped command
            cutoff: Minimum similarity ratio (0.0 to 1.0)

        Returns:
            Best matching command or None if no match found
        """
        matches = difflib.get_close_matches(
            typo,
            self.valid_commands,
            n=1,
            cutoff=cutoff,
        )
        return matches[0] if matches else None

    def handle_unknown_command(self, command: str) -> NoReturn:
        """Handle unknown command with suggestion.

        Args:
            command: The unknown command

        Raises:
            typer.Exit: Always exits with USAGE_ERROR
        """
        suggestion = self.suggest_command(command)

        hint = None
        if suggestion:
            hint = f"Did you mean: [cyan]{suggestion}[/cyan]?"
        elif self.valid_commands:
            available = ", ".join(self.valid_commands[:5])
            hint = f"Available commands: {available}"

        self.output.output_error(
            f"Unknown command: '{command}'",
            hint=hint,
        )
        raise typer.Exit(ExitCodes.USAGE_ERROR)

    def handle_config_error(
        self,
        message: str,
        *,
        missing_vars: list[str] | None = None,
        config_path: str | None = None,
    ) -> NoReturn:
        """Handle configuration error with guidance.

        Args:
            message: Error message
            missing_vars: List of missing environment variable names
            config_path: Path to configuration file

        Raises:
            typer.Exit: Always exits with CONFIG_ERROR
        """
        resolved_config_path = config_path or str(get_shared_env_path())
        details: dict[str, str] = {"config_file": resolved_config_path}
        if missing_vars:
            details["missing_variables"] = ", ".join(missing_vars)

        self.output.output_error(
            message,
            hint=f"Check your configuration at {resolved_config_path}",
            details=details,
        )
        raise typer.Exit(ExitCodes.CONFIG_ERROR)

    def handle_auth_error(
        self,
        message: str,
        *,
        service: str = "API",
    ) -> NoReturn:
        """Handle authentication error.

        Args:
            message: Error message
            service: Name of the service (for hint)

        Raises:
            typer.Exit: Always exits with AUTH_ERROR
        """
        self.output.output_error(
            message,
            hint=f"Verify your {service} credentials in {get_shared_env_path()}",
            details={"service": service},
        )
        raise typer.Exit(ExitCodes.AUTH_ERROR)

    def handle_permission_error(
        self,
        message: str,
        *,
        required_role: str | None = None,
        current_role: str | None = None,
    ) -> NoReturn:
        """Handle permission error with role information.

        Args:
            message: Error message
            required_role: Role required for the operation
            current_role: User's current role

        Raises:
            typer.Exit: Always exits with PERMISSION_ERROR
        """
        details: dict[str, str] = {}
        if required_role:
            details["required_role"] = required_role
        if current_role:
            details["current_role"] = current_role

        hint = "Request elevated access from your administrator"
        if required_role:
            hint = f"Required role: {required_role}. Contact admin for access."

        self.output.output_error(message, hint=hint, details=details)
        raise typer.Exit(ExitCodes.PERMISSION_ERROR)

    def handle_network_error(
        self,
        message: str,
        *,
        url: str | None = None,
    ) -> NoReturn:
        """Handle network/connection error.

        Args:
            message: Error message
            url: URL that failed to connect

        Raises:
            typer.Exit: Always exits with NETWORK_ERROR
        """
        hints = [
            "Check your VPN connection",
            "Verify the service URL is correct",
            "Ensure network connectivity",
        ]

        details: dict[str, str] = {}
        if url:
            details["url"] = url

        self.output.output_error(
            message,
            hint=" | ".join(hints),
            details=details,
        )
        raise typer.Exit(ExitCodes.NETWORK_ERROR)

    def handle_not_found(
        self,
        resource_type: str,
        resource_id: str,
    ) -> NoReturn:
        """Handle resource not found error.

        Args:
            resource_type: Type of resource (e.g., "Index", "Page")
            resource_id: ID or name of the resource

        Raises:
            typer.Exit: Always exits with NOT_FOUND_ERROR
        """
        self.output.output_error(
            f"{resource_type} not found: '{resource_id}'",
            hint=f"Verify the {resource_type.lower()} exists and you have access",
        )
        raise typer.Exit(ExitCodes.NOT_FOUND_ERROR)

    def handle_validation_error(
        self,
        message: str,
        *,
        field: str | None = None,
        expected: str | None = None,
    ) -> NoReturn:
        """Handle input validation error.

        Args:
            message: Error message
            field: Field that failed validation
            expected: Expected value or format

        Raises:
            typer.Exit: Always exits with VALIDATION_ERROR
        """
        details: dict[str, str] = {}
        if field:
            details["field"] = field
        if expected:
            details["expected"] = expected

        self.output.output_error(
            message,
            hint="Check your input and try again",
            details=details,
        )
        raise typer.Exit(ExitCodes.VALIDATION_ERROR)

    def handle_general_error(
        self,
        message: str,
        *,
        hint: str | None = None,
        details: dict[str, str] | None = None,
    ) -> NoReturn:
        """Handle general error with optional hint and details.

        Args:
            message: Error message
            hint: Optional hint for resolution
            details: Optional additional details

        Raises:
            typer.Exit: Always exits with GENERAL_ERROR
        """
        self.output.output_error(message, hint=hint, details=details)
        raise typer.Exit(ExitCodes.GENERAL_ERROR)

    def handle_http_error(
        self,
        exc: Any,
        *,
        url: str | None = None,
        resource_id: str | None = None,
        resource_type: str = "Resource",
    ) -> NoReturn:
        """Dispatch HTTP-ish exceptions to the most specific handler.

        Added in VAMI-018 (F-3) to replace blanket ``handle_network_error(...)``
        catches that were hiding 400/422 validation failures and 5xx server
        errors behind a misleading VPN / network hint. Inspects the exception
        type and (for ``httpx.HTTPStatusError``) the response status code, then
        dispatches to the appropriate ``handle_*`` method so operators get
        actionable detail instead of a generic "check your VPN" message.

        - ``httpx.HTTPStatusError`` with 4xx -> validation / not-found / auth /
          permission per status; detail is pulled from the response body.
        - ``httpx.HTTPStatusError`` with 5xx -> general error with server-side
          hint pointing at the API logs.
        - ``httpx.TimeoutException`` / ``httpx.ConnectError`` /
          ``httpx.NetworkError`` -> network error (the original, legitimate
          use of the VPN hint).
        - Anything else -> general error with ``str(exc)`` as the message.

        VAMI-026: ``resource_id`` and ``resource_type`` kwargs added so CLI
        callers can surface context-aware 404 messages
        (e.g. "Memory not found: 'pg_abc-123'") instead of the generic
        "Resource not found: 'http://localhost:8010'" that results when
        only ``url`` is provided. Both kwargs are optional — existing
        callers remain backward-compatible.

        Raises:
            typer.Exit: Always exits via the delegated handler.
        """
        try:
            import httpx
        except ImportError:  # pragma: no cover - httpx is a hard dep in practice
            httpx = None  # type: ignore[assignment]

        # HTTP status errors (4xx/5xx) — branch on status code
        if httpx is not None and isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            detail = _extract_detail(exc)

            if status_code in (400, 422):
                self.handle_validation_error(
                    f"Request rejected (HTTP {status_code})",
                    field=None,
                    expected=detail,
                )
            if status_code in (401, 403):
                self.handle_auth_error(
                    f"Authentication failed (HTTP {status_code}): {detail}",
                )
            if status_code == 404:
                self.handle_not_found(
                    resource_type,
                    resource_id or url or detail or "unknown",
                )
            if 500 <= status_code < 600:
                self.handle_general_error(
                    f"Server error (HTTP {status_code})",
                    hint=("Check API logs (docker logs vds-ai-memory-api-1) or stack health (vds-cli memory health)"),
                    details={"url": url, "detail": detail}  # type: ignore[dict-item]
                    if url
                    else {"detail": detail},
                )
            # Other 4xx codes that don't have a dedicated handler
            self.handle_general_error(
                f"Unexpected HTTP {status_code}: {detail}",
                hint="Check the service state or the CLI invocation",
                details={"url": url} if url else None,
            )

        # Network / timeout — the legitimate VPN-hint case
        if httpx is not None and isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
            self.handle_network_error(str(exc) or exc.__class__.__name__, url=url)

        # Fallback for unknown exception types (ensures the "VPN" hint never
        # surfaces unless we're genuinely in a network-error branch)
        self.handle_general_error(
            str(exc) or exc.__class__.__name__,
            hint="Unexpected error — re-run with -v for detail",
            details={"url": url, "error_type": exc.__class__.__name__}  # type: ignore[dict-item]
            if url
            else {"error_type": exc.__class__.__name__},
        )


def _extract_detail(exc: Any) -> str:
    """Best-effort extraction of a human-readable detail from an httpx error.

    Prefers the ``detail`` field of a JSON body (FastAPI/Pydantic convention),
    falls back to the first 200 chars of the body text, then to ``str(exc)``.
    """
    try:
        body = exc.response.json()
    except Exception:
        try:
            text = (exc.response.text or "")[:200].strip()
        except Exception:
            text = ""
        return text or str(exc)

    result = str(body)[:200]
    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, str):
            result = detail
        elif isinstance(detail, list) and detail:
            first = detail[0]
            result = str(first["msg"]) if isinstance(first, dict) and "msg" in first else str(first)
        elif detail is not None:
            result = str(detail)
        else:
            message = body.get("message")
            if isinstance(message, str):
                result = message
    return result
