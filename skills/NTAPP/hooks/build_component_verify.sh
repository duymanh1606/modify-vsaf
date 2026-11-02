#!/usr/bin/env bash
# Hook 6 — build-component-verify
# Event: SubagentStop after /ntapp-ds-build-component.
# Check: build_report.md exists + master_token.json schema valid.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable
stop_reentry_guard "build-component-verify"

SPEC="$(get_spec_repo_root)"

# Multi-DS aware (_shared/ds-resolution.md nhánh D): tìm report qua mọi DS root;
# master_token/components_metadata verify theo DS root CHỨA report (derive từ path),
# không assume 1 root cố định.
# Driver (Antigravity host) may pin the exact unit via HOOK_TARGET_ID — deterministic.
# Else newest build_report.md (last 5 min) — Claude SubagentStop path. ds-build is mc:1
# (sequential) so the heuristic is race-free, but targeting makes it exact either way.
REPORT=""
if [[ -n "${HOOK_TARGET_ID:-}" ]]; then
  tdir="$(find_unit_delta_dir "$HOOK_TARGET_ID")" \
    && [[ -f "$tdir/build_report.md" ]] \
    && REPORT="$tdir/build_report.md"
fi
if [[ -z "$REPORT" ]]; then
  while IFS= read -r dsr; do
    [[ -d "$dsr/feature_deltas" ]] || continue
    REPORT=$(find "$dsr/feature_deltas" -maxdepth 3 -name 'build_report.md' -mmin -5 2>/dev/null | head -1)
    [[ -n "$REPORT" ]] && break
  done < <(ds_roots)
fi
[[ -n "$REPORT" ]] || ok  # nothing newly built → not our event

DS_ROOT="$(ds_root_of_delta_path "$REPORT")" || DS_ROOT="$(get_design_system_root)"
MASTER_TOKEN="$DS_ROOT/master_token.json"
COMP_META="$DS_ROOT/components_metadata.json"

ID=$(dirname "$REPORT" | xargs basename)
problems=()

# 1) build_report has required header lines
grep -qE '^# Build Report|^## Build Report' "$REPORT" \
  || problems+=( "build_report.md missing header" )

# 2) build_report references proposal
PROPOSAL="$(dirname "$REPORT")/proposed_ds_updates.md"
[[ -f "$PROPOSAL" ]] || problems+=( "proposed_ds_updates.md missing in same dir" )

# 2b) proposal checksum khớp — chống build_report stale (report cũ pass gate trong khi
# proposal đã sửa). Format canonical (ds-build step-05): `**Proposal checksum:** sha256:{hash}`;
# nhận thêm biến thể `proposal_sha256: {hash}`. Report không có checksum → skip (compat).
declared_sha=$(grep -iE 'proposal[ _]?checksum|proposal_sha256' "$REPORT" 2>/dev/null | head -1 \
  | grep -oE '[0-9a-fA-F]{64}' | head -1 | tr '[:upper:]' '[:lower:]')
if [[ -n "$declared_sha" && -f "$PROPOSAL" ]]; then
  actual_sha=$( (shasum -a 256 "$PROPOSAL" 2>/dev/null || sha256sum "$PROPOSAL" 2>/dev/null) \
    | awk '{print $1}' | tr '[:upper:]' '[:lower:]')
  [[ -z "$actual_sha" || "$declared_sha" == "$actual_sha" ]] \
    || problems+=( "proposal checksum mismatch — build_report stale so với proposed_ds_updates.md hiện tại (re-run /ntapp-ds-build-component $ID)" )
fi

# 3) master_token.json valid JSON with required keys
if [[ -f "$MASTER_TOKEN" ]]; then
  if ! python3 -c "
import json, sys
d = json.load(open('$MASTER_TOKEN'))
required = {'tokens', 'version'}
missing = required - set(d.keys())
if missing: sys.exit('missing keys: ' + ','.join(missing))
" 2>/tmp/.hook_mt_err; then
    problems+=( "master_token.json invalid: $(cat /tmp/.hook_mt_err)" )
  fi
else
  problems+=( "master_token.json missing" )
fi

# 4) components_metadata.json valid JSON
if [[ -f "$COMP_META" ]]; then
  python3 -c "import json; json.load(open('$COMP_META'))" 2>/dev/null \
    || problems+=( "components_metadata.json invalid JSON" )
else
  problems+=( "components_metadata.json missing" )
fi

if [[ ${#problems[@]} -gt 0 ]]; then
  log_event "build-component-verify" "BLOCK" "$ID: ${problems[*]}"
  "$HOOK_DIR/notify.sh" error false \
    "DS build verify failed — $ID" \
    "Problems:
$(printf '  - %s\n' "${problems[@]}")
Re-run /ntapp-ds-build-component sau khi fix." \
    --mention "@DSO"
  block "DS build verify failed for $ID:
$(printf '  - %s\n' "${problems[@]}")"
fi

log_event "build-component-verify" "PASS" "$ID"
ok
