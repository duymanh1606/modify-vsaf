"""DRY Alembic env.py runtime helpers (WP-5.2 / ADR-INF-12).

Centralises the ~80% boilerplate shared across 4 service alembic/env.py files
(memory, audit, progress, scheduler). Each service's env.py is ~25 LOC of
declarative configuration.

API:
    resolve_database_url  — read DSN from a single canonical env var
    run_migrations_offline — configure Alembic context for offline SQL output
    run_migrations_online  — create engine, configure context, run migrations

Design constraints (per ADR-INF-11):
  - NEVER call connection.execute(text("SET search_path ...")) here.
    Under SQLAlchemy 2.0 that statement opens an implicit autocommit
    transaction that closes before Alembic's own begin_transaction() runs,
    silently breaking the alembic_version CREATE/INSERT. Per-app search_path
    is handled at the orchestrator level (psycopg `_connect()` helper for
    progress; SQLAlchemy `connect` event listener for memory) — see
    references/connection-pooling.md F21/D1 caveats.
  - NullPool is always used — no connection reuse across CLI invocations.
  - include_schemas=True is always set — required for cross-schema management.

v2.15.12: Removed `force_psycopg_v3` param + URL-rewriting / `?options=`
stripping logic. Per-stanza connect_query in pgbouncer.ini handles search_path
at backend startup; URLs no longer carry `?options=` fragments. Function
signature simplified from a fallback-list `env_vars: Sequence[str]` to a
single canonical `env_var: str` per the no-fallback directive.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from alembic import context
from sqlalchemy import MetaData, engine_from_config, pool

# Type alias matching alembic's include_name callback signature.
IncludeNameCallback = Callable[[str | None, str, dict[str, Any]], bool]


def resolve_database_url(*, env_var: str) -> str:
    """Return the database URL for Alembic migrations.

    Reads a single canonical env var. No fallback chain; if unset, raises.
    Post-v2.15.12 each service's env.py declares ONE env var (e.g., audit uses
    ``VDS_AUDIT_STATE_DSN``, memory/progress/scheduler use ``DATABASE_URL``).
    Mixed compose-vs-host-mode operator workflows must set the canonical var
    explicitly — there is no implicit fallback to a typed legacy variable.

    Raises:
        RuntimeError: if the env var is unset or empty.
    """
    url = os.environ.get(env_var)
    if not url:
        raise RuntimeError(
            f"Required environment variable is not set: {env_var}. Set it before running alembic or pass -x db=<url>."
        )
    return url


def run_migrations_offline(
    *,
    target_metadata: MetaData,
    schema: str,
    url: str,
    include_name: IncludeNameCallback,
    version_table_schema: str | None = None,
) -> None:
    """Configure Alembic context for offline mode and run migrations.

    Offline mode produces SQL script output rather than executing against a
    live database.  Useful for generating migration SQL for review/approval.

    *version_table_schema* defaults to *schema* when not provided, implementing
    the in-schema alembic_version policy from ADR-INF-11.  Pass an explicit
    value (e.g. ``version_table_schema="sched"``) to preserve WP-5.1's
    explicit override for scheduler.
    """
    effective_vts = version_table_schema if version_table_schema is not None else schema
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
        version_table="alembic_version",
        version_table_schema=effective_vts,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online(
    *,
    target_metadata: MetaData,
    schema: str,
    url: str,
    include_name: IncludeNameCallback,
    version_table_schema: str | None = None,
    alembic_config: Any,
) -> None:
    """Create a synchronous engine and run migrations in online mode.

    *alembic_config* must be the ``context.config`` object from the caller's
    env.py (used to read the [alembic] ini section and inject sqlalchemy.url).

    *version_table_schema* defaults to *schema* — same policy as offline mode.

    IMPORTANT: this function NEVER calls connection.execute(text("SET search_path
    ...")).  Doing so outside an explicit SA2.0 transaction causes the
    alembic_version CREATE/INSERT to silently fail.  Search_path is set
    out-of-band via DSN options + ALTER DATABASE (per ADR-INF-11 §SA2.0
    Implicit-TX Gotcha).
    """
    effective_vts = version_table_schema if version_table_schema is not None else schema

    configuration = alembic_config.get_section(alembic_config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            version_table="alembic_version",
            version_table_schema=effective_vts,
        )
        with context.begin_transaction():
            context.run_migrations()
