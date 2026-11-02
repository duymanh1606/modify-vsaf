# Field-Level Validation Rule

## Mục đích
Đảm bảo sinh các ca kiểm thử validation (kiểm duyệt dữ liệu) chi tiết, đầy đủ và chuyên biệt cho TỪNG loại trường dữ liệu (Field Type) trên UI. Tuyệt đối không dùng chung một kịch bản validation cho tất cả các trường.

## Bảng tra cứu các trạm kiểm duyệt bắt buộc (Validation Checkpoints)

Dựa vào danh sách input fields từ UI Spec (phần Giao diện trong `_detailed_design`), Agent phải áp dụng các trạm kiểm tra tương ứng sau đây:

| Loại Field (Field Type) | 🔍 Các Trạm Kiểm Duyệt Cần Test (Validation Checkpoints) |
| :--- | :--- |
| **Text** <br> *(Name, Address...)* | Required/Optional · Min/Max length · Chỉ khoảng trắng (whitespace-only) · Ký tự đặc biệt (`<>&"'`) · XSS injection (`<script>alert(1)</script>`) · SQL injection (`' OR 1=1--`) · Unicode/Emoji · Khoảng trắng đầu, cuối (trimspace) · Chữ hoa · Chữ thường · Số. |
| **Email** | Format hợp lệ (`user@domain.com`) · Thiếu `@` · Thiếu domain · Domain không hợp lệ · Nhiều `@` · Ký tự đặc biệt trước `@` · Max length · Case sensitivity · Email đã tồn tại (nếu unique) · Khoảng trắng đầu, cuối (trimspace) · Chữ hoa · Chữ thường · Số. |
| **Phone** | Chỉ chấp nhận số · Prefix hợp lệ (ví dụ: `+84`, `0`) · Min/Max length · Chữ cái xen lẫn · Dấu `-`, `.`, khoảng trắng · Mã vùng không hợp lệ. |
| **Date / DateTime** | Format đúng (`dd/MM/yyyy`, ISO...) · Ngày không tồn tại (`31/02`, `30/02`) · Năm nhuận (`29/02/2024`) · Ngày quá khứ / tương lai (tùy business rule) · Giá trị min/max date · Timezone · Kiểm tra mặc định (nếu có). |
| **Number / Currency** | Min/Max value · Số âm · Số 0 · Số thập phân · Ký tự không phải số · Overflow (số cực lớn) · Leading zeros · Định dạng currency (dấu phẩy, dấu chấm). |
| **Dropdown / Select** | Giá trị mặc định · Tất cả options hợp lệ · Option bị disabled · Thay đổi selection · Required validation (chưa chọn). |
| **Checkbox / Radio** | Trạng thái mặc định · Check/Uncheck · Required validation · Nhóm radio (chỉ chọn 1). |
| **File Upload** | File type hợp lệ/không hợp lệ · Max size · File rỗng (`0 KB`) · Tên file có ký tự đặc biệt · Multiple files · Kéo thả vs nút chọn. |
| **Password** | Min/Max length · Yêu cầu ký tự đặc biệt · Yêu cầu chữ hoa/thường · Yêu cầu số · Copy-paste bị chặn? · Hiện/ẩn password · Confirm password khớp/không khớp. |
| **Textarea** | Max length · Line breaks (xuống dòng) · HTML tags · Resize (nếu UI cho phép) · Character counter (nếu có). |

## Yêu cầu khi sinh testcase
- Mỗi trường dữ liệu phải có nhóm testcase validation riêng rẽ.
- Tên testcase phải thể hiện rõ trường nào đang được test và điều kiện kiểm tra là gì (Ví dụ: `Validate trường Số điện thoại khi nhập chữ cái`).
- Dữ liệu test (`Data Test`) phải phản ánh chính xác điều kiện (Ví dụ nhập `abc` cho số điện thoại).
