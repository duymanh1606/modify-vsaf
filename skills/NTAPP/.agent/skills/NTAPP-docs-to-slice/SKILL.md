---
name: ntapp-docs-to-slice
description: 'Một lệnh từ trạng thái bất kỳ tới slice plan: TỰ PHÁT HIỆN dự án đã có tài liệu hay chưa. Chưa có → tạo tài liệu (grill → PRD → Epics → UX sketch → HLD/Module 0/WBS) → review → duyệt → chia slice. Có tài liệu thô (BRD/SRS/PRD khách gửi) → dùng làm nguồn rồi tạo phần thiếu. Đã có tài liệu chuẩn → bỏ qua tạo, review → duyệt → chia slice. Có code repo → đọc code sinh tài liệu qua /NTAPP-brownfield (cũng review rồi chia slice). Tự chạy tiếp từ bước dở; dừng ở điểm duyệt. Sử dụng khi người dùng nói "tạo/review tài liệu rồi chia slice", "chạy từ đầu tới slice", "đóng gói tất cả", "greenfield".'
---

# NTAPP Docs → Slice — tự phát hiện tài liệu, tạo phần thiếu, review, chia slice

Orchestrator mỏng: KHÔNG tự viết PRD/Epics/WBS/slice/review, chỉ gọi đúng skill theo đúng thứ tự (mirror `create_prd_epics.yaml` + Track B trong `CLAUDE.md`). Idempotent — mỗi lần chạy đọc state rồi làm bước kế tiếp.

Đối số (`$ARGUMENTS`, tuỳ chọn): mô tả ý tưởng sản phẩm, và/hoặc đường dẫn tới tài liệu nguồn (BRD/SRS/PRD .md/.pdf/.docx).

Đường dẫn: `OUT = NTAPP-output`, `S1 = OUT/Stage_1_Discovery`, `S2 = OUT/Stage_2_Architecture`.

Hash nội dung (bỏ front-matter — để việc ký `approved_by` KHÔNG làm review bị coi là cũ):
```bash
body_sha() { awk 'NR==1&&/^---$/{f=1;next} f&&/^---$/{f=0;next} !f' "$1" | sha256sum | cut -c1-12; }
```

## Bước 0 — Preflight

1. Phải đứng ở spec repo (có `NTAPP-output/` và `CLAUDE.md`).
2. Skill cần gọi được: `grill-with-docs` (hoặc `grill-me`), `bmad-create-prd`, `bmad-create-epics-and-stories`, `NTAPP-ux-sketch`, `bmad-validate-prd`, `bmad-review-adversarial-general`, `NTAPP-architecture-design`, `bmad-check-implementation-readiness`, `NTAPP-slice-planning`. Thiếu → **DỪNG**, hướng dẫn `! vsaf sync NTAPP --skills-only` rồi mở lại `claude`.

## Bước 1 — Phát hiện tài liệu

Quét và phân loại, rồi in **bảng phát hiện** cho người dùng:

| Nhóm | Dấu hiệu |
|---|---|
| **Code** | thư mục cùng cấp spec repo có `package.json` / `pom.xml` / `build.gradle` / `go.mod` / `pyproject.toml` / `*.csproj` … |
| **Chuẩn NTAPP** | `S1/CONTEXT.md`, `S1/prd.md`, `S1/epics.md`, `S1/ux_sketch.md`, `S2/project_wbs.md`, `S2/architecture_design.md`, `S2/00_system_connectivity_integration.md`, `S2/slices/SLICE-*.md` — kèm trạng thái ký (`approved_by`) |
| **Tài liệu thô** | đường dẫn trong `$ARGUMENTS`; file `.md/.pdf/.docx/.txt` trong `S1/` (gồm `S1/inputs/`, `S1/brainstorms/`) KHÔNG thuộc nhóm chuẩn, KHÔNG nằm trong `reviews/`, `adr/`, `system_overview/`, `Bugs_Issues/`, `triage/` |

Bỏ qua `.gitkeep` và `CONTEXT.md` ở root repo (template). Tài liệu thô có tên mơ hồ → hỏi người dùng MỘT lần để xác nhận loại (BRD / PRD / SRS / user story / khác).

**Chọn chế độ:**

| Phát hiện | Chế độ |
|---|---|
| Có **Code** | **TỪ CODE** — báo chế độ rồi gọi `Skill("NTAPP-brownfield", "$ARGUMENTS")` và để skill đó điều phối toàn bộ (đọc code → sinh tài liệu → review đối chiếu code → duyệt → chia slice). KHÔNG chạy tiếp bảng A–J bên dưới. Chỉ khi người dùng nói rõ muốn bỏ qua code (dự án mới viết lại từ đầu) mới đi tiếp greenfield. |
| Không có gì | **TẠO MỚI** — bắt đầu từ A |
| Chỉ có tài liệu thô | **TỪ NGUỒN** — A dùng tài liệu thô làm nguồn |
| Có tài liệu chuẩn | **REVIEW** — bỏ qua bước tạo đã có, chỉ tạo phần còn thiếu |

Rồi chọn bước ĐẦU TIÊN chưa xong theo bảng dưới.

| # | Pha | Bước | Xong khi |
|---|---|---|---|
| A | Tạo | Làm rõ yêu cầu | có `S1/CONTEXT.md`, HOẶC đã có `S1/prd.md` |
| B | Tạo | PRD | có `S1/prd.md` |
| C | Tạo | Epics + Stories | có `S1/epics.md` |
| D | Tạo | UX sketch | có `S1/ux_sketch.md`, hoặc skill đã báo SKIP, hoặc đã có `S2/project_wbs.md` |
| E | Review | Review Stage 1 | `S1/reviews/stage1_review.md` có `reviewed:` khớp `body_sha` hiện tại của `prd.md` + `epics.md` |
| F | Duyệt | Duyệt Stage 1 | `prd.md` + `epics.md` có `approved_by` + `approved_at` VÀ review E không còn 🔴 `open` (hoặc đã ký `approved_with_open`) |
| G | Tạo | Kiến trúc | có `S2/project_wbs.md` |
| H | Review | Review Stage 2 | `S2/reviews/stage2_review.md` có `reviewed:` khớp `body_sha` của `project_wbs.md` (+ HLD, Module 0 nếu có) |
| I | Duyệt | Duyệt Stage 2 | như F, cho `project_wbs.md` (+ HLD, Module 0 nếu có) |
| J | Chia | Slice plan | có `S2/slices/SLICE-*.md` mới hơn lần duyệt I |

Đã có slice từ trước và WBS không đổi → báo đã xong, hỏi có muốn chia lại không (chia lại = gọi lại J; skill tự archive bản cũ).

## Bước 2 — Thực thi

Mỗi bước gọi qua `Skill(...)` — bắt buộc, KHÔNG thay bằng tự viết. Skill con hiện menu → chuyển nguyên cho người dùng, KHÔNG tự chọn. Xong một bước → cập nhật bảng, sang bước kế; chỉ dừng ở F, I hoặc khi cần người trả lời.

### Pha tạo (chỉ chạy bước còn thiếu)
- **A. Làm rõ** — `Skill("grill-with-docs")` (fallback `grill-me`). Output theo CLAUDE.md §Override path: `S1/CONTEXT.md`, ADR `S1/adr/NNNN-slug.md`.
  - TẠO MỚI: grill từ ý tưởng trong `$ARGUMENTS` (chưa có → hỏi một câu mô tả sản phẩm).
  - TỪ NGUỒN: đọc tài liệu thô trước (`.pdf` đọc trực tiếp; `.docx` chuyển qua skill docx/pandoc), grill CHỈ những chỗ mơ hồ / mâu thuẫn / thiếu — không hỏi lại điều tài liệu đã nói rõ.
  - Nhiều chức năng → grill TỪNG user story một. Kết thúc khi người dùng nói đủ.
- **B. PRD** — `Skill("bmad-create-prd")`, nguồn: `S1/CONTEXT.md` + `S1/adr/` + tài liệu thô (nếu có). Output `S1/prd.md`.
- **C. Epics** — `Skill("bmad-create-epics-and-stories")`, input `S1/prd.md`. Output `S1/epics.md`.
- **D. UX sketch** — `Skill("NTAPP-ux-sketch")`; SKIP là kết quả hợp lệ.
- **G. Kiến trúc** — `Skill("NTAPP-architecture-design")` mode FULL. Output HLD + Module 0 + `S2/project_wbs.md`.

### Review (E, H)
- **E** — (1) `Skill("bmad-validate-prd")` trên `prd.md`; (2) `Skill("bmad-review-adversarial-general")` trên `epics.md` đối chiếu `prd.md` + `CONTEXT.md` + tài liệu thô: FR/NFR nào chưa có story; story không truy về PRD; thuật ngữ lệch glossary; story quá to / thiếu actor-giá trị; điểm PRD mâu thuẫn tài liệu thô.
- **H** — (1) `Skill("bmad-check-implementation-readiness")`; (2) `Skill("bmad-review-adversarial-general")` trên `project_wbs.md` + Module 0: US nào trong `epics.md` chưa map unit; unit không truy về story; `consumes`/`used_by` hai chiều lệch; contract External thiếu ownership; ID sai prefix (`SCR-*`/`WGT-*` cho UI).
- Gộp vào `S1/reviews/stage1_review.md` / `S2/reviews/stage2_review.md`:
  ```markdown
  ---
  reviewed: { prd.md: <body_sha>, epics.md: <body_sha> }   # H: project_wbs.md, architecture_design.md, ...
  reviewed_at: <ISO-8601 UTC>
  ---
  | ID | Mức 🔴/🟡/⚪ | File | Vấn đề | Đề xuất sửa | Trạng thái |
  ```
  Review lại sau khi sửa → giữ dòng cũ (đổi trạng thái), thêm finding mới với ID kế tiếp.

### Duyệt (F, I — DỪNG nếu cần)
- Tài liệu **đã ký từ trước** và review KHÔNG có 🔴 `open` → giữ chữ ký, báo ngắn rồi chạy tiếp, không dừng.
- Ngược lại → in số finding theo mức + danh sách 🔴, chờ người dùng gõ:
  - **"sửa F1,F3"** → sửa đúng finding đó (PRD: `Skill("bmad-edit-prd")`; Epics: chạy lại `bmad-create-epics-and-stories`; WBS: `Skill("NTAPP-architecture-design", "--append")`, chạm contract Module 0 → hỏi trước khi chạy FULL). Sửa xong → đánh `fixed`, quay lại E/H review lại.
  - **"bỏ qua F2 vì …"** → `dismissed` + lý do (không xoá dòng).
  - **"duyệt, tên <X>"** → ghi `approved_by: "<X>"` + `approved_at: <ISO-8601 UTC>` vào front-matter (F: `prd.md`, `epics.md`; I: `project_wbs.md` + `architecture_design.md` + `00_system_connectivity_integration.md` nếu tồn tại). Còn 🔴 `open` → nhắc 1 lần; vẫn duyệt thì thêm `approved_with_open: [IDs]`. Rồi chạy tiếp.
  - Sửa nội dung một tài liệu đã ký → chữ ký cũ không còn giá trị: xoá `approved_by`/`approved_at` của file đó, phải duyệt lại.

### Chia slice (J)
`Skill("NTAPP-slice-planning")`. In bảng slice (ID · tên · AFK/HITL · units · blocked_by) + drift finding nếu có; nhắc slice plan cần SeniorDev + SA duyệt trước `/NTAPP-vsaf-slice-loop <slice_id>`.

## Quy tắc

- Chỉ ghi `approved_by` khi người dùng nói rõ "duyệt" kèm tên. Không có tên → hỏi.
- Review KHÔNG tự sửa tài liệu; tài liệu thô của khách KHÔNG bao giờ bị sửa.
- Hook BLOCK → báo lý do, KHÔNG lách bằng biến môi trường.
- Skill con fail → dừng ở bước đó, báo lỗi nguyên văn; lần chạy sau retry đúng bước này.
- Cuối mỗi lượt: in chế độ đã chọn + bảng state A–J (✅ / ⏸ chờ duyệt / ⏭ skip / ⬜) + câu người dùng cần gõ tiếp.
