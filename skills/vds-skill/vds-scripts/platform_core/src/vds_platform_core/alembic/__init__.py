"""vds_platform_core.alembic — DRY Alembic env.py helper (ADR-INF-12).

Exposes the three-function public API used by each service's alembic/env.py.
Landed in WP-5.2; all 4 service env.py files delegate to these helpers,
reducing per-service boilerplate from 138-170 LOC to ~25 LOC.
"""

from vds_platform_core.alembic.runtime import (
    resolve_database_url,
    run_migrations_offline,
    run_migrations_online,
)

__all__ = [
    "resolve_database_url",
    "run_migrations_offline",
    "run_migrations_online",
]
