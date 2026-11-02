#!/usr/bin/env bash
# Assert No OpenSpace Commits Script (TSK-2.2)
#
# Checks that no commits authored by 'openspace-mcp' exist on master.
# Fails if any OpenSpace-authored commits are found.
#
# Usage: ./scripts/ci/assert_no_openspace_commits.sh <repo>

set -uo pipefail

REPO="${1:-vds-skills}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_PATH="$PROJECT_ROOT/WHO-project/$REPO"

echo "=== Checking for OpenSpace-authored commits on master ==="
echo

if [ ! -d "$REPO_PATH/.git" ]; then
    echo "Error: Not a git repository: $REPO_PATH"
    exit 1
fi

cd "$REPO_PATH"

# Check for commits by openspace-mcp
COMMITS=$(git log master --since="2024-01-01" --author="openspace-mcp" --oneline 2>/dev/null || echo "")

if [ -n "$COMMITS" ]; then
    echo "✗ Found OpenSpace-authored commits on master:"
    echo "$COMMITS"
    echo
    echo "This indicates a violation of branch protection policy."
    exit 1
else
    echo "✓ No OpenSpace-authored commits found on master"
    exit 0
fi
