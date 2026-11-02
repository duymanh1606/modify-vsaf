# Product Research Workflow (Problem-Solution Fit)

**Goal:** Thực hiện nghiên cứu Problem-Solution Fit qua chuỗi Agent (User Researcher → Product Manager
→ Chief Editor) để tạo Customer Pain Points Report (Personas, Customer Journey, Pain Matrix,
Prioritization P0/P1/P2).

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (bản đồ + cổng + rule). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi PAUSE) RỒI mới đọc step kế.
  KHÔNG đọc trước nhiều step. State chuyển tiếp qua temp file, không qua việc giữ instruction trong context.

---

## INITIALIZATION
Load config từ `{project-root}/_bmad/config.yaml`.

### Paths
- `market_data_input` = `{planning_artifacts}/master-market-research.md`
- `raw_personas` = `{planning_artifacts}/temp/pr-personas.md`
- `raw_journey` = `{planning_artifacts}/temp/pr-journey.md`
- `raw_pain_matrix` = `{planning_artifacts}/temp/pr-pain-matrix.md`
- `raw_prioritization` = `{planning_artifacts}/temp/pr-prioritization.md`
- `final_report` = `{planning_artifacts}/{project_name}-customer-pain-points-report.md`
- `archive_report` = `{planning_artifacts}/archive/{project_name}-pr-report-{date}.md`

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

| # | Step file | Role | Output |
|---|---|---|---|
| 1 | steps/step-01-init.md           | pr_chief_editor | (đọc market_data_input + chọn focus) |
| 2 | steps/step-02-segmentation.md   | user_researcher | raw_personas |
| 3 | steps/step-03-journey.md        | user_researcher | raw_journey |
| 4 | steps/step-04-pain-matrix.md    | user_researcher | raw_pain_matrix |
| 5 | steps/step-05-prioritization.md | product_manager | raw_prioritization |
| 6 | steps/step-06-synthesis.md      | pr_chief_editor | final_report + archive_report |

Chuỗi: **1 → [GATE chọn focus] → 2 → [GATE chờ lệnh] → 3 → [GATE chờ lệnh] → 4 → 5 → 6**.

---

## GLOBAL RULES (bất biến — áp dụng mọi step)

- ⛔ Đọc đúng một step file mỗi lần; chỉ đọc step kế khi step hiện tại xong + qua cổng user (nếu có).
- ✅ **NO HALLUCINATION:** KHÔNG BAO GIỜ tự bịa dữ liệu — mọi nhận định về tệp khách hàng / hành vi /
  nỗi đau phải Verify bằng Web Search (trừ step tổng hợp chỉ gộp nguyên văn từ file raw).
- ✅ Ghi ngay kết quả vào file đích sau khi hoàn tất phân tích của mỗi step.

---

## LAUNCH

Khởi động luồng Product Research từ bước Context Ingestion (pr_chief_editor đọc Market Research làm bối cảnh).
**Next:** Read fully and follow `./steps/step-01-init.md`
