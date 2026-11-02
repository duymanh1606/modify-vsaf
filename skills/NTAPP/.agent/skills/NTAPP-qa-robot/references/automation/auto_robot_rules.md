# QUY TẮC TỰ ĐỘNG HÓA ROBOT FRAMEWORK (ROBOT AUTOMATION RULES)

> **Phạm vi bề mặt:** phần lớn quy tắc dưới đây viết cho bề mặt **`ui`** (Selenium: locator, `Open Browser`/`Maximize`, `Input Text`, `Page Contains`, Smart Wait element). Các nguyên tắc **feature-agnostic áp cho cả `service`**: POM (§1 — đổi Page↔Service Object), library-first (§5, dùng `RequestsLibrary`), DRY/KISS, cấm `Sleep`, data-driven (không hardcode). Các mục thuần-UI (mở browser/maximize, gõ element, `Page Contains`) **KHÔNG áp** cho bề mặt `service` — thay bằng `Create Session` + `... On Session` + assert status/body/DB/MSG, async dùng `Wait Until Keyword Succeeds` (xem [iron_rules R7s](../../principles/iron_rules.md) + step-02 nhánh service).

## 1. Page Object Model (POM)
- **Cấu trúc Thư mục**: Tổ chức source code phân mảnh rõ ràng theo cấu trúc Page.
- **Variables Resource (`{Page}Variables.resource`)**: Chứa 100% locator của giao diện đang test.
- **Keywords Resource (`{Page}Keywords.resource`)**: Chứa các action tương tác UI và các hàm logic kiểm tra.
- **Test Suite (`[Screen]Test.robot`)**: Chỉ chứa `*** Settings ***` + `*** Test Cases ***` (+ tối đa `*** Variables ***`) — **GỌI** high-level keyword, **KHÔNG có section `*** Keywords ***`** (mọi định nghĩa keyword nằm ở `.resource` — xem [iron_rules R4](../../principles/iron_rules.md)). TUYỆT ĐỐI không khai báo định danh/locator/SQL ở đây.

## 2. Quản Lý Dữ Liệu Test (Test Data Management)
- **Tách biệt dữ liệu**: Tách dữ liệu khỏi script logic bằng file định dạng `.yaml`, `.json` (nạp dataset theo `@id` mỗi case). "Data-driven" ở đây = *tách nguồn dữ liệu*, KHÔNG phải dùng `Test Template`/`[Template]` để gom nhiều case vào 1 test — mỗi case là 1 Test Case riêng (per-case, xem [iron_rules R8/R11](../../principles/iron_rules.md)).
- **Tính tự sinh**: Các dữ liệu mang tính định danh duy nhất (email, username, ID) bắt buộc phải được sinh ngẫu nhiên (ví dụ bằng Faker) để tránh trùng lặp dữ liệu khi chạy lại.
- **Tiền tố `auto_`**: Mọi giá trị định danh kiểu chuỗi sinh ra và ghi vào hệ thống phải BẮT ĐẦU bằng `auto_` — dạng `auto_<nhãn>_<run-marker>_<uuid8>` (xem [iron_rules R7d](../../principles/iron_rules.md)). Miễn trừ: trường chỉ nhận số và ca biên độ dài. Keyword sinh tên đặt tập trung một chỗ trong `actions/common/`, cấm mỗi test tự nối chuỗi tên riêng.
- **Biến môi trường**: Các thông số về Server URL, Browser type, Global Timeout phải được đặt tại file config chung của dự án.
- **Escape ký tự đặc biệt khi emit data vào step** (lỗi sinh thường gặp):
  - **Khoảng trắng trọng yếu**: giá trị chứa ≥2 space liên tiếp, hoặc space đầu/cuối có ý nghĩa, BẮT BUỘC dùng `${SPACE}` cho từng space (vd `Hồ${SPACE}${SPACE}sơ A`). Robot Framework tách argument theo 2+ space → để literal `Hồ  sơ A` sẽ bị tách thành 2 argument → keyword nhận sai số tham số.
  - **Ký tự ngoài BMP (astral, vd emoji 🚀 U+1F680)**: ChromeDriver `send_keys` KHÔNG gửi được → `WebDriverException: only supports characters in the BMP`. Nếu data nguồn chứa astral char: route case sang `manual` (ghi rõ lý do giới hạn driver) HOẶC dùng JS set-value; KHÔNG emit `Input Text` với astral char. Ký tự BMP (©®™€§…) thì gõ bình thường.
  - **Xoá field validation phải bắn event**: `Clear Element Text` không bắn `input` → Angular không `dirty/touched` → lỗi required/regex không hiện. Cần xoá để test required: dùng `Press Keys ${locator}    CTRL+a    DELETE` (+`TAB` nếu cần touched).

## 3. Quản Lý Thời Gian Chờ (Wait Strategies)
- **Cấm Sleep tĩnh**: Cấm sử dụng từ khóa `Sleep` với thời gian cứng.
- **Smart Wait**: Bắt buộc sử dụng các keyword thăm dò trạng thái như `Wait Until Element Is Visible`, `Wait Until Element Is Enabled`, hoặc `Wait Until Keyword Succeeds`.
- **Click bị lớp phủ che**: element `Visible`+`Enabled` VẪN có thể bị lớp phủ loading (spinner/overlay/backdrop) chặn → click ném `ElementClickInterceptedException`. Wrapper click/input phải **chờ lớp phủ biến mất trước khi thao tác** (vd `Wait Until Keyword Succeeds` kiểm không còn overlay hiển thị). Chỉ `Wait Until Enabled` là KHÔNG đủ — đây là lỗi hay lọt.
- **Cấm Hardcode Timeout**: Khi sử dụng Smart Wait, KHÔNG được hardcode thời gian. Ví dụ: `timeout=10s`. BẮT BUỘC truyền biến từ `GlobalConstants.resource`, chọn 1 trong 3 tầng theo bản chất thao tác:
  - `${SHORT_TIMEOUT}` (2s) — probe element **có thể không xuất hiện** (đi kèm `Run Keyword And Return Status`). Ví dụ: kiểm tra form login đã hiện chưa.
  - `${GLOBAL_TIMEOUT}` (10s) — **mặc định**, chờ element load bình thường. Ví dụ: `Wait Until Element Is Visible    ${locator}    timeout=${GLOBAL_TIMEOUT}`.
  - `${LONG_TIMEOUT}` (30s) — thao tác biết trước sẽ chậm. Ví dụ: submit nặng, chờ bảng lớn render, gọi API/downstream.
- **CẤM IMPLICIT WAIT — và CẤM TRỘN implicit với explicit.** `Set Selenium Implicit Wait`, `Open Browser ... implicit_wait=`, `driver.implicitly_wait()` trong Python library: KHÔNG dùng, giữ implicit wait = **0**. Chỉ chờ bằng explicit (`Wait Until *`).
  - **Vì sao:** trộn hai loại làm thời gian chờ **không đoán được** (driver đã chờ ngầm rồi explicit chờ tiếp), và mọi phép kiểm **phủ định** (`Element Should Not Be Visible`, probe `Run Keyword And Return Status`) bị đội lên trọn implicit timeout — suite chậm gấp N lần số assert phủ định, đồng thời che race condition thật vì cái gì cũng "kịp" hiện.
  - **Bẫy đã thấy ngoài thực tế:** khung base set `implicitlyWait(30s)` ở tầng khởi tạo driver trong khi tầng page dùng `WebDriverWait(30s)` — không ai chỉnh vì test vẫn xanh, nhưng mỗi negative check tốn 30s và số đo timeout trong code không còn phản ánh hành vi thật.
  - **Chọn tier theo bản chất phép kiểm, không theo thói quen:** kiểm **có xuất hiện** → `${GLOBAL_TIMEOUT}` (hoặc `${LONG_TIMEOUT}` nếu biết chậm); kiểm **không/chưa xuất hiện** → `${SHORT_TIMEOUT}`. Dùng `${LONG_TIMEOUT}` cho check phủ định là lỗi hiệu năng, không phải "cho chắc".

## 4. Quy Tắc Chống Mẫu Nghiêm Cấm (Anti-Patterns)
- ❌ **Tự chế dữ liệu (Data Fabrication)**: Tuyệt đối KHÔNG tự ý sinh ra dữ liệu giả (fake data) khi chưa có file dữ liệu gốc. Mọi dữ liệu (hằng số môi trường, payload test) BẮT BUỘC phải được kế thừa từ file cấu hình hoặc dữ liệu thực tế (từ Manual Testcase, `{id}_fixtures.yaml`). Nếu không có, để rỗng hoặc báo lỗi.
- ❌ **Hardcode dữ liệu**: Nhúng thẳng chuỗi text/password/username trực tiếp vào các Test Case.
- ❌ **Locator rác**: Khai báo Xpath/CSS rải rác ngay trong file `.robot` hoặc file `{Page}Keywords.resource`.
- ❌ **Thiếu Assertion**: Test steps chỉ thực hiện hành động click/input nhưng không có bước kiểm tra kết quả (thiếu các keyword `Should Be ...`).
- ❌ **Test Case Phụ Thuộc Nhau**: Kịch bản Test 2 không thể chạy nếu Kịch bản Test 1 fail. Bắt buộc: mỗi Test Case phải hoàn toàn độc lập, có Setup và Teardown tự dọn dẹp trạng thái. **Trường hợp ẩn — tài nguyên precondition BỊ TIÊU THỤ** (vd tạo composite ăn 1 pending): CẤM resolve-once + `Set Suite Variable` dùng lại cho mọi case; case đầu tiêu thụ xong thì case sau fail. Phải seed/rotate bản ghi tươi cho từng case tiêu thụ — xem [auto_db_oracle_rules §11](./auto_db_oracle_rules.md#11-tài-nguyên-precondition-bị-tiêu-thụ-consumable--cấm-cache-1-lần-cho-cả-suite).
  - **Teardown Variable Safety**: BẮT BUỘC dùng `Get Variable Value` trong Teardown cho các biến được khởi tạo trễ (hoặc có thể chưa gán) để tránh lỗi `Variable not found` làm ngắt quãng việc dọn dẹp dữ liệu/DB.
  - **Chọn dòng trên danh sách UI**: Khi dữ liệu cũ trong DB không được dọn dẹp tự động: CẤM chọn dòng theo vị trí cố định (như dòng đầu tiên) ở happy path. BẮT BUỘC truy vấn DB lấy ID bản ghi chưa sử dụng (unconsumed) và thực hiện chọn theo ID đó.
  - **Duy trì Access Token**: Khi reload/navigation làm mới đối tượng `window` (mất JS hook/sniffer): BẮT BUỘC lưu Access Token vào biến Suite ngay sau khi login và cấu hình hàm đọc Token tự động fallback về biến này.
- ❌ **Trùng lặp keyword**: Tạo nhiều keyword có cùng hành vi/chức năng (ví dụ `Wait Until Text Visible` và `Page Should Contain Text`). Chỉ dùng duy nhất một đại diện.
- ❌ **Đặt tên Keyword bằng tiếng Việt**: Tên Keyword trong `.resource` (định nghĩa ở `*** Keywords ***`) BẮT BUỘC tiếng Anh — không có ngoại lệ (xem `auto_coding_convention.md` §1). Không tự dịch/paraphrase business term sang tiếng Việt để "dễ đọc" — vẫn giữ nguyên ngữ nghĩa bằng tiếng Anh (vd `Open Compose Screen`, không phải `Mở Màn Compose`).



## 5. Nguyên tắc lập trình (Design Principles)
- **Library-first**: Ưu tiên keyword của thư viện Robot chuẩn (SeleniumLibrary, RequestsLibrary, DatabaseLibrary, String, Collections, DateTime…) cho MỌI thao tác (UI / HTTP / DB / chuỗi / ngày). KHÔNG tự viết Python library hay logic riêng khi đã có keyword thư viện làm được.
- **DRY**: **Trước khi sinh keyword mới, BẮT BUỘC quét toàn bộ keyword hiện có (BasePage, BaseTest, các Page Object Keywords liên quan). Đã có keyword cùng chức năng → tái sử dụng, TUYỆT ĐỐI không sinh thêm keyword mới.** Cụm code lặp → trích ra common keyword.
- **KISS + YAGNI**: **Mỗi keyword chỉ mang DUY NHẤT 1 trách nhiệm** — tên nói đúng những gì nó làm, không hơn; vừa làm A vừa làm B → tách 2 keyword (vd `Open App Browser` chỉ mở browser, không kiêm lưu path điều hướng). Chỉ implement trong phạm vi yêu cầu hiện tại: TUYỆT ĐỐI không nhồi `[Arguments]` / `Set Suite Variable` "dự phòng cho sau này" khi chưa keyword nào đọc tới (dead code).

## 6. Hướng Dẫn Khởi Tạo Nguồn Tài Nguyên (Generation Guidelines)
- **Base Components**:
  - actions/common/GlobalConstants.resource: Khai báo các hằng số cấu hình. CHỈ khởi tạo khi thực sự cần thiết và ĐÃ CÓ SẴN thông tin. Tuyệt đối không tự chế mock data.
  - actions/common/BasePage.resource: Wrapper bọc lại các lệnh gốc (VD: SeleniumLibrary). CHỈ thêm các Custom Keywords khi kịch bản test thực sự dùng đến. Phải kết hợp sẵn Smart Wait và Log/Exception.
    - **Mở browser BẮT BUỘC phóng to cửa sổ**: keyword wrapper mở browser (vd `Open App Browser`) phải gọi `Maximize Browser Window` NGAY SAU `Open Browser`, trước mọi thao tác điều hướng. Lý do: cửa sổ mặc định/nhỏ dễ đẩy element vào responsive/collapsed layout (menu ẩn sau hamburger, cột bảng bị ẩn) → locator không visible → false-fail. KHÔNG dựa vào `--window-size` cứng thay cho maximize. Ví dụ:
      ```robotframework
      Open App Browser
          Open Browser    ${BASE_URL}    ${BROWSER}    options=...
          Maximize Browser Window
          Register Keyword To Run On Failure    NONE
      ```
  - actions/common/BaseTest.resource: Chứa các hàm tiện ích cấp độ Suite. Tránh khai báo hàm thừa thãi.
- **Suite & Imports**:
  - configs/imports.resource: Nơi tập trung import của dự án. Tự động khai báo thêm đường dẫn import tới các file Page Keywords mới tạo.
  - [FeatureName]Test.robot: Trong file Suite, phần *** Settings *** chỉ import duy nhất configs/imports.resource (nguyên tắc Top-down).
  - TUYỆT ĐỐI không khai báo trực tiếp locator trong file .robot. Nếu chưa có data thực tế, bắt buộc phải dừng lại hoặc để rỗng.

---

## 7. Chọn Oracle Kiểm Chứng (Verification Strategy)

Chọn keyword assertion theo **bản chất nơi kết quả hiển thị** — sai oracle là lỗi sinh thường gặp gây false-fail:

- **Giá trị NẰM TRONG input/textarea** (verify field giữ/echo đúng text đã nhập: maxlength, space-handling, unicode echo) → assert bằng **`Get Value`** của field đó (vd keyword `<Field> Value Should Be/Contain`). **CẤM** dùng `Page Should Contain` / `Wait Until Page Contains` — value của input KHÔNG phải text-node của trang nên Page-Contains luôn FAIL.
- **Text render ra trang** (toast, ô trong list/grid, **inline error message**, banner) → mới dùng `Page Should Contain` / `Wait Until Page Contains` hoặc `Element Should Be Visible` trên locator của phần tử đó.
- **Trạng thái element** (enabled/disabled/visible) → `Element Should Be Enabled/Disabled`, `Element Should Be Visible`.
- **Tập kết quả** (list/grid/panel — Expected "mọi bản ghi khớp filter" / "hiển thị đủ N") → lấy tập dòng (`Get WebElements`) rồi assert TỪNG dòng khớp điều kiện + `Length Should Be`/count. CẤM coi `Page Should Contain` 1 giá trị là đủ (list đúng một phần vẫn pass sai).
- **Phản hồi lỗi độc quyền** (Expected exclusivity) → assert đúng 1 phản hồi đặc tả, kèm `Page Should Not Contain` message generic/khác bị cấm.
- Quy tắc nhanh: *"Mình đang gõ vào ô và kiểm ô có giữ đúng không?"* → `Get Value`. *"Mình kiểm hệ thống có hiện chữ/thông báo ra màn không?"* → `Page Contains`.

---

## 8. Chụp Ảnh

CHỈ chụp khi test FAIL. Mặc định `run_on_failure` chụp mọi keyword fail (kể cả fail bị nuốt bởi `Run Keyword And Return Status`) → case PASS vẫn ra ảnh thừa.

- Suite Setup: `Register Keyword To Run On Failure    NONE`
- Test Teardown: `Run Keyword If Test Failed    Capture Page Screenshot`
