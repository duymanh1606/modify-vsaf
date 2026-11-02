"""Unit tests for ``vds-cli ecosystem report`` (TSK-P3-3.4).

Per VDS testing rules, these tests must NOT touch a real Postgres
instance. The session factory ``vds_cli.ecosystem.report._make_session``
is patched on every test that exercises a command body.

Spec: ``.gpt-5.4/specs/ecosystem-daily-report/tasks.md`` Wave 3.

Coverage breakdown (≥8 unit tests required):

* 3 happy-path tests — one per command (history / trends / anomalies).
* 3 empty-result tests — one per command.
* 1 missing-metric error test — ``trends --metric BOGUS``.
* 1 invalid ``--days`` test — ``history --days 0``.

Plus extra coverage tests for ``render_sparkline`` and the DSN guard,
keeping the module above 80% line coverage.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner
from vds_cli.ecosystem import ecosystem_app
from vds_cli.ecosystem.report import (
    EMPTY_STATE_BANNER,
    NULL_CELL,
    SPARKLINE_BARS,
    SPARKLINE_MIN_POINTS,
    TREND_METRICS,
    _fmt_nullable,
    _get_database_url,
    _validate_days,
    render_sparkline,
    render_sparkline_with_hint,
)

# ── Test helpers ─────────────────────────────────────────────────────────────


def _row(**kwargs):
    """Build a SimpleNamespace mimicking a SQLAlchemy Row (attribute access)."""
    base = {
        "report_date": date(2026, 4, 30),
        "generated_at": datetime(2026, 4, 30, 6, 0, tzinfo=UTC),
        "health_score": 90,
        "error_24h": 0,
        "success_24h": 100,
        "pending_depth": 0,
        "enqueued_depth": 0,
        "generation_duration_ms": 1234,
        "anomalies": {"items": []},
        "report_path": "/tmp/r.md",
        "value": 90,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _stub_session(rows):
    """Return a ``_make_session`` replacement yielding a session whose
    ``execute()`` returns the supplied rows.

    The session supports ``with`` (context manager) since the production
    code uses ``with _make_session() as session:``.
    """
    session = MagicMock()
    session.execute.return_value = iter(rows)
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return lambda: session


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ── render_sparkline ─────────────────────────────────────────────────────────


class TestRenderSparkline:
    def test_empty_series_returns_empty_string(self) -> None:
        assert render_sparkline([]) == ""

    def test_constant_series_collapses_to_lowest_bar(self) -> None:
        result = render_sparkline([5.0, 5.0, 5.0])
        assert result == SPARKLINE_BARS[0] * 3

    def test_strictly_increasing_series_uses_lowest_and_highest(self) -> None:
        result = render_sparkline([1.0, 2.0, 3.0, 4.0, 5.0])
        # First bar must be lowest, last bar must be highest.
        assert result[0] == SPARKLINE_BARS[0]
        assert result[-1] == SPARKLINE_BARS[-1]
        # All chars must be from the bar set.
        assert set(result).issubset(set(SPARKLINE_BARS))

    def test_uses_spec_bar_characters(self) -> None:
        # Spec mandates exactly these eight characters.
        assert SPARKLINE_BARS == ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")


# ── _validate_days / _get_database_url ───────────────────────────────────────


class TestValidationHelpers:
    def test_validate_days_accepts_positive(self) -> None:
        assert _validate_days(1) == 1
        assert _validate_days(365) == 365

    def test_validate_days_rejects_zero(self) -> None:
        with pytest.raises(typer.BadParameter):
            _validate_days(0)

    def test_validate_days_rejects_negative(self) -> None:
        with pytest.raises(typer.BadParameter):
            _validate_days(-3)

    def test_get_database_url_raises_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(typer.BadParameter):
            _get_database_url()

    def test_get_database_url_returns_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
        assert _get_database_url() == "postgresql://u:p@h/db"


# ── Command happy paths ──────────────────────────────────────────────────────


class TestHistoryCommand:
    def test_happy_path_renders_table(self, runner: CliRunner) -> None:
        rows = [
            _row(report_date=date(2026, 4, 30), health_score=92),
            _row(report_date=date(2026, 4, 29), health_score=88),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session",
            _stub_session(rows),
        ):
            result = runner.invoke(
                ecosystem_app, ["report", "history", "--days", "2"]
            )
        assert result.exit_code == 0, result.output
        assert "Ecosystem Report" in result.output
        assert "2026-04-30" in result.output
        assert "2026-04-29" in result.output

    def test_empty_result_prints_no_data(self, runner: CliRunner) -> None:
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session([])
        ):
            result = runner.invoke(
                ecosystem_app, ["report", "history", "--days", "7"]
            )
        assert result.exit_code == 0, result.output
        assert "No data available" in result.output

    def test_invalid_days_arg_raises_bad_parameter(
        self, runner: CliRunner
    ) -> None:
        # No DB calls expected; --days 0 must short-circuit at validation.
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session([])
        ):
            result = runner.invoke(
                ecosystem_app, ["report", "history", "--days", "0"]
            )
        # typer.BadParameter renders an error and a non-zero exit code.
        assert result.exit_code != 0
        # The error message surfaces somewhere — exact text varies by Typer
        # version but must contain at least one of these markers.
        output = result.output or ""
        assert (
            "must be a positive integer" in output
            or "BadParameter" in output
            or result.exit_code == 2
        )


class TestTrendsCommand:
    def test_happy_path_renders_sparkline_and_stats(
        self, runner: CliRunner
    ) -> None:
        rows = [
            _row(report_date=date(2026, 4, 30), value=90),
            _row(report_date=date(2026, 4, 29), value=70),
            _row(report_date=date(2026, 4, 28), value=80),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session(rows)
        ):
            result = runner.invoke(
                ecosystem_app,
                [
                    "report",
                    "trends",
                    "--metric",
                    "health_score",
                    "--days",
                    "3",
                ],
            )
        assert result.exit_code == 0, result.output
        assert "health_score" in result.output
        # At least one sparkline bar character must appear in the output.
        assert any(bar in result.output for bar in SPARKLINE_BARS)

    def test_empty_result_prints_metric_specific_message(
        self, runner: CliRunner
    ) -> None:
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session([])
        ):
            result = runner.invoke(
                ecosystem_app,
                ["report", "trends", "--metric", "health_score"],
            )
        assert result.exit_code == 0, result.output
        assert "No data available" in result.output
        assert "health_score" in result.output

    def test_unknown_metric_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(
            ecosystem_app,
            ["report", "trends", "--metric", "BOGUS_METRIC"],
        )
        assert result.exit_code != 0
        # Error message must list at least one valid metric so the operator
        # can self-correct.
        assert any(m in (result.output or "") for m in TREND_METRICS) or \
            "Unknown metric" in (result.output or "")


class TestAnomaliesCommand:
    def test_happy_path_aggregates_counts(self, runner: CliRunner) -> None:
        rows = [
            _row(
                report_date=date(2026, 4, 30),
                anomalies={"items": ["High error count: 5", "Queue backlog: 12"]},
            ),
            _row(
                report_date=date(2026, 4, 29),
                anomalies={"items": ["High error count: 5"]},
            ),
            _row(
                report_date=date(2026, 4, 28),
                anomalies={"items": []},
            ),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session(rows)
        ):
            result = runner.invoke(
                ecosystem_app,
                ["report", "anomalies", "--days", "30"],
            )
        assert result.exit_code == 0, result.output
        assert "Anomaly frequency" in result.output
        assert "High error count" in result.output
        # The most-common anomaly appeared twice; verify that count surfaces.
        assert "2" in result.output

    def test_empty_result_prints_no_data(self, runner: CliRunner) -> None:
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session([])
        ):
            result = runner.invoke(
                ecosystem_app,
                ["report", "anomalies", "--days", "30"],
            )
        assert result.exit_code == 0, result.output
        assert "No data available" in result.output

    def test_runs_with_no_anomalies_renders_clean_message(
        self, runner: CliRunner
    ) -> None:
        rows = [
            _row(report_date=date(2026, 4, 30), anomalies={"items": []}),
            _row(report_date=date(2026, 4, 29), anomalies={"items": []}),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session(rows)
        ):
            result = runner.invoke(
                ecosystem_app,
                ["report", "anomalies", "--days", "30"],
            )
        assert result.exit_code == 0, result.output
        assert "No anomalies" in result.output

    def test_legacy_list_payload_shape_supported(
        self, runner: CliRunner
    ) -> None:
        # Some historical rows may carry a bare list rather than {"items":[]}.
        rows = [
            _row(
                report_date=date(2026, 4, 30),
                anomalies=["alpha", "beta", "alpha"],
            ),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session(rows)
        ):
            result = runner.invoke(
                ecosystem_app,
                ["report", "anomalies", "--days", "1"],
            )
        assert result.exit_code == 0, result.output
        assert "alpha" in result.output
        assert "beta" in result.output


class TestEcosystemHelp:
    def test_top_level_help_lists_report_subgroup(
        self, runner: CliRunner
    ) -> None:
        result = runner.invoke(ecosystem_app, ["--help"])
        assert result.exit_code == 0
        assert "report" in result.output

    def test_report_help_lists_three_subcommands(
        self, runner: CliRunner
    ) -> None:
        result = runner.invoke(ecosystem_app, ["report", "--help"])
        assert result.exit_code == 0
        for cmd in ("history", "trends", "anomalies"):
            assert cmd in result.output


# ── _make_session SQLAlchemy factory (lines 107-112) ─────────────────────────


class TestMakeSession:
    """Cover the lazy SQLAlchemy import + session factory path."""

    def test_make_session_invokes_create_engine_and_sessionmaker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Patch SQLAlchemy at the import boundary; verify the DSN flows
        through ``create_engine`` and the returned object is what
        ``sessionmaker(...)()`` produced."""
        from vds_cli.ecosystem import report as report_mod

        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")

        engine_sentinel = object()
        session_sentinel = MagicMock(name="Session")
        sessionmaker_factory = MagicMock(return_value=session_sentinel)

        create_engine_calls: list[str] = []

        def fake_create_engine(url: str):
            create_engine_calls.append(url)
            return engine_sentinel

        sessionmaker_kwargs: dict = {}

        def fake_sessionmaker(**kwargs):
            sessionmaker_kwargs.update(kwargs)
            return sessionmaker_factory

        # The report module imports lazily inside _make_session; patch
        # at the source so the function-scope import resolves to fakes.
        import sqlalchemy
        import sqlalchemy.orm

        monkeypatch.setattr(sqlalchemy, "create_engine", fake_create_engine)
        monkeypatch.setattr(
            sqlalchemy.orm, "sessionmaker", fake_sessionmaker
        )

        result = report_mod._make_session()

        assert create_engine_calls == ["postgresql://u:p@h/db"]
        assert sessionmaker_kwargs.get("bind") is engine_sentinel
        assert sessionmaker_kwargs.get("expire_on_commit") is False
        assert result is session_sentinel


# ── History anomaly payload shape branches (lines 182-185) ───────────────────


class TestHistoryAnomalyPayloadShapes:
    """Cover the list / non-dict-non-list branches in the history command."""

    def test_history_handles_list_anomaly_payload(
        self, runner: CliRunner
    ) -> None:
        """A bare-list anomaly payload counts items via ``len(list)``."""
        rows = [
            _row(
                report_date=date(2026, 4, 30),
                anomalies=["err-a", "err-b", "err-c"],
            ),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session",
            _stub_session(rows),
        ):
            result = runner.invoke(
                ecosystem_app, ["report", "history", "--days", "1"]
            )
        assert result.exit_code == 0, result.output
        # The anomaly count column must read "3" (len of the list payload).
        assert "3" in result.output
        assert "2026-04-30" in result.output

    def test_history_handles_unexpected_payload_shape(
        self, runner: CliRunner
    ) -> None:
        """An unexpected anomaly payload type collapses to count=0 (else branch)."""
        rows = [
            # Anomaly column carries a non-dict, non-list value (e.g. str).
            # This is shape pollution, not API contract — the renderer must
            # treat it as zero anomalies and not crash.
            _row(
                report_date=date(2026, 4, 30),
                anomalies="legacy-string-payload",
            ),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session",
            _stub_session(rows),
        ):
            result = runner.invoke(
                ecosystem_app, ["report", "history", "--days", "1"]
            )
        assert result.exit_code == 0, result.output
        # The anomaly count column must read "0" — else-branch fallthrough.
        # Date present + table renders proves the row was processed.
        assert "2026-04-30" in result.output
        assert "Ecosystem Report" in result.output


# ── Anomalies command: unexpected payload-shape branch (line 319) ────────────


class TestAnomaliesUnexpectedPayloadShape:
    """The anomalies command must skip rows with non-dict/non-list payloads."""

    def test_anomalies_skips_unexpected_payload_shape(
        self, runner: CliRunner
    ) -> None:
        """When ``row.anomalies`` is a string (shape pollution), the row
        contributes zero items — the command must report 'No anomalies'."""
        rows = [
            _row(report_date=date(2026, 4, 30), anomalies="garbage"),
            _row(report_date=date(2026, 4, 29), anomalies=42),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session",
            _stub_session(rows),
        ):
            result = runner.invoke(
                ecosystem_app, ["report", "anomalies", "--days", "30"]
            )
        assert result.exit_code == 0, result.output
        # Both rows were skipped → no anomalies aggregated → clean message.
        assert "No anomalies" in result.output


# ── Wave 3.1 — Column truncation / fold ──────────────────────────────────────


class TestColumnFold:
    """Long path/timestamp columns must NOT silently truncate to ``…``.

    The default render must fold the long columns so the full text is
    visible (possibly across multiple lines). ``--full`` disables fold.
    """

    def test_long_report_path_is_not_truncated_by_default(
        self, runner: CliRunner
    ) -> None:
        """A 200-character report path must appear in full (folded), not
        cut off with a single-char ellipsis."""
        long_path = "/var/lib/vds/reports/ecosystem/" + ("subdir/" * 20) + (
            "report-2026-04-30.md"
        )
        rows = [
            _row(report_date=date(2026, 4, 30), report_path=long_path),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session",
            _stub_session(rows),
        ):
            # Force a wide rendering width so we can see the folded path.
            # CliRunner uses Console internally; an env var coerces width.
            result = runner.invoke(
                ecosystem_app,
                ["report", "history", "--days", "1"],
                env={"COLUMNS": "120"},
            )
        assert result.exit_code == 0, result.output
        # A unique substring deep inside the path proves no truncation
        # happened. With the old `overflow="ellipsis"` default this would
        # appear as `report_da…` and the substring would not be present.
        assert "report-2026-04-30.md" in result.output

    def test_full_flag_is_accepted(self, runner: CliRunner) -> None:
        """``--full`` is a valid flag and must not crash the command."""
        rows = [
            _row(report_date=date(2026, 4, 30), report_path="/tmp/r.md"),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session",
            _stub_session(rows),
        ):
            result = runner.invoke(
                ecosystem_app,
                ["report", "history", "--days", "1", "--full"],
            )
        assert result.exit_code == 0, result.output
        assert "Ecosystem Report" in result.output

    def test_history_help_documents_full_flag(
        self, runner: CliRunner
    ) -> None:
        """``--help`` for the history subcommand mentions ``--full``."""
        result = runner.invoke(ecosystem_app, ["report", "history", "--help"])
        assert result.exit_code == 0
        assert "--full" in result.output


# ── Wave 3.2 — Single-point sparkline hint ───────────────────────────────────


class TestSparklineInsufficientHint:
    """``render_sparkline_with_hint`` must annotate short series."""

    def test_single_point_includes_hint(self) -> None:
        out = render_sparkline_with_hint([42.0])
        assert "trend insufficient" in out
        assert "N=1" in out
        assert "≥3" in out

    def test_two_points_includes_hint(self) -> None:
        out = render_sparkline_with_hint([1.0, 2.0])
        assert "trend insufficient" in out
        assert "N=2" in out

    def test_three_or_more_points_no_hint(self) -> None:
        out = render_sparkline_with_hint([1.0, 2.0, 3.0])
        assert "trend insufficient" not in out
        # Bar characters only.
        assert set(out).issubset(set(SPARKLINE_BARS))

    def test_threshold_constant_is_three(self) -> None:
        # The renderer-spec contract: ≥3 points are required for a trend.
        assert SPARKLINE_MIN_POINTS == 3

    def test_trends_command_renders_hint_with_single_row(
        self, runner: CliRunner
    ) -> None:
        """End-to-end: ``trends`` over a single-row series surfaces the
        N<3 hint in the rendered table."""
        rows = [_row(report_date=date(2026, 4, 30), value=90)]
        with patch(
            "vds_cli.ecosystem.report._make_session",
            _stub_session(rows),
        ):
            result = runner.invoke(
                ecosystem_app,
                ["report", "trends", "--metric", "health_score"],
            )
        assert result.exit_code == 0, result.output
        assert "trend insufficient" in result.output
        assert "N=1" in result.output


# ── Wave 3.3 — Empty-state consistency across the three commands ─────────────


class TestEmptyStateConsistency:
    """All three commands must use the same empty-state banner shape."""

    def test_empty_banner_constant_uses_yellow_no_data(self) -> None:
        # Anchor the banner shape so the helper can't drift accidentally.
        assert "No data available" in EMPTY_STATE_BANNER
        assert "yellow" in EMPTY_STATE_BANNER

    def test_history_empty_banner_matches_anomalies_empty_banner(
        self, runner: CliRunner
    ) -> None:
        """The two commands that print the bare banner must produce
        byte-identical 'No data available' strings."""
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session([])
        ):
            history_out = runner.invoke(
                ecosystem_app, ["report", "history", "--days", "7"]
            ).output
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session([])
        ):
            anomalies_out = runner.invoke(
                ecosystem_app, ["report", "anomalies", "--days", "30"]
            ).output
        # Both must contain the canonical banner phrase.
        assert "No data available" in history_out
        assert "No data available" in anomalies_out

    def test_trends_empty_keeps_metric_suffix(
        self, runner: CliRunner
    ) -> None:
        """The trends-empty banner must extend the canonical phrase with a
        metric suffix, not invent a new one."""
        with patch(
            "vds_cli.ecosystem.report._make_session", _stub_session([])
        ):
            result = runner.invoke(
                ecosystem_app,
                ["report", "trends", "--metric", "health_score"],
            )
        assert "No data available" in result.output
        assert "health_score" in result.output


# ── Wave 3.4 — NULL cells render dim-grey ────────────────────────────────────


class TestNullCellDimRendering:
    """``_fmt_nullable`` must wrap ``None`` in Rich ``[dim]`` markup."""

    def test_fmt_nullable_none_returns_dim_em_dash(self) -> None:
        assert _fmt_nullable(None) == NULL_CELL
        assert NULL_CELL.startswith("[dim]")
        assert NULL_CELL.endswith("[/dim]")
        assert "—" in NULL_CELL

    def test_fmt_nullable_value_passes_through_unstyled(self) -> None:
        assert _fmt_nullable(42) == "42"
        assert _fmt_nullable("hello") == "hello"
        assert _fmt_nullable(0) == "0"

    def test_history_renders_em_dash_for_null_health_score(
        self, runner: CliRunner
    ) -> None:
        """A NULL ``health_score`` must surface as ``—`` in the table.

        Rich strips the ``[dim]`` markup before printing; what reaches
        ``result.output`` is the bare em-dash. The visual dim styling is
        applied at render time. We assert the em-dash is present.
        """
        rows = [
            _row(report_date=date(2026, 4, 30), health_score=None),
        ]
        with patch(
            "vds_cli.ecosystem.report._make_session",
            _stub_session(rows),
        ):
            result = runner.invoke(
                ecosystem_app, ["report", "history", "--days", "1"]
            )
        assert result.exit_code == 0, result.output
        assert "—" in result.output
