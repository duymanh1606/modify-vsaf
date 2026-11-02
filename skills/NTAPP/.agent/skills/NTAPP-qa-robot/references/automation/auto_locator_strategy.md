# CHIẾN LƯỢC ĐỊNH VỊ PHẦN TỬ (LOCATOR STRATEGY)

> **Chỉ áp cho bề mặt `ui`** (Selenium/Page Object). Bề mặt **`service`** (no-UI, RequestsLibrary) KHÔNG có locator/DOM — "định vị" bằng Contract Map (endpoint/path/field) theo [iron_rules R7s](../../principles/iron_rules.md); bỏ qua toàn bộ file này.

## 1. Thứ Tự Ưu Tiên (Priority Rules)
- **Mức 1**: Thuộc tính duy nhất (Ví dụ: `id`, `data-testid`, `data-qa`, `name`,...).
- **Mức 2**: `Class name` (nếu class mang tính định danh rõ ràng, không bị auto-generate dạng mã băm hash).
- **Mức 3**: `CSS` (ưu tiên do tốc độ truy vấn nhanh và cú pháp gọn gàng).
- **Mức 4**: `Text / Link Text` (phù hợp cho các element tĩnh không đổi ngôn ngữ).
- **Mức 5**: `XPath` (chỉ dùng khi cần xác định phần tử cha-con phức tạp hoặc tìm theo text `//div[contains(text(), "xxx")]` hoặc cần truy vấn nhiều điều kiện liên quan nhau trong một câu lệnh).

## 2. Cú Pháp Định Vị Bắt Buộc (Explicit Locator Syntax)
**Luôn ghi tiền tố tường minh** (`id` · `name` · `identifier` · `class` · `tag` · `css` · `xpath` · `text`) — không để locator trần, tránh mập mờ và tăng tốc engine. Dấu phân cách `:` hoặc `=` đều được nhưng **phải nhất quán trên toàn framework**. Ví dụ: `id:login-button`, `css:.btn-primary > span`, `xpath=//div[@class='menu']`.

## 3. Nguyên Tắc Trích Xuất Bắt Buộc
- **Cấm Absolute XPath**: Tuyệt đối không dùng XPath tuyệt đối theo cấu trúc DOM (VD: `/html/body/div[1]/div[2]/span`).
- **ĐÚNG**: Step 02 lấy locator từ source code thật (template/DS), không suy diễn ngoài source; thiếu → `[TBD]`, cấm bịa. Xác minh khớp DOM + sửa khi lệch là ở **Step 05** (chạy thật → fail → self-heal re-derive từ DOM).
- **TRACE ĐỦ LỚP trước khi `[TBD]`**: với component **wrapper / config-driven** (vd `vt-filter-list` → `vt-filter-button`, `vt-c-table`, `vt-input`), PHẢI đi hết chuỗi tới DOM thật trước khi kết luận thiếu hook: (1) template host → (2) `*.component.ts` (configs/fields định nghĩa control: `controlName`/`fieldName`/`type`) → (3) template component con (`vt-*`/`app-*`) lộ element thật (`input`/`button`/`nz-*` + class/name/aria) → (4) i18n (`*/i18n/*.json`) lấy text/placeholder/label thật cho locator-theo-text. CẤM dừng ở lớp wrapper rồi đánh `[TBD]` chỉ vì "render động" — component động CÀNG bắt buộc đào xuống lớp con tìm DOM. `[TBD]` chỉ hợp lệ sau khi đã đi hết 4 lớp mà source THẬT SỰ không lộ hook ổn định.
- **CẤM neo vào chuỗi i18n khi còn hook khác**: `placeholder`/text lấy qua `*/i18n/*.json` chỉ đúng với **đúng commit đang đọc** — bản deploy thường mới/cũ hơn repo, và chuỗi hiển thị là thứ CR đổi thường xuyên nhất. Thứ tự neo: `data-testid`/`id`/`name`/`formControlName` → class ngữ nghĩa của DS → **nhãn (`<label>`) do DD quy định** → placeholder → text tự do. Buộc phải neo theo chuỗi thì lấy chuỗi từ **DD/contract**, không lấy từ i18n repo, và phải verify trên DOM thật ở bậc smoke ([step-05 §2.b0](../../steps/step-05-execute-and-analyze-logs.md)) TRƯỚC khi sinh tiếp phần còn lại.
- **Source phải là mốc ổn định**: file template đang `modified` chưa commit → nêu rõ trong báo cáo và verify DOM thật, KHÔNG coi là nguồn chuẩn.
- **DUY NHẤT**: locator phải khớp đúng 1 phần tử (để automate trúng). Tránh thứ chỉ duy nhất *tình cờ theo state* (class framework tự sinh, hash, shape/util) — đổi state là hết duy nhất.
- **CÓ NGHĨA**: trong các cách duy nhất, chọn cái mô tả đúng danh tính/chức năng control (`data-testid` / `id` / `name` / `placeholder` / class ngữ nghĩa do dev đặt / text / `aria-label`).
- **Độ ổn định**: HẠN CHẾ TỐI ĐA việc định vị theo index/thứ tự; tránh tuyệt đối index *không chắc chắn* (VD: `(//div[@class='item'])[4]`) hoặc các pseudo-class phụ thuộc vị trí như `nth-child()`, `nth-of-type()` trong CSS. Ưu tiên sử dụng các thuộc tính có ý nghĩa như `name`, `formControlName`, `placeholder` hoặc các custom attributes (`data-testid`). Chỉ dùng vị trí khi thật sự không còn thuộc tính nào phân biệt được.

## 4. Chuẩn Đặt Tên Biến Locator
Tất cả các locator phải được lưu vào file `{Page}Variables.resource` và tuân thủ định dạng:
`${LOAI_ELEMENT}_${CHUC_NANG}`

**Ví dụ:**
- Input: `${INPUT_USERNAME}`, `${INPUT_PASSWORD}`, `${INPUT_SEARCH}`
- Button: `${BTN_LOGIN}`, `${BTN_SUBMIT}`, `${BTN_CANCEL}`
- Dropdown: `${DDL_COUNTRY}`, `${DDL_STATUS}`
- Checkbox/Radio: `${CHK_REMEMBER_ME}`, `${RDO_GENDER_MALE}`
- Text/Label: `${LBL_ERROR_MESSAGE}`, `${TXT_WELCOME}`

## 5. Xử Lý Các Trường Hợp Đặc Biệt
- **Phần tử động (Dynamic Elements)**: Sử dụng các hàm xpath như `contains()`, `starts-with()` để đối phó với các element sinh tự động có tiền tố/hậu tố random.
- **Xử lý Dynamic Locator**: Sử dụng biến tích hợp (Embedded Arguments) hoặc từ khóa thuộc thư viện String để định dạng chuỗi (String Formatting), giúp linh hoạt hóa các Locator.
  - **Đặt tên biến template:** thêm hậu tố `_TPL` để phân biệt với locator tĩnh — `${MENU_ITEM_TPL}`, `${BTN_BY_LABEL_TPL}`, `${ROW_BY_CODE_TPL}`. Nhìn tên là biết phải `Format String` trước khi dùng, không truyền thẳng vào `Click Element`.
  - **Khi nào BẮT BUỘC chuyển sang template (DRY):** có **≥3 locator chỉ khác nhau đúng một chuỗi** (`${LNK_MENU_ORDER}`, `${LNK_MENU_CUSTOMER}`, `${LNK_MENU_REPORT}`…) → gom về 1 template + 1 keyword nhận `[Arguments]`. Mỗi menu/hàng/tab thêm một biến locator là mỗi lần phải sửa N chỗ khi DOM đổi.
  - **Khi nào KHÔNG dùng template:** control **đơn nhất** trên màn (nút Lưu, ô tìm kiếm) — template hoá làm mất tính đọc-hiểu mà không tái dùng được gì; và khi tham số truyền vào là **text i18n** dễ đổi trong khi đã có `id`/`data-testid` ổn định (§1 vẫn thắng: ưu tiên id).
  - *Ví dụ phân tách file theo chuẩn POM:*
  
  **File `MenuVariables.resource`:**
  ```robotframework
  *** Variables ***
  ${MENU_ITEM_TPL}    xpath=//div[@class='menu']//a[text()='{menu_name}']
  ```

  **File `MenuKeywords.resource`:**
  ```robotframework
  *** Settings ***
  Resource    MenuVariables.resource
  Library     String

  *** Keywords ***
  Click Menu Item
      [Arguments]    ${menu_name}
      ${locator}    Format String    ${MENU_ITEM_TPL}    menu_name=${menu_name}
      Click Element    ${locator}
  ```
- **Phần tử bên ngoài Viewport**: Sử dụng keyword `Scroll Element Into View` trước khi tương tác.

## 6. Nguồn locator khi KHÔNG có code FE (Live-DOM Harvest — `locator_source: live-dom`)

> Áp khi Step 01 detect `locator_source: live-dom` (không có repo FE source, nhưng app staging login được). Đổi **nguồn** locator từ source tĩnh sang **DOM thật của app đang chạy** — cùng thứ tự ưu tiên §1, cùng nguyên tắc trích §3, cùng chuẩn đặt tên §4. Đây là **phiên soi DOM riêng ở Step 02, KHÔNG phải chạy test case**; mục tiêu là ghi `{Page}Variables.resource` đã verify TRƯỚC khi sinh + chạy suite (không phụ thuộc self-heal Step 05).

### 6.1 Quy trình soi (một lần, ở Step 02)

> **Không có chicken-and-egg:** DOM **trang login đọc được TRƯỚC khi đăng nhập** (trang pre-auth, render ngay khi mở browser) → locator login harvest được mà không cần login trước. Thứ tự: (a) nếu repo **đã có keyword login chạy được** → locator login đã tồn tại → bỏ qua, vào thẳng bước 2 dưới; (b) nếu chưa → soi DOM trang login pre-auth lấy `INPUT_USERNAME`/`INPUT_PASSWORD`/`INPUT_CAPTCHA`/`BTN_LOGIN` rồi mới build login. Locator màn chức năng (post-auth) soi sau khi đã login. Locator login KHÔNG phụ thuộc locator màn chức năng.

1. `Open Browser ${BASE_URL}` (1 lần) → login: **TÁI DÙNG keyword login sẵn có của repo automation** (đã tự giải captcha-text qua API gen/verify) nếu tồn tại — KHÔNG dựng lại luồng login. Chỉ khi repo chưa có keyword login mới soi DOM trang login (pre-auth) theo ghi chú trên + `automation_prereq.auth`.
2. **Click** điều hướng tới từng màn cần locator (theo R9 — CẤM `Go To`; mở modal/màn con bằng nút ở màn cha).
3. Đưa màn về **đúng state có đủ control** (có data để list/row hiện; mở modal nếu control nằm trong modal). List rỗng → không có locator của row/nút thao tác → cần data (báo nếu thiếu).
4. Với mỗi control trong `ui_schema` checklist, đọc DOM thật:
   - `Get WebElements` + `Get Element Attribute`, hoặc `Execute Javascript` trả về danh sách ứng viên kèm thuộc tính (`id`, `data-testid`/`data-qa`, `name`, `formControlName`, `class`, `aria-label`, `placeholder`, `innerText`).
5. Chọn locator theo **thứ tự ưu tiên §1** (id/data-testid/name → class ngữ nghĩa → css → text → xpath), tuân nguyên tắc §3 (DUY NHẤT + CÓ NGHĨA, cấm index/nth-child, cấm absolute xpath).
6. **Ghi thẳng** locator đã chọn vào `{Page}Variables.resource` (chuẩn tên §4). Verify mỗi locator resolve đúng 1 element ngay trong phiên soi (vd `Get Element Count == 1`).

### 6.2 Gate
- Mọi control trong checklist phải có locator verify được từ DOM. Control **thật sự vắng** trên DOM (state chưa đúng / feature chưa build) → `[TBD]` + báo, KHÔNG bịa (R1/R5).
- Xong phiên soi + Variables.resource sạch `[TBD]` → mới sang Step 03. KHÔNG dùng phiên soi này để assert nghiệp vụ (nó chỉ lấy locator).

### 6.3 Lưu ý
- Locator live-dom mất "trace về source" (provenance §3 ĐÚNG) — đổi lại khớp DOM thật, ổn định hơn cho black-box. Chấp nhận được khi không có code.
- Nếu app KHÔNG login được / KHÔNG tới được màn → không harvest được → fallback: nhận **DOM snapshot** (`outerHTML` từng màn do người cung cấp) và trích locator từ HTML thật đó; vẫn KHÔNG có snapshot → `[TBD]` toàn bộ + DỪNG báo thiếu (R5).

### 6.4 Thang fallback khi phiên soi Selenium không dựng được (thiếu driver / không có display)

Đây là **trở ngại runtime** → R12 áp: **DỪNG + báo user TRƯỚC**, không tự đổi công cụ. Sau khi user xác nhận, đi theo thứ tự:

1. **Selenium headed (mặc định)** — cách duy nhất không cần xin phép.
2. **Tool browser của môi trường agent (vd MCP `playwright`), CHỈ nếu môi trường đang có tool đó** — dùng **read-only để thu DOM**, không phải để chạy test:
   - Điều hướng vẫn **theo click** như §6.1 bước 1-3 (R9 — cấm deep-link URL tới màn chức năng).
   - Lấy `outerHTML` / danh sách thuộc tính ứng viên, rồi chọn locator theo **§1-§4 như thường**.
   - **Locator ghi ra `{Page}Variables.resource` phải là cú pháp SeleniumLibrary** (`id=`, `css=`, `xpath=` — §2). CẤM copy selector đặc thù của Playwright (`get_by_role`, `text=`, `>> nth=`) vào Variables.
   - Xác minh duy-nhất (đúng 1 element) ngay trong phiên soi; kết quả vẫn phải pass **§6.2 Gate**.
   - Suite thực thi (Step 03/05) **vẫn là SeleniumLibrary headed** — R12 không nới. Phiên soi này không phải test run nên không tính là lách R12, nhưng **phải ghi rõ trong báo cáo Step 02** là locator harvest bằng tool nào.
3. **DOM snapshot do người cung cấp** (§6.3) → cuối cùng mới `[TBD]` + DỪNG.
