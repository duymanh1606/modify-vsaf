# STEP 02: SINH PAGE/SERVICE RESOURCES (VARIABLES & KEYWORDS)

> **Acting as:** [Agent Robot Generator](../agents/agent_robot_generator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R4, R7/R7s, R9, R16. Chi tiết: [Locator Strategy](../references/automation/auto_locator_strategy.md), [Robot Rules](../references/automation/auto_robot_rules.md) (§6 Generation Guidelines — **BẮT BUỘC đọc**), [Coding Convention](../references/automation/auto_coding_convention.md).
> ⛔ Chỉ đọc step kế qua con trỏ Next ở CUỐI file — sau khi qua đủ cổng ra.

**Sinh 1 folder + 2 file `.resource` cho mỗi Object mà Step 01 đã chốt.** `surface_type` quyết định nhánh: `ui` → §2 · `service` → §3. *(Unit hỗn hợp — TẬP `{ui, service}` → chạy **cả** §2 và §3, mỗi nhánh cho nhóm Object của nó.)*

## 1. Input

| Nguồn | Dùng để |
|---|---|
| Danh sách Object + `surface_type` + `locator_source` + `gen_run_id` | Từ [Step 01](step-01-parse.md) — quyết định sinh gì, lấy locator ở đâu, ghi manifest dưới mốc nào |
| `ui_schema_{id}.json` | **Checklist độ phủ control** — KHÔNG phải nguồn locator |
| `**/*.component.html` (template màn + component con) | Nguồn locator lớp 1-3 |
| `**/*.component.ts` | Field/cột config-driven |
| `**/i18n/*.json` | Text/aria/placeholder thật cho locator-theo-text |
| `{id}_testspec.feature` | Tên control + chuỗi hiển thị mà `Then` nêu → suy ra control nào cần locator |
| DD **per-unit** (`SCR-*`/`WGT-*`/`HUB-*`) | Fallback checklist control · schema hợp đồng. Thiếu thì bỏ qua, KHÔNG DỪNG |

> **Có fixture `$db.query`/`$seed.*`?** BẮT BUỘC đọc [DB/Oracle Rules §10-§11](../references/automation/auto_db_oracle_rules.md) **trước khi** viết resolver ở §4. Step 01 chỉ *lập kế hoạch* tier; step này *viết code* nên phải theo §11.

**Áp cho cả 2 nhánh — [R16] Variables.resource đã có từ run trước thì GIỮ, chỉ THÊM:** biến locator đã có → **giữ giá trị cũ**, KHÔNG đè bằng giá trị suy từ source lần này; biến `healed: true` trong `gen_manifest.yaml` → **tuyệt đối không đè**. Chỉ **thêm** biến cho control mới; locator trỏ control đã bị xoá khỏi màn → xoá kèm nêu trong báo cáo. Làm lại từ đầu chỉ khi user yêu cầu rõ hoặc file bị xoá tay ([R16 §16.3](../principles/iron_rules.md)).

## 2. Nhánh `ui` — Page Object (Selenium)

**a. Lấy locator theo `locator_source`:**
- **`source`** (có code FE): Đào đủ 4 lớp theo [Locator Strategy §1-5](../references/automation/auto_locator_strategy.md). Cấm absolute XPath.
- **`live-dom`** (không code FE): Chạy phiên soi DOM bằng Selenium (không phải test suite). Nếu thiếu driver/display -> DỪNG báo user, áp dụng fallback [§6.4](../references/automation/auto_locator_strategy.md).

**b. Điều hướng (R9):**
- Login và điều hướng sidebar đặt ở `Suite Setup` (1 lần/suite).
- Mỗi Test Case chỉ thao tác element của màn hình và reset state bằng click đóng/mở lại modal (R4). Cấm dùng `Go To` / `Reload Page`.

## 3. Nhánh `service` — Service Object (RequestsLibrary)

**a. Cấu trúc (R4):** 1 endpoint/operation = `{Service}Variables.resource` (base_url, path, headers) + `{Service}Keywords.resource` (keyword request + keyword assert).

**b. Quản lý phiên:** Khởi tạo session (`Create Session`) ở `Suite Setup`, lấy token gán header. Đóng session ở `Suite Teardown`.

**c. Keyword request:** Nhận payload qua `[Arguments]` lấy từ `datatest/` (R8), cấm hardcode. Keyword assert tách riêng (assert status code, JSON path, DB, MSG).

**d. Side-effect async:** Dùng `Wait Until Keyword Succeeds`, cấm dùng `Sleep` tĩnh (R7s).

**e. Mock downstream:** Dựng stub theo `automation_prereq.api.mocks` trước khi chạy.

## 4. Resolver dữ liệu mồi (Khi có `$db.query`/`$seed.*`)

Viết resolver theo [DB/Oracle Rules §10-§11](../references/automation/auto_db_oracle_rules.md):
1. Tách resolver đọc/hiển thị (đọc và cache) khỏi resolver tiêu thụ/tạo mới (KHÔNG cache).
2. Tra DB tái dùng bản ghi un-consumed trước. Thiếu bao nhiêu seed bù bấy nhiêu.
3. Tái dùng owner/container, cấm tạo owner mới ở mỗi case.
4. Sinh keyword seed đầy đủ, cấm sử dụng stub (`SEED-TODO` / placeholder).

## 5. Đầu ra yêu cầu
- Thư mục tuân thủ [Framework Structure](../references/automation/auto_framework_structure.md).
- File resource được tạo tại `actions/pageObject/` (ui) hoặc `actions/serviceObject/` (service).
- **Whitelist `actions/common/` — đúng 5 file:** `BasePage` (helper UI + shell dùng chung mọi màn: toast/modal/alert) · `BaseTest` (cấp suite + wrapper mở browser) · `GlobalConstants` (timeout/env) · `SuiteFixtures` (Setup/Teardown + session + auth + kết nối DB) · `SeedRegistry` (seed/teardown data). Keyword dùng chung 2+ màn xếp vào đúng 1 ô; **cấm file thứ 6** trừ khi nêu lý do trong báo cáo.
- Cập nhật import vào `configs/imports.resource`.
- Manifest `datatest/{id}_gen_manifest.yaml` được cập nhật: ghi nhận locator mới (healed: false, giữ nguyên healed: true cũ) và append vào `touched_files` kèm `round` (lượt sinh đầu = `0`, vòng sửa sau review = số vòng đó).
- File Python `.py` (nếu có) phải mang header quy định để pass pre-commit hook (R15).

## 6. Cổng ra

| Cổng | Rule | Pass khi |
|---|---|---|
| **Locator valid + Smart Wait** *(ui)* | R7 | Locator dò đúng nguồn, dùng explicit wait, cấm `Sleep` tĩnh. |
| **Contract valid + no Sleep** *(service)* | R7s | Endpoint/field khớp Contract Map, cấm `Sleep` tĩnh. |
| **Seed đầy đủ** | R15 | Keyword seed được sinh đầy đủ cho các `$seed.*`, không dùng stub. |
| **Không headless / lách gate** | R12 | Quét code theo [gate_commands §3 và §4](../references/automation/auto_gate_commands.md), không chứa vi phạm. |

**Next:**
- **Lượt sinh mới** -> `./step-03-generate-suite.md`.
- **Chỉ sửa resource** (sau review FAIL) -> Quay lại `./step-04-review-code.md` (chạy trực tiếp review cho touched files).
- **Sửa cả file suite `.robot`** -> Chạy tiếp sang `./step-03-generate-suite.md`.
