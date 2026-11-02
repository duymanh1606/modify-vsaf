#!/usr/bin/env bash
# validate-cli-standardization.sh — Validate vds-cli standardization
# Usage: ./scripts/validate-cli-standardization.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "========================================"
echo "  VDS CLI Standardization Validation"
echo "========================================"
echo ""

PASS=0
FAIL=0

pass() { echo "  ✅ PASS: $1"; ((PASS++)) || true; }
fail() { echo "  ❌ FAIL: $1"; ((FAIL++)) || true; }

# 1. Check DEFAULT_ENV_PATHS is populated
echo "1. Checking DEFAULT_ENV_PATHS..."
if grep -q "DEFAULT_ENV_PATHS = get_default_env_paths()" vds_cli_common/src/vds_cli_common/env.py; then
    pass "DEFAULT_ENV_PATHS is populated"
else
    fail "DEFAULT_ENV_PATHS is empty or broken"
fi

# 2. Check router has 33+ services
echo ""
echo "2. Checking router service count..."
COUNT=$(grep -c '"module"' vds_cli/src/vds_cli/router.py)
if [[ "$COUNT" -ge 33 ]]; then
    pass "Router has $COUNT services (>= 33)"
else
    fail "Router has $COUNT services (< 33)"
fi

# 3. Check new services are in router
echo ""
echo "3. Checking new services in router..."
for svc in hexagonal markdown mcp metabase multi_agent public_interface; do
    if python3 -c "
import sys
sys.path.insert(0, 'vds_cli/src')
from vds_cli.router import ORCHESTRATORS
assert '$svc' in ORCHESTRATORS, '$svc missing'
" 2>/dev/null; then
        pass "$svc in router"
    else
        fail "$svc missing from router"
    fi
done

# 4. Check vds-cli --help lists new services
echo ""
echo "4. Checking vds-cli --help lists new services..."
HELP_OUTPUT=$(./scripts/worktree_uv.sh run --project vds_cli vds-cli --help 2>&1 || true)
for svc in hexagonal markdown mcp metabase multi-agent public-interface; do
    if echo "$HELP_OUTPUT" | grep -q "$svc"; then
        pass "$svc in vds-cli --help"
    else
        fail "$svc missing from vds-cli --help"
    fi
done

# 5. Check vds-scripts AGENTS.md has unified routing
echo ""
echo "5. Checking vds-scripts AGENTS.md..."
if grep -q "single canonical entry point" AGENTS.md; then
    pass "vds-scripts AGENTS.md has unified routing mandate"
else
    fail "vds-scripts AGENTS.md missing unified routing mandate"
fi

# 6. Check vds-skills AGENTS.md has unified routing
echo ""
echo "6. Checking vds-skills AGENTS.md..."
VDS_SKILLS=""
for p in ../vds-skills/AGENTS.md ../../vds-skills/AGENTS.md; do
    if [ -f "$p" ]; then
        VDS_SKILLS="$p"
        break
    fi
done
if [ -n "$VDS_SKILLS" ] && grep -q "single canonical entry point" "$VDS_SKILLS"; then
    pass "vds-skills AGENTS.md has unified routing mandate"
else
    fail "vds-skills AGENTS.md missing unified routing mandate"
fi

# 7. Check vds-scripts-skill SKILL.md uses vds-cli
echo ""
echo "7. Checking vds-scripts-skill SKILL.md..."
SKILL_FILES=""
for p in ../vds-skills/skills/vds-scripts-skill/SKILL.md ../../vds-skills/skills/vds-scripts-skill/SKILL.md; do
    if [ -f "$p" ]; then SKILL_FILES="$p"; break; fi
done
if [ -n "$SKILL_FILES" ] && grep -q "vds-cli" "$SKILL_FILES"; then
    pass "vds-scripts-skill SKILL.md uses vds-cli"
else
    fail "vds-scripts-skill SKILL.md missing vds-cli"
fi

# 8. Check audit-orchestrator-skill uses vds-cli
echo ""
echo "8. Checking audit-orchestrator-skill SKILL.md..."
SKILL_FILES=""
for p in ../vds-skills/skills/audit-orchestrator-skill/SKILL.md ../../vds-skills/skills/audit-orchestrator-skill/SKILL.md; do
    if [ -f "$p" ]; then SKILL_FILES="$p"; break; fi
done
if [ -n "$SKILL_FILES" ] && grep -q "vds-cli audit" "$SKILL_FILES"; then
    pass "audit-orchestrator-skill SKILL.md uses vds-cli audit"
else
    fail "audit-orchestrator-skill SKILL.md missing vds-cli audit"
fi

# 9. Check .claude/rules/ use vds-cli
echo ""
echo "9. Checking .claude/rules/ project guides..."
RULES_DIR=""
for p in ../../.claude/rules ../.claude/rules .claude/rules; do
    if [ -d "$p" ]; then
        RULES_DIR="$p"
        break
    fi
done
IFS=$'\n'
if [ -n "$RULES_DIR" ] && [ -d "$RULES_DIR" ]; then
    : # RULES_DIR found
    # The glob in the for loop will not expand if no match; use explicit file check
    _rule1="$RULES_DIR/project-payment-dept.md"
    _rule2="$RULES_DIR/project-par.md"
    _rule3="$RULES_DIR/project-miniapp.md"
    unset IFS
    for rule_file in "$_rule1" "$_rule2" "$_rule3"; do
        if [ -f "$rule_file" ]; then
            if grep -q "vds-cli audit" "$rule_file"; then
                pass "$(basename "$rule_file") uses vds-cli audit"
            else
                fail "$(basename "$rule_file") missing vds-cli audit"
            fi
        fi
    done
else
    unset IFS
    echo "  ⚠️ No .claude/rules/ directory found, skipping"
fi

# 10. Check shell scripts use vds-cli
echo ""
echo "10. Checking shell scripts..."
for script in scripts/run-audit-in-tmux.sh scripts/run-project-audit.sh scripts/run-department-audit.sh; do
    if [[ -f "$script" ]]; then
        if grep -q "vds-cli audit" "$script"; then
            pass "$(basename $script) uses vds-cli audit"
        else
            fail "$(basename $script) missing vds-cli audit"
        fi
    fi
done

# 11. Check CI workflows use vds-cli (Phase 3, FR-11)
echo ""
echo "11. Checking CI workflows use vds-cli (not direct entry points)..."
CI_FAIL=0
for wf in .github/workflows/*.yml .github/workflows/*.yaml; do
    if [ -f "$wf" ]; then
        # Detect direct entry points: vds-<service> that is NOT preceded by "vds-cli"
        if grep -v 'vds-cli' "$wf" | grep -qE '\bvds-(audit|bitbucket|confluence|jira|git|memory|markdown|pdf|elastic|grafana|sonarqube|hexagonal|mcp|metabase|multi_agent|public_interface|openapi|links|structure|brd|intellij|lsp|circular_dependency|db_query|evolution|task|progress)\b'; then
            fail "$(basename "$wf") may contain direct entry-point invocation"
            CI_FAIL=1
        fi
    fi
done
if [ "$CI_FAIL" -eq 0 ]; then
    pass "CI workflows use vds-cli (no direct entry points)"
fi

# Summary
echo ""
echo "========================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
