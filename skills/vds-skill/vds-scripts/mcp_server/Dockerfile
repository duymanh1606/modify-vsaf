# syntax=docker/dockerfile:1
# =============================================================================
# VDS MCP Server - Dockerfile
# Phase: ecosystem-infrastructure-evolution v2.12.2 follow-up
#
# Build context: vds-scripts workspace root (per docker-compose.cli.yml)
# Example: docker build -f mcp_server/Dockerfile .
#
# Runtime contract:
#   - MCP (Model Context Protocol) server for VDS
#   - Reads ~/.vds/.env via env_file
#   - Long-running service (HEALTHCHECK polls --help)
# =============================================================================

FROM python:3.14.4-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# System deps (curl for healthcheck; ca-certificates for outbound HTTPS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy mcp_server + its workspace dep (vds_cli_common)
COPY mcp_server/pyproject.toml /app/mcp_server/
COPY mcp_server/README.md /app/mcp_server/
COPY mcp_server/src /app/mcp_server/src

COPY vds_cli_common /app/vds_cli_common

# Canonical workspace pattern: per-path `uv pip install --no-sources`
# (matches audit/progress/pdf/db-query Dockerfiles; avoids per-package
# uv.lock requirement that the workspace doesn't carry per-service).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --python 3.14 /opt/venv && \
    uv pip install --python /opt/venv/bin/python --no-sources \
        /app/vds_cli_common \
        /app/mcp_server

# Create non-root user for security (matches pattern in all other VDS Dockerfiles)
RUN groupadd --system vds && useradd --system --no-create-home --gid vds mcp && \
    chown -R mcp:vds /app /opt/venv
USER mcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /opt/venv/bin/vds-mcp-server --help || exit 1

ENTRYPOINT ["/opt/venv/bin/vds-mcp-server"]
CMD ["--help"]

LABEL org.opencontainers.image.title="VDS MCP Server" \
      org.opencontainers.image.description="Model Context Protocol server for VDS orchestrators" \
      org.opencontainers.image.created="2026-04-26"
