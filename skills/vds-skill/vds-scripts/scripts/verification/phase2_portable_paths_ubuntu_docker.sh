#!/usr/bin/env bash
set -euo pipefail

# Phase 2 portable path/config verification on Ubuntu via Docker Compose.
# This validates the shared helper layer in a real Linux userspace while keeping
# the checked-out worktree mounted from the host.
#
# What this script proves:
# - explicit VDS env overrides work in Linux containers
# - platformdirs-backed helper defaults remain importable in Linux
# - focused Phase 2 tests pass under an Ubuntu image with uv installed
#
# What this script does NOT prove:
# - native Windows execution
# - Windows container behavior
# - any host-specific Docker Desktop path quirks beyond this mounted workspace

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE_ROOT="$(cd "$SCRIPT_DIR/.."/.. && pwd)"
COMPOSE_FILE="$WORKTREE_ROOT/docker/compose.phase2-verification.yml"

mkdir -p "$WORKTREE_ROOT/.phase2-linux/config" "$WORKTREE_ROOT/.phase2-linux/cache" "$WORKTREE_ROOT/.phase2-linux/logs"

docker compose -f "$COMPOSE_FILE" run --rm phase2-ubuntu-verifier

echo "Phase 2 Ubuntu/Docker Compose verification completed successfully."
