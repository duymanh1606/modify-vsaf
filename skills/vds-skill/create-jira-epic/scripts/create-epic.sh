#!/bin/bash
# vds-skill-create-jira-epic: create a Jira Epic via vds-cli
# Usage: create-epic.sh [--dry-run] [--project KEY] [--description-file FILE] [--feature NAME]

# NOTE: No `set -e` — we want full control of the exit-code path.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../../_shared/vds-skill/credentials.sh"

require_command python3
# Note: require_command vds-cli moved AFTER dry-run check so --dry-run
#       works without vds-cli installed (preview mode).

DRY_RUN=false
PROJECT_KEY=""
DESC_FILE=""
FEATURE_NAME=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --project) PROJECT_KEY="$2"; shift 2 ;;
        --description-file) DESC_FILE="$2"; shift 2 ;;
        --feature) FEATURE_NAME="$2"; shift 2 ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

# Determine PRD file path
if [[ -z "$DESC_FILE" ]]; then
    if [[ -n "$FEATURE_NAME" ]]; then
        for path in ".vsaf/docs/features/$FEATURE_NAME/02-prd.md"; do
            [[ -f "$path" ]] && DESC_FILE="$path" && break
        done
    fi

    # Fallback: most recent 02-prd.md
    if [[ -z "$DESC_FILE" ]]; then
        DESC_FILE=$(find .vsaf/docs/features -name '02-prd.md' 2>/dev/null \
                    | xargs -I{} ls -t {} 2>/dev/null | head -1)
    fi
fi

if [[ -z "$DESC_FILE" ]] || [[ ! -f "$DESC_FILE" ]]; then
    echo "ERROR: PRD file not found. Run /sdlc-prd first or specify --description-file" >&2
    exit 1
fi

# Derive feature name from PRD path if not given
if [[ -z "$FEATURE_NAME" ]]; then
    FEATURE_NAME=$(basename "$(dirname "$DESC_FILE")")
fi

# Extract summary from PRD (first H1)
SUMMARY=$(grep -m1 '^# ' "$DESC_FILE" | sed 's/^# //' || true)
[[ -z "$SUMMARY" ]] && SUMMARY="$FEATURE_NAME"

if [[ "$DRY_RUN" == "true" ]]; then
    DISPLAY_PROJECT="${PROJECT_KEY:-${VDS_JIRA_PROJECT_DEFAULT:-<VDS_JIRA_PROJECT_DEFAULT>}}"
    CMD_DRY=(vds-cli jira create
         --project "$DISPLAY_PROJECT"
         --issuetype Epic
         --summary "$SUMMARY"
         --description-file "$DESC_FILE")
    echo "DRY-RUN — would execute:"
    printf '  %q' "${CMD_DRY[@]}"
    echo ""
    echo "  + --yes --json-only"
    exit 0
fi

require_command vds-cli

# Ensure credentials
ensure_env VDS_JIRA_TOKEN "Enter VDS Jira personal access token"
ensure_env VDS_JIRA_PROJECT_DEFAULT "Enter default Jira project key (e.g. NTTC)" false

PROJECT_KEY="${PROJECT_KEY:-$VDS_JIRA_PROJECT_DEFAULT}"

CMD=(vds-cli jira create
     --project "$PROJECT_KEY"
     --issuetype Epic
     --summary "$SUMMARY"
     --description-file "$DESC_FILE")

echo "About to create Jira Epic:"
echo "  Project:      $PROJECT_KEY"
echo "  Summary:      $SUMMARY"
echo "  Description:  $DESC_FILE"
echo "  Feature:      $FEATURE_NAME"
echo ""
read -rp "Proceed? [y/N]: " confirm
if [[ "$confirm" != "y" ]] && [[ "$confirm" != "Y" ]]; then
    echo "Aborted"
    exit 1
fi

RESULT=$("${CMD[@]}" --yes --json-only)
EPIC_KEY=$(echo "$RESULT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("key",""))')

if [[ -z "$EPIC_KEY" ]]; then
    echo "ERROR: Failed to extract epic key from vds-cli response" >&2
    echo "Response: $RESULT" >&2
    exit 1
fi

EPIC_KEY_FILE="$(dirname "$DESC_FILE")/jira-epic-key.txt"
echo "$EPIC_KEY" > "$EPIC_KEY_FILE"

echo ""
echo "✓ Created Jira Epic: $EPIC_KEY"
echo "  Saved key to: $EPIC_KEY_FILE"
