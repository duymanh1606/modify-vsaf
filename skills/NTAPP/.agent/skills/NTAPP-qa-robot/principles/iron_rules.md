# IRON RULES — Quy tắc bất biến của workflow NTAPP QA Robot

## Áp dụng theo `surface_type`
* **`ui`** (Chrome, `@scr`, có `ui_schema`): Selenium POM, áp dụng R7 và R9 đầy đủ.
* **`service`** (no-UI, `@svc`, không `ui_schema`): RequestsLibrary POM, R7/R9 thay bằng phiên bản service.
* **Cả hai:** R1-R6, R7d, R8, R10-R16.

---

## R1. ZERO-FABRICATION (Cấm bịa dữ liệu)
* Chỉ dùng 3 input tại `{qa_artifacts}/{id}/`: `.feature` (nguồn chính sinh script), `fixtures.yaml` và manual testcase. Expected chỉ lấy từ `.feature`.
* Cấm tự bịa dữ liệu, URL, endpoint hoặc expected. Thiếu thông tin -> để `[TBD]` và dừng báo user.
* **Hằng số môi trường** (URL/endpoint/port/tên tài khoản — KHÔNG áp cho expected): lấy thêm từ `data_sources.yaml`, fixtures slice cùng feature, config code repo ([step-01 §2.6e](../steps/step-01-parse.md)). `[TBD]` chỉ hợp lệ sau khi tra hết 3 nguồn.

## R2. MAP 1-1 (Cấm tóm tắt / bỏ scenario)
* Mỗi scenario automate map 1-1 thành 1 Test Case. Cấm nhồi 2 scenario vào 1 test.
* Cấm bỏ UI gesture (focus out, blur, tab out, paste, Enter, double-click) — mọi gesture phải được thực thi thật.
* **Map 1-1 tính theo hành vi được thực thi, không theo số dòng trong `.robot`.** Gom chuỗi micro-step thành 1 keyword nghiệp vụ là ĐÚNG; lặp ở ≥3 case thì BẮT BUỘC gom. Kiểm bằng đọc thân keyword.
* Mức gom theo [robot §5](../references/automation/auto_robot_rules.md) (1 keyword = 1 trách nhiệm) — cấm gom cả case vào 1 keyword. Chỉ gom bước thao tác; **assert giữ tường minh**: giá trị mong đợi truyền qua tham số, cấm assert tên chung chung (`Should Be Complete` / `Valid` / `Correct`).

## R3. TRACEABILITY (Truy vết)
* Mã Test Case (`KB-{id}-NN`) ở tag và tên phải khớp 1-1 với manual.
* Propagate nguyên văn nhãn phân loại: `@block:*`, `@tech:*`, `@rule:*`, `@risk:*`, `@oracle:*`.
* Tên Page Object / Service Object phải khớp tài liệu L2/L3 / Contract Map, cấm tự phát sinh.

## R4. POM & QUALITY GATE (Bắt buộc Object Model)
* File `.robot` chỉ chứa Settings, Variables (hằng số suite), và Test Cases. **TUYỆT ĐỐI KHÔNG chứa `*** Keywords ***`** hoặc locator/URL/SQL thô. Đưa hết về `.resource`.
* Reset state vô điều kiện sau mỗi test case: đóng/mở lại modal bằng click, điều hướng lại từ menu. Cấm dùng `Go To` / `Reload Page` để reset.

## R5. MISSING-INPUT HANDLING
* Thiếu file input (chưa approve/không readable) -> DỪNG ngay, cấm bịa mock, báo rõ explicit path file thiếu cho user.
* **Trước MỌI câu hỏi user về data/môi trường: BẮT BUỘC đọc `{qa_artifacts}/data_sources.yaml`** (+ fixtures slice cùng feature + config code repo) rồi mới lập danh sách thiếu. Hỏi thứ file đó đã cấp = vi phạm R5.

## R6. SINGLE-SOURCE PATH
* Ghi code relative tại `{code_repo_root}` (cấm ghi ngoài dự án/file tạm).
* File resource đặt tại `actions/pageObject/{Page}/` (ui) hoặc `actions/serviceObject/{Service}/` (service).

### R6b. CẤM FILE RÁC
* Cấm ghi file ra ngoài dự án (cấm `/tmp`, `AppData`, scratchpad...).
* Cấm sinh file tạm. So sánh mã parity (R3) thực hiện trực tiếp trong memory.

## R7. LOCATOR STRATEGY & WAITS (UI)
* Locator dò từ code FE tĩnh. Cấm absolute XPath. Tên biến dạng `${LOAI_ELEMENT}_${CHUC_NANG}`.
* Dùng Smart Wait, cấm `Sleep` tĩnh, cấm trộn implicit wait với explicit wait.
* **Self-Healing:** Dò lại locator tĩnh, ghi đè Variables, retry tối đa 3 lần. Ghi manifest `healed: true`.
* **Biến thể no-source (`live-dom`):** Soi DOM ứng dụng ở Step 02 trước khi generate, cấm suy DOM runtime lúc chạy test (trừ self-heal).

### 5 Stopping Errors (Dừng pipeline ngay):
1. `id` không có trong WBS/spec.
2. Spec L2/L3/UX chưa approve.
3. Drift `.md` ↔ `.feature` -> lấy theo `.feature` và dừng báo user.
4. Locator không tìm được / không self-heal được.
5. Assertion fail do app có bug thật -> DỪNG NGAY, cấm retry/self-heal, cấm sửa test để né bug.

### R7s. Biến thể SERVICE (no-UI)
* Định vị qua Contract (endpoint, path, schema, error code).
* Chờ async qua `Wait Until Keyword Succeeds`, cấm dùng `Sleep` tĩnh.
* FAIL do transient -> retry ≤3; FAIL do contract/assert -> bug thật, DỪNG ngay.

### R7b. MULTI-CONNECTION RESOLUTION
* Mở kết nối ở Suite Setup, đóng ở Suite Teardown.
* DB query select rỗng -> dừng test. Resolver dynamic data phải reuse trước seed sau, seed đủ số lượng.
* Tên bản ghi test trên môi trường dùng chung phải unique per-run (`$uuid` / `$timestamp`).

### R7d. TIỀN TỐ `auto_` (áp cho cả `ui` và `service`)
* Định danh **kiểu chuỗi** automation ghi vào hệ thống dùng chung phải **BẮT ĐẦU** bằng `auto_` (tiền tố, không phải hậu tố). Dạng `auto_<nhãn>_<run-marker>_<uuid8>` → dọn môi trường bằng một mệnh đề `LIKE 'auto\_%'`. Override qua `AUTO_DATA_PREFIX`.
* **Ngoại lệ:** (1) trường chỉ nhận số — giữ định dạng số, unique bằng phần số ngẫu nhiên; (2) ca biên độ dài (`<char>×N`) — ghi lý do miễn trừ vào manifest.
* **Không phải ngoại lệ:** payload SQL-like / XSS / khoảng trắng VẪN gắn tiền tố (payload còn nguyên trong chuỗi).

## R8. DATA-DRIVEN & DYNAMIC RESOLUTION
* Lấy dữ liệu từ fixtures, cấm hardcode.
* 1 case = 1 Test Case tường minh, cấm dùng `[Template]`. **"Tường minh" = 1 test cho 1 mã case (giữ tag + traceability), KHÔNG có nghĩa phải inline từng bước** — thân test gọi keyword nghiệp vụ với data của case đó; chuỗi bước đã có keyword thì tái dùng.
* Ký tự biên `<char>×N` expand qua `Evaluate  "char" * N`.

## R9. NAV-BY-CLICK (Cấm `Go To` / `Reload Page` UI)
* Cấm `Go To` / `Reload Page` như **đường tắt điều hướng**. Chỉ dùng `Open Browser` trang login 1 lần ở Suite Setup.
* Di chuyển tới màn qua Click. Reset state bằng click đóng/mở lại modal.

### R9b. NGOẠI LỆ — khi chính hành vi được kiểm là điều hướng URL
Scenario mà **đối tượng kiểm thử chính là URL/reload** thì `Go To` / `Reload Page` là *bước nghiệp vụ bắt buộc*, không phải lách rule — được dùng. Ba nhóm hợp lệ:
1. **Deep-link**: `.feature` yêu cầu mở URL kèm queryParam để kiểm prefill / hydrate filter / nhảy trang.
2. **Tải lại trang**: ca kiểm giữ trạng thái sau F5 (vd "giữ bộ lọc sau khi tải lại trang").
3. **Lịch sử trình duyệt**: ca kiểm back/forward giữ state.

Điều kiện áp dụng — thiếu 1 trong 3 là quay về cấm:
* Mệnh đề `When` của scenario nêu rõ mở URL / reload / back-forward. Suy diễn "cho nhanh" không tính.
* Chỉ dùng đúng ở bước tái hiện hành vi đó, KHÔNG dùng để tới màn hay reset state ở bước khác trong cùng test.
* Test mang tag `nav-by-url` để gate cơ học lọc ra và người đọc biết đây là ngoại lệ có chủ đích.

Ngoài 3 nhóm trên: cấm như cũ. Cần tới màn thì click.

## R10. DEFERRED-RUN SAFETY GATE
* Phân nhóm nhạy cảm (`timeout`, `mock`, `security`, `destructive`) -> Hỏi user **từng bucket một**: mỗi bucket = 1 câu hỏi riêng (chạy / hoãn), chờ trả lời xong mới hỏi bucket kế. CẤM gộp nhiều bucket vào 1 câu, CẤM gộp bucket với câu hỏi khác (env, prereq…) -> Nếu chọn hoãn -> gắn tag `pending <bucket>`, đặt bước đầu là `Skip PENDING (<bucket>)`.
* `deferred_run_policy`: `ask` (default — hỏi từng bucket một) · `run-all` / `defer-all` (non-interactive, không hỏi). Mọi mode ghi quyết định vào `run_state` + `r10_decisions`.

## R11. ANTI-STUB / ORACLE-FIDELITY
* Expected/Assert lấy duy nhất từ `.feature`, cấm dùng expected từ code implementation. Cấm dùng assert baseline.
* Executor nhận `${expected}` phải tiêu thụ trong assert.
* Mỗi `@oracle` tag phải assert đầy đủ (ui, api, db, msg, log).
* Dòng chứa `[TBD-spec/data]` -> gán `Skip [TBD]` + tag `tbd`, cấm fake pass.

## R12. RULE SKILL > GIẢI PHÁP RUNTIME (Cấm lách)
* Rule skill là ràng buộc **CỨNG**. Gặp trở ngại runtime (thiếu display/driver/proxy) -> DỪNG báo user + đề xuất trong khuôn khổ rule, cấm tự lách. Chỉ vượt rule khi user yêu cầu rõ bằng lời.
* **CẤM headless mọi hình thức:** `--headless`, `${HEADLESS}`, env var, `Set Variable If ... headless`, `options.add_argument`. Browser giữ HEADED + `Maximize Browser Window`. Môi trường không có desktop (viewport 0px -> `element has zero size`) -> DỪNG báo user chạy máy có desktop, KHÔNG bật headless để "sửa".
* Việc bị cấm ở R7/R9 thì cấm ở **mọi ngôn ngữ**: `time.sleep`/`Thread.sleep`/`implicitly_wait`, `driver.get`/`window.location`/`history.back`, hoặc gọi keyword bằng biến để giấu tên. *(Ngoại lệ R9b áp cho cả mục này — ca deep-link/reload/back-forward được dùng đúng lệnh điều hướng của nó.)*
* Gate cơ học ở Step 02 + Step 03: quét theo [gate_commands §3-§4](../references/automation/auto_gate_commands.md).

## R13. COMPOUND ORACLE
* 1 mệnh đề expected = 1 assert. Đếm `k` mệnh đề expected -> sinh `≥k` assert. Miễn trừ style thị giác.

## R14. VOLUME/COUNT FIDELITY
* Ca grid/list phải bảo đảm đủ N bản ghi khả dụng, assert theo COUNT thực tế.
* Cấm assert tautology (so actual với chính actual). Vế kỳ vọng phải là hằng số hoặc fixture.

## R15. SEED CODE ROBUST
* Resolver phải query reuse trước, seed sau, honor count.
* File `.py` sinh ra phải chứa header hợp lệ: `# id: <ID> | dd_version: vN` ở 10 dòng đầu.

## R16. SINH LẠI THEO TỪNG CASE
* Ghi manifest `datatest/{id}_gen_manifest.yaml` — **file trạng thái duy nhất** của skill (schema: `id`, `gen_run_id`, `generated_at`, `excluded_ids`, `r10_decisions`, `touched_files` (`path`, `round` — lượt sinh đầu = `0`), `cases` (`run_state`, `bucket`, `reason`, `sync_action`, `src_hash`, `last_gen_run`), `locators` (`healed: true`)). Step 01 tạo, Step 02/03 merge thêm — cấm rewrite, cấm tách file thứ hai.
* So sánh `src_hash` và `run_state` để phân loại: Giữ nguyên / Sinh lại / Thêm / Xoá.
* Giữ nguyên healed locator. Cấm xoá file suite rồi ghi lại từ đầu.
* Báo cáo thống kê: `giữ nguyên: k · sinh lại: m · thêm: n · xoá: p`.
