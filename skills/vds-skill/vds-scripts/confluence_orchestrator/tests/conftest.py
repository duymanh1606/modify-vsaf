from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# After TSK-7.19 BaseSettings migration, ConfluenceSettings pulls from
# os.environ on instantiation (including model_validate). Ambient VDS_*
# and CONFLUENCE_* vars from ~/.vds/.env would leak into test settings
# and change auth-branch selection (password vs token). This autouse
# fixture restores the pre-migration hermeticity by clearing these vars
# before every test.
_CONFLUENCE_ENV_KEYS = (
    "VDS_USERNAME",
    "VDS_PASSWORD",
    "INTERNAL_CONFLUENCE_TOKEN",
    "EXTERNAL_CONFLUENCE_TOKEN",
    "CONFLUENCE_DEFAULT_SERVER",
    "CONFLUENCE_INTERNAL_URL",
    "CONFLUENCE_EXTERNAL_URL",
    "CONFLUENCE_EXTERNAL_ALTERNATE_URL",
    "CONFLUENCE_INTERNAL_ALTERNATE_URL",
    "CONFLUENCE_SECONDARY_EXTERNAL_URL",
    "CONFLUENCE_INTERNAL_FALLBACK_URL",
    "CONFLUENCE_MAX_RETRIES",
    "CONFLUENCE_RETRY_BACKOFF",
    "CONFLUENCE_HTTP_TIMEOUT",
)


@pytest.fixture(autouse=True)
def _clear_confluence_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _CONFLUENCE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    # Prevent DEFAULT_ENV_PATHS (e.g. ~/.vds/.env) from leaking into
    # pydantic-settings DotEnvSettingsSource during test runs — the config
    # module exposes these as a tuple; patch to empty for hermeticity.
    import confluence_orchestrator.config as _cfg_mod

    monkeypatch.setattr(_cfg_mod, "DEFAULT_ENV_PATHS", ())
