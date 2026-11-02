# STEP 04: DATA & INTEGRATION

> **Acting as:** [Agent F2 — Test Data Specialist](../agents/agent_f2_test_data_specialist.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fab từ L2 schema), R5 (Consistency entity name), R10 (Inheritance L2 ERD).

## 0. Skip Condition (theo Execution Matrix)

| `id_type` | Action |
|---|---|
| `feature_id` (BE) | ✅ RUN — design field mapping + entity schema + integration error codes. |
| `screen_id` (FE) | **SKIP** — screen không own data state. F0 SKIP action (không tạo `f2_data_part.md`), tiếp tục **Next**. |
| `widget_id` (FE) | ⚠️ **PROMPT user:** "Widget `{id}` có own local state schema riêng không (vd: form draft, local cache)? [y/n]" — yes → RUN (scope local state), no → SKIP. |

## 1. Mục tiêu
Xác lập "ngôn ngữ chung" về dữ liệu và các điểm chạm tích hợp tại Section 4.

## 2. Nguyên liệu đầu vào (Input)
- **Logic Matrix (`f1_logic_part.md`)**: Để lấy danh sách các tham số API và logic rẽ nhánh. (Chỉ có nếu `id_type == feature_id`.)
- **UI Blueprint (`f3_ui_part.md`)**: Để lấy danh sách các trường hiển thị. (Chỉ có nếu `id_type ∈ {screen_id, widget_id}`.)
- **L2 TechSpec ERD** (§11 Logical Data Model — §11.1 ERD): Schema entity baseline.

## 3. Chỉ thị thực thi
1. **Field Mapping (4.1)**: Ánh xạ 100% các trường dữ liệu từ UI lên Database.
   - Chỉ rõ Type, Format, Mapping Column.
2. **Integration Error Codes (4.2)**: 
   - Liệt kê mã lỗi từ các Module liên quan.
   - Giải thích ý nghĩa lỗi để FE có thể hiển thị thông báo tương ứng.
3. **Persistence Write-Spec (4.3)**: Với MỖI thao tác ghi (INSERT/UPDATE/DELETE) lấy từ Logic Matrix (`f1_logic_part.md`), đặc tả theo bảng template §4.3 (cột + giá trị + nguồn).
   - **BẮT BUỘC** liệt kê cả field hệ thống tự gán không có nguồn UI (`status`, `created_at`, FK từ context...).
   - Nguồn giá trị theo enum chuẩn: Request/Input · Hằng số · Tính toán · Query/Lookup · Context/Session · System.
   - Mọi field phải có entity origin từ L2 TechSpec §11 (R4).
4. **Schema Spec**: Định nghĩa cấu trúc JSON/API cho tính năng.

## 3. Đầu ra yêu cầu
- Section 4 hoàn chỉnh trong Master Detailed Design.
- **Technical Data Samples**: Payload mẫu cho các trường hợp biên, sẵn sàng bàn giao cho Agent F4 (QA).
- **Lưu trữ:** Bản thảo Markdown lưu tại `{intermediate_folder}/f2_data_part.md`.
- Đảm bảo tính nhất quán với Logical ERD ở Level 2.

## [GATE] — Skip / PROMPT decision (⛔ quyết định trước khi sang Next)

- `id_type == feature_id` → **RUN** action, đảm bảo Section 4 + `f2_data_part.md` đã ghi (field mapping §4.1 + error codes §4.2 + **Persistence Write-Spec §4.3** + Technical Data Samples cho F4).
- `id_type == screen_id` → **SKIP** action (không tạo `f2_data_part.md`).
- `id_type == widget_id` → ⚠️ **PROMPT user (PAUSE & WAIT):** "Widget `{id}` có own local state schema riêng không (vd: form draft, local cache)? [y/n]" — yes → RUN (scope local state), no → SKIP.
- Traversal tuyến tính: luôn sang Step 05 (Step 05 luôn RUN, scope theo part đã tạo).

**Next:** Read fully and follow `./step-05-qa-protocol.md`
