#!/usr/bin/env bash
# install-agy-hooks.sh — set up the agy-native PostToolUse hook for Hook 9 (build_loop).
#
# CONTEXT: Most NTAPP hooks for slice-loop/ad-hoc-per-unit are enforced by the DRIVER at
# node boundaries (scripts/antigravity/hooks/run-hooks.cjs) — that needs no agy config and
# is already on. The git pre-commit hook is the hard Rules-1-9 backstop. So Hook 9 is ALREADY
# enforced two ways without this.
#
# This installer adds the OPTIONAL third layer: realtime per-EDIT feedback inside an agy
# session, so the agent self-corrects a bad header/token mid-turn instead of at node end.
# agy fires PostToolUse with the tool event as JSON on stdin; agy-posttool-shim.cjs reshapes
# it for build_loop.sh.
#
# agy 1.0.14 has NO CLI to register hooks (no `agy hooks` subcommand) — they are created via
# the interactive `/hooks` form. So this script chmods the shim, writes a reference JSON of
# the derived schema, and prints the exact values to type into that form.
set -eo pipefail

HERE="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHIM="$HERE/agy-posttool-shim.cjs"
chmod +x "$SHIM" 2>/dev/null || true

REF="$HERE/agy-hooks.reference.json"
cat > "$REF" <<JSON
{
  "_comment": "Reference schema derived from agy 1.0.14 protobuf (exa.hooks_pb). Field names: postToolHooks[].{name,command,args,event,matcher,timeout_millis}. agy 1.0.14 stores hooks via the interactive /hooks form, not this file — keep this as the source of truth for if/when agy adds JSON import.",
  "postToolHooks": [
    {
      "name": "ntapp-build-loop",
      "event": "PostToolUse",
      "matcher": "write_to_file|replace_file_content",
      "command": "node",
      "args": ["$SHIM"],
      "timeout_millis": 30000
    }
  ]
}
JSON

echo "✓ shim executable: $SHIM"
echo "✓ reference schema written: $REF"
echo
echo "To enable realtime per-edit Hook 9 inside agy, open the agy TUI and run /hooks, then:"
echo "  ┌────────────────────────────────────────────────────────────────"
echo "  │ event   : PostToolUse"
echo "  │ matcher : write_to_file|replace_file_content"
echo "  │ command : node"
echo "  │ args    : $SHIM"
echo "  │ timeout : 30000   (ms)"
echo "  └────────────────────────────────────────────────────────────────"
echo
echo "NOTE: Hook 9 is ALREADY enforced without this — the driver runs build_loop as a"
echo "post-node sweep over changed files, and git pre-commit enforces Rules 1-9 at commit."
echo "This only adds the in-session 'fail fast' realtime layer."
