"""Shared infrastructure for VDS CLI packages.

This package provides reusable components for building consistent CLIs:
- CLIContext: TTY detection, color control, output mode management
- OutputManager: Unified output with spinners, progress bars, tables
- ErrorHandler: Consistent error formatting with suggestions
- ExitCodes: Standard exit codes for all CLIs
- create_version_callback: Factory for --version flag handlers
"""

from vds_cli_common.app import make_vds_app
from vds_cli_common.context import CLIContext
from vds_cli_common.env import DEFAULT_ENV_PATHS, load_shared_env
from vds_cli_common.errors import ErrorHandler, ExitCodes
from vds_cli_common.output import NullProgress, OutputManager
from vds_cli_common.paths import get_shared_env_path, get_vds_cache_root, get_vds_config_root, get_vds_log_root
from vds_cli_common.version import create_version_callback

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_ENV_PATHS",
    "CLIContext",
    "ErrorHandler",
    "ExitCodes",
    "NullProgress",
    "OutputManager",
    "__version__",
    "create_version_callback",
    "get_shared_env_path",
    "get_vds_cache_root",
    "get_vds_config_root",
    "get_vds_log_root",
    "load_shared_env",
    "make_vds_app",
]
