# NTAPP Core Compliance & Anti-Patterns

## Mục đích
Tài liệu này quy định các quy tắc cốt lõi (Iron Rules) và chống mẫu (Anti-Patterns) đặc thù của dự án NTAPP khi sinh kịch bản kiểm thử (KBKT).

---

## 1. Quy tắc Bất Biến (Iron Rules)

### 1.1. Zero-Summarization & Zero-Fabrication
- **Không tóm tắt**: Giữ nguyên 100% chi tiết kỹ thuật, cấu trúc JSON sample, schema dữ liệu.
- **Không tự chế**: Cấm tự chế dữ liệu hoặc mock giả định. Sinh test data phải dùng dữ liệu kiểm thử cụ thể, tường minh, có cấu trúc thực tế. (Xem thêm: [no-hallucination-rule.md](./no-hallucination-rule.md))

### 1.2. Traceability (Truy vết)
- Từng dòng kịch bản kiểm thử phải chỉ rõ link liên kết tới dòng logic của BE (phần Logic trong `_detailed_design`) hoặc UI Control của FE (phần Giao diện trong `_detailed_design`).
- Đảm bảo 100% các dòng logic matrix và mã lỗi trong specs được bao phủ trọn vẹn trong test cases.
- **Tag bắt buộc**: Mỗi testcase cần gắn tag phân loại rõ ràng:
  - `[HappyPath]`
  - `[Negative]`
  - `[Boundary]`
  - `[Validation]`
  - `[Permission]`
  - `[Integration]`
  - `[Regression]`
  - `[ImpactArea]`
  - `[BugRecheck]`

### 1.3. Bảo mật
- Tuyệt đối không đọc trực tiếp file `.env` hoặc ghi lộ lọt credentials.

---

## 2. Quy Tắc Chống Mẫu (Anti-Patterns)

Nghiêm cấm các hành vi sau khi sinh KBKT:
- ❌ **Gộp nhiều bước chạy 1 lần**: Phải tuân thủ quy trình chạy tuần tự từng Mode/Step.
- ❌ **Rút gọn hoặc bỏ sót test case khi mapping sang bảng**: Phải map đầy đủ 100% kịch bản kiểm thử đã thiết kế sang bảng 10 cột, không gộp hay cắt bớt.
- ❌ **Sinh tất cả test cases 1 lần cho hệ thống lớn**: Phải chia tách thành từng module/id nhỏ để xử lý cuốn chiếu chất lượng cao.
- ❌ **Test Steps mơ hồ, không ghi rõ dữ liệu nhập**: Từng bước kiểm thử phải mô tả rõ thao tác nhập liệu gì, chọn gì, với dữ liệu cụ thể nào.
- ❌ **Sinh kịch bản hời hợt, gom nhóm (Superficial Generation)**: NGHIÊM CẤM việc gom chung các trường hợp kiểm thử khác biệt vào một kịch bản duy nhất hoặc chỉ sinh ra số lượng ít ỏi các kịch bản bề mặt. Phải vét cạn toàn bộ luồng rẽ, tổ hợp biến, ranh giới biên (BVA) và kiểm thử chéo để đảm bảo khối lượng testcase cực kỳ chi tiết, cụ thể cho từng trường hợp nhỏ nhất.
- ❌ **Gộp validation nhiều trường vào 1 test case**: Mỗi trường dữ liệu (input field) phải có các Test Case validation riêng biệt.
- ❌ **Dùng chung 1 bộ validation cho tất cả fields**: Phải thiết kế validation riêng dựa trên đặc tính của từng trường dữ liệu (Email ≠ Phone ≠ Date ≠ Text).
- ❌ **Bỏ qua security validation cho text/textarea fields**: Phải bao phủ kiểm thử bảo mật cơ bản như SQL Injection, XSS trên các trường nhập liệu tự do.
- ❌ **Không liệt kê danh sách fields trước khi sinh validation TCs**: Bắt buộc phải liệt kê đầy đủ danh sách trường thông tin từ UI spec trước rồi mới tiến hành sinh các ca kiểm thử validation tương ứng.
- ❌ **Sao chép KBKT nhúng sẵn ở phần Đảm bảo chất lượng / Kiểm thử của `_detailed_design`**: Được đọc `_detailed_design` để phân tích, nhưng TUYỆT ĐỐI KHÔNG lấy/sao chép/trích xuất các kịch bản kiểm thử (KBKT) đã nhúng sẵn ở phần Đảm bảo chất lượng / Kiểm thử (phần này phải bỏ qua khi đọc). Hệ thống BẮT BUỘC phải thiết kế testcase mới từ đầu dựa trên việc phân tích phần Logic và phần Dữ liệu.
