# Workflow: NTAPP DS Build Component

**Goal:** Apply delta proposal (NEW + MODIFIED tokens & components) vào codebase + Master DS một cách atomic, lock-protected, idempotent.

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (INITIALIZATION + UNIVERSAL SUB-AGENT RULES + PIPELINE MAP + FAIL/OUTPUT/HARD GATE reference). Chi tiết thực thi của mỗi step nằm TRONG step file tương ứng.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi HITL/STOP gate) RỒI mới theo pointer `**Next:**` ở cuối step để đọc step kế. KHÔNG đọc trước nhiều step cùng lúc.
- State chuyển tiếp giữa các step qua routing object + `build_report_sections[]` in-memory, không qua việc giữ instruction trong context.

## INITIALIZATION

> **⚠️ Cross-repo alert:** Skill này phải chạy **trong code repo** (cwd = code repo có `package.json`), KHÔNG phải spec repo. Spec repo chỉ giữ Master DS metadata + proposed_ds_updates; component code thuộc về code repo. Yêu cầu **multi-root workspace** mở cả 2 repo. Xem [Manual_phase_1.md mục 8](../../docs/Process/Manual_phase_1.md) — Multi-repo setup.

### Bước 1 — Resolve `id`

Hỏi user `id` của đơn vị work (lấy từ `project_wbs.md`). Cung cấp placeholder ví dụ theo prefix convention:

- `SCR-{NAME}` — màn hình FE (vd: `SCR-LOGIN`)
- `WGT-{NAME}` — widget FE dùng chung (vd: `WGT-AVATAR`)

> **Build-component chỉ áp dụng cho FE đơn vị.** Proposal `proposed_ds_updates.md` được sinh từ `/ntapp-ui-generation` Stage 4b, mà Stage 4b chỉ chạy với `screen_id` / `widget_id`. Nếu user cung cấp `feature_id` (BE) → DỪNG, báo: *"`{id}` là BE feature, không có DS delta. Build-component skip — BE không động vào Master DS."*

Nếu user không cung cấp `id`, agent auto-detect từ proposal path (folder cha = `{id}`).

### Bước 2 — Auto-derive `id_type`

Từ prefix:

| Prefix | `id_type` |
|---|---|
| `SCR-*` | `screen_id` |
| `WGT-*` | `widget_id` |
| Khác | **STOP** — không phải FE unit, không vào build-component |

### Bước 3 — Inputs khác

- **Proposal path** (required) — path tới `proposed_ds_updates.md`. Default lookup: `{design_system_root}/feature_deltas/{id}/proposed_ds_updates.md` (resolve qua spec repo). Nếu user không nói rõ → agent dùng default này.
- **Proposal source** (auto-detect) — `bmad-stage-4b` nếu proposal nằm trong `feature_deltas/`, hoặc `manual` nếu DSO viết tay nơi khác.

Các quyết định khác (warning override, auto-commit) sẽ hỏi HITL tại các step tương ứng.

### Context Loading
Load `.bmm-config.yaml` block `bmad`, `ds-build` (ở **code repo root**) — extract:
- `bmad.spec_repo_root` — relative/absolute path tới spec repo (vd: `../business-management-system-doc`).
- `bmad.design_system_root` — resolved path tới **DS root của repo này** (default `{spec_repo_root}/NTAPP-output/design-system`). Project multi-DS: trỏ `{family_root}/{ds_id}` — thủ tục chuẩn `_shared/ds-resolution.md` **nhánh A**. **Guard:** `{design_system_root}/registry.yaml` tồn tại → đang trỏ family root → STOP, hint sửa config trỏ vào `{family}/{ds_id}` của repo (ngoại lệ: registry có system `root: "."` với `code_repo` khớp repo hiện tại → hợp lệ, tiếp tục).
- `bmad.code_repo_root` — root của code repo. Default = cwd (auto-detect nếu cwd có `package.json`).
- `ds-build.component_target_root` — relative path trong code repo nơi scaffold components (default per framework — Angular `src/app/lib/components`, React `src/components`, etc.).

Load các file:
- `{design_system_root}/master_token.json`, `components_metadata.json`, `stack-profile.json` (spec repo, READ).
- `{design_system_root}/_shared/proposal-schema.md`, `token-format-schema.md`, `component-metadata-schema.md` (spec repo, READ). **Multi-DS:** `_shared/` LUÔN ở family root — `{design_system_root}/_shared/` không tồn tại (DS namespaced) → đọc `{design_system_root}/../_shared/` (fallback cơ học, áp cho mọi ref `_shared/*`).

### Pre-conditions
- **Cwd phải là code repo** — verify `{code_repo_root}/package.json` tồn tại. Nếu cwd = spec repo (vd: thấy `NTAPP-output/design-system/` ngay tại cwd) → STOP với message: *"Skill phải chạy trong code repo, không phải spec repo. Mở multi-root workspace, switch sang code repo, chạy lại."*
- **Spec repo accessible** — verify `{spec_repo_root}` exist + writable (skill cần ghi master_token, metadata, build_report về spec repo).
- `master_token.json` + `components_metadata.json` + `stack-profile.json` đã tồn tại trong spec repo. Chưa có → STOP với hint chạy `/ntapp-ds-bootstrap` trước.
- Proposal file path tồn tại + parse-able theo `proposal-schema.md`.
- `components_metadata.lock` (spec repo) chưa bị giữ bởi process khác. Lock nằm TRONG `{design_system_root}` → tự per-DS: 2 DS khác nhau build song song KHÔNG đụng lock nhau.
- **Single-dev-per-DS assumption** — file-based lock chỉ protect cùng filesystem. Skill KHÔNG safe khi 2 dev concurrent chạy từ máy khác nhau với **cùng một DS root** (lock không cross-machine). Tại 1 thời điểm chỉ 1 dev chạy build-component cho cùng DS; điều phối ngoài skill (vd: Slack heads-up, branch protection). Multi-DS: dev A build DS `web-admin` + dev B build DS `mobile-app` đồng thời = OK.
- **Pre-flight runtime token config** — đọc `stack-profile.json.styling`. Nếu thiếu `runtime_token_path` HOẶC `runtime_token_format` (repo legacy schema v1.0-v1.2 chưa migrate) → trigger HITL prompt **TẠI ĐÂY** (trước Step 1), KHÔNG defer sang Step 3b. Lý do: nếu defer, DSO abort prompt giữa pipeline thì spec repo đã có `master_token` mới (Step 3) nhưng code repo không có runtime token → partial state, phải rollback manual. Pre-flight ghi override vào `{code_repo_root}/.bmm-config.yaml` block `stack.styling.{runtime_token_path, runtime_token_format}`; lần chạy sau auto-resolve. Validation: path relative (không leading `/`, không `..`), parent dir tồn tại hoặc offer tạo; format ∈ enum support (xem `runtime-token-exporter.md` §5). Skip điều kiện: `styling.css_vars_supported = false` + format không yêu cầu CSS vars → exporter vẫn chạy theo format alternative.

---

## UNIVERSAL SUB-AGENT RULES

Mọi persona/sub-agent của skill này tuân thủ các convention sau (declared **ONCE** ở đây, persona không lặp lại):

### U1. Atomic file write
Mọi write thao tác filesystem (master_token, components_metadata, runtime token file, component files, build_report, archive contents) PHẢI dùng pattern **tempfile → fsync → rename**. Không append-write, không partial write. Tránh corrupt nếu process interrupted.

### U2. Path resolution
- File trong **code repo**: path **relative** to `{code_repo_root}` (vd: `src/app/lib/components/alert-banner/alert-banner.component.ts`). KHÔNG absolute, KHÔNG prefix `{code_repo_root}`. Resolve lúc đọc/ghi: `absolute = {code_repo_root}/{relative_path}`.
- File trong **spec repo**: path relative to `{design_system_root}` (vd: `feature_deltas/{id}/build_report.md`).
- Lý do relative: portability cross-machine (dev clone code repo path khác nhau).

### U3. Cross-repo spec-repo guard (defense-in-depth)
Mọi resolve path tới code repo file (scaffold target, patch target, runtime token output) PHẢI check: nếu resolved absolute path bắt đầu bằng `{spec_repo_root}/...` → STOP với message: *"Target `{path}` rơi vào spec repo. Skill phải write file code trong code repo. Verify `.bmm-config.yaml` `bmad.code_repo_root` + multi-root workspace setup."*

Áp dụng cho: component-scaffolder (Step 4 scaffold target), component-patcher (Step 4 file_path resolve), runtime-token-exporter (Step 3b output path).

### U4. Deterministic output
Output phải reproducible: same input + same state → same output. Áp dụng:
- JSON pretty-print: 2-space indent, sorted keys (alphabetical).
- File content: stable ordering (sort tokens alphabetical TRONG tier, components alphabetical).
- Timestamps chỉ trong metadata fields định trước (`metadata.last_updated`), không scatter trong body.

### U5. Drift = STOP, not auto-correct
Bất kỳ mismatch nào giữa proposal expectation vs current state (master_token value khác `before`, file vanished, metadata mismatch) → STOP với message drift detail. Sub-agent KHÔNG được auto-correct, KHÔNG được silent ignore.

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

| # | Step file | Persona(s) | Output chính |
|---|---|---|---|
| 1 | steps/step-01-route.md | delta-router | routing object (4 paths) + `proposal_checksum` |
| 2 | steps/step-02-warning-gate.md | warning-blocker | warning gate PASS (+ override section nếu có) |
| 3 | steps/step-03-apply-tokens.md | token-applier | `master_token.json` patched (spec repo) |
| 3b | steps/step-03b-export-runtime-tokens.md | runtime-token-exporter | runtime token file (code repo) |
| 4 | steps/step-04-apply-components.md | component-scaffolder + component-patcher + metadata-registrar | component files (code repo) + `components_metadata.json` (spec repo) |
| 5 | steps/step-05-archive-report.md | metadata-registrar (reuse) | `build_report.md` + archive snapshot |

Chuỗi: **1 → 2 → 3 → 3b → 4 → 5**. Step 5 là TERMINAL. Idempotent toàn bộ ở Step 1 → log "no-op", return early (KHÔNG chạy 2-5).

Cổng HITL nằm TRONG chính step canh nó: warning override (Step 2), file collision overwrite (Step 3b), auto-commit (Step 5). Mọi drift / validation fail → STOP (Universal Rule U5).

---

## FAIL CONDITIONS (agent stop + báo user)
- **Invalid proposal** — schema fail, missing fields, decision required (vd: `library_wrap` chưa quyết).
- **Drift** — `master_token` / `components_metadata` không match prerequisites trong proposal.
- **Write error** — filesystem permission denied, lock conflict.
- **WARNING PENDING block** — DSO chưa cung cấp override note hợp lệ (hoặc warning thuộc category `library_wrap_undecided` không cho phép override).
- **Apply partial fail** — Step 3/3b/4 fail giữa chừng → rollback advisory cho DSO.
- **Runtime token export config missing (INITIALIZATION pre-flight)** — `stack-profile.json` thiếu `styling.runtime_token_path` / `runtime_token_format` VÀ DSO không phản hồi pre-flight HITL prompt (hoặc đáp không hợp lệ). Hint: chạy `/ntapp-ds-bootstrap --refresh-stack` hoặc ghi override `.bmm-config.yaml` block `stack.styling`. Pre-flight catch trước Step 1 chạy → không có partial state risk.
- **Runtime token file collision** — Step 3b detect file đích đã có nội dung không có header `AUTO-GENERATED` VÀ DSO từ chối overwrite.
- **Layout library config missing** — Step 4 detect `stack-profile.json` thiếu `layout_library` block (legacy v1.0-v1.2) VÀ proposal có layout-primitive component. Fallback `name=css-vanilla, strategy=generated-component` + emit warning, không hard stop. Khuyến nghị DSO chạy `/ntapp-ds-bootstrap --refresh-stack` để populate đúng.
- **Layout primitive mapping missing** — `layout_library.primitive_mapping` thiếu entry cho primitive cần generate (vd Sidebar nhưng `primitive_mapping.Sidebar` không có). Fallback `generated-component` strategy (xem `component-scaffolder.md` §3.1a) + warn. DSO có thể override qua `.bmm-config.yaml`.

## OUTPUTS

**Spec repo** (`{design_system_root}/...` — Master DS metadata, audit trail):
- `master_token.json` (updated)
- `components_metadata.json` (updated)
- `feature_deltas/{id}/build_report.md` (cho pre-commit Rule 7)
- `archive/_v{N+1}_{timestamp}/` (snapshot)

**Code repo** (`{code_repo_root}/...` — implementation code):
- **Runtime token file** tại `{code_repo_root}/{styling.runtime_token_path}` (vd Angular `src/styles/_design-tokens.scss`, React Tailwind `tailwind.config.js`) — auto-generated, header `AUTO-GENERATED — DO NOT EDIT`, overwrite full mỗi run.
- (Optional multi-output nếu format = `tailwind-config` + theme = `css-vars`) file thứ 2 tại `{styling.runtime_token_path_css}`.
- New component files trong `{component_target_root}/{component_name}/` (per stack-profile `component_convention.location_pattern`).
- Patched files (MODIFIED components) — git diff visible trong code repo.

> **Cross-repo commit:** sau khi skill chạy xong, dev phải tạo **2 commit ở 2 repo riêng** (không atomic). Khuyến nghị merge code repo PR trước, spec repo PR sau. Link 2 commit qua `id` header. Xem [Manual_phase_1.md mục 8.3](../../docs/Process/Manual_phase_1.md) — Cross-repo commit playbook.

## HARD GATE
Pre-commit hook Rule 7 (Manual_phase_1.md mục 7) check:
- Nếu `feature_deltas/{id}/proposed_ds_updates.md` có `[NEW]` non-empty
- VÀ `feature_deltas/{id}/build_report.md` không tồn tại HOẶC checksum mismatch
- → BLOCK commit

`build_report.md` lưu `proposal_checksum` để hook detect outdated.

---

## LAUNCH

Sau khi INITIALIZATION hoàn tất (`id` + `id_type` resolved, inputs + Context loaded, Pre-conditions + pre-flight runtime token config PASS) → bắt đầu pipeline.

**Next:** Read fully and follow `./steps/step-01-route.md`
