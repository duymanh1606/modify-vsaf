"""Minimal PDF orchestrator tests — no external services required."""

from __future__ import annotations

import sys
from pathlib import Path

from vds_pdf_orchestrator.config import load_settings

# Add src to path for imports (matches conftest.py pattern)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vds_pdf_orchestrator.config import PDFSettings


def test_pdf_settings_defaults() -> None:
    settings = PDFSettings()

    assert settings.pdf_output_dir == Path.cwd()
    assert settings.pdf_strict_validation_default is False
    assert settings.pdf_default_page_limit == 0


def test_load_settings_returns_pdf_settings() -> None:
    settings = load_settings()

    assert isinstance(settings, PDFSettings)


def test_memory_monitor_exists(memory_monitor) -> None:
    assert memory_monitor is not None


def test_error_handler_fixture_is_reset(error_handler) -> None:
    error_handler.history.append("error")
    assert error_handler.history == ["error"]
