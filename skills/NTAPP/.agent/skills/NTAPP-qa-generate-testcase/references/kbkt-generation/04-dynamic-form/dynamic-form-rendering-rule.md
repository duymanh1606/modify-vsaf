---
cases_count: 8
---
# Dynamic Form Rendering Rule

## Mục đích

Sinh testcase cho các màn hình có chức năng Render Form động dựa trên một Profile/Cấu hình được chọn (Ví dụ: Form thay đổi tùy theo Category, Template, hoặc Role). Rule này áp dụng cho màn hình **End-user**, không áp dụng cho màn hình Admin cấu hình Rule.

## Điều kiện kích hoạt

Kích hoạt khi màn hình có các trường dữ liệu (field) thay đổi động, phụ thuộc vào một thuộc tính phân loại (Ví dụ: Chọn Template A thì ra 3 fields, chọn Template B thì ra 5 fields và 1 array).

## Nguyên tắc Thiết kế Testcase (Bắt buộc)

### 1. Luồng E2E theo Profile cấu hình (Configuration Variations)
Không được chỉ test từng field đơn lẻ. Bắt buộc test toàn bộ luồng nghiệp vụ dựa trên các Variation của cấu hình:
- **Profile rỗng/chỉ chứa trường tĩnh**: Chọn Profile không có trường động -> Form chỉ hiển thị trường cố định -> Submit thành công.
- **Profile chứa trường động đơn**: Chọn Profile có các trường động dạng Single (không lặp) -> Form hiển thị thêm khối động -> Submit thành công (Lưu JSON/EAV).
- **Profile chứa trường mảng (Array/Repeating Group)**: Chọn Profile có nhóm trường cho phép nhập nhiều lần (`is_array = 1` / Multiple Group) -> Form hiển thị khối động kèm nút Thêm `+` -> Thao tác thêm cụm -> Submit thành công (Lưu JSON Array).

### 2. Context Switching (Thay đổi Profile giữa chừng)
- Kịch bản user chọn Profile A, đã nhập dữ liệu vào các trường động của A.
- Đổi sang Profile B.
- **Kỳ vọng bắt buộc**: Hệ thống phải hiển thị Cảnh báo (nếu có trong spec) và **xóa sạch toàn bộ dữ liệu động** của Profile A, sau đó render lại cấu trúc của Profile B.

### 3. Cascading Dependency Graph (Đổ lùi Đa cấp)
Nếu Profile có cấu hình Rule móc nối (Cascading/Visibility) giữa các trường động, bắt buộc phải có các testcase:
- **Lọc data & Ẩn/hiện (N-level)**: Chọn Cấp 1 thỏa mãn -> Hiển thị/Lọc Cấp 2. Chọn Cấp 2 thỏa mãn -> Hiển thị/Lọc Cấp 3.
- **Reset dây chuyền (N-level)**: Đang có dữ liệu ở cả 3 Cấp. Thay đổi Cấp 1 làm sai điều kiện Cấp 2 -> Hệ thống tự động Ẩn/Xóa data Cấp 2 -> Kéo theo hệ quả Cấp 3 mất điều kiện -> Hệ thống tự động Ẩn/Xóa data Cấp 3.

### 4. Tính toán Validation Ảo (Dynamic Required)
- Nếu một trường được đánh dấu là "Bắt buộc" (Required) nhưng do điều kiện Cascading nên nó đang bị **Ẩn** -> Khi bấm Lưu, hệ thống phải **Bỏ qua lỗi Require** của trường đó.
- Nếu trường đó đang **Hiện** -> Khi bấm Lưu mà bỏ trống, hệ thống phải bắt lỗi Require.

## Điều kiện reject
- Không phân loại được các luồng End-to-End theo từng Variation của cấu hình.
- Bỏ sót kịch bản Reset N-level (Dây chuyền) khi thay đổi giá trị Cấp cha.
