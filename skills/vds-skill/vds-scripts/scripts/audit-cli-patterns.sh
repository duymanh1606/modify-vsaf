#!/usr/bin/env bash
# audit-cli-patterns.sh — Phase 3 adoption audit (FR-22, FR-23)
# Scans orchestrator cli.py files for ExitCodes/ErrorHandler and make_vds_app() adoption

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "========================================"
echo "  CLI Pattern Adoption Audit"
echo "========================================"
echo ""

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Tier-1 orchestrators (highest priority)
TIER1="audit memory research bitbucket confluence jira git"

# Collect findings
echo "Scanning orchestrator cli.py files..."
echo ""

find . \
    -path './.venv' -prune -o \
    -path './__pycache__' -prune -o \
    -path './node_modules' -prune -o \
    -name 'cli.py' -print | sort > "$TMPDIR/cli_files.txt"

# Header
cat > "$TMPDIR/report.md" << 'EOF'
# CLI Pattern Adoption Audit Report

| Orchestrator | Tier | sys.exit | bare RuntimeError | make_vds_app | ExitCodes | ErrorHandler | Pattern |
| --- | --- | --- | --- | --- | --- | --- | --- |
EOF

TOTAL_EXIT=0
TOTAL_ERROR=0
TOTAL_FACTORY=0
TOTAL_EXITCODES=0
TOTAL_HANDLER=0

while read -r cli_file; do
    # Extract orchestrator name from path
    orch=$(echo "$cli_file" | sed -E 's|\./([^/]+)/.*|\1|')
    # Skip non-orchestrator cli.py files
    if [[ ! "$orch" =~ _orchestrator$ ]]; then
        continue
    fi
    
    # Tier classification
    tier="other"
    orch_short=${orch%_orchestrator}
    if echo "$TIER1" | grep -qw "$orch_short"; then
        tier="1"
    fi
    
    has_exit="no"
    has_error="no"
    has_factory="no"
    has_exitcodes="no"
    has_handler="no"
    
    if grep -qE '\bsys\.exit\b' "$cli_file"; then
        has_exit="yes"
        ((TOTAL_EXIT++)) || true
    fi
    
    if grep -qE '\braise RuntimeError\b' "$cli_file"; then
        has_error="yes"
        ((TOTAL_ERROR++)) || true
    fi
    
    if grep -q 'make_vds_app' "$cli_file"; then
        has_factory="yes"
        ((TOTAL_FACTORY++)) || true
    fi
    
    if grep -q 'ExitCodes' "$cli_file"; then
        has_exitcodes="yes"
        ((TOTAL_EXITCODES++)) || true
    fi
    
    if grep -q 'ErrorHandler' "$cli_file"; then
        has_handler="yes"
        ((TOTAL_HANDLER++)) || true
    fi
    
    # Pattern classification
    pattern="unknown"
    if [ "$has_factory" = "yes" ]; then
        pattern="make_vds_app"
    elif [ "$has_exit" = "no" ] && [ "$has_error" = "no" ] && grep -q 'typer\.Typer' "$cli_file"; then
        pattern="typer_direct"
    else
        pattern="needs_review"
    fi
    
    echo "| $orch | $tier | $has_exit | $has_error | $has_factory | $has_exitcodes | $has_handler | $pattern |" >> "$TMPDIR/report.md"
done < "$TMPDIR/cli_files.txt"

echo ""
echo "=== Adoption Summary ==="
echo ""
echo "| Metric | Count |"
echo "| --- | --- |"
echo "| Total orchestrators scanned | $(grep -c 'yes\|no' \"$TMPDIR/report.md\") |"
echo "| Using sys.exit (needs migration) | $TOTAL_EXIT |"
echo "| Using bare RuntimeError (needs migration) | $TOTAL_ERROR |"
echo "| Using make_vds_app (target pattern) | $TOTAL_FACTORY |"
echo "| Using ExitCodes (shared lib) | $TOTAL_EXITCODES |"
echo "| Using ErrorHandler (shared lib) | $TOTAL_HANDLER |"
echo ""

cat "$TMPDIR/report.md"

echo ""
echo "=== Recommendations ==="
echo ""
if [ "$TOTAL_EXIT" -gt 0 ] || [ "$TOTAL_ERROR" -gt 0 ]; then
    echo "⚠️  Found orchestrators using sys.exit() or bare RuntimeError."
    echo "   Recommended: Migrate to ExitCodes + ErrorHandler from vds_cli_common."
    echo ""
fi

if [ "$TOTAL_FACTORY" -eq 0 ]; then
    echo "ℹ️  No orchestrator uses make_vds_app() yet."
    echo "   This is expected for existing CLIs — use it for NEW orchestrators only."
    echo ""
fi

echo "=== Tier-1 Priority List ==="
grep "| 1 |" "$TMPDIR/report.md" || echo "(none found)"
