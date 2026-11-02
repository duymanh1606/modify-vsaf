#!/bin/bash
# vds-skill-create-bitbucket-pr: create Bitbucket PR via vds-cli
# Usage: create-pr.sh [--dry-run] [--target BRANCH] [--description-file FILE] [--title TITLE]
# Auto-extracts project/repo from `git remote get-url origin`.

# NOTE: No `set -e` — we want full control of the exit-code path.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../../_shared/vds-skill/credentials.sh"

require_command git
# Note: require_command vds-cli moved AFTER dry-run check.

DRY_RUN=false
TARGET_BRANCH="master"
DESC_FILE=""
TITLE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --target) TARGET_BRANCH="$2"; shift 2 ;;
        --description-file) DESC_FILE="$2"; shift 2 ;;
        --title) TITLE="$2"; shift 2 ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

REMOTE_URL=$(git remote get-url origin 2>/dev/null || true)
if [[ -z "$REMOTE_URL" ]]; then
    echo "ERROR: No git remote 'origin' configured" >&2
    exit 1
fi

if [[ ! "$REMOTE_URL" =~ bitbucket\.digital\.vn ]]; then
    echo "WARNING: Remote URL does not match bitbucket.digital.vn pattern:" >&2
    echo "  $REMOTE_URL" >&2
    echo "  This skill is for Viettel Bitbucket. For GitHub, use 'gh pr create'." >&2
    exit 1
fi

# Extract PROJECT/REPO from URL
# Handles:
#   ssh://git@bitbucket.digital.vn/PROJECT/repo.git
#   ssh://git@bitbucket.digital.vn:7999/PROJECT/repo.git
#   https://bitbucket.digital.vn/scm/PROJECT/repo.git
if [[ "$REMOTE_URL" =~ /scm/([^/]+)/([^/]+)\.git$ ]]; then
    PROJECT="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]}"
elif [[ "$REMOTE_URL" =~ /([^/]+)/([^/]+)\.git$ ]]; then
    PROJECT="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]}"
else
    echo "ERROR: Cannot parse PROJECT/REPO from remote URL: $REMOTE_URL" >&2
    exit 1
fi

SOURCE_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ -z "$SOURCE_BRANCH" ]] || [[ "$SOURCE_BRANCH" == "HEAD" ]]; then
    echo "ERROR: Not on a named branch" >&2
    exit 1
fi

if [[ -z "$TITLE" ]]; then
    TITLE=$(git log -1 --pretty=%s)
fi

if [[ -z "$DESC_FILE" ]]; then
    DESC_FILE=$(find .vsaf/docs/features -name '09-ship.md' 2>/dev/null | head -1)
    [[ -z "$DESC_FILE" ]] && DESC_FILE=$(find .vsaf/docs/hotfixes -name '03-ship.md' 2>/dev/null | head -1)
fi

CMD=(vds-cli bitbucket pr create "$PROJECT/$REPO"
     --source "$SOURCE_BRANCH"
     --target "$TARGET_BRANCH"
     --title "$TITLE")
[[ -n "$DESC_FILE" ]] && [[ -f "$DESC_FILE" ]] && CMD+=(--description-file "$DESC_FILE")

if [[ "$DRY_RUN" == "true" ]]; then
    echo "DRY-RUN — would execute:"
    printf '  %q' "${CMD[@]}"
    echo ""
    echo "  + --yes --json-only"
    exit 0
fi

require_command vds-cli

ensure_env VDS_BITBUCKET_TOKEN "Enter VDS Bitbucket personal access token"

echo "About to create PR:"
echo "  Project/Repo: $PROJECT/$REPO"
echo "  Source:       $SOURCE_BRANCH"
echo "  Target:       $TARGET_BRANCH"
echo "  Title:        $TITLE"
echo "  Description:  ${DESC_FILE:-<empty>}"
echo ""
read -rp "Proceed? [y/N]: " confirm
if [[ "$confirm" != "y" ]] && [[ "$confirm" != "Y" ]]; then
    echo "Aborted"
    exit 1
fi

"${CMD[@]}" --yes --json-only
