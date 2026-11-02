"""Tests for common completers."""

from __future__ import annotations

from vds_cli_common.completers import (
    complete_index,
    complete_log_level,
    complete_output_format,
    complete_project,
    complete_server,
    complete_time_field,
)


class TestCompleteIndex:
    """Tests for complete_index function."""

    def test_returns_matching_patterns(self) -> None:
        """Test returns patterns that match incomplete input."""
        results = complete_index("logs")
        assert "logs-*" in results

    def test_returns_all_patterns_for_empty_input(self) -> None:
        """Test returns all patterns for empty input."""
        results = complete_index("")
        assert len(results) > 0
        assert "logs-*" in results
        assert "*" in results

    def test_returns_empty_for_no_match(self) -> None:
        """Test returns empty list for no match."""
        results = complete_index("xyz")
        assert results == []

    def test_includes_otel_patterns(self) -> None:
        """Test includes OpenTelemetry patterns."""
        results = complete_index("otel")
        assert "otel-logs-*" in results


class TestCompleteTimeField:
    """Tests for complete_time_field function."""

    def test_returns_matching_fields(self) -> None:
        """Test returns fields that match incomplete input."""
        results = complete_time_field("@")
        assert "@timestamp" in results

    def test_returns_timestamp_fields(self) -> None:
        """Test returns timestamp-related fields."""
        results = complete_time_field("time")
        assert "timestamp" in results

    def test_returns_empty_for_no_match(self) -> None:
        """Test returns empty list for no match."""
        results = complete_time_field("xyz")
        assert results == []


class TestCompleteProject:
    """Tests for complete_project function."""

    def test_returns_matching_projects(self) -> None:
        """Test returns projects that match incomplete input."""
        results = complete_project("ins")
        assert "insurance" in results

    def test_case_insensitive(self) -> None:
        """Test matching is case-insensitive."""
        results = complete_project("LEP")
        assert "lep" in results

    def test_returns_all_projects_for_empty(self) -> None:
        """Test returns all projects for empty input."""
        results = complete_project("")
        assert "lep" in results
        assert "insurance" in results
        assert "saving" in results
        assert "ekyc" in results

    def test_returns_empty_for_no_match(self) -> None:
        """Test returns empty list for no match."""
        results = complete_project("xyz")
        assert results == []


class TestCompleteServer:
    """Tests for complete_server function."""

    def test_returns_matching_servers(self) -> None:
        """Test returns servers that match incomplete input."""
        results = complete_server("int")
        assert "internal" in results

    def test_case_insensitive(self) -> None:
        """Test matching is case-insensitive."""
        results = complete_server("EXT")
        assert "external" in results

    def test_returns_all_servers_for_empty(self) -> None:
        """Test returns all servers for empty input."""
        results = complete_server("")
        assert "internal" in results
        assert "external" in results


class TestCompleteOutputFormat:
    """Tests for complete_output_format function."""

    def test_returns_matching_formats(self) -> None:
        """Test returns formats that match incomplete input."""
        results = complete_output_format("js")
        assert "json" in results

    def test_case_insensitive(self) -> None:
        """Test matching is case-insensitive."""
        results = complete_output_format("JSON")
        assert "json" in results

    def test_returns_all_formats_for_empty(self) -> None:
        """Test returns all formats for empty input."""
        results = complete_output_format("")
        assert "json" in results
        assert "table" in results
        assert "csv" in results


class TestCompleteLogLevel:
    """Tests for complete_log_level function."""

    def test_returns_matching_levels(self) -> None:
        """Test returns levels that match incomplete input."""
        results = complete_log_level("ERR")
        assert "ERROR" in results

    def test_case_insensitive(self) -> None:
        """Test matching is case-insensitive."""
        results = complete_log_level("debug")
        assert "DEBUG" in results

    def test_returns_all_levels_for_empty(self) -> None:
        """Test returns all levels for empty input."""
        results = complete_log_level("")
        assert "DEBUG" in results
        assert "INFO" in results
        assert "WARNING" in results
        assert "ERROR" in results
        assert "CRITICAL" in results
