# Coverage Audit Rule (Rà Soát Độ Bao Phủ)

## Mục đích
Thực hiện đối chiếu chéo (Cross-check) chi tiết kịch bản kiểm thử với các tài liệu Specs nguồn nhằm đảm bảo tính đầy đủ, độ bao phủ nghiệp vụ, hiệu năng và bảo mật.

## Các Tiêu Chí Rà Soát Độ Bao Phủ

### 📊 Tiêu chí 1: Kiểm tra tính Đầy đủ (Completeness Audit)
Bạn phải xác minh tính đầy đủ trên 5 khía cạnh nghiệp vụ và kỹ thuật:

1. **Common Testcase Giao diện:**
   - **Yêu cầu:** Kịch bản kiểm tra giao diện phải bao phủ đầy đủ các trường hợp kiểm tra quy định trong *common testcase* (kiểm tra font, màu sắc, bố cục, căn chỉnh, validate biên ký tự, regex format, leading/trailing space, whitespace-only, và xử lý ký tự đặc biệt `<>&"'`).
   - **Lỗi cần bắt:** Bỏ sót kịch bản validation hoặc kiểm tra hiển thị cơ bản của bất kỳ UI control nào.

2. **Bao phủ Yêu cầu Nghiệp vụ (Specs Coverage):**
   - **Yêu cầu:** Kịch bản kiểm tra chức năng phải bao phủ 100% yêu cầu nghiệp vụ được mô tả trong Specs hoặc phiếu yêu cầu nghiệp vụ (Business Requirements).
   - **Lỗi cần bắt:** Thiếu kịch bản cho bất kỳ luồng nghiệp vụ rẽ nhánh, luồng ngoại lệ hoặc logic nghiệp vụ nào được mô tả trong phần Logic (`_detailed_design`).

2b. **Bao phủ Button / Action (Button Coverage):**
   - **Yêu cầu:** MỌI button enable hiển thị trong chức năng phải có testcase click → điều hướng/xử lý đúng nghiệp vụ (đích đến cụ thể), và testcase click nhiều lần liên tiếp (chống double-submit/tạo request trùng/mở chồng dialog).
   - **Lỗi cần bắt:** Bỏ sót button enable không có case click; case click ghi đích đến mơ hồ ("điều hướng đúng"); thiếu case click nhiều lần cho button gây tác động nghiệp vụ.

3. **Môi trường triển khai cụ thể:**
   - **Yêu cầu:** Kịch bản kiểm thử bắt buộc phải ghi rõ nội dung môi trường triển khai chi tiết ở cột Môi trường/Công cụ test, bao gồm: **loại trình duyệt** (ví dụ: Google Chrome, Microsoft Edge, Firefox, Safari) và **version tương ứng** (hoặc ghi rõ *Latest version*).
   - **Lỗi cần bắt:** Chỉ ghi chung chung `Môi trường Staging` hoặc `Môi trường Web` không có thông tin chi tiết trình duyệt/version.

4. **Kịch bản kiểm thử hồi quy (Regression Testing):**
   - **Yêu cầu:** Với các nghiệp vụ thuộc luồng **nâng cấp, sửa đổi hệ thống**, bắt buộc phải có các testcase kiểm thử hồi quy (Regression) cho các chức năng, phân hệ hoặc luồng dữ liệu bị ảnh hưởng gián tiếp bởi lần nâng cấp này (dựa trên bảng Impact Analysis).
   - **Lỗi cần bắt:** Thiếu các ca test hồi quy cho các chức năng xung quanh phân hệ được nâng cấp sửa đổi.

5. **Mô tả tác động Tài khoản Ngân hàng / Tài khoản Ví kênh:**
   - **Yêu cầu:** Với các nghiệp vụ có tác động tới tài khoản ngân hàng hoặc tài khoản ví kênh (ví dụ: rút tiền, nạp tiền, thanh toán, đối soát), cột **Kết quả mong muốn** bắt buộc phải mô tả chi tiết:
     - **Tài khoản nào bị GHI NỢ (Debit):** Số tiền ghi nợ cụ thể, số dư sau khi ghi nợ.
     - **Tài khoản nào được GHI CÓ (Credit):** Số tiền ghi có cụ thể, số dư sau khi ghi có.
     - Trạng thái hạch toán kế toán tương ứng.
   - **Lỗi cần bắt (Nghiêm trọng):** Thiếu mô tả ghi nợ/ghi có tài khoản đối với từng tình huống kiểm thử liên quan đến tài chính.

### ⚡ Tiêu chí 2: Kiểm tra tính Hiệu năng (Performance Audit)
- **Yêu cầu:** Đối với các nghiệp vụ có yêu cầu phi chức năng về hiệu năng (ví dụ: xử lý đồng thời, thời gian phản hồi API phải dưới 500ms, khả năng chịu tải của hệ thống), kịch bản kiểm thử bắt buộc phải có các testcase kiểm tra hiệu năng cụ thể (nêu rõ công cụ kiểm thử như JMeter/k6, số lượng concurrent users, và tiêu chí đánh giá).
- **Lỗi cần bắt:** Bỏ sót kịch bản hiệu năng đối với các nghiệp vụ có yêu cầu hiệu năng cao.

### 🔒 Tiêu chí 3: Kiểm tra tính Bảo mật (Security Audit)
- **Yêu cầu:** Kịch bản kiểm thử bắt buộc phải bao phủ các ca kiểm tra lỗi bảo mật cơ bản cho toàn bộ các trường nhập liệu tự do, thanh tìm kiếm, URL và API endpoint:
  1. **SQL Injection:** Inject payload độc hại (`' OR 1=1--`, v.v.) vào input fields và API endpoint.
  2. **Cross-Site Scripting (XSS):** Nhập các thẻ script (`<script>alert(1)</script>`, v.v.) để kiểm tra escape HTML.
  3. **Manipulation URL:** Thay đổi tham số ID trên thanh địa chỉ trình duyệt (ví dụ: đổi `?id=100` thành `?id=101`) để kiểm tra lỗi phân quyền ngang (IDOR - Insecure Direct Object Reference) và kiểm tra lỗi rò rỉ dữ liệu.
  4. **Cross-Site Request Forgery (CSRF):** Kiểm tra tính hợp lệ của Anti-CSRF Token hoặc kiểm tra SameSite cookie attribute trên các request nhạy cảm (POST/PUT/DELETE).
- **Lỗi cần bắt:** Thiếu bất kỳ ca kiểm tra lỗi bảo mật cơ bản nào (SQLi, XSS, Manipulation URL, CSRF) trong bộ kịch bản kiểm thử.
