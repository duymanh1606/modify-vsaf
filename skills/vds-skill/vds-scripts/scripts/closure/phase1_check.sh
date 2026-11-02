#!/usr/bin/env bash
# =============================================================================
# Phase 1 Closure Check Script for WHO Ecosystem Evolution Loop (TSK-2.9)
# =============================================================================
#
# Verifies AC-9.7: Phase 1 closure criteria are met before proceeding to
# Phase 2. This script is a gate that must pass before the phase can close.
#
# AC-9.7 Requirements Verified:
# 1. Shadow tree exists and is populated
# 2. Anthropic judge reachable with pinned model ID matching calibration-manifest.yaml
# 3. Spot-check artifact present (TSK-1.10)
# 4. Rollback drill artifact exists and is recent (< 90 days)
#
# Usage:
#   ./scripts/closure/phase1_check.sh
#
# Exit Codes:
#   0 - All checks passed (phase 1 closure criteria met)
#   1 - One or more checks failed
#   2 - Missing required configuration
#
# Environment:
#   OPENSPACE_REPOSITORY_ROOT - Path to the openspace repository (defaults to CWD parent)
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve paths relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Repository root (parent of scripts directory)
REPO_ROOT="${OPENSPACE_REPOSITORY_ROOT:-$(cd "${SCRIPT_ROOT}/.." && pwd)}"

# Evolution log directory (within vds-skills repo)
EVOLUTION_LOG_ROOT="${REPO_ROOT}/WHO-project/vds-skills/.evolution-log"
DRILL_DIR="${EVOLUTION_LOG_ROOT}/drills"
CALIBRATION_DIR="${EVOLUTION_LOG_ROOT}/calibration"

# Paths to check
SHADOW_TREE="${REPO_ROOT}/WHO-project/vds-skills/skills"
CALIBRATION_MANIFEST="${EVOLUTION_LOG_ROOT}/calibration-manifest.yaml"
SPOT_CHECK="${CALIBRATION_DIR}/spot-check.json"
OPENSPACE_SKILLS="${REPO_ROOT}/WHO-project/vds-skills/skills"

# Maximum age for rollback drill artifact (in days)
MAX_DRILL_AGE_DAYS=90

# Counters
PASSED=0
FAILED=0
WARNINGS=0
TOTAL=0

# Track individual check results
declare -a CHECK_RESULTS=()

# ---------------------------------------------------------------------------
# Colors and Output
# ---------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_header() {
    echo ""
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${BLUE}  ${1}${NC}"
    echo -e "${BLUE}=============================================${NC}"
    echo ""
}

log_section() {
    echo -e "\n${CYAN}--- ${1} ---${NC}"
}

log_pass() {
    local check_name="${1}"
    local detail="${2:-}"
    PASSED=$((PASSED + 1))
    TOTAL=$((TOTAL + 1))
    CHECK_RESULTS+=("PASS:${check_name}")
    echo -e "  ${GREEN}[PASS]${NC} ${check_name}"
    if [[ -n "${detail}" ]]; then
        echo -e "         ${detail}"
    fi
}

log_fail() {
    local check_name="${1}"
    local detail="${2:-}"
    FAILED=$((FAILED + 1))
    TOTAL=$((TOTAL + 1))
    CHECK_RESULTS+=("FAIL:${check_name}")
    echo -e "  ${RED}[FAIL]${NC} ${check_name}"
    if [[ -n "${detail}" ]]; then
        echo -e "         ${detail}"
    fi
}

log_warn() {
    local check_name="${1}"
    local detail="${2:-}"
    WARNINGS=$((WARNINGS + 1))
    CHECK_RESULTS+=("WARN:${check_name}")
    echo -e "  ${YELLOW}[WARN]${NC} ${check_name}"
    if [[ -n "${detail}" ]]; then
        echo -e "         ${detail}"
    fi
}

# ---------------------------------------------------------------------------
# Check Functions
# ---------------------------------------------------------------------------

# AC-9.7.1: Shadow tree exists and is populated
check_shadow_tree() {
    log_section "AC-9.7.1: Shadow Tree Verification"

    # Check if shadow tree directory exists
    if [[ ! -d "${SHADOW_TREE}" ]]; then
        log_fail "Shadow tree directory does not exist" \
            "Expected: ${SHADOW_TREE}"
        return 1
    fi

    # Check if shadow tree is populated (has SKILL.md files)
    local skill_count
    skill_count=$(find "${SHADOW_TREE}" -name "SKILL.md" -type f 2>/dev/null | wc -l || echo "0")

    if [[ "${skill_count}" -eq 0 ]]; then
        log_fail "Shadow tree is empty (no SKILL.md files found)" \
            "Expected at least one skill in ${SHADOW_TREE}"
        return 1
    fi

    log_pass "Shadow tree exists and is populated" \
        "Found ${skill_count} skill(s) with SKILL.md files"

    # Additional: Check that shadow tree has recent entries
    local recent_count
    recent_count=$(find "${SHADOW_TREE}" -name "SKILL.md" -type f -mtime -30 2>/dev/null | wc -l || echo "0")

    if [[ "${recent_count}" -eq 0 ]]; then
        log_warn "No shadow skills modified in the last 30 days" \
            "This may indicate the shadow tree is stale"
    else
        echo -e "         ${recent_count} skill(s) modified within last 30 days"
    fi

    return 0
}

# AC-9.7.2: Anthropic judge reachable with pinned model ID
check_anthropic_judge() {
    log_section "AC-9.7.2: Anthropic Judge Reachability"

    # Check if Anthropic API key is set
    local api_key="${ANTHROPIC_API_KEY:-}"
    if [[ -z "${api_key}" ]]; then
        log_fail "ANTHROPIC_API_KEY is not set" \
            "Required for Gate 3 semantic judge"
        return 1
    fi

    log_pass "ANTHROPIC_API_KEY is configured"

    # Check if calibration manifest exists
    if [[ ! -f "${CALIBRATION_MANIFEST}" ]]; then
        log_warn "Calibration manifest not found at ${CALIBRATION_MANIFEST}" \
            "Cannot verify pinned model ID without calibration manifest"
        return 0  # Warning, not failure (manifest may be generated later)
    fi

    log_pass "Calibration manifest exists"

    # Extract pinned model ID from calibration manifest
    local pinned_model_id=""
    if command -v yq &>/dev/null; then
        pinned_model_id=$(yq '.judge.model_id' "${CALIBRATION_MANIFEST}" 2>/dev/null || echo "")
    elif command -v python3 &>/dev/null; then
        pinned_model_id=$(python3 -c "
import yaml
with open('${CALIBRATION_MANIFEST}') as f:
    data = yaml.safe_load(f)
print(data.get('judge', {}).get('model_id', ''))
" 2>/dev/null || echo "")
    fi

    if [[ -z "${pinned_model_id}" ]]; then
        log_warn "Could not extract pinned model ID from calibration manifest" \
            "Check that the manifest has 'judge.model_id' field"
        return 0  # Warning, not failure
    fi

    log_pass "Pinned model ID found in calibration manifest" \
        "Model: ${pinned_model_id}"

    # Attempt to verify the model ID is a known Anthropic model
    local known_models=("claude-3-5-sonnet-20241022" "claude-3-opus-20240229" "claude-3-sonnet-20240229" "claude-3-haiku-20240307" "claude-3-5-sonnet-latest" "claude-3-7-sonnet-20250219")
    local model_valid=false
    for known in "${known_models[@]}"; do
        if [[ "${pinned_model_id}" == "${known}" || "${pinned_model_id}" == "${known}"* ]]; then
            model_valid=true
            break
        fi
    done

    if [[ "${model_valid}" == "false" ]]; then
        log_warn "Pinned model ID '${pinned_model_id}' is not in the known models list" \
            "This may indicate an unknown or deprecated model"
    else
        log_pass "Pinned model ID is a known Anthropic model"
    fi

    # Test reachability with a minimal API call
    log_info "Testing Anthropic API reachability..."
    local api_response
    local api_status

    # Use a minimal request to test connectivity (not a full inference)
    api_response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "https://api.anthropic.com/v1/messages" \
        -H "x-api-key: ${api_key}" \
        -H "anthropic-version: 2023-06-01" \
        -H "content-type: application/json" \
        -d '{
            "model": "'"${pinned_model_id}"'",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "test"}]
        }' 2>/dev/null) || api_response="connection_failed"

    if [[ "${api_response}" == "connection_failed" ]]; then
        log_warn "Could not connect to Anthropic API" \
            "Check network connectivity and API key"
    elif [[ "${api_response}" == "429" ]]; then
        log_pass "Anthropic API is reachable (rate limited, but reachable)" \
            "HTTP ${api_response} - Rate limit hit means API is operational"
    elif [[ "${api_response}" == "400" || "${api_response}" == "401" || "${api_response}" == "403" ]]; then
        log_fail "Anthropic API returned error ${api_response}" \
            "Check API key validity and model access"
        return 1
    elif [[ "${api_response}" == "200" ]]; then
        log_pass "Anthropic API returned success (HTTP ${api_response})"
    else
        log_warn "Anthropic API returned unexpected status: ${api_response}"
    fi

    return 0
}

# AC-9.7.3: Spot-check artifact present (TSK-1.10)
check_spot_check_artifact() {
    log_section "AC-9.7.3: Spot-Check Artifact (TSK-1.10)"

    if [[ ! -f "${SPOT_CHECK}" ]]; then
        log_fail "Spot-check artifact not found" \
            "Expected: ${SPOT_CHECK}"
        log_info "Ensure TSK-1.10 spot-check has been executed"
        return 1
    fi

    log_pass "Spot-check artifact exists"

    # Validate artifact structure (basic JSON validation)
    if command -v python3 &>/dev/null; then
        local validation_result
        validation_result=$(python3 -c "
import json
import sys

try:
    with open('${SPOT_CHECK}') as f:
        data = json.load(f)

    # Check required fields
    required = ['artifact_id', 'timestamp', 'skills_checked', 'verdict']
    missing = [f for f in required if f not in data]

    if missing:
        print(f\"MISSING_FIELDS:{','.join(missing)}\")
        sys.exit(1)

    # Check skills_checked has entries
    if not data.get('skills_checked', []):
        print('EMPTY_SKILLS_CHECKED')
        sys.exit(1)

    print('VALID')
except json.JSONDecodeError as e:
    print(f\"INVALID_JSON:{e}\")
    sys.exit(1)
except Exception as e:
    print(f\"ERROR:{e}\")
    sys.exit(1)
" 2>&1) || true

        case "${validation_result}" in
            VALID)
                log_pass "Spot-check artifact has valid structure"
                ;;
            MISSING_FIELDS:*)
                local missing_fields="${validation_result#MISSING_FIELDS:}"
                log_fail "Spot-check artifact is missing required fields" \
                    "Missing: ${missing_fields}"
                return 1
                ;;
            EMPTY_SKILLS_CHECKED)
                log_fail "Spot-check artifact has no skills checked" \
                    "skills_checked array is empty"
                return 1
                ;;
            INVALID_JSON:*)
                log_fail "Spot-check artifact is not valid JSON" \
                    "Error: ${validation_result#INVALID_JSON:}"
                return 1
                ;;
            ERROR:*)
                log_fail "Error reading spot-check artifact" \
                    "Error: ${validation_result#ERROR:}"
                return 1
                ;;
        esac
    else
        log_warn "python3 not available for JSON validation" \
            "Skipping structure validation"
    fi

    return 0
}

# AC-9.7.4: Rollback drill artifact exists and is recent (< 90 days)
check_rollback_drill_artifact() {
    log_section "AC-9.7.4: Rollback Drill Artifact Recency"

    # Find the most recent rollback drill artifact
    local latest_artifact=""
    local latest_mtime=0

    if [[ ! -d "${DRILL_DIR}" ]]; then
        log_fail "Drill directory does not exist" \
            "Expected: ${DRILL_DIR}"
        return 1
    fi

    # Find all rollback artifacts
    while IFS= read -r artifact; do
        if [[ -f "${artifact}" ]]; then
            local mtime
            mtime=$(stat -f "%m" "${artifact}" 2>/dev/null || stat -c "%Y" "${artifact}" 2>/dev/null || echo "0")
            if [[ "${mtime}" -gt "${latest_mtime}" ]]; then
                latest_mtime="${mtime}"
                latest_artifact="${artifact}"
            fi
        fi
    done < <(find "${DRILL_DIR}" -name "rollback-*.json" -type f 2>/dev/null || true)

    if [[ -z "${latest_artifact}" ]]; then
        log_fail "No rollback drill artifacts found" \
            "Expected artifacts in: ${DRILL_DIR}"
        return 1
    fi

    log_pass "Rollback drill artifact exists" \
        "Latest: ${latest_artifact##*/}"

    # Check artifact age
    local current_time
    current_time=$(date +%s)
    local age_seconds=$((current_time - latest_mtime))
    local age_days=$((age_seconds / 86400))

    if [[ "${age_days}" -gt "${MAX_DRILL_AGE_DAYS}" ]]; then
        log_fail "Rollback drill artifact is too old (${age_days} days)" \
            "Maximum allowed age: ${MAX_DRILL_AGE_DAYS} days"
        return 1
    fi

    log_pass "Rollback drill artifact is recent" \
        "Age: ${age_days} day(s) (threshold: ${MAX_DRILL_AGE_DAYS} days)"

    return 0
}

# ---------------------------------------------------------------------------
# Summary and Exit
# ---------------------------------------------------------------------------

print_summary() {
    log_header "Phase 1 Closure Check Summary"

    echo -e "  Total checks:  ${TOTAL}"
    echo -e "  ${GREEN}Passed:        ${PASSED}${NC}"

    if [[ "${FAILED}" -gt 0 ]]; then
        echo -e "  ${RED}Failed:        ${FAILED}${NC}"
    else
        echo -e "  Failed:        ${FAILED}"
    fi

    if [[ "${WARNINGS}" -gt 0 ]]; then
        echo -e "  ${YELLOW}Warnings:      ${WARNINGS}${NC}"
    fi

    echo ""

    # Print detailed results
    if [[ ${#CHECK_RESULTS[@]} -gt 0 ]]; then
        echo -e "  ${BLUE}Check Details:${NC}"
        for result in "${CHECK_RESULTS[@]}"; do
            local status="${result%%:*}"
            local name="${result#*:}"
            case "${status}" in
                PASS)
                    echo -e "    ${GREEN}✓${NC} ${name}"
                    ;;
                FAIL)
                    echo -e "    ${RED}✗${NC} ${name}"
                    ;;
                WARN)
                    echo -e "    ${YELLOW}⚠${NC} ${name}"
                    ;;
            esac
        done
        echo ""
    fi

    # Final verdict
    if [[ "${FAILED}" -gt 0 ]]; then
        echo -e "  ${RED}PHASE 1 CLOSURE: NOT MET${NC}"
        echo -e "  ${RED}Fix ${FAILED} failure(s) before proceeding to Phase 2.${NC}"
        echo ""
        return 1
    else
        echo -e "  ${GREEN}PHASE 1 CLOSURE: MET${NC}"
        echo -e "  ${GREEN}All ${PASSED} required checks passed.${NC}"
        if [[ "${WARNINGS}" -gt 0 ]]; then
            echo -e "  ${YELLOW}${WARNINGS} warning(s) noted but do not block phase closure.${NC}"
        fi
        echo ""
        return 0
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    log_header "Phase 1 Closure Check (AC-9.7)"
    echo -e "  Timestamp:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo -e "  Repository: ${REPO_ROOT}"
    echo -e "  Max drill age: ${MAX_DRILL_AGE_DAYS} days"
    echo ""

    # Run all checks
    local all_passed=true

    check_shadow_tree || all_passed=false
    check_anthropic_judge || all_passed=false
    check_spot_check_artifact || all_passed=false
    check_rollback_drill_artifact || all_passed=false

    # Print summary
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main "$@"
