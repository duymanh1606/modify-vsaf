# QUY CHUẨN CẤU TRÚC FRAMEWORK (FRAMEWORK STRUCTURE)

## 1. Cấu trúc thư mục tổng thể

Dự án Automation sẽ tuân theo cấu trúc phân tầng như sau:

```text
robot_framework_project/
├── actions/                  # Thư mục quản lý toàn bộ các hành động tương tác
│   ├── common/               # Quản lý các function dùng chung cho testcase/pages
│   │   ├── BasePage.resource # Wrapper cho PageObjects (KHÔNG khai locator)
│   │   ├── BaseTest.resource # Các hàm common dùng cho tầng testcases
│   │   ├── SuiteFixtures.resource # Suite Setup/Teardown + session/auth/kết nối DB
│   │   ├── GlobalConstants.resource # Hằng số dùng chung (URL, user/pass, API)
│   │   └── SeedRegistry.resource # Seed/teardown dữ liệu mồi (registry-driven)
│   ├── pageObject/           # (bề mặt ui) Quản lý các actions trong từng page
│   │   ├── ShellPage/        # Locator shell dùng chung mọi màn (toast, modal, overlay…)
│   │   │   ├── ShellKeywords.resource
│   │   │   └── ShellVariables.resource
│   │   ├── LoginPage/
│   │   │   ├── LoginKeywords.resource
│   │   │   └── LoginVariables.resource
│   │   └── HomePage/
│   │       ├── HomeKeywords.resource
│   │       └── HomeVariables.resource
│   └── serviceObject/        # (bề mặt service, no-UI) 1 endpoint/operation = 1 object
│       └── TransferService/
│           ├── TransferServiceKeywords.resource   # request RequestsLibrary + assert status/body/DB/MSG
│           └── TransferServiceVariables.resource  # base_url, path, header (KHÔNG locator)
├── resources/                # Quản lý các external file cho toàn bộ framework
├── libraries/                # Quản lý thư viện cho toàn bộ framework
├── configs/                  # Chứa các file cấu hình môi trường, thông số khởi tạo, và import tập trung các Keywords (ví dụ: từ các page)
│   ├── env_<environment>.resource # CHỈ tạo env thực sự dùng + thực sự được import (xem §2.3)
│   └── imports.resource      # File import tập trung các Keywords
├── datatest/                 # Chứa Test Data (Excel, JSON, CSV) 
│   ├── accounts.json
│   └── test_data.xlsx
├── tests/                    # Chứa các kịch bản kiểm thử (Test Suites)
│   ├── LoginTest.robot
│   └── HomeTest.robot
└── results/                  # Chứa các file báo cáo kết quả (Log, Report, Screenshots)
```

## 2. Quy ước tổ chức các tầng (Layers)

### 2.1 Tầng Actions (`actions/`)
- Thư mục quản lý toàn bộ các hành động tương tác, bao gồm các function dùng chung và các action riêng của từng page.
- **`common/`**: Không để trong thư mục `resources/`. Quản lý các function dùng chung cho cả testcases và pages.
  - **BasePage**: wrapper của keyword thư viện (SeleniumLibrary…) dùng chung cho PageObjects.
    - **CẤM khai `*** Variables ***` locator trong BasePage.** Mọi locator đều thuộc `pageObject/*/*Variables.resource` — kể cả locator shell dùng chung mọi màn (toast, modal, tooltip, popover, lớp phủ loading): gom vào một page object riêng `pageObject/ShellPage/ShellVariables.resource` + `ShellKeywords.resource`. BasePage chỉ nhận locator **qua tham số**, không tự biết locator nào.
  - **BaseTest**: hàm common cấp Suite cho tầng testcases. **Wrapper mở browser BẮT BUỘC `Maximize Browser Window` ngay sau `Open Browser`** (xem [auto_robot_rules §6](./auto_robot_rules.md#6-hướng-dẫn-khởi-tạo-nguồn-tài-nguyên-generation-guidelines)) — tránh responsive/collapsed layout ẩn element gây false-fail.
    - **CHỈ chứa hàm feature-agnostic** (không biết page/entity/bảng DB cụ thể). Keyword nào tham chiếu locator / dữ liệu nghiệp vụ / bảng DB của 1 màn — **kể cả teardown/cleanup dữ liệu của màn đó** — PHẢI nằm ở `*Keywords.resource` của page tương ứng, KHÔNG để BaseTest. (Teardown gắn với tầng test ở chỗ *khi nào chạy*, nhưng *nội dung dọn gì* là domain-specific → thuộc Page.)
  - **Global Constants**: Chứa các thông tin hằng số dùng chung trên toàn framework:
    -  URL server, user/pass dùng chung (Server, DataBase), thông tin API. **Tên biến CỐ ĐỊNH — sinh code chỉ được dùng đúng các tên này, đặt tên khác sẽ làm `robot --dryrun` đỏ ở Step 03 và đốt trọn 1 vòng:** `${BASE_URL}` (trang login, bề mặt `ui` — argument duy nhất được phép của `Open Browser` theo R9) · `${API_BASE_URL}` (bề mặt `service`, cho `Create Session`).
    -  Biến timeout 3 tầng: `${SHORT_TIMEOUT}` (2s) / `${GLOBAL_TIMEOUT}` (10s) / `${LONG_TIMEOUT}` (30s), **+ `${POLL_INTERVAL}`** (chu kỳ poll của `Wait Until Keyword Succeeds` — bắt buộc có khi bề mặt `service` assert side-effect async, xem [iron_rules R7s](../../principles/iron_rules.md))
    -  **Env var đọc theo tiền tố dự án `<ENV_PREFIX>`** (vd `%{<ENV_PREFIX>_DB_HOST}`): `<ENV_PREFIX>` do project khai, KHÔNG hardcode tiền tố của một dự án cụ thể vào skill (Portability principle — skill canonical phải chạy được ở repo khác).
    -  Browser: `${BROWSER}`. Keyword mở browser dùng **mặc định thư viện = HEADED** + `Maximize Browser Window`. ⛔ **TUYỆT ĐỐI KHÔNG scaffold toggle headless** — cấm mọi hình thức: `--headless`, biến `${HEADLESS}`, `%{<ENV_PREFIX>_HEADLESS=...}`, `Set Variable If ... headless`. Chỉ thêm khi **user yêu cầu rõ ràng bằng lời**. ⚠️ **Cạm bẫy lách-runtime (đã vi phạm):** khi chạy live gặp lỗi do môi trường KHÔNG có desktop (headed → viewport 0px → `element has zero size` / `ElementNotInteractableException`), **KHÔNG được "sửa" bằng cách bật headless** — đó là lách rule. Xử lý đúng: **DỪNG, báo user chạy trên máy có desktop hiển thị** (headed render bình thường ở đó). Rule skill > giải pháp kỹ thuật cho tiện. Xem [iron_rules R12](../../principles/iron_rules.md).
    -  Số lần retry cho test failed (≤3 — R7/R7s)
    -  Đường dẫn tương đối tới thư mục download, file data, file upload
- **`serviceObject/`** *(bề mặt `service` — no-UI)*: Đối ứng của `pageObject/` cho test API/service. Mỗi endpoint/operation = 1 thư mục chứa `{Service}Variables.resource` (base_url/path/header — KHÔNG locator) + `{Service}Keywords.resource` (keyword gọi request qua `RequestsLibrary` + keyword assert status/body, gọi verify DB/MSG). Cùng nguyên tắc POM: test suite chỉ gọi high-level keyword, không chứa URL/payload thô. Session (`Create Session` + auth) + kết nối DB/queue verify đặt ở `common/SuiteFixtures.resource`. Thư viện `RequestsLibrary` khai ở `libraries/`. KHÔNG dùng SeleniumLibrary/browser cho bề mặt này.
- **`pageObject/`** *(bề mặt `ui`)*: Quản lý các actions trong từng page. Tất cả các Page trong dự án sẽ được đặt ở đây.
  - Mỗi page sẽ quản lý các sự kiện của chính page đó (ví dụ: `LoginPage`, `HomePage`).
  - Mỗi thư mục chức năng chỉ được phép chứa:
    - **`*Variables.resource`**: Chứa toàn bộ element locators của page đó.
    - **`*Keywords.resource`**: Chứa các actions tương tác trực tiếp lên UI. Bắt buộc phải import file Variables tương ứng và có thể sử dụng các wrapper từ `BasePage`.
  - **Lưu ý**: 
    - Tầng Page Objects KHÔNG chứa logic Test Case (không có thẻ `*** Test Cases ***`).
    - Keyword **thao tác** không tự assert — trả giá trị về để tầng Test verify. Nhưng keyword **verify theo chức năng** (`<Field> Value Should Be`, verify DB…) VẪN đặt ở Page/Service Keywords, vì `.robot` không được định nghĩa keyword ([iron_rules R4](../../principles/iron_rules.md)) — test chỉ *gọi* chúng.

### 2.2 Tầng External Resources & Libraries (`resources/`, `libraries/`)
- **resources/**: Quản lý các tài sản tĩnh (Assets/Binary) hỗ trợ cho framework nhưng không phải là dữ liệu nghiệp vụ có cấu trúc. 
  - Ví dụ: Các file hình ảnh/PDF mẫu dùng để test chức năng Upload, file `.exe` của WebDriver, hoặc các file cấu hình đặc thù của bên thứ 3 (ví dụ: config cho Appium, proxy profile).
  - *Lưu ý: Không để dữ liệu test (test data) hoặc cấu hình biến môi trường của Robot Framework vào đây.*
- **libraries/**: Quản lý thư viện cho toàn bộ framework (ví dụ: các thư viện Python tự viết hoặc các custom library khác).

### 2.3 Tầng Data & Config (`configs/`, `datatest/`)
- Tầng này không chứa logic, tập trung vào cấu hình chạy test và dữ liệu đầu vào.
- **configs/**: Chứa các file cấu hình *của chính Robot Framework* như biến môi trường (URL, Account mặc định, Database config cho Dev/Staging). **CHỈ tạo file env thực sự dùng và thực sự được `imports.resource` import** — scaffold `env_dev`/`env_stg` rỗng "cho đủ bộ" là config-theatre — vi phạm YAGNI ([robot §5](./auto_robot_rules.md)).
- **datatest/**: Chứa toàn bộ dữ liệu kiểm thử có cấu trúc (Structured Test Data). Đây là các file chứa giá trị nghiệp vụ (JSON, CSV, Excel) có thể parse ra thành biến/mảng để sử dụng cho Data-Driven Testing.
- **Quản lý Import tập trung**: Thư mục `configs/` có thể chứa các file `.resource` đóng vai trò tập hợp (ví dụ: `imports.resource`). File này dùng để import tất cả các file `*Keywords.resource` từ các page. Giúp các file Test Suite gọn gàng hơn vì chỉ cần gọi import file tập hợp này thay vì khai báo lại nhiều file nhỏ lẻ.
- Các file Test Suite hoặc Base Test sẽ load data và import các Keywords thông qua tầng này để thực thi.

### 2.4 Tầng Test Execution (`tests/`)
- File ở tầng này bắt buộc có đuôi `.robot` và có chứa thẻ `*** Test Cases ***`. **Mỗi file = 1 Test Suite cho 1 UNIT màn/operation** (`@scr:<unit_id>` / `@svc:<unit_id>`) — KHÔNG phải 1 file cho cả `surface_type`: slice N màn → N file. Luật tách & đặt tên đầy đủ (tên theo màn/operation, cấm nhét `{id}`, cấm file "tổng hợp", cấm mashup) ở [step-03 §2](../../steps/step-03-generate-suite.md) — không lặp lại ở đây.
- **Suite Setup/Teardown + fixtures điều hướng dùng chung** cho nhiều suite → đặt ở `actions/common/SuiteFixtures.resource` (import qua `configs/imports.resource`), các suite gọi lại — CẤM copy-paste block Setup vào từng `.robot` (DRY).
- Các file Test chỉ import các `Keywords.resource` cần thiết, file data và file cấu hình chung (`BaseTest`).
- **KHÔNG**: Viết trực tiếp locator (XPath, CSS) hoặc logic phức tạp trong file Test. File Test chỉ gọi High-level Keyword để mô tả flow kinh doanh và dùng các câu lệnh Assertion.
- Các bước thực hiện kiểm thử thủ công như nào thì ánh xạ qua như thế.
- Dùng Setup và Teardown để đảm bảo testcase chạy chính xác, tránh viết code lặp lại.

## 3. Quy tắc Import (Tránh Circular Dependency)

Để tránh lỗi lặp vòng và dễ quản lý khi import các tài nguyên, hãy tuân thủ nguyên tắc một chiều (Top-down) và cơ chế import tập trung:
1. **Tests** import file **imports.resource** (để lấy tất cả Keywords), **BaseTest** (để chạy Setup/Teardown), và file **Data**. KHÔNG import lẻ tẻ từng file Keyword.
2. **imports.resource** (tại thư mục `configs/`) import toàn bộ **Keywords (Pages)**, **BaseTest**, và **Global Constants**.
3. **Keywords (Pages)** chỉ import **Variables (Pages)** tương ứng của nó và **BasePage** (chứa các wrapper chung).
4. **Tuyệt đối không**:
   - File Variables không được import File Keywords.
   - Các Page ngang hàng hạn chế import chéo lẫn nhau nếu không thực sự cần thiết (tránh page A gọi page B rồi page B gọi lại page A). Việc luân chuyển page nên được thực thi ở tầng Test Suites.