# Contract & Consistency Gap Rules

Nhóm "so khớp / mâu thuẫn" — chạy ĐỦ; im lặng / lệch → GAP + `[TBD]`.

---

## 1. Contradiction & Core Gaps

Bốn loại gap cơ bản — soi trong từng unit và giữa DD ↔ nguồn.

- **Logic Gaps**: luồng lỗi downstream (PMT/PCM/Policy) chưa định nghĩa, thiếu xử lý lỗi mạng, token Keycloak hết hạn, thiếu logic lưu DB.
- **Parameter Gaps**: trường dữ liệu (phần Dữ liệu) thiếu `maxLength` / format-Regex.
- **UI-Logic Inconsistency**: controls (Giao diện) ↔ biến logic (Logic/Dữ liệu) lệch naming — vd `userId` vs `user_id`.
- **Contradiction Gaps**: cùng ràng buộc (maxLength, enum, tồn-tại param, error-code) lệch giữa nguồn (`_detailed_design` ↔ L2 TechSpec / DD cũ) — vd `maxLength 64` (Giao diện) vs `100` (nơi khác); param còn ở techspec nhưng đã bỏ ở DD → Gap, không tự chọn giá trị.
  - **maxLength** hoà giải 3 điểm: spec ↔ FE `maxlength` attr ↔ BE `@Size(max=)`/cột DB. Lệch cặp nào = GAP (vd FE=100, BE=64, spec=20). FE-attr > BE-limit → testcase drive biên `BE+1` (≥🟡).
- **Navigation / Post-action Routing** (MỖI create/submit/save/cancel/delete): đối chiếu đích điều hướng sau khi thành công giữa mọi mục (Post-condition, bảng control, Navigation-map, luồng UX). Đích khác nhau (vd `redirect /detail/{id}` vs "về List + highlight row") → GAP (≥🟡, 🔴 nếu luồng chính). Khác theo mode (modal A vs page B) mà DD không tách → GAP (thiếu điều kiện).
  - **Side-effect completeness**: liệt kê đủ side-effect mỗi action thành công (thêm/xoá/reorder row; counter/badge; toast; clear draft/localStorage) + kiểm mỗi cái có trong bảng logic tất định, không chỉ Post-condition / ghi chú "inherit". Chỉ ở prose mà vắng bảng logic = GAP (≥🟡, 🔴 nếu là tiêu chí demo — vd badge/count).
- **Cụm "A HOẶC B" chưa-chốt**: quét Post-condition/Expected/bảng tương tác tìm "X HOẶC Y" (/, hay) cho một hành vi tất định (điều hướng, status khởi tạo, thông báo, đích lưu) → GAP + `[TBD]`, PO chốt 1 nhánh hoặc nêu điều kiện.

---

## 2. Cross-Unit Contract Gap

Dựng ma trận contract cross-unit theo khoá dùng chung (field/regex/maxLength, enum + hoa/thường, query param FE↔BE, response field FE↔BE, error-code, cache key); diff mọi unit chạm khoá, lệch = Gap. Bắt cả >1 spec cho 1 surface, và mẫu wireframe ≠ dữ liệu staging thật.

---

## 3. Cross-Document Gap

Đối chiếu nguồn: Module 0 (state registry/ERD, cache key, contract) ↔ techspec ↔ ux_design ↔ PRD (FR/BR). Bắt mâu thuẫn nội bộ 1 tài liệu (vd ux_design 2 mục lệch) + citation "ma" (DD cite mục không tồn tại).

---

## 4. FE↔BE Business-Rule & Guard/Validate Parity

So luật nghiệp vụ 2 nhánh: ai enforce phân quyền/data-scope (FE-only vs BE), enum canonical, luồng hợp lệ (state tạo từ màn nào), partial/ordering, list "count + status". Lệch hành vi (không chỉ tên field) = Gap.

- **FE-guard ↔ BE-validate** (MỖI create/submit/action): FE chặn (nút disabled, min-selection, field required, confirm dialog, empty-state) ↔ BE validate (`@NotNull`/`@Size(min/max)`/required-when/regex/cardinality). Cờ ca FE chặn-BE cho qua & ngược lại. Vét: empty/zero-selection (vd tạo composite khi chưa chọn sub-link), min-cardinality (≥1), nút-disabled, kết quả input rỗng (BE tạo record gì? 400? status nào?). ≥🟡, 🔴 nếu luồng chính / expected mơ hồ. Mỗi mâu thuẫn = 1 GAP riêng.
