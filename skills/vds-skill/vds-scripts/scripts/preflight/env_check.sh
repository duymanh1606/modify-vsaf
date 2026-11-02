#!/usr/bin/env bash
# =============================================================================
# TSK-0.0: Environmental prerequisite check for WHO Ecosystem Evolution Loop
# FR: FR-3 (Gate 3 single-judge requires ANTHROPIC_API_KEY)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load .env if present
if [[ -f ~/.vds/.env ]]; then
    set -a
    source ~/.vds/.env
    set +a
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

echo "=============================================="
echo "Evolution Loop - Environment Prerequisite Check"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# Required: ANTHROPIC_API_KEY (for Gate 3 single-judge)
# -----------------------------------------------------------------------------
echo -n "Checking ANTHROPIC_API_KEY... "
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo -e "${RED}MISSING${NC}"
    echo "  → Required for Gate 3 (single-judge semantic evaluation)"
    echo "  → Add to ~/.vds/.env: ANTHROPIC_API_KEY=sk-ant-..."
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}OK${NC}"
fi

# -----------------------------------------------------------------------------
# Optional: OPENAI_API_KEY (for Phase 3+ three-judge ensemble)
# -----------------------------------------------------------------------------
echo -n "Checking OPENAI_API_KEY... "
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo -e "${YELLOW}NOT SET (optional in Phase 0-2)${NC}"
    echo "  → Will be required if Phase 3+ three-judge ensemble is activated"
else
    echo -e "${GREEN}OK${NC}"
fi

# -----------------------------------------------------------------------------
# Optional: VDS_GOOGLE_CREDENTIALS_PATH (for Phase 3+ judge provider)
# -----------------------------------------------------------------------------
echo -n "Checking VDS_GOOGLE_CREDENTIALS_PATH... "
if [[ -z "${VDS_GOOGLE_CREDENTIALS_PATH:-}" ]]; then
    echo -e "${YELLOW}NOT SET (optional in Phase 0-2)${NC}"
    echo "  → Will be required if Phase 3+ three-judge ensemble is activated"
else
    echo -e "${GREEN}OK${NC}"
fi

# -----------------------------------------------------------------------------
# Check OpenSpace installation (if applicable)
# -----------------------------------------------------------------------------
echo -n "Checking OpenSpace installation... "
OPENSPACE_PATH="${OPENSPACE_PATH:-$HOME/tools/OpenSpace}"
if [[ -d "$OPENSPACE_PATH" ]]; then
    echo -e "${GREEN}OK ($OPENSPACE_PATH)${NC}"
else
    echo -e "${YELLOW}NOT FOUND${NC}"
    echo "  → Will be installed during TSK-0.1"
fi

# -----------------------------------------------------------------------------
# Check vds-evolution package (internal detail, accessed via vds-cli evolution)
# -----------------------------------------------------------------------------
echo -n "Checking vds-evolution package (via vds-cli)... "
# vds-evolution binary is internal; vds-cli evolution is the user-facing command
    echo -e "${GREEN}OK${NC}"
elif python -c "import vds_evolution" 2>/dev/null; then
    echo -e "${GREEN}OK (importable)${NC}"
else
    echo -e "${YELLOW}NOT INSTALLED${NC}"
    echo "  → Will be scaffolded during TSK-0.6"
fi

echo ""
echo "=============================================="
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}Environment check PASSED${NC}"
    echo "All required prerequisites are met."
    exit 0
else
    echo -e "${RED}Environment check FAILED${NC}"
    echo "Missing $ERRORS required prerequisite(s)."
    echo "Please resolve the issues above before proceeding."
    exit 2
fi
