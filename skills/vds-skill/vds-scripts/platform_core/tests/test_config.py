"""Tests for vds_platform_core.config."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource
from vds_platform_core.config import VDS_BASE_SETTINGS_CONFIG, vds_settings_customise_sources


class _DemoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DEMO__")
    value: str = "default"


class TestVDSBaseSettingsConfig:
    def test_has_required_keys(self) -> None:
        assert VDS_BASE_SETTINGS_CONFIG["env_file"] == "~/.vds/.env"
        assert VDS_BASE_SETTINGS_CONFIG["dotenv_filtering"] == "match_prefix"
        assert VDS_BASE_SETTINGS_CONFIG["env_nested_delimiter"] == "__"

    def test_case_insensitive_flag(self) -> None:
        """TSK-7.12a: case_sensitive=False must be present."""
        assert VDS_BASE_SETTINGS_CONFIG["case_sensitive"] is False

    def test_populate_by_name_flag(self) -> None:
        """TSK-7.12a: populate_by_name=True must be present."""
        assert VDS_BASE_SETTINGS_CONFIG["populate_by_name"] is True


class TestSettingsCustomiseSources:
    def test_returns_tuple_with_init_and_env_sources_first(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DEMO__VALUE=from-env\n", encoding="utf-8")

        init_settings = object()
        env_settings = object()
        sources = vds_settings_customise_sources(
            _DemoSettings,
            init_settings,  # type: ignore[arg-type]
            env_settings,  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            env_paths=(env_file,),
        )

        assert isinstance(sources, tuple)
        assert sources[0] is init_settings
        assert sources[1] is env_settings

    def test_custom_env_paths_add_dotenv_sources(self, tmp_path: Path) -> None:
        env_file = tmp_path / "custom.env"
        env_file.write_text("DEMO__VALUE=custom\n", encoding="utf-8")

        sources = vds_settings_customise_sources(
            _DemoSettings,
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            env_paths=(env_file,),
        )
        dotenv_sources = [source for source in sources if isinstance(source, DotEnvSettingsSource)]
        assert len(dotenv_sources) == 1
        assert Path(dotenv_sources[0].env_file) == env_file

    def test_missing_env_paths_are_skipped(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.env"
        existing.write_text("DEMO__VALUE=ok\n", encoding="utf-8")
        missing = tmp_path / "missing.env"

        sources = vds_settings_customise_sources(
            _DemoSettings,
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            env_paths=(missing, existing),
        )
        dotenv_sources = [source for source in sources if isinstance(source, DotEnvSettingsSource)]
        assert len(dotenv_sources) == 1
        assert Path(dotenv_sources[0].env_file) == existing
