#!/bin/bash
# vds-skill-pull: git pull + detect stale local knowledge index
# Exit codes: forwards `git pull` exit code (0 on success even if knowledge stale)

# Run git pull, forwarding all args. Capture exit code for explicit forwarding.
# (No `set -e` — we want full control of the exit-code path for the advisory stale check.)
git pull "$@"
EXIT=$?

if [[ $EXIT -ne 0 ]]; then
    exit $EXIT
fi

# Skip stale check if not a fetch-based pull (e.g., --no-rebase --quiet might skip FETCH_HEAD)
if [[ ! -f .git/FETCH_HEAD ]]; then
    exit 0
fi

FETCH_HEAD_MTIME=$(stat -c %Y .git/FETCH_HEAD 2>/dev/null || stat -f %m .git/FETCH_HEAD 2>/dev/null || echo 0)
STALE_REASONS=()

# Check .gitnexus/
if [[ -d .gitnexus ]]; then
    GITNEXUS_MTIME=$(stat -c %Y .gitnexus 2>/dev/null || stat -f %m .gitnexus 2>/dev/null || echo 0)
    if [[ $GITNEXUS_MTIME -lt $FETCH_HEAD_MTIME ]]; then
        STALE_REASONS+=(".gitnexus/ index older than fetched commits")
    fi
fi
# Note: .gitnexus missing is OK (project may not use GitNexus)

# Check graphify-out/graph.json
if [[ -f graphify-out/graph.json ]]; then
    GRAPH_MTIME=$(stat -c %Y graphify-out/graph.json 2>/dev/null || stat -f %m graphify-out/graph.json 2>/dev/null || echo 0)
    if [[ $GRAPH_MTIME -lt $FETCH_HEAD_MTIME ]]; then
        STALE_REASONS+=("graphify-out/graph.json older than fetched commits")
    fi
fi
# Note: graphify-out missing is OK

# Print suggestion if anything stale
if [[ ${#STALE_REASONS[@]} -gt 0 ]]; then
    echo ""
    echo "⚠️  Knowledge index có thể stale sau pull:"
    for reason in "${STALE_REASONS[@]}"; do
        echo "   - $reason"
    done
    echo ""
    echo "   Khuyến nghị: chạy /sdlc-onboard-code để rebuild GitNexus + Graphify locally."
    echo ""
fi

exit 0
