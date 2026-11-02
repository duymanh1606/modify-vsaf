import pytest
from vds_google_sheets_orchestrator.client import GoogleSheetsClient
from vds_google_sheets_orchestrator.config import GoogleSheetsSettings
from vds_google_sheets_orchestrator.errors import AuthenticationError, InvalidAuthMethodError


def test_invalid_auth_method_raises():
    client = GoogleSheetsClient(GoogleSheetsSettings(), auth_method="nope")
    with pytest.raises(InvalidAuthMethodError):
        client._get_client()


def test_api_key_requires_key(monkeypatch):
    settings = GoogleSheetsSettings(api_key=None)
    client = GoogleSheetsClient(settings, auth_method="api_key")
    with pytest.raises(AuthenticationError):
        client._get_client()


def test_service_account_missing(monkeypatch, tmp_path):
    settings = GoogleSheetsSettings(credentials_path=tmp_path / "missing.json")
    client = GoogleSheetsClient(settings, auth_method="service_account")
    with pytest.raises(AuthenticationError):
        client._get_client()
