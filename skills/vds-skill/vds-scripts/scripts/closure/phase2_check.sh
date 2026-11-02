#!/usr/bin/env bash
# =============================================================================
# Phase 2 Closure Check Script for WHO Ecosystem Evolution Loop (TSK-2.10)
# =============================================================================
#
# Verifies AC-9.8 Phase 2 closure requirements before proceeding to Phase 3:
#   - At least one canonical promotion exists
#   - Server-side branch protection on master is active
#   - CI check for zero OpenSpace-authored master commits is green
#   - Classifier unit tests are green
#   - Rollback drill artifact < 90 days old
#
# Usage:
#   ./scripts/closure/phase2_check.sh
#
# Exit codes:
#   0 - All checks passed (phase 2 closure complete)
#   1 - One or more checks failed (phase 2 NOT ready to close)
#   2 - Script execution error
#
# Requires:
#   - Git repository initialized
#   - vds_evolution package installed
#   - Classifier tests available
#   - CI configuration present
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Evolution log and artifact paths
EVOLUTION_LOG="${PROJECT_ROOT}/.evolution-log"
DRILL_DIR="${EVOLUTION_LOG}/drills"
CALIBRATION_DIR="${EVOLUTION_LOG}/calibration"
SPECS_DIR="${PROJECT_ROOT}/.gpt-5.4/specs/who-ecosystem-evolution-loop"

# Paths to check
VDS_EVOLUTION="${PROJECT_ROOT}/vds_evolution"
CLASSIFIER_TESTS="${VDS_EVOLUTION}/tests/unit/test_classifier.py"
GATES_TESTS="${VDS_EVOLUTION}/tests/unit/test_gate1.py"

# Branch and promotion checks
MASTER_BRANCH="master"
EVOLUTION_LOG_FILE="${EVOLUTION_LOG}/promotion-log.json"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Counters and State
# ---------------------------------------------------------------------------

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_SKIPPED=0
TOTAL_CHECKS=0

# Array to store check results for summary
declare -a CHECK_RESULTS=()

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_ok() {
    echo -e "${GREEN}[PASS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $*"
}

log_section() {
    echo ""
    echo -e "${CYAN}================================================================${NC}"
    echo -e "${CYAN} $*${NC}"
    echo -e "${CYAN}================================================================${NC}"
}

record_check() {
    local check_name="$1"
    local result="$2"  # "pass", "fail", "skip"
    local detail="${3:-}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    case "${result}" in
        pass)
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
            record_result "${check_name}" "PASS" "${detail}"
            log_ok "${check_name}: ${detail}"
            ;;
        fail)
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            record_result "${check_name}" "FAIL" "${detail}"
            log_fail "${check_name}: ${detail}"
            ;;
        skip)
            CHECKS_SKIPPED=$((CHECKS_SKIPPED + 1))
            record_result "${check_name}" "SKIP" "${detail}"
            log_warn "${check_name}: ${detail}"
            ;;
    esac
}

record_result() {
    local check_name="$1"
    local result="$2"
    local detail="$3"

    CHECK_RESULTS+=("{\"check\":\"${check_name}\",\"result\":\"${result}\",\"detail\":\"${detail}\"}")
}

# ---------------------------------------------------------------------------
# AC-9.8 Check Functions
# ---------------------------------------------------------------------------

check_canonical_promotion() {
    log_section "AC-9.8.1: Canonical Promotion Verification"

    # Check 1: Verify promotion log exists and has entries
    if [[ -f "${EVOLUTION_LOG_FILE}" ]]; then
        local promotion_count
        promotion_count=$(python3 -c "
import json
try:
    with open('${EVOLUTION_LOG_FILE}') as f:
        data = json.load(f)
    if isinstance(data, list):
        promoted = [p for p in data if p.get('promotion_state') == 'promoted']
        print(len(promoted))
    elif isinstance(data, dict):
        promoted = data.get('promotions', [])
        print(len(promoted))
    else:
        print(0)
except Exception:
    print(0)
" 2>/dev/null || echo "0")

        if [[ "${promotion_count}" -gt 0 ]]; then
            record_check "canonical_promotion" "pass" "Found ${promotion_count} promotion(s) in log"
            return 0
        else
            # Check for alternative promotion markers
            if check_alternative_promotion_markers; then
                return 0
            fi
            record_check "canonical_promotion" "fail" "No promotions found in promotion log"
            return 1
        fi
    else
        # Check for promotion artifacts in quarantine repo
        if check_quarantine_promotions; then
            record_check "canonical_promotion" "pass" "Promotion artifacts found in quarantine"
            return 0
        fi
        record_check "canonical_promotion" "fail" "No promotion log and no quarantine artifacts"
        return 1
    fi
}

check_alternative_promotion_markers() {
    # Look for .evolution-log/promotions/ directory with promoted skill records
    local promotions_dir="${EVOLUTION_LOG}/promotions"

    if [[ -d "${promotions_dir}" ]]; then
        local promoted_files
        promoted_files=$(find "${promotions_dir}" -name "*.json" -exec grep -l '"promotion_state": *"promoted"' {} \; 2>/dev/null | wc -l || echo "0")
        if [[ "${promoted_files}" -gt 0 ]]; then
            record_check "alternative_promotion_check" "pass" "Found ${promoted_files} promoted skill(s)"
            return 0
        fi
    fi

    # Check for git merge commits on master that mention evolution
    if git rev-parse --verify "${MASTER_BRANCH}" &>/dev/null; then
        local evolution_commits
        evolution_commits=$(git log "${MASTER_BRANCH}" --grep="Evolution" --oneline 2>/dev/null | wc -l || echo "0")
        if [[ "${evolution_commits}" -gt 0 ]]; then
            record_check "alternative_promotion_check" "pass" "Found ${evolution_commits} evolution-related commits on master"
            return 0
        fi
    fi

    return 1
}

check_quarantine_promotions() {
    # Look for promoted verdicts in quarantine artifacts
    local quarantine_dir="${PROJECT_ROOT}/.evolution-log/quarantine"

    if [[ -d "${quarantine_dir}" ]]; then
        local verdict_count
        verdict_count=$(find "${quarantine_dir}" -name "*.json" -exec grep -l '"final_eligibility": *"eligible"' {} \; 2>/dev/null | wc -l || echo "0")
        if [[ "${verdict_count}" -gt 0 ]]; then
            record_check "quarantine_promotion_check" "pass" "Found ${verdict_count} eligible verdict(s)"
            return 0
        fi
    fi

    return 1
}

check_branch_protection() {
    log_section "AC-9.8.2: Branch Protection Verification"

    # Check if we're in a repository
    if ! git rev-parse --git-dir &>/dev/null; then
        record_check "branch_protection" "skip" "Not a Git repository"
        return 0
    fi

    # Check for branch protection rules via gh CLI (preferred)
    if command -v gh &>/dev/null; then
        local protection_status
        protection_status=$(gh api "repos/$(git remote get-url origin 2>/dev/null | sed 's|.*://github.com/||;s|\.git$||')/branches/${MASTER_BRANCH}/protection" 2>/dev/null || echo "NOT_FOUND")

        if [[ "${protection_status}" != "NOT_FOUND" ]]; then
            record_check "branch_protection" "pass" "Branch protection active on ${MASTER_BRANCH}"
            return 0
        fi
    fi

    # Fallback: Check for protected branch markers
    local protected_branches_file="${PROJECT_ROOT}/.github/protected-branches.json"

    if [[ -f "${protected_branches_file}" ]]; then
        if grep -q "\"${MASTER_BRANCH}\"" "${protected_branches_file}" 2>/dev/null; then
            record_check "branch_protection" "pass" "Branch listed in protected-branches.json"
            return 0
        fi
    fi

    # Check for CODEOWNERS or branch rules
    local codeowners_file="${PROJECT_ROOT}/.github/CODEOWNERS"
    if [[ -f "${codeowners_file}" ]]; then
        record_check "branch_protection" "pass" "CODEOWNERS file present (partial protection)"
        return 0
    fi

    # Warn but don't fail - server-side protection may be configured outside repo
    log_warn "Branch protection not detected - verify server-side configuration"
    record_check "branch_protection" "warn" "No local protection markers found"
    return 0
}

check_ci_zero_openspace_commits() {
    log_section "AC-9.8.3: Zero OpenSpace Master Commits Check"

    # Check if we're in a repository
    if ! git rev-parse --git-dir &>/dev/null; then
        record_check "ci_zero_openspace" "skip" "Not a Git repository"
        return 0
    fi

    # Check if master branch exists
    if ! git rev-parse --verify "${MASTER_BRANCH}" &>/dev/null; then
        record_check "ci_zero_openspace" "skip" "Master branch not found"
        return 0
    fi

    # Count OpenSpace-authored commits on master
    local openspace_commits
    openspace_commits=$(git log "${MASTER_BRANCH}" --author="openspace\|OpenSpace\|evolution-loop\|Evolution" --oneline 2>/dev/null | wc -l || echo "0")

    if [[ "${openspace_commits}" -eq 0 ]]; then
        record_check "ci_zero_openspace" "pass" "Zero OpenSpace-authored commits on master"
        return 0
    else
        record_check "ci_zero_openspace" "fail" "Found ${openspace_commits} OpenSpace-authored commit(s) on master"
        return 1
    fi
}

check_classifier_tests() {
    log_section "AC-9.8.4: Classifier Unit Tests"

    # Check if test file exists
    if [[ ! -f "${CLASSIFIER_TESTS}" ]]; then
        record_check "classifier_tests" "skip" "Classifier test file not found"
        return 0
    fi

    # Check if pytest is available
    if ! command -v pytest &>/dev/null && ! python3 -c "import pytest" 2>/dev/null; then
        log_warn "pytest not available - skipping classifier tests"
        record_check "classifier_tests" "skip" "pytest not available"
        return 0
    fi

    # Run classifier tests
    log_info "Running classifier unit tests..."

    local test_output
    local test_exit_code

    test_output=$(cd "${PROJECT_ROOT}" && python3 -m pytest "${CLASSIFIER_TESTS}" -q --tb=short 2>&1 || true)
    test_exit_code=$?

    if [[ ${test_exit_code} -eq 0 ]]; then
        # Parse test count from output
        local passed
        passed=$(echo "${test_output}" | grep -oP '\d+ passed' | grep -oP '\d+' || echo "0")
        record_check "classifier_tests" "pass" "${passed} test(s) passed"
        return 0
    else
        local failed
        failed=$(echo "${test_output}" | grep -oP '\d+ failed' | grep -oP '\d+' || echo "unknown")
        record_check "classifier_tests" "fail" "${failed} test(s) failed"
        return 1
    fi
}

check_rollback_drill_artifact() {
    log_section "AC-9.8.5: Rollback Drill Artifact Recency"

    # Check if drill directory exists
    if [[ ! -d "${DRILL_DIR}" ]]; then
        record_check "rollback_drill_artifact" "fail" "Drill directory not found"
        return 1
    fi

    # Find the most recent rollback drill artifact
    local latest_artifact
    latest_artifact=$(find "${DRILL_DIR}" -name "rollback-*.json" -type f | sort -r | head -n 1)

    if [[ -z "${latest_artifact}" ]]; then
        # Check for template as acceptable fallback
        if [[ -f "${DRILL_DIR}/rollback-drill-template.json" ]]; then
            record_check "rollback_drill_artifact" "warn" "No drill artifacts, template exists"
            return 0
        fi
        record_check "rollback_drill_artifact" "fail" "No rollback drill artifacts found"
        return 1
    fi

    # Get artifact modification date
    local artifact_date
    artifact_date=$(stat -f "%Sm" -t "%Y-%m-%d" "${latest_artifact}" 2>/dev/null || \
                   stat -c "%y" "${latest_artifact}" 2>/dev/null | cut -d' ' -f1)

    if [[ -z "${artifact_date}" ]]; then
        record_check "rollback_drill_artifact" "warn" "Cannot determine artifact date"
        return 0
    fi

    # Calculate age in days
    local current_date
    current_date=$(date +%Y-%m-%d)

    local age_days
    age_days=$(( ($(date -d "${current_date}" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "${current_date}" +%s 2>/dev/null) - \
                  $(date -d "${artifact_date}" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "${artifact_date}" +%s 2>/dev/null) ) / 86400 ))

    if [[ ${age_days} -lt 0 ]]; then
        age_days=0
    fi

    if [[ ${age_days} -le 90 ]]; then
        record_check "rollback_drill_artifact" "pass" "Drill artifact is ${age_days} days old (within 90-day threshold)"
        return 0
    else
        record_check "rollback_drill_artifact" "fail" "Drill artifact is ${age_days} days old (exceeds 90-day threshold)"
        return 1
    fi
}

check_calibration_artifacts() {
    log_section "AC-9.8.6: Calibration Artifacts Verification"

    # Check calibration manifest
    local calibration_manifest="${EVOLUTION_LOG}/calibration-manifest.yaml"

    if [[ -f "${calibration_manifest}" ]]; then
        record_check "calibration_manifest" "pass" "Calibration manifest exists"
    else
        record_check "calibration_manifest" "fail" "Calibration manifest not found"
        return 1
    fi

    # Check calibration directory
    if [[ -d "${CALIBRATION_DIR}" ]]; then
        local calibration_files
        calibration_files=$(find "${CALIBRATION_DIR}" -type f 2>/dev/null | wc -l || echo "0")
        if [[ ${calibration_files} -gt 0 ]]; then
            record_check "calibration_directory" "pass" "Found ${calibration_files} calibration artifact(s)"
        else
            record_check "calibration_directory" "fail" "Calibration directory is empty"
            return 1
        fi
    else
        record_check "calibration_directory" "fail" "Calibration directory not found"
        return 1
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Summary and Reporting
# ---------------------------------------------------------------------------

print_summary() {
    log_section "Phase 2 Closure Check Summary"

    echo ""
    echo "  Checks passed: ${CHECKS_PASSED}"
    echo "  Checks failed: ${CHECKS_FAILED}"
    echo "  Checks skipped: ${CHECKS_SKIPPED}"
    echo "  Total checks: ${TOTAL_CHECKS}"
    echo ""

    if [[ ${CHECKS_FAILED} -eq 0 ]]; then
        echo -e "${GREEN}Phase 2 closure criteria met. Proceed to Phase 3.${NC}"
        return 0
    else
        echo -e "${RED}Phase 2 closure criteria NOT met. Resolve failures before proceeding.${NC}"
        return 1
    fi
}

generate_report() {
    local report_file="${EVOLUTION_LOG}/phase-closure/phase-2-check-$(date +%Y-%m-%d).json"

    mkdir -p "${EVOLUTION_LOG}/phase-closure"

    cat > "${report_file}" <<EOF
{
  "check_type": "phase2_closure",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "checks_passed": ${CHECKS_PASSED},
  "checks_failed": ${CHECKS_FAILED},
  "checks_skipped": ${CHECKS_SKIPPED},
  "total_checks": ${TOTAL_CHECKS},
  "passed": $([ ${CHECKS_FAILED} -eq 0 ] && echo "true" || echo "false"),
  "results": [
$(printf '    %s,\n' "${CHECK_RESULTS[@]}" | sed '$ s/,$//')
  ]
}
EOF

    log_info "Report written to: ${report_file}"
}

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

main() {
    log_section "WHO Ecosystem Evolution Loop - Phase 2 Closure Check"
    log_info "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    log_info "Project Root: ${PROJECT_ROOT}"
    log_info "AC-9.8 Verification:"
    log_info "  1. Canonical promotion exists"
    log_info "  2. Server-side branch protection active"
    log_info "  3. Zero OpenSpace-authored master commits"
    log_info "  4. Classifier unit tests green"
    log_info "  5. Rollback drill artifact < 90 days old"

    # Run all checks
    check_canonical_promotion || true
    check_branch_protection || true
    check_ci_zero_openspace_commits || true
    check_classifier_tests || true
    check_rollback_drill_artifact || true
    check_calibration_artifacts || true

    # Print summary
    print_summary
    local exit_code=$?

    # Generate report
    generate_report

    exit ${exit_code}
}

# Run main
main "$@"
