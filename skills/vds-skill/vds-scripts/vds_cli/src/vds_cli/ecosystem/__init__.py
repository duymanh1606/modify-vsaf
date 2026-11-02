"""vds-cli ecosystem subcommand group.

Implements TSK-P3-0.1 from .gpt-5.4/specs/ecosystem-daily-report/tasks.md
(Phase 3, Wave 0).

This package provides the operator-facing CLI dashboard for the Ecosystem
Daily Report (`scheduler_orchestrator`). Subcommands query the
`sched.ecosystem_report_runs` Postgres table directly to render historical
runs, metric trends with sparklines, and anomaly aggregations.

Layout:
    ecosystem/
        __init__.py     -- top-level Typer app + `report` subgroup binding
        report.py       -- history / trends / anomalies command implementations
"""

from __future__ import annotations

import typer

from .report import report_app

ecosystem_app = typer.Typer(
    help=(
        "Ecosystem Daily Report dashboard — query historical runs, metric "
        "trends with sparklines, and anomaly aggregations from "
        "sched.ecosystem_report_runs. Spec: "
        ".gpt-5.4/specs/ecosystem-daily-report/."
    ),
)

ecosystem_app.add_typer(
    report_app,
    name="report",
    help="Daily ecosystem report dashboard subcommands.",
)


__all__ = ["ecosystem_app"]
