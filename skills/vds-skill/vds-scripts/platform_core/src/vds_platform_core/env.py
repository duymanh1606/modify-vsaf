"""Platform-level env-path defaults — TSK-7.12b.

Provides DEFAULT_ENV_PATHS so platform_core.config can resolve the primary
VDS .env file without importing from vds_cli_common (which sits one layer up).
Respects the same VDS_ENV_FILE / VDS_CONFIG_DIR env overrides as vds_cli_common.
"""

import os
from pathlib import Path


def _vds_env_path() -> Path:
    """Resolve the primary VDS .env file, honoring env-var overrides."""
    if raw := (os.getenv("VDS_ENV_FILE") or "").strip():
        return Path(raw).expanduser().resolve()
    config_dir = (os.getenv("VDS_CONFIG_DIR") or "").strip()
    root = Path(config_dir).expanduser().resolve() if config_dir else Path.home() / ".vds"
    return root / ".env"


# Evaluated once at import time — same semantics as vds_cli_common.paths.get_default_env_paths()
DEFAULT_ENV_PATHS: tuple[Path, ...] = (_vds_env_path(),)

__all__ = ["DEFAULT_ENV_PATHS"]
