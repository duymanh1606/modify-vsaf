# Kỹ Thuật Thiết Kế Kịch Bản (ISTQB Test Design Standards)

> **Mục đích:** Hướng dẫn áp dụng các kỹ thuật thiết kế testcase hộp đen tiêu chuẩn vào dự án NTAPP.

---

## 1. Áp dụng Kỹ thuật Hộp đen (Black-box)

1. **Phân vùng tương đương (EP):** Chia tập dữ liệu đầu vào thành hợp lệ và không hợp lệ. Chọn 1 giá trị đại diện cho mỗi phân vùng.
2. **Phân tích giá trị biên (BVA):** Xác định các biên cứng trong phần Dữ liệu và phần Giao diện để test các giá trị: `Min-1`, `Min`, `Min+1`, `Max-1`, `Max`, `Max+1`, Null, trống, khoảng trắng.
3. **Bảng Quyết Định (Decision Tables):** Áp dụng cho các logic kết hợp nhiều điều kiện IF-THEN phức tạp trong phần Logic (ví dụ: các API song song phản hồi thành công/thất bại chéo nhau).
4. **Kiểm thử Tổ hợp Đa Nguồn:** Áp dụng khi dữ liệu tổng hợp từ nhiều nguồn phân loại khác nhau. Bắt buộc test: Đơn nguồn, Đa nguồn cùng loại, Tổ hợp chéo loại, và Chọn tất cả (Select All).
5. **Chuyển đổi Trạng thái (State Transition):** Bao phủ vòng đời trạng thái của đối tượng nghiệp vụ (Nháp -> Chờ Duyệt -> Duyệt / Từ Chối) và vòng đời của JWT Token/Cookie.
6. **Phỏng đoán lỗi (Error Guessing):** Test SQL Injection, XSS trên các bộ lọc tìm kiếm; mất kết nối Redis; timeout API downstream.

---

## 2. Chiến lược nâng cao đặc thù NTAPP
- **Dynamic Form Behavior:** Vét cạn các luồng E2E theo những Profile biến thể khác nhau. Test luồng thay đổi Profile giữa chừng (Context Switching) để kiểm tra logic Clear/Reset dữ liệu.
- **Integration & Kafka:** Mô tả rõ trong expected result việc sinh Topic nào, payload ra sao và hệ thống consumer phản hồi thế nào (Không ghi chung chung).
- **Declarative Steps:** Viết các bước test tập trung vào mục tiêu nghiệp vụ (ví dụ: "Đăng nhập bằng tài khoản Admin") thay vì mô tả quá chi tiết thao tác click từng nút cứng nhắc, giúp kịch bản không bị lỗi thời khi thay đổi UI nhẹ.
