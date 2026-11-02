# Compliance Audit Rule (Rà Soát Tính Tuân Thủ)

## Mục đích
Quy định chi tiết các tiêu chí kiểm tra tính tuân thủ cấu trúc và nội dung kỹ thuật cơ bản của file kịch bản kiểm thử.

## 3 Tiêu Chí Rà Soát Tính Tuân Thủ

### ⚙️ Tiêu chí 1: Tuân thủ cấu trúc kịch bản chức năng người dùng cuối (End-User Scenarios)
- **Đối tượng:** Các kịch bản kiểm thử thao tác trực tiếp trên giao diện người dùng (ví dụ: login form, input data form, search list screen...).
- **Yêu cầu:** Kịch bản phải được tổ chức và bao phủ đầy đủ cả 3 nội dung sau:
  - 🖥️ **Giao diện (UI):** Kiểm tra hiển thị, bố cục, font chữ, trạng thái default của các control (checkbox, input, select box...), tính responsive và căn chỉnh.
  - 💼 **Chức năng (Functional):** Kiểm tra logic nghiệp vụ khi click nút, chuyển trang, submit dữ liệu, các luồng happy/negative.
  - 🔒 **An toàn thông tin (Security - nếu có):** Kiểm thử phân quyền truy cập (Authorization), mã hóa dữ liệu nhập (ví dụ: password hiển thị dạng `*`), tự động timeout session.
- **Lỗi cần bắt:** Kịch bản người dùng cuối bị thiếu một trong ba nội dung trên (ví dụ: chỉ test chức năng mà bỏ qua kiểm tra hiển thị giao diện hoặc bỏ qua các case an toàn thông tin cơ bản).

### 🌐 Tiêu chí 2: Tuân thủ cấu trúc kịch bản tiến trình/API (Backend / API Scenarios)
- **Đối tượng:** Các kịch bản kiểm thử gọi API trực tiếp, chạy các tiến trình ngầm, hoặc các service kết nối downstream.
- **Yêu cầu:** Kịch bản phải bao phủ đầy đủ cả 2 nội dung sau:
  - ⚙️ **Chức năng (Functional):** Kiểm tra định dạng API Payload, các mã code trả về (`200 OK`, `400 Bad Request`, `500 Internal Error`), kiểm tra lưu trữ DB tương ứng, logic xử lý lỗi nghiệp vụ và lỗi downstream.
  - 🔒 **An toàn thông tin (Security - nếu có):** Kiểm tra JWT token validation (expired token, invalid token, missing Bearer header), kiểm tra SQL Injection, Manipulation URL, CSRF hoặc dữ liệu nhạy cảm bị rò rỉ trong API payload/response.
- **Lỗi cần bắt:** Kịch bản API thiếu kiểm thử an toàn thông tin (chỉ test happy path của API mà không thử bypass token hoặc inject payload độc hại).

### 📝 Tiêu chí 3: Sự hiện diện của 5 thông tin bắt buộc trong từng Testcase
- **Yêu cầu:** Bất kể định dạng kịch bản như thế nào, từng dòng testcase trong bảng bắt buộc phải điền đầy đủ và rõ ràng 5 thông tin cốt lõi sau:
  1. **Mục đích kiểm thử:** Mô tả ngắn gọn kiểm thử cái gì (ví dụ: `Kiểm tra hiển thị form đăng ký merchant`).
  2. **Trường hợp kiểm thử (Test Case Title):** Mô tả bối cảnh và điều kiện test (ví dụ: `Đăng ký merchant mới với đầy đủ thông tin hợp lệ`).
  3. **Data test (Dữ liệu kiểm thử):** Ghi rõ dữ liệu nhập cụ thể (ví dụ: `merchant_name: Cửa hàng Hoa Sen`, `phone: 0987654321`). Tuyệt đối không để trống hoặc dùng placeholder chung chung.
  4. **Các bước thực hiện (Test Steps):** Mô tả từng bước thao tác vật lý, đánh số thứ tự rõ ràng (Step 1, Step 2...).
  5. **Kết quả mong muốn (Expected Result):** Mô tả chi tiết kết quả kỳ vọng ở các tầng UI, DB, Log và ghi nợ/có ví/ngân hàng nếu có.
- **Lỗi cần bắt:** Bất kỳ testcase nào bị để trống hoặc ghi chung chung một trong năm thông tin bắt buộc trên.
