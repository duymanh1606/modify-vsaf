# STEP 06: CONTENT STRATEGY & MICROCOPY → `ux_conventions.md` §C2

> **Thực hiện bởi:** Agent UX4 (Content Strategist — Paige)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R3, R5, R8.2 (Module 0 §7 read-only cho status), R10**. Ghi TRỰC TIẾP vào `ux_conventions.md` (ngoại lệ R1).

## 0. Delta-mode check (chạy TRƯỚC)

Delta mode VÀ §C2 hiện có cover đủ feature mới → SKIP (log "§C2 no delta"). Feature mới thêm entity/status enum mới (Module 0 §7 có enum chưa map) hoặc empty/loading state mới → chỉ append rows tương ứng + CHANGE LOG.

## 1. Mục tiêu

"Giọng nói" của product (project-wide): writing rules, microcopy (empty/loading), status labels canonical-mapped Module 0 §7.

**Lưu ý:** Notification copy KHÔNG ở đây — single source of truth là §C4 (step-12).

## 2. Đầu vào cần đọc

- §1 part (bối cảnh + domain terminology) + §C1 (Feedback & Visibility, Error Prevention)
- Module 0 §7 Global State Registry (nếu có) — state enum cho status labels (R8.2 1-1)
- `component_catalog.md` — component EmptyState/Skeleton nếu có (R5 — gọi đúng tên; thiếu → `[gap — propose Stage 4b]`)
- `master_token.json` — verify `semantic.color.status.*` token paths
- PRD — BR trạng thái workflow

## 3. Chỉ thị thực thi

### 3.1. §C2 UI Content Writing Rules

Bảng `| Quy tắc | Ví dụ đúng | Ví dụ sai |` ≥5 quy tắc bắt buộc (adapt example theo domain THẬT):
1. **Ngắn gọn, hành động** — verb-first label; 2. **Ngôi thứ 2**; 3. **Nói rõ hệ quả**; 4. **Không mã lỗi kỹ thuật**; 5. **Hướng dẫn sửa, không chỉ báo lỗi**.

### 3.2. §C2 Contextual Microcopy

- **Empty State** (structured spec, KHÔNG ASCII): Icon + Headline + Guidance + CTA; component từ catalog. Minimum 2 (primary view + secondary view nếu có).
- **Loading State**: skeleton (load data) vs spinner + message (submit — đặt expectation).

### 3.3. §C2 Status Labels

Bảng `| Display Status | Color (token path) | Module 0 §7 enum | User Description |`:
- Color reference `semantic.color.status.*` — KHÔNG hex.
- 1-1 mapping với Module 0 §7 enum (R8.2 + R10): mỗi enum đúng 1 row, 1 label không map nhiều enum. Module 0 §7 thiếu → derive từ PRD BR + mark "pending Tech Lead reconcile".
- Cover lifecycle theo archetype (preliminary — step-08 confirm; lệch → quay lại patch).

## 4. Đầu ra yêu cầu

- **Ghi trực tiếp:** `ux_conventions.md` §C2 + CHANGE LOG row.
- Báo cáo: "§C2 {bootstrap | delta X rows | no delta}. {Z} status labels 1-1 Module 0 §7."

**Next:** Read fully and follow `./step-07-information-architecture.md`
