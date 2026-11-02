---
name: ntapp-qa-robot
description: 'Từ kịch bản manual testcase đã chốt (bảng 11 cột có `Exec`, hoặc 10 cột khi không có cột đó), tự động sinh mã nguồn kiểm thử Robot Framework chuẩn POM (Page Object Model) rồi chạy test + self-heal. Map chính xác 1-1 mỗi bước manual thành Robot keyword; locator đọc từ source code FE, với ui_schema_{id}.json làm checklist control; cấm Sleep, bắt buộc Smart Wait; FAIL do locator thì retry self-healing ≤3 lần. Hỗ trợ cả bề mặt no-UI (RequestsLibrary Service Object). Output: code repo tests/, actions/pageObject/ (ui) hoặc actions/serviceObject/ (service), datatest/, results/. Sử dụng khi người dùng nói "tạo automation test", "generate robot test", "/generate_robot_test", "viết script automation".'
---

# NTAPP QA Robot Automation Generator

Sinh bộ mã nguồn Robot Framework Automation chuẩn POM từ manual testcase đã chốt, kết hợp tài liệu thiết kế L2/L3 + UI Semantic Schema / Contract Map, rồi tự chạy và self-heal.

> **Hai bề mặt (xác định ở Step 01):**
> - **`ui`** (`Chrome`, `@scr`, có `ui_schema`) → **Selenium POM** (nav-by-click R9, self-heal R7).
> - **`service`** (no-UI: `RequestsLibrary`, `@svc`, không `ui_schema`) → **RequestsLibrary POM** (1 endpoint = 1 Service Object). Cấm `Sleep`, async dùng `Wait Until Keyword Succeeds` (R7s).

> **Input tại `{qa_artifacts}/{id}/`:**
> - `{id}_detailed_test_manual_testcase.md` (Bảng manual bắt buộc): Lọc cột `Exec = automate` (R2).
> - `{id}_testspec.feature` (Gherkin + tag): Canonical khi lệch `.md`. Vắng -> propagate nhãn sẵn có, thiếu ghi `N/A`, cấm bịa (R1).
> - `{id}_fixtures.yaml` (Dữ liệu mồi + prereq): Vắng -> đọc cột "Data Test" ở step 01 bước 6b.

> **Bốn rule quan trọng (chi tiết tại [principles/iron_rules.md](./principles/iron_rules.md)):**
> - **R6**: Đọc tại spec repo, ghi tại `{code_repo_root}` (không mặc định `cwd`).
> - **R10**: Deferred-Run Safety Gate (hoãn chạy nhóm nhạy cảm -> `Pending`).
> - **R11**: Anti-stub (assert đúng kết quả thực tế, cấm test generic).
> - **R16**: Đồng bộ tăng dần từng case khi chạy lại, bảo toàn locator đã self-heal.

Đọc đầy đủ và tuân theo: `./workflow.md`
