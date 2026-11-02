# QUY CHUẨN NAMING & CODING CONVENTIONS

## 1. Ngôn ngữ & Mã nguồn chung (General Rules)
- **Ngôn ngữ**: Sử dụng tiếng Anh cho toàn bộ code và comment (trừ test cases name có thể phụ thuộc vào test case name của Manual).
- **Tránh code thừa**: Phần code bị comment không sử dụng nên xóa, nếu muốn giữ lại phải comment rõ ràng mục đích.
- **Dọn dẹp**: Remove các variables, keywords đã khai báo nhưng không sử dụng.

## 2. Thư mục và File (Files & Folders)
- **Đặt tên theo page hoặc chức năng**: Ví dụ: `Login`, `HomePage`, `ActivePin`.

- **Tên File**: Viết hoa chữ cái đầu tiên, các chữ còn lại là chữ thường. Các từ được viết liền nhau (PascalCase). Đuôi file: `.resource` cho Variables/Keywords, `.robot` cho Test Suite.
  - Ví dụ: `LoginKeywords.resource`, `LoginVariables.resource`, `LoginTest.robot`.

## 3. Test Cases & Test Suites
- **Tên Test Suite**: (Định nghĩa trong phần `*** Settings ***`) Phải viết hoa chữ cái đầu mỗi từ (Title Case), mô tả cụ thể module/tính năng đang test. VD: `Login User Authentication`.
- **Tên Test Case**: Cấu trúc bắt buộc: [Mã manual `KB-{id}-NN`] - [Mục tiêu test] (không có phần tiền tố tên chức năng). **Số/mã lấy NGUYÊN VĂN từ mã manual — KHÔNG tự đánh số thứ tự riêng** (mã auto phải trùng mã manual, R3). Phần mục tiêu test viết hoa chữ cái đầu tiên (nên bắt đầu bằng từ khóa mô tả kiểm thử như `Kiểm tra`, `Verify`). VD: `KB-SLICE-01-03 - Kiểm tra đăng nhập thành công với thông tin hợp lệ`.
- **Tags (`[Tags]`)**: Viết thường kebab-case/snake_case cho tag phân loại (vd `smoke`, `regression-test`, `login_flow`). **BẮT BUỘC** mỗi Test Case automate mang **mã manual nguyên văn** `KB-{id}-NN` **+ propagate nguyên văn `@block:*` / `@tech:*` / `@rule:*` / `@risk:*` / `@oracle:*`** của scenario gốc (`@oracle:*` mang **đủ số lượng** khi scenario có nhiều tầng) — các gate cơ học lọc case theo `@rule:*` và `@oracle:*` (R3). VD: `[Tags]    KB-SLICE-06-02    @block:ui    @tech:BVA    @rule:grid-base    @risk:P2    @oracle:ui    @oracle:db` (giữ nguyên độ pad `NN` của mã manual — `-02` ≠ `-002`; `@scr:*`/`@svc:*` đặt ở suite-level `Test Tags`, không per-test).

## 4. Keywords
- **Nguyên tắc tái sử dụng**: Khi viết keyword mới, xem lại các keyword hiện có xem đã có hay có thể tái sử dụng một phần keyword khác không.
- **Xác nhận hành động ≠ assert oracle** (đọc kèm [structure §2.1](./auto_framework_structure.md) — hai chỗ này nói về hai thứ khác nhau, đừng chấm ngược):
  - Keyword thao tác **được và nên** chờ xác nhận thao tác đã xảy ra, bằng **`Wait Until *`** trên dấu hiệu kỹ thuật (trang đích đã render, overlay loading đã tan, nút đã enable) — vd `Click Button Login` chờ tới khi form login biến mất. Đây là **chống race**, không phải verify kết quả nghiệp vụ.
  - Keyword thao tác **KHÔNG** assert `Kết quả mong muốn` của case (`Should Be Equal`, so message/giá trị/count) — thứ đó trả về hoặc để keyword **verify riêng** (`<Field> Value Should Be`) làm, và Test Case là nơi gọi. Nhồi oracle của case vào keyword thao tác làm `${expected}` biến mất khỏi tầng test → vi phạm [R11 — anti-stub: `${expected}` phải được tiêu thụ trong assert](../../principles/iron_rules.md).
- **Tên Keyword**: Được đặt tên theo chức năng của keyword (V + N/N phrase).
  - Ví dụ: `Add...`, `Login...`, `Check...`, `Get...`, `Verify...`.
  - Những hàm nào trả về Boolean thì thêm tiền tố Is (ví dụ: Is Login Form Displayed).
  - Viết hoa các chữ cái đầu tiên, các chữ còn lại là chữ thường. Các từ được viết cách nhau bởi 1 SPACE (Title Case).
  - Ví dụ: `Get Customer Infomation`, `Register Account`, `Access Homepage`.
- **CẤM "gate-breaking name"** — tên keyword (và comment) KHÔNG được chứa cụm token bị cấm: `Sleep`, `Go To`, `Reload Page`. Phép kiểm R7/R9 ([gate_commands §2](./auto_gate_commands.md)) chỉ tính **dòng gọi** keyword, nên tên như `Sleep Until Ready` / `Verify User Go To Dashboard` **không** bị chấm là vi phạm điều hướng — nhưng người kiểm sau cứ phải dừng lại đọc rồi loại nó ra, nên **phải đổi tên** (vd `Wait Until Ready`, `Verify Dashboard Opened`).
- **Độ dài Keyword**: Chứa tối đa 20 steps (nếu nhiều hơn nên chia nhỏ keyword).
- **CẤM `[Documentation]`** ở Test Case và Keyword (header `Documentation` mức `*** Settings ***` vẫn giữ). Ý nghĩa nằm ở tên keyword / tên Test Case — chưa rõ thì đổi tên. Sửa file cũ → xoá kèm dòng nối `...`.
- **CẤM comment `#`**: không emit dòng comment nào trong code sinh tự động — không chú thích mô tả, không banner phân mục (`# ==== ... ====`). Cần diễn giải thì viết vào `Documentation` mức `*** Settings ***`.

## 5. Biến (Variables) & Đối số (Arguments)
- **Tên ngắn gọn, gắn với đối tượng** (ý nghĩa + mục đích sử dụng), từ dài nối bằng snake_case.
- **Các ký hiệu Prefix**: `$` (Scalar), `@` (List), `&` (Dictionary) viết thường.
- **Biến toàn cục (Global Variables) & Environment Variables**: Ký hiệu `%` và nội dung viết hoa tất cả các chữ cái (SCREAMING_SNAKE_CASE).
  - Ví dụ: `%{PATH}`, `${BROWSER}`, `${BASE_URL}`.
- **Biến Locator**: theo [locator_strategy §4](./auto_locator_strategy.md#4-chuẩn-đặt-tên-biến-locator) — **UPPER_SNAKE_CASE** `${LOAI_ELEMENT}_${CHUC_NANG}` (`${BTN_LOGIN}`, `${INPUT_USERNAME}`, `${LBL_ERROR_MESSAGE}`). Quy tắc snake_case chữ thường ở trên chỉ áp cho biến/đối số thường, KHÔNG áp cho locator.
- **Biến tích hợp ngoại lệ (Built-in variables)**: Chú ý sử dụng đúng chuẩn: `${True}`, `${False}`, `${None}`, `${EMPTY}`, `${SPACE}`, `${SUITE NAME}`, `${TEST_NAME}`, `${TEST STATUS}`.

## 6. Coding Convention Cụ Thể (Syntax Rules)
- **Khoảng cách (Spacing)**:
  - BẮT BUỘC sử dụng ít nhất 2 khoảng trắng (spaces) hoặc 1 tab (khuyến nghị dùng 4 spaces) để phân tách giữa các khai báo (biến, keywords, arguments, tham số locator).
  - TUYỆT ĐỐI không sử dụng 1 khoảng trắng duy nhất để ngăn cách, vì Robot Framework sẽ coi đó là một chuỗi liền mạch.
  - Không nên: `${btn_login} css:button` (sai vì chỉ có 1 space).
  - **Nên dùng**: `${btn_login}    css:button` (4 spaces).
- **IF Conditions**:
  - Không nên: `IF '${is_checked}'=='${True}'` ➔ **Nên dùng**: `IF ${is_checked}`
  - Không nên: `IF '${is_checked}'=='${False}'` ➔ **Nên dùng**: `IF not ${is_checked}`
- **Gán biến (Assignment)**:
  - Không dùng dấu `=` sát biến.
  - Không nên: `${OTP}=    Set Variable    ${get_otp}` ➔ **Nên dùng**: `${OTP}    Set Variable    ${get_otp}`