"""Tests for version callback factory."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import typer

from vds_cli_common.version import create_version_callback, get_package_version


class TestCreateVersionCallback:
    """Tests for create_version_callback function."""

    def test_callback_prints_version_and_exits(self) -> None:
        """Test callback prints version and exits when value is True."""
        callback = create_version_callback("vds-cli-common")

        with patch("typer.echo") as mock_echo:
            with pytest.raises(typer.Exit) as exc_info:
                callback(True)

            assert exc_info.value.exit_code == 0
            mock_echo.assert_called_once()
            call_args = mock_echo.call_args[0][0]
            assert "vds-cli-common" in call_args

    def test_callback_does_nothing_when_false(self) -> None:
        """Test callback does nothing when value is False."""
        callback = create_version_callback("vds-cli-common")

        with patch("typer.echo") as mock_echo:
            # Should not raise or print
            result = callback(False)
            assert result is None
            mock_echo.assert_not_called()

    def test_callback_handles_unknown_package(self) -> None:
        """Test callback handles unknown package gracefully."""
        callback = create_version_callback("nonexistent-package-xyz")

        with patch("typer.echo") as mock_echo:
            with pytest.raises(typer.Exit):
                callback(True)

            call_args = mock_echo.call_args[0][0]
            assert "unknown" in call_args


class TestGetPackageVersion:
    """Tests for get_package_version function."""

    def test_returns_version_for_known_package(self) -> None:
        """Test returns version for installed package."""
        # typer should be installed
        version = get_package_version("typer")
        assert version != "unknown"
        assert "." in version  # Should have version format

    def test_returns_unknown_for_missing_package(self) -> None:
        """Test returns 'unknown' for missing package."""
        version = get_package_version("nonexistent-package-xyz")
        assert version == "unknown"
