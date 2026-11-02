# STEP 03: ROUGH IA (§3)

> **Thực hiện bởi:** Agent UXS0 (UX Sketch Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R3, R4, R10**.

## 1. Mục tiêu

Tạo top-level navigation tree (3-5 mục cấp 1) + integration points với existing systems. **Đặc biệt critical cho brownfield/integration projects** — đây là input chính giúp Tech Lead design HLD module breakdown sát flow user.

## 2. Đầu vào

- §2 Personas (từ Step 02 — biết user goals)
- PRD: feature list + scope
- Epics: feature → epic mapping
- Project knowledge (nếu có): existing systems list, terminology
- Briefing từ Step 01

## 3. Chỉ thị thực thi

### 3.1. Top-Level Navigation Tree

Generate ASCII tree:
- 3-5 mục cấp 1 (top-level menu items)
- Mỗi mục cấp 1: 2-4 item cấp 2 (sub-features)
- Đặt tên theo user mental model, KHÔNG theo backend service/module name (vì backend chưa design).

**Naming guideline:**
- Dùng noun + verb đơn giản (vd "Manage Merchants", "View Reports").
- Tránh technical term (vd "MERCHANT_PROFILE Service") — UX là user-facing.

**Trace:** Mỗi nav item phải tương ứng với ≥ 1 feature trong PRD/Epics. Nếu không có evidence → KHÔNG tạo (R3 + R10).

### 3.2. Integration Points với Existing Systems (BROWNFIELD CRITICAL)

Nếu project là brownfield hoặc cần tích hợp với hệ thống sẵn có:

Liệt kê table với 4 cột:

| Existing System | Direction | Data / Action | UX Touchpoint |
|:--|:--|:--|:--|

**Direction values:**
- `Read` — UX hiển thị data từ system khác (vd portal hiện info từ CRM)
- `Write` — UX gửi data sang system khác (vd form submit tạo record bên kia)
- `Sync (bi-directional)` — 2 chiều
- `SSO/Auth` — chỉ authentication, không transfer data

**Source for "Existing System" list:**
- Project knowledge docs (nếu có) — section "Existing Systems" / "Hệ thống liên quan"
- PRD §X — "External Systems" hoặc "Integrations"
- User interview / brief

**Lưu ý:** Đây là **rough guess** — SA sẽ refine ở Stage 2 HLD/Module 0. Mark rõ là proposal:
> "**Note:** Đây là rough guess. SA sẽ refine ở Stage 2 HLD/Module 0. Nếu có drift → escalate."

### 3.3. Greenfield project (no existing systems)

Nếu không có existing system để tích hợp:
- §3.2 chỉ list "—" hoặc note "Greenfield project — no integration points to map."
- Không bịa system (R3).

## 4. Đầu ra yêu cầu

- **Lưu trữ:** Append vào `{intermediate_folder}/uxs0_journey_part.md` (khởi tạo file ở step này, sẽ append §4 ở Step 04)
- Nội dung: §3.1 Navigation Tree + §3.2 Integration Points table
- Báo cáo: "§3 Rough IA hoàn tất. X nav items cấp 1, Y sub-items cấp 2, Z integration points với existing systems."

## NEXT
[step-04-primary-journey.md](./step-04-primary-journey.md)
