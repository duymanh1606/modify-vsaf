# DYNAMIC DATA RULES — Chuẩn hóa dữ liệu động chống hardcode (School B)

> **Mục đích:** Định nghĩa cách phân loại field cần dữ liệu động (chống hardcode unique/FK), thuật toán xác định
> nguồn dữ liệu thật, và chiến lược resolve tại runtime. Dùng ở Step 02 (khi phát hiện field Runtime-dependent)
> và Step 03 (khi khai báo `overrides` trong `fixtures.yaml`). Đầu ra được `/ntapp-qa-robot` tiêu thụ
> (xem `iron_rules.md` R7b/R8 + `auto_db_oracle_rules.md` §10 của skill đó).
>
> **Quan hệ với [automation_contract_rules.md](./automation_contract_rules.md):** File này là nguồn sự thật cho
> *cách xác định + cú pháp* dữ liệu động; `automation_contract_rules.md` chỉ dẫn chiếu tới đây.

---

## 1. Tiêu chí phân loại field

Phân loại **theo từng màn/từng unit**, KHÔNG theo tên field — cùng 1 tên field ở 2 màn khác nhau có thể phục vụ
bởi 2 backend khác nhau (1 bên đọc DB nội bộ, 1 bên gọi service khác) → phân loại lại từ đầu mỗi màn.

| Tiêu chí | Loại ràng buộc | Cách nhận biết trong phần Dữ liệu | Cách xử lý |
| :--- | :--- | :--- | :--- |
| **1. Khóa ngoại / Bộ lọc** | Bắt buộc trỏ tới 1 bản ghi thật đang tồn tại (FK, hoặc filter cần data không rỗng để test) | Cột DB có `FK`/`ref`/`Lookup`, hoặc field filter/search gọi sang service khác | Xem Mục 3 (4-tier) |
| **2. Khóa chính / Độc bản** | Ràng buộc duy nhất (`UNIQUE`/`PRIMARY KEY`) | Cột DB có `UNIQUE`/`PRIMARY KEY` | `$uuid` hoặc `$timestamp(format)` |
| **3. Dữ liệu tự do** | Không ràng buộc | Cột thường, cho phép null/duplicate | Ghi tĩnh bình thường |

Một field có thể vừa Loại 1 vừa Loại 2 cùng lúc (vd định danh vừa phải trỏ bản ghi thật đang ở đúng trạng thái,
vừa phải chưa từng được dùng do `UNIQUE` composite-level) — cần **cả 2 cơ chế cộng lại**, không chọn 1.

**Cách GHI vào `fixtures.yaml` theo loại** (chi tiết: [automation_contract_rules.md §1 "Inline-value vs fixture_ref"](./automation_contract_rules.md#1-triple-emit-contract-1-nguồn--3-artifact)):
- **Loại 3 (tự do, tĩnh) dùng-1-lần** → ghi **thẳng giá trị inline** trong `data: {…}` của dòng dataset. CẤM tách fixture tên riêng rồi `fixture_ref` (indirection thừa, khó đọc).
- **Loại 1/2 (động)** hoặc **data dùng chung ≥2 dataset / payload phức tạp** → mới dùng `fixture_ref` (hoặc inline `data:` mang trực tiếp marker `$db.query/$seed.*/$uuid/$timestamp`).

---

## 2. Thuật toán xác định nguồn dữ liệu (bắt buộc trước khi viết `$db.query`/`$seed.*`)

Sai ở bước này thì cú pháp đúng cũng vô nghĩa (query nhầm connection, nhầm bảng). Dừng ngay khi không đủ
thông tin — **không đoán, không bịa** (R1):

1. **Xác định unit backend sở hữu field** — đọc field `units` trong file SLICE để lấy danh sách unit ứng viên.
2. **Đọc phần Dữ liệu (Field Mapping) trong `_detailed_design` của TỪNG unit ứng viên** — nói rõ field đến từ cột DB, gọi upstream service khác,
   hay **không hề có trong response/request contract** của unit đó. Field không xuất hiện ở bất kỳ mapping nào
   trong toàn bộ `_detailed_design` của unit → không được backend hỗ trợ, không phải do thiếu wiring.
3. **Nếu là cột DB → đối chiếu DDL/schema thật nếu project có** (thường dạng `*.sql` trong tài liệu tổng quan hệ
   thống) — KHÔNG tin tuyệt đối prose phần Dữ liệu của `_detailed_design` (phần này có thể viết tắt 1 phép JOIN thành như thể là 1 cột đơn).
4. **Xác định bảng/API đó thuộc service nào → suy ra connection cần dùng** — tra tài liệu tổng quan hệ thống.
   1 slice có thể chạm nhiều service, mỗi service có thể là 1 connection tách biệt hoàn toàn (khác host/schema).
   Không có tài liệu xác nhận → dừng, hỏi người phụ trách.
5. **Nếu cần tạo mới (seed) thay vì tìm có sẵn → tra tài liệu API của đúng service đó.** Chỉ liệt kê tên
   quyền/permission code (không có method+path+request schema) → **chưa đủ điều kiện Tier 1**, fallback Tier 2.
   Nếu API cần xác thực (login) → xác định luôn cơ chế lấy token (kể cả có captcha — captcha dạng text hiển thị
   vẫn tự động hóa được bằng 1-2 API con gen/verify, không phải rào cản mặc định).
6. **Không tìm thấy đủ ở cả DB lẫn API → đánh dấu `[UNRESOLVED-BACKEND]`, escalate, dừng** — không chế cột/endpoint
   không có thật.

### 2b. ĐỊNH TUYẾN `source_id` THEO SUB-SYSTEM SỞ HỮU FIELD (chống gán sai nguồn — BẮT BUỘC, portable)

> **Lỗi kinh điển:** sinh fixtures đi tắt — "field nào trông giống dữ liệu động thì gán hết về CÙNG 1 source".
> Sai vì mỗi field có thể do một sub-system/service khác sở hữu. `source_id` phải suy ra từ **sub-system sở hữu
> field** (đã xác định ở §2 bước 1–4), KHÔNG từ cảm tính "trông giống".

Bất biến (đúng cho MỌI project, không phụ thuộc tên sub-system/source_id cụ thể):

1. **CẤM mặc định mọi field động về CÙNG 1 `source_id`.** Chạy §2 cho **TỪNG field một**, kể cả nhiều field trên
   cùng 1 dòng testcase → mỗi field resolve riêng.
2. **`source_id` chọn cho field PHẢI có `owner_service` (trong `data_sources.yaml`) khớp sub-system sở hữu field.**
   Field thuộc sub-system X mà lại trỏ `source_id` của sub-system Y = sai định tuyến → FAIL.
3. **Ca cross-source** (1 dòng chạm ≥2 sub-system): `note`/`overrides` ghi **từng field → từng `source_id`** riêng
   rẽ, CẤM gộp chung 1 nguồn.
4. **Sub-system có mặt trong dữ liệu test nhưng KHÔNG có `source_id` nào trong `data_sources.yaml`** → đánh
   **`[UNRESOLVED-BACKEND]`** (theo §2 bước 6), KHÔNG mượn source của sub-system khác, KHÔNG hardcode.
5. **Sub-system chỉ xuất hiện dạng mock/degraded** (CB open, fan-out suy giảm, stub 200) → KHÔNG cần source thật;
   ghi rõ "mock/degraded" trong `note` để phân biệt với ca cần data thật.

**Cách kiểm (portable):** dựng bảng `sub_system → source_id` từ chính `data_sources.yaml` của project (đọc
`owner_service`/`tables`), rồi đối chiếu từng dataset. Đây là self-audit ngữ nghĩa; grep chỉ là *trợ giúp cơ học*
và **phải thay token theo registry của project** (xem ví dụ ở [step-03 §10c](../steps/step-03-write-testcase.md)).

> **Ví dụ minh hoạ (project BMS — CHỈ để tham khảo, KHÔNG phải luật cứng):** `merchantCode/subId PMT → pmt_profile` ·
> `productCode/PCM → pcm_catalog` · `Policy` (registry chưa khai) → `[UNRESOLVED-BACKEND]` · `composite_* → bms_hub`.
> Project khác thay bằng sub-system/source_id của mình.

---

## 3. Chiến lược ưu tiên xử lý Loại 1 (FK/Lookup) — 4 tier

**Dấu hiệu nhận biết data do automation tạo (bắt buộc):** mọi giá trị Tier 1 sinh ra (`code`, `name`...) PHẢI
mang 1 marker cố định, duy nhất cho automation (vd tiền tố `rei` + hậu tố `_auto`: `rei{MMdd}{index}_code_auto`
đã dùng thật). Không có marker này, Tier 0 không có cách nào phân biệt data do automation tạo với data thật
của người dùng khác trong cùng môi trường.

| Tier | Cơ chế | Khi dùng | Rủi ro |
| :--- | :--- | :--- | :--- |
| **0 — Tái dùng data cũ** | `reuse_check.<target_state>` — lọc theo marker, tìm bản ghi đúng trạng thái cần | Luôn thử trước Tier 1 | Thấp nhất — không tạo thêm data mới |
| **1 — Seed qua API thật** | `$seed.create(<source_id>: <operation>)` — PHẢI gắn marker | Tier 0 không có; registry (Mục 4) đã xác nhận có API tạo hợp lệ (qua Bước 5) | Thấp — data tự cấp phát riêng/test, đi qua validate nghiệp vụ thật |
| **2 — Query bản ghi có sẵn** | `$db.query(<source_id>: SELECT ...)` — không cần marker | Chưa xác nhận API tạo, nhưng có quyền đọc DB | Trung bình — phụ thuộc môi trường đang có sẵn bản ghi; có thể bị race hoặc trả rỗng |
| **3 — Insert thẳng DB (bypass API)** | `$seed.insert(<source_id>: INSERT ...)` — PHẢI gắn marker | Cả Tier 1 lẫn Tier 2 đều không khả thi, có quyền ghi DB xác nhận | Cao nhất — bỏ qua validate/side-effect thật; cần người phụ trách unit chấp thuận rõ ràng |
| **— Unresolved** | Không cơ chế nào | Field không tồn tại ở backend nào (Bước 6) | Escalate thành gap, giữ `[TBD]`/`[UNRESOLVED-BACKEND]`, KHÔNG chặn field khác cùng slice |

**`target_state` của Tier 0** — không phải lúc nào cũng cần data "còn dùng được":
- `available`: bản ghi chưa bị tiêu thụ (vd `status=5`) → dùng cho happy path.
- `already_consumed`: bản ghi đã bị tiêu thụ rồi → dùng cho test lỗi "đã bị gom bởi người khác".

`already_consumed` thường phải tra 2 connection khác nhau (nơi tạo + nơi tiêu thụ) rồi lọc giao nhau ở code
Robot, không gộp thành 1 câu SQL JOIN xuyên DB được.

**Data tạo qua Tier 1 không mặc định phải xóa sau khi test** — nếu nó là 1 nghiệp vụ hợp lệ thật (vd "yêu cầu
chờ phê duyệt"), có thể giữ nguyên trong môi trường cho testcase khác dùng tiếp. Chỉ khai `teardown` khi
người phụ trách xác nhận cần dọn (vd merchant test hết hạn dùng, tồn đọng quá nhiều).

---

## 4. Format Registry — `{qa_artifacts}/data_sources.yaml`

Khai báo tay bởi QA Lead/dev khi phát sinh field cần Tier 0/1/2/3 — **AI không tự đoán connection/API**.

```yaml
sources:
  <source_id>:
    owner_service: <tên service/unit sở hữu>
    db:
      env_prefix: <PREFIX>            # dùng ${<PREFIX>_HOST}, ${<PREFIX>_USER}, ...
      tables: [<bảng 1>, <bảng 2>]
    auth:                              # nếu API cần xác thực trước khi seed
      login: { method: POST, url: "...", body: {...}, token_field: "..." }
    create_api:
      <operation_name>:
        method: POST
        url: "..."
        body: {...}                    # mọi giá trị định danh PHẢI mang marker automation (Mục 3)
        response: { success_code: "...", fields: [...] }
        # ---- Tier 0: tái dùng pending record đã tạo trước đó thay vì luôn tạo mới ----
        reuse_check:
          available:                   # dùng cho happy path
            via: db
            sql: "SELECT ... FROM ... WHERE ... LIMIT 1"
          already_consumed:            # dùng cho negative path
            via: db_cross_check
            step_1: "SELECT ... WHERE <marker>"           # nguồn: <source_id> này
            step_2: "SELECT ... WHERE ... IN ({step_1_result})"   # nguồn: source_id khác — lọc giao nhau ở code Robot
    teardown:
      required: false                  # mặc định false — xem lưu ý Mục 3
      method: null
```

`fixtures.yaml` tham chiếu registry qua `<source_id>`, KHÔNG tự embed host/port/credential:
```yaml
overrides:
  <field>: "$db.query(<source_id>: SELECT ... FROM <bảng> WHERE <điều kiện> LIMIT 1)"
```

**Gate bắt buộc:** `<source_id>` không tồn tại trong `data_sources.yaml` → DỪNG, báo thiếu registry.
**Bảo mật:** giá trị connection/token chỉ ghi tên biến env (`${PMT_DB_HOST}`...) — KHÔNG dán credential/token
thật trực tiếp vào registry (file này có thể bị commit vào spec repo).
