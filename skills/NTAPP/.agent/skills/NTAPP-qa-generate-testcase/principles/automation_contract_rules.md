# AUTOMATION CONTRACT RULES — Hợp đồng bàn giao cho Automation (School B)

> **Mục đích:** Định nghĩa **artifact canonical máy-đọc-được** và **tag dictionary** để output của skill này
> dùng trực tiếp cho automation (qua skill `/ntapp-qa-robot`) thay vì chỉ là tài liệu manual.
> File này là **nguồn sự thật duy nhất** cho format bàn giao automation. Mọi step/template tham chiếu về đây.
>
> **Quan hệ với [iron_rules.md](./iron_rules.md):** Contract này KHÔNG nới lỏng bất kỳ Iron Rule nào (R1 zero-fabrication, R2 zero-summarization, R3 traceability vẫn giữ nguyên). Nó chỉ thêm **lớp emit thứ 2 và thứ 3** bên cạnh markdown.

---

## 1. Triple-Emit Contract (1 nguồn → 3 artifact)

Skill emit **3 artifact từ cùng một tập kịch bản đã chốt**, KHÔNG sinh rời rạc:

| # | Artifact | Vai trò | Người/Máy tiêu thụ |
|---|---|---|---|
| 1 | `{id}_testspec.feature` | **CANONICAL** — Gherkin + tags. Nguồn-sự-thật về *what to test* + routing automation | Human BDD review · qa-robot (P3) · Playwright (tương lai) |
| 2 | `{id}_detailed_test_manual_testcase.md` | **VIEW** render bảng 11 cột — interface chính với `qa-robot` hiện tại + bản QA ký HITL | Manual tester · qa-robot (parse bảng) |
| 3 | `{id}_fixtures.yaml` | **DATA** máy-đọc: dữ liệu mồi + môi trường + mock (thay Mục 5.3 prose) | qa-robot `test_data_generator` |

**Bất biến đồng bộ (Sync Invariant) — mô hình "1 SỐ GỐC + 2 PHÉP CHIẾU" (CANONICAL — mọi file khác cite về đây):** Mỗi `Scenario`/`Example` trong `.feature` ⇔ đúng 1 dòng bảng markdown **có `@exec:automate` hoặc `@exec:exploratory`** ⇔ cùng `@id:KB-{id}-NN` (`{id}` = ID đầy đủ SLICE/unit, vd `KB-SLICE-06-02` / `KB-WGT-SIDEBAR-02`).

**Số tổng CHỐT ngay ở bước plan; các con số artifact chỉ là PHÂN HOẠCH của số đó theo cột Exec — KHÔNG đếm lại, KHÔNG phải đẳng thức độc lập (CẤM viết "3-way ==").**

- **Số gốc `X`** = tổng case **chốt cụ thể ở Step 02 Math Forcing** (đây là con số cuối cùng, không phải ước lượng; chỉ đổi khi `risk-gated` Step 02b cắt P2, kèm công thức trừ tường minh). `X` gồm **cả** automate + manual + exploratory. "Bước ra số trước, bước sau tuân theo" → từ Step 02b trở đi `X` bất biến; Step 03 BẮT BUỘC ghi đủ `X` dòng, KHÔNG đẻ số mới.
- **Step 02b KHÔNG đổi tổng `X`** — chỉ **dán nhãn** `Exec` cho từng dòng: mỗi dòng trong `X` mang đúng 1 nhãn → `A`(automate) `+ E`(exploratory) `+ M`(manual) `= X`. `A/E/M` là cách chia đúng `X` dòng đã cố định, KHÔNG phải số mới đếm ra.
- **Gate gốc (Math Check):** `Y == X`, với `Y` = **tổng** dòng markdown thực ghi (KỂ CẢ manual).
- **Phép chiếu 1 (feature):** `count(@id distinct trong .feature) == A + E` — chỉ *đếm bao nhiêu dòng route sang* `.feature`.
- **Phép chiếu 2 (fixtures):** `count(dataset trong fixtures.yaml) == A` (exploratory chỉ ghi `note:`, không dataset; manual ở lại markdown, không sang `.feature`/fixtures).

Hai phép chiếu chỉ *đếm dòng route sang từng file*, KHÔNG định nghĩa lại và KHÔNG bao giờ vượt `X`. Lệch bất kỳ đâu → vi phạm R2, phải sửa (KHÔNG hạ manual, KHÔNG drop @id để "cho khớp").

> **[HARD CHECK — cross-artifact, BẮT BUỘC]** Kiểm phép chiếu 1 bằng cách so CHÉO `.md`↔`.feature`, **KHÔNG** đếm nội bộ `.feature` (`count(Scenario)==count(@id)` là tautology — không thấy khi @id bị drop).
> **Sàn chống FALSE-PASS (BẮT BUỘC trước khi tin `comm`):** đếm `N_md = số dòng grep được ở phía `.md`` và đối chiếu `N_md == A + E` (số automate+exploratory kỳ vọng từ Step 02b). **`N_md == 0` hoặc `N_md != A+E` → FAIL ngay** (thường do format bảng lệch làm grep trượt) — `comm` rỗng lúc này là rỗng-giả, KHÔNG được coi là PASS. Chỉ khi `N_md == A+E` mới chạy `comm`, và `comm` phải RỖNG:
> **So trong bộ nhớ, KHÔNG sinh file trung gian.** ⛔ CẤM `<(…)` (process substitution) — trên git-bash Windows nó materialize thành file thật trong `/tmp`, tức ghi rác ra ngoài dự án.
> ```powershell
> $md = Select-String -Path '{id}_detailed_test_manual_testcase.md' -Pattern '^\| \*\*(KB-[A-Z0-9-]+)\*\*.*\| (automate|exploratory) \|' |
>        ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
> $ft = Select-String -Path '{id}_testspec.feature' -Pattern 'KB-[A-Z0-9-]+' -AllMatches |
>        ForEach-Object { $_.Matches.Value } | Sort-Object -Unique
> "N_md=$($md.Count)  N_feature=$($ft.Count)"      # N_md phải == A+E trước khi tin kết quả so
> Compare-Object $md $ft                            # rỗng = khớp; '<=' là @id .feature bỏ sót
> ```
> Ra @id nào = dòng `Exec∈{automate,exploratory}` của `.md` bị `.feature` bỏ sót → **DỪNG**, bổ sung 1 Example/Scenario cho mỗi @id (Rebalance §6.1 đổi cấu trúc, KHÔNG giảm @id).

**Nhất quán data E2E (fixtures):** Trong 1 slice, mỗi luồng dùng **một bộ định danh thống nhất** xuyên suốt — giá trị để chọn/tick (lấy từ unit pending/nguồn) PHẢI trùng với giá trị trong payload tạo và giá trị assert ở DB. CẤM ghép sample rời từ phần Dữ liệu (`_detailed_design`) của từng unit khiến lệch `merchantCode`/`subId`/khóa định danh giữa "data hiển thị để thao tác" và "data được tạo/verify". Fixture `scope: e2e` (chạy qua UI) phải đủ field để **drive UI**: filter value (vd `merchantCode`), định danh phần tử để tương tác (vd dòng pending để tick) — không chỉ payload API. Thiếu giá trị thật → `[TBD]` (R1), KHÔNG lấy bừa sample của unit khác.

**Dynamic Binding (field Runtime-dependent):** Field Loại 1 (FK/lookup) và Loại 2 (unique) theo [dynamic_data_rules.md](./dynamic_data_rules.md) KHÔNG hardcode — khai báo trong `overrides` bằng `$db.query(<source_id>: SELECT ...)` (chỉ SELECT) · `$seed.create(<source_id>: <operation>)` · `$uuid` · `$timestamp(format)`. `<source_id>` phải có trong `{qa_artifacts}/data_sources.yaml`. Không xác định được nguồn → `[UNRESOLVED-BACKEND]` + `note:`, không bịa.

**Ví dụ nhận diện nhanh (để KHÔNG bỏ sót khi viết fixtures.yaml):** subId/subSystem của 1 dòng lấy từ danh sách trả về bởi unit khác (vd fan-out pending) là Loại 1, PHẢI dùng $db.query/$seed.create, KHÔNG được viết cứng kiểu "PMT-2026-00451". merchantCode/mã dùng làm điều kiện filter để tìm bản ghi có sẵn cũng là Loại 1. ULID/PK do backend tự sinh (vd compositeId trả về sau POST) thì KHÔNG cần fixture, chỉ capture runtime. Field tự do do Tester gõ (tên hồ sơ, mô tả, ghi chú) là Loại 3, viết tĩnh bình thường, KHÔNG áp dụng mục này.

**Inline-value vs `fixture_ref` (BẮT BUỘC — chống indirection khó đọc):** Đọc 1 dòng dataset phải thấy NGAY dữ liệu của nó, không phải nhảy lên mục `fixtures:` tra. Quyết định theo bảng:

| Data của dataset là… | Cách ghi | Ví dụ |
|---|---|---|
| **Loại 3 tĩnh, dùng 1 lần** (validation/BVA/security-input/space-handling — giá trị chính là thứ đang test) | **Ghi thẳng inline** trong `data: {…}` ngay trên dòng dataset. CẤM tách thành fixture tên riêng rồi `fixture_ref`. | `- { id: KB-…-054, data: { name: "<tiếng Việt 100 ký tự>" } }` |
| **Dùng lại ≥2 dataset** (cùng 1 session, cùng 1 pending fan-out, cùng 1 payload submit) | `fixture_ref: <key>` (+ `overrides:` nếu case này khác chút) | `- { id: KB-…-203, fixture_ref: valid_compose_minimal }` |
| **Payload/seed nhiều field phức tạp** (dài, lồng mảng — inline sẽ vỡ 1 dòng) | `fixture_ref: <key>` | `fixture_ref: pending_all_sources` |
| **Loại 1/2 động** (FK/filter/unique — theo Dynamic Binding ở trên) | `fixture_ref: <key>` chứa `$db.query/$seed.*`, hoặc inline `data:` mang trực tiếp marker `$…` | `data: { subId: "$db.query(pmt_pending: …)" }` |

Nguyên tắc 1 câu: **fixture tên riêng chỉ tồn tại khi được ≥2 dataset dùng chung, hoặc data quá phức tạp/động để inline.** Fixture chỉ-dùng-1-lần cho giá trị tĩnh = indirection thừa → nội hoá (inline) vào chính dòng dataset. Điều này KHÔNG nới lỏng R1 (giá trị vẫn phải truy về phần Dữ liệu của `_detailed_design`/audit) — chỉ đổi *nơi ghi* giá trị, không đổi *nguồn* giá trị.

> **`data:` phải máy-đọc-được để qa-robot bind trực tiếp:** keyed theo TÊN FIELD + giá trị thật (`data: { merchantCode: "doi@tac#1" }`). CẤM prose gộp 1 khóa `input:` và CẤM placeholder mô tả (`"<100 ký tự>"`); chuỗi biên dài dùng `"a"×255` hoặc giá trị thật. Prose/placeholder → robot không bind được, buộc hardcode (vỡ R8).

---

## 2. Tag Dictionary (taxonomy bắt buộc trên mỗi Scenario)

Mỗi `Scenario` mang đủ các tag dưới đây (trừ tag đánh dấu *(optional)*):

| Tag | Giá trị hợp lệ | Ý nghĩa | Nguồn |
|---|---|---|---|
| `@<id>` | `@SLICE-06` / `@WGT-SIDEBAR` / `@HUB-01` | SLICE/unit sở hữu | file SLICE / WBS |
| `@scr:<unit_id>` *(bề mặt `ui`)* | `@scr:SCR-COMPOSE` | Màn hình Action chứa case | unit `[Action]` |
| `@svc:<unit_id>` *(bề mặt `service`)* | `@svc:HUB-01` | Operation/endpoint chứa case (dùng THAY `@scr` khi no-UI) | unit `[Operation]` |
| `@id:<KB-id>` | `@id:KB-SLICE-06-02` | Khóa 1-1 với dòng markdown | running ID |
| `@block` | `ui` \| `functional` \| `security` \| `contract` | Khối testcase. *(ui)* 3 khối `ui`/`functional`/`security` · *(service)* 3 khối `contract` (Hợp đồng & Request Validation) / `functional` (Nghiệp vụ & E2E) / `security` — KHÔNG dùng `ui` cho service | cấu trúc 3 khối |
| `@tech` | `EP` \| `BVA` \| `DT` \| `ST` \| `EG` | Kỹ thuật thiết kế test | rule file `@tech` |
| `@rule:<slug>` | `@rule:textbox-base` | Truy vết về file kbkt-generation | bảng Mapping Rule (Step 02) |
| `@risk` | `P0` \| `P1` \| `P2` | Risk tier (= cột "Độ ưu tiên") | [risk_based_allocation_rules.md](./risk_based_allocation_rules.md) |
| `@exec` | `automate` \| `manual` \| `exploratory` | **Cổng automation** | risk allocation (Step 02b) |
| `@target` *(chỉ khi `@exec:automate`)* | `robot` \| `playwright` | Đích sinh code | mặc định `robot` |
| `@oracle` | `ui` `api` `db` `log` `msg` (đa giá trị) | Tầng kiểm chứng assert được (`msg` = event/message phát ra — bề mặt service) | Expected result đa lớp |
| `@manual-verify` *(optional)* | — | Đánh dấu tầng oracle phải verify bằng người (automation KHÔNG được giả vờ phủ) | — |
| `@regression` *(optional)* | — | Thuộc bộ regression guard (P5) | — |

**Quy tắc `@exec` (cổng quyết định automation):**
- `automate` → có ≥1 `@oracle` tự động assert được (ui/api/db) **và** không phụ thuộc phán đoán người. Bắt buộc có `@target`.
- `manual` → oracle chủ yếu visual/UX/khó-tự-động (vd zoom, responsive, focus order) → ở lại markdown view, KHÔNG sang automation.
- `exploratory` → **mặc định KHÔNG dùng** và **KHÔNG tạo charter/section riêng**. Mọi rủi ro bất định (timing/đồng thời/phiên/spec `[TBD]`/UX mới) phải phân tích ra oracle rồi viết thành **case scripted (`automate`/`manual`) trong KHỐI 2/3** (dòng `[BR]` nếu expected neo theo contract canonical mà code chưa đạt) — theo [risk_based_allocation_rules §3](./risk_based_allocation_rules.md) + [explore_and_consistency_rules §5](./explore_and_consistency_rules.md). CHỈ giữ `exploratory` cho quan sát thẩm mỹ thuần không assert được (so màu/spacing), nằm trong KHỐI 1 UI.

**Quy tắc `@oracle` (theo bề mặt):**
- *Bề mặt `ui` — UI-first:* test được/quan sát được qua UI thì BẮT BUỘC có `@oracle:ui` + drive qua `@scr` (cột Công cụ `Chrome`). API-only (bỏ `@scr`, Công cụ `Postman`) CHỈ khi hành vi không có mặt trên UI.
- *Bề mặt `service` — API-first:* dùng `@svc` (không `@scr`), Công cụ `Postman`/`RequestsLibrary`. BẮT BUỘC `@oracle:api` (hoặc `@oracle:db`/`@oracle:msg` khi job/consumer không trả HTTP); **CẤM `@oracle:ui`**. `@oracle:msg` = event/message phát ra outbox/topic. Chi tiết: [service_surface_rules.md §3](./service_surface_rules.md).

Chi tiết chấm risk/exec: [risk_based_allocation_rules.md §3](./risk_based_allocation_rules.md).

**Quy tắc `@target`:** mặc định `robot` (consumer sẵn có). Chỉ đặt `playwright` khi project khai báo `automation_target: playwright` ở `.bmm-config.yaml`.

---

## 3. Cấu trúc Scenario chuẩn (Gherkin)

- **1 `Scenario` tường minh = 1 dòng testcase (per-case — CẤM gom).** Mỗi case là 1 block `Scenario` riêng, đọc đứng một mình là hiểu đủ input→expected. **CẤM `Scenario Outline` + `Examples`** — kể cả BVA/EP nhiều giá trị cùng-một-logic: viết N `Scenario` riêng, mỗi cái 1 `@id`. Chống trùng-lặp KHÔNG bằng cách gom scenario mà bằng cách **để giá trị input ở `fixtures.yaml`** (mỗi case 1 dataset) — `.feature` chỉ tham chiếu qua nhãn/`<fixture_ref>`, phần thân N scenario khác nhau ở giá trị được nạp, không copy-paste literal. Lý do: giữ map 1-1 (R2) tường minh, fail chỉ đúng case, dễ skip/annotate lẻ.
- `Given/When/Then` mô tả hành động vật lý tuần tự — **không** chứa selector/endpoint-URL cứng. *(ui)* chỉ dùng **Nhãn hiển thị UI** (selector do qa-robot lấy từ `ui_schema_{id}.json`) · *(service)* mô tả gọi request theo tên operation + nhận response + quan sát side-effect (endpoint path lấy từ Contract Map/DD, không hardcode payload dài — dùng `<fixture_ref>`).
- Mỗi tầng oracle = 1 dòng `Then`/`And`, prefix theo thứ tự ưu tiên: *(ui)* `UI:` → `API:` → `DB:` → `Log:` · *(service)* `API:` → `DB:` → `MSG:` → `Log:` — khớp đúng thứ tự Expected result của markdown.
- Tầng oracle không tự động được → gắn comment `# @manual-verify` ở cuối dòng `Then` đó.
- Data lấy từ fixtures: tham chiếu `<fixture_ref>` (vd `<valid_compose_payload>`), KHÔNG hardcode payload dài trong feature.

Khung mẫu đầy đủ: [`references/templates/testspec_feature_template.feature`](../references/templates/testspec_feature_template.feature).

---

## 4. Ranh giới với qa-robot (không lấn việc)

- Skill này **KHÔNG sinh selector/keyword, KHÔNG sinh Robot code**. Chỉ sinh *what to test* (feature) + *data* (fixtures) + *view* (markdown).
- `qa-robot` chịu trách nhiệm: *(ui)* selector từ `ui_schema`, POM Selenium, execute, self-heal · *(service)* keyword `RequestsLibrary` **vẫn theo POM** (mỗi endpoint/operation = 1 "service object" đóng vai page-object), execute, self-heal.
- Vì vậy: *(ui)* thiếu `ui_schema_{id}.json` **không** chặn skill này (việc của qa-robot) — nhưng PHẢI cảnh báo ở Mục 5.3/round-trip rằng automation sẽ chặn nếu thiếu · *(service)* **KHÔNG cần `ui_schema`**; thay bằng `automation_prereq`: `base_url` + `auth` + `api_contract` + `mocks` (xem [service_surface_rules.md §5](./service_surface_rules.md)).

---

## 5. Backward-compatibility

- Markdown view giữ nguyên bảng 3-khối + Mục 5.x để QA hiện tại ký HITL không gãy. Thêm **đúng 1 cột `Exec`** (xem table template).
- `.feature` và `fixtures.yaml` là **mới, không thay thế** markdown. Nếu config `emit_automation: false` (Layer 3) → skill chỉ emit markdown như cũ (chế độ legacy).
