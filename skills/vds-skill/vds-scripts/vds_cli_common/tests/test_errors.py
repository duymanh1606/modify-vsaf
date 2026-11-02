"""Tests for ErrorHandler and ExitCodes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import typer

from vds_cli_common import CLIContext, ErrorHandler, ExitCodes, OutputManager


class TestExitCodes:
    """Tests for ExitCodes enum."""

    def test_success_is_zero(self) -> None:
        """Test SUCCESS is 0."""
        assert ExitCodes.SUCCESS == 0

    def test_general_error_is_one(self) -> None:
        """Test GENERAL_ERROR is 1."""
        assert ExitCodes.GENERAL_ERROR == 1

    def test_all_codes_are_integers(self) -> None:
        """Test all exit codes are integers."""
        for code in ExitCodes:
            assert isinstance(code.value, int)

    def test_codes_are_unique(self) -> None:
        """Test all exit codes are unique."""
        values = [code.value for code in ExitCodes]
        assert len(values) == len(set(values))


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    @pytest.fixture
    def handler(self) -> ErrorHandler:
        """Create an ErrorHandler for testing."""
        ctx = CLIContext.from_options(json_only=True)
        output = OutputManager(ctx)
        return ErrorHandler(output, valid_commands=["search", "count", "ping", "export"])

    def test_suggest_command_finds_match(self, handler: ErrorHandler) -> None:
        """Test suggest_command finds close matches."""
        assert handler.suggest_command("serch") == "search"
        assert handler.suggest_command("cout") == "count"
        assert handler.suggest_command("pimg") == "ping"

    def test_suggest_command_no_match(self, handler: ErrorHandler) -> None:
        """Test suggest_command returns None for no match."""
        assert handler.suggest_command("xyz") is None
        assert handler.suggest_command("foo") is None

    def test_suggest_command_exact_match(self, handler: ErrorHandler) -> None:
        """Test suggest_command works with exact match."""
        assert handler.suggest_command("search") == "search"

    def test_suggest_command_custom_cutoff(self, handler: ErrorHandler) -> None:
        """Test suggest_command respects cutoff parameter."""
        # With high cutoff, weak matches should fail
        assert handler.suggest_command("s", cutoff=0.9) is None
        # With low cutoff, weak matches might succeed
        result = handler.suggest_command("sear", cutoff=0.5)
        assert result is not None

    def test_handle_unknown_command_exits(self, handler: ErrorHandler) -> None:
        """Test handle_unknown_command exits with USAGE_ERROR."""
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_unknown_command("foo")
        assert exc_info.value.exit_code == ExitCodes.USAGE_ERROR

    def test_handle_unknown_command_with_suggestion(self, handler: ErrorHandler) -> None:
        """Test handle_unknown_command provides suggestion."""
        handler.output = MagicMock()
        with pytest.raises(typer.Exit):
            handler.handle_unknown_command("serch")
        # Should have called output_error
        handler.output.output_error.assert_called_once()

    def test_handle_config_error_exits(self, handler: ErrorHandler) -> None:
        """Test handle_config_error exits with CONFIG_ERROR."""
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_config_error("Missing config")
        assert exc_info.value.exit_code == ExitCodes.CONFIG_ERROR

    def test_handle_config_error_with_missing_vars(self, handler: ErrorHandler) -> None:
        """Test handle_config_error includes missing variables."""
        handler.output = MagicMock()
        with pytest.raises(typer.Exit):
            handler.handle_config_error(
                "Config error",
                missing_vars=["VAR1", "VAR2"],
            )
        handler.output.output_error.assert_called_once()
        call_kwargs = handler.output.output_error.call_args[1]
        assert "missing_variables" in call_kwargs["details"]

    def test_handle_auth_error_exits(self, handler: ErrorHandler) -> None:
        """Test handle_auth_error exits with AUTH_ERROR."""
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_auth_error("Invalid credentials")
        assert exc_info.value.exit_code == ExitCodes.AUTH_ERROR

    def test_handle_permission_error_exits(self, handler: ErrorHandler) -> None:
        """Test handle_permission_error exits with PERMISSION_ERROR."""
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_permission_error("Access denied")
        assert exc_info.value.exit_code == ExitCodes.PERMISSION_ERROR

    def test_handle_permission_error_with_roles(self, handler: ErrorHandler) -> None:
        """Test handle_permission_error includes role information."""
        handler.output = MagicMock()
        with pytest.raises(typer.Exit):
            handler.handle_permission_error(
                "Access denied",
                required_role="admin",
                current_role="viewer",
            )
        call_kwargs = handler.output.output_error.call_args[1]
        assert call_kwargs["details"]["required_role"] == "admin"
        assert call_kwargs["details"]["current_role"] == "viewer"

    def test_handle_network_error_exits(self, handler: ErrorHandler) -> None:
        """Test handle_network_error exits with NETWORK_ERROR."""
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_network_error("Connection failed")
        assert exc_info.value.exit_code == ExitCodes.NETWORK_ERROR

    def test_handle_network_error_with_url(self, handler: ErrorHandler) -> None:
        """Test handle_network_error includes URL."""
        handler.output = MagicMock()
        with pytest.raises(typer.Exit):
            handler.handle_network_error(
                "Connection failed",
                url="http://example.com",
            )
        call_kwargs = handler.output.output_error.call_args[1]
        assert call_kwargs["details"]["url"] == "http://example.com"

    def test_handle_not_found_exits(self, handler: ErrorHandler) -> None:
        """Test handle_not_found exits with NOT_FOUND_ERROR."""
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_not_found("Index", "logs-*")
        assert exc_info.value.exit_code == ExitCodes.NOT_FOUND_ERROR

    def test_handle_validation_error_exits(self, handler: ErrorHandler) -> None:
        """Test handle_validation_error exits with VALIDATION_ERROR."""
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_validation_error("Invalid input")
        assert exc_info.value.exit_code == ExitCodes.VALIDATION_ERROR

    def test_handle_validation_error_with_field(self, handler: ErrorHandler) -> None:
        """Test handle_validation_error includes field information."""
        handler.output = MagicMock()
        with pytest.raises(typer.Exit):
            handler.handle_validation_error(
                "Invalid input",
                field="index",
                expected="string",
            )
        call_kwargs = handler.output.output_error.call_args[1]
        assert call_kwargs["details"]["field"] == "index"
        assert call_kwargs["details"]["expected"] == "string"

    def test_handle_general_error_exits(self, handler: ErrorHandler) -> None:
        """Test handle_general_error exits with GENERAL_ERROR."""
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_general_error("Something went wrong")
        assert exc_info.value.exit_code == ExitCodes.GENERAL_ERROR

    def test_handle_general_error_with_hint(self, handler: ErrorHandler) -> None:
        """Test handle_general_error includes hint."""
        handler.output = MagicMock()
        with pytest.raises(typer.Exit):
            handler.handle_general_error(
                "Error",
                hint="Try again",
                details={"key": "value"},
            )
        handler.output.output_error.assert_called_once_with(
            "Error",
            hint="Try again",
            details={"key": "value"},
        )


class TestHandleHttpError:
    """Tests for ErrorHandler.handle_http_error (VAMI-018 T-F3-2).

    Covers F-3: previously every client-side exception funnelled through
    handle_network_error's VPN hint, hiding 400/422 validation failures and
    5xx server errors. handle_http_error now dispatches by type + status.
    """

    @pytest.fixture
    def handler(self) -> ErrorHandler:
        ctx = CLIContext.from_options(json_only=True)
        output = OutputManager(ctx)
        return ErrorHandler(output, valid_commands=["store", "search"])

    @staticmethod
    def _status_error(status_code: int, body: dict[str, object] | str) -> Exception:
        import httpx

        if isinstance(body, dict):
            response = httpx.Response(status_code=status_code, json=body)
        else:
            response = httpx.Response(status_code=status_code, text=body)
        return httpx.HTTPStatusError("simulated", request=httpx.Request("POST", "http://x"), response=response)

    def test_400_routes_to_validation_error(self, handler: ErrorHandler) -> None:
        exc = self._status_error(400, {"detail": "content contains dangerous content"})
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_http_error(exc, url="http://localhost:8010")
        assert exc_info.value.exit_code == ExitCodes.VALIDATION_ERROR

    def test_422_routes_to_validation_error(self, handler: ErrorHandler) -> None:
        exc = self._status_error(422, {"detail": [{"msg": "field required", "loc": ["body", "session_id"]}]})
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_http_error(exc, url="http://localhost:8010")
        assert exc_info.value.exit_code == ExitCodes.VALIDATION_ERROR

    def test_401_routes_to_auth_error(self, handler: ErrorHandler) -> None:
        exc = self._status_error(401, {"detail": "token expired"})
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_http_error(exc, url="http://localhost:8010")
        assert exc_info.value.exit_code == ExitCodes.AUTH_ERROR

    def test_404_routes_to_not_found(self, handler: ErrorHandler) -> None:
        exc = self._status_error(404, {"detail": "Memory not found"})
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_http_error(exc, url="http://localhost:8010/memories/abc")
        assert exc_info.value.exit_code == ExitCodes.NOT_FOUND_ERROR

    def test_500_routes_to_general_error_with_server_hint(self, handler: ErrorHandler) -> None:
        handler.output = MagicMock()
        exc = self._status_error(500, "Internal Server Error")
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_http_error(exc, url="http://localhost:8010")
        assert exc_info.value.exit_code == ExitCodes.GENERAL_ERROR
        call_kwargs = handler.output.output_error.call_args[1]
        assert "API logs" in call_kwargs["hint"]

    def test_timeout_preserves_network_hint(self, handler: ErrorHandler) -> None:
        import httpx

        exc = httpx.TimeoutException("request timed out")
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_http_error(exc, url="http://localhost:8010")
        assert exc_info.value.exit_code == ExitCodes.NETWORK_ERROR

    def test_connect_error_preserves_network_hint(self, handler: ErrorHandler) -> None:
        import httpx

        exc = httpx.ConnectError("cannot connect")
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_http_error(exc, url="http://localhost:8010")
        assert exc_info.value.exit_code == ExitCodes.NETWORK_ERROR

    def test_unknown_exception_routes_to_general_error(self, handler: ErrorHandler) -> None:
        exc = RuntimeError("something unusual")
        with pytest.raises(typer.Exit) as exc_info:
            handler.handle_http_error(exc, url="http://localhost:8010")
        assert exc_info.value.exit_code == ExitCodes.GENERAL_ERROR

    def test_400_detail_surfaced_into_validation_hint(self, handler: ErrorHandler) -> None:
        handler.output = MagicMock()
        exc = self._status_error(400, {"detail": "content contains dangerous content"})
        with pytest.raises(typer.Exit):
            handler.handle_http_error(exc, url="http://localhost:8010")
        call_kwargs = handler.output.output_error.call_args[1]
        # handle_validation_error writes "expected" into details
        assert "dangerous content" in call_kwargs["details"].get("expected", "")
