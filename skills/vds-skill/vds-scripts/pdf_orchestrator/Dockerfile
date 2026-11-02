# Multi-stage Dockerfile for VDS PDF Orchestrator
# Optimized for team development and production deployment

# Build Stage - with uv caching for faster builds
FROM python:3.14.4-slim AS builder

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Set work directory
WORKDIR /app

# Build context is vds-scripts/ workspace root.
# Use per-path `uv pip install` (avoids workspace-resolution requirement).
COPY pdf_orchestrator /app/pdf_orchestrator
COPY vds_cli_common /app/vds_cli_common

WORKDIR /app/pdf_orchestrator

# Install workspace deps as paths first, then pdf_orchestrator. uv has access
# to vds-cli-common in site-packages by the time pdf's pyproject references it.
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python --no-sources \
        /app/vds_cli_common \
        /app/pdf_orchestrator

# Production Stage - Minimal runtime image
FROM python:3.14.4-slim AS runtime

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PDF processing dependencies
    poppler-utils \
    ghostscript \
    imagemagick \
    # Image processing dependencies
    libfreetype6 \
    libpng-dev \
    libjpeg-dev \
    # Font support and text rendering
    fonts-dejavu-core \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz0b \
    libcairo2 \
    libfribidi0 \
    # Additional libraries for WeasyPrint and pandoc
    libpango-1.0-0 \
    libxml2 \
    libxslt1.1 \
    # File type detection
    libmagic1 \
    # Security and monitoring
    curl \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r vds && useradd -r -g vds --home-dir=/app vds

# Set work directory
WORKDIR /app

# Copy venv from builder to the SAME path so the entry-script shebangs
# (`#!/app/.venv/bin/python`) keep working in the runtime stage. Copying to
# a different path breaks shebangs without a rewrite step.
COPY --from=builder --chown=vds:vds /app/.venv /app/.venv

# Create data directories
RUN mkdir -p /app/data /app/logs /app/cache && \
    chown -R vds:vds /app/data /app/logs /app/cache /app/.venv

# Switch to non-root user
USER vds

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Healthcheck: pdf is a CLI now (post v2.7.0 prune); verify the entry point
# is callable. No HTTP server, no port to expose.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD /app/.venv/bin/vds-pdf --help > /dev/null 2>&1 || exit 1

# pdf is a CLI tool; the MCP server module was removed in v2.7.0 dep prune
# (fastmcp was a phantom dep). Run the typer CLI as the default — operators
# override CMD to invoke specific subcommands.
CMD ["/app/.venv/bin/vds-pdf", "--help"]
