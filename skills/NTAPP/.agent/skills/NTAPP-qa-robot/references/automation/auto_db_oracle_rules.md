# QUY TẮC ORACLE DATABASE (DB VERIFICATION RULES)

Áp dụng khi scenario có tag `@oracle:db` + dòng `Then DB: ...` (vd "chỉ 1 composite_requests được tạo", "lưu đủ 100 ký tự"). Mục tiêu: thay placeholder `Verify DB` (chỉ `Log`) bằng query + assert thật. Map 1-1: mỗi dòng `DB: ...` → 1 keyword DB.

## 1. Vị trí trong POM — KHÔNG tách file DB riêng
Theo [auto_framework_structure.md §2.1](./auto_framework_structure.md) (common = function dùng chung; GlobalConstants chứa "Database config"):

| Tầng | Nội dung | Đặt ở |
|---|---|---|
| **Hạ tầng chung** | `Library DatabaseLibrary`; keyword `Connect To Database` / `Disconnect From Database` (tên keyword **tiếng Anh** — [auto_robot_rules §4](./auto_robot_rules.md)) | `actions/common/BasePage.resource` (chung như SeleniumLibrary) |
| **Tham số kết nối** | host/port/db/user/pass | `actions/common/GlobalConstants.resource` |
| **Verify DB theo CHỨC NĂNG** | SQL + assert riêng từng màn/operation (`composite_requests`, `transfers`...) | *(ui)* viết trong `<Page>Keywords.resource`, cạnh keyword verify UI · *(service)* viết trong `<Service>Keywords.resource`, cạnh keyword verify response (KHÔNG có verify UI) |
| Connect / Disconnect | gọi ở Suite Setup / Suite Teardown | `tests/*.robot` |

→ Hạ tầng connect viết 1 lần ở BasePage, dùng lại. Check DB nghiệp vụ nằm **cùng file Page** với keyword UI của màn đó. Test Suite `.robot` chỉ gọi high-level keyword, KHÔNG chứa SQL (đồng nhất R4 — `.robot` cấm kỹ thuật DOM/locator, áp tương tự cho SQL).

## 2. Khi nào wire — quyết định theo REGISTRY, không phán đoán env lúc generate
Wire khi `@oracle:db` (KHÔNG phải `@manual-verify`) **và** `source_id` liên quan có khai báo trong `data_sources.yaml`. Env var chỉ tồn tại lúc **RUN** — generator CẤM lấy "lúc generate chưa thấy env" làm lý do bỏ resolver rồi thay bằng biến env đặt tay:

- **Registry CÓ source** (`db:` env_prefix / `create_api`) → PHẢI sinh resolver thật đọc `${<env_prefix>_*}` theo pattern **Tier 0 → Tier 1: check DB tìm bản ghi có sẵn trước, không có thì seed qua API** ([iron_rules R7b](../../principles/iron_rules.md)). Runtime thiếu env → resolver tự fail rõ ràng (`Should Not Be Empty ... msg=cần env <PREFIX>_*`) đúng case đó — không kéo đổ case khác.
- **Registry KHÔNG có source** → giữ stub `Log` + ghi chú "thiếu registry entry" ([iron_rules](../../principles/iron_rules.md) R1 cấm bịa, R5 thiếu input thì dừng).
- **Biến env đặt tay** (vd `<ENV_PREFIX>_*_SUBID`) chỉ được sinh làm **override tùy chọn** (user set thì tôn trọng — check trước rồi mới resolve). TUYỆT ĐỐI không để env tay là đường lấy data DUY NHẤT khi registry đã có nguồn.
- **Field `[TBD]` trong body `create_api`** (registry thiếu giá trị, không có cách tra) → vẫn sinh resolver, đọc field đó từ env `${<env_prefix>_<FIELD>}` + liệt kê vào mục "Data gaps" của generation report — KHÔNG âm thầm bỏ cả operation.

TUYỆT ĐỐI không hardcode connection để "chạy cho có".

## 3. Thư viện + driver
Driver theo **DB thật** khai ở `data_sources.yaml` (`<source>.db`) hoặc user cung cấp — **CẤM mặc định cứng Postgres**. `${DB_API}` để `[TBD]`, user set qua env `<ENV_PREFIX>_DB_API` (`psycopg2` Postgres · `pymysql` MySQL/MariaDB · `oracledb` Oracle). Cài driver tương ứng.
```
pip install robotframework-databaselibrary
pip install <driver>   # theo DB thật: psycopg2-binary | pymysql | oracledb
```

## 4. Connection — KHÔNG hardcode (R1)
Trong `GlobalConstants.resource`, đọc từ env var (SCREAMING_SNAKE_CASE, giống `${BASE_URL}` — [coding_convention §5](./auto_coding_convention.md)):
```robotframework
${DB_API}     %{<ENV_PREFIX>_DB_API=[TBD]}   # theo DB thật, KHÔNG mặc định Postgres
${DB_NAME}    %{<ENV_PREFIX>_DB_NAME=[TBD]}
${DB_USER}    %{<ENV_PREFIX>_DB_USER=[TBD]}
${DB_PASS}    %{<ENV_PREFIX>_DB_PASS=[TBD]}
${DB_HOST}    %{<ENV_PREFIX>_DB_HOST=[TBD]}
${DB_PORT}    %{<ENV_PREFIX>_DB_PORT=[TBD]}   # theo DB thật: 5432 Postgres · 3306 MySQL · 1521 Oracle — KHÔNG mặc định cứng (§3)
```
- Credential CẤM commit git — chỉ truyền qua env lúc chạy.
- Connect 1 lần ở **Suite Setup**, disconnect ở **Suite Teardown** — KHÔNG connect/disconnect mỗi test case.

## 5. Query — luôn parameterize
Dùng tham số `%s` (hoặc `:name`) + truyền value qua **`parameters=${list}`** (tạo bằng `Create List`), CẤM nối chuỗi vào SQL. ⚠️ **CẤM truyền value positional** (`Query  SELECT ... %s  ${name}`) — arg thứ 2 của `Query` là `sansTran`, không phải param → `%s` không bind → lỗi SQL `near '%s'`.

## 6. Template

**Hạ tầng — thêm vào `actions/common/BasePage.resource`:**
```robotframework
*** Settings ***
Library    SeleniumLibrary
Library    DatabaseLibrary          # ← thêm
Resource   GlobalConstants.resource

*** Keywords ***
Connect To Main Database              # gọi ở Suite Setup
    Connect To Database    ${DB_API}    ${DB_NAME}    ${DB_USER}    ${DB_PASS}    ${DB_HOST}    ${DB_PORT}

Disconnect From Main Database         # gọi ở Suite Teardown
    Disconnect From Database
```

**Theo feature — viết thẳng trong `<Page>Keywords.resource` của màn đang test (thay stub `Verify DB`):**

> ⚠️ **VÍ DỤ minh hoạ** — tên file (`ComposePage/ComposeKeywords.resource`), tên bảng (`composite_requests`...), tên cột, tên keyword bên dưới đều là minh hoạ cho feature Compose. **PHẢI thay bằng Page / bảng / cột / oracle thật** của màn đang test (đọc từ dòng `DB: ...` trong `.feature` + schema thật). KHÔNG mặc định ghi vào `ComposePage`.
```robotframework
Composite Count By Name Should Be    # ← map dòng "DB: chỉ 1 composite_requests"
    [Arguments]    ${name}    ${rows}=1
    ${p}    Create List    ${name}
    ${r}    Query    SELECT * FROM composite_requests WHERE name = %s    parameters=${p}
    Length Should Be    ${r}    ${rows}

Composite Sub Link Count Should Be   # ← map dòng "DB: 3 rows composite_sub_links"
    [Arguments]    ${composite_id}    ${count}
    ${p}    Create List    ${composite_id}
    ${r}    Query    SELECT * FROM composite_sub_links WHERE composite_id = %s    parameters=${p}
    Length Should Be    ${r}    ${count}
```
> ⛔ **Tên keyword BẮT BUỘC tiếng Anh, không ngoại lệ** ([auto_robot_rules §4](./auto_robot_rules.md) · [coding_convention §1/§4](./auto_coding_convention.md)) — đặt cạnh các keyword verify UI của cùng màn, cùng convention V + N Title Case tiếng Anh (vd `Profile Name Value Should Be`). Chỉ **tên Test Case** trong `.robot` mới được bám tiếng Việt theo manual.

## 7. Teardown dữ liệu test (R4 test độc lập)
Để lưu trữ lịch sử và audit trên Staging, CẤM tự động xóa bản ghi DB do testcase tạo ra trong teardown. `[Teardown]` của test case chỉ thực hiện reset trạng thái giao diện UI (đóng modal, click quay lại trang list), không thực hiện bất kỳ câu lệnh SQL DELETE nào.
Dữ liệu tạo ra bắt buộc phải mang định danh unique per-run (timestamp/UUID) để chạy lại không đụng nhau, và **bắt đầu bằng tiền tố `auto_`** theo [iron_rules R7d](../../principles/iron_rules.md) — dạng `auto_<nhãn>_<run-marker>_<uuid8>`. Nhờ tiền tố này, dọn môi trường về sau chỉ cần một mệnh đề `LIKE 'auto\_%'`. Hai ngoại lệ: trường chỉ nhận số (số điện thoại, mã số thuế, numeric) và ca biên độ dài (giá trị phải đúng N ký tự).

## 8. Tầng `@manual-verify`
Oracle ghi `(manual-verify)` (vd audit log) → GIỮ placeholder `Log`, KHÔNG cố wire — tester verify tay. Đừng bịa query cho tầng này.

## 9. Dịch `DB:` → SQL (dòng `DB:` là ý định, dịch lại từ ngữ nghĩa — không bám literal)
- **"Không có record mới" = count-delta** (`COUNT(*)` trước == sau thao tác). CẤM dịch thành đếm theo nhãn (`COUNT WHERE <tên> = 0`).
- **Key tra cứu theo định danh, kết hợp nhiều trường để khoanh đúng 1 bản ghi**: dùng PK (từ response create) và/hoặc khóa nghiệp vụ UNIQUE, có thể kết hợp thêm trường data đã biết của chính case. Tránh chỉ dựa nhãn người-đọc đơn lẻ (không unique). Kiểm *giá trị* một cột nhãn thì tra bản ghi theo định danh rồi đọc cột đó.
- **Re-run sạch bằng teardown keyed theo định danh** (xoá theo PK/composite_id của record case tạo, đúng thứ tự FK) — xem §7.
- **Tạo mới = kiểm lưu đủ trường:** `SELECT` bản ghi vừa tạo, assert **từng cột** khác NULL/rỗng (kể cả bảng phụ thuộc + số dòng). Không so nguyên văn (cột có thể mã hóa) trừ khi manual testcase ghi rõ lưu nguyên bản. Chỉ `COUNT(*) = 1` hoặc chỉ kiểm cột trạng thái là KHÔNG đủ.
- **Cấm tự thêm comment diễn giải rồi code theo nó.**

## 10. Đa-connection cho `$db.query`/`$seed.*` (setup data — khác oracle assertion ở §1-9)

Hạ tầng connect ở §1/§4/§6 áp dụng lặp lại cho MỌI connection khai trong `{qa_artifacts}/data_sources.yaml`
(registry dùng chung nhiều `{id}`, đọc ở Step 01 bước 6c), không chỉ 1 DB mặc định:

- Mỗi `source_id` có keyword kết nối riêng (nhân bản theo template §6, đổi tên `Connect To {SourceId} Database` — tiếng Anh), Suite
  Setup gọi đủ cho các `source_id` thực sự dùng trong slice — connect 1 lần, disconnect ở Suite Teardown.
- Credential mỗi connection đọc theo `env_prefix` khai trong registry (vd `${PMT_DB_HOST}` cho source `pmt_profile`)
  — không hardcode, không dùng chung biến `${DB_HOST}` mặc định cho mọi source.
- **Connection identity = `env_prefix`, KHÔNG phải ranh giới source/service:** 2 `source_id` khai CÙNG
  `env_prefix` = chung 1 DB vật lý → dùng chung 1 connection (connect 1 lần), JOIN/subquery chéo bảng của
  2 source trong 1 câu SQL là **hợp lệ**. KHÁC `env_prefix` → cross-check 2 bước (query từng connection rồi
  lọc giao nhau ở code Robot), CẤM JOIN xuyên DB. Đọc `env_prefix` của các source liên quan TRƯỚC khi quyết
  định tách/gộp query — đừng mặc định "khác service = khác DB" và cũng đừng gộp bừa khi chưa thấy registry
  khai cùng prefix.
- `$seed.create`/`$seed.insert` (nếu registry có `auth` — vd login + captcha text để lấy Bearer token) thực hiện
  ở Suite Setup/Test Setup tùy phạm vi dùng token (token có TTL — nếu nhiều test case cùng dùng, lấy 1 lần ở
  Suite Setup và cache lại, không login lại mỗi test).
- **Sinh `$seed.create` qua API (reuse rỗng/thiếu N):** auth captcha→token → tra tham số DB (`create_api.lookup_*`) → POST `create_api.<op>` (đúng method/content_type, multipart theo `body_part`, né trùng khóa) → `result_verify`; **lặp tới đủ N**. Dùng **`RequestsLibrary`** (HTTP) + **`DatabaseLibrary`** (lookup) — library-first (§5 auto_robot_rules), KHÔNG file `.py` riêng; bypass proxy bằng `Set Environment Variable    no_proxy    <host>`.
  - **Bắt buộc, không stub:** registry có `create_api` → generate seed đầy đủ ngay lúc GENERATE. CẤM `Fail [SEED-TODO]`/"verify sau". Thiếu env → fail-at-run, không stub-at-generate.
  - **Generic registry-driven — KHÔNG bespoke per-slice** (rule: [iron_rules R15](../../principles/iron_rules.md))**:** seed đọc `data_sources.yaml` (auth/create_api/lookup/reuse_check) để chạy; CẤM viết logic subsystem/nghiệp-vụ-cứng riêng cho từng slice. Buộc phải dùng Python thì là **1 lib DÙNG CHUNG registry-driven**, KHÔNG `<Slice>SeedLibrary.py` mỗi slice (đó là lý do "lần nào sinh cũng lỗi" — mỗi lần tái phát minh code seed mong manh).
  - **Robust BẮT BUỘC (encode 1 lần ở tầng dùng chung, không tune lại per-slice):** (1) **reuse-first + cap/owner** — reuse un-consumed trước; giữ số pending/owner dưới ngưỡng để fan-out không ẩn dòng; cạn mới tạo owner mới. (2) **retry re-fetch** — sau seed nếu chưa lên fan-out (Redis TTL/sync) thì re-fetch + poll rồi mới fail. (3) **query đếm bằng JOIN gom-nhóm 1 lần**, KHÔNG subquery COUNT tương quan mỗi dòng (→ `max_statement_time`). (4) **escaping** — literal `LIKE 'x%'` đi cùng tham số `%s` phải viết `%%`.
- **Gọi API mà `503`/`403` HTML (không phải JSON):** (1) `503` = proxy chặn → bypass (`requests` `trust_env=False` / `curl --noproxy '*'`); (2) `403` nginx = base URL thiếu version prefix → ghép đủ `basePath+endpoint+version` theo FE (`api-path.ts`), đừng đoán `${BASE}/public/...` là đủ. Tell: bước UI PASS nhưng call API fail → gần như chắc do proxy.
- **Tài nguyên precondition BỊ TIÊU THỤ → xem §11** (đừng chỉ "reuse khi rỗng"): nếu action của case *ăn* bản ghi mồi, phải seed đủ N un-consumed theo số case tiêu thụ, không phải top-up khi pool = 0.

## 11. Tài nguyên precondition BỊ TIÊU THỤ (consumable) — CẤM cache-1-lần cho cả suite

Một số scenario có action **tiêu thụ** bản ghi mồi: tạo composite "ăn" 1 pending (link vào `composite_sub_links` → pending không còn khả dụng để compose lần 2). Với loại này, resolver **KHÔNG** được lấy 1 bản ghi rồi `Set Suite Variable ... yes` dùng lại cho mọi test — case tiêu thụ đầu ăn xong, các case tiêu thụ sau tái dùng bản ghi đã bị "ăn" → API từ chối → **false-fail hàng loạt** (đây là lỗi sinh đã gặp: 1 pending resolve-once, ~20 ca create sau đó fail "success toast not shown").

**Nhận diện (self-check bắt buộc khi sinh resolver):** *"Action của case có LÀM MẤT bản ghi mồi cho case sau không?"* — xét **THEO TỪNG CASE**, không gán cả suite:
- **Có** (state-mutating create/submit ghi vào bảng link/junction, hoặc đổi trạng thái bản ghi mồi `pending → consumed`) → áp §11 (fresh-per-case).
- **Không** (case chỉ ĐỌC/hiển thị/tick bản ghi mồi — kể cả bản ghi ĐÃ bị tiêu thụ vẫn render được trên màn) → cache-1-lần OK, resolver read-only bình thường.

**⛔ Anti-pattern "một resolver cho tất cả":** CẤM ép mọi case động đi qua pool un-consumed/seed. Case nào tạo thì case đó seed — case hiển thị/tick KHÔNG được phụ thuộc seed. Ép chung → pool cạn/seed hỏng kéo đổ cả các case vốn không cần data tươi (đã gặp: 36 case display fail oan vì gate pool). Tách 2 resolver: (a) display vars resolve-1-lần ở Suite Setup (mọi bản ghi mồi, kể cả consumed, un-consumed xếp trước); (b) fresh-per-case cho đúng các case tiêu thụ.

**Quy tắc sinh khi §11 áp:**
1. **Đếm NHU CẦU, không đếm tồn kho.** Số bản ghi mồi un-consumed phải ≥ số test case tiêu thụ nó (mỗi case 1 bản ghi tươi). `$db.query` trả 1 row lúc generate **KHÔNG** chứng minh đủ cho N case.
2. **SELECT phải lọc bản ghi CHƯA tiêu thụ**, không chỉ `status=5`: `LEFT JOIN <link_table> l ON l.<fk>=t.<pk> WHERE l.<pk> IS NULL`.
3. **Provision tươi qua `$seed.create` (§10) — per-case, seed fail KHÔNG cascade:** mỗi case tiêu thụ query fresh un-consumed ngay lúc cần; rỗng → seed bù TRONG case đó (DB tự phản ánh consumption — không cần pool/con trỏ thủ công), **KHÔNG** khoá 1 giá trị bằng `Set Suite Variable`. Seed bọc `Run Keyword And Ignore Error`: fail → log WARN, chỉ FAIL đúng case đó. **Seed phải LẶP QUA NHIỀU candidate** (skip candidate hỏng, thử candidate kế) — lý do fail khó đoán trước per-candidate (vd PMT-029 chỉ vài service có template data đầy đủ); chọn `LIMIT 1` sẽ kẹt vĩnh viễn ở candidate hỏng vì nó không bao giờ được đăng ký thành công.
4. **Cache chỉ cho read-only.** Tài nguyên tiêu thụ tuyệt đối không cache xuyên suite.
5. **Teardown/headroom.** Vì không tự động xóa DB ở teardown để giữ audit, bắt buộc phải seed dư headroom + định danh unique (§7) để các lần chạy lại (re-run) không bị đụng dữ liệu cũ.
6. **Container-entity rotation khi cạn slot.** Nếu bản ghi mồi đăng ký theo cặp unique `(container, item)` (vd merchantId+serviceId) thì mỗi container có SỐ SLOT HỮU HẠN — chạy nhiều run sẽ cạn item seedable trên container hiện tại. Khi mọi candidate fail → TẠO CONTAINER MỚI qua create-op trong registry (vd `create_api.merchant`) rồi seed lại: container mới dùng lại được toàn bộ item "tốt". Resolver trả kèm container của bản ghi tươi (subId thuộc merchant nào → search theo merchant đó), KHÔNG giả định container cố định.
7. **Record vừa seed chưa chắc hiện ngay trên UI — 2 bẫy phải kiểm trước khi tin retry:** (a) **cache backend** (vd Redis TTL 30s per key filter) → retry phải kéo dài > TTL; (b) **FE dedupe search** (`distinctUntilChanged` trên pipe filter) → re-click Tìm kiếm CÙNG filter bị nuốt, KHÔNG re-fetch — retry phải **mở lại màn/modal** (pipe mới) chứ không chỉ re-click. Đọc spec (HLD keyspaces/TTL) + FE component source để chọn cơ chế retry đúng; retry mù theo thời gian sẽ fail oan.
8. **Danh sách chọn bản ghi mồi có thể là virtual scroll** (cdk-virtual-scroll...): dòng ngoài viewport KHÔNG có trong DOM → trước khi click theo id phải cuộn viewport từng bước tới khi dòng render (probe nhanh mỗi bước, không Sleep). Suite chạy nhiều lần làm list dài ra — lỗi chỉ lộ khi data tích lũy, dryrun/subset ít data không bắt được.
9. **Case tiêu thụ NHIỀU bản ghi trong 1 lần load list → seed HẾT trên CÙNG 1 owner TRƯỚC khi load.** Màn chọn thường load list 1 lần (snapshot lúc search). Nếu seed bản ghi thứ 2 SAU khi đã load → nó không có trong list, mà re-load thì rớt tick trước đó. Đúng: gom nhu cầu (N bản ghi), bảo đảm đủ N un-consumed trên **cùng một owner** TRƯỚC, load list 1 lần (thấy hết), rồi tick từng cái; nếu 1 dòng chưa render thì reopen+search+**re-tick cả list** (idempotent, WUKS). CẤM xen kẽ seed↔tick. Case cross nhiều sub-system (vd PMT+PCM) cũng vậy: dồn tất cả lên cùng owner/merchantCode để 1 fan-out thấy hết. **Cách bảo đảm N phải theo §11.9a ngay dưới (tái dùng trước, seed đúng phần thiếu) — KHÔNG tạo owner mới mỗi case.**

    **§11.9a — TIẾT KIỆM data (mọi nhánh seed, không chỉ multi):** seed tạo data thật trên môi trường chung → CẤM seed thừa. Thứ tự bắt buộc mỗi lần cần bản ghi: (1) **đếm un-consumed sẵn có trên owner hiện tại** → đủ thì DÙNG, không seed; (2) thiếu k → seed **đúng k** lên **owner hiện tại** (mỗi owner chứa được nhiều item — không cần owner mới); (3) **chỉ tạo owner mới khi owner hiện tại thật sự cạn slot** (mọi candidate item fail — §11.6), rồi tiếp tục trên owner mới. Sai thường gặp (đã xảy ra): tạo owner mới + seed đủ N **mỗi case** → rác bùng nổ (vd 37 merchant/ngày). Owner + item đã seed nhưng chưa bị tiêu thụ là **tài sản tái dùng** cho case sau, không phải dùng-một-lần. Ưu tiên teardown/định danh unique (§7) để re-run không tích rác.
10. **Seed qua API cần tham số phụ (categoryId/formId/...) → tra ĐỘNG qua API list, KHÔNG hardcode UUID.** Nếu create-op cần id tham chiếu (danh mục, form, template...) mà registry để `[TBD]`: tìm endpoint list (`GET .../category`, `GET .../forms`) lấy phần tử đầu hợp lệ lúc chạy, ghi endpoint đó vào registry `lookup_*` thay cho UUID mẫu. Hardcode UUID sẽ hỏng khi data đổi/môi trường khác.

11. **Record "độc" (DB có, UI vĩnh viễn không hiện) → BLACKLIST runtime, KHÔNG đoán cột filter.** Có record un-consumed hợp lệ về schema nhưng fan-out/UI không bao giờ render (nguyên nhân per-record khó suy từ cột — đã thử lọc theo `sanbox` và SAI: cả 55 service đều sanbox=1 kể cả loại hiển thị tốt, filter giết sạch candidate). Xử lý đúng: sau khi retry hết ngưỡng (§11.7) mà dòng vẫn không hiện → ghi subId vào blacklist (scope theo `source_id`, xem cuối mục này) + lấy record kế (self-heal ≤3/case); ORDER BY DESC + không blacklist = 1 record độc đầu độc MỌI case sau nó. **Persist blacklist theo hợp đồng single-writer:** chạy 1 process thì append thẳng canonical, không cần shard; chạy song song thì chỉ append vào **shard của chính process**, **tên shard PHẢI mang `source_id`**: `results/parts/{id}/{run_id}/blacklist-<source_id>-<shard>.jsonl` (hợp đồng tên file canonical là [step-05 §3](../../steps/step-05-execute-and-analyze-logs.md) — bỏ `<source_id>` thì bước merge lặp theo từng source **không thấy shard nào**, promote 0 record mà không báo lỗi, và run sau lại tốn 3 retry cho đúng record độc cũ). Step 05 merge union vào canonical `datatest/blacklist/{source_id}.jsonl` (**`{source_id}` = khoá registry trong `data_sources.yaml` chứa bản ghi mồi** — scope theo NGUỒN DATA, không theo slice, để mọi slice dùng cùng nguồn chia sẻ được blacklist) bằng tmp+`mv`, **dedupe theo khoá `subId`** (không phải `sort -u`); reader đọc `canonical + shard của run hiện tại`. CẤM append trực tiếp vào canonical trong lúc test chạy — nhiều process ghi chen nhau làm hỏng blacklist, run sau đọc sai (chi tiết: [step-05 §3](../../steps/step-05-execute-and-analyze-logs.md)). Lesson: khi định lọc data theo một cột "nghi là nguyên nhân", PHẢI kiểm phân bố cột đó trên data thật trước (record tốt và xấu có khác giá trị không?) — không thì filter dựa trên trùng hợp.

12. **Reuse-check BOUNDED theo N bản ghi GẦN NHẤT — không thỏa thì SEED NGAY (đỡ mất thời gian).** Khi kiểm Tier 0 (tái dùng trước khi seed — §11.9a), CHỈ query **N bản ghi mang hậu tố định danh auto** (`*_code_auto` / marker của môi trường) **mới nhất** — `... WHERE <marker> LIKE '...auto%' ORDER BY <ngày tạo/đăng ký> DESC LIMIT N` (mặc định **N=5**) — rồi đối chiếu **TRẠNG THÁI** của chúng với **điều kiện đầu vào của testcase** (vd pending `status=5` + `is_history=0` + un-consumed / chưa bị link). Lý do bound N recent: bản ghi mới nhất xác suất render/khả dụng cao hơn, né 'record độc' cũ nằm đầu bảng (§11.11), và query nhẹ. **Không bản ghi nào trong N recent thỏa điều kiện → SEED MỚI NGAY (Tier 1)** — TUYỆT ĐỐI không scan toàn bảng / retry mù để "chờ có" (lãng phí thời gian). Nếu bản trong N recent thỏa ở DB nhưng dùng trên UI vẫn fail (record độc) → blacklist (§11.11) rồi rơi xuống seed. Đây là bước kiểm bắt buộc TRƯỚC mọi nhánh seed.
