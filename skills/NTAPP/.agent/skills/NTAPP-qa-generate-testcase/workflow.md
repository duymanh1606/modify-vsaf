# WORKFLOW: NTAPP QA GENERATE SLICE TESTCASE (E2E + AUTOMATION-READY)

## Goal
Sinh kịch bản kiểm thử E2E cho một **SLICE** (nhiều unit) HOẶC một **đơn vị đứng riêng** (`{id}` = HUB/WGT/SCR/MPF… — tính năng không gom vào SLICE), đạt Coverage Gate 100% luồng E2E, **theo School B**: shift-left → risk-based allocation → **triple-emit** (`.feature` canonical + markdown view + `fixtures.yaml`) để output dùng trực tiếp cho automation qua `/ntapp-qa-robot`.

> **Hai lane input** (auto-detect ở Step 00): `slice` — có file `{slices_root}/{id}-*.md` → phối hợp nhiều unit + xếp thứ tự E2E · `unit` — không có file SLICE nhưng có `{id}_detailed_design.md` → coi như "slice một unit", bỏ bước xếp thứ tự liên-unit, giữ nguyên triple-emit + risk allocation + per-screen. **Mọi định danh dùng chung một khóa `{id}`** = ID đầy đủ (vd `SLICE-06` / `WGT-SIDEBAR`); output luôn nằm dưới `{qa_artifacts}/{id}/`.

## Your Role
Bạn điều phối một **Senior QA Engineer** chạy vòng lặp qua các chốt chặn (PRE-FLIGHT GATE, HITL GATE). Toàn bộ workflow tuân thủ [`principles/iron_rules.md`](./principles/iron_rules.md) + [`principles/automation_contract_rules.md`](./principles/automation_contract_rules.md) + [`principles/run_mode_rules.md`](./principles/run_mode_rules.md). **CẤM TUYỆT ĐỐI đọc trước tài liệu bước sau hoặc thực thi bước tiếp khi bước trước chưa Approve** — *trừ khi lane `batch` đã defer HITL (auto-proceed có kiểm soát) hoặc lane `delta` đi entry tắt; mọi internal checkpoint (Math Check, Sync Invariant) vẫn enforce.*

## Run Mode (3 lane — xem [principles/run_mode_rules.md](./principles/run_mode_rules.md))
Lane điều chỉnh *tần suất dừng người* (HITL) + *phạm vi reload* + *điểm vào*; **KHÔNG** nới Iron Rules / độ phủ.

| Lane | HITL gate | Reload | Khi dùng |
|---|---|---|---|
| `full` *(default)* | 4 (E2E + Plan + per-screen + finalize) | per-screen đầy đủ | Slice mới quan trọng, governance/audit |
| `batch` | **2** (E2E flow + batch review cuối) — auto-proceed giữa màn | scoped (Context Ledger) | Lặp nhanh, ít gián đoạn |
| `delta` | **0–1** (in delta-map, 1 OK) | chỉ tài liệu delta | Re-run trên slice đã có 3 artifact |

## Workflow Steps
```
[Input: {id}  → lane SLICE nếu có {slices_root}/{id}-*.md · lane UNIT nếu chỉ có {id}_detailed_design.md]
       │
       ▼
0. steps/step-00-shiftleft-gate.md  (Detect input_type + surface_type(ui|service) + Resolve run_mode + auto-detect delta · Shift-left: ambiguity / delegate qa-audit)
       │
       ├─[run_mode=delta · 3 artifact đã tồn tại]──────────────► 5. step-05-roundtrip.md (Nhánh A: delta-map → patch) ──► Output
       │
       ▼ (full / batch)
1. steps/step-01-init-slice.md  (lane SLICE: đọc SLICE → luồng E2E nhiều unit · lane UNIT: 1 unit, bỏ xếp thứ tự liên-unit · surface ui→màn / service→operation · map FE-BE / Contract · DỰNG Context Ledger load-once)
       │
       ▼ [HITL GATE: Duyệt luồng E2E + Ledger]  (giữ ở mọi lane)
┌── VÒNG LẶP PER-MÀN: mỗi màn/operation chạy TRỌN 2 → 2b → 3 rồi MỚI sang màn kế (cấm gom 2+2b nhiều màn) ──┐
2. steps/step-02-plan-screen.md  (Test Plan cho ĐÚNG 1 màn hiện tại · ui→9 chốt slice_planning · service→9 chốt service_surface · scoped reload)
       │
       ▼ [HITL GATE: Duyệt Plan]  (full: dừng · batch: defer, checkpoint im lặng)
2b. steps/step-02b-risk-allocation.md  (Gán @risk + @exec/@oracle/@target CHO CHÍNH MÀN ĐÓ; mode exhaustive|risk-gated)
       │
       ▼
3. steps/step-03-write-testcase.md  (TRIPLE-EMIT cho MÀN ĐÓ: .feature + bảng 11 cột + fixtures.yaml · scoped reload)
       │
       ▼ [HITL GATE: chuyển màn]  (full: dừng · batch: auto-proceed)
└── CÒN màn/operation? → quay lại 2 cho MÀN KẾ (khép kín 1 chu trình/màn). HẾT màn → xuống 4 ──────────────┘
4. steps/step-04-finalize-testcase.md  (Hợp nhất fixtures, Coverage Debt Ledger 5.6, Final Sync Audit · batch: HITL review GỘP cuối)
       │
       ▼ (tùy chọn) 5. steps/step-05-roundtrip.md  (Delta update + nuốt results/ từ qa-robot)
       │
       ▼
[Output 3 artifact tại {qa_artifacts}/{id}/]
  - {id}_testspec.feature                      (CANONICAL → automation)
  - {id}_detailed_test_manual_testcase.md      (VIEW → QA ký + qa-robot parse)
  - {id}_fixtures.yaml                          (DATA máy-đọc)
  (Ngoại lệ: {qa_artifacts}/data_sources.yaml — registry dùng CHUNG nhiều slice/unit, KHÔNG nằm trong {id}/)
       │
       ▼ [Bridge] /ntapp-qa-robot {id}  → sinh Robot POM + EXECUTE (chỉ dòng Exec=automate)
```

> **VÒNG LẶP PER-MÀN (IRON — mọi lane):** Sau Step 01, xử lý **tuần tự từng màn/operation một**. Với mỗi màn chạy KHÉP KÍN chuỗi `Step 02 (plan/Math Forcing) → Step 02b (policy @risk/@exec) → Step 03 (triple-emit + HITL)` rồi MỚI chuyển sang màn kế. **CẤM batch theo pha** — không lập plan (02) cho toàn bộ màn trước rồi mới emit (03) hàng loạt. Lane `batch` chỉ hoãn *điểm dừng người* (HITL), KHÔNG cho phép gộp pha xuyên màn. Enforce cơ học: Step 03 §1b (GATE plan-exists per-màn) + Step 03 §11 (loop-back về Step 02 khi còn màn).

## Quality Gates Map
1. **Shift-left Gate (Step 00):** Có `qa-audit` report hoặc mini-audit; không thiết kế test trên spec mơ hồ.
2. **HITL GATE (Duyệt E2E Flow - Step 01):** Dừng chờ User duyệt luồng E2E + Context Ledger. *(Giữ ở mọi lane.)*
3. **Missing File Guard (Step 02):** Báo lỗi và dừng nếu thiếu file `_detailed_design` của unit.
3b. **Dynamic Data Gate (Step 02 — [BẮT BUỘC, KHÔNG ĐƯỢC BỎ QUA]):** Với MỌI field Runtime-dependent (filter/search gọi service khác, checkbox/lựa chọn lấy từ danh sách API khác, ID/mã do hệ thống khác cấp phát dùng làm điều kiện tra cứu, field `UNIQUE`/`PRIMARY KEY`) — bắt buộc `view_file` đọc [principles/dynamic_data_rules.md](./principles/dynamic_data_rules.md) và chạy thuật toán §2 để phân loại Tier trước khi tính case ở Chốt chặn 6 của Step 02. Đây là gate **tách riêng** khỏi Bảng Mapping Rule UI (`kbkt-generation/**`) — KHÔNG được coi là đã xong chỉ vì đã có Mapping Rule cho control UI. Bỏ qua gate này là nguyên nhân phổ biến khiến `fixtures.yaml` hardcode ID/mã tra cứu không có thật trong môi trường Staging.
4. **HITL GATE (Duyệt Plan - Step 02):** `full` dừng chờ duyệt Plan (Math Forcing + Bảng Mapping Rule + Dynamic Data) · `batch` defer (checkpoint im lặng).
5. **Allocation Gate (Step 02b):** Mọi mục có đủ `@risk`+`@exec`; không P0 nào exploratory; oracle-first đúng bề mặt (`ui`→`@oracle:ui`/`@scr` · `service`→`@oracle:api`/`@svc`, cấm `@oracle:ui`); tính `X` (số case sau mode). *(Internal — mọi lane.)*
6. **Automation Emit + Sync Invariant Gate (Step 03):** áp mô hình **"1 số gốc + 2 phép chiếu"** ([automation_contract_rules.md §1](./principles/automation_contract_rules.md) — CANONICAL): **gate gốc `Y == X`** (`X` = tổng Math Forcing chốt ở Step 02/02b, `Y` = tổng dòng markdown KỂ CẢ manual); phép chiếu 1 `count(@id .feature) == A+E`; phép chiếu 2 `count(dataset fixtures) == A`. Tag đầy đủ; **fixtures.yaml không hardcode field Loại 1/2 đã phân loại ở Gate 3b** (phải dùng `$db.query`/`$seed.create`/`$uuid`/`$timestamp` + có `data_sources.yaml` tương ứng). **[HARD CHECK cross-artifact]** so `.md`(Exec∈{automate,exploratory}) ↔ `.feature`(@id) bằng `comm` (automation_contract_rules §1) — kèm **sàn chống false-pass** (`N_md == A+E`; `N_md==0` → FAIL, không PASS); CẤM đếm nội bộ `.feature` (tautology); `comm` không rỗng → DỪNG, bổ sung @id thiếu. *(Internal — mọi lane; lệch ở `batch` → rớt về dừng-tại-màn.)*
7. **HITL GATE (Chuyển màn - Step 03):** `full` dừng duyệt từng màn · `batch` auto-proceed (gộp về Gate 8).
8. **Final Sync Audit + Batch Review (Step 04):** Mọi `@id` đồng bộ 3 artifact; ID liên tục (R8); prereq automation thiếu được liệt kê (*ui*: `ui_schema` · *service*: `base_url`/`auth`/`api_contract`/`mocks`). **Cổng terminal chạy lại HARD CHECK cross-artifact** (`comm` `.md` Exec∈{automate,exploratory} ↔ `.feature` @id phải rỗng, kèm sàn `N_md==A+E`). `batch`: là **HITL review gộp duy nhất** (gate gốc `Y==X` + 2 phép chiếu PASS toàn slice trước khi mở).

## Bản đồ Luật theo Step (chỉ nạp luật liên quan — tiết kiệm context)
> `iron_rules.md` + `run_mode_rules.md` là **xuyên suốt** (mọi step ngầm tuân). Bảng dưới chỉ liệt kê luật **đặc thù** cần `view_file` thêm cho từng step — KHÔNG nạp cả 10 principle mỗi bước.

| Step | Principle đặc thù cần nạp | Reference / template |
|---|---|---|
| 00 shift-left | — *(chỉ xuyên suốt)* | — |
| 01 init slice | `unit_classification_rules` (ui, gồm §4 scope) **hoặc** `service_surface_rules §1` (service) · **`borrowed_surface_rules` (khi `units:` toàn BE mà `What to build`/`demoable` nêu màn của slice khác)** | — |
| 02 plan screen/op | *(ui)* `slice_planning_rules` · `unit_classification §4` · `markdown_safety §4` **hoặc** *(service)* `service_surface_rules §2` · `markdown_safety §4` · **`dynamic_data_rules` (BẮT BUỘC nạp riêng, xem Quality Gate 3b — cả ui lẫn service, dù không có field nào "trông giống" unique/FK)** | `templates/plan_template.md` · `kbkt-generation/**` (ui: control rule · service: 10-be + request-validation) |
| 02b risk alloc | `risk_based_allocation_rules` · `explore_and_consistency_rules` (Oracle phủ định + Surface Invariant §2 + TBD-escape §3) · *(service)* `service_surface_rules §3–§4` (API-first oracle + Surface Inventory service) | — |
| 03 write testcase | `testcase_generation_gates` · `automation_contract_rules` (tag `@scr`/`@svc` theo bề mặt) · `markdown_safety_rules` · **`dynamic_data_rules` (đối chiếu lại khi viết `overrides` trong `fixtures.yaml` — xem Quality Gate 6)** · *(service)* `service_surface_rules §5` (bridge) | `templates/slice_testcase_table_template.md` · `templates/testspec_feature_template.feature` · `templates/fixtures_template.yaml` · `kbkt-generation/00-core/*` |
| 04 finalize | `finalization_rules` · `automation_contract_rules` · `markdown_safety_rules` · `explore_and_consistency_rules` (§4-§5 materialize KHỐI 2/3 + Coverage Debt Ledger §3) | — (KHÔNG dùng charter template) |
| 05 round-trip | `incremental_update_rules` | — |

## Configuration Resolution
Resolve config theo cascade 3 layer:
1. **Layer 1 (Resolve `{project-root}`):** Tìm thư mục chứa `_bmad/` hoặc `.git/` từ `cwd`.
2. **Layer 2 (BMad config):** Đọc `{project-root}/_bmad/bmm/config.yaml` lấy `project_name` và `stage_5_build_verify`.
3. **Layer 3 (Override/Fallback):** Đọc `{project-root}/.bmm-config.yaml` mục `ntapp-qa-generate-testcase:`. Nếu thiếu, default `qa_artifacts` = `{project-root}/_bmad-output/Stage_5_Build_Verify/test`.

### Runtime Variables
- `project_name`: Header tài liệu.
- `qa_artifacts`: Đường dẫn ghi output file.
- `id`: **khóa định danh duy nhất** — ID đầy đủ của SLICE (vd `SLICE-06`) hoặc đơn vị đứng riêng (vd `WGT-SIDEBAR`, `HUB-01`). Mọi tên file/thư mục output đều dẫn xuất từ đây (`{qa_artifacts}/{id}/{id}_*`).
- `input_type`: `slice` \| `unit` — resolve ở Step 00 (xem quy tắc detect). Điều khiển nhánh Step 01.
- `slices_root`: Thư mục chứa file SLICE đầu vào (Mặc định: `{stage_5_build_verify}/slices`). Chỉ dùng khi `input_type=slice`.

### Cờ cấu hình mới (Layer 3 `.bmm-config.yaml` mục `ntapp-qa-generate-testcase:`)
- `run_mode` *(`full`\|`batch`\|`delta`, default `full`)*: lane chạy — giảm ceremony / incremental / scoped reload (xem [run_mode_rules.md](./principles/run_mode_rules.md)). Override được bằng ý định trong câu lệnh; `delta` còn auto-detect khi 3 artifact đã tồn tại.
- `emit_automation` *(bool, default `true`)*: bật triple-emit (`.feature` + `fixtures.yaml`). `false` → chỉ markdown (legacy).
- `risk_mode` *(`exhaustive`\|`risk-gated`, default `exhaustive`)*: độ bung case theo risk (xem [risk_based_allocation_rules.md](./principles/risk_based_allocation_rules.md)).
- `shiftleft_required` *(bool, default `true`)*: bắt buộc có `qa-audit` report hoặc mini-audit ở Step 00.
- `automation_target` *(`robot`\|`playwright`, default `robot`)*: đích mặc định cho `@target`.

## Output Naming (Triple-Emit)
- **Mọi output riêng của 1 SLICE/unit nằm dưới `{qa_artifacts}/{id}/`** (không còn flat trực tiếp dưới `{qa_artifacts}/`). `{id}` = ID đầy đủ (SLICE-06 / WGT-SIDEBAR) → tên file slice cũ (`SLICE-06_*`) giữ nguyên, không đổi.
- **Test Plan (Nháp):** Lưu trực tiếp vào `{qa_artifacts}/{id}/{id}_implementation_plan.md` (Không lưu tệp phụ).
- **Canonical (Gherkin):** Ghi đè `{qa_artifacts}/{id}/{id}_testspec.feature`.
- **View (Manual Testcase):** Ghi đè `{qa_artifacts}/{id}/{id}_detailed_test_manual_testcase.md`.
- **Data (Fixtures):** Ghi đè `{qa_artifacts}/{id}/{id}_fixtures.yaml`.
- **Q&A audit report (đọc từ `/ntapp-qa-audit`):** `{qa_artifacts}/{id}/{id}_qa_report.md`.
- **Ngoại lệ dùng chung nhiều slice/unit (KHÔNG nest):** `{qa_artifacts}/data_sources.yaml` (registry dynamic data — xem `principles/dynamic_data_rules.md`).
- Tất cả canonical-only (R6) — ghi đè, không archive/_vN.


