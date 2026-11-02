# SERVICE SURFACE RULES — Lập kế hoạch kiểm thử cho bề mặt KHÔNG-GIAO-DIỆN (API / service / job / consumer)

> **Mục đích:** File này là **biến thể tầng-service** của [slice_planning_rules.md](./slice_planning_rules.md) (vốn dành cho bề mặt UI). Dùng khi một unit/bề mặt test **không có giao diện** — nghiệp vụ chỉ phơi ra qua API/hợp đồng, không qua màn hình. Áp cho `surface_type=service` (detect ở [step-00](../steps/step-00-shiftleft-gate.md) / [step-01](../steps/step-01-init-slice.md)).
>
> **Không thay Iron Rules.** R1 (zero-fabrication), R2 (zero-summarization), R3 (traceability), Math Check, Sync Invariant vẫn nguyên. File này chỉ đổi **đối tượng test** (endpoint/operation thay cho màn hình) và **tầng oracle** (api/db/log/msg thay cho ui).

---

## 0. Khi nào dùng file này (`surface_type=service`)

> **⚠️ GATE QUAN TRỌNG — quyết định ở CẤP TEST-TARGET, không per-unit:** File này CHỈ áp khi **TOÀN BỘ test-target KHÔNG có màn hình nào** (`input_type=unit` trên 1 unit BE, hoặc slice thuần BE không chứa `SCR-*`/`WGT-*`).
>
> **Nếu target có ≥1 màn (slice UI): TUYỆT ĐỐI KHÔNG dùng file này cho các unit BE.** Trong slice UI, HUB/MPF/INT/PMT-EXT… là **backend của màn** — test E2E **tích hợp đi qua màn** (theo [slice_planning_rules.md](./slice_planning_rules.md)), BE được verify bằng **oracle API/DB nhúng trong testcase của màn** ([unit_classification_rules.md §3](./unit_classification_rules.md): BE map theo story-code; BE không map → Background). BE **KHÔNG** phải "service surface" độc lập, **KHÔNG** đứng riêng trong thứ tự E2E. Đây là luật "có UI thì tích hợp như cũ; không UI mới test API riêng".

Đọc `_detailed_design` của unit. Xác định `surface_type=service` khi **KHÔNG có phần Giao diện** mô tả màn hình/control render được, và unit phơi nghiệp vụ qua một trong các dạng:

| Dạng bề mặt service | Nhận diện trong DD | Ví dụ prefix WBS |
|---|---|---|
| **REST/HTTP endpoint** | mô tả method + path + request/response schema | HUB-*, MPF-*, INT-* |
| **gRPC / SOAP operation** | operation + message contract | INT-* |
| **Message consumer** | tiêu thụ topic/queue, xử lý event | HUB-*, INT-* |
| **Message producer / outbox** | phát event/message ra hệ thống khác | HUB-*, INT-* |
| **Batch / scheduled job** | chạy theo lịch/trigger, xử lý theo lô | MPF-*, HUB-* |
| **Internal service method có hợp đồng** | method phơi qua contract nội bộ (không UI) | HUB-* |

> Prefix WBS chỉ là **tín hiệu phụ**. Quyết định cuối dựa trên: DD có phần Giao diện render được không. `SCR-*`/`WGT-*` gần như luôn là `ui`; `HUB-*`/`MPF-*`/`INT-*` gần như luôn là `service` — nhưng nếu một `HUB-*` lại mô tả màn hình admin thì vẫn là `ui`, và ngược lại. **Đọc DD, không suy từ prefix.**

Một bề mặt hỗn hợp (unit vừa có màn admin vừa phơi API độc lập) → tách 2 bề mặt: chạy nhánh `ui` cho phần màn, nhánh `service` cho phần API. KHÔNG gộp.

---

## 1. Phân loại vai trò unit (service) — analog Action/Verify/Nav

Thay bộ nhãn UI (`[Action]`/`[Verify]`/`[Nav]`) bằng bộ nhãn service:

- **`[Operation]`** (operation/endpoint chính đang test): chạy đầy đủ vòng lặp Step 02 → Step 03. Là đối tượng test chính.
- **`[Effect]`** (đích side-effect để xác minh): bảng DB, bút toán ledger, outbox/event phát ra, audit log, trạng thái được chuyển. **KHÔNG chạy Step 02-03 riêng**; nhúng thành **oracle** (`@oracle:db`/`@oracle:log`/`@oracle:msg`) trong testcase của `[Operation]` gây ra nó.
- **`[Downstream]`** (đối tác/service khác mà operation này GỌI đi): core-banking, payment gateway, service nội bộ khác. **KHÔNG chạy Step 02-03 riêng**; đưa vào Precondition + khai báo **mock/stub** trong `fixtures.yaml#environment.mocks`. Vẫn phải `list_dir` liệt kê tài liệu (`_detailed_design`/integration spec) của nó; thiếu → thông báo rõ.

> Với `input_type=unit` no-UI: unit `{id}` mặc định `[Operation]`. Các bảng/event/log nó tác động là `[Effect]`; các service nó gọi là `[Downstream]`.

---

## 2. Quy trình lập plan service (9 Chốt chặn — analog slice_planning §1)

Giữ nguyên đánh số 9 chốt để đồng bộ với [step-02](../steps/step-02-plan-screen.md); chỉ đổi nội dung theo tầng service.

1. **Nạp trí nhớ E2E:** Xác định operation/endpoint hiện tại từ `implementation_plan.md` + **Context Ledger**. (Với unit đơn: chính `{id}`.)

2. **Nạp tài liệu thiết kế (SCOPED RELOAD):** `view_file` phần **Logic + Dữ liệu + Hợp đồng API** của `_detailed_design` operation hiện tại và các `[Downstream]` trực tiếp. **KHÔNG có phần Giao diện để đọc.** Fact dùng chung lấy từ Context Ledger.

3. **Lập Bảng Hợp đồng (Contract Map) — thay "Ánh xạ Nhãn UI":** Trích từ DD, không bịa (R1). Với mỗi operation:
   - **Request contract:** danh sách field (tên, kiểu, `required?`, ràng buộc: range/length/format/enum), header bắt buộc (auth, `Idempotency-Key`…), path/query param.
   - **Response contract:** schema thành công + mã HTTP; schema lỗi.
   - **Error catalog:** liệt kê **mọi mã lỗi nghiệp vụ** DD khai (mã lỗi + HTTP status + điều kiện kích hoạt). Thiếu định nghĩa → `[TBD]` + Q&A.
   - **Side-effects (`[Effect]`):** bảng/cột DB ghi, trạng thái chuyển, event/message phát, audit log ghi.
   - **State machine (nếu có):** tập trạng thái + transition hợp lệ (vd `INIT → PENDING → SUCCESS/FAILED → REVERSED`).
   - Ghi Contract Map vào `implementation_plan.md` (thay cho "Nhật Ký Đọc File" + ánh xạ nhãn).

4. **Lập Bảng Mapping Rule (tầng service):**
   - **Core (luôn có):** `00-core/*` — đánh dấu "đã nạp qua Context Ledger".
   - **Backend (luôn có với service):** `10-be/backend-resilience-rule.md` + `10-be/data-visibility-rule.md` — service surface **luôn** áp (không như UI chỉ áp khi có gọi API).
   - **Request-field validation (tái dùng rule input ở TẦNG REQUEST-BODY, KHÔNG phải control UI):** với mỗi field request có ràng buộc, map sang rule tương ứng nhưng diễn giải ở tầng payload:
     - bắt buộc → `02-input/required-field-rule.md` (thiếu field → 400/422, KHÔNG phải "viền đỏ").
     - độ dài → `02-input/maxlength-rule.md` (BVA N-1/N/N+1 trên giá trị gửi lên; bỏ phần "đọc attr DOM maxlength" — không có DOM).
     - format/regex/kiểu → `02-input/textbox-base-rule.md` phần định dạng (bỏ phần thao tác gõ/space UI thuần; giữ trim/space-handling nếu server chuẩn hóa).
     - injection/payload độc → `02-input/security-input-rule.md` ở tầng API (SQLi/oversized body/type-confusion).
     - enum/giá trị-cho-phép → `03-selection/*` phần **allowed-values** (giá trị ngoài whitelist → lỗi), BỎ hành vi combobox/render UI.
   - **Validation nghiệp vụ:** `06-validation/duplicate-data-rule.md`, `06-validation/error-response-behavior-rule.md` ở tầng API (mã lỗi + status + side-effect DB, thay "toast").
   - **KHÔNG áp (đánh dấu N/A, 0 case):** `01-ui/*`, `02-input` phần thao tác bàn phím/space thuần-UI, `03-selection` phần render dropdown, `04-dynamic-form/*`, `datepicker`/`file-upload` phần widget UI, `09-data-grid` phần hiển thị bảng — **trừ khi** operation là query/list endpoint (khi đó lấy phần *logic phân trang/filter* của `09`/`11` ở tầng response, bỏ phần render).
   - **[!CAUTION] Dynamic Data Gate — vẫn BẮT BUỘC (workflow Quality Gate 3b):** quét field request là khóa tra cứu (FK/lookup do hệ thống khác cấp) hoặc `UNIQUE`/`PK` → `view_file` [dynamic_data_rules.md](./dynamic_data_rules.md), phân Tier, ghi `source_id`. Service surface **dễ dính** vì payload hay chứa mã do backend cấp (subId, merchantCode, transactionRef). CẤM hardcode.

5. **Đọc Rule kiểm thử (PRE-FLIGHT GATE):** `view_file` từng rule per-operation chưa có trong Ledger (10-be/*, 06-validation/*, và các input-rule được map ở tầng request).

6. **Tính số lượng case (Deterministic):** tổng case = cộng các nguồn dưới (đọc `cases_count` header rule, không đếm tay):
   - **Request validation:** mỗi field × các rule áp cho field đó (ở tầng request-body).
   - **Business logic / Decision Table:** vẽ bảng quyết định cho logic rẽ nhánh; mỗi dòng = 1 case (tổ hợp > 30 dòng → script `allpairspy`, như UI).
   - **State machine:** mỗi transition **hợp lệ** = 1 case; mỗi transition **KHÔNG hợp lệ phải bị chặn** = 1 case (rule tài chính: cấm set status tự do).
   - **Error catalog completeness:** mỗi mã lỗi trong catalog (chốt chặn 3) = ≥1 case kích hoạt → assert đúng HTTP status + error body + **side-effect đúng** (0 row / bút toán đảo khi lỗi).
   - **Idempotency / dedupe** (BẮT BUỘC nếu operation ghi giao dịch tiền hoặc là consumer): gửi trùng `Idempotency-Key`/message id → assert **đúng 1** side-effect, lần 2 trả kết quả lần đầu, KHÔNG xử lý lại.
   - **Resilience (10-be):** timeout downstream, circuit breaker, retry-safety, partial failure → theo `cases_count` của `backend-resilience-rule`.
   - **Data-visibility / scope:** phạm vi dữ liệu theo owner/role → theo `data-visibility-rule`.
   - **AuthZ/IDOR:** ownership check + role check (xem §4 dưới).

7. **Tự đối soát (Self-Reflection):** bao phủ tổ hợp đa điều kiện + **đối chiếu error catalog** (mọi mã lỗi có case? mọi transition invalid bị chặn?).

8. **Bung testcase 3 nhóm (reframe cho service — KHÔNG checklist vào plan; theo slice_planning Chốt 8):**
   - **Nhóm 1 — Hợp đồng & Request Validation:** mọi field request × rule validation của nó (required/length/format/enum/injection) → mỗi case = 1 dòng testcase (bung ở Step 03). Bao gồm conformance schema/HTTP status của happy-path.
   - **Nhóm 2 — Nghiệp vụ & E2E (API → DB → downstream/event/audit):** mọi dòng Decision Table, mọi transition state machine, mọi mã error catalog + side-effect, idempotency/dedupe, resilience. **Mỗi dòng Decision Table/transition/error-code ánh xạ 1-1 thành 1 dòng testcase, cấm gộp.**
   - **Nhóm 3 — Phân quyền & ATTT:** IDOR/ownership, role/scope, injection, **rò rỉ dữ liệu nhạy cảm trong response/log** (PAN/OTP/token/mật khẩu — theo rule tài chính, cấm log thô).
   - Quy tắc Zero-Summarization + công thức phân rã toán học + không lộ mã hệ thống trong nội dung (dùng tên nghiệp vụ, ID chỉ ở phần `rule:`/`Ref:`) — **giữ nguyên như [slice_planning_rules.md §1.8](./slice_planning_rules.md)**.

9. **Ghi & Duyệt Plan (HITL GATE):** append vào `implementation_plan.md` theo [plan_template.md](../references/templates/plan_template.md) (dùng phần Contract Map thay Bảng UI Controls). Dừng/defer theo `run_mode` — [run_mode_rules.md §3](./run_mode_rules.md).

---

## 3. Oracle service (API-first) — thay quy tắc UI-first

Bề mặt `service` KHÔNG có `@oracle:ui`. Thứ tự ưu tiên oracle và prefix Expected result:

```
API: <HTTP status + response body/schema>   →  @oracle:api
DB:  <trạng thái/row/bút toán sau xử lý>     →  @oracle:db
MSG: <event/message phát ra outbox/topic>    →  @oracle:msg
Log: <audit trail append-only>               →  @oracle:log
```

- Mỗi mục test được ở tầng service **BẮT BUỘC có `@oracle:api`** (hoặc `@oracle:db`/`@oracle:msg` khi là job/consumer không trả HTTP). CẤM oracle nông kiểu "gọi API trả 200 là pass" — phải assert **body/schema + side-effect** (§1 explore: oracle phủ định bất biến).
- `Công cụ test` (cột markdown) = `Postman` / `RequestsLibrary` (API), KHÔNG `Chrome`.
- Tag surface: dùng **`@svc:<unit_id>`** thay cho `@scr:<unit_id>` (xem [automation_contract_rules.md §2](./automation_contract_rules.md)).

---

## 4. Surface Inventory (service) — reframe explore §2 cho tầng API

Áp ở [step-02b](../steps/step-02b-risk-allocation.md). Thay bảng bề mặt UI bằng bảng bề mặt service:

| Loại bề mặt service | Nhận diện | Bất biến BẮT BUỘC | Data đối nghịch phải seed |
|---|---|---|---|
| **Write op (create/update)** | endpoint ghi | **error-side-effect:** mỗi mã lỗi → HTTP status đúng + error body đúng + **DB 0 row / bút toán đảo** khi lỗi | tái lập từng nhánh lỗi: duplicate/conflict (409), validation (400/422), business-rule (422) |
| **Money op** | ghi giao dịch tiền / số dư | **rounding+scale đúng, currency khớp, không âm quỹ, không double-spend** khi 2 request song song | biên: 0, âm, max, scale lẻ, currency không thập phân; 2 request đồng thời |
| **Idempotent write / consumer** | có `Idempotency-Key` / tiêu thụ message | **dedupe:** request/message trùng → đúng 1 side-effect, lần 2 trả kết quả cũ | gửi trùng key/message id ≥2 lần |
| **Query / list endpoint** | trả danh sách | **filter-correctness** (mọi record khớp điều kiện, record không khớp vắng mặt, `count==kỳ vọng`) + **volume/pagination** (> page size không im lặng cắt) | ≥1 khớp + ≥2 không khớp; seed > page size |
| **Có phân quyền/scope** | dữ liệu theo owner/role | **cross-actor:** principal A không truy được resource của B (IDOR → 403/404 theo spec) | seed data ≥2 owner; gọi bằng token khác chủ |
| **State-changing** | chuyển trạng thái bản ghi | **state-machine:** transition hợp lệ đúng; transition KHÔNG hợp lệ bị chặn (không set status tự do) | đưa bản ghi về từng trạng thái rồi thử transition sai |
| **Gọi downstream** | call đối tác/core-banking | **resilience:** timeout → PENDING/UNKNOWN (không tự đoán success), circuit breaker mở, retry chỉ khi idempotent | mock downstream: timeout / 5xx / trả sai schema |

Đối soát gate (explore §2.2): in bảng `<bề mặt service> × <bất biến> → <@id | THIẾU>`. Còn `THIẾU` → bổ sung case (hoặc TBD-escape §3) trước khi sang Step 03.

---

## 5. Bridge sang qa-robot (API — vẫn theo POM)

- Với dòng `@exec:automate` bề mặt `service`, `/ntapp-qa-robot` sinh keyword bằng **RequestsLibrary** (hoặc client tương đương) — **vẫn tổ chức theo POM**: mỗi endpoint/operation là một "service object" (resource file đóng vai page-object), keyword = thao tác gọi + assert contract, tách khỏi test case như POM tách locator.
- Service surface **KHÔNG cần `ui_schema_{id}.json`** (không có selector). Thay vào đó `fixtures.yaml#automation_prereq` khai: `base_url`, `auth` (cách lấy token), `api_contract` (tham chiếu phần Hợp đồng trong DD/OpenAPI nếu có), `mocks` (các `[Downstream]` cần stub).
- Do đó Rule 6 pre-commit (thiếu `ui_schema` chặn) **không áp** cho code test service — nêu rõ ở Mục 5.3.
