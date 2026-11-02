# NTAPP Hooks — Canonical Source

**Canonical location:** `<NTAPP-VSAF-Blended>/hooks/`. Consumer repos (spec repo, code repos) symlink hoặc copy về `.claude/hooks/` để Claude Code event API pick up.

Implementation cho 15 hook trong `<spec-repo>/docs/Process/hooks_design.md` (1-10) và `<spec-repo>/docs/Process/workflow_recommedation.md` §3 (12-16). *(Hook 11 post-merge-sensors đã gỡ cùng workflow `post-merge-sensors` — số thứ tự giữ nguyên để tránh renumber.)*

---

## Consume từ repo khác

### Pattern 1 — Symlink (recommended, single source of truth)

Đặt NTAPP-VSAF-Blended repo + consumer repo cùng folder cha. Từ consumer repo root:

```bash
# Spec repo example (parent: ~/Ngoanh CoWork/BMS HUB/business-management-system-doc)
# NTAPP-VSAF-Blended repo at:  ~/Ngoanh CoWork/NTAPP-VSAF-Blended
# Relative depth: 3 levels up to common ancestor "Ngoanh CoWork"
ln -s ../../../NTAPP-VSAF-Blended/hooks .claude/hooks
chmod +x .claude/hooks/*.sh .claude/hooks/*.py  # one-time, follows symlink
```

Relative path tự verify:

```bash
$ readlink .claude/hooks
../../../NTAPP-VSAF-Blended/hooks
$ ls -la .claude/hooks/notify.sh  # should resolve transparently
```

Khi NTAPP-VSAF-Blended repo update (git pull), symlink tự thấy version mới — không cần action thêm.

### Pattern 2 — Copy + sync (khi không thể symlink, vd Windows native)

```bash
cp -r <ntapp-vsaf-blended>/hooks/. .claude/hooks/
chmod +x .claude/hooks/*.sh .claude/hooks/*.py
```

Phải re-sync mỗi lần NTAPP-VSAF-Blended repo update. Khuyến nghị thêm script CI check checksum.

### Đăng ký events — tự động qua bootstrap (khuyến nghị)

`./scripts/bootstrap.sh` (step `link_event_hooks`) tự làm 2 việc cho **mọi repo** (spec + code):

1. Symlink `hooks/` → `.claude/hooks/` (relative, machine-local, gitignored).
2. Merge block `hooks` từ manifest `scripts/templates/claude-hooks.settings.json` vào `.claude/settings.json` (committed).

Re-run bootstrap ghi đè trọn block `hooks` → tự nhặt hook mới khi manifest đổi. Không cần `ln -s` hay sửa settings tay nữa.

> ⚠️ **Hook KHÔNG merge** giữa `settings.json` ↔ `settings.local.json` — local **thay thế hoàn toàn** project. Block `hooks` PHẢI ở `settings.json` (committed). **Đừng** để `hooks` trong `settings.local.json` kẻo xoá sạch. (Permissions thì merge — không sao.)

**Schema lưu ý** (đã verify với Claude Code docs):
- `UserPromptSubmit` / `Stop` — **không** field `matcher` (fire mọi prompt / mọi turn-end).
- `PostToolUse` — `matcher` **bắt buộc**, match tool name: `"Write|Edit|MultiEdit"`.
- `SubagentStop` — `matcher` match *agent type*; manifest dùng `".*"` (mọi subagent). *Chỉ fire cho Task-subagent — nếu skill chạy ở main loop, smoke-test thật để xác nhận, fallback đổi sang `Stop`.*
- Exit `2` = block; nhiều hook cùng event chạy hết theo thứ tự, gặp `2` thì action bị chặn.

Đăng ký thủ công (chỉ khi không chạy được bootstrap, vd Windows native không symlink được): copy `hooks/` → `.claude/hooks/`, rồi merge nội dung `scripts/templates/claude-hooks.settings.json` vào `.claude/settings.json`.

---

## Hook map

| # | File | Event | Behavior |
|---|---|---|---|
| 1 | `approval_gate.sh` | UserPromptSubmit | Block trigger Stage 2+/2b+ khi PRD/Epics/HLD/WBS thiếu `approved_by:` — *trừ nhánh brownfield reproduce, xem dưới* |
| 2 | `drift_detector.py` | UserPromptSubmit + PostToolUse | 3-way drift check WBS ↔ Module 0 ↔ HLD ↔ Epics |
| 3 | `stage3_input_gate.sh` | UserPromptSubmit | Verify WBS + HLD + Master DS + slice plan trước Stage 3/4a |
| 4 | `stage4a_complete.sh` | SubagentStop | Verify DD required sections (§1, §2.2, §3.2, §5.2, FE-specific) |
| 5 | `ds_delta_router.sh` | SubagentStop | RECORDER — `[NEW]` non-empty → ghi `ds_delta_decision.md` (pending\|auto_approved) + notify DSO, **warn_pass** (không block-on-Stop) |
| 5b | `ds_build_approval_gate.sh` | UserPromptSubmit | Chặn `/ntapp-ds-build-component` khi decision record còn `pending` (gate chờ-người thật, an toàn 1-shot) |
| 6 | `build_component_verify.sh` | SubagentStop | Verify `build_report.md` + `master_token.json` schema |
| 7 | `story_bridge_gate.sh` | SubagentStop | Verify story AC + Tasks + Dev Notes + Testing + `slice_id` |
| 8 | `atdd_classifier.sh` | UserPromptSubmit | ⛔ DECISION — ambiguous ATDD → notify QA |
| 9 | `build_loop.sh` | PostToolUse + pre-commit | 9 pre-commit rules realtime per-edit |
| 10 | `verification_gate.sh` | UserPromptSubmit | Test suite + ATDD + SonarQube + code-review check trước story commit (không phải PR) |
| 12 | `triage_prereq_gate.sh` | UserPromptSubmit | Block `/ntapp-feature-triage` nếu batch phase chưa xong |
| 13 | `triage_decision_validate.sh` | SubagentStop | Verify decision file front-matter complete |
| 14 | `stage2_completeness.sh` | SubagentStop | Verify HLD + Module 0 + WBS sau `/ntapp-architecture-design` |
| 15 | `slice_coverage_dag_validate.py` | SubagentStop | Coverage + DAG no-cycle sau `/ntapp-slice-planning` |
| 16 | `hotfix_classifier.sh` | UserPromptSubmit | Express Lane preset match — block abuse |

## Hook 1 — brownfield reproduce relaxation (Stage 1 gate)

Nhánh gate PRD/Epics (fire khi prompt gọi `/ntapp-architecture-design` hoặc `/ntapp-system-overview`) có 1 ngoại lệ: workflow `NTAPP/reproduce_architecture` dựng kiến trúc **as-is từ code**, PRD/Epics không phải tiền điều kiện.

| Trạng thái Stage 1 | Bằng chứng brownfield | Verdict |
|---|---|---|
| `prd.md` + `epics.md` **cùng vắng mặt** | có `NTAPP-output/.reproduce-mode` (node `input-gate` ghi) **hoặc** ≥1 `*.md` trong `Stage_1_Discovery/system_overview/` | `warn_pass` (log verdict `RELAX`) |
| `prd.md` + `epics.md` cùng vắng mặt | không có bằng chứng nào | **BLOCK** (greenfield chưa chạy Stage 1) |
| Có ≥1 file nhưng thiếu `approved_by:`/`approved_at:` | (không xét) | **BLOCK** — Stage 1 đã chạy thì phải ký |

`BROWNFIELD_REPRODUCE=1` = escape tay, pass cả trường hợp file tồn tại chưa ký. Env này **chỉ** nới nhánh Stage 1; gate Stage 2 (HLD/Module 0/WBS trước `slice-planning` / `technical-design` / `ux-design`) không bị ảnh hưởng.

## Stop/SubagentStop re-entry guard

Hook `SubagentStop` có `block` (6/7/13/15) gọi `stop_reentry_guard "<name>"` ngay sau khi source `common.sh`. Claude Code đặt `stop_hook_active: true` khi hook đã block ≥1 lần và agent vẫn chạy tiếp vì bị chặn dừng; guard thoát `0` ở lần re-entry đó để tránh **livelock** (block → continue → block vô hạn) với gate mà agent không tự thỏa mãn được. Lần block đầu vẫn enforce như cũ; chỉ lần lặp thứ 2+ được release (ghi verdict `RELEASE` vào `hook_events.log`).

> Hook 5 (`ds-delta-router`) **không** dùng guard này nữa vì đã đổi sang **warn_pass** (không bao giờ block-on-Stop). Đây là nguyên tắc chung: **cổng chờ-người luôn đặt ở `UserPromptSubmit`** (như Hook 1, 5b) — nơi "chặn = từ chối 1 prompt do người resubmit", không bao giờ ở `Stop`. Decision-cho-người ở `Stop` chỉ nên *ghi sổ + notify*, để gate `UserPromptSubmit` enforce.

## DS delta — auto-approve & decision record

Hook 5 ghi `<design-system>/feature_deltas/<ID>/ds_delta_decision.md` (front-matter `status:` = `pending` | `approved` | `auto_approved`). Hook 5b đọc record này để quyết định cho `/ntapp-ds-build-component` chạy hay không.

- **Auto-approve OFF** (default): NEW delta → `status: pending`. DSO duyệt tay (đổi `status: approved`) hoặc revise design. Hook 5b chặn ds-build tới khi approved.
- **Auto-approve ON**: NEW delta → `status: auto_approved` ngay, audit trail vẫn ghi. Bật bằng `.bmm-config.yaml` → `ntapp-ds-build-component.ds_delta_auto_approve: true`, hoặc env `DS_DELTA_AUTO_APPROVE=1` (tạm 1 phiên).
- Hook 5 **không clobber** record đã `approved`/`auto_approved` — chạy lại không reset DSO approval. (Hạn chế đã biết: nếu NEW entries đổi *sau* khi approved, record không tự re-pend — sửa tay nếu cần.)

## Shared lib

- `lib/common.sh` — color codes, repo path resolution, block/ok helpers, `stop_reentry_guard`, event logger, `json_get`

> **`json_get` — jq optional, không phải hard dependency.** Đọc payload hook bằng `jq` nếu có, thiếu `jq` thì fallback `python3` với **cùng semantics** `jq -r '<path> // empty'` (key thiếu / null / rỗng → in rỗng; bool → `true`/`false`; hỗ trợ path lồng như `.tool_input.file_path`). Lý do phải có fallback: mọi hook branch theo payload (`.prompt`, `.hook_event_name`, `.tool_input.file_path`) — path đọc ra rỗng nghĩa là hook không nhận ra prompt/file nào, thoát `0`, và **cả hàng rào biến thành no-op mà không có dấu hiệu gì** trên máy chưa cài jq. Thiếu cả `jq` lẫn `python3` → in `[HOOK DEGRADED]` ra stderr (fail-open, không brick session). Test suite chạy xanh ở cả 2 chế độ (có jq / không jq) — xem block `json_get fallback` trong `tests/run.sh`.
- `lib/entry_mode.sh` — parse `.bmm-entry-mode` (full / stage_4_standalone / stage_5_standalone)
- `lib/telegram.sh` — Telegram POST sender (env: `TELEGRAM_BOT_TOKEN`, `TG_CHAT_<ROLE>`)
- `lib/wbs_parser.py` — parse `project_wbs.md` markdown table → unit list

## Notification

`notify.sh` — single sink, multi-channel. Usage:

```bash
.claude/hooks/notify.sh <severity> <decision_required> <title> <body> [--mention @role]

# Examples:
.claude/hooks/notify.sh decision_required true "DS delta NEW — SCR-FOO" "..." --mention @DSO
.claude/hooks/notify.sh warn false "Stage 4a DD incomplete" "..." --mention @SeniorDev
```

Routing per `hooks_design.md §4`:
- `info` → log file
- `warn` → IDE chat inbox (`NTAPP-output/_notifications/inbox.md`)
- `decision_required=true` → Telegram + IDE chat
- `error` → IDE chat (LLM tự đọc + sửa)

## Path resolution

Hooks dùng CWD-based path resolution (`git rev-parse --show-toplevel`, `.bmm-config.yaml` block `spec_repo_root` / `code_repo_root`). Bất kể hooks sống ở `<NTAPP-VSAF-Blended>/hooks/` hay symlink, khi Claude Code spawn hook thì CWD = consumer repo root → `get_repo_root()` / `get_spec_repo_root()` / `get_code_repo_root()` resolve đúng repo đang invoke.

Hooks tham chiếu lẫn nhau qua `$HOOK_DIR/lib/*.sh` (resolved từ `${BASH_SOURCE[0]}`) — sibling resolution, không phụ thuộc CWD.

## Bypass khẩn cấp

- Disable 1 hook: `DISABLE_HOOK_<NAME>=1` (NAME = tên file viết HOA, `_` thay ký tự khác — vd `DISABLE_HOOK_BUILD_LOOP=1`). Đã wire qua `maybe_disable` (sh) / `hook_disabled` (py).
- Disable tất cả hook: `DISABLE_HOOKS_ALL=1`.
- Skip pre-commit hook: `SKIP_PRECOMMIT=1 git commit` (Manual §7).

## verification-gate cache

Hook 10 cache kết quả `tests + sonar` theo **git-state** (HEAD + diff + untracked đã hash). Diff không đổi → skip chạy lại (cùng 1 prompt resubmit nhiều lần không trả giá test suite mỗi lần). Marker ở `NTAPP-output/_notifications/.verif_cache/<key>`, giữ tối đa 20 cái gần nhất. Code đổi → key đổi → cache tự miss. Các check rẻ (code-review recency, ATDD checklist) vẫn chạy mỗi lần.

## Test fixtures

`hooks/tests/run.sh` — harness pre-rollout: mỗi hook block có ≥1 ca PASS + ≥1 ca BLOCK, chạy trong sandbox git tạm (mktemp, tự dọn). Bao gồm ca **chống livelock** (`stop_hook_active=true` → release), **kill switch** (`DISABLE_HOOK_*`), và 2 ca **engine** (fixture trong `.vsaf/workflows/NTAPP/tests/`):

- `loop-exhaust-fixture.yaml` — loop `on_fail` cạn `max_retries` phải DỪNG bằng failure, không treo.
- `args-quoting-fixture.yaml` — hợp đồng nội suy `$ARGUMENTS` trong `bash:` node: engine **shell-escape** giá trị, nên template phải đọc `args=$ARGUMENTS` (bare). Tự bọc quote (`args="$ARGUMENTS"`) làm giá trị mang theo dấu `'` → `xargs` chết "unterminated quote" → biến rỗng **im lặng**, node gate biến thành no-op. Fixture in ra `QUOTED-LEAK`/`BARE-OK` và tự fail nếu recipe parse vỡ.

```bash
bash hooks/tests/run.sh    # exit 0 nếu all pass
```

> ⚠️ **Engine exit-code:** `vsaf run` **exit 0 kể cả khi workflow failed**. CI wrapper PHẢI gate bằng cách grep `Workflow failed` trong output, KHÔNG dựa `$?`. (Phát hiện từ fixture loop-exhaust.)

## Entry mode

`.bmm-entry-mode` marker file ở consumer repo root, gitignored. Schema:

```yaml
mode: stage_4_standalone        # full | stage_4_standalone | stage_5_standalone
declared_by: <user>
declared_at: <ISO>
reason: "<≥20 chars>"
```

Hooks 1/2/3/4/7/14/15 mode-aware — skip hoặc relax gate upstream. Hooks 5/6/9/10 vẫn enforce (DS integrity + build loop độc lập với pipeline).

## Ratchet log

Mỗi rule mới trace 1 incident thực vào `<spec-repo>/docs/Process/ratchet-log.md` (KHÔNG thêm rule phòng ngừa chung). Defer hooks không có incident: golden-principles, context-rot-monitor, skill-conflict-guard, code-review-completeness, express-compensate-block.

## Test fixtures

(TODO Sprint 1) Mỗi hook cần ≥1 pass case + ≥1 fail case fixture ở `<NTAPP-VSAF-Blended>/hooks/tests/`. Pre-rollout checklist: xem `<spec-repo>/docs/Process/hooks_design.md §6.3`.
