"""Configuration for PDF orchestrator."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from vds_cli_common.env import load_shared_env


class PDFSettings(BaseSettings):
    """Environment-backed settings for PDF operations."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    pdf_output_dir: Path = Field(default_factory=lambda: Path.cwd())
    pdf_strict_validation_default: bool = False
    pdf_default_page_limit: int = 0


def load_settings() -> PDFSettings:
    """Load shared VDS environment and construct settings."""
    load_shared_env()
    return PDFSettings()


__all__ = ["PDFSettings", "load_settings"]
