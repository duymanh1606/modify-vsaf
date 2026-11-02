# STEP 10: SECONDARY & ADDITIONAL ROLE JOURNEYS (§4.2-4.3)

> **Thực hiện bởi:** Agent UX0 (UX Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R2 (Journey Screen Table fidelity), R5, R8.4, R10**.

## 1. Mục tiêu

Journey cho secondary role (§4.2 — role có responsibility khác primary trên cùng entity) và mỗi additional role (§4.3, nếu ≥3 role). Cùng format step-09: Mermaid + Journey Screen Table (mọi rule §3.2 step-09 áp dụng — kể cả sketch preview link trong cell Purpose khi có) — KHÔNG per-screen Screen Spec.

## 2. Đầu vào cần đọc

- §2 part (archetype) + §4.1 (primary journey — để close loop) + §1.3 (role enumeration)
- `project_wbs.md` (SCR-* — R8.4); `ux_conventions.md` (§C-x refs)
- PRD — user story phụ + BR approval/oversight/external boundary

## 3. Chỉ thị thực thi

### 3.1. §4.2 Secondary Role Journey

**Applicability:** ≥2 distinct role non-overlapping trên cùng entity. Pattern: MAKER_CHECKER (reviewer) / COLLABORATIVE (co-author) / ADMIN_OVERSIGHT (auditor). **Single-role app → SKIP §4.2, KHÔNG placeholder.**

1. **Mermaid** — archetype-specific: MAKER_CHECKER `entry → queue → detail → decision → confirmation`; COLLABORATIVE `notification → review → comment/approve → notify back`; ADMIN_OVERSIGHT `dashboard → drill-down → action`. Entry signal cụ thể; end state close-loop với primary nếu archetype yêu cầu (node feedback + hàng tương ứng trong table §4.1 Key states — vd `Rejected (editable + reason)`).
2. **Journey Screen Table** (R2 — 5 cột): queue/list screen (nếu role xử lý batch), detail/decision screen, feedback-to-primary (thể hiện qua Key states của screen primary bị ảnh hưởng — KHÔNG spec màn mới nếu WBS không có). Key states nắm intent quyết định: vd `per-section Approve/Reject + reason bắt buộc khi reject` — chi tiết control là việc Stage 4a.

### 3.2. §4.3 Additional Role Journeys

**Applicability:** ≥3 distinct role. 1 sub-section per role. Pattern: SELF_SERVICE / ADMIN_CONFIGURATOR / READ_ONLY_AUDITOR / BATCH_OPERATOR / API_CONSUMER / OTHER.

Mỗi role: (1) **Role Context** 1-2 dòng (vì sao tách — access scope / UI simplification / external boundary; không copy-paste primary/secondary); (2) **Mermaid**; (3) **Journey Screen Table**. Skip role không có user story trong PRD — KHÔNG placeholder TBD.

### 3.3. Layout self-audit

Cùng L5/L6/L9 warn-only như step-09 §3.3 — 1 dòng cuối mỗi journey.

## 4. Đầu ra yêu cầu

- **Lưu trữ:** Append `{intermediate_folder}/ux0_journeys_part.md` (§4.2-4.3)
- Báo cáo: "§4.2-4.3 hoàn tất. Secondary: {X screens}; Additional: {N} role; WBS OK; L5/L6/L9: {…}."

## [GATE R6] — WBS ↔ Journey Sync (sau step 09+10)
> Mọi `SCR-*` trong §4 tables tồn tại trong `project_wbs.md`? Lệch → sửa journey hoặc escalate WBS amend (R8.4). KHÔNG đọc step-11 khi chưa sync.

**Next:** Read fully and follow `./step-11-interaction-patterns.md`
