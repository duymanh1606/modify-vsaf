# Quy Tắc Kiểm Đếm Độ Bao Phủ (Coverage Checklist Rule)

> **Mục đích:** Quy định cách kiểm đếm độ phủ (Math Forcing) để vét cạn 100% tài liệu đầu vào ở Step 02. **Lưu ý:** plan KHÔNG chứa checklist `[ ]` (Chốt 8 đã bỏ) — Step 02 chỉ ghi công thức phân rã (X); mỗi rule-case được bung 1-1 thành dòng testcase ở Step 03 (Math Check `X = Y`).

---

## 1. Công thức tính số lượng case (Mathematical Forcing)
Bắt buộc in ra công thức toán học (Math Forcing) tính tổng số lượng testcase dự kiến (`X`) + giải thích sơ bộ, ngay trong plan Step 02.
- *Ví dụ:* `3 inputs x (1 Required + 2 BVA + 2 Special chars) = 15 cases`.
- **Ràng buộc số lượng:** Số dòng testcase ở bảng 11 cột (bung ở Step 03) bắt buộc phải $\ge$ kết quả công thức này (`X`). Cấm ghi dấu ba chấm `...` hoặc `tương tự`.

---

## 2. Quy tắc vét cạn các mảng kiểm thử (Exhaustive Coverage)

### Ràng buộc Nạp Rule Tệp Tin (File-Level Rule Ingestion - BẮT BUỘC)
- Cấm tự suy luận chung chung về EP/BVA hay UI/UX.
- **Bắt buộc** phải lập bảng ánh xạ (Mapping Table): *(bề mặt `ui`)* liên kết từng control, nút bấm, nhóm lựa chọn trên màn hình · *(bề mặt `service`)* liên kết từng field request / operation / mã lỗi — với các tệp tin rule chi tiết tương ứng trong `references/kbkt-generation/` (ui: `02-input/*`, `03-selection/*`, `07-save-cancel/*` · service: `10-be/*` + `02-input/*`,`03-selection/*` diễn giải ở tầng payload theo [service_surface_rules.md §2.4](../../../principles/service_surface_rules.md)).
- **Bắt buộc** gọi tool `view_file` đọc toàn bộ nội dung của các tệp tin rule đã ánh xạ.
- **Bắt buộc** dịch chính xác, 1-1 không tóm tắt, từng số thứ tự/trường hợp trong danh sách *"Testcase Bắt Buộc"* của tệp tin rule đó thành **1 dòng testcase** tương ứng với control thực tế (bung ở Step 03). Quy tắc này là bắt buộc để tránh thiếu hụt case.

### Mảng Button / Action (BẮT BUỘC vét cạn)
- Liệt kê **đầy đủ MỌI button/nút bấm** hiển thị trong bề mặt đang test (không bỏ sót button enable nào). Gắn mỗi button với rule tương ứng: Lưu/Submit → `07-save-cancel/save-button-rule.md`; Hủy/Đóng/Back → `07-save-cancel/cancel-button-rule.md`; còn lại (điều hướng/action nghiệp vụ) → `07-save-cancel/action-button-rule.md`.
- **Vét cạn button phải quét MỌI STATE, không chỉ state mặc định.** Rất nhiều button chỉ xuất hiện **bên trong một state điều kiện** (banner lỗi/suy giảm, empty-state, loading, dialog xác nhận) và **không nằm trong bảng UI-Controls** của `_detailed_design` — vì DD mô tả chúng như một thuộc tính/hành vi của component cha (vd *"Action [Thử lại]: re-fetch"* nằm trong banner). Những button lồng này (điển hình: **[Thử lại]/Retry**, CTA empty-state như **[Tạo mới]/[Tinh chỉnh bộ lọc]**, nút trong confirm-dialog) **BẮT BUỘC được enroll vào danh sách button** và nhận đủ cụm testcase của rule tương ứng — KHÔNG được coi là "phần hiển thị của state" rồi chỉ assert render. Khi lập inventory, duyệt lần lượt: default → empty → error/5xx → degraded → loading → dialog, và bóc mọi button trong mỗi state ra.
- Với **mỗi button enable**, bắt buộc có tối thiểu: (1) case click → điều hướng/xử lý đúng nghiệp vụ (đích đến cụ thể), và (2) case click nhiều lần liên tiếp (chống double-submit/idempotency). Cấm gộp nhiều button vào một dòng.
- **Nút Retry ("Thử lại") — cụm coverage riêng (BẮT BUỘC):** với mỗi nút retry (trên banner lỗi/degraded/timeout hoặc toast), tối thiểu 3 dòng độc lập: (a) click retry → hành động lặp lại thành công (banner/lỗi biến mất, dữ liệu render); (b) click retry mà **vẫn lỗi lần nữa** → banner/lỗi **giữ nguyên** (không biến mất), state an toàn, cho phép bấm lại; (c) **giới hạn số lần retry** nếu spec nêu (vd "retry thủ công tối đa N lần") → sau N lần chặn không cho retry, đối soát đúng N request phát sinh. Nếu spec không nêu giới hạn/đích retry → tạo Q&A, không tự đoán.

### Mảng Luồng Nghiệp Vụ (Business Logic)
- Rà soát file mô tả `SLICE` và phần Logic (`_detailed_design`).
- **Quy tắc tổ hợp (Decision Table):** Nếu hệ thống gọi $N$ API song song hoặc tương tác $M$ hệ thống con, bắt buộc lập ma trận tổ hợp trạng thái phản hồi ($2^N$ hoặc $3^N$ dòng) để vét cạn các trường hợp lỗi một phần (Partial Failure). Cấm gộp chung thành một lỗi hệ thống chung chung.
- **Chống gộp nhóm đa nguồn (Cross-Source Combinatorial Testing):** Khi dữ liệu đến từ nhiều nguồn/hệ thống khác nhau (Multi-Source), đây là phần logic nghiệp vụ/chức năng, cấm đưa vào validate trường đơn. Bắt buộc phân rã thành các case trong phần chức năng:
  1. Chỉ thao tác với 1 nguồn A.
  2. Thao tác với nhiều item trong cùng nguồn A.
  3. Kết hợp chéo nguồn A + B.
  4. Chọn toàn bộ tất cả các nguồn (Select All).

### Mảng Validation (Field-Level)
- Bắt buộc lấy đầy đủ danh sách các case từ các tệp tin rule của từng control đã ánh xạ trong Bảng Ánh Xạ Rule (ví dụ: `02-input/...`, `03-selection/...`). Tuyệt đối không tự suy diễn hay viết chung chung.

### Mảng UI & Accessibility *(chỉ bề mặt `ui`)*
- Bắt buộc nạp và kiểm tra đầy đủ các tệp tin rule về UI/UX được ánh xạ (ví dụ: `01-ui/...`). Phủ toàn bộ các trường hợp phím tắt, zoom giao diện, trạng thái mặc định theo các tệp tin đó.
- *(bề mặt `service` — no-UI)* Mảng này **N/A**; thay bằng **Mảng Hợp đồng & Request Validation**: mỗi field request × rule tầng payload (required/length/format/enum), + conformance schema/HTTP status của happy-path, + state machine transition + idempotency/dedupe (theo [service_surface_rules.md §2.6](../../../principles/service_surface_rules.md)).

### Mảng Kháng lỗi & Bảo mật
- Nạp tệp tin bảo mật được ánh xạ (ví dụ: `02-input/security-input-rule.md`) và kết hợp các mã lỗi API (401, 403, 409, 5xx) trong tài liệu thiết kế chi tiết để sinh checklist bảo mật, kháng lỗi tương ứng.
- Spec có catalog mã lỗi kèm hành vi phản hồi per-code → nạp `06-validation/error-response-behavior-rule.md`, phủ mỗi (mã lỗi × side-effect) thành 1 case.
