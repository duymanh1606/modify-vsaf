# WORKFLOW: NTAPP QA ROBOT AUTOMATION GENERATOR

Sinh **mã nguồn Robot Framework chuẩn POM** từ manual testcase đã chốt (HUB 10 cột / SLICE 11 cột +`Exec`): parse → Page Resources → Test Suite → **review code** → execute + self-heal. Nguồn vào là manual testcase + `.feature` + fixtures; tài liệu thiết kế L2/L3 + UI Semantic Schema làm tham chiếu.

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này chỉ giữ KHUNG điều phối (bản đồ + cổng + rule). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần: xong step hiện tại (gồm mọi cổng dừng) mới đọc step kế qua con trỏ Next. State chuyển tiếp qua artifact output, không qua instruction giữ trong context.

---

## Goal

Chuyển đổi chính xác 1-1 từng bước manual testcase thành Robot keyword, đóng gói theo Page Object Model (locator/action tách khỏi test suite), chạy thật và tự sửa (self-healing) khi FAIL do locator/timing.

## Your Role

- Step 01-03 + 05: [Agent Robot Generator](./agents/agent_robot_generator.md) — Senior Automation Engineer / Robot Framework Architect. Persona này tự chứa năng lực **self-healing** (Step 05 re-derive locator + retry) — KHÔNG có agent locator-healer riêng.
- Step 04: [Agent Robot Reviewer](./agents/agent_robot_reviewer.md) — reviewer ĐỘC LẬP, chỉ emit verdict + vi phạm, KHÔNG sửa code. Vào step này chỉ khi user đã duyệt cổng `review_gate` ở [step-03 §6](./steps/step-03-generate-suite.md); khi đó **BẮT BUỘC dispatch subagent riêng** (fresh context). CẤM tự review thay.

---

## INITIALIZATION (Configuration Resolution)

Resolve cấu hình trước khi chạy bất kỳ step nào theo cascade 3 layer:

### Bước 0 — Resolve `{project-root}` (spec repo - nơi ĐỌC input)
Walk up từ `cwd` tìm marker: `_bmad/` → `{project-root}`; else `.git/` → `{project-root}`; else fallback `cwd` + warning.

### Bước 0b — Resolve `{code_repo_root}` (nơi GHI robot code)
1. Layer 2 `.bmm-config.yaml` § `ntapp-qa-robot.code_repo_root` -> Dùng luôn.
2. Nếu `cwd` khác `{project-root}` và có `.git/` riêng -> `code_repo_root = cwd`.
3. Fallback: DỪNG hỏi user và ghi vào `.bmm-config.yaml`.
*Lưu ý:* In `{code_repo_root}` ra chat + xác nhận ở Step 01 trước khi ghi file. Mọi path output relative theo `{code_repo_root}`.

### Layer 1 — BMad project config
Đọc `{project-root}/_bmad/bmm/config.yaml` lấy: `project_name`, `stage_5_build_verify`, `stage_4_design`, `planning_artifacts`.

### Layer 2 — Skill family config (override)
Đọc `{project-root}/.bmm-config.yaml`, section `ntapp-qa-robot:`:
```yaml
ntapp-qa-robot:
  qa_artifacts: <path>            # optional, override default
  code_repo_root: <path>          # optional - nơi ghi robot code (R6)
  detailed_design_root: <path>    # optional - DD per-unit
  ui_schema_root: <path>          # optional - nơi có ui_schema_{id}.json
  review_gate: ask                # ask (default) | auto | skip — cổng HITL đầu Step 04
  review_escalation: interactive  # interactive (default) | ci
  deferred_run_policy: ask        # ask (default) | run-all | defer-all
```

### Layer 3 — Default + Interactive (fallback)
* `qa_artifacts` default = `{stage_5_build_verify}/test`. Nếu không tìm thấy, DỪNG hỏi user và ghi vào `.bmm-config.yaml`.
* Resolve các nguồn bổ trợ:
  * `ui_schema_root`: Cấu hình `ntapp-qa-robot.ui_schema_root` hoặc `{stage_4_design}/ui_schema`. Nếu thiếu -> DỪNG hỏi user.
  * `detailed_design_root`: Cấu hình `ntapp-qa-robot.detailed_design_root` hoặc `{stage_4_design}/detailed_design`. Nếu thiếu -> Bỏ qua, nêu trong báo cáo (KHÔNG dừng). Lane SLICE dùng DD của từng unit, không dùng DD cấp slice.

### Biến runtime
| Biến | Nguồn | Ghi chú |
|---|---|---|
| `project_name` | Layer 1/2/3 | Tên dự án |
| `qa_artifacts` | Layer 1/2/3 | Gốc chứa manual testcase/fixtures (spec repo) |
| `code_repo_root` | Bước 0b | Nơi ghi robot code (R6). Mọi path test/resource relative theo biến này |
| `planning_artifacts` | Layer 1/2 | Thư mục chứa `project_wbs.md` |
| `stage_4_design` | Layer 1 | Thư mục thiết kế |
| `detailed_design_root` | Layer 2 → Layer 1 | DD per-unit, tham chiếu bổ trợ |
| `ui_schema_root` | Layer 2 → Layer 1 | Thư mục chứa `ui_schema_{id}.json` |
| `gen_run_id` | Step 01 | Định danh lượt chạy skill, lưu vào manifest và báo cáo review |
| `manual_testcase_path` | Step 01 | Đường dẫn tuyệt đối đến file manual testcase `.md` |
| `excluded_ids[]` | Step 01 | Mã case có `@target` khác `robot`, loại khỏi scope check R3 |
| `id` | User input | ID đầy đủ của SLICE/unit cần xử lý |
| `surface_type` | Step 01 | Tập hợp bề mặt: `ui` (Selenium POM), `service` (RequestsLibrary POM) |
| `locator_source` | Step 01 | *(chỉ `ui`)* Nguồn locator: `source` (code FE tĩnh) \| `live-dom` (phiên soi DOM ở Step 02) |
| `run_id` | Step 05 | Định danh lượt chạy test thật, truyền qua `--variable RUN_ID:` |
| `review_gate` | Layer 2 | Cổng HITL đầu Step 04: `ask` (default — DỪNG hỏi user có chạy review không) \| `auto` (dispatch thẳng, không hỏi) \| `skip` (bỏ review, sang Step 05) |
| `review_escalation` | Layer 2 | Hành vi khi review vòng 3 vẫn FAIL: `interactive` (default) \| `ci` |
| `deferred_run_policy` | Layer 2 | Hành vi R10: `ask` (default) \| `run-all` \| `defer-all` |
| `agent_personas_path` | Hardcode | Đường dẫn chứa Agent personas (`./agents/`) |
| `date` | System | Thời gian chạy (ISO 8601) |

## Output Naming
Tên path cố định, không dual-write, không archive. Ghi relative tại `{code_repo_root}` (R6).

* **Bề mặt `ui` (Selenium POM):**
  * Page Objects: `actions/pageObject/{Page}/{Page}Variables.resource` & `*Keywords.resource`
  * Test Suite: `tests/[Screen]Test.robot` (1 file/màn, PascalCase theo tên màn, cấm nhét ID slice/unit).
  * Suite Fixtures: `actions/common/SuiteFixtures.resource`.
  * Data: `datatest/`
* **Bề mặt `service` (RequestsLibrary POM):**
  * Tương tự UI, thay `pageObject` thành `serviceObject`, suite `tests/[Operation]Test.robot` chia theo `@svc`.

---

## PIPELINE MAP

| # | Step | Agent | Output | Gate chính |
|---|---|---|---|---|
| 01 | [step-01-parse.md](steps/step-01-parse.md) | Generator | `datatest/{id}_gen_manifest.yaml`, `{id}_dynamic_fixtures.json` | Khớp code repo (R6), đọc input (R5), hoãn case (R10) |
| 02 | [step-02-gen-resources.md](steps/step-02-generate-resources.md) | Generator | Resource files (`.resource`) | Locator/Contract valid (R7/R7s), seed đầy đủ (R15) |
| 03 | [step-03-gen-suite.md](steps/step-03-generate-suite.md) | Generator | `tests/[Screen]Test.robot`, `datatest/{id}_gen_manifest.yaml` | 6 cổng cơ học: parity mã (R3), nhãn (R3), POM purity (R4), no Sleep/Go To (R9/R12), dryrun sạch, manifest tồn tại (R16) → **cổng HITL `review_gate`** |
| 04 | [step-04-review-code.md](steps/step-04-review-code.md) | Reviewer | `results/{id}_robot_review.md` | 6 Lõi (tĩnh), review phần thay đổi (R16) |
| 05 | [step-05-execute.md](steps/step-05-execute-and-analyze-logs.md) | Generator | Chạy test, self-healing, log merge | Phân loại 5 bucket, self-heal ≤3 retry (R7), log data mồi (R15) |

## GLOBAL RULES
- **Iron Rules:** Tuân thủ [principles/iron_rules.md](./principles/iron_rules.md).
- **Launcher:** In ra chat `{qa_artifacts}` (đọc) ↔ `{code_repo_root}` (ghi). Đọc file input R5 và chốt R6 trước khi chạy.

**Next:** Đọc và thực hiện theo `./steps/step-01-parse.md`
