from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner
from vds_jira_orchestrator import cli


def _mock_settings(mock_settings_cls: MagicMock) -> None:
    settings = mock_settings_cls.return_value
    settings.require_basic_or_token.return_value = None
    settings.username = "user"
    settings.password = "pass"
    settings.token = "token"
    settings.base_url = "https://jira.test"


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_discover_fields_outputs_sorted_fields(
    mock_settings_cls: MagicMock,
    mock_adapter_cls: MagicMock,
) -> None:
    _mock_settings(mock_settings_cls)
    mock_adapter = mock_adapter_cls.return_value
    mock_adapter.get_createmeta.return_value = {
        "projects": [
            {
                "key": "TEST",
                "issuetypes": [
                    {
                        "name": "Task",
                        "fields": {
                            "summary": {
                                "name": "Summary",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                            "customfield_10000": {
                                "name": "Choice",
                                "required": False,
                                "schema": {"type": "option"},
                                "allowedValues": [{"id": 1, "value": "Option A"}],
                            },
                        },
                    }
                ],
            }
        ]
    }

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        ["discover-fields", "--project", "TEST", "--issuetype", "Task", "--include-system"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 2
    assert "duration_ms" in payload
    assert payload["fields"][0]["name"] == "Summary"
    assert payload["fields"][0]["required"] is True
    assert payload["fields"][1]["allowedValues"] == [{"id": "1", "value": "Option A"}]


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_discover_fields_excludes_system_by_default(
    mock_settings_cls: MagicMock,
    mock_adapter_cls: MagicMock,
) -> None:
    _mock_settings(mock_settings_cls)
    mock_adapter = mock_adapter_cls.return_value
    mock_adapter.get_createmeta.return_value = {
        "projects": [
            {
                "key": "TEST",
                "issuetypes": [
                    {
                        "name": "Task",
                        "fields": {
                            "summary": {
                                "name": "Summary",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                            "customfield_10000": {
                                "name": "Choice",
                                "required": False,
                                "schema": {"type": "option"},
                            },
                        },
                    }
                ],
            }
        ]
    }

    runner = CliRunner()
    result = runner.invoke(cli.app, ["discover-fields", "--project", "TEST", "--issuetype", "Task"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["fields"][0]["id"] == "customfield_10000"


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_discover_fields_filters_by_name(
    mock_settings_cls: MagicMock,
    mock_adapter_cls: MagicMock,
) -> None:
    _mock_settings(mock_settings_cls)
    mock_adapter = mock_adapter_cls.return_value
    mock_adapter.get_createmeta.return_value = {
        "projects": [
            {
                "key": "TEST",
                "issuetypes": [
                    {
                        "name": "Task",
                        "fields": {
                            "customfield_10000": {
                                "name": "Choice",
                                "required": False,
                                "schema": {"type": "option"},
                            },
                            "customfield_10001": {
                                "name": "Owner",
                                "required": False,
                                "schema": {"type": "user"},
                            },
                        },
                    }
                ],
            }
        ]
    }

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        ["discover-fields", "--project", "TEST", "--issuetype", "Task", "--field", "choice"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["fields"][0]["name"] == "Choice"


@patch("vds_jira_orchestrator.cli.JiraAdapter")
@patch("vds_jira_orchestrator.cli.JiraSettings")
def test_discover_fields_merges_allowed_values_from_editmeta(
    mock_settings_cls: MagicMock,
    mock_adapter_cls: MagicMock,
) -> None:
    _mock_settings(mock_settings_cls)
    mock_adapter = mock_adapter_cls.return_value
    mock_adapter.get_createmeta.return_value = {
        "projects": [
            {
                "key": "TEST",
                "issuetypes": [
                    {
                        "name": "Task",
                        "fields": {
                            "customfield_10000": {
                                "name": "Choice",
                                "required": False,
                                "schema": {"type": "option"},
                            },
                        },
                    }
                ],
            }
        ]
    }
    mock_adapter.get_editmeta.return_value = {
        "fields": {
            "customfield_10000": {
                "allowedValues": [{"id": 10, "value": "Option X"}],
            }
        }
    }

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "discover-fields",
            "--project",
            "TEST",
            "--issuetype",
            "Task",
            "--issue-key",
            "TEST-1",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["fields"][0]["allowedValues"] == [{"id": "10", "value": "Option X"}]
