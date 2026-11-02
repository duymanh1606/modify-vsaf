# STEP 01: INPUT DISCOVERY & SCAFFOLD

> **Thực hiện bởi:** Agent UXS0 (UX Sketch Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R3, R7, R9**.

## 1. Mục tiêu

Thu thập PRD + Epics, xác nhận phạm vi, khởi tạo tài liệu Master Sketch + parts dir + briefing cho UXS1.

## 2. Chỉ thị thực thi

### 2.1. Pre-flight Input Audit (R7 + R9)

**Path resolution:** Trước khi search, load config cascade (workflow.md §5.1) để resolve `{stage_1_discovery}`, `{planning_artifacts}`, `{project_knowledge}`.

Tìm và verify:

| Tài liệu | Bắt buộc? | Đường dẫn | Action khi miss |
|:--|:--|:--|:--|
| **PRD** | ✅ Required | `{stage_1_discovery}/prd*.md` | DỪNG (R7 #1) |
| **Epics/Stories** | ✅ Required | `{stage_1_discovery}/epics*.md` | DỪNG (R7 #1) |
| **Project knowledge** | Recommended | `{project_knowledge}/` | WARN — sketch §3 thiếu integration points |

**Validate format:**
- PRD có actors phân biệt rõ (không chỉ "user" generic)? Nếu không → R7 #2, escalate PM/BA refine.
- Epics có user story format ("As a X, I want Y, so that Z")? Nếu không → R7 #3, escalate BA refine.

### 2.1b. Pre-resolve preview design source (cho Step 05)

Preview hi-fi ở [step-05](./step-05-validation.md) §3.1b cần biết skin bằng gì — resolve NGAY ở đây để báo user cùng lúc xác nhận phạm vi, không để phát hiện thiếu DS giữa gate:

1. Đọc `sketch_preview` (default `lavish` = hi-fi) + `sketch_preview_theme` (default `corporate`) từ `.bmm-config.yaml` block `ntapp-ux-sketch:`. Value `off` → bỏ qua mục này.
2. Resolve DS root theo `{design_system_root}/_shared/ds-resolution.md` **nhánh F** (cosmetic, read-only, KHÔNG BAO GIỜ STOP) → check `{ds_root}/master_token.json` + `{ds_root}/_reference/` có tồn tại.
3. Ghi lại kết quả (dùng ở §2.2 mục 6): `master_token.json` có → *"preview skin bằng Master DS `{ds_id}`"*; không có → *"preview dùng theme placeholder `{sketch_preview_theme}` — chạy `/ntapp-ds-bootstrap` (Stage 0) trước nếu muốn preview mang đúng identity product"*.

### 2.2. Xác nhận phạm vi với User

Trình bày:
1. **Tài liệu tìm được:** Liệt kê file + tóm tắt 1 dòng.
2. **Anchor system:** Hệ thống chính (từ PRD).
3. **Existing systems** (nếu brownfield): list từ project knowledge / PRD.
4. **Vai trò người dùng:** Danh sách sơ bộ từ PRD.
5. **Primary user goals:** Top 3 từ PRD.
6. **Preview design source** (kết quả §2.1b): fidelity đang dùng (`hi-fi` / `lofi` / `off`) + skin lấy từ đâu.

**CHỜ USER XÁC NHẬN** trước khi tiếp tục.

### 2.3. Khởi tạo Master Sketch

1. Đọc template: `../templates/ux-sketch-template.md`
2. Điền các biến cơ bản:
   - `{{project_name}}`, `{{anchor_system}}`, `{{date}}`, `{{user_name}}`
3. Lưu file Master tại: `{planning_artifacts}/ux_sketch.md`
4. Tạo thư mục parts: `{planning_artifacts}/ux_sketch_parts/` (= `{intermediate_folder}`)
5. Cập nhật frontmatter:
   ```yaml
   stepsCompleted: [step-01-init]
   inputDocuments: [path/to/prd.md, path/to/epics.md]
   ```

### 2.4. Draft §1 Executive Brief

UXS0 tự viết §1 Executive Brief (3-5 câu) trực tiếp vào Master scaffold:
- Anchor system
- Top 3 primary user goals (từ PRD)
- Business outcomes expected (1 đoạn)

Trace mỗi goal về PRD §X.

### 2.5. Briefing cho UXS1

Tạo bản tóm tắt ngắn truyền cho UXS1 ở Step 02:
- Tên dự án + anchor system
- Danh sách actors từ PRD §X
- Top pain points đã hint trong PRD problem statement
- Đường dẫn PRD + Epics

## 3. Đầu ra yêu cầu

- [ ] PRD + Epics đã verify exist + có cấu trúc đúng (R7 pass)
- [ ] Preview design source đã resolve (§2.1b) — `sketch_preview` + DS root / theme placeholder
- [ ] Master Sketch khởi tạo (header + change log + frontmatter + §1 Executive Brief draft)
- [ ] `ux_sketch_parts/` đã tạo
- [ ] Briefing cho UXS1 chuẩn bị xong
- [ ] User xác nhận phạm vi

## NEXT
[step-02-rough-personas.md](./step-02-rough-personas.md)
