# STEP 02: EXECUTIVE SUMMARY (§1 — slim)

> **Thực hiện bởi:** Agent UX2 (PM Liaison — John)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R3, R4, R10**.

## 1. Mục tiêu

Thiết lập bối cảnh + mục tiêu đo được cho Journey Spec — NGẮN (chi tiết nằm trong PRD, cite thay vì chép lại). Kèm persona references (actor lock: HLD §3.1.1 — bắt buộc; nguồn chi tiết: `ux_sketch.md` nếu có / PRD §User Stories nếu không).

## 2. Đầu vào cần đọc

- PRD: Background, Vision, Success Criteria, User Journeys
- Briefing từ Step 01 (locked actor list, sketch status)
- `ux_sketch.md` §Personas (nếu có)

## 3. Chỉ thị thực thi

### 3.1. §1.1 Context & Vision

- ≤2 đoạn: hệ thống/quy trình hiện tại + pain chính (quantified nếu PRD có số — không bịa số) + 1 câu UX vision (metaphor dễ nhớ).
- KHÔNG lập bảng hiện trạng dài — cite PRD section thay vì chép.

### 3.2. §1.2 Design Goals

Bảng `| Mục tiêu | Đo lường |` — tối thiểu 3, mỗi measurement có CON SỐ, truy ngược PRD success criteria.

### 3.3. §1.3 Personas (reference — KHÔNG viết lại persona table)

- 1 dòng/role: `{Persona name} — {role}: {mục tiêu chính}` → pointer `ux_sketch.md §Personas` (có sketch) hoặc `PRD §User Stories` (không sketch).
- Chỉ liệt kê actor CÓ trong HLD §3.1.1 lock (R10). Actor PRD nhắc mà HLD không có → escalate R7 #4, không tự thêm.

## 4. Đầu ra yêu cầu

- **Lưu trữ:** `{intermediate_folder}/ux2_executive_summary_part.md`
- Nội dung: §1.1 + §1.2 + §1.3 theo template v4.0.
- Báo cáo: "§1 hoàn tất. {X} goals đo được, {Y} personas referenced (actor lock HLD OK)."

**Next:** Read fully and follow `./step-04-ux-principles.md` *(step-03 personas đã retired — §1.3 chỉ reference: actor lock HLD §3.1.1, chi tiết ux-sketch nếu có / PRD nếu không)*
