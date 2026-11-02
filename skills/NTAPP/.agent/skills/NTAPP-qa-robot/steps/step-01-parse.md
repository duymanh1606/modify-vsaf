# STEP 01: ĐỌC MANUAL TESTCASE & LẬP KẾ HOẠCH SINH CODE

> **Acting as:** [Agent Robot Generator](../agents/agent_robot_generator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R1, R2, R3, R5, R6, R10, R11, R16. Chi tiết: [Robot Rules](../references/automation/auto_robot_rules.md), [Framework Structure](../references/automation/auto_framework_structure.md).
> ⛔ Chỉ đọc step kế qua con trỏ Next ở CUỐI file — sau khi qua đủ 4 cổng ra.

**Step này CHƯA sinh code.** Nó chốt 7 thứ cho Step 02/03/04: `{code_repo_root}` · `manual_testcase_path` · `surface_type` · `locator_source` · `excluded_ids[]` · case nào `run`/`pending`/`tbd` · case nào giữ/sinh lại/thêm/xoá.

## 1. Input

`{id}` = ID đầy đủ (`SLICE-06` / `WGT-SIDEBAR` / `HUB-01`); 3 file đầu ở `{qa_artifacts}/{id}/`.

| File | Vai trò | Thiếu thì |
|---|---|---|
| `{id}_detailed_test_manual_testcase.md` | Bản QA ký — dùng **cột mã** + **cột `Exec`**; cột "Data Test" chỉ khi vắng fixtures. KHÔNG phải nguồn assert | DỪNG (R5) |
| `{id}_testspec.feature` | Gherkin + tag — **nguồn DUY NHẤT sinh script**, canonical khi lệch `.md` | **DỪNG (R5)**. Chỉ bỏ qua ở lane HUB legacy vốn không có file này |
| `{id}_fixtures.yaml` | Nguồn data mồi duy nhất (`datasets[]` + `automation_prereq` + marker `$…`) | rơi về nhánh 6b |
| `{ui_schema_root}/ui_schema_{id}.json` *(ui)* | Checklist control cho selector | DỪNG (R5) nếu `automation_prereq.ui_schema_required` khai. Lane HUB legacy: DỪNG khi bề mặt `ui` không có checklist nào |
| `{detailed_design_root}/*_detailed_design.md` | Tham chiếu bổ trợ khi `.feature` nói vắn. Lane SLICE dùng DD **từng unit** (`@scr`/`@svc`), KHÔNG có `{slice_id}_detailed_design.md` | **KHÔNG DỪNG** — bỏ qua, nêu 1 dòng |
| `{qa_artifacts}/data_sources.yaml` | Registry sinh **data động** (auth · create_api · lookup · reuse_check · teardown) — vai trò chính. Kèm theo đó là base URL / env prefix / tài khoản đã verify của chính nguồn seed: có sẵn thì dùng, cấm hỏi lại | DỪNG (R5) nếu fixture có `$db.query`/`$seed.*` |
| `project_wbs.md` (`{planning_artifacts}`) | `{id}` có trong WBS — R7 #1 | Không có trong WBS → **DỪNG**. WBS chưa tồn tại → bỏ qua, nêu 1 dòng |

Tag / marker lạ → propagate nguyên văn + nêu trong báo cáo, KHÔNG suy nghĩa (R1).

## 2. Trình tự thực thi — đúng thứ tự này

**1. Chốt nơi ghi code (R6).** Resolve `{code_repo_root}`; chưa chốt → **KHÔNG sinh file nào**. Mọi path output relative theo biến này.

**2. Tìm testcase.** Tìm `{qa_artifacts}/{id}/{id}_detailed_test_manual_testcase.md` (hoặc `{qa_artifacts}/{id}_*.md` flat legacy). Nếu thiếu → **DỪNG (R5)**. Chốt đường dẫn tuyệt đối vào `manual_testcase_path`. Nếu vắng `.feature`, lấy mã từ `.md` và điền `N/A` cho nhãn thiếu, cấm bịa (R1).

**2b. R7 #3 — so khớp tập mã `.feature` ↔ `.md`.** Mã có bên này thiếu bên kia → **DỪNG**, báo `@id`. Bám theo `.feature` làm canonical, ghi nhận lệch trong báo cáo.

**3. Lọc phạm vi automation (R2).** Lọc dòng có `Exec = automate` VÀ `@target` ∈ {`robot`, vắng} (nếu không có cột `Exec` -> coi tất cả là automate). Các case có `@target` khác lưu vào `excluded_ids[]`.

**4. Xác định `surface_type`.** Đọc tag scenario thật (`@scr` -> UI, `@svc` -> Service).
- Một scenario mang cả hai tag → **DỪNG (R5)**.
- Có cả scenario `@scr` và `@svc` riêng biệt → `surface_type` là **TẬP** (chạy cả hai nhánh).

**5. Detect `locator_source`** *(chỉ `ui`)*: `source` (đọc được `*.component.html`) · `live-dom` (app staging login được + `automation_prereq` có `base_url`/`auth`/đường click) · không có cả hai → **DỪNG (R5)**.

**6. Chép dữ liệu mồi sang code repo.** Suite chạy ở code repo, CI không thấy spec repo (R6) → data phải đi cùng code. Đây là bước **sao chép**, không giải mã.

- **a. Có `fixtures.yaml`** → chép `datasets[]` + `automation_prereq.mocks` sang `datatest/{id}_dynamic_fixtures.json` **nguyên giá trị** (YAML→JSON, runtime đọc bằng stdlib). Kèm `source_fixtures` (path) + **`source_sha256`** (hash nguồn — thứ duy nhất phát hiện bản sao cũ khi chạy lại). `<ký-tự>×N` và marker `$…` **giữ nguyên văn** — runtime xử (`Resolve Fixture Value` + `SeedRegistry`).
- **b. Không có fixtures** → chuyển cột "Data Test" thành cùng file đó, mỗi `@id` → 1 object `field: value`. Prose không đủ → ghi "Data gaps", KHÔNG bịa (R1).
- **c. Có `$db.query`/`$seed.*`** → kiểm `data_sources.yaml` có entry; thiếu → **DỪNG (R5)**. Chép marker vào khoá `bindings`.
- **d. Đọc `automation_prereq`** → thiếu prereq theo bề mặt (`ui`: `base_url`/`auth` · `service`: `api`/`mocks`) → **DỪNG (R5)**.
- **e. Hằng số môi trường** (base URL, endpoint, port, tên tài khoản): `[TBD]` cấm bê thẳng vào code. Tra 3 nguồn — (1) `data_sources.yaml` (phụ phẩm của registry seed: base URL, env prefix, tài khoản) · (2) `*_fixtures.yaml` slice cùng feature · (3) config code repo (`environment*.ts`, `proxy.conf*.json`, `application*.yml`) + DD "Stag environment". Tra ra → làm **default biến env** + comment nguồn `file:dòng`; cả 3 rỗng mới `[TBD]`. Secret luôn chỉ đọc env. Chỉ hỏi user phần đã tra hết vẫn rỗng.

*Tên file output bắt buộc là `datatest/{id}_dynamic_fixtures.json`, chứa 2 khoá `datasets` + `bindings`.*

**7. Xác định Object cần tạo.**
- `ui`: Mỗi màn hình = 1 Page Object PascalCase.
- `service`: Mỗi endpoint/operation = 1 Service Object. Cấm tự phát sinh Object ngoài spec (R3).

**8. Quyết định chạy/hoãn (R10).** Phân nhóm nhạy cảm theo R10, áp dụng `deferred_run_policy` (`ask`/`run-all`/`defer-all`) và gán `run_state: run|pending` kèm `bucket` + `reason`.

**8a2. Quét emoji trong expected.** `Then` chứa emoji (U+2600-27BF, U+1F300-1FAFF) → nghi bị chép từ wireframe (UI code cấm emoji, Rule 9). Đối chiếu mô tả text/i18n của DD: lệch → dừng báo user sửa `.feature`, KHÔNG tự bỏ emoji trong assert.

**8b. Quét [TBD] (R11).** Trường hợp expected chứa `[TBD-spec]` hoặc `[TBD-data]` → gán `run_state: tbd` (không gắn tag `pending`).

**9. Kế hoạch đồng bộ (R16).** Đối chiếu manifest cũ `datatest/{id}_gen_manifest.yaml` (nếu có) để phân chia case: giữ nguyên / sinh lại / thêm / xoá.

**9b. Quản lý `gen_run_id`.** Kế thừa `gen_run_id` từ `results/{id}_robot_review.md` nếu có (để giữ vòng sửa), ngược lại tạo mới. Cấm dùng `generated_at` làm mốc tính round.

**10. Kết quả bước 1.** In ra chat: qa_artifacts, code_repo_root, manual_testcase_path, surface_type, locator_source, gen_run_id, số case loại và kế hoạch đồng bộ (giữ nguyên/sinh lại/thêm/xoá).

## 3. Đầu ra
* **`datatest/{id}_dynamic_fixtures.json`** (luôn có): Chứa dữ liệu mồi (`datasets` + `bindings`).
* **`datatest/{id}_gen_manifest.yaml`** (**luôn ghi** — chưa có thì tạo): Step 01 ghi các khoá `id`, `gen_run_id`, `generated_at`, `excluded_ids` (rỗng thì ghi `[]`), `r10_decisions`, và `cases[]` — mỗi case `id`, `run_state` (`run|pending|tbd`), `bucket`, `reason`, `sync_action` (`giữ nguyên` | `sinh lại` | `thêm` | `xoá`). Step 02/03 bổ sung `src_hash`, `last_gen_run`, `touched_files`, `locators` vào **cùng file** (merge, cấm rewrite).
  > ⛔ Một chiều `manifest → [Tags]`. Sau Step 03, **tag là nguồn sự thật**; lệch nhau thì manifest sai → cập nhật manifest theo suite, không sửa suite theo manifest.
* *Cấm ghi file rác ngoài whitelist (R6b).*

## 4. Cổng ra
1. **Resolved `{code_repo_root}`** (R6) đã chốt + in ra chat.
2. **Đọc được đầy đủ input** (R5, R7), không lỗi drift mã `.md` ↔ `.feature`.
3. **Mọi case đã phân loại `run_state`** (R10, R11).
4. **Có kế hoạch đồng bộ tăng dần (R16)** khi chạy lại.

**Next:** Đọc và thực hiện theo `./step-02-generate-resources.md`
