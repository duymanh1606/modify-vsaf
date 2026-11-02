"""Webhook management for SonarQube event notifications."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from vds_cli_common.paths import get_vds_config_root

logger = structlog.get_logger(__name__)

WEBHOOKS_FILE = get_vds_config_root() / "sonarqube_webhooks.json"


class WebhookError(Exception):
    """Base error for webhook operations."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


@dataclass
class WebhookConfig:
    """Configuration for a registered webhook."""

    id: str
    url: str
    events: list[str]
    secret: str | None = None
    project_key: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "events": self.events,
            "secret": "***" if self.secret else None,
            "project_key": self.project_key,
            "created_at": self.created_at,
            "enabled": self.enabled,
        }

    def to_storage_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "events": self.events,
            "secret": self.secret,
            "project_key": self.project_key,
            "created_at": self.created_at,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebhookConfig:
        return cls(
            id=data["id"],
            url=data["url"],
            events=data.get("events", []),
            secret=data.get("secret"),
            project_key=data.get("project_key"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            enabled=data.get("enabled", True),
        )


@dataclass
class WebhookDeliveryResult:
    """Result of a webhook delivery attempt."""

    webhook_id: str
    url: str
    success: bool
    status_code: int | None = None
    error: str | None = None
    attempts: int = 1
    delivered_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "webhook_id": self.webhook_id,
            "url": self.url,
            "success": self.success,
            "status_code": self.status_code,
            "error": self.error,
            "attempts": self.attempts,
            "delivered_at": self.delivered_at,
        }


class WebhookManager:
    """Manager for webhook registration and delivery."""

    SUPPORTED_EVENTS = ["scan_complete", "quality_gate_change", "issue_created", "issue_resolved"]

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or WEBHOOKS_FILE
        self._webhooks: dict[str, WebhookConfig] = {}
        self._load_webhooks()

    def _load_webhooks(self) -> None:
        if self._config_path.exists():
            try:
                data = json.loads(self._config_path.read_text())
                self._webhooks = {
                    wh["id"]: WebhookConfig.from_dict(wh) for wh in data.get("webhooks", [])
                }
            except Exception as exc:
                logger.warning("Failed to load webhooks config", error=str(exc))
                self._webhooks = {}

    def _save_webhooks(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"webhooks": [wh.to_storage_dict() for wh in self._webhooks.values()]}
        self._config_path.write_text(json.dumps(data, indent=2))

    def register_webhook(
        self,
        url: str,
        events: list[str],
        secret: str | None = None,
        project_key: str | None = None,
    ) -> WebhookConfig:
        """Register a new webhook."""
        for event in events:
            if event not in self.SUPPORTED_EVENTS:
                raise WebhookError(
                    f"Unsupported event: {event}",
                    {"supported": self.SUPPORTED_EVENTS},
                )

        webhook_id = str(uuid.uuid4())[:8]
        webhook = WebhookConfig(
            id=webhook_id,
            url=url,
            events=events,
            secret=secret,
            project_key=project_key,
        )

        self._webhooks[webhook_id] = webhook
        self._save_webhooks()

        logger.info("Webhook registered", id=webhook_id, url=url, events=events)
        return webhook

    def list_webhooks(self, project_key: str | None = None) -> list[WebhookConfig]:
        """List all registered webhooks."""
        webhooks = list(self._webhooks.values())
        if project_key:
            webhooks = [
                wh for wh in webhooks if wh.project_key == project_key or not wh.project_key
            ]
        return webhooks

    def get_webhook(self, webhook_id: str) -> WebhookConfig | None:
        """Get a specific webhook by ID."""
        return self._webhooks.get(webhook_id)

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook by ID."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            self._save_webhooks()
            logger.info("Webhook deleted", id=webhook_id)
            return True
        return False

    def sign_payload(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for payload."""
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    async def trigger_webhooks(
        self,
        event: str,
        payload: dict[str, Any],
        project_key: str | None = None,
    ) -> list[WebhookDeliveryResult]:
        """Trigger webhooks for an event (async)."""
        import aiohttp

        matching = [
            wh
            for wh in self._webhooks.values()
            if wh.enabled
            and event in wh.events
            and (wh.project_key is None or wh.project_key == project_key)
        ]

        results: list[WebhookDeliveryResult] = []
        payload_str = json.dumps(payload)

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for webhook in matching:
                headers = {"Content-Type": "application/json"}
                if webhook.secret:
                    headers["X-Sonarqube-Signature"] = self.sign_payload(
                        payload_str, webhook.secret
                    )

                result = await self._deliver_webhook(session, webhook, payload_str, headers)
                results.append(result)

        return results

    async def _deliver_webhook(
        self,
        session,
        webhook: WebhookConfig,
        payload: str,
        headers: dict[str, str],
    ) -> WebhookDeliveryResult:
        """Deliver a single webhook with retry logic."""
        max_attempts = 3
        backoff = [1, 2, 4]

        for attempt in range(max_attempts):
            try:
                async with session.post(webhook.url, data=payload, headers=headers) as resp:
                    if resp.status < 400:
                        return WebhookDeliveryResult(
                            webhook_id=webhook.id,
                            url=webhook.url,
                            success=True,
                            status_code=resp.status,
                            attempts=attempt + 1,
                        )
                    if attempt < max_attempts - 1:
                        import asyncio

                        await asyncio.sleep(backoff[attempt])
            except Exception as exc:
                if attempt == max_attempts - 1:
                    return WebhookDeliveryResult(
                        webhook_id=webhook.id,
                        url=webhook.url,
                        success=False,
                        error=str(exc),
                        attempts=attempt + 1,
                    )
                import asyncio

                await asyncio.sleep(backoff[attempt])

        return WebhookDeliveryResult(
            webhook_id=webhook.id,
            url=webhook.url,
            success=False,
            error="Max retries exceeded",
            attempts=max_attempts,
        )


__all__ = [
    "WebhookManager",
    "WebhookConfig",
    "WebhookDeliveryResult",
    "WebhookError",
]
