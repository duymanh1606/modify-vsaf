# STEP 06: INTERACTION SYNC AUDIT

> **Acting as:** [Agent F0 — Lead Orchestrator](../agents/agent_f0_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R5 (Consistency), R6 (UI↔Logic Sync Gate, Logic↔KBKT Coverage Gate), R7 (Stopping Errors khi drift).

## 1. Mục tiêu
Thực hiện kiểm toán chéo giữa các bản thiết kế thành phần đã được tạo (F3, F1, F2, F4) để đảm bảo tính khép kín và không có sai lệch (Zero-Gap). Đây là chốt chặn cuối cùng trước khi Assembly.

## 2. Nguyên liệu đầu vào (Input — conditional theo part đã tạo)

Theo `id_type` (Execution Matrix workflow §3), một số part KHÔNG tồn tại. Agent F0 PHẢI list part files thực tế trong `{intermediate_folder}` trước khi chạy protocol:

- `f0_overview_part.md` — luôn có
- `f3_ui_part.md` — có nếu `id_type ∈ {screen_id, widget_id}`
- `f1_logic_part.md` — có nếu `id_type == feature_id`
- `f2_data_part.md` — có nếu `id_type == feature_id` HOẶC (`id_type == widget_id` AND user prompted "own state = y")
- `f4_qa_part.md` — luôn có

## 3. Nghị thức Kiểm toán (Audit Protocols — applicable theo part đã có)

### Bảng applicability

| Protocol | Required parts | Áp dụng khi |
|---|---|---|
| P1: UI-Logic Sync | f3 + f1 | Cả 2 part tồn tại (rare — chỉ khi widget vừa có UI vừa có embedded logic) |
| P2: Logic-Data Sync | f1 + f2 | Cả 2 part tồn tại (`feature_id` BE) |
| P3a: Logic-QA Coverage | f1 + f4 | f1 tồn tại (`feature_id` BE) |
| P3b: UI-QA Coverage | f3 + f4 | f3 tồn tại (`screen_id` / `widget_id`) |
| P3c: Data-QA Coverage | f2 + f4 | f2 tồn tại (BE hoặc widget own state) |
| P4: Traceability Audit | f0 + ≥1 specialist part | Luôn áp dụng |

**Quy tắc skip:** Protocol thiếu required part → mark `N/A (no required input)` trong sync matrix output, KHÔNG fail.

### P1: UI-Logic Sync (Đối soát FE-BE)
- **Check-list:** 
    - [ ] Mọi Action/Event trên UI đều có Logic Step tương ứng.
    - [ ] Mọi Case lỗi trong Logic Matrix đều có Error Message hiển thị trên UI Blueprint.
- **Fail Criteria:** Có nút bấm mà không có logic xử lý, hoặc ngược lại.

### P2: Logic-Data Sync (Đối soát Logic-Tích hợp)
- **Check-list:**
    - [ ] Mọi tham số đầu vào trong Logic Matrix đều có trong bảng Field Mapping của F2.
    - [ ] Mọi mã lỗi (Error Codes) từ API tích hợp đều được Logic Matrix xử lý phân đoạn.
    - [ ] **Write coverage:** Mọi thao tác ghi (INSERT/UPDATE/DELETE) trong Logic Matrix (§3.2) có dòng tương ứng trong Write-Spec §4.3; mọi field ghi có cột `Nguồn giá trị` rõ ràng (không để trống cho field hệ thống tự gán).
- **Fail Criteria:** Logic sử dụng biến/id mà tầng dữ liệu không định nghĩa; hoặc có thao tác ghi nhưng không có dòng Write-Spec §4.3.

### P3a: Logic-QA Coverage (Đối soát Chất lượng BE)
- **Check-list:**
    - [ ] 100% các nhánh rẽ (IF-ELSE/Switch Case) trong Logic Matrix phải có ít nhất một mã KBKT ID (vd: TC_01) dẫn chiếu.
    - [ ] Toàn bộ các Technical Data Samples của F2 đều được sử dụng trong cột "Data Test" của F4.
- **Fail Criteria:** Có logic xử lý nhưng không có kịch bản test bao phủ.

### P3b: UI-QA Coverage (Đối soát Chất lượng FE)
- **Check-list:**
    - [ ] 100% UI Controls (Validation rules) trong f3 phải có ít nhất 1 KBKT scenario ref.
    - [ ] Mọi interaction state (default/hover/disabled/error) trong wireframe phải có test case tương ứng.
- **Fail Criteria:** Có UI control mà không có test case bao phủ trạng thái.

### P3c: Data-QA Coverage (chỉ áp dụng khi f2 tồn tại)
- **Check-list:**
    - [ ] Mọi entity field trong f2 có Technical Sample được dùng trong f4 Data Test column.
    - [ ] Mọi thao tác ghi trong Write-Spec §4.3 có ít nhất 1 KBKT (§5.2) kiểm chứng trạng thái DB sau ghi (cột "Kết quả mong muốn").
- **Fail Criteria:** Có thao tác ghi §4.3 nhưng không có KBKT xác nhận DB state.

### P4: Traceability Audit (Đối soát vết)
- **Check-list:**
    - [ ] Tất cả các Section đều dẫn link tham chiếu về `id` trong WBS unit list tương ứng.
    - [ ] BE feature: ref về L2 TechSpec section. FE screen/widget: ref về Journey Spec §4 (hàng journey table) + Conventions §C-x liên quan.
- **Fail Criteria:** Xuất hiện các thành phần "tự chế" không có căn cứ từ source primary.

## 4. Hành động nếu Audit FAIL
Nếu vi phạm bất kỳ tiêu chí của protocol applicable, Agent F0 **BẮT BUỘC** yêu cầu các Specialist liên quan cập nhật lại bản thảo trước khi tiến hành Step 07.

## 5. Đầu ra yêu cầu
- Bảng **Interaction Sync Matrix** (Ma trận đồng bộ tương tác) hoàn chỉnh nạp vào Master Detailed Design.
- **Lưu trữ:** Bản thảo Markdown lưu tại `{intermediate_folder}/f0_sync_matrix_part.md`.

## [GATE] — Audit PASS (⛔ kiểm trước khi sang Next)

- Mọi protocol *applicable* (theo part đã tạo — §3 applicability table) PASS; protocol thiếu required part → mark `N/A`, KHÔNG fail.
- Nếu vi phạm bất kỳ tiêu chí protocol applicable → **BẮT BUỘC** yêu cầu Specialist liên quan cập nhật lại bản thảo (§4) TRƯỚC khi sang Next. KHÔNG Assembly khi còn drift.
- `f0_sync_matrix_part.md` (Interaction Sync Matrix) đã ghi.

**Next:** Read fully and follow `./step-07-assembly.md`
