from vds_cli_common.paths import get_vds_config_root
from vds_google_sheets_orchestrator.config import GoogleSheetsSettings, load_settings


def test_default_paths(tmp_path):
    settings = GoogleSheetsSettings()
    config_root = get_vds_config_root()
    assert settings.credentials_path.name.endswith(".json")
    assert settings.credentials_path.parent == config_root
    assert settings.oauth_credentials_path == config_root / "gspread_oauth.json"
    assert settings.api_key_path == config_root / "google_api_key.txt"


def test_load_settings_with_overrides():
    settings = load_settings(overrides={"api_key": "abc123"})
    assert settings.api_key == "abc123"
