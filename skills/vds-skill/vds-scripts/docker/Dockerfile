# syntax=docker/dockerfile:1
# =============================================================================
# VDS CLI (unified router) - Dockerfile
# Phase: ecosystem-infrastructure-evolution v2.12.2 follow-up
#
# Build context: vds-scripts workspace root (per docker-compose.cli.yml)
# Example: docker build -f docker/Dockerfile .
#
# Runtime contract:
#   - vds-cli is the unified routed CLI for all VDS orchestrator commands
#   - Reads ~/.vds/.env via env_file
#   - CLI tool, not a long-running service (HEALTHCHECK polls vds-cli version)
# =============================================================================

FROM python:3.14.4-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# System deps (curl for healthcheck; ca-certificates + git for outbound network/repo ops)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Workspace dep tree (per vds_cli/pyproject.toml [tool.uv.sources]):
#   vds_cli
#   ├── vds_cli_common (leaf)
#   ├── vds_evolution → vds_cli_common
#   ├── vds_bitbucket_orchestrator → vds_cli_common
#   └── vds_google_sheets_orchestrator → vds_cli_common
#
# Copy all 5 in topological order (leaf-first).
COPY vds_cli_common /app/vds_cli_common
COPY vds_evolution /app/vds_evolution
COPY bitbucket_orchestrator /app/bitbucket_orchestrator
COPY google_sheets_orchestrator /app/google_sheets_orchestrator
COPY vds_cli /app/vds_cli

# Canonical workspace install pattern: per-path `uv pip install --no-sources`
# (matches audit/progress/pdf/db-query/mcp-server Dockerfiles; avoids
# per-package uv.lock requirement).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python 3.14 /opt/venv && \
    uv pip install --python /opt/venv/bin/python --no-sources \
        /app/vds_cli_common \
        /app/vds_evolution \
        /app/bitbucket_orchestrator \
        /app/google_sheets_orchestrator \
        /app/vds_cli

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /opt/venv/bin/vds-cli --help > /dev/null 2>&1 || exit 1

ENTRYPOINT ["/opt/venv/bin/vds-cli"]
CMD ["--help"]

LABEL org.opencontainers.image.title="VDS CLI (unified router)" \
      org.opencontainers.image.description="Unified routed CLI entry point for all VDS orchestrator commands" \
      org.opencontainers.image.created="2026-04-26"
