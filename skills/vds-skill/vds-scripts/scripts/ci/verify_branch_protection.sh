#!/usr/bin/env bash
# Verify Branch Protection Script (TSK-2.2)
#
# Checks that server-side branch protection is active on Bitbucket.
# Fails if any required restriction is missing.
#
# Usage: ./scripts/ci/verify_branch_protection.sh <repo>

set -uo pipefail

REPO="${1:-vds-skills}"
BITBUCKET_BASE="${VDS_BITBUCKET_HTTP_BASE:-http://bitbucket.digital.vn}"

# Load credentials
source ~/.vds/.env 2>/dev/null || true

if [ -z "${VDS_USERNAME:-}" ] || [ -z "${VDS_PASSWORD:-}" ]; then
    echo "Error: VDS_USERNAME and VDS_PASSWORD must be set in ~/.vds/.env"
    exit 1
fi

echo "=== Verifying Branch Protection for $REPO ==="
echo

FAILED=0

# Required restrictions
REQUIRED_RESTRICTIONS=(
    "no-deletes"
    "fast-forward-only"
    "read-only"
)

for RESTRICTION in "${REQUIRED_RESTRICTIONS[@]}"; do
    echo -n "Checking '$RESTRICTION' restriction... "

    RESPONSE=$(curl -s -u "$VDS_USERNAME:$VDS_PASSWORD" \
        "$BITBUCKET_BASE/rest/branch-permissions/2.0/projects/WHO/repos/$REPO/restrictions" \
        -H "Accept: application/json" 2>/dev/null)

    if echo "$RESPONSE" | grep -q "\"type\":\"$RESTRICTION\""; then
        echo "✓"
    else
        echo "✗ (missing)"
        FAILED=1
    fi
done

# Check openspace-mcp user restriction
echo -n "Checking 'openspace-mcp' user restriction... "
if echo "$RESPONSE" | grep -q "openspace-mcp"; then
    echo "✓"
else
    echo "⚠ (openspace-mcp user not restricted)"
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo "✓ Branch protection verification PASSED"
    exit 0
else
    echo "✗ Branch protection verification FAILED"
    exit 1
fi
