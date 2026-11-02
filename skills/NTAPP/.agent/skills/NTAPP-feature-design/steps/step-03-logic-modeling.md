# STEP 03: LOGIC & EXECUTION MODELING

> **Acting as:** [Agent F1 — Logic Specialist](../agents/agent_f1_logic_specialist.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R4 (Traceability WBS→Logic Matrix), R5 (Consistency naming với F3).

## 0. Skip Condition (theo Execution Matrix)

| `id_type` | Action |
|---|---|
| `feature_id` (BE) | ✅ RUN — design Logic Matrix + Sequence Diagram backend. |
| `screen_id` (FE) | **SKIP** — FE screen consume BE logic, không own. F0 SKIP action (không tạo `f1_logic_part.md`), tiếp tục **Next**. |
| `widget_id` (FE) | **SKIP** — widget consume BE logic. F0 SKIP action (không tạo `f1_logic_part.md`), tiếp tục **Next**. |

## 1. Mục tiêu
Mô hình hóa "bộ não" thực thi của BE feature tại Section 3 (Backend Workspace).

## 2. Nguyên liệu đầu vào (Input)
- **Section 1 (Tổng quan)**: Do Agent F0 chắt lọc tại Step 01.
- **L2 TechSpec** (`{module}_techspec.md` §11-12): persistence schema (§11 Logical Data Model) + API contract (§12 Interface Contracts).

## 3. Chỉ thị thực thi
1. **Sequence Diagram (3.1)**: Sử dụng Mermaid SequenceDiagram để mô phỏng toàn bộ vòng đời thực thi: **Nhận Input -> Validate -> Xử lý (Process) -> Tích hợp/Ghi dữ liệu -> Trả kết quả/Hoàn tất task**. Đảm bảo thể hiện rõ tương tác giữa các lớp (Controller, Service, Repository).
2. **Logic Matrix (3.2)**: 
   - Phân rã logic thành từng bước (Step-by-step).
   - Đặc tả 100% các rẽ nhánh IF-ELSE cho cả luồng thành công và luồng lỗi (Exception handling).
   - Tham chiếu WBS ID cho từng bước xử lý.

## 3. Đầu ra yêu cầu
- Section 3 hoàn chỉnh với Mermaid code và bảng Logic Matrix.
- **Lưu trữ:** Bản thảo Markdown lưu tại `{intermediate_folder}/f1_logic_part.md`.
- Tuyệt đối không mô tả giao diện (UI) tại đây.

## [GATE] — Skip-decision (⛔ quyết định trước khi sang Next)

- `id_type == feature_id` → **RUN** action, đảm bảo Section 3 + `f1_logic_part.md` đã ghi (Sequence Diagram + Logic Matrix, tuyệt đối không mô tả UI).
- `id_type ∈ {screen_id, widget_id}` → **SKIP** action (không tạo `f1_logic_part.md`).
- Traversal tuyến tính: luôn sang Step 04 (Step 04 tự SKIP/PROMPT theo Skip Condition §0 của nó).

**Next:** Read fully and follow `./step-04-data-integration.md`
