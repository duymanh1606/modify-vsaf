# IRON RULES — Quy tắc bất biến của workflow NTAPP UX Sketch (Stage 1 sub-step)

> File này là **nguồn sự thật duy nhất** cho các nguyên tắc bất biến của workflow UX Sketch.
> Đây là **subset relaxed** của iron_rules cho `/ntapp-ux-design` (Stage 3b) — vì sketch chạy trước khi có HLD/Module 0/Master DS, không thể enforce những lock đó.
> Mọi step file PHẢI tham chiếu file này thay vì tự lặp lại nội dung.

---

## R1. VERBATIM INJECTION (Bơm dữ liệu nguyên văn)

Khi hợp nhất `uxs*_part.md` thành tài liệu Master Sketch (Step 06), **TUYỆT ĐỐI KHÔNG** thực hiện thao tác "Merge" truyền thống bằng cách đọc toàn bộ và viết lại bản tóm tắt.

**Tuân thủ:** Bơm dữ liệu thô từ các Part đơn lẻ vào các vị trí giữ chỗ trong Template `ux-sketch-template.md`.

---

## R2. ZERO-SUMMARIZATION (Cấm tóm tắt) — RELAXED cho screen intent

Mọi Screen Intent Table, Mermaid Diagram, bảng (Persona, IA tree) từ part file **PHẢI được giữ nguyên 100%** dung lượng khi đi vào Master Sketch.

**Screen Fidelity sub-clause — RELAXED so với full ux-design:**
- Bố cục diễn đạt bằng **Screen Intent Table** (Screen / Role / Content blocks / Primary CTA / Branch / Trace) — KHÔNG vẽ ASCII wireframe, KHÔNG cần layout grid chính xác.
- Nội dung KHÔNG bắt buộc phải là content thực — placeholder OK miễn đại diện đúng kiểu data của nghiệp vụ.
- KHÔNG cần component mapping (Stage 4b own quyền chốt component/token).
- Vẫn cần đủ: screen identifier + content blocks + CTA + branch + trace.

**Preview Fidelity sub-clause:** preview HTML ở Step 05 render **hi-fi** (skin bằng token Master DS nếu đã bootstrap) để reviewer annotate chính xác. Hi-fi là fidelity của **bản render**, KHÔNG phải commitment về design: preview không phải SSoT, không phải visual đã DS-approve, và không sinh/không sửa token. `ux_sketch.md` + parts vẫn canonical — feedback sửa vào part rồi re-render, KHÔNG sửa tay HTML.

**Vi phạm điển hình:** Cắt ngắn persona table; gộp 2 screen thành 1 row; bỏ Mermaid diagram khi assemble; sửa trực tiếp preview HTML rồi để part file lệch.

---

## R3. ZERO-FABRICATION / ZERO-HALLUCINATION (Cấm bịa)

Chỉ sử dụng thông tin từ các nguồn đã xác nhận. Sketch CHỈ có 1 nguồn primary:

| Nguồn | Path | UX Sketch dùng cho |
|:--|:--|:--|
| **PRD/Epics** (primary) | `{stage_1_discovery}/prd*.md` + `epics*.md` | Toàn bộ — actors, FR/BR, user stories |
| **Project domain docs** (optional) | `{project_knowledge}/` | Bối cảnh brownfield — existing systems để integrate, terminology |

**KHÔNG có HLD/Module 0/Master DS để reference** ở Stage này — đó là lý do sketch là "rough", không phải full spec.

Khi thiếu thông tin (vd persona pain point chưa rõ trong PRD) → đánh dấu `[TBD - cần PM/BA confirm]`. **TUYỆT ĐỐI không bịa**.

---

## R4. TRACEABILITY (Traceability cơ bản)

- Mỗi persona §2 phải tương ứng với ≥ 1 actor trong PRD.
- Mỗi journey step §4 phải reference ≥ 1 Epic ID hoặc Story ID từ Epics document.
- Mỗi Open Question §5 phải gắn với 1 ambiguity cụ thể trong PRD/Epics — không câu hỏi chung chung.

**Lưu ý:** Sketch KHÔNG cần PRD→UX closure mapping (§16) như full ux-design — đó là việc của Stage 3b.

---

## R6. QUALITY GATES — RELAXED

| Gate | Sau step | Owner | Hành động khi FAIL |
|---|---|---|---|
| Pre-flight Input Audit | 01 | UXS0 | DỪNG, escalate user xác nhận PRD/Epics tồn tại |
| Validation Gate | 05 | UXS0 + User | Loop back step tương ứng để sửa nếu PM/BA/PO không approve |

KHÔNG có Token↔Wireframe Sync, Component Coverage, Quantitative Audit, PRD→UX Closure như full ux-design — vì sketch không có DS coverage hoặc closure requirement.

---

## R7. STOPPING ERRORS

Dừng pipeline ngay và báo cáo nếu phát hiện:

1. PRD hoặc Epics **không tồn tại** hoặc rỗng → broken inheritance.
2. PRD có actors mơ hồ (chỉ "user" generic, không phân biệt role) → personas §2 không thể derive → cần PM/BA refine PRD trước.
3. Epics không có user story format ("As a X, I want Y, so that Z") → journey §4 không thể derive Epic/Story trace → cần BA refine Epics trước.

---

## R9. MISSING INPUT HANDLING

Nếu input file (PRD, Epics) không tồn tại hoặc không readable:

- DỪNG ngay, **KHÔNG generate placeholder content** thay thế.
- Báo user explicit: "File `X` tại path `Y` không tìm thấy. Vui lòng cung cấp đường dẫn hoặc xác nhận file."
- Chỉ tiếp tục sau khi user confirm file tồn tại + readable.

**Phân biệt Required vs Recommended:**
- **PRD + Epics:** Required. Thiếu → DỪNG.
- **Project knowledge docs:** Recommended cho brownfield. Thiếu → WARN, sketch §3 Rough IA sẽ thiếu integration points với existing systems → đánh dấu rõ "không có domain docs, cần SA reconcile ở Stage 2".

**KHÔNG list HLD/Module 0/Master DS** — vì những file này CHƯA tồn tại ở Stage 1.

---

## R10. INHERITANCE COMPLIANCE — Partial

UX Sketch chỉ kế thừa từ 1 nguồn:

- **PRD/Epics inheritance:** Mọi actor, FR, BR, user story trong PRD/Epics phải có representation trong sketch (persona, journey step, IA item).

KHÔNG có HLD/Module 0/Master DS upstream để inherit ở Stage này.

**Vi phạm điển hình:**
- §2 Personas có "Approver" nhưng PRD chỉ có "Operator" — bịa actor → SAI.
- §4 Journey có step không trace về Epic/Story nào → SAI.
- §3 Rough IA có module "Reporting" nhưng PRD không nhắc reporting → SAI.

---

## Note: Quan hệ với `/ntapp-ux-design` Iron Rules (Stage 3b)

Sketch's iron_rules là subset relaxed của full ux-design:

| Rule | Sketch | Full ux-design |
|:--|:--|:--|
| R1 Verbatim | ✓ | ✓ |
| R2 Zero-Sum | ✓ relaxed (Screen Intent Table + preview hi-fi) | ✓ strict wireframe |
| R3 Zero-Fab | ✓ (PRD only) | ✓ (PRD + HLD + Module 0 + Master DS) |
| R4 Traceability | ✓ basic | ✓ full §16 closure |
| R5 Consistency | ✗ | ✓ token/component naming |
| R6 Quality Gates | ✓ 2 gates | ✓ 6 gates |
| R7 Stopping | ✓ 3 errors | ✓ 7 errors |
| R8 Contract Lock | ✗ | ✓ HLD + Module 0 §7 + Master DS |
| R9 Missing Input | ✓ | ✓ |
| R10 Inheritance | ✓ partial (PRD only) | ✓ full (PRD + HLD + Module 0 §7 + Master DS) |

→ Sketch deliberately weaker để chạy được ở Stage 1 khi upstream chưa có. Master UX Spec ở Stage 3b sẽ ENFORCE 10/10 rules — sketch chỉ là seed.
