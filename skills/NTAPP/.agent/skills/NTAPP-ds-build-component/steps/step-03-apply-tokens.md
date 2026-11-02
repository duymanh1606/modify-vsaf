# Step 3: Apply Tokens

## GOAL
Patch `master_token.json` với `tokens_to_apply` từ routing object — theo thứ tự tier (global → semantic → component), validate downward-only references, log breaking changes.

## 1. Load Persona

Adopt role của **Token Applier** sub-agent tại `../agents/token-applier.md`. Persona declare: role + constraints + breaking detection rules + output build_report section format. Pipeline + validation matrix ở step file này.

## 2. Inputs

- Routing object `tokens_to_apply` (đã sorted theo `apply_order` từ Step 1).
- `master_token.json` (current latest, spec repo).
- `_shared/token-format-schema.md` (validation rules).

## 3. Pipeline

### Stage 3.1: Load + parse

Đọc `master_token.json`. Parse JSON. Fail → STOP `"master_token.json corrupt, đề xuất DSO rollback từ archive snapshot gần nhất"`.

**Greenfield** (file không tồn tại): tạo từ template tối thiểu (metadata + 3 empty tier objects), proceed.

### Stage 3.2: Apply theo tier order

Iterate `tokens_to_apply` (sorted: global → semantic → component):

**NEW operation:**
1. Verify `path` KHÔNG tồn tại (delta-router đã check, double-check).
2. Insert vào tier object đúng (tạo nested keys nếu cần).
3. Nếu value là reference (`{path.to.token}`):
   - Resolve tier của reference target.
   - Verify reference tier ≤ current tier (downward-only).
   - Verify reference path đã tồn tại trong `master_token` HOẶC đã apply earlier trong batch CÙNG TIER trước đó. Forward reference cùng tier same batch → KHÔNG cho phép (STOP yêu cầu reorder/split).
   - Fail → STOP "invalid reference".

**MODIFIED operation:**
1. Verify current `master_token[path]` value match `before` (drift check Universal Rule U5).
2. Replace với `after`.
3. Detect breaking change (Stage 3.3).

### Stage 3.3: Breaking change detection

Đánh dấu `breaking: true` (log vào build_report) nếu MODIFIED gây:

| Condition | Severity |
|---|---|
| Type change (color → spacing, color → size) | BREAKING |
| Reference target tier upgrade (semantic → component reference) | BREAKING — và BLOCK (vi phạm downward-only) |
| Numeric value delta > 30% (vd: 16px → 24px là OK; 16px → 24px+ → cảnh báo layout break) | BREAKING |

Proposal khai `breaking: false` nhưng skill detect `true` → STOP `"breaking change not declared in proposal — re-review Agent 1 output"`. Config `ds-build.breaking_declaration_mode: lenient` → log warning thay vì STOP.

### Stage 3.4: Cascade analysis (informational)

Sau khi MODIFIED token X:
- Tìm tất cả tokens reference `{X}` trực tiếp hoặc gián tiếp.
- Output cascade list vào build_report section (informational).
- KHÔNG auto-cascade rewrite — Agent 1 đã decide cascade trong proposal (nếu user chọn manual cascade).

### Stage 3.5: Validate full master_token post-apply

Theo `_shared/token-format-schema.md`:

| Rule | Check |
|---|---|
| 3-tier structure intact | top-level keys = `{global, semantic, component, metadata, schema_version}` |
| Tất cả references resolve được | Iterate, resolve, fail nếu missing |
| Tất cả references downward-only | tier source ≤ tier target |
| Type inference từ path patterns nhất quán | path `color.*` value phải parse hex/rgb |
| Schema version + metadata vẫn present | top-level fields không bị strip |

Fail bất kỳ rule → STOP `"apply partial fail"` + dump diff vào `{design_system_root}/_failed_master_token.json` cho debug. KHÔNG ghi đè latest.

### Stage 3.6: Atomic write

Theo Universal Rule U1 (workflow.md): tempfile → fsync → rename. Path: `{design_system_root}/master_token.json`. Update `metadata.last_updated = <iso timestamp>`. Pretty-print 2-space indent (U4 deterministic).

### Stage 3.7: Emit build_report section

Append `[TOKENS APPLIED]` vào in-memory `build_report_sections[]` theo format ở `token-applier.md` §4. Subsections: NEW (list), MODIFIED (list with breaking flag), Cascade (informational).

## 4. Output

- `{design_system_root}/master_token.json` patched (atomic write).
- In-memory `applied_tokens` list (cho Step 4 cross-ref verify component `tokens_used`).
- In-memory build_report section `[TOKENS APPLIED]`.

## DECISION POINTS

- Validation fail post-apply → STOP "apply partial fail" + dump `_failed_master_token.json`.
- Skill detect breaking nhưng proposal khai `breaking: false` → STOP (default mode) hoặc log warning (lenient mode).
- Forward reference cùng tier same batch → STOP yêu cầu reorder/split proposal.

> **[GATE]** Validation post-apply (Stage 3.5) phải PASS + breaking declaration khớp (Stage 3.3). Fail → STOP + dump `_failed_master_token.json`, KHÔNG đọc step kế.

**Next:** Read fully and follow `./step-03b-export-runtime-tokens.md`
