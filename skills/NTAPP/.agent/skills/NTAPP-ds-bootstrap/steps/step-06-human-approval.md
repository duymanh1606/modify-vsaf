# Step 6: Human Approval (HITL)

## GOAL

Compose `bootstrap_report.md` từ in-memory `report_sections[]` (concat-by-emit-order), tạm dừng workflow để DSO review, approve/reject từng proposal, resolve hard validation fail (WCAG), confirm conflict decisions.

## 1. Inputs

- `report_sections[]` — array in-memory chứa markdown sections emit bởi Step 1-5 (theo concat-by-emit-order, KHÔNG hardcode list).
- `master_token_parts/01_raw_extracted.json`, `02_normalized.json`, `03_conflict_resolved.json` (nếu Step 5).
- `components_metadata_parts/01_discovered.json`.
- `stack-profile.json`.
- `.bmm-config.yaml` field `ds-bootstrap.auto_apply_high_confidence` (optional).

## 2. Pipeline

### Stage 2.1: Compose `bootstrap_report.md` (concat-by-emit-order)

Đọc `report_sections[]` array (in-memory). Concat theo thứ tự emit từ Step 1-5 (KHÔNG re-order, KHÔNG hardcode section list). Mỗi section là markdown block đã được sub-agent format theo template trong persona.

Prepend header:

```markdown
# Bootstrap Report — {project-name}
- Generated at: <iso timestamp>
- Stack profile: stack-profile.json
- Mode: {full | incremental | overhaul}
```

Atomic write theo U1 + U2: `{design_system_root}/bootstrap_report.md`.

**Section ordering reference** (emit-order theo workflow, không cố định — sub-agent có thể skip section nếu trống):

| Emit order | Section | Source |
|---|---|---|
| 1 | `[STACK PROFILE]` (optional summary) | Step 1 |
| 2 | `[LIBRARY APIs PARSED]` | Step 1b (nếu chạy) |
| 3 | `[LIBRARY API DIFF]` | Step 1b (re-parse mode) |
| 4 | `[FUNCTIONAL DUPLICATES]` | Step 3 |
| 5 | `[WRAPPER PROP HIDDEN]` | Step 3 |
| 6 | `[HIGH CONFIDENCE]` | Step 4 |
| 7 | `[MEDIUM CONFIDENCE]` | Step 4 |
| 8 | `[LOW CONFIDENCE]` | Step 4 |
| 9 | `[HARD VALIDATION FAILURES]` | Step 4 |
| 10 | `[CONFLICT RESOLUTION]` | Step 5 (nếu chạy) |

Bảng trên CHỈ là reference cho debug. Pipeline thực tế dùng `report_sections[]` array — section nào emit trước thì xếp trước.

### Stage 2.2: Auto-approve HIGH (config-driven, fallback HITL)

Đọc `.bmm-config.yaml` field `ds-bootstrap.auto_apply_high_confidence`:
- `true` → mark sẵn `[x]` toàn bộ HIGH items trong report file (re-write atomic), log "auto-applied high confidence per config", skip Stage 2.3 prompt.
- `false` (default) hoặc absent → HITL prompt: *"Auto-approve toàn bộ HIGH confidence proposals (chỉ review MEDIUM/LOW + hard validation)? Y/N"*. Y → mark `[x]` HIGH; N → để DSO review từng item.

### Stage 2.3: HITL pause — chờ DSO review

Báo DSO: *"Bootstrap report sẵn sàng tại `{path}`. Review và tick `[x]` / untick `[ ]` các proposals, resolve hard validation fail. Khi xong, reply 'approved' (hoặc 'cancel' để abort) để agent tiếp tục Step 7."*

Agent dừng tại đây cho đến khi DSO reply.

### Stage 2.4: DSO actions trên report (làm trong editor)

- Tick checkbox `[x]` cho proposals đồng ý.
- Untick `[ ]` cho proposals reject (skill bỏ qua khi apply).
- Resolve hard validation fail: chọn 1 option (vd: darken color hoặc override note).
- Conflict resolution: chọn radio option cho mỗi DSO_DECIDE entry.

### Stage 2.5: Post-approval validation

Sau khi DSO reply `'approved'`:
- Agent re-parse `bootstrap_report.md` để extract decisions.
- Validate: hard validation fail chưa resolve → STOP *"WCAG fail còn `{N}` items chưa resolve, mở report sửa rồi reply lại 'approved'".*
- Pass validation → transition tiếp Step 7.

## 3. Decision Points

- **DSO reply `'cancel'`** → agent dừng workflow, KHÔNG transition Step 7. Report đã ghi vẫn còn ở `{path}` (DSO chạy lại sau).
- **DSO reply `'approved'` nhưng `bootstrap_report.md` chưa tồn tại** (vd: agent invoke vào step-06 đơn lẻ) → quay lại Step 1-5 trước rồi mới hỏi lại approval.
- **`report_sections[]` rỗng** (greenfield repo, không có proposal) → vẫn compose report với header + note "no proposals to review", DSO reply `'approved'` để skip vào Step 7 (chỉ write skeleton master_token + empty components_metadata).

## 4. Output

- `{design_system_root}/bootstrap_report.md` (atomic write).
- DSO decisions parsed in-memory để Step 7 consume.

## [GATE: DSO APPROVAL] — ⛔ DỪNG TẠI ĐÂY

Agent dừng tại Stage 2.3 cho đến khi DSO reply. KHÔNG đọc step-07 trước khi cả hai điều kiện đạt:
- DSO reply `'approved'` (reply `'cancel'` → abort workflow, KHÔNG transition Step 7).
- Post-approval validation (Stage 2.5) pass — hard validation (WCAG) fail còn lại = 0.

**Next:** Read fully and follow `./step-07-apply.md`
