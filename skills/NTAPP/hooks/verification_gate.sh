#!/usr/bin/env bash
# Hook 10 — verification-gate
# Event: UserPromptSubmit before story local-commit (bmad-dev-story --commit / bmad-quick-dev --commit).
#        Còn trigger trước /superpowers-finishing-a-development-branch (express-hotfix exception).
# Check: test suite passes + ATDD tests PASS (if Mandatory) + bmad-code-review ran ≥1 + SonarQube pass.
# Note: KHÔNG check PR push — convention mới: commit local trước, PR sau khi QA approve staging.

set -uo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HOOK_DIR/lib/common.sh"
maybe_disable

INPUT="$(read_stdin_json)"
PROMPT="$(json_get "$INPUT" '.prompt')"

echo "$PROMPT" | grep -qE '/(superpowers-finishing-a-development-branch|bmad-dev-story[[:space:]]+--commit|bmad-quick-dev[[:space:]]+--commit)' || ok

CODE_ROOT="$(get_code_repo_root)"
SPEC="$(get_spec_repo_root)"
problems=()

# ─── Cache theo git-state: tests + sonar deterministic theo code, không cần
#     chạy lại khi diff không đổi. Key = HEAD + diff + untracked đã hash.
CACHE_DIR="$SPEC/NTAPP-output/_notifications/.verif_cache"
cache_key=""
if git -C "$CODE_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  cache_key=$( { git -C "$CODE_ROOT" rev-parse HEAD 2>/dev/null
                 git -C "$CODE_ROOT" diff HEAD 2>/dev/null
                 git -C "$CODE_ROOT" status --porcelain 2>/dev/null
               } | { command -v shasum >/dev/null 2>&1 && shasum -a 256 || sha256sum; } \
             | cut -c1-16 )
fi
cache_hit=false
if [[ -n "$cache_key" && -f "$CACHE_DIR/$cache_key" ]]; then
  cache_hit=true
  echo "[verification-gate] Cache hit ($cache_key) — tests+sonar đã pass cho đúng git-state này, skip chạy lại." >&2
fi

TEST_LOG="$(mktemp)"; SONAR_LOG="$(mktemp)"
trap 'rm -f "$TEST_LOG" "$SONAR_LOG"' EXIT

# 1) Detect test runner from manifest
test_cmd=""
if [[ -f "$CODE_ROOT/package.json" ]]; then
  if grep -q '"test"' "$CODE_ROOT/package.json"; then
    test_cmd="npm test --silent"
  fi
elif [[ -f "$CODE_ROOT/pyproject.toml" || -f "$CODE_ROOT/setup.py" ]]; then
  test_cmd="pytest -q"
elif [[ -f "$CODE_ROOT/go.mod" ]]; then
  test_cmd="go test ./..."
elif [[ -f "$CODE_ROOT/pom.xml" ]]; then
  test_cmd="mvn -q test"
fi

if $cache_hit; then
  : # skip — đã pass cho git-state này
elif [[ -n "$test_cmd" ]]; then
  echo "[verification-gate] Running: $test_cmd" >&2
  if ! (cd "$CODE_ROOT" && eval "$test_cmd") >"$TEST_LOG" 2>&1; then
    problems+=( "Test suite failed. Last 20 lines:
$(tail -20 "$TEST_LOG")" )
  fi
else
  echo "[verification-gate] No test runner detected — skipping test step." >&2
fi

# 2) /bmad-code-review ran ≥1 (look for review file referencing current branch)
BRANCH=$(cd "$CODE_ROOT" && git symbolic-ref --short HEAD 2>/dev/null || echo "")
REVIEW_DIR="$SPEC/NTAPP-output/Stage_5_Build_Verify/reviews"
if [[ -d "$REVIEW_DIR" ]]; then
  recent_review=$(find "$REVIEW_DIR" -maxdepth 2 -name '*.md' -mtime -1 2>/dev/null | head -1)
  if [[ -n "$recent_review" ]]; then
    # A file existing proves a file exists — not that it is a review. Count the
    # pinned `okf-finding:` markers so a freestyle note is distinguishable from a
    # conforming report. WARN only, never block: a clean review legitimately has
    # zero findings, and this check cannot tell that apart from a malformed one.
    # NOTE: `grep -c` prints 0 *and* exits 1 on no-match, so `|| echo 0` would
    # yield the two-line string "0\n0" and make the -eq test below a syntax error.
    marker_count=$(grep -cE '^[[:space:]]*<!--[[:space:]]*okf-finding:' "$recent_review" 2>/dev/null || true)
    if [[ "${marker_count:-0}" -eq 0 ]]; then
      echo "[verification-gate] WARN: $(basename "$recent_review") has no 'okf-finding:' markers." >&2
      echo "[verification-gate]       Either the review was clean, or it does not follow" >&2
      echo "[verification-gate]       .agent/skills/bmad-code-review/templates/review_report_template.md" >&2
      echo "[verification-gate]       Unmarked findings are invisible to every downstream count." >&2
    fi
  else
    problems+=( "/bmad-code-review not run in last 24h. Run it on the diff before committing story." )
  fi
else
  problems+=( "reviews/ folder missing — run /bmad-code-review before committing story." )
fi

# 3) ATDD tests PASS (if Mandatory) — heuristic: if atdd-checklist exists in
#    code repo and has unchecked items
ATDD_CHECKLIST=$(find "$CODE_ROOT/NTAPP-output/test-artifacts" -maxdepth 1 \
  -name 'atdd-checklist-*.md' 2>/dev/null | head -1)
if [[ -n "$ATDD_CHECKLIST" ]]; then
  unchecked=$(grep -cE '^\s*[-*]\s*\[ \]' "$ATDD_CHECKLIST" 2>/dev/null || echo 0)
  if [[ "$unchecked" -gt 0 ]]; then
    problems+=( "ATDD checklist has $unchecked unchecked item(s) in $(basename "$ATDD_CHECKLIST")" )
  fi
fi

# 4) SonarQube — check if sonar-scanner or vds-cli sonarqube available; run if yes
if $cache_hit; then
  : # skip — đã pass cho git-state này
elif command -v sonar-scanner >/dev/null 2>&1; then
  echo "[verification-gate] Running sonar-scanner (quality gate check)..." >&2
  if ! (cd "$CODE_ROOT" && sonar-scanner -Dsonar.qualitygate.wait=true) \
      >"$SONAR_LOG" 2>&1; then
    problems+=( "SonarQube Quality Gate FAILED.
$(tail -15 "$SONAR_LOG")" )
  fi
else
  echo "[verification-gate] sonar-scanner not found — SonarQube gate skipped (verify manually)." >&2
fi

if [[ ${#problems[@]} -gt 0 ]]; then
  log_event "verification-gate" "BLOCK" "${#problems[@]} problem(s)"
  msg="Verification gate failed before story commit:
"
  for p in "${problems[@]}"; do msg+="
- $p
"; done
  msg+="
Fix and retry commit. (Sau khi tất cả stories pass → /ntapp-staging-deploy để build staging cho QA.)"
  block "$msg"
fi

# PASS → ghi cache cho git-state này (lần sau cùng diff sẽ skip tests+sonar)
if [[ -n "$cache_key" ]] && ! $cache_hit; then
  mkdir -p "$CACHE_DIR"
  : > "$CACHE_DIR/$cache_key"
  # prune: giữ tối đa 20 marker gần nhất
  ls -1t "$CACHE_DIR" 2>/dev/null | tail -n +21 | while IFS= read -r old; do
    rm -f "$CACHE_DIR/$old"
  done
fi

log_event "verification-gate" "PASS"
ok
