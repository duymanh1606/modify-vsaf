# CÁC PHÉP KIỂM BẮT BUỘC 

Bản **duy nhất** của các phép kiểm trong skill. Step 02 và Step 03 dùng file này ở cổng ra. Đường dẫn tính từ `{code_repo_root}`.

Mỗi mục có 4 phần: **Phải đúng** (điều cần thoả) · **Đọc gì** (mở file nào) · **Dấu hiệu sai** (nhìn thấy gì là vi phạm) · **Ghi vào báo cáo** (bằng chứng phải có).

## 1. Năm Luật Chung (áp cho mọi mục dưới)

- **Đọc hết, không lấy mẫu**: mục nào ghi "đọc `tests/` và `actions/`" thì phải mở **mọi** file trong đó. Không được kết luận "chắc không có" khi chưa mở hết. *("Hết" = hết phạm vi mà bước gọi file này giao; trong phạm vi đó thì vẫn phải đọc 100%.)*
- **Bằng chứng là danh sách, không phải lời khẳng định**: mỗi mục ghi `đã đọc <X>/<Y> file (hoặc case) — <n> vi phạm` + liệt kê vị trí `file:dòng` của từng vi phạm. ❌ "Đã xem, không thấy vấn đề" = coi như **chưa kiểm**.
- **`X` phải bằng `Y`**: đọc thiếu file nào thì nêu rõ thiếu file nào và vì sao; mục đó ghi `UNVERIFIED`.
- **Không nới điều kiện**: thấy vi phạm thì ghi vi phạm, không tự cho ngoại lệ vì "chạy vẫn được" — [R12: rule skill là ràng buộc cứng](../../principles/iron_rules.md).
- **Kiểm xong không để lại rác**: mọi phép đối chiếu tập mã làm **trong bộ nhớ, một lệnh** (`Compare-Object` / `awk` một lượt qua 2 file nguồn). CẤM file trung gian, CẤM `<(…)` (trên git-bash Windows nó thành file thật trong `/tmp`), CẤM ghi ra ngoài `{code_repo_root}` + `{qa_artifacts}` — [R6b](../../principles/iron_rules.md).

## 2. Cấm Chờ Tĩnh, Cấm Nhảy URL (R7 · R9)

- **Phải đúng**: không chỗ nào gọi `Sleep`, `Go To`, **`Reload Page`**. Chờ → `Wait Until *`; tới màn → bấm menu/nút như người dùng; reset màn → đóng+mở lại bằng click.
- **Đọc gì**: mọi file trong `tests/`, `actions/`, `resources/`, `configs/`, **`libraries/`**. Bỏ `libraries/` là bỏ đúng chỗ hay bị lách nhất (keyword bọc đặt ở đó).
- **Dấu hiệu sai** — dòng **gọi** keyword, tức dòng thụt đầu dòng và tên nằm trong một ô riêng (cách nhau ≥2 space **hoặc 1 tab**):
  - ❌ `    Sleep    3s` · `<TAB>Sleep<TAB>3s` · `    Go To    ${URL}` · `    Reload Page`
  - ✅ không tính: `Sleep Until Ready` ở **sát lề** (đó là dòng đặt tên keyword) · `    Verify User Go To Dashboard` (chữ "Go To" nằm giữa tên keyword, cách nhau 1 space) · chữ nằm sau dấu `#` (ghi chú)
  - ⚠️ **Nhớ soi cả file dùng TAB**: Robot cho phép tách ô bằng tab, nên `Sleep` có thể không nằm sau 4 space như thường thấy. Đây là chỗ đã từng lọt sạch.
- **Ghi vào báo cáo**: `đã đọc X/Y file — n vi phạm` + `file:dòng` từng chỗ.
- **Không đạt** → thay chờ tĩnh bằng `Wait Until *`, thay nhảy URL bằng bấm chuột. Ngoại lệ duy nhất được phép: `Open Browser` vào trang login, 1 lần ở Suite Setup.
- Tên keyword / ghi chú có chứa chữ `Sleep`, `Go To` không tính vi phạm ở đây, nhưng phải **đổi tên** — [convention §4](./auto_coding_convention.md).

## 3. Cấm Lách Bằng Python / JavaScript / Keyword Động (R12)

- **Phải đúng**: việc đã cấm ở mục 2 và 4 thì cấm ở **mọi ngôn ngữ**, không chỉ cấm đúng chữ đó trong `.robot`.
- **Đọc gì**: mọi file `.py` trong `libraries/`, mọi keyword có gọi JavaScript, mọi chỗ gọi keyword bằng biến.
- **Dấu hiệu sai**:
  - chờ tĩnh viết bằng Python: `time.sleep`, `Thread.sleep`, `threading.Event().wait`, `implicitly_wait`
  - nhảy URL: `driver.get(...)`, `window.location`, `location.href`, `history.go/back`, hoặc `Execute Javascript` / `Execute Async Javascript` làm việc đó
  - bật headless: `options.add_argument("--headless")`
  - gọi keyword bằng biến: `Run Keyword    ${ten_keyword}` — cách này làm mọi phép soi theo tên trở nên vô nghĩa
- **Ghi vào báo cáo**: từng chỗ tìm được + kết luận nó là gì. Chỗ nào là chờ tĩnh / nhảy URL / headless viết bằng ngôn ngữ khác → **vi phạm**, tính vào chính mục nó lách (2 hoặc 4). Chỗ gọi keyword bằng biến → phải liệt kê **mọi giá trị biến đó có thể nhận** và chứng minh không có keyword bị cấm; không chứng minh được = vi phạm.
- ⚠️ **Mục 2 đọc thấy sạch mà mục này có vi phạm → mục 2 KHÔNG được ghi đạt**: việc bị cấm vẫn còn, chỉ đổi cách viết.

## 4. Cấm Chạy Ẩn Cửa Sổ (headless — R12)

- **Phải đúng**: browser mở thật + phóng to. Thiếu màn hình để chạy → DỪNG báo người dùng, không tự bật headless.
- **Đọc gì**: `configs/` (nhất là chỗ khai `${BROWSER}` và tham số mở browser), keyword mở browser trong `actions/common/`, mọi `.py` trong `libraries/`.
- **Dấu hiệu sai**: chữ `headless` ở bất kỳ dạng nào — `--headless`, biến `${HEADLESS}`, biến môi trường `..._HEADLESS`, `Set Variable If ... headless`, `options.add_argument`.
- **Ghi vào báo cáo**: `đã đọc X/Y file — n vi phạm` + vị trí.
- **Không đạt** → xoá cách bật headless (kể cả trong `.py`).

## 5. Mã Test Tự Động Phải Trùng Mã Testcase Tay (R3 · R2)

- **Phải đúng**: tập mã `KB-*` trong `.robot` = tập mã các dòng `automate` trong testcase tay **trừ `excluded_ids[]`**. Không thiếu, không thừa.
- **`excluded_ids[]`** (`datatest/{id}_gen_manifest.yaml`, do Step 01 ghi) = case có **`@target` ∉ {`robot`, vắng}** (hôm nay là `playwright`, giá trị mới upstream thêm cũng tính) — consumer khác sinh, skill này KHÔNG được sinh. `@target` là tag trong `.feature`, **không phải cột trong `.md`** → đừng cố tìm nó ở bảng markdown; lấy nguyên danh sách từ manifest. Không có file/không có `.feature` → coi như rỗng (mặc định `@target: robot`).
- **Đọc gì**: `tests/*.robot` (lấy mã ở `[Tags]` từng test) và **`{manual_testcase_path}`** (lấy mã ở các dòng có cột `Exec` = `automate`) — path do Step 01 resolve rồi truyền vào, có thể là bản nested `{qa_artifacts}/{id}/{id}_…md` **hoặc** bản flat legacy `{qa_artifacts}/{id}_…md`. ⛔ **KHÔNG tự ghép path**: ghép bản nested ở lane HUB legacy sẽ đọc trống → `B = 0` → FAIL oan.
- **Cách làm**: so 2 tập mã trong bộ nhớ, rồi ghi **số đếm** `A/B/C` + liệt kê **chỉ mã lệch**. Cấm in cả 2 danh sách mã (suite lớn = hàng nghìn mã in ra vô ích). Chỉ nói "đã đối chiếu, khớp" mà không có số đếm là không đủ.
- **Dấu hiệu sai**:
  - mã có trong `.robot` mà không có trong testcase tay → mã thừa hoặc tự đặt → xoá, hoặc sửa về mã đúng.
  - mã có ở dòng `automate` mà không có test → thiếu test → viết bổ sung.
- **Ghi vào báo cáo**: `số mã trong .robot = A · số mã automate trong testcase tay (đã TRỪ excluded_ids) = B · số mã bị loại vì @target:playwright = C` + danh sách mã lệch (nếu có). ⚠️ Ghi `B` **trước khi trừ** rồi so với `A` là tự tạo ra lệch giả — phải trừ trước, và nêu `C` riêng để người đọc thấy phần bị loại đi đâu.
  ⚠️ **A hoặc B bằng 0 là dấu hiệu đọc sai chỗ** (sai file, hoặc cột `Exec` nằm khác vị trí tưởng) — kiểm lại, **đừng kết luận "khớp"**.
- Case `pending` / `[TBD]` **vẫn phải có test mang mã** → vẫn nằm trong danh sách `.robot`.

## 6. File Test Không Chứa Chi Tiết Kỹ Thuật (R4)

- **Phải đúng**: `tests/*.robot` chỉ gọi keyword. Locator, câu SQL, định nghĩa keyword nằm ở `.resource`.
- **Đọc gì**: mọi file trong `tests/`.
- **Dấu hiệu sai**: có mục `*** Keywords ***` trong file test · locator viết thẳng (`xpath=`, `css=`, `css:`, `Get WebElements`) · câu `SELECT ...` · chuỗi kết nối DB (`jdbc:`).
- **Ghi vào báo cáo**: `đã đọc X/Y file test — n vi phạm` + vị trí.
- **Không đạt** → chuyển định nghĩa keyword sang `{Page}Keywords.resource`, locator sang `{Page}Variables.resource`, dữ liệu sang `datatest/`.

## 7. Mỗi Case Là Một Test Riêng (R11)

- **Phải đúng**: không gom nhiều case vào một test.
- **Đọc gì**: mọi file trong `tests/`.
- **Dấu hiệu sai**: có `[Template]` hoặc `Test Template` · một test chạy vòng lặp qua nhiều bộ dữ liệu của nhiều case khác nhau.
- **Ghi vào báo cáo**: vị trí từng chỗ.
- **Không đạt** → tách thành N test riêng, mỗi test kiểm đúng kết quả mong muốn của case đó.

## 8. Test Phải Mang Đủ Nhãn Phân Loại Của Case (R3)

- **Phải đúng**: ngoài mã `KB-*`, mỗi test mang **đúng nguyên văn** `@block:`, `@risk:`, `@rule:` (và `@oracle:` nếu có) của case gốc.
- **Vì sao quan trọng**: nhiều phép kiểm khác **lọc case theo nhãn** (phép đếm chỉ soi case `@rule:grid-base`; nhóm lỗi và nhóm bảo mật lọc theo `@block:`; oracle-coverage lọc theo `@oracle:`). Test chỉ mang `KB-*` thì các phép kiểm đó soi **0 case rồi báo đạt** — mất phần kiểm mà không ai thấy.
- **Đọc gì**: `[Tags]` của từng test trong `tests/*.robot` (nhãn có thể **viết tiếp ở dòng dưới bằng `...`** — phải đọc cả dòng tiếp đó, nếu không sẽ kết luận thiếu nhãn oan), đối chiếu với nhãn của scenario cùng mã trong `{qa_artifacts}/{id}/{id}_testspec.feature`.

### 8a. Có đủ 5 nhóm nhãn

- **Dấu hiệu sai**: test có mã `KB-*` nhưng `[Tags]` thiếu **bất kỳ** nhóm nào trong `@block:` · `@tech:` · `@rule:` · `@risk:` · `@oracle:`.
- **`@oracle:` đếm theo SỐ LƯỢNG, không chỉ có-hay-không**: một scenario mang nhiều `@oracle` (vd `@oracle:ui` + `@oracle:db`) thì test phải mang **đủ số đó**. Thiếu 1 nhãn = mất phép kiểm oracle-coverage của R11 cho tầng đó (nó lọc case theo nhãn → soi 0 case → báo đạt im lặng). So số nhãn `@oracle` của từng mã giữa `.feature` và `.robot`.
- **Kèm theo — suite-level `Test Tags`**: mỗi file `.robot` phải khai `Test Tags` ở `*** Settings ***` mang unit id (`@scr:<unit_id>` / `@svc:<unit_id>`) theo [step-03 §2](../../steps/step-03-generate-suite.md). Thiếu → vi phạm; dùng `Force Tags` (đã deprecated ở RF 6) → vi phạm, đổi sang `Test Tags`.
- **Ghi vào báo cáo**: `đã đọc X/Y test — n test thiếu nhãn` + `mã case | nhãn thiếu | file:dòng`.
- **Không đạt** → thêm nhãn còn thiếu, lấy **đúng giá trị** từ case gốc, không tự đặt giá trị mới.

### 8b. Nhãn đúng nguyên văn (chỉ làm khi có file `.feature`; lane HUB cũ thì dừng ở 8a)

- **Cách làm**: với từng mã case, đặt cạnh nhau nhãn trong `.feature` và nhãn trong `.robot`, so từng nhãn.
- **Dấu hiệu sai**: nhãn có ở `.feature` mà mất trong `.robot` (nặng nhất là mất `@rule:`) · nhãn có trong `.robot` mà `.feature` không có, hoặc giá trị bị đổi.
- **Ghi vào báo cáo**: bảng `mã case | nhãn bị mất | nhãn tự thêm/sai giá trị` — chỉ ghi case lệch, **không** kẻ bảng case đạt.
- **Nhãn do skill tự thêm, KHÔNG tính là "tự thêm"** (đừng chấm vi phạm vì `.feature` không có chúng): `pending` · `tbd` · và **tên bucket đi kèm `pending`**: `timeout` · `mock` · `security` · `destructive` (R10 quy định `[Tags]  pending  <bucket>`).

## 9. Phân Tầng POM Đúng Vai (R4 · robot §1 · structure §2-§3)

- **Phải đúng**: mỗi thứ nằm đúng tầng của nó — locator ở `*Variables.resource`, keyword ở `*Keywords.resource`, chỉ `tests/` có `*** Test Cases ***`, và chiều import đi một hướng từ trên xuống.
- **Đọc gì**: mọi file trong `tests/`, `actions/pageObject/`, `actions/serviceObject/`, `actions/common/`, `configs/`. Đọc cả phần `*** Settings ***` của từng file — đó là nơi chiều import hiện ra.
- **Dấu hiệu sai**:
  - locator (`xpath=`, `css=`, `id=`) khai thẳng trong `*Keywords.resource` thay vì file Variables cùng page · file Variables có mục `*** Keywords ***` · file trong `pageObject/`/`serviceObject/` có `*** Test Cases ***`
  - `serviceObject/` có locator hoặc gọi keyword SeleniumLibrary
  - file test import lẻ từng `*Keywords.resource` thay vì `configs/imports.resource` · file Variables import file Keywords · hai page ngang hàng import lẫn nhau
  - có page/service mới sinh ra mà `configs/imports.resource` không khai — thiếu import thì `robot --dryrun` đỏ ở Step 03, mất trọn 1 vòng
  - keyword trong `actions/common/` chạm locator / entity / bảng DB của **một màn cụ thể** — kể cả keyword dọn dữ liệu của màn đó (nội dung dọn gì là việc của Page, không phải BaseTest)
- **Ghi vào báo cáo**: `đã đọc X/Y file — n vi phạm` + `file:dòng`, nêu rõ mỗi chỗ sai tầng nào và phải chuyển sang tầng nào.
- **Không đạt** → chuyển đúng tầng; sửa `*** Settings ***` về chiều một hướng; khai import còn thiếu.

## 10. Không Viết Lại Cái Đã Có (DRY — robot §4 · §5)

- **Phải đúng**: một hành vi chỉ có một keyword; cụm code lặp được trích ra dùng chung.
- **Đọc gì**: **danh sách tên keyword của toàn bộ** `actions/` (gồm `common/BasePage`, `common/BaseTest`, mọi Page/Service Keywords), và phần `*** Settings ***` + Setup/Teardown của mọi file trong `tests/`.
- **Cách làm**: liệt kê tên keyword ra rồi soi hai chiều — trùng **tên**, và trùng **hành vi** dù khác tên (`Wait Until Text Visible` vs `Page Should Contain Text`, `Check X Displayed` vs `Verify X Visible`). Chỉ trùng tên là chưa đủ để kết luận đạt.
- **Dấu hiệu sai**: hai keyword cùng hành vi · cùng một khối bước xuất hiện ≥3 chỗ mà không có keyword chung · block Suite Setup/điều hướng copy-paste vào từng `.robot` thay vì nằm ở `actions/common/SuiteFixtures.resource` · ≥3 locator chỉ khác một tham số khai thành N biến rời thay vì một template.
- **Ghi vào báo cáo**: `đã soi X/Y keyword — n cặp trùng` + danh sách cặp trùng kèm `file:dòng` của cả hai, và giữ cái nào.
- **Không đạt** → giữ một đại diện, sửa mọi chỗ gọi sang nó; trích khối lặp thành keyword chung.
