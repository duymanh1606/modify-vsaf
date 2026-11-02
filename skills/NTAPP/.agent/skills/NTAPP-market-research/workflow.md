# Market Research Analysis Workflow

**Goal:** Thực hiện nghiên cứu thị trường, chiến lược đối thủ và phân tích tính năng chuyên sâu thông qua
chuỗi 5 Agent chuyên biệt để tạo ra một bản trình bày chuẩn C-Level.

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (bản đồ + cổng + rule). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi PAUSE) RỒI mới đọc step kế.
  KHÔNG đọc trước nhiều step. State chuyển tiếp qua temp file, không qua việc giữ instruction trong context.

---

## INITIALIZATION

### Configuration Loading
Load config from `{project-root}/_bmad/config.yaml` and resolve:
- `project_name`, `output_folder`, `planning_artifacts`, `user_name`
- `communication_language`, `document_output_language`, `user_skill_level`
- `date` as system-generated current datetime

### Paths
- `scout_data`         = `{planning_artifacts}/temp/scout-jtbd-competitors.md`
- `raw_market_data`    = `{planning_artifacts}/temp/raw-market-landscape.md`
- `raw_strategy_data`  = `{planning_artifacts}/temp/raw-product-strategy.md`
- `raw_feature_data`   = `{planning_artifacts}/temp/raw-feature-matrix.md`
- `final_output_file`  = `{planning_artifacts}/master-market-research.md`
- `archive_output_file`= `{planning_artifacts}/archive/{project_name}-master-market-research-{date}.md`

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

| # | Step file | Agent | Output |
|---|---|---|---|
| 0 | steps/step-00-scout-jtbd.md          | scout_agent        | scout_data |
| 1 | steps/step-01-market-research.md     | market_researcher  | raw_market_data |
| 2 | steps/step-02-product-strategy.md    | product_strategist | raw_strategy_data |
| 3 | steps/step-03-feature-analysis.md    | feature_analyst    | raw_feature_data |
| 4 | steps/step-04-chief-editor-synthesis.md | chief_editor    | final_output_file + archive_output_file |

Chuỗi: **0 → [GATE chọn target] → 1 → 2 → 3 → 4**.
Hai cổng người-dùng: **trước step-0** (intake) và **sau step-0** (chọn 3–5 target).

---

## GLOBAL RULES (bất biến — áp dụng mọi step)

- ✅ YOU MUST ALWAYS SPEAK OUTPUT in your Agent communication style với `{communication_language}`.
- ✅ YOU MUST ALWAYS WRITE all artifact and document content bằng `{document_output_language}`.
- ✅ **NO HALLUCINATION TIER 1:** Chief Editor tuyệt đối KHÔNG thêm nếm số liệu kinh doanh ngoài 3 file raw.
- ⛔ Đọc đúng một step file mỗi lần; chỉ đọc step kế khi step hiện tại xong + qua cổng user (nếu có).

---

## LAUNCH — [GATE 1: INTAKE] (bắt buộc dừng)

In chính xác lời chào:
> "Chào mừng bạn đến với module Market Research! Hãy nhập Chủ đề, Sản phẩm và Khu vực địa lý bạn muốn
> nghiên cứu (Ví dụ: Khu vui chơi trẻ em tại Hà Nội, hoặc App quản lý tài chính GenZ tại VN)."
> 👉 **[PAUSE & WAIT FOR USER INPUT]**

Sau khi user trả lời → gán input vào `{Research_Topic}` →
**Next:** Read fully and follow `./steps/step-00-scout-jtbd.md`
