"""Tests for webhook management with SonarQube event notifications."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vds_sonarqube_orchestrator.webhooks import (
    WebhookConfig,
    WebhookDeliveryResult,
    WebhookError,
    WebhookManager,
)


class MockAsyncContextManager:
    """Helper class to create a proper async context manager for mocking."""

    def __init__(
        self, return_value: Any = None, status: int = 200, should_raise: Exception | None = None
    ) -> None:
        self.return_value = return_value
        self.status = status
        self.should_raise = should_raise

    async def __aenter__(self) -> MockAsyncContextManager:
        if self.should_raise:
            raise self.should_raise
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary config file for testing."""
    return tmp_path / "webhooks.json"


@pytest.fixture
def sample_webhook_data() -> dict[str, Any]:
    """Sample webhook data for testing."""
    return {
        "id": "wh-123",
        "url": "http://example.com/webhook",
        "events": ["scan_complete", "quality_gate_change"],
        "secret": "test_secret",
        "project_key": "test-project",
        "created_at": "2025-01-15T10:30:00",
        "enabled": True,
    }


class TestWebhookConfig:
    def test_to_dict_masks_secret(self) -> None:
        """Test that to_dict masks the secret value."""
        webhook = WebhookConfig(
            id="wh-123",
            url="http://example.com/webhook",
            events=["scan_complete"],
            secret="my_secret",
            project_key="test-project",
        )

        data = webhook.to_dict()
        assert data["secret"] == "***"
        assert data["url"] == "http://example.com/webhook"

    def test_to_dict_no_secret(self) -> None:
        """Test to_dict when there's no secret."""
        webhook = WebhookConfig(
            id="wh-123",
            url="http://example.com/webhook",
            events=["scan_complete"],
            secret=None,
        )

        data = webhook.to_dict()
        assert data["secret"] is None

    def test_to_storage_dict_preserves_secret(self) -> None:
        """Test that to_storage_dict preserves the secret value."""
        webhook = WebhookConfig(
            id="wh-123",
            url="http://example.com/webhook",
            events=["scan_complete"],
            secret="my_secret",
        )

        data = webhook.to_storage_dict()
        assert data["secret"] == "my_secret"

    def test_from_dict(self) -> None:
        """Test creating WebhookConfig from dict."""
        data = {
            "id": "wh-123",
            "url": "http://example.com/webhook",
            "events": ["scan_complete", "quality_gate_change"],
            "secret": "my_secret",
            "project_key": "test-project",
            "created_at": "2025-01-15T10:30:00",
            "enabled": True,
        }

        webhook = WebhookConfig.from_dict(data)
        assert webhook.id == "wh-123"
        assert webhook.url == "http://example.com/webhook"
        assert len(webhook.events) == 2
        assert webhook.secret == "my_secret"
        assert webhook.project_key == "test-project"
        assert webhook.created_at == "2025-01-15T10:30:00"
        assert webhook.enabled is True

    def test_from_dict_defaults(self) -> None:
        """Test from_dict with optional fields missing."""
        data = {
            "id": "wh-123",
            "url": "http://example.com/webhook",
            "events": ["scan_complete"],
        }

        webhook = WebhookConfig.from_dict(data)
        assert webhook.id == "wh-123"
        assert webhook.secret is None
        assert webhook.project_key is None
        assert webhook.enabled is True
        # created_at should have a value
        assert webhook.created_at is not None


class TestWebhookDeliveryResult:
    def test_to_dict_success(self) -> None:
        """Test WebhookDeliveryResult serialization for successful delivery."""
        result = WebhookDeliveryResult(
            webhook_id="wh-123",
            url="http://example.com/webhook",
            success=True,
            status_code=200,
            attempts=1,
        )

        data = result.to_dict()
        assert data["webhook_id"] == "wh-123"
        assert data["success"] is True
        assert data["status_code"] == 200
        assert data["error"] is None
        assert data["attempts"] == 1

    def test_to_dict_failure(self) -> None:
        """Test WebhookDeliveryResult serialization for failed delivery."""
        result = WebhookDeliveryResult(
            webhook_id="wh-123",
            url="http://example.com/webhook",
            success=False,
            error="Connection timeout",
            attempts=3,
        )

        data = result.to_dict()
        assert data["success"] is False
        assert data["status_code"] is None
        assert data["error"] == "Connection timeout"
        assert data["attempts"] == 3

    def test_delivered_at_default(self) -> None:
        """Test that delivered_at gets a default value."""
        result = WebhookDeliveryResult(
            webhook_id="wh-123",
            url="http://example.com/webhook",
            success=True,
        )

        assert result.delivered_at is not None
        # Should be a valid ISO timestamp
        datetime.fromisoformat(result.delivered_at)


class TestWebhookError:
    def test_error_with_context(self) -> None:
        """Test WebhookError includes context."""
        error = WebhookError(
            "Webhook delivery failed",
            context={"webhook_id": "wh-123", "url": "http://example.com"},
        )

        assert "Webhook delivery failed" in str(error)
        assert error.context["webhook_id"] == "wh-123"

    def test_error_without_context(self) -> None:
        """Test WebhookError works without context."""
        error = WebhookError("Webhook delivery failed")
        assert "Webhook delivery failed" in str(error)
        assert error.context == {}


class TestWebhookManager:
    def test_init_default_path(self) -> None:
        """Test initialization with default config path."""
        manager = WebhookManager()
        assert manager._config_path.name == "sonarqube_webhooks.json"
        assert ".vds" in str(manager._config_path)

    def test_init_custom_path(self, temp_config_file: Path) -> None:
        """Test initialization with custom config path."""
        manager = WebhookManager(config_path=temp_config_file)
        assert manager._config_path == temp_config_file

    def test_load_webhooks_from_file(
        self, temp_config_file: Path, sample_webhook_data: dict
    ) -> None:
        """Test loading webhooks from existing config file."""
        config_data = {"webhooks": [sample_webhook_data]}
        temp_config_file.write_text(json.dumps(config_data))

        manager = WebhookManager(config_path=temp_config_file)
        webhooks = manager.list_webhooks()

        assert len(webhooks) == 1
        assert webhooks[0].id == "wh-123"
        assert webhooks[0].url == "http://example.com/webhook"

    def test_load_webhooks_invalid_json(self, temp_config_file: Path) -> None:
        """Test loading webhooks with invalid JSON."""
        temp_config_file.write_text("{invalid json")

        manager = WebhookManager(config_path=temp_config_file)
        webhooks = manager.list_webhooks()

        # Should handle error gracefully and return empty list
        assert webhooks == []

    def test_load_webhooks_no_file(self, temp_config_file: Path) -> None:
        """Test loading webhooks when file doesn't exist."""
        # Don't create the file
        manager = WebhookManager(config_path=temp_config_file)
        webhooks = manager.list_webhooks()

        assert webhooks == []

    def test_register_webhook_success(self, temp_config_file: Path) -> None:
        """Test successful webhook registration."""
        manager = WebhookManager(config_path=temp_config_file)

        webhook = manager.register_webhook(
            url="http://example.com/webhook",
            events=["scan_complete"],
            secret="my_secret",
            project_key="test-project",
        )

        assert webhook.id is not None
        assert len(webhook.id) == 8  # UUID truncated to 8 chars
        assert webhook.url == "http://example.com/webhook"
        assert webhook.events == ["scan_complete"]
        assert webhook.secret == "my_secret"
        assert webhook.project_key == "test-project"
        assert webhook.enabled is True

        # Verify it was saved
        webhooks = manager.list_webhooks()
        assert len(webhooks) == 1

    def test_register_webhook_unsupported_event(self, temp_config_file: Path) -> None:
        """Test webhook registration with unsupported event."""
        manager = WebhookManager(config_path=temp_config_file)

        with pytest.raises(WebhookError) as exc_info:
            manager.register_webhook(
                url="http://example.com/webhook",
                events=["unsupported_event"],
            )

        assert "Unsupported event" in str(exc_info.value)
        assert exc_info.value.context["supported"] == WebhookManager.SUPPORTED_EVENTS

    def test_register_webhook_multiple_events(self, temp_config_file: Path) -> None:
        """Test webhook registration with multiple events."""
        manager = WebhookManager(config_path=temp_config_file)

        webhook = manager.register_webhook(
            url="http://example.com/webhook",
            events=["scan_complete", "quality_gate_change", "issue_created"],
        )

        assert len(webhook.events) == 3
        assert "scan_complete" in webhook.events
        assert "quality_gate_change" in webhook.events
        assert "issue_created" in webhook.events

    def test_list_webhooks_all(self, temp_config_file: Path) -> None:
        """Test listing all webhooks."""
        manager = WebhookManager(config_path=temp_config_file)

        manager.register_webhook("http://example.com/wh1", ["scan_complete"])
        manager.register_webhook("http://example.com/wh2", ["quality_gate_change"])
        manager.register_webhook("http://example.com/wh3", ["issue_created"])

        webhooks = manager.list_webhooks()
        assert len(webhooks) == 3

    def test_list_webhooks_filtered_by_project(self, temp_config_file: Path) -> None:
        """Test listing webhooks filtered by project."""
        manager = WebhookManager(config_path=temp_config_file)

        manager.register_webhook("http://example.com/wh1", ["scan_complete"], project_key="proj-a")
        manager.register_webhook(
            "http://example.com/wh2", ["quality_gate_change"], project_key="proj-b"
        )
        manager.register_webhook("http://example.com/wh3", ["issue_created"])  # Global

        # List all for proj-a
        proj_a_webhooks = manager.list_webhooks(project_key="proj-a")
        assert len(proj_a_webhooks) == 2  # proj-a specific + global
        assert any(wh.project_key == "proj-a" for wh in proj_a_webhooks)

        # List all for proj-b
        proj_b_webhooks = manager.list_webhooks(project_key="proj-b")
        assert len(proj_b_webhooks) == 2  # proj-b specific + global

    def test_get_webhook(self, temp_config_file: Path) -> None:
        """Test getting a specific webhook."""
        manager = WebhookManager(config_path=temp_config_file)

        registered = manager.register_webhook(
            "http://example.com/webhook",
            ["scan_complete"],
            project_key="test-project",
        )

        webhook = manager.get_webhook(registered.id)
        assert webhook is not None
        assert webhook.id == registered.id
        assert webhook.url == "http://example.com/webhook"

    def test_get_webhook_not_found(self, temp_config_file: Path) -> None:
        """Test getting a non-existent webhook."""
        manager = WebhookManager(config_path=temp_config_file)

        webhook = manager.get_webhook("non-existent-id")
        assert webhook is None

    def test_delete_webhook(self, temp_config_file: Path) -> None:
        """Test deleting a webhook."""
        manager = WebhookManager(config_path=temp_config_file)

        registered = manager.register_webhook(
            "http://example.com/webhook",
            ["scan_complete"],
        )

        assert len(manager.list_webhooks()) == 1

        deleted = manager.delete_webhook(registered.id)
        assert deleted is True
        assert len(manager.list_webhooks()) == 0

    def test_delete_webhook_not_found(self, temp_config_file: Path) -> None:
        """Test deleting a non-existent webhook."""
        manager = WebhookManager(config_path=temp_config_file)

        deleted = manager.delete_webhook("non-existent-id")
        assert deleted is False

    def test_sign_payload(self) -> None:
        """Test HMAC signature generation for payload."""
        manager = WebhookManager()

        payload = '{"event": "test"}'
        secret = "my_secret"

        signature = manager.sign_payload(payload, secret)

        assert signature is not None
        assert len(signature) == 64  # SHA256 hex length
        assert signature != manager.sign_payload("different", secret)

    def test_sign_payload_deterministic(self) -> None:
        """Test that sign_payload produces same signature for same input."""
        manager = WebhookManager()

        payload = '{"event": "test"}'
        secret = "my_secret"

        sig1 = manager.sign_payload(payload, secret)
        sig2 = manager.sign_payload(payload, secret)

        assert sig1 == sig2

    @pytest.mark.asyncio
    async def test_trigger_webhooks_success(self, temp_config_file: Path) -> None:
        """Test successful webhook triggering."""
        manager = WebhookManager(config_path=temp_config_file)

        manager.register_webhook(
            "http://example.com/wh1",
            ["scan_complete"],
            secret="secret1",
        )
        manager.register_webhook(
            "http://example.com/wh2",
            ["scan_complete"],
            secret="secret2",
        )

        payload = {"project": "test-project", "status": "OK"}

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            # session.post should return an async context manager
            mock_context = MockAsyncContextManager(status=200)
            mock_session.post = MagicMock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            results = await manager.trigger_webhooks("scan_complete", payload)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.status_code == 200 for r in results)

    @pytest.mark.asyncio
    async def test_trigger_webhooks_with_project_filter(self, temp_config_file: Path) -> None:
        """Test triggering webhooks filtered by project."""
        manager = WebhookManager(config_path=temp_config_file)

        manager.register_webhook(
            "http://example.com/wh1",
            ["scan_complete"],
            project_key="proj-a",
        )
        manager.register_webhook(
            "http://example.com/wh2",
            ["scan_complete"],
            project_key="proj-b",
        )
        manager.register_webhook(
            "http://example.com/wh3",
            ["scan_complete"],
            project_key=None,  # Global
        )

        payload = {"project": "test-project"}

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_context = MockAsyncContextManager(status=200)
            mock_session.post = MagicMock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            # Trigger for proj-a should match proj-a + global
            results = await manager.trigger_webhooks("scan_complete", payload, project_key="proj-a")

        # Should trigger proj-a webhook + global webhook (not proj-b)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_trigger_webhooks_with_disabled(self, temp_config_file: Path) -> None:
        """Test that disabled webhooks are not triggered."""
        manager = WebhookManager(config_path=temp_config_file)

        webhook = manager.register_webhook(
            "http://example.com/wh1",
            ["scan_complete"],
        )
        webhook.enabled = False
        manager._save_webhooks()

        payload = {"project": "test-project"}

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.post = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            results = await manager.trigger_webhooks("scan_complete", payload)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_trigger_webhooks_with_signature(self, temp_config_file: Path) -> None:
        """Test that webhooks with secrets include signature header."""
        manager = WebhookManager(config_path=temp_config_file)

        manager.register_webhook(
            "http://example.com/webhook",
            ["scan_complete"],
            secret="test_secret",
        )

        payload = {"project": "test-project"}

        captured_headers = {}

        def capture_post(_url, _data=None, headers=None, **_kwargs):
            captured_headers.update(headers or {})
            return MockAsyncContextManager(status=200)

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.post = MagicMock(side_effect=capture_post)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            await manager.trigger_webhooks("scan_complete", payload)

        assert "X-Sonarqube-Signature" in captured_headers
        signature = captured_headers["X-Sonarqube-Signature"]
        assert len(signature) == 64

    @pytest.mark.asyncio
    async def test_trigger_webhooks_event_filter(self, temp_config_file: Path) -> None:
        """Test that only webhooks matching the event are triggered."""
        manager = WebhookManager(config_path=temp_config_file)

        manager.register_webhook(
            "http://example.com/wh1",
            ["scan_complete"],
        )
        manager.register_webhook(
            "http://example.com/wh2",
            ["quality_gate_change"],
        )
        manager.register_webhook(
            "http://example.com/wh3",
            ["scan_complete", "quality_gate_change"],
        )

        payload = {"project": "test-project"}

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_context = MockAsyncContextManager(status=200)
            mock_session.post = MagicMock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            results = await manager.trigger_webhooks("scan_complete", payload)

        # Should trigger wh1 and wh3 (not wh2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_deliver_webhook_retry_on_failure(self, temp_config_file: Path) -> None:
        """Test webhook delivery retry logic."""
        manager = WebhookManager(config_path=temp_config_file)

        webhook = manager.register_webhook(
            "http://example.com/webhook",
            ["scan_complete"],
        )

        payload = json.dumps({"test": "data"})

        call_count = 0

        def create_mock_post(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return MockAsyncContextManager(status=500)
            else:
                return MockAsyncContextManager(status=200)

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.post = MagicMock(side_effect=create_mock_post)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            result = await manager._deliver_webhook(mock_session, webhook, payload, {})

        assert result.success is True
        assert result.attempts == 3

    @pytest.mark.asyncio
    async def test_deliver_webhook_max_retries_exceeded(self, temp_config_file: Path) -> None:
        """Test webhook delivery when max retries exceeded."""
        manager = WebhookManager(config_path=temp_config_file)

        webhook = manager.register_webhook(
            "http://example.com/webhook",
            ["scan_complete"],
        )

        payload = json.dumps({"test": "data"})

        # Always return status 500 (failure)
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_context = MockAsyncContextManager(status=500)
            mock_session.post = MagicMock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            result = await manager._deliver_webhook(mock_session, webhook, payload, {})

        assert result.success is False
        assert result.attempts == 3
        assert "Max retries exceeded" in result.error

    @pytest.mark.asyncio
    async def test_deliver_webhook_connection_error(self, temp_config_file: Path) -> None:
        """Test webhook delivery with connection error."""
        import aiohttp

        manager = WebhookManager(config_path=temp_config_file)

        webhook = manager.register_webhook(
            "http://example.com/webhook",
            ["scan_complete"],
        )

        payload = json.dumps({"test": "data"})

        # Return a context manager that raises an error
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_context = MockAsyncContextManager(
                should_raise=aiohttp.ClientError("Connection refused")
            )
            mock_session.post = MagicMock(return_value=mock_context)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            result = await manager._deliver_webhook(mock_session, webhook, payload, {})

        assert result.success is False
        assert "Connection refused" in result.error
        assert result.attempts == 3  # Should retry

    def test_supported_events(self) -> None:
        """Test that supported events are correctly defined."""
        expected = ["scan_complete", "quality_gate_change", "issue_created", "issue_resolved"]
        assert expected == WebhookManager.SUPPORTED_EVENTS

    def test_save_webhooks_creates_directory(self, tmp_path: Path) -> None:
        """Test that saving webhooks creates parent directory."""
        config_path = tmp_path / "nested" / "dir" / "webhooks.json"

        manager = WebhookManager(config_path=config_path)
        manager.register_webhook("http://example.com/webhook", ["scan_complete"])

        assert config_path.exists()
        assert config_path.parent.exists()
