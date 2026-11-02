# STEP 04: UX PRINCIPLES → `ux_conventions.md` §C1

> **Thực hiện bởi:** Agent UX0 (UX Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R3, R5, R10**. Ghi TRỰC TIẾP vào `ux_conventions.md` (ngoại lệ R1 khai báo).

## 0. Delta-mode check (chạy TRƯỚC)

`conventions_mode: delta` (Step 01) VÀ §C1 hiện có vẫn đúng cho feature mới (không principle mới, không mâu thuẫn) → **SKIP**: log *"§C1 no delta"* + đi Next. Feature đòi principle mới / sửa principle cũ → chỉ **append/patch** mục thay đổi + CHANGE LOG row (không viết lại cả section).

## 1. Mục tiêu

Xác lập "hiến pháp" UX của PROJECT (không phải per-feature): nguyên tắc cốt lõi + nguyên tắc đặc thù domain. Mọi wireframe Stage 4a + screen Stage 5 tuân theo.

## 2. Đầu vào cần đọc

- §1 Executive Summary part (pain, vision, goals)
- PRD: Business Rules, constraints
- Briefing Step 01; `ux_conventions.md` hiện có (delta mode)

## 3. Chỉ thị thực thi

### 3.1. §C1 Core Principles

Bảng tối thiểu 7 nguyên tắc — mỗi nguyên tắc PHẢI có cột "Áp dụng trong {{project_name}}" với ví dụ CỤ THỂ (UI element/flow, không chung chung):

| # | Nguyên tắc | Mô tả | Áp dụng trong {{project_name}} |
|:--|:-----------|:------|:-------------------------------|
| 1 | **Progressive Disclosure** | Chỉ hiển thị thông tin cần thiết tại thời điểm hiện tại | _element/flow cụ thể_ |
| 2 | **Consistency** | Cùng hành động → cùng giao diện, vị trí, hành vi | _button/pattern cụ thể_ |
| 3 | **Error Prevention** | Ngăn lỗi trước khi xảy ra | _disable/validate/auto-save cụ thể_ |
| 4 | **Recognition over Recall** | Hiển thị ngữ cảnh, không yêu cầu nhớ | _auto-populate, labels, badges_ |
| 5 | **Feedback & Visibility** | Mọi hành động có phản hồi rõ ràng, kịp thời | _toast, progress, rejection detail_ |
| 6 | **Flexibility & Efficiency** | Hỗ trợ cả người mới và người thành thạo | _guided flow vs shortcut_ |
| 7 | **Minimal Input** | Giảm thiểu nhập liệu thủ công | _auto-populate, dropdown, template_ |

> **Enforcement reference (không duplicate):** §C1 được enforce qua rule catalog `{design_system_path}/_shared/layout-best-practices.md` (L1-L11). ux-design owns audit **L5/L6/L9** (journey/IA-level, warn-only — gate R6 sau step 09-10). Composition-level (L1/L2/L7…) owner là `feature-design`. **Chỉ cite rule ID, KHÔNG chép nội dung rule.**

### 3.2. §C1 Domain-Specific Principles

Phân tích mô hình tương tác chính (theo archetype sẽ chốt ở step-08 — dùng preliminary hint từ PRD) → tối thiểu 4 nguyên tắc đặc thù, format `| Nguyên tắc | {{Role A}} nhìn thấy | {{Role B}} nhìn thấy |`, mô tả CONCRETE UI elements.

### 3.3. Kiểm tra chéo

- Mỗi pain point (§1.1) có ≥1 nguyên tắc giải quyết?
- Mỗi design goal (§1.2) có ≥1 nguyên tắc hỗ trợ?
- Nguyên tắc xung đột → ghi chú ưu tiên.

## 4. Đầu ra yêu cầu

- **Ghi trực tiếp:** `{planning_artifacts}/ux_conventions.md` §C1 (atomic write) + CHANGE LOG row.
- Báo cáo: "§C1 {bootstrap hoàn tất | delta: X mục | no delta}."

**Next:** Read fully and follow `./step-06-content-strategy.md` *(step-05 design-system đã retired — DS vocabulary đi qua component_catalog.md digest)*
