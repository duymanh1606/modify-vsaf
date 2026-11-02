<!-- diátaxis: reference -->

# System Requirements

## Required

| Component | Version | Check Command |
|-----------|---------|---------------|
| Python | 3.14+ | `python3 --version` |
| uv | Latest | `uv --version` |
| Git | 2.40+ | `git --version` |
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |

## Optional

| Component | Purpose | Check Command |
|-----------|---------|---------------|
| VS Code | Recommended IDE | `code --version` |
| fzf | Fuzzy finder for shell | `fzf --version` |
| ripgrep (rg) | Fast search | `rg --version` |
| tree | Directory visualization | `tree --version` |

## Platform Support

| OS | Status | Notes |
|----|--------|-------|
| macOS | Supported | Apple Silicon and Intel |
| Linux | Supported | Ubuntu 22.04+, Rocky Linux 9+ |
| Windows | Not supported | Use WSL2 |

## Services (Docker)

| Service | Port | Image |
|---------|------|-------|
| Postgres | 5432 | postgres:16 |
| Redis | 6379 | redis:7 |
| Qdrant | 6333 | qdrant/qdrant |

## Verify Everything

```bash
# Run all checks
python3 --version && uv --version && git --version && docker --version

# Check running services
docker compose ps
```

## See Also

- [Quick Start](../tutorials/quick-start.md)
- [Configuration Reference](../reference/configuration-reference.md)

## Verification Workflow

Run this checklist before first `vds-cli` use:
```bash
# Core toolchain
python3 --version  # Expected: 3.14+
uv --version

# Container runtime
docker compose version
docker compose ps  # Verify Postgres/Redis/Qdrant are healthy

# Repository
python3 -c "import uuid; print('Python OK')"
uv sync  # Reproducible install
```

## See Also

- [Quick Start](../tutorials/quick-start.md)
- [Configuration Reference](../reference/configuration-reference.md)
- [Troubleshooting Guide](../how-to/troubleshooting-guide.md)