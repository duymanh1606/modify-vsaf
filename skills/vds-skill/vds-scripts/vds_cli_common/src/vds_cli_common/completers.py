"""Common completers for VDS CLIs.

This module provides shell completion functions for common arguments
used across VDS orchestrator CLIs.

Usage:
    from vds_cli_common.completers import complete_index, complete_project

    @app.command()
    def search(
        index: str = typer.Option(
            "*",
            "--index", "-i",
            help="Index pattern",
            autocompletion=complete_index,
        ),
    ):
        pass
"""

from __future__ import annotations


def complete_index(incomplete: str) -> list[str]:
    """Provide common Elasticsearch index pattern suggestions.

    Returns common index patterns that match the incomplete input.
    This is static completion - doesn't query Elasticsearch for performance.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of matching index patterns
    """
    common_patterns = [
        "logs-*",
        "metrics-*",
        "traces-*",
        "filebeat-*",
        "metricbeat-*",
        "apm-*",
        ".kibana*",
        "otel-logs-*",
        "*",
    ]
    return [p for p in common_patterns if p.startswith(incomplete)]


def complete_time_field(incomplete: str) -> list[str]:
    """Provide common time field suggestions.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of matching time field names
    """
    common_fields = [
        "@timestamp",
        "timestamp",
        "time",
        "created_at",
        "updated_at",
        "event.created",
        "event_time",
    ]
    return [f for f in common_fields if f.startswith(incomplete)]


def complete_project(incomplete: str) -> list[str]:
    """Provide VDS project name suggestions.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of matching project names
    """
    projects = [
        "lep",
        "insurance",
        "saving",
        "ekyc",
    ]
    return [p for p in projects if p.startswith(incomplete.lower())]


def complete_server(incomplete: str) -> list[str]:
    """Provide Confluence server suggestions.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of matching server names
    """
    servers = [
        "internal",
        "external",
    ]
    return [s for s in servers if s.startswith(incomplete.lower())]


def complete_output_format(incomplete: str) -> list[str]:
    """Provide output format suggestions.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of matching output formats
    """
    formats = [
        "json",
        "table",
        "csv",
        "yaml",
    ]
    return [f for f in formats if f.startswith(incomplete.lower())]


def complete_log_level(incomplete: str) -> list[str]:
    """Provide log level suggestions.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of matching log levels
    """
    levels = [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]
    return [lvl for lvl in levels if lvl.startswith(incomplete.upper())]
