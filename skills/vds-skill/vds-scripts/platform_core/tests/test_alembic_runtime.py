"""Unit tests for vds_platform_core.alembic.runtime (WP-5.2 / ADR-INF-12).

All tests are fully synthetic — no real Postgres, no real Alembic runner.
alembic.context and SQLAlchemy are mocked at the boundary so the helper
module's logic is exercised in isolation.

TDD discipline:
  - These tests were written BEFORE runtime.py existed (RED step).
  - They must fail until runtime.py is implemented (GREEN step).

Coverage targets:
  - resolve_database_url: single env var lookup; RuntimeError on missing.
    (v2.15.12: removed force_psycopg_v3 + fallback-list semantics — no-fallback
    directive; per-stanza connect_query in pgbouncer.ini handles search_path.)
  - run_migrations_offline: version_table_schema defaulting; explicit "sched"
    override; include_name plumbing; correct configure kwargs; no SET search_path.
  - run_migrations_online: same defaulting/override; engine_from_config called;
    context.configure called with connection kwarg; no text("SET search_path")
    executed on the connection.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_include_name():
    """Return a trivial include_name callable for wiring tests."""

    def _fn(name: str | None, type_: str, parent_names: dict[str, Any]) -> bool:
        return True

    return _fn


# ---------------------------------------------------------------------------
# resolve_database_url
# ---------------------------------------------------------------------------


class TestResolveDatabaseUrl:
    """Tests for resolve_database_url (v2.15.12 single-var, no-fallback)."""

    def test_returns_value_when_env_var_set(self, monkeypatch):
        """The env var's value is returned when set."""
        monkeypatch.setenv("MY_DSN", "postgresql://host/db")
        from vds_platform_core.alembic.runtime import resolve_database_url

        result = resolve_database_url(env_var="MY_DSN")
        assert result == "postgresql://host/db"

    def test_raises_runtime_error_when_unset(self, monkeypatch):
        """RuntimeError raised when env var is unset."""
        monkeypatch.delenv("MY_DSN", raising=False)
        import pytest
        from vds_platform_core.alembic.runtime import resolve_database_url

        with pytest.raises(RuntimeError, match="MY_DSN"):
            resolve_database_url(env_var="MY_DSN")

    def test_raises_runtime_error_when_empty_string(self, monkeypatch):
        """RuntimeError raised when env var is set to empty string."""
        monkeypatch.setenv("MY_DSN", "")
        import pytest
        from vds_platform_core.alembic.runtime import resolve_database_url

        with pytest.raises(RuntimeError, match="MY_DSN"):
            resolve_database_url(env_var="MY_DSN")

    def test_value_returned_verbatim_no_rewriting(self, monkeypatch):
        """v2.15.12: no URL rewriting (force_psycopg_v3 removed); returned as-is."""
        url = "postgresql+asyncpg://host/db"
        monkeypatch.setenv("MY_DSN", url)
        from vds_platform_core.alembic.runtime import resolve_database_url

        result = resolve_database_url(env_var="MY_DSN")
        assert result == url


# ---------------------------------------------------------------------------
# run_migrations_offline
# ---------------------------------------------------------------------------


class TestRunMigrationsOffline:
    """Tests for run_migrations_offline."""

    def _run(self, mock_context, *, schema, version_table_schema=None, **extra):
        """Helper: patch alembic.context and call run_migrations_offline."""
        from sqlalchemy import MetaData
        from vds_platform_core.alembic.runtime import run_migrations_offline

        include_name = _make_include_name()
        kwargs = {
            "target_metadata": MetaData(),
            "schema": schema,
            "url": "postgresql+psycopg://host/db",
            "include_name": include_name,
        }
        if version_table_schema is not None:
            kwargs["version_table_schema"] = version_table_schema
        kwargs.update(extra)
        run_migrations_offline(**kwargs)

    def test_version_table_schema_defaults_to_schema(self):
        """When version_table_schema omitted, it defaults to the schema argument."""
        with patch("vds_platform_core.alembic.runtime.context") as mock_ctx:
            mock_ctx.begin_transaction.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.begin_transaction.return_value.__exit__ = MagicMock(return_value=False)
            self._run(mock_ctx, schema="memory")
            configure_call = mock_ctx.configure.call_args
            assert configure_call.kwargs["version_table_schema"] == "memory"

    def test_explicit_version_table_schema_sched_preserved(self):
        """Explicit version_table_schema='sched' overrides the default."""
        with patch("vds_platform_core.alembic.runtime.context") as mock_ctx:
            mock_ctx.begin_transaction.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.begin_transaction.return_value.__exit__ = MagicMock(return_value=False)
            self._run(mock_ctx, schema="sched", version_table_schema="sched")
            configure_call = mock_ctx.configure.call_args
            assert configure_call.kwargs["version_table_schema"] == "sched"

    def test_include_name_callable_wired(self):
        """The include_name callable is passed through to context.configure."""
        with patch("vds_platform_core.alembic.runtime.context") as mock_ctx:
            mock_ctx.begin_transaction.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.begin_transaction.return_value.__exit__ = MagicMock(return_value=False)
            from sqlalchemy import MetaData

            fn = _make_include_name()
            from vds_platform_core.alembic.runtime import run_migrations_offline

            run_migrations_offline(
                target_metadata=MetaData(),
                schema="audit_state",
                url="postgresql+psycopg://host/db",
                include_name=fn,
            )
            configure_call = mock_ctx.configure.call_args
            assert configure_call.kwargs["include_name"] is fn

    def test_offline_configure_receives_url_and_literal_binds(self):
        """context.configure receives url= and literal_binds=True for offline mode."""
        with patch("vds_platform_core.alembic.runtime.context") as mock_ctx:
            mock_ctx.begin_transaction.return_value.__enter__ = MagicMock(return_value=None)
            mock_ctx.begin_transaction.return_value.__exit__ = MagicMock(return_value=False)
            self._run(mock_ctx, schema="progress")
            configure_kwargs = mock_ctx.configure.call_args.kwargs
            assert configure_kwargs["url"] == "postgresql+psycopg://host/db"
            assert configure_kwargs["literal_binds"] is True
            assert configure_kwargs["include_schemas"] is True

    def test_run_migrations_called_inside_transaction(self):
        """context.run_migrations() is called inside begin_transaction context."""
        with patch("vds_platform_core.alembic.runtime.context") as mock_ctx:
            tx_ctx = MagicMock()
            tx_ctx.__enter__ = MagicMock(return_value=None)
            tx_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.begin_transaction.return_value = tx_ctx
            self._run(mock_ctx, schema="memory")
            mock_ctx.begin_transaction.assert_called_once()
            mock_ctx.run_migrations.assert_called_once()


# ---------------------------------------------------------------------------
# run_migrations_online
# ---------------------------------------------------------------------------


class TestRunMigrationsOnline:
    """Tests for run_migrations_online."""

    def _build_alembic_config(self):
        """Build a minimal mock alembic config."""
        cfg = MagicMock()
        cfg.get_section.return_value = {}
        cfg.config_ini_section = "alembic"
        return cfg

    def _run(self, mock_context, mock_engine_from_config, *, schema, version_table_schema=None):
        """Helper: patch context + engine_from_config and call run_migrations_online."""
        from sqlalchemy import MetaData
        from vds_platform_core.alembic.runtime import run_migrations_online

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mock_engine_from_config.return_value = mock_engine

        mock_tx = MagicMock()
        mock_tx.__enter__ = MagicMock(return_value=None)
        mock_tx.__exit__ = MagicMock(return_value=False)
        mock_context.begin_transaction.return_value = mock_tx

        alembic_cfg = self._build_alembic_config()

        include_name = _make_include_name()
        kwargs = {
            "target_metadata": MetaData(),
            "schema": schema,
            "url": "postgresql+psycopg://host/db",
            "include_name": include_name,
            "alembic_config": alembic_cfg,
        }
        if version_table_schema is not None:
            kwargs["version_table_schema"] = version_table_schema
        run_migrations_online(**kwargs)
        return mock_conn, mock_engine

    def test_version_table_schema_defaults_to_schema_online(self):
        """version_table_schema defaults to schema when not provided (online mode)."""
        with (
            patch("vds_platform_core.alembic.runtime.context") as mock_ctx,
            patch("vds_platform_core.alembic.runtime.engine_from_config") as mock_efc,
        ):
            self._run(mock_ctx, mock_efc, schema="memory")
            configure_kwargs = mock_ctx.configure.call_args.kwargs
            assert configure_kwargs["version_table_schema"] == "memory"

    def test_explicit_sched_version_table_schema_preserved_online(self):
        """version_table_schema='sched' preserved from caller (WP-5.1 contract)."""
        with (
            patch("vds_platform_core.alembic.runtime.context") as mock_ctx,
            patch("vds_platform_core.alembic.runtime.engine_from_config") as mock_efc,
        ):
            self._run(mock_ctx, mock_efc, schema="sched", version_table_schema="sched")
            configure_kwargs = mock_ctx.configure.call_args.kwargs
            assert configure_kwargs["version_table_schema"] == "sched"

    def test_engine_from_config_called_with_url(self):
        """engine_from_config is called with sqlalchemy.url injected."""
        with (
            patch("vds_platform_core.alembic.runtime.context") as mock_ctx,
            patch("vds_platform_core.alembic.runtime.engine_from_config") as mock_efc,
        ):
            self._run(mock_ctx, mock_efc, schema="audit_state")
            assert mock_efc.called
            call_kwargs = mock_efc.call_args
            # First positional arg is the config dict
            config_dict = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("configuration", {})
            assert config_dict.get("sqlalchemy.url") == "postgresql+psycopg://host/db"

    def test_context_configure_receives_connection(self):
        """context.configure must receive connection= (not url=) in online mode."""
        with (
            patch("vds_platform_core.alembic.runtime.context") as mock_ctx,
            patch("vds_platform_core.alembic.runtime.engine_from_config") as mock_efc,
        ):
            _conn, _ = self._run(mock_ctx, mock_efc, schema="progress")
            configure_kwargs = mock_ctx.configure.call_args.kwargs
            assert "connection" in configure_kwargs
            assert "url" not in configure_kwargs

    def test_no_set_search_path_executed_on_connection(self):
        """connection.execute must NEVER be called with SET search_path.

        ADR-INF-11 §SA2.0 Implicit-TX Gotcha: executing SET search_path outside
        a transaction silently breaks the alembic_version CREATE/INSERT.
        The helper must NEVER call connection.execute with any SET statement.
        """
        with (
            patch("vds_platform_core.alembic.runtime.context") as mock_ctx,
            patch("vds_platform_core.alembic.runtime.engine_from_config") as mock_efc,
        ):
            conn, _ = self._run(mock_ctx, mock_efc, schema="memory")
            # Verify connection.execute was never called with SET search_path
            for call_args in conn.execute.call_args_list:
                args = call_args.args
                if args:
                    stmt = str(args[0])
                    assert "SET search_path" not in stmt, (
                        f"connection.execute called with SET search_path: {stmt!r}. "
                        "ADR-INF-11 §SA2.0 Implicit-TX Gotcha forbids this."
                    )

    def test_include_schemas_true_in_online_configure(self):
        """include_schemas=True must be in context.configure kwargs."""
        with (
            patch("vds_platform_core.alembic.runtime.context") as mock_ctx,
            patch("vds_platform_core.alembic.runtime.engine_from_config") as mock_efc,
        ):
            self._run(mock_ctx, mock_efc, schema="audit_state")
            configure_kwargs = mock_ctx.configure.call_args.kwargs
            assert configure_kwargs.get("include_schemas") is True

    def test_run_migrations_called_in_online_mode(self):
        """context.run_migrations() called inside begin_transaction in online mode."""
        with (
            patch("vds_platform_core.alembic.runtime.context") as mock_ctx,
            patch("vds_platform_core.alembic.runtime.engine_from_config") as mock_efc,
        ):
            self._run(mock_ctx, mock_efc, schema="sched")
            mock_ctx.run_migrations.assert_called_once()
