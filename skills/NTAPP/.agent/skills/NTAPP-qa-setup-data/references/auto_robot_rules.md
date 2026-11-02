# QUY TẮC TỰ ĐỘNG HÓA ROBOT FRAMEWORK (ROBOT AUTOMATION RULES)

Tài liệu này quy định các nguyên tắc thiết kế kịch bản, quản lý dữ liệu và đảm bảo chất lượng code cho dự án.

## 1. Page Object Model (POM)
- **Cấu trúc Thư mục**: Tổ chức source code phân mảnh rõ ràng theo cấu trúc Page.
- **Variables Resource (`_variables.resource`)**: Chứa 100% locator của giao diện đang test.
- **Keywords Resource (`_keywords.resource`)**: Chứa các action tương tác UI và các hàm logic kiểm tra.
- **Test Suite (`_tests.robot`)**: Chỉ chứa các High-Level Keywords (luồng nghiệp vụ) và bộ test case. TUYỆT ĐỐI không khai báo định danh ở đây.

## 2. Quản Lý Dữ Liệu Test (Test Data Management)
- **Tách biệt dữ liệu**: Tách dữ liệu khỏi script logic bằng file định dạng `.yaml`, `.json` hoặc áp dụng Data-Driven Testing (DDT).
- **Tính tự sinh**: Các dữ liệu mang tính định danh duy nhất (email, username, ID) bắt buộc phải được sinh ngẫu nhiên (ví dụ bằng Faker) để tránh trùng lặp dữ liệu khi chạy lại.
- **Tiền tố `auto_`**: Mọi định danh kiểu chuỗi sinh ra và ghi vào hệ thống phải BẮT ĐẦU bằng `auto_` (dạng `auto_<nhãn>_{timestamp}`), override qua `AUTO_DATA_PREFIX`. Dùng tiền tố chứ không phải hậu tố để dọn môi trường bằng đúng một mệnh đề `LIKE 'auto\_%'`. Trường chỉ nhận số miễn trừ.
- **Biến môi trường**: Các thông số về Server URL, Browser type, Global Timeout phải được đặt tại file config chung của dự án.

## 3. Quản Lý Thời Gian Chờ (Wait Strategies)
- **Cấm Sleep tĩnh**: Cấm sử dụng từ khóa `Sleep` với thời gian cứng.
- **Smart Wait**: Bắt buộc sử dụng các keyword thăm dò trạng thái như `Wait Until Element Is Visible`, `Wait Until Element Is Enabled`, hoặc `Wait Until Keyword Succeeds`.
- **Cấm Hardcode Timeout**: Khi sử dụng Smart Wait, KHÔNG được hardcode thời gian (VD: `timeout=10s`). BẮT BUỘC phải truyền biến toàn cục đã khai báo (VD: `timeout=${GLOBAL_TIMEOUT}`) từ `GlobalConstants.resource`.

## 4. Quy Tắc Chống Mẫu Nghiêm Cấm (Anti-Patterns)
- ❌ **Tự chế dữ liệu (Data Fabrication)**: Tuyệt đối KHÔNG tự ý sinh ra dữ liệu giả (fake data) khi chưa có file dữ liệu gốc. Mọi dữ liệu (hằng số môi trường, payload test) BẮT BUỘC phải được kế thừa từ file cấu hình hoặc dữ liệu thực tế (từ Manual Testcase, phần Dữ liệu trong `_detailed_design`). Nếu không có, để rỗng hoặc báo lỗi.
- ❌ **Hardcode dữ liệu**: Nhúng thẳng chuỗi text/password/username trực tiếp vào các Test Case.
- ❌ **Locator rác**: Khai báo Xpath/CSS rải rác ngay trong file `.robot` hoặc file `_keywords.resource`.
- ❌ **Thiếu Assertion**: Test steps chỉ thực hiện hành động click/input nhưng không có bước kiểm tra kết quả (thiếu các keyword `Should Be ...`).
- ❌ **Test Case Phụ Thuộc Nhau**: Kịch bản Test 2 không thể chạy nếu Kịch bản Test 1 fail. Bắt buộc: mỗi Test Case phải hoàn toàn độc lập, có Setup và Teardown tự dọn dẹp trạng thái.

## 5. Nguyên tắc lập trình (Design Principles)
- **DRY (Don't Repeat Yourself)**: Tuyệt đối không lặp lại chính những tính năng, cụm keyword hoặc dòng code giống nhau trong 1 class/framework. Hãy trích xuất chúng ra thành các common keyword.
- **KISS (Keep It Simple, Stupid)**: Giữ cho logic code và keyword đơn giản nhất có thể.
- **YAGNI (You Aren't Gonna Need It)**: Chỉ nên implement những task/keyword trong phạm vi yêu cầu hiện tại, không nên "vẽ" thêm việc khác ra để làm dự phòng trong khi các việc chính chưa được hoàn thành.

## 6. Hướng Dẫn Khởi Tạo Nguồn Tài Nguyên (Generation Guidelines)
- **Base Components**:
  - ctions/common/GlobalConstants.resource: Khai báo các hằng số cấu hình. CHỈ khởi tạo khi thực sự cần thiết và ĐÃ CÓ SẴN thông tin. Tuyệt đối không tự chế mock data.
  - ctions/common/BasePage.resource: Wrapper bọc lại các lệnh gốc (VD: SeleniumLibrary). CHỈ thêm các Custom Keywords khi kịch bản test thực sự dùng đến. Phải kết hợp sẵn Smart Wait và Log/Exception.
  - ctions/common/BaseTest.resource: Chứa các hàm tiện ích cấp độ Suite. Tránh khai báo hàm thừa thãi.
- **Suite & Imports**:
  - configs/imports.resource: Nơi tập trung import của dự án. Tự động khai báo thêm đường dẫn import tới các file Page Keywords mới tạo.
  - [FeatureName]Test.robot: Trong file Suite, phần *** Settings *** chỉ import duy nhất configs/imports.resource (nguyên tắc Top-down).
  - TUYỆT ĐỐI không khai báo trực tiếp locator trong file .robot. Nếu chưa có data thực tế, bắt buộc phải dừng lại hoặc để rỗng.
