# Phạm vi: WBS (xương sống toàn hệ) + đánh dấu phần xây mới (tùy chọn)

## Mô hình nguồn (đã chốt)
Tài liệu Tổng quan nghiệp vụ mô tả **bức tranh toàn hệ**. Nguồn theo thứ tự:
1. **`architecture_design.md`** (HLD) — C4 context/container, ERD, security zoning, mô hình tổng quan.
2. **`project_wbs.md`** — **xương sống phân rã chức năng toàn hệ** (§6 cây phân rã bám cái này).
3. **PRD / Epics** — bối cảnh, vấn đề, mục tiêu kinh doanh (thứ code/thiết kế không nói).
4. (fallback) **source code** — suy actor/flow/ERD khi tài liệu thiếu; xem [extract-from-code.md](extract-from-code.md).

## Đánh dấu "phần xây mới" (tùy chọn — chỉ khi người dùng chọn xem 2 lớp)
`project_wbs.md` thường **TRỘN** brownfield AS-IS (đã có) + phần xây mới của dự án hiện tại. Nếu người dùng muốn
**phân biệt** hai lớp trên cây §6, nguồn xác định phần xây mới **chính xác** là:

`NTAPP-output/Stage_4_Design/detailed_design/feature_design_parts/<ID>/` — **mỗi thư mục con = 1 feature THỰC SỰ
được thiết kế để build**. Đọc `f0_overview_part.md` mỗi feature lấy tên/loại (backend-service / frontend-app /
integration-contract)/mục đích. (Có thể tham chiếu thêm slice plan `Stage_2_Architecture/slices/`.)

## Tín hiệu brownfield vs greenfield trong HLD/WBS
- Bảng phạm vi §1.2 HLD thường có cột "Brownfield/Greenfield".
- Bảng "Tổng số WBS items" tách theo version (vd v3.0 AS-IS vs v3.1+ bổ sung) và theo `module_type`.
- Nhãn trong tên cụm / mô tả (vd "service mới", "brownfield extend").

## Cách xử lý trong skill (BƯỚC 2 hỏi phạm vi)
- **Mặc định — Toàn hệ theo WBS:** cây §6 dựng từ `project_wbs.md` (bức tranh đầy đủ), **không** phân lớp AS-IS/mới. PRD/epic cho bối cảnh.
- **Tùy chọn — Toàn hệ 2 lớp:** thêm tách nhánh **A** "Nền tảng sẵn có (brownfield)" (tô xám, mức cụm — đọc WBS) + nhánh **B** "Xây mới" (tô màu theo 3 loại, mức feature — đọc `feature_design_parts`). Highlight phần xây mới trên §2 (viền nhấn).
- **Tùy chọn — Chỉ phần xây mới:** chỉ nhánh B (`feature_design_parts`).
- Nếu KHÔNG có `feature_design_parts` (dự án chưa tới Stage 4) mà người dùng vẫn muốn 2 lớp → dùng nhãn greenfield trong WBS để suy, **đánh dấu `[Cần xác nhận]`**.
- Khi mơ hồ giữa các mức → **HỎI**, không mặc định lấy hết hay bỏ sót.
