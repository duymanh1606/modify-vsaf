from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_webhooks_list(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.list_webhooks.return_value = [{"id": 1}]
    mock_build.return_value.__enter__.return_value = client

    settings = Mock()
    settings.is_cloud_mode = True
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        [
            "webhooks",
            "list",
            "PRJ",
            "repo",
            "--filter-event",
            "pr:opened",
            "--statistics",
        ],
    )
    assert result.exit_code == 0
    client.list_webhooks.assert_called_once_with("PRJ", "repo", event="pr:opened", statistics=True)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_webhooks_requires_cloud_mode(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    settings = Mock()
    settings.is_cloud_mode = False
    mock_load.return_value = settings

    result = runner.invoke(app, ["webhooks", "list", "PRJ", "repo"])
    assert result.exit_code != 0
    mock_build.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_webhooks_create_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        ["webhooks", "create", "PRJ", "repo", "--name", "hook", "--url", "https://example.com", "--event", "repo:push"],
    )
    assert result.exit_code != 0
    assert "Refusing to create webhook without --yes" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_webhooks_create_success(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    client.create_webhook.return_value = {"id": 42}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "webhooks",
            "create",
            "PRJ",
            "repo",
            "--name",
            "My Hook",
            "--url",
            "https://example.com",
            "--event",
            "repo:push",
            "--event",
            "pr:opened",
            "--inactive",
            "--secret",
            "token",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    client.create_webhook.assert_called_once_with(
        "PRJ",
        "repo",
        "My Hook",
        ["repo:push", "pr:opened"],
        "https://example.com",
        active=False,
        secret="token",
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_webhooks_update_requires_changes(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        ["webhooks", "update", "PRJ", "repo", "--webhook-id", "7", "--yes"],
    )
    assert result.exit_code != 0
    assert "Must provide at least one field to update" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_webhooks_update_success(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "webhooks",
            "update",
            "PRJ",
            "repo",
            "--webhook-id",
            "12",
            "--name",
            "Updated Hook",
            "--event",
            "repo:push",
            "--set-inactive",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    client.update_webhook.assert_called_once_with(
        "PRJ",
        "repo",
        12,
        name="Updated Hook",
        webhook_url=None,
        events=["repo:push"],
        active=False,
        secret=None,
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_webhooks_delete_error(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    client.delete_webhook.side_effect = VDSClientError("boom", context={"foo": "bar"})
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        ["webhooks", "delete", "PRJ", "repo", "--webhook-id", "9", "--yes"],
    )
    assert result.exit_code != 0
    assert "bitbucket_error" in result.stdout
