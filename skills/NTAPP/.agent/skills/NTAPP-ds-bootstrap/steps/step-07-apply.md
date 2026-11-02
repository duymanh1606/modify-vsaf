# Step 7: Apply & Archive
> ⛔ Đây là step cuối (TERMINAL) — KHÔNG còn step kế, KHÔNG có pointer dẫn sang step tiếp.

## GOAL

Apply approved proposals (từ Step 6) vào `master_token.json` + `components_metadata.json` latest, dual-write archive snapshot, optional W3C export. Append `[APPLY SUMMARY]` vào `bootstrap_report.md`.

## ENTRY CONDITION

Chỉ chạy sau khi DSO đã tick checkboxes trong `bootstrap_report.md` tại Step 6 VÀ reply `'approved'` ở HITL prompt cuối Step 6.

## 1. Load Persona

Adopt role của **Bootstrap Applier** sub-agent tại `../agents/bootstrap-applier.md`. Persona declare: role + decision policies (§4.1 approved set composition, §4.2 validation matrix, §4.3 archive numbering, §4.4 W3C export) + output spec (§5 file list + `[APPLY SUMMARY]` markdown template) + edge cases (§6) + constraints (§7).

## 2. Inputs

- `bootstrap_report.md` (DSO-ticked).
- `master_token_parts/02_normalized.json` (`preliminary_master_token` + approved proposals).
- `master_token_parts/03_conflict_resolved.json` (optional, nếu Step 5).
- `components_metadata_parts/01_discovered.json`.
- `stack-profile.json` (snapshot vào archive).
- `_shared/token-format-schema.md`, `component-metadata-schema.md`.

## 3. Pipeline

### Stage 3.1: Re-parse approved decisions

Đọc `bootstrap_report.md`, extract approved checkboxes per section (HIGH/MEDIUM/LOW + conflict decisions + hard validation resolutions). Validate: hard validation fail chưa resolve → STOP per persona §6 message.

### Stage 3.2: Build final master_token

Theo `bootstrap-applier.md` §4.1 approved set composition:
- Start với `preliminary_master_token` từ `02_normalized.json`.
- Merge approved MEDIUM/LOW proposals.
- Merge conflict decisions từ `03_conflict_resolved.json` (nếu Step 5 chạy).
- Apply hard validation resolutions (vd: darken color values).

### Stage 3.3: Build final components_metadata

- Start với `01_discovered.json`.
- Strip `discovery_metadata` field (internal-only).
- Replace `<TODO: DSO fill>` placeholders với DSO inputs từ report (nếu DSO đã fill inline trong report editor).
- TODO chưa fill → giữ placeholder, mark `metadata.status: "incomplete"` cho component đó.

### Stage 3.4: Validate full structure

Theo persona §4.2 matrix:
- Token format theo `_shared/token-format-schema.md` — 3-tier, downward-only refs, type inference consistent.
- Component metadata theo `_shared/component-metadata-schema.md` mục 7 — 2 layers, tokens_used resolve, file_path resolve, no duplicate names.

Fail → STOP, dump `{design_system_root}/_failed_bootstrap.json`. KHÔNG ghi đè latest.

### Stage 3.5: Atomic write latest

Theo U1 + U2 + U4:
- Tempfile → rename pattern cho cả 2 files.
- Update `metadata.last_updated` ISO timestamp.
- Pretty-print 2-space indent, sorted keys (deterministic).

Paths:
- `{design_system_root}/master_token.json`
- `{design_system_root}/components_metadata.json`

### Stage 3.5b: Derive `component_catalog.md` (digest cho Stage 3b/4a)

Sinh từ `components_metadata.json` final (KHÔNG nguồn khác — derived artifact, regenerate mỗi khi metadata đổi; `/ntapp-ds-build-component` metadata-registrar cũng regenerate sau mỗi lần apply delta):

```markdown
# Component Catalog — {project}{ — {ds_id} nếu multi-DS} (derived — DO NOT EDIT; regenerate từ components_metadata.json)

| Component | Category | Intent (≤90 chars) | Variants | Used in (top 3) |
|---|---|---|---|---|
| search-input | form | Ô tìm kiếm có debounce + clear | default, compact | merchant-list, tx-history, +3 |

## Recipes (composition patterns quan sát từ code)
- **filter-bar-row** = search-input + status-dropdown + date-range-picker + search-button — thấy ở: merchant-list, tx-history
## Layout primitives
Stack, Cluster, Grid, ... (category `layout-primitive` — xem components_metadata.json §12)
```

- 1 dòng/component (mọi category trừ layout-primitive — nhóm này gộp 1 dòng liệt kê). Intent cắt ≤90 chars. `Used in` từ `usage.screens` (tên folder cuối, ≤3 + `+N`).
- Mục đích: **F3 (Stage 4a) và UX3 (Stage 3b) load file NÀY thay vì full `components_metadata.json`** — đủ vocabulary + recipes để author wireframe theo tên component thật, không tốn context. Matcher authoritative ở Stage 4b vẫn dùng full metadata.
- Atomic write: `{design_system_root}/component_catalog.md`.

### Stage 3.6: Dual-write archive

Per persona §4.3:
- Tạo `{design_system_root}/archive/_v{N+1}_{timestamp}/` (N = count existing `archive/_v*/` + 1).
- Copy: `master_token.json`, `components_metadata.json`, `stack-profile.json`, `bootstrap_report.md`.
- Timestamp collision → suffix `_a`, `_b`, ...
- Disk full → report success cho latest, cảnh báo archive skip, không exit fail.

### Stage 3.7: Optional W3C export

Nếu DSO chọn `target_format = w3c` tại INITIALIZATION:
- Convert `master_token.json` qua `_shared/w3c-converter.md` mục 3.
- Atomic write: `{design_system_root}/master_token.w3c.json`.

### Stage 3.8: Append `[APPLY SUMMARY]`

Append section vào `report_sections[]` theo `bootstrap-applier.md` §5 template. Re-compose `bootstrap_report.md` cuối cùng với apply summary (atomic write). **Multi-DS:** header report ghi thêm dòng `ds_id: {ds_id}` (lấy từ `registry.yaml` entry có root khớp `{design_system_root}`; không có registry → bỏ qua) — audit trail phân biệt report thuộc DS nào.

## 4. Decision Points

- **Hard validation fail chưa resolve** (DSO reply `'approved'` nhưng còn fail) → STOP với hint DSO mở report sửa rồi reply lại.
- **Token reference unresolved** (component dùng `semantic.color.unknown`) → validation fail. STOP, dump `_failed_bootstrap.json`.
- **`bootstrap_report.md` parse fail** → STOP với hint DSO restore valid markdown.
- **Disk full khi write archive** → log warning, vẫn report success cho latest (không exit fail).
- **TODO placeholder chưa fill** trong components_metadata → giữ placeholder + mark `status: "incomplete"` cho component đó (không block apply).

## 5. Output

- `{design_system_root}/master_token.json` (latest).
- `{design_system_root}/components_metadata.json` (latest).
- `{design_system_root}/component_catalog.md` (derived digest — Stage 3.5b).
- `{design_system_root}/bootstrap_report.md` (final, với `[APPLY SUMMARY]`).
- `{design_system_root}/archive/_v{N+1}_{timestamp}/` (snapshot).
- (Optional) `{design_system_root}/master_token.w3c.json` (nếu DSO chọn target format w3c).

## 6. Cross-repo note

Step này write **chỉ** spec repo. Code repo KHÔNG bị động chạm (Universal Rule U3). Sau khi skill chạy xong, DSO commit/push spec repo. Không cần commit code repo cho bootstrap.
