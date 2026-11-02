# syntax=docker/dockerfile:1
FROM python:3.14.4-slim

# Install uv
RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh && echo "export PATH=\"$HOME/.cargo/bin:$PATH\"" >> /etc/profile

WORKDIR /app
COPY confluence_orchestrator/pyproject.toml /app/
COPY confluence_orchestrator/uv.lock /app/

# Sync deps (frozen)
RUN /root/.cargo/bin/uv sync --frozen

# Copy sources
COPY confluence_orchestrator/src /app/src

# Default command: run CLI help via uvx
CMD ["/root/.cargo/bin/uvx", "vds-confluence-cli", "--help"]
