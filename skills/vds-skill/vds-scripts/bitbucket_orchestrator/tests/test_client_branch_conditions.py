from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient, VDSClientError
from vds_bitbucket_orchestrator.config import BitbucketSettings


@pytest.fixture
@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def client(mock_bb: MagicMock) -> BitbucketClient:
    mock_instance = MagicMock()
    mock_bb.return_value = mock_instance
    settings = BitbucketSettings(BITBUCKET_TOKEN="token")
    return BitbucketClient(settings)


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_set_branches_permissions_defaults(mock_bb: MagicMock) -> None:
    stub = MagicMock()
    stub.set_branches_permissions.return_value = {"ok": True}
    mock_bb.return_value = stub
    client = BitbucketClient(BitbucketSettings(BITBUCKET_TOKEN="token"))

    result = client.set_branches_permissions(
        "PRJ",
        matcher_type="BRANCH",
        matcher_value="refs/heads/main",
        permission_type="READ_ONLY",
    )

    assert result == {"ok": True}
    stub.set_branches_permissions.assert_called_once_with(
        "PRJ",
        multiple_permissions=False,
        matcher_type="BRANCH",
        matcher_value="refs/heads/main",
        permission_type="READ_ONLY",
        repository_slug=None,
        except_users=[],
        except_groups=[],
        except_access_keys=[],
        start=0,
        limit=25,
    )


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_set_branches_permissions_error(mock_bb: MagicMock) -> None:
    stub = MagicMock()
    stub.set_branches_permissions.side_effect = RuntimeError("boom")
    mock_bb.return_value = stub
    client = BitbucketClient(BitbucketSettings(BITBUCKET_TOKEN="token"))

    with pytest.raises(VDSClientError):
        client.set_branches_permissions("PRJ")


@patch("vds_bitbucket_orchestrator.client.requests.get")
@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_list_branch_permissions_server_mode(mock_bb: MagicMock, mock_get: MagicMock) -> None:
    mock_bb.return_value = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"values": [{"id": 1}]}'
    response.json.return_value = {"values": [{"id": 1}]}
    mock_get.return_value = response

    settings = BitbucketSettings(BITBUCKET_TOKEN="token", BITBUCKET_BASE_URL="http://bitbucket.example.com")
    client = BitbucketClient(settings)

    result = client.list_branch_permissions("PRJ", repository_slug="repo")

    assert result == [{"id": 1}]
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer token"
    assert kwargs["params"] == {"start": 0, "limit": 25}


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_get_project_conditions_coerces_list(mock_bb: MagicMock) -> None:
    stub = MagicMock()
    stub.get_project_conditions.return_value = {"id": 1}
    mock_bb.return_value = stub
    client = BitbucketClient(BitbucketSettings(BITBUCKET_TOKEN="token"))

    result = client.get_project_conditions("PRJ")
    assert result == [{"id": 1}]


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_get_project_conditions_handles_none(mock_bb: MagicMock) -> None:
    stub = MagicMock()
    stub.get_project_conditions.return_value = None
    mock_bb.return_value = stub
    client = BitbucketClient(BitbucketSettings(BITBUCKET_TOKEN="token"))

    result = client.get_project_conditions("PRJ")
    assert result == []
