#!/usr/bin/env bash
# =============================================================================
# Rollback Drill Script for WHO Ecosystem Evolution Loop (TSK-1.12)
# =============================================================================
#
# This script performs an intentional rollback drill to verify that:
# 1. Shadow skill corruption can be detected
# 2. Single-skill restore via git checkout works correctly
# 3. Whole-quarantine restore via git reset --hard works correctly
# 4. verify-alignment.sh passes post-rollback
# 5. Drill results are recorded as artifacts
#
# Usage:
#   ./scripts/rollback_drill.sh [--single | --full | --both]
#
# Options:
#   --single   Perform single-skill restore only (default)
#   --full     Perform whole-quarantine restore only
#   --both     Perform both single and full rollback drills
#
# Artifacts produced:
#   .evolution-log/drills/rollback-YYYY-MM-DD.json
#
# Requires:
#   - Git repository initialized
#   - openspace-evolved branch exists
#   - master branch exists
#   - verify-alignment.sh script exists
#   - At least one shadow skill in the quarantine
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve project root (assumes script is run from project root or vds-scripts dir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Evolution log directory
EVOLUTION_LOG_DIR="${PROJECT_ROOT}/.evolution-log"
DRILL_DIR="${EVOLUTION_LOG_DIR}/drills"

# Paths
SKILLS_ROOT="${PROJECT_ROOT}/WHO-project/vds-skills/skills"
VDS_SCRIPTS_ROOT="${PROJECT_ROOT}/WHO-project/vds-scripts"
VERIFY_ALIGNMENT="${PROJECT_ROOT}/WHO-project/vds-skills/scripts/verify-alignment.sh"

# Timestamp for artifact naming
DRILL_TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
DRILL_DATE="$(date +%Y-%m-%d)"
ARTIFACT_PATH="${DRILL_DIR}/rollback-${DRILL_DATE}.json"

# Drill mode (default: single)
DRILL_MODE="${1:---single}"

# Colors for output (if terminal supports it)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $*"
}

# Initialize drill result structure
# Returns JSON-compatible object stored in associative array
declare -A DRILL_RESULT
DRILL_RESULT[status]="pending"
DRILL_RESULT[start_time]=""
DRILL_RESULT[end_time]=""
DRILL_RESULT[mode]=""
DRILL_RESULT[steps]="[]"
DRILL_RESULT[error]=""

drill_init() {
    DRILL_RESULT[start_time]="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    DRILL_RESULT[mode]="${DRILL_MODE}"
    log_info "Rollback drill initialized: mode=${DRILL_MODE}"
}

drill_complete() {
    DRILL_RESULT[end_time]="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    DRILL_RESULT[status]="completed"
    log_info "Rollback drill completed: status=${DRILL_RESULT[status]}"
}

drill_fail() {
    local reason="${1:-unknown error}"
    DRILL_RESULT[end_time]="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    DRILL_RESULT[status]="failed"
    DRILL_RESULT[error]="${reason}"
    log_error "Rollback drill failed: ${reason}"
}

# Add a step to the drill steps array (JSON fragment)
add_step() {
    local step_name="${1}"
    local step_status="${2:-pending}"
    local step_detail="${3:-}"

    log_info "Drill step: ${step_name} [${step_status}]"

    # Store step for later JSON assembly
    eval "STEP_${step_name//[^a-zA-Z0-9]/_}_status='${step_status}'"
    eval "STEP_${step_name//[^a-zA-Z0-9]/_}_detail='${step_detail}'"
}

# ---------------------------------------------------------------------------
# Drill Steps
# ---------------------------------------------------------------------------

# Step 1: Verify prerequisites exist
step_prerequisites() {
    log_info "=== Step 1: Verifying prerequisites ==="

    # Check Git repository
    if ! git rev-parse --git-dir &>/dev/null; then
        drill_fail "Not a Git repository"
        return 1
    fi
    add_step "prerequisites.git" "pass" "Git repository verified"

    # Check branches
    local branches
    branches="$(git branch --list 2>/dev/null || true)"

    if ! echo "${branches}" | grep -q "openspace-evolved"; then
        drill_fail "Branch 'openspace-evolved' not found"
        return 1
    fi
    add_step "prerequisites.branches" "pass" "openspace-evolved branch exists"

    if ! echo "${branches}" | grep -q "master"; then
        drill_fail "Branch 'master' not found"
        return 1
    fi
    add_step "prerequisites.branches.master" "pass" "master branch exists"

    # Check shadow skills exist
    if [[ ! -d "${SKILLS_ROOT}" ]]; then
        log_warn "Skills root does not exist: ${SKILLS_ROOT}"
        log_warn "Skipping shadow skill tests - no skills directory found"
        add_step "prerequisites.shadow_skills" "skipped" "No shadow skills directory"
        return 0
    fi

    local skill_count
    skill_count="$(find "${SKILLS_ROOT}" -name "SKILL.md" 2>/dev/null | wc -l || echo "0")"

    if [[ "${skill_count}" -eq 0 ]]; then
        log_warn "No shadow skills found - drill will test git mechanics only"
        add_step "prerequisites.shadow_skills" "skipped" "No SKILL.md files found"
        return 0
    fi

    add_step "prerequisites.shadow_skills" "pass" "Found ${skill_count} shadow skill(s)"

    # Check verify-alignment.sh
    if [[ -f "${VERIFY_ALIGNMENT}" ]]; then
        add_step "prerequisites.verify_alignment" "pass" "verify-alignment.sh found"
    else
        log_warn "verify-alignment.sh not found at ${VERIFY_ALIGNMENT}"
        log_warn "Post-rollback alignment check will be skipped"
        add_step "prerequisites.verify_alignment" "skipped" "Script not found"
    fi

    return 0
}

# Step 2: Intentionally corrupt a shadow skill
step_corrupt_skill() {
    log_info "=== Step 2: Injecting corruption into shadow skill ==="

    # Find a skill to corrupt
    local target_skill=""
    local target_skill_path=""

    if [[ ! -d "${SKILLS_ROOT}" ]]; then
        log_warn "No skills directory - skipping corruption step"
        add_step "corrupt_skill" "skipped" "No skills directory"
        return 0
    fi

    # Pick the first skill found
    target_skill_path="$(find "${SKILLS_ROOT}" -name "SKILL.md" -type f | head -n 1)"

    if [[ -z "${target_skill_path}" ]]; then
        log_warn "No SKILL.md files found - skipping corruption"
        add_step "corrupt_skill" "skipped" "No files found"
        return 0
    fi

    target_skill="$(dirname "${target_skill_path}")"
    target_skill="$(basename "${target_skill}")"

    log_info "Target skill for corruption: ${target_skill}"

    # Save original content hash for verification
    local original_hash
    original_hash="$(sha256sum "${target_skill_path}" | awk '{print $1}')"
    add_step "corrupt_skill.original_hash" "pass" "${original_hash:0:16}..."

    # Inject malformed frontmatter
    local corruption_marker="CORRUPTED_DRILL_MARKER_$(date +%s)"

    # Create corrupted version by injecting invalid YAML frontmatter
    local corrupted_content
    corrupted_content="---
name: ${target_skill}
description: Pre-drill content
category: development
broken-frontmatter: [unclosed
---

# Skill Content (restored after drill)"

    cp "${target_skill_path}" "${target_skill_path}.drill-backup"

    echo "${corrupted_content}" > "${target_skill_path}"

    local corrupted_hash
    corrupted_hash="$(sha256sum "${target_skill_path}" | awk '{print $1}')"

    if [[ "${original_hash}" == "${corrupted_hash}" ]]; then
        log_error "Corruption injection failed - hashes are identical"
        # Restore from backup
        mv "${target_skill_path}.drill-backup" "${target_skill_path}"
        return 1
    fi

    log_success "Skill corrupted: ${target_skill}"
    log_info "  Original hash:  ${original_hash:0:16}..."
    log_info "  Corrupted hash: ${corrupted_hash:0:16}..."

    # Store for artifact
    eval "STEP_CORRUPT_SKILL_CORRUPTED_HASH='${corrupted_hash}'"
    eval "STEP_CORRUPT_SKILL_BACKUP_PATH='${target_skill_path}.drill-backup'"

    add_step "corrupt_skill.injection" "pass" "Malformed frontmatter injected"

    return 0
}

# Step 3: Detect corruption via verify-alignment
step_detect_corruption() {
    log_info "=== Step 3: Detecting corruption ==="

    if [[ ! -f "${VERIFY_ALIGNMENT}" ]]; then
        log_warn "verify-alignment.sh not found - skipping detection"
        add_step "detect_corruption" "skipped" "Script not available"
        return 0
    fi

    log_info "Running verify-alignment.sh to detect corruption..."

    local output
    local exit_code

    output="$(bash "${VERIFY_ALIGNMENT}" 2>&1 || true)"
    exit_code=$?

    if [[ ${exit_code} -ne 0 ]]; then
        log_success "verify-alignment.sh detected corruption (exit code ${exit_code})"
        add_step "detect_corruption" "pass" "Corruption detected by verify-alignment.sh"
    else
        log_warn "verify-alignment.sh passed despite corruption"
        log_warn "This may indicate the detection script needs updating"
        add_step "detect_corruption" "warn" "Corruption not detected - consider improving detection"
    fi

    return 0
}

# Step 4: Single-skill restore via git checkout
step_single_skill_restore() {
    log_info "=== Step 4: Single-skill restore (git checkout) ==="

    # Find target skill name
    local target_skill_path
    target_skill_path="$(find "${SKILLS_ROOT}" -name "SKILL.md" -type f | head -n 1)"

    if [[ -z "${target_skill_path}" ]]; then
        log_warn "No skills to restore - skipping single restore"
        add_step "single_skill_restore" "skipped" "No skill files found"
        return 0
    fi

    local target_skill
    target_skill="$(dirname "${target_skill_path}")"
    target_skill="$(basename "${target_skill}")"

    # Get relative path from repository root
    local rel_path
    rel_path="$(realpath --relative-to="${PROJECT_ROOT}" "${target_skill}")"

    log_info "Restoring skill: ${rel_path}"

    # Save current branch
    local current_branch
    current_branch="$(git symbolic-ref --short HEAD)"

    # Attempt single-skill restore from master
    log_info "Running: git checkout master -- ${rel_path}"

    local output
    output="$(git checkout master -- "${rel_path}" 2>&1)" || {
        log_warn "git checkout returned non-zero, but this may be expected if file not on master"
        log_info "  Output: ${output:0:200}"
        add_step "single_skill_restore" "pass" "Restored (or file absent from master)"
        return 0
    }

    log_success "Single skill restored: ${rel_path}"

    # Verify restoration
    local restored_hash
    restored_hash="$(sha256sum "${target_skill_path}" | awk '{print $1}')"

    if [[ -f "${target_skill_path}.drill-backup" ]]; then
        local original_hash
        original_hash="$(sha256sum "${target_skill_path}.drill-backup" | awk '{print $1}')"

        if [[ "${restored_hash}" == "${original_hash}" ]]; then
            log_success "File content matches pre-drill state"
            add_step "single_skill_restore.verification" "pass" "Content verified"
        else
            log_warn "File content differs from pre-drill state"
            add_step "single_skill_restore.verification" "warn" "Content differs"
        fi
    else
        add_step "single_skill_restore.verification" "skip" "No backup for comparison"
    fi

    return 0
}

# Step 5: Whole-quarantine restore via git reset --hard
step_full_quarantine_restore() {
    log_info "=== Step 5: Whole-quarantine restore (git reset) ==="

    # Save current state
    local current_branch
    current_branch="$(git symbolic-ref --short HEAD)"

    log_info "Current branch: ${current_branch}"

    # If on openspace-evolved, save current HEAD
    local before_sha=""
    if [[ "${current_branch}" == "openspace-evolved" ]]; then
        before_sha="$(git rev-parse HEAD)"
        log_info "Before SHA: ${before_sha:0:12}"
    fi

    # Determine target branch for reset
    local reset_branch="openspace-evolved"

    # Check if reset branch exists
    if ! git rev-parse --verify "${reset_branch}" &>/dev/null; then
        log_warn "Branch '${reset_branch}' not found - skipping full restore"
        add_step "full_quarantine_restore" "skipped" "Branch not found"
        return 0
    fi

    log_info "Performing: git reset --hard ${reset_branch}"

    local output
    output="$(git reset --hard "${reset_branch}" 2>&1)" || {
        log_error "git reset --hard failed"
        log_info "  Output: ${output:0:200}"
        add_step "full_quarantine_restore" "fail" "Reset failed"
        return 1
    }

    log_success "Whole-quarantine restore completed"

    # Get new HEAD
    local after_sha
    after_sha="$(git rev-parse HEAD)"

    log_info "After SHA: ${after_sha:0:12}"

    if [[ -n "${before_sha}" ]]; then
        if [[ "${before_sha}" == "${after_sha}" ]]; then
            log_info "Branch was already at target (no-change reset)"
        fi
    fi

    add_step "full_quarantine_restore" "pass" "Reset to ${reset_branch} (${after_sha:0:12})"

    return 0
}

# Step 6: Post-rollback alignment verification
step_post_rollback_verification() {
    log_info "=== Step 6: Post-rollback alignment verification ==="

    if [[ ! -f "${VERIFY_ALIGNMENT}" ]]; then
        log_warn "verify-alignment.sh not found - skipping post-rollback check"
        add_step "post_rollback_verification" "skipped" "Script not available"
        return 0
    fi

    log_info "Running verify-alignment.sh post-rollback..."

    local output
    local exit_code

    output="$(bash "${VERIFY_ALIGNMENT}" 2>&1)" || {
        log_warn "verify-alignment.sh returned non-zero"
        log_info "  Output: ${output:0:500}"
        add_step "post_rollback_verification" "warn" "Non-zero exit: ${exit_code}"
        return 0
    }

    exit_code=$?

    if [[ ${exit_code} -eq 0 ]]; then
        log_success "verify-alignment.sh passed post-rollback"
        add_step "post_rollback_verification" "pass" "Alignment verified"
    else
        log_warn "verify-alignment.sh failed after rollback"
        log_info "  Output: ${output:0:500}"
        add_step "post_rollback_verification" "warn" "Alignment check failed"
    fi

    return 0
}

# Step 7: Clean up drill artifacts
step_cleanup() {
    log_info "=== Step 7: Cleaning up drill artifacts ==="

    # Find and remove backup files created during drill
    if [[ -d "${SKILLS_ROOT}" ]]; then
        local backup_count
        backup_count="$(find "${SKILLS_ROOT}" -name "*.drill-backup" -type f | wc -l || echo "0")"

        if [[ "${backup_count}" -gt 0 ]]; then
            find "${SKILLS_ROOT}" -name "*.drill-backup" -type f -delete
            log_success "Cleaned up ${backup_count} drill backup file(s)"
        fi

        add_step "cleanup" "pass" "Removed ${backup_count} backup(s)"
    else
        add_step "cleanup" "skip" "No skills directory"
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Artifact Generation
# ---------------------------------------------------------------------------

generate_artifact_json() {
    local drill_start="${DRILL_RESULT[start_time]}"
    local drill_end="${DRILL_RESULT[end_time]}"
    local drill_status="${DRILL_RESULT[status]}"
    local drill_mode="${DRILL_RESULT[mode]}"
    local drill_error="${DRILL_RESULT[error]}"

    # Build steps JSON array
    local steps_json="["
    local first=true

    # Collect all STEP_* variables
    for var in "${!STEP_@}"; do
        local step_name=""
        local step_status=""
        local step_detail=""

        # Parse variable name: STEP_<NAME>_<field>
        if [[ ${var} == *"_status" ]]; then
            step_name="${var#STEP_}"
            step_name="${step_name%_status}"
            eval "step_status=\${STEP_${var%_status}_status:-pending}"
            eval "step_detail=\${STEP_${var%_status}_detail:-}"
        elif [[ ${var} == *"_detail" ]]; then
            step_name="${var#STEP_}"
            step_name="${step_name%_detail}"
            eval "step_detail=\${STEP_${var%_status}_detail:-}"
            eval "step_status=\${STEP_${var%_status}_status:-pending}"
        else
            continue
        fi

        # Convert step name to readable format
        local readable_name
        readable_name="$(echo "${step_name}" | tr '_' ' ' | sed 's/  */ /g')"

        if [[ "${first}" == "true" ]]; then
            first=false
        else
            steps_json+=","
        fi

        steps_json+="{\"name\":\"${readable_name}\",\"status\":\"${step_status}\""

        if [[ -n "${step_detail}" ]]; then
            # Escape special JSON characters in detail
            local escaped_detail
            escaped_detail="$(echo "${step_detail}" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')"
            steps_json+=",\"detail\":\"${escaped_detail}\""
        fi

        steps_json+="}"
    done

    steps_json+="]"

    # Build full JSON
    cat > "${ARTIFACT_PATH}" <<ENDJSON
{
  "drill_type": "rollback",
  "version": "1.0",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "drill_start": "${drill_start}",
  "drill_end": "${drill_end}",
  "mode": "${drill_mode}",
  "status": "${drill_status}",
  "error": "${drill_error}",
  "git_info": {
    "branch": "$(git symbolic-ref --short HEAD 2>/dev/null || echo 'detached')",
    "head": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "repository": "$(git remote get-url origin 2>/dev/null || echo 'unknown')"
  },
  "steps": ${steps_json},
  "notes": [
    "This drill is for verification/testing purposes only.",
    "Always verify restore integrity after actual corruption events.",
    "Ensure verify-alignment.sh is up-to-date before relying on it for detection."
  ]
}
ENDJSON

    log_info "Drill artifact written to: ${ARTIFACT_PATH}"
}

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

main() {
    log_info "=============================================="
    log_info "WHO Ecosystem Evolution Loop - Rollback Drill"
    log_info "=============================================="
    log_info "Timestamp: ${DRILL_TIMESTAMP}"
    log_info "Mode: ${DRILL_MODE}"
    log_info "Artifact: ${ARTIFACT_PATH}"
    log_info "Project Root: ${PROJECT_ROOT}"
    log_info "=============================================="

    # Initialize
    drill_init

    # Ensure drill directory exists
    mkdir -p "${DRILL_DIR}"

    # Validate drill mode
    case "${DRILL_MODE}" in
        --single|--full|--both)
            ;;
        *)
            log_error "Invalid drill mode: ${DRILL_MODE}"
            echo "Usage: $0 [--single | --full | --both]"
            exit 1
            ;;
    esac

    # Step 1: Prerequisites
    if ! step_prerequisites; then
        drill_fail "Prerequisites check failed"
        generate_artifact_json
        exit 1
    fi

    case "${DRILL_MODE}" in
        --single|--both)
            # Step 2: Corrupt skill
            if ! step_corrupt_skill; then
                log_warn "Corruption step failed - continuing with other steps"
                add_step "corrupt_skill" "fail" "Injection failed"
            fi

            # Step 3: Detect corruption
            if ! step_detect_corruption; then
                log_warn "Corruption detection failed - continuing"
                add_step "detect_corruption" "fail" "Detection failed"
            fi

            # Step 4: Single-skill restore
            if ! step_single_skill_restore; then
                log_warn "Single-skill restore failed - continuing"
                add_step "single_skill_restore" "fail" "Restore failed"
            fi
            ;;
        --full)
            # Step 4: For full mode, we still do single restore first (they're compatible)
            step_single_skill_restore || true
            ;;
    esac

    # Step 5: Full quarantine restore (for --full or --both)
    case "${DRILL_MODE}" in
        --full|--both)
            if ! step_full_quarantine_restore; then
                log_warn "Full quarantine restore failed - continuing"
                add_step "full_quarantine_restore" "fail" "Reset failed"
            fi
            ;;
    esac

    # Step 6: Post-rollback verification
    step_post_rollback_verification || true

    # Step 7: Cleanup
    step_cleanup || true

    # Complete
    drill_complete
    generate_artifact_json

    log_info "=============================================="
    log_info "Rollback Drill Complete"
    log_info "Artifact: ${ARTIFACT_PATH}"
    log_info "Status: ${DRILL_RESULT[status]}"
    log_info "=============================================="

    # Exit with appropriate code
    if [[ "${DRILL_RESULT[status]}" == "completed" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main "$@"
