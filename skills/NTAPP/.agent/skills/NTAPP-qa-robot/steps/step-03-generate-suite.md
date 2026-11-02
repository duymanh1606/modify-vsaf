# STEP 03: SINH TEST SUITE

> **Acting as:** [Agent Robot Generator](../agents/agent_robot_generator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R2, R3, R4, R8, R10, R11, R13/R14, R16. Chi tiết: [Robot Rules](../references/automation/auto_robot_rules.md) (§6 Suite & Imports — **BẮT BUỘC đọc**; §7 chọn oracle), [Framework Structure](../references/automation/auto_framework_structure.md), [Coding Convention §3](../references/automation/auto_coding_convention.md) (tên Test Case = `[mã KB-{id}-NN] - [mục tiêu]`, tag kebab-case).
> ⛔ Chỉ đọc step kế qua con trỏ Next ở CUỐI file — sau khi qua đủ cổng ra.

**Sinh `.robot` gọi các Keyword đã có từ Step 02.** `.robot` chỉ chứa logic nghiệp vụ — zero locator/URL/SQL/keyword-definition.

## 1. Input
Các `[Page|Service]Keywords.resource` từ [Step 02](step-02-generate-resources.md) · **`{qa_artifacts}/{id}/{id}_testspec.feature`** · manual testcase tại **`manual_testcase_path`** · `{id}_fixtures.yaml` + `datatest/` · `datatest/{id}_gen_manifest.yaml` từ [Step 01](step-01-parse.md) — `gen_run_id`, `excluded_ids`, `r10_decisions`, `cases[]`.

⛔ **`.feature` là nguồn CHÍNH của step này, phải ĐỌC THÂN scenario — không chỉ grep tag.** Nó canonical khi lệch `.md` (Step 01 §2) và là **nguồn duy nhất** của nhãn phân loại (R3). Cụ thể: `When/And` → chuỗi step (§3b) · `Then` → assert (§3c-d, R13) · tag → `[Tags]`. Mọi chỗ dưới đây viết "cột Kết quả mong muốn" đọc là **`Then` của scenario cùng mã**; `.md` chỉ dùng khi `.feature` vắng (lane HUB legacy) hoặc để lấy cột `Exec`/`Data Test`.

## 2. Tách file & đặt tên (CỨNG)

- **1 file `.robot` cho mỗi unit màn/operation**: UI chia theo `@scr:<unit_id>`, Service chia theo `@svc:<unit_id>`. Cấm gộp chung.
- **Tên file**: PascalCase theo tên màn/operation (vd: `LoginTest.robot`), cấm nhét ID slice/unit vào tên file. Mã unit đặt ở suite `Test Tags`; mã case `KB-{id}-NN` và các tag phân loại đặt ở per-test `[Tags]`.
- **Suite Setup/Teardown chung**: Tách ra `actions/common/SuiteFixtures.resource`, cấm copy-paste block Setup vào từng file suite.

## 3. Sinh Test Case

**a. Đồng bộ tăng dần (R16):** Case giữ nguyên không đụng, chỉ viết lại đúng khối Test Case của case `sinh lại` hoặc `thêm`. Cấm xoá trắng file.

**b. Map 1-1 theo hành vi (R2):** Mọi mệnh đề `When/And` phải được thực thi thật, cấm bỏ gesture (focus out, paste, Enter, double-click). **Gom chuỗi bước thao tác thành 1 keyword nghiệp vụ** (`Open Detail Tab    Sub-links`) thay vì bung từng dòng; lặp ở ≥3 case thì bắt buộc gom. Mức gom theo [robot §5](../references/automation/auto_robot_rules.md) — cấm gom cả case vào 1 keyword. **Assert giữ tường minh**: 1 assert / 1 mệnh đề `Then`, giá trị mong đợi qua tham số (`Sub Link Row Count Should Be    11`); cấm tên chung chung (`Should Be Complete` / `Valid` / `Correct`).

**c. Chọn oracle (R11 · R13):** UI assert render/value; Service assert status code + JSON path. Đếm `k` mệnh đề trong `Then` → sinh **≥ k assert**. Mỗi nhãn `@oracle:` (`ui`/`api`/`db`/`log`/`msg`) phải có khối assert của tầng đó.

**c2. Nhãn (R3):** Propagate nguyên văn `@block:` `@tech:` `@rule:` `@risk:` `@oracle:` của scenario gốc vào `[Tags]`, `@oracle` đủ **số lượng**; suite khai `Test Tags` mang `@scr:`/`@svc:`.

**c3. Đếm số lượng (R14):** Vế mong muốn là hằng số kịch bản hoặc giá trị fixtures. Cấm `> 0` / `>= 1`, cấm so số vừa đo với chính nó.

**c4. Test độc lập (R4 · R7b):** Mỗi test tự reset state bằng click (modal: đóng + mở lại). Để lưu lịch sử/audit, cấm xóa dữ liệu DB trong teardown; dữ liệu tạo ra mang định danh unique per-run và **bắt đầu bằng tiền tố `auto_`** (R7d) — sinh qua keyword dùng chung `Build Unique Name`, cấm test tự nối tên. Ngoại lệ: trường chỉ nhận số, ca biên độ dài. Tài nguyên precondition bị tiêu thụ: cấm resolve 1 lần rồi `Set Suite Variable`.

**c5. Dynamic-binding (db §11):** Marker `$db.query` / `$seed.*` gọi resolver keyword thật từ Step 02. Marker chưa resolve ghi ở "Data gaps", cấm stub.

**d. Toast/Error-path toast (R11):** Bắt buộc dùng phủ định `Page Should Not Contain` hoặc đếm `Get Element Count ... == 1`. Với toast biến mất nhanh, dùng MutationObserver trong JS lưu vào biến rồi assert.

**e. Dữ liệu (R8):** Lấy từ fixtures, cấm hardcode. Escape khoảng trắng bằng `${SPACE}`, chuỗi dài biên `<ký-tự>×N` expand qua `Evaluate  "a" * N`.

**f. Case pending/tbd (R10/R11):** Vẫn sinh Test Case, thêm tag `pending <bucket>` hoặc `tbd` và đặt bước đầu tiên là `Skip PENDING (<bucket>)` hoặc `Skip [TBD]`.

**g. Manifest `datatest/{id}_gen_manifest.yaml` (R16):** Merge thay vì rewrite.
- `cases`: Mỗi case có `src_hash` (hash dòng manual) + `last_gen_run` (gen_run_id hiện tại). Giữ nguyên entry case không đổi.
- `touched_files`: Mỗi entry `path` + `round` (vòng sửa hiện tại; lượt sinh đầu = `0`). Gộp file resource Step 02 và file suite Step 03 đụng trong lượt, KHÔNG xoá entry vòng cũ.
- `locators`: Giữ nguyên tuyệt đối các entry có `healed: true`.
- `gen_run_id`: Giữ nguyên mốc Step 01, cấm dùng `generated_at` làm mốc round.

## 4. Đầu ra yêu cầu
- `[Screen]Test.robot` (chỉ chứa settings, variables và test cases).
- `actions/common/SuiteFixtures.resource` (nếu tách).
- Cập nhật manifest `datatest/{id}_gen_manifest.yaml` theo định dạng merge (R16).

## 5. Cổng ra

Yêu cầu sinh nằm ở §3. Cổng ra chỉ **4 phép kiểm cơ học** — phần ngữ nghĩa (oracle, seed, test độc lập, phân tầng POM) do [Step 04](./step-04-review-code.md) chấm, KHÔNG tự chấm lại ở đây.

| # | Cổng | Rule | Pass khi |
|---|---|---|---|
| 1 | **Mã parity** | R3, R2 | Tập mã `.robot` = tập mã manual `automate` trừ `excluded_ids`. Ghi **số đếm** `A/B/C` + liệt kê **chỉ mã lệch** ([gate_commands §5](../references/automation/auto_gate_commands.md)); cấm in cả 2 danh sách mã. |
| 2 | **Nhãn đủ** | R3 | Mỗi test có đủ 5 nhóm nhãn (§3c2), `@oracle` đủ số lượng, suite có `Test Tags`. |
| 3 | **POM purity** | R4 | Suite không có `*** Keywords ***`, không locator/SQL/payload thô, không `[Template]`. |
| 4 | **No Sleep, no jump URL** | R9, R9b, R7s, R12 | Không `Sleep`/`Go To`/`Reload Page` (kể cả `.py`/JS). Chỉ 1 `Open Browser` ở Suite Setup. **Miễn trừ R9b:** test mang tag `nav-by-url` được dùng `Go To`/`Reload Page` — kiểm ngược lại: mọi test có `nav-by-url` phải có `When` nêu rõ deep-link/reload/back-forward, và mọi lời gọi `Go To`/`Reload Page` phải nằm trong test mang tag đó. |
| 5 | **Compile sạch** | R12 | `robot --dryrun --output NONE --log NONE --report NONE tests/` → **0 ERROR / 0 WARN**, không ghi file nào. Đỏ thì sửa tại đây, cấm sang Step 04/05. |
| 6 | **Manifest tồn tại** | R16 | `datatest/{id}_gen_manifest.yaml` **có thật trên đĩa**, đủ `cases` (mọi mã có `src_hash` + `last_gen_run`) + `touched_files` (có `round`) + `excluded_ids` + `r10_decisions`. Thiếu → FAIL, ghi tại đây, cấm sang Step 04 — không có manifest thì mọi vòng review đều phải đọc `full`. |

## 6. Cổng HITL trước khi sang Step 04

Qua đủ 6 cổng §5 rồi mới tới cổng này. `review_gate`: `ask` (default) · `auto` (đi thẳng) · `skip` (bỏ review, sang Step 05).

`ask` → **DỪNG hỏi user 1 câu** có chạy review không, kèm số case + số file trong `touched_files`:

- **Có** → đọc `./step-04-review-code.md`.
- **Không** → ghi `review_skipped: <lý do user>` vào `datatest/{id}_gen_manifest.yaml`, nêu trong báo cáo, đọc thẳng `./step-05-execute-and-analyze-logs.md`.

⛔ Chưa có trả lời thì KHÔNG đọc step kế.

**Next:** Theo lựa chọn ở §6.
