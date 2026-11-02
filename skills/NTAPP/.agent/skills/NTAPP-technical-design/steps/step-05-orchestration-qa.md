# STEP 05: SEQUENTIAL ASSEMBLY & QUANTITATIVE AUDIT

> **Acting as:** [Agent 0 — Orchestrator](../agents/agent_0_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R1 (Verbatim Injection), R2 (Zero-Summarization), R6 (Quality Gates), R7 (Stopping Errors).
> ⛔ **TERMINAL** — đây là step CUỐI của pipeline: KHÔNG còn step kế, KHÔNG có con trỏ điều hướng tiếp theo. Cổng `[GATE — ASSEMBLY AUDIT]` của step này là **Pass 5** (Quantitative Audit) + **Pass 6** (Grounding Check Section 7): mismatch số bảng/sơ đồ hoặc state bịa → DỪNG, redo Injection, TUYỆT ĐỐI không bàn giao tài liệu lỗi.

## 1. Mục tiêu
Hợp nhất các phần thiết kế từ `.ts_parts` thành tài liệu TechSpec hoàn chỉnh bằng quy trình lắp ráp tuần tự để bảo toàn 100% dữ liệu thô.

## 2. Chỉ thị thực thi (Sequential Assembly Protocol)
1. **Pass 1: Initialization**: Tạo file rỗng sử dụng `techspec_v3_ultimate_template.md` (template name giữ nguyên — version trong tên template, không phải output). Điền đầy đủ thông tin Metadata (Mục 1, 2, 3).
2. **Pass 2: Strategic Injection**: Đọc `part_1_strategy.md`. Sao chép nguyên văn (Verbatim) nội dung vào các Mục 1, 2, 3 và 6.1.
3. **Pass 3: Modeling Injection**: Đọc `part_2_modeling.md`. Sao chép nguyên văn nội dung vào các Mục 4, 5, 6.2, 6.3 và 7.
4. **Pass 4: Implementation Injection**: Đọc `part_3_implementation.md`. Sao chép nguyên văn nội dung vào các Mục 8, 9, 10, 11 và 12.
5. **Pass 5: Quantitative Audit (Bắt buộc)**:
    - Đếm số bảng (`|`) và sơ đồ (`mermaid`) trong tất cả các file Part.
    - So sánh với số lượng tương ứng trong file Final.
    - **Stopping Rule**: Nếu số lượng không khớp, PHẢI thực hiện lại khâu Injection cho phần bị thiếu. TUYỆT ĐỐI không bàn giao tài liệu lỗi.
6. **Pass 6: Qualitative Grounding Check — Section 7 (theo R3):** Audit định lượng KHÔNG phát hiện được state bịa. Kiểm thêm Section 7:
    - Nếu Step 01 verdict = `stateless` → Section 7 PHẢI là dòng khai báo stateless, KHÔNG được có StateDiagram. Có diagram → R7 Stopping, trả lại Agent 2.
    - Nếu có StateDiagram → mọi state PHẢI truy về một entity + giá trị status trong `Stateful Entity Verdict` (Step 01). State nào không truy được (vd map từ WBS action như `VALIDATED`) → R7 Stopping, yêu cầu Agent 2 sửa hoặc khai báo stateless.

## 3. Dual-Write Output (Canonical + Archive)

Sau khi Pass 5 PASS, Agent 0 PHẢI:

1. `mkdir -p {planning_artifacts}/archive/` (idempotent).
2. Detect `N_next`: list `{planning_artifacts}/archive/{module_name}_techspec_v*.md` → `max(N) + 1` (hoặc `1` nếu rỗng).
3. Ghi 2 file (cùng nội dung):
    - **Canonical:** `{planning_artifacts}/{module_name}_techspec.md` (overwrite — latest pointer).
    - **Archive:** `{planning_artifacts}/archive/{module_name}_techspec_v{N_next}.md` (new snapshot history).
4. Báo user: "✅ Đã ghi canonical `{module_name}_techspec.md` + archive `_v{N_next}.md`".

## 4. Đầu ra yêu cầu
- **Canonical TechSpec:** `{planning_artifacts}/{module_name}_techspec.md` (latest, overwrite mỗi run).
- **Archive snapshot:** `{planning_artifacts}/archive/{module_name}_techspec_v{N_next}.md` (history).
- **Bảng đối soát định lượng (Quantitative Audit)**:
    - [Diagram/Table Type] | [Count in Parts] | [Count in Final] | [Status (Match/Mismatch)].
