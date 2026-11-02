"""Manual verification tests — skipped by default.

These tests hit real external services (Confluence, Jira) via the MCP server
and require ambient credentials.  They are NOT part of the default pytest suite.

Run explicitly with::

    pytest --run-verification mcp_server/tests/verification/

Or set the environment variable::

    VDS_RUN_VERIFICATION=1 pytest mcp_server/tests/verification/
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register ``--run-verification`` CLI flag."""
    try:
        parser.addoption(
            "--run-verification",
            action="store_true",
            default=False,
            help="Run manual verification tests that hit real services.",
        )
    except ValueError:
        pass  # already registered by another conftest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip verification tests unless explicitly opted in.

    Only targets items whose node ID contains ``verification/`` so that
    the hook never accidentally skips non-verification tests when pytest
    collects from a parent directory.
    """
    if os.environ.get("VDS_RUN_VERIFICATION") == "1":
        return
    if config.getoption("--run-verification", default=False):
        return
    skip_marker = pytest.mark.skip(
        reason="Verification tests require --run-verification or VDS_RUN_VERIFICATION=1",
    )
    for item in items:
        if "verification" in item.nodeid:
            item.add_marker(skip_marker)
