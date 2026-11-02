#!/usr/bin/env bash
# NTAPP hooks — test harness (pre-rollout checklist, hooks/README.md §Test fixtures).
# Mỗi hook block có ≥1 ca PASS (exit 0) + ≥1 ca FAIL/BLOCK (exit 2).
# Thêm 1 ca engine: loop cạn max_retries phải DỪNG (không treo) — invariant chống infinite-loop.
#
# Chạy:  bash hooks/tests/run.sh
# Exit:  0 nếu tất cả pass, 1 nếu có ca fail.

set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$HOOKS/.." && pwd)"
PASS=0; FAIL=0
TMPDIRS=()
cleanup() { for d in "${TMPDIRS[@]:-}"; do [[ -n "$d" ]] && rm -rf "$d"; done; }
trap cleanup EXIT

new_repo() { local d; d="$(mktemp -d)"; git -C "$d" init -q; TMPDIRS+=("$d"); echo "$d"; }

# expect <desc> <want_exit> <got_exit>
expect() {
  if [[ "$3" == "$2" ]]; then
    printf '  \033[0;32mok  \033[0m %s (exit %s)\n' "$1" "$3"; PASS=$((PASS+1))
  else
    printf '  \033[0;31mFAIL\033[0m %s (want %s, got %s)\n' "$1" "$2" "$3"; FAIL=$((FAIL+1))
  fi
}

mk_wbs() { mkdir -p "$1/NTAPP-output/Stage_2_Architecture"
  printf '| ID | Type | Module |\n|----|------|--------|\n| MPF-01 | feature | core |\n' \
    > "$1/NTAPP-output/Stage_2_Architecture/project_wbs.md"; }

echo "── build_loop ──────────────────────────────────────────────"
R="$(new_repo)"; mk_wbs "$R"
printf '// id: MPF-99 | dd_version: v1\nx\n' > "$R/foo.ts"
P="{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$R/foo.ts\"}}"
echo "$P" | ( cd "$R" && "$HOOKS/build_loop.sh" ) >/dev/null 2>&1; expect "single-repo, ID không trong WBS → BLOCK" 2 $?

R="$(new_repo)"; mkdir -p "$R/code" "$R/spec"; git -C "$R/code" init -q
printf 'spec_repo_root: ../spec\n' > "$R/code/.bmm-config.yaml"; mk_wbs "$R/spec"
printf '// id: MPF-99 | dd_version: v1\nx\n' > "$R/code/foo.ts"
P="{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$R/code/foo.ts\"}}"
echo "$P" | ( cd "$R/code" && "$HOOKS/build_loop.sh" ) >/dev/null 2>&1; expect "dual-repo, ID không trong WBS → NOTICE (pass)" 0 $?

R="$(new_repo)"
printf 'export const x=1\n' > "$R/no_header.ts"
P="{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$R/no_header.ts\"}}"
echo "$P" | ( cd "$R" && "$HOOKS/build_loop.sh" ) >/dev/null 2>&1; expect "thiếu header id: → BLOCK (Rule 1)" 2 $?

echo "── ds_delta_router (Hook 5, recorder) ──────────────────────"
R="$(new_repo)"; D="$R/NTAPP-output/design-system/feature_deltas/SCR-FOO"; mkdir -p "$D"
printf '[NEW]\n- color.brand #1A73E8\n[SUMMARY]\nok\n' > "$D/proposed_ds_updates.md"
echo '{}' | ( cd "$R" && "$HOOKS/ds_delta_router.sh" ) >/dev/null 2>&1; expect "NEW non-empty → warn_pass (không block Stop)" 0 $?
grep -q '^status: pending' "$D/ds_delta_decision.md" 2>/dev/null && expect "→ ghi record status: pending" 0 0 || expect "→ ghi record status: pending" 0 1

R="$(new_repo)"; D="$R/NTAPP-output/design-system/feature_deltas/SCR-BAR"; mkdir -p "$D"
printf '[NEW]\n- color.brand #1A73E8\n[SUMMARY]\nok\n' > "$D/proposed_ds_updates.md"
echo '{}' | ( cd "$R" && DS_DELTA_AUTO_APPROVE=1 "$HOOKS/ds_delta_router.sh" ) >/dev/null 2>&1
grep -q '^status: auto_approved' "$D/ds_delta_decision.md" 2>/dev/null && expect "auto-approve env → status: auto_approved" 0 0 || expect "auto-approve env → status: auto_approved" 0 1

echo "── ds_build_approval_gate (Hook 5b, gate) ──────────────────"
R="$(new_repo)"; D="$R/NTAPP-output/design-system/feature_deltas/SCR-FOO"; mkdir -p "$D"
printf -- '---\nid: SCR-FOO\nstatus: pending\n---\n' > "$D/ds_delta_decision.md"
echo '{"prompt":"/ntapp-ds-build-component SCR-FOO"}' | ( cd "$R" && "$HOOKS/ds_build_approval_gate.sh" ) >/dev/null 2>&1; expect "record pending → BLOCK ds-build" 2 $?
printf -- '---\nid: SCR-FOO\nstatus: approved\n---\n' > "$D/ds_delta_decision.md"
echo '{"prompt":"/ntapp-ds-build-component SCR-FOO"}' | ( cd "$R" && "$HOOKS/ds_build_approval_gate.sh" ) >/dev/null 2>&1; expect "record approved → PASS ds-build" 0 $?
echo '{"prompt":"/some-other-skill"}' | ( cd "$R" && "$HOOKS/ds_build_approval_gate.sh" ) >/dev/null 2>&1; expect "prompt không liên quan → PASS" 0 $?

echo "── multi-DS (registry.yaml, namespaced roots) ──────────────"
R="$(new_repo)"; FAM="$R/NTAPP-output/design-system"
mkdir -p "$FAM/web-admin/feature_deltas/SCR-ADM-FOO" "$FAM/mobile-app/feature_deltas"
printf 'version: 1\nsystems:\n  web-admin:\n    root: "web-admin/"\n    code_repo: admin-fe\n    framework: react\n  mobile-app:\n    root: "mobile-app/"\n    code_repo: mobile\n    framework: react-native\n' > "$FAM/registry.yaml"
printf '[NEW]\n- color.brand #1A73E8\n[SUMMARY]\nok\n' > "$FAM/web-admin/feature_deltas/SCR-ADM-FOO/proposed_ds_updates.md"
echo '{}' | ( cd "$R" && "$HOOKS/ds_delta_router.sh" ) >/dev/null 2>&1; expect "hook 5: proposal trong DS namespaced → tìm thấy, warn_pass" 0 $?
grep -q '^status: pending' "$FAM/web-admin/feature_deltas/SCR-ADM-FOO/ds_delta_decision.md" 2>/dev/null \
  && expect "→ record pending ghi ĐÚNG DS root (web-admin/)" 0 0 \
  || expect "→ record pending ghi ĐÚNG DS root (web-admin/)" 0 1
echo '{"prompt":"/ntapp-ds-build-component SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/ds_build_approval_gate.sh" ) >/dev/null 2>&1; expect "hook 5b: pending trong DS namespaced → BLOCK" 2 $?
printf -- '---\nid: SCR-ADM-FOO\nstatus: approved\n---\n' > "$FAM/web-admin/feature_deltas/SCR-ADM-FOO/ds_delta_decision.md"
echo '{"prompt":"/ntapp-ds-build-component SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/ds_build_approval_gate.sh" ) >/dev/null 2>&1; expect "hook 5b: approved → PASS" 0 $?

# Hook 3: block khi KHÔNG DS nào bootstrap; pass khi ≥1 DS xong (DS kia thiếu → chỉ warn)
mk_wbs "$R"; printf 'x\n' > "$R/NTAPP-output/Stage_2_Architecture/architecture_design.md"
mkdir -p "$R/NTAPP-output/Stage_2_Architecture/slices"; printf 'x\n' > "$R/NTAPP-output/Stage_2_Architecture/slices/SLICE-01.md"
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "hook 3: 0/2 DS bootstrap → BLOCK" 2 $?
printf '{"tokens":{},"version":1}\n' > "$FAM/web-admin/master_token.json"
printf '{}\n' > "$FAM/web-admin/components_metadata.json"
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "hook 3: 1/2 DS bootstrap → PASS (DS thiếu chỉ warn)" 0 $?

echo "── figma drift gate (Hook 3, read-only 0 network) ──────────"
# Kế thừa $R multi-DS ở trên (web-admin đã bootstrap → hook 3 base PASS).
DD="$R/NTAPP-output/Stage_4_Design/detailed_design"; mkdir -p "$DD"
MFD="$FAM/web-admin/_reference/figma"; mkdir -p "$MFD"
mk_manifest() { # <checksum> <status>
  printf 'schema_version: "1.0"\nfile_key: AbC\nfigma_version: "9"\nunits:\n  - unit_id: SCR-ADM-FOO\n    figma_status: %s\n    checksum: "%s"\n' "$2" "$1" > "$MFD/figma-manifest.yaml"
}
# 1. DD chưa có → không có baseline → PASS
mk_manifest "sha256:aaaa1111" mapped
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "figma: DD chưa có → PASS" 0 $?
# 2. DD có figma_ref khớp checksum → PASS
printf -- '- **figma_ref:** `AbC` / node `1:2` / version `9` / checksum `sha256:aaaa1111`\n' > "$DD/SCR-ADM-FOO_detailed_design.md"
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "figma: checksum khớp → PASS" 0 $?
# 3. Designer sửa Figma → checksum lệch → BLOCK
mk_manifest "sha256:bbbb2222" mapped
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "figma: checksum lệch → BLOCK" 2 $?
# 4. Kill switch
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && DISABLE_FIGMA_DRIFT_GATE=1 "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "figma: DISABLE_FIGMA_DRIFT_GATE=1 → PASS" 0 $?
# 5. Unit missing (author mode) → lệch cũng KHÔNG block
mk_manifest "sha256:cccc3333" missing
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "figma: status=missing → PASS (author mode)" 0 $?
# 6. DD không có figma_ref nhưng manifest mapped → chỉ WARN
mk_manifest "sha256:dddd4444" mapped
printf -- '# DD không có figma_ref\n' > "$DD/SCR-ADM-FOO_detailed_design.md"
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "figma: DD author-mode + manifest mapped → PASS (warn)" 0 $?
# 7. Prefix collision: SCR-ADM-FOO-DETAIL không được ăn checksum của SCR-ADM-FOO
printf -- '- **figma_ref:** checksum `sha256:zzzz9999`\n' > "$DD/SCR-ADM-FOO-DETAIL_detailed_design.md"
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO-DETAIL"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "figma: unit khác prefix-lồng → PASS (không false BLOCK)" 0 $?
# 8. not_in_scope (ingest hẹp scope không phủ unit) + DD có figma_ref → WARN, KHÔNG block
mk_manifest "sha256:eeee5555" not_in_scope
printf -- '- **figma_ref:** checksum `sha256:eeee5555`\n' > "$DD/SCR-ADM-FOO_detailed_design.md"
echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) >/dev/null 2>&1; expect "figma: not_in_scope + có figma_ref → PASS (warn)" 0 $?
# 9. not_in_scope mà checksum LỆCH → vẫn PASS (chưa xét thì không kết luận drift)
printf -- '- **figma_ref:** checksum `sha256:ffff6666`\n' > "$DD/SCR-ADM-FOO_detailed_design.md"
out=$( echo '{"prompt":"/ntapp-feature-design SCR-ADM-FOO"}' | ( cd "$R" && "$HOOKS/stage3_input_gate.sh" ) 2>&1 ); rc=$?
expect "figma: not_in_scope + checksum lệch → PASS (không kết luận về unit chưa xét)" 0 $rc
printf '%s' "$out" | grep -q 'NOT-IN-SCOPE\|not_in_scope' && expect "figma: not_in_scope phát WARN đúng loại" 0 0 || expect "figma: not_in_scope phát WARN đúng loại" 0 1
rm -rf "$MFD"

echo "── figma TRANSCRIBE vision gate (Hook 4, read-only 0 network) ──"
R="$(new_repo)"; FAM4="$R/NTAPP-output/design-system"
MFD4="$FAM4/_reference/figma"; DD4="$R/NTAPP-output/Stage_4_Design/detailed_design"
mkdir -p "$MFD4" "$DD4"
mk_manifest4() { # <status> <n_frames_true>
  { printf 'schema_version: "1.1"\nunits:\n  - unit_id: SCR-ADM-FOO\n    figma_status: %s\n    states:\n' "$1"
    local i=0; while [[ $i -lt ${2:-1} ]]; do printf '      - state: "s%s"\n        frame_exported: true\n' "$i"; i=$((i+1)); done
  } > "$MFD4/figma-manifest.yaml"
}
# DD hợp lệ: 2 dòng bảng + quan sát thật
mk_dd4_good() { cat > "$DD4/SCR-ADM-FOO_detailed_design.md" <<'EOF'
# DD
## 2.2 Wireframe — Layout Groups
| Group ID | Type | Members | Props |
| R1 | Stack | a, b | direction=column, gap=md |
## 2.3 UI Controls
[input_x] [button_y]
## 2.5 Deviation log
**[FRAMES VIEWED]**
| State | Frame | Quan sát |
| :--- | :--- | :--- |
| default | `frames/SCR-ADM-FOO.png` | logo canh GIỮA, nút bo pill hết hai đầu |
| error | `frames/SCR-ADM-FOO__error.png` | thẻ không viền chỉ có bóng mềm |
## 3.2 Logic Matrix
P0
EOF
}
mk_dd4_good; mk_manifest4 mapped 2
echo '{}' | ( cd "$R" && HOOK_TARGET_ID=SCR-ADM-FOO "$HOOKS/stage4a_complete.sh" ) >/dev/null 2>&1; expect "hook4 figma: mapped + bảng đủ 2 dòng → PASS" 0 $?
# Thiếu hẳn bảng
mk_dd4_good; sed -i.bak '/FRAMES VIEWED/d' "$DD4/SCR-ADM-FOO_detailed_design.md"
echo '{}' | ( cd "$R" && HOOK_TARGET_ID=SCR-ADM-FOO "$HOOKS/stage4a_complete.sh" ) >/dev/null 2>&1; expect "hook4 figma: mapped + thiếu [FRAMES VIEWED] → BLOCK" 2 $?
# Kill switch
echo '{}' | ( cd "$R" && HOOK_TARGET_ID=SCR-ADM-FOO DISABLE_FIGMA_TRANSCRIBE_GATE=1 "$HOOKS/stage4a_complete.sh" ) >/dev/null 2>&1; expect "hook4 figma: DISABLE_FIGMA_TRANSCRIBE_GATE=1 → PASS" 0 $?
# Thiếu state: manifest 3 frame, bảng 2 dòng
mk_dd4_good; mk_manifest4 mapped 3
echo '{}' | ( cd "$R" && HOOK_TARGET_ID=SCR-ADM-FOO "$HOOKS/stage4a_complete.sh" ) >/dev/null 2>&1; expect "hook4 figma: bảng 2 dòng < 3 state export → BLOCK" 2 $?
# Câu rỗng
mk_manifest4 mapped 1
cat > "$DD4/SCR-ADM-FOO_detailed_design.md" <<'EOF'
# DD
## 2.5
**[FRAMES VIEWED]**
| default | `frames/SCR-ADM-FOO.png` | đã xem, khớp specs |
EOF
echo '{}' | ( cd "$R" && HOOK_TARGET_ID=SCR-ADM-FOO "$HOOKS/stage4a_complete.sh" ) >/dev/null 2>&1; expect "hook4 figma: quan sát là câu rỗng → BLOCK" 2 $?
# AUTHOR mode: status missing → không đòi bảng
mk_manifest4 missing 1; printf '# DD trống\n' > "$DD4/SCR-ADM-FOO_detailed_design.md"
echo '{}' | ( cd "$R" && HOOK_TARGET_ID=SCR-ADM-FOO "$HOOKS/stage4a_complete.sh" ) >/dev/null 2>&1; expect "hook4 figma: status=missing → PASS (author mode, không đòi bảng)" 0 $?
# Không có manifest → author mode
rm -f "$MFD4/figma-manifest.yaml"
echo '{}' | ( cd "$R" && HOOK_TARGET_ID=SCR-ADM-FOO "$HOOKS/stage4a_complete.sh" ) >/dev/null 2>&1; expect "hook4 figma: không có manifest → PASS" 0 $?
# BE unit: mapped nhưng không phải FE → không áp
mk_manifest4 mapped 2
printf 'schema_version: "1.1"\nunits:\n  - unit_id: MPF-01\n    figma_status: mapped\n    states:\n      - state: "s0"\n        frame_exported: true\n' > "$MFD4/figma-manifest.yaml"
printf '# DD BE\nP0\nlogic matrix\n' > "$DD4/MPF-01_detailed_design.md"
echo '{}' | ( cd "$R" && HOOK_TARGET_ID=MPF-01 "$HOOKS/stage4a_complete.sh" ) >/dev/null 2>&1; expect "hook4 figma: BE unit (MPF-*) → PASS (gate chỉ áp FE)" 0 $?

echo "── approval_gate (Hook 1) ──────────────────────────────────"
R="$(new_repo)"; mkdir -p "$R/NTAPP-output/Stage_1_Discovery"
echo '{"prompt":"/ntapp-architecture-design"}' | ( cd "$R" && "$HOOKS/approval_gate.sh" ) >/dev/null 2>&1; expect "gate file PRD/Epics thiếu → BLOCK" 2 $?
printf -- '---\napproved_by: vinh\napproved_at: 2026-01-01T00:00:00Z\n---\n# prd\n' > "$R/NTAPP-output/Stage_1_Discovery/prd.md"
cp "$R/NTAPP-output/Stage_1_Discovery/prd.md" "$R/NTAPP-output/Stage_1_Discovery/epics.md"
echo '{"prompt":"/ntapp-architecture-design"}' | ( cd "$R" && "$HOOKS/approval_gate.sh" ) >/dev/null 2>&1; expect "gate file đã approved → PASS" 0 $?

# Brownfield reproduce (Stage 2 as-is): PRD/Epics không phải tiền điều kiện.
R="$(new_repo)"; mkdir -p "$R/NTAPP-output/Stage_1_Discovery"; printf 'mode: brownfield_code_only\n' > "$R/NTAPP-output/.reproduce-mode"
echo '{"prompt":"/ntapp-architecture-design"}' | ( cd "$R" && "$HOOKS/approval_gate.sh" ) >/dev/null 2>&1; expect "brownfield: không PRD/Epics + marker .reproduce-mode → PASS" 0 $?

R="$(new_repo)"; mkdir -p "$R/NTAPP-output/Stage_1_Discovery/system_overview"; printf '# baseline\n' > "$R/NTAPP-output/Stage_1_Discovery/system_overview/_overview.md"
echo '{"prompt":"/ntapp-system-overview"}' | ( cd "$R" && "$HOOKS/approval_gate.sh" ) >/dev/null 2>&1; expect "brownfield: không PRD/Epics + baseline đã sinh → PASS" 0 $?

R="$(new_repo)"; mkdir -p "$R/NTAPP-output/Stage_1_Discovery"; printf 'mode: brownfield_code_only\n' > "$R/NTAPP-output/.reproduce-mode"
printf '# prd chưa ký\n' > "$R/NTAPP-output/Stage_1_Discovery/prd.md"
echo '{"prompt":"/ntapp-architecture-design"}' | ( cd "$R" && "$HOOKS/approval_gate.sh" ) >/dev/null 2>&1; expect "brownfield: PRD tồn tại nhưng chưa ký → vẫn BLOCK" 2 $?
echo '{"prompt":"/ntapp-architecture-design"}' | ( cd "$R" && BROWNFIELD_REPRODUCE=1 "$HOOKS/approval_gate.sh" ) >/dev/null 2>&1; expect "BROWNFIELD_REPRODUCE=1 → escape tay (PASS)" 0 $?

echo "── json_get fallback (máy không có jq) ────────────────────"
# Không có fallback thì payload đọc ra rỗng → hook không nhận ra prompt → thoát 0 → cả hàng rào
# thành no-op im lặng. PATH chỉ giữ /usr/bin:/bin (có python3, không có jq ở /opt/homebrew).
NOJQ="$(mktemp -d)"; TMPDIRS+=("$NOJQ")
R="$(new_repo)"; mkdir -p "$R/NTAPP-output/Stage_1_Discovery"
echo '{"prompt":"/ntapp-architecture-design"}' | ( cd "$R" && PATH="$NOJQ:/usr/bin:/bin" "$HOOKS/approval_gate.sh" ) >/dev/null 2>&1; expect "không jq → fallback python3 vẫn BLOCK" 2 $?
out="$( . "$HOOKS/lib/common.sh"; PATH="$NOJQ:/usr/bin:/bin" json_get '{"tool_input":{"file_path":"/a/b.ts"},"stop_hook_active":true}' '.tool_input.file_path' )"
[[ "$out" == "/a/b.ts" ]] && expect "fallback đọc path lồng (.tool_input.file_path)" 0 0 || expect "fallback đọc path lồng (.tool_input.file_path)" 0 1
out="$( . "$HOOKS/lib/common.sh"; PATH="$NOJQ:/usr/bin:/bin" json_get '{"stop_hook_active":true}' '.stop_hook_active' )"
[[ "$out" == "true" ]] && expect "fallback trả bool dạng true (guard so sánh chuỗi)" 0 0 || expect "fallback trả bool dạng true (guard so sánh chuỗi)" 0 1
out="$( . "$HOOKS/lib/common.sh"; PATH="$NOJQ:/usr/bin:/bin" json_get '{"a":1}' '.khong_co' )"
[[ -z "$out" ]] && expect "fallback key thiếu → rỗng (như jq // empty)" 0 0 || expect "fallback key thiếu → rỗng (như jq // empty)" 0 1

echo "── stop_reentry_guard (chống livelock SubagentStop) ────────"
R="$(new_repo)"; mkdir -p "$R/NTAPP-output/design-system/feature_deltas"
echo '{"stop_hook_active":true}' | ( cd "$R" && "$HOOKS/build_component_verify.sh" ) >/dev/null 2>&1; expect "stop_hook_active=true → RELEASE (exit 0)" 0 $?

echo "── maybe_disable (kill switch) ─────────────────────────────"
R="$(new_repo)"; mk_wbs "$R"; printf '// id: MPF-99 | dd_version: v1\nx\n' > "$R/foo.ts"
P="{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$R/foo.ts\"}}"
echo "$P" | ( cd "$R" && DISABLE_HOOK_BUILD_LOOP=1 "$HOOKS/build_loop.sh" ) >/dev/null 2>&1; expect "DISABLE_HOOK_BUILD_LOOP=1 → skip (exit 0 dù lẽ ra BLOCK)" 0 $?
echo "$P" | ( cd "$R" && DISABLE_HOOKS_ALL=1 "$HOOKS/build_loop.sh" ) >/dev/null 2>&1; expect "DISABLE_HOOKS_ALL=1 → skip (exit 0)" 0 $?

echo "── engine: loop cạn max_retries phải DỪNG (anti-infinite-loop) ──"
if command -v vsaf >/dev/null 2>&1; then
  out="$(mktemp)"
  ( cd "$ROOT" && vsaf run NTAPP/tests/loop-exhaust-fixture ) >"$out" 2>&1 &
  vpid=$!; ( sleep 60; kill -9 $vpid 2>/dev/null ) & wpid=$!
  wait $vpid 2>/dev/null; kill $wpid 2>/dev/null
  fails=$(grep -c '✗ FAILED' "$out" 2>/dev/null || echo 0)
  if grep -q 'Workflow failed' "$out" && [[ "$fails" == "3" ]]; then
    expect "loop fail x(1+max_retries:2)=3 rồi engine dừng" 0 0
  else
    expect "loop fail x(1+max_retries:2)=3 rồi engine dừng" 0 1
  fi
  # Lưu ý quan trọng cho CI: vsaf EXIT 0 dù workflow failed → gate bằng cách
  # parse 'Workflow failed' trong output, KHÔNG dựa $?.
  grep -q 'Workflow failed' "$out" && printf '  \033[0;33mnote\033[0m vsaf exit 0 dù failed → CI phải grep output, không gate bằng $?\n'
  rm -f "$out"
else
  printf '  \033[0;33mskip\033[0m vsaf không có trên PATH — bỏ qua ca engine\n'
fi

echo "── lib/slice_paths.py (phân giải đường dẫn slice — A/B/C §3.7) ──"
# Bộ ca riêng vì nó kiểm một THƯ VIỆN chứ không kiểm một hook: fixture tổng hợp,
# không cần repo git giả, chạy được cả khi máy không có `vsaf`.
if PY="$(command -v python3 || command -v python)" && [[ -n "$PY" ]]; then
  if "$PY" "$HOOKS/tests/test_slice_paths.py" >/dev/null 2>&1; then
    expect "slice_paths: toàn bộ ca xanh" 0 0
  else
    expect "slice_paths: toàn bộ ca xanh" 0 1
    printf '  \033[0;33mnote\033[0m xem chi tiết: python3 hooks/tests/test_slice_paths.py\n'
  fi
else
  printf '  \033[0;33mskip\033[0m không có python3/python trên PATH\n'
fi

echo '── engine: $ARGUMENTS trong bash node (hợp đồng quoting) ───'
# Engine shell-escape $ARGUMENTS ở bash node → template tự bọc quote ("$ARGUMENTS") làm giá trị
# mang theo dấu ' → `xargs` chết "unterminated quote" → biến RỖNG im lặng (input-gate của
# path-b-quick-dev từng luôn exit 1 vì lỗi này). Fixture parse bare + sed rồi tự exit 1 nếu sai.
if command -v vsaf >/dev/null 2>&1; then
  out="$(mktemp)"
  ( cd "$ROOT" && vsaf run NTAPP/tests/args-quoting-fixture --args 'BE-CTX-01 | fix off-by-one' ) >"$out" 2>&1
  if grep -q 'Workflow completed' "$out" && ! grep -q 'Workflow failed' "$out"; then
    expect "bash node parse được unit_id từ \$ARGUMENTS (bare + sed)" 0 0
  else
    expect "bash node parse được unit_id từ \$ARGUMENTS (bare + sed)" 0 1
  fi
  rm -f "$out"
else
  printf '  \033[0;33mskip\033[0m vsaf không có trên PATH — bỏ qua ca quoting\n'
fi

echo "── workflow-bash-lint (chặn tái phát 4 lỗi hỏng-mà-không-kêu) ──"
# Quét mọi bash node của mọi workflow: $ARGUMENTS ghép thẳng vào chuỗi, $WORKSPACE (không tồn tại),
# node đụng git/test mà thiếu workspace:false, và `set -u`/`set -o pipefail` (chết trên dash).
# Workflow ngoài NTAPP chỉ cảnh báo (xem script).
( cd "$ROOT" && python3 hooks/tests/workflow_bash_lint.py >/dev/null 2>&1 )
expect "mọi bash node NTAPP theo đúng hợp đồng engine" 0 $?

# Luật D phải THẬT SỰ bắt — lint sạch có thể chỉ vì luật không chạy.
wtmp="$(mktemp -d)"; TMPDIRS+=("$wtmp")
lintd="$wtmp/lintd/NTAPP"; mkdir -p "$lintd"
cat > "$lintd/w.yaml" <<'YAML'
name: w
nodes:
  - id: n1
    bash: |
      set -euo pipefail
      echo hi
YAML
( cd "$ROOT" && python3 hooks/tests/workflow_bash_lint.py "$wtmp/lintd" >/dev/null 2>&1 )
expect "lint D: bắt được 'set -euo pipefail' trong bash node" 1 $?

echo "── bug-fix-batch: cổng HITL buộc chữ ký khớp bản plan ───────"
# Cổng này là xác nhận DUY NHẤT trước khi các node fix chạm code thật. Hai bất biến:
#   (1) chạy được trên dash — /bin/sh của Debian/Ubuntu, nơi `set -o pipefail` sẽ giết script ở dòng 1;
#   (2) chữ ký gắn với checksum plan — batch dir đặt tên <ngày>-<slug> nên chạy lại cùng ngày sẽ rơi
#       trúng thư mục cũ, marker APPROVED của lần trước còn đó sẽ auto-duyệt bản plan chưa ai đọc.
gate="$wtmp/gate.sh"
( cd "$ROOT" && python3 -c "
import yaml,sys
d=yaml.safe_load(open('.vsaf/workflows/NTAPP/bug-fix-batch.yaml',encoding='utf-8'))
open(sys.argv[1],'w').write([n for n in d['nodes'] if n['id']=='approve-plan'][0]['bash'])
" "$gate" ) 2>/dev/null
gd="$wtmp/gatedir"; mkdir -p "$gd/NTAPP-output/b"
printf 'NTAPP-output/b\n' > "$gd/NTAPP-output/.current-bug-batch"
printf 'groups: [ban-1]\n' > "$gd/NTAPP-output/b/bug-groups.yaml"
for sh in bash dash; do
  command -v "$sh" >/dev/null 2>&1 || continue
  rm -f "$gd/NTAPP-output/b/APPROVED"
  ( cd "$gd" && "$sh" "$gate" ) >/dev/null 2>&1
  expect "gate/$sh: chưa duyệt → CHẶN" 1 $?
  sum=$( (shasum -a 256 "$gd/NTAPP-output/b/bug-groups.yaml" 2>/dev/null || sha256sum "$gd/NTAPP-output/b/bug-groups.yaml") | cut -c1-16 )
  echo "$sum" > "$gd/NTAPP-output/b/APPROVED"
  ( cd "$gd" && "$sh" "$gate" ) >/dev/null 2>&1
  expect "gate/$sh: duyệt đúng bản → QUA (dash không chết vì set -o pipefail)" 0 $?
  printf 'groups: [ban-2-KHAC-HAN]\n' > "$gd/NTAPP-output/b/bug-groups.yaml"
  ( cd "$gd" && "$sh" "$gate" ) >/dev/null 2>&1
  expect "gate/$sh: plan đổi sau khi duyệt → CHẶN (không fail-open)" 1 $?
  printf 'groups: [ban-1]\n' > "$gd/NTAPP-output/b/bug-groups.yaml"
done

echo "── bug-fix-batch: group phụ thuộc không nằm chung fanout mc>1 ──"
# Engine bắn tới max_concurrency item cùng lúc và KHÔNG chờ item trước xong (dispatchFanoutAi lặp tới
# `inflight < mc`), nên thứ tự tên file chỉ đổi được thứ tự phát lệnh. `git worktree add -B b2 <path> b1`
# vẫn trả rc=0 khi b1 chưa có commit → b2 lặng lẽ base về main và nuốt mất fix của b1. Rào chắn duy nhất là mc:1.
( cd "$ROOT" && python3 - <<'PY'
import sys, yaml
d = yaml.safe_load(open(".vsaf/workflows/NTAPP/bug-fix-batch.yaml", encoding="utf-8"))
fo = {n["id"]: n["fanout"] for n in d["nodes"] if "fanout" in n}
deps = {n["id"]: (n.get("depends_on") or []) for n in d["nodes"]}
# Lane serial (nơi group phụ thuộc nhau sống) BẮT BUỘC mc:1.
serial = [k for k, v in fo.items() if v["over"].rstrip("/*").endswith("serial")]
if not serial:
    print("thiếu lane serial/"); sys.exit(1)
for k in serial:
    if fo[k]["max_concurrency"] != 1:
        print(f"{k}: mc={fo[k]['max_concurrency']} — lane serial phải mc:1"); sys.exit(1)
# Không được còn lane "rest/" gộp parallel+serial như bản cũ.
if any(v["over"].rstrip("/*").endswith("rest") for v in fo.values()):
    print("còn lane rest/ gộp parallel+serial"); sys.exit(1)
# Thứ tự phải là foundation -> parallel -> serial -> verify.
if "fix-parallel" not in deps.get(serial[0], []):
    print(f"{serial[0]} phải chạy sau fix-parallel"); sys.exit(1)
if serial[0] not in deps.get("integrate-verify", []):
    print("integrate-verify phải phụ thuộc lane serial"); sys.exit(1)
PY
) >/dev/null 2>&1
expect "lane serial/ tách riêng, mc:1, xâu đúng thứ tự foundation→parallel→serial→verify" 0 $?

echo ""
echo "════════════════════════════════════════════════════════════"
printf 'PASS=%d  FAIL=%d\n' "$PASS" "$FAIL"
[[ "$FAIL" == "0" ]]
