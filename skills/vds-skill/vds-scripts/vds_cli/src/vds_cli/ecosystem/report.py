"""Ecosystem Daily Report dashboard commands.

Implements TSK-P3-3.1 / TSK-P3-3.2 / TSK-P3-3.3 from
``.gpt-5.4/specs/ecosystem-daily-report/tasks.md``.

The three subcommands all read from the Postgres table
``sched.ecosystem_report_runs``:

* ``vds-cli ecosystem report history --days N`` — table of last N runs.
* ``vds-cli ecosystem report trends --metric NAME`` — sparkline + stats.
* ``vds-cli ecosystem report anomalies --days N`` — anomaly frequency report.

Design notes
------------
* SQLAlchemy and ``DATABASE_URL`` resolution are imported lazily so that
  ``vds-cli ecosystem --help`` still works in environments that have not
  installed the scheduler runtime.
* All three commands route empty results through ``_render_empty_state``
  so the banner shape stays consistent (Wave 3.3).
* Sparkline characters match the spec verbatim: ``▁▂▃▄▅▆▇█``. With fewer
  than ``SPARKLINE_MIN_POINTS`` (3) values, ``render_sparkline_with_hint``
  appends an explicit "trend insufficient" hint so a single-bar sparkline
  is not misread as a trend (Wave 3.2).
* ``--days`` must be a positive integer; ``typer.BadParameter`` is raised
  otherwise.
* The ``history`` table folds long columns by default (``overflow="fold"``)
  so an 80-col terminal does not silently truncate the report path
  (Wave 3.1). Pass ``--full`` to force untruncated rendering.
* NULL cells in ``history`` render as ``[dim]—[/dim]`` so operators can
  see "data not yet populated" at a glance (Wave 3.4).
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

console = Console()

report_app = typer.Typer(
    help=(
        "Query the daily ecosystem report archive in "
        "sched.ecosystem_report_runs."
    ),
)


# ── Shared rendering helpers ─────────────────────────────────────────────────

# Sentinel rendered for NULL columns. Wrapped in Rich `[dim]` so operators
# can visually distinguish "data not yet populated" (Phase-3-pending columns)
# from a literal value at a glance (Wave 3.4).
NULL_CELL: str = "[dim]—[/dim]"

# Shared empty-state banner used by all three subcommands so the output
# shape is consistent (Wave 3.3).
EMPTY_STATE_BANNER: str = "[yellow]No data available[/yellow]"


def _render_empty_state(suffix: str = "") -> None:
    """Render the canonical empty-state banner.

    All three commands route through this helper so the operator sees the
    same shape regardless of which subcommand they run. ``suffix`` is an
    optional trailing string (e.g. ``" for metric 'health_score'"``) that
    keeps the metric-specific hint while preserving banner shape.
    """
    console.print(f"{EMPTY_STATE_BANNER}{suffix}")


def _fmt_nullable(value: Any) -> str:
    """Format a possibly-NULL cell value.

    Returns the dim-grey sentinel for ``None``; otherwise stringifies the
    value. Used for Phase-3-pending columns in history rows so missing
    data reads as "not yet populated", not as a literal em-dash (Wave 3.4).
    """
    if value is None:
        return NULL_CELL
    return str(value)


# ── Sparkline rendering (spec: ▁▂▃▄▅▆▇█) ─────────────────────────────────────

SPARKLINE_BARS: tuple[str, ...] = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")

# Numeric metrics whitelisted for the `trends` command. These are top-level
# columns on `sched.ecosystem_report_runs` (Phase 1 + Phase 2). When a new
# numeric column is added in a later phase, append it here.
TREND_METRICS: tuple[str, ...] = (
    "health_score",
    "error_24h",
    "success_24h",
    "pending_depth",
    "enqueued_depth",
    "generation_duration_ms",
)


def render_sparkline(values: list[float]) -> str:
    """Render a Unicode sparkline for a numeric series.

    Returns an empty string for an empty series. Constant series collapse
    to the lowest bar character — this matches the spec design.md
    pseudocode (the formatter never crashes on a flat series).
    """
    if not values:
        return ""
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return SPARKLINE_BARS[0] * len(values)
    span = hi - lo
    n = len(SPARKLINE_BARS) - 1
    return "".join(SPARKLINE_BARS[int((v - lo) / span * n)] for v in values)


# Minimum number of points required for a sparkline to convey a meaningful
# trend. With N=1 the sparkline is just ``▁`` (min=avg=max=latest); with
# N=2 the trend is ambiguous. Below this threshold the renderer appends
# an explicit hint so operators don't misread the bar (Wave 3.2).
SPARKLINE_MIN_POINTS: int = 3


def render_sparkline_with_hint(values: list[float]) -> str:
    """Render a sparkline; append a "trend insufficient" hint when N < 3.

    Returns the bare sparkline when there are enough points; otherwise
    returns ``"<spark> (trend insufficient: N=<count>, need ≥3)"`` so the
    operator immediately knows the bar is not a trend signal.
    """
    spark = render_sparkline(values)
    count = len(values)
    if count < SPARKLINE_MIN_POINTS:
        return (
            f"{spark} (trend insufficient: N={count}, "
            f"need ≥{SPARKLINE_MIN_POINTS})"
        )
    return spark


# ── Database access helpers (lazy SQLAlchemy import) ─────────────────────────


def _get_database_url() -> str:
    """Resolve the Postgres DSN for the scheduler database.

    Mirrors `scheduler_orchestrator.config.EcosystemSchedulerConfig`: the
    canonical env var is ``DATABASE_URL``. We do not import the scheduler
    config module here to keep the CLI independent of the orchestrator
    runtime (which may not be installed for plain operators).
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise typer.BadParameter(
            "DATABASE_URL is not set. Configure the scheduler Postgres DSN "
            "in ~/.vds/.env (key: DATABASE_URL).",
            param_hint="env:DATABASE_URL",
        )
    return url


def _make_session() -> Any:
    """Lazily build a SQLAlchemy session bound to the scheduler DSN.

    Returns a context-manageable Session. Tests patch this function
    directly to avoid touching real Postgres.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(_get_database_url())
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


def _validate_days(days: int) -> int:
    """Coerce/validate the --days argument."""
    if days <= 0:
        raise typer.BadParameter(
            f"--days must be a positive integer, got {days}.",
            param_hint="'--days'",
        )
    return days


# ── Commands ─────────────────────────────────────────────────────────────────


@report_app.command("history")
def history(
    days: Annotated[
        int,
        typer.Option(
            "--days",
            "-d",
            help="Number of recent runs to display (most recent first).",
        ),
    ] = 7,
    full: Annotated[
        bool,
        typer.Option(
            "--full/--no-full",
            help=(
                "Force full-width rendering instead of folding long columns. "
                "Default folds long timestamps and report paths so the table "
                "fits in an 80-column terminal."
            ),
        ),
    ] = False,
) -> None:
    """Show the last N ecosystem report runs as a table.

    Columns: report_date, generated_at, health_score, error_24h,
    success_24h, anomaly_count, report_path. Long columns
    (``generated_at``, ``report_path``) fold by default to fit narrow
    terminals; pass ``--full`` to disable folding.
    """
    n = _validate_days(days)
    from sqlalchemy import text

    sql = text(
        """
        SELECT report_date,
               generated_at,
               health_score,
               error_24h,
               success_24h,
               anomalies,
               report_path
        FROM sched.ecosystem_report_runs
        ORDER BY report_date DESC
        LIMIT :limit
        """
    )

    with _make_session() as session:
        rows = list(session.execute(sql, {"limit": n}))

    if not rows:
        _render_empty_state()
        return

    # Wave 3.1 — long columns fold by default so an 80-col terminal does
    # not silently truncate to "report_da…". Operators who want the full
    # untruncated table pass ``--full``.
    overflow = "ignore" if full else "fold"
    table = Table(title=f"Ecosystem Report — last {len(rows)} run(s)")
    table.add_column("report_date", style="cyan", overflow=overflow)
    table.add_column("generated_at", style="white", overflow=overflow)
    table.add_column("health", justify="right", overflow=overflow)
    table.add_column("err_24h", justify="right", style="red", overflow=overflow)
    table.add_column(
        "ok_24h", justify="right", style="green", overflow=overflow
    )
    table.add_column("anomalies", justify="right", overflow=overflow)
    table.add_column("report_path", style="dim", overflow=overflow)

    for row in rows:
        anomaly_payload = row.anomalies or {}
        if isinstance(anomaly_payload, dict):
            anomaly_count = len(anomaly_payload.get("items", []) or [])
        elif isinstance(anomaly_payload, list):
            anomaly_count = len(anomaly_payload)
        else:
            anomaly_count = 0
        table.add_row(
            _fmt_nullable(row.report_date),
            _fmt_nullable(row.generated_at),
            _fmt_nullable(row.health_score),
            _fmt_nullable(row.error_24h),
            _fmt_nullable(row.success_24h),
            str(anomaly_count),
            _fmt_nullable(row.report_path),
        )
    console.print(table)


@report_app.command("trends")
def trends(
    metric: Annotated[
        str,
        typer.Option(
            "--metric",
            "-m",
            help=(
                "Numeric metric to trend. Allowed: "
                + ", ".join(TREND_METRICS)
                + "."
            ),
        ),
    ] = "health_score",
    days: Annotated[
        int,
        typer.Option(
            "--days",
            "-d",
            help="History window (most-recent-first ordering).",
        ),
    ] = 7,
) -> None:
    """Show a sparkline + summary statistics for a metric over the window."""
    if metric not in TREND_METRICS:
        raise typer.BadParameter(
            f"Unknown metric '{metric}'. Allowed metrics: "
            f"{', '.join(TREND_METRICS)}.",
            param_hint="'--metric'",
        )
    n = _validate_days(days)

    from sqlalchemy import text

    # Column name is whitelisted above, so safe to interpolate.
    sql = text(
        f"""
        SELECT report_date, {metric} AS value
        FROM sched.ecosystem_report_runs
        WHERE {metric} IS NOT NULL
        ORDER BY report_date DESC
        LIMIT :limit
        """
    )
    with _make_session() as session:
        rows = list(session.execute(sql, {"limit": n}))

    if not rows:
        _render_empty_state(suffix=f" for metric '{metric}'")
        return

    # Reverse so the sparkline reads oldest → newest, left-to-right.
    ordered = list(reversed(rows))
    values = [float(r.value) for r in ordered]
    # Wave 3.2 — append a "trend insufficient" hint when N < 3 so a
    # single-bar sparkline isn't mistaken for a trend signal.
    spark = render_sparkline_with_hint(values)

    avg = sum(values) / len(values)
    table = Table(title=f"Trend — {metric} (last {len(values)} run(s))")
    table.add_column("metric", style="cyan")
    table.add_column("sparkline", style="magenta")
    table.add_column("min", justify="right")
    table.add_column("avg", justify="right")
    table.add_column("max", justify="right")
    table.add_column("latest", justify="right")
    table.add_row(
        metric,
        spark,
        f"{min(values):g}",
        f"{avg:.2f}",
        f"{max(values):g}",
        f"{values[-1]:g}",
    )
    console.print(table)


@report_app.command("anomalies")
def anomalies(
    days: Annotated[
        int,
        typer.Option(
            "--days",
            "-d",
            help="Lookback window in days (most-recent-first).",
        ),
    ] = 30,
) -> None:
    """Aggregate anomaly frequency over the last N runs.

    Reads the JSONB ``anomalies`` column. Each row's payload is expected
    to follow either the ``{"items": [str, ...]}`` shape (Phase 1) or a
    bare ``[str, ...]`` list. Unknown shapes are skipped.
    """
    n = _validate_days(days)
    from sqlalchemy import text

    sql = text(
        """
        SELECT report_date, anomalies
        FROM sched.ecosystem_report_runs
        ORDER BY report_date DESC
        LIMIT :limit
        """
    )
    with _make_session() as session:
        rows = list(session.execute(sql, {"limit": n}))

    if not rows:
        _render_empty_state()
        return

    counter: Counter[str] = Counter()
    runs_with_any = 0
    for row in rows:
        payload = row.anomalies or {}
        if isinstance(payload, dict):
            items = payload.get("items") or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        if items:
            runs_with_any += 1
        for item in items:
            counter[str(item)] += 1

    if not counter:
        console.print(
            f"[green]No anomalies in last {len(rows)} run(s)[/green]"
        )
        return

    table = Table(
        title=(
            f"Anomaly frequency — last {len(rows)} run(s) "
            f"({runs_with_any} run(s) flagged)"
        )
    )
    table.add_column("count", justify="right", style="red")
    table.add_column("anomaly", style="white")
    for label, count in counter.most_common():
        table.add_row(str(count), label)
    console.print(table)


__all__ = [
    "EMPTY_STATE_BANNER",
    "NULL_CELL",
    "SPARKLINE_BARS",
    "SPARKLINE_MIN_POINTS",
    "TREND_METRICS",
    "render_sparkline",
    "render_sparkline_with_hint",
    "report_app",
]
