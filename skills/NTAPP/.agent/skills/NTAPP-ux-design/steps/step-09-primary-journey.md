# STEP 09: PRIMARY USER JOURNEY (§4.1 — Mermaid + Journey Screen Table)

> **Thực hiện bởi:** Agent UX0 (UX Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R2 (Journey Screen Table fidelity — KHÔNG per-screen Screen Spec), R5, R8.4, R10**.

## 1. Mục tiêu

Thiết kế luồng primary role hoàn chỉnh: Mermaid flow + **Journey Screen Table** (1 hàng/screen — intent + key states, KHÔNG spec layout per-screen; đó là việc feature-design Stage 4a).

## 2. Đầu vào cần đọc

- **§2 part** (archetype, composition, state taxonomy, propagation) — quyết định verb set + end states + key states
- §3 part (nav tree — leaf nodes khớp screens) + §1 part (primary persona)
- `project_wbs.md` — SCR-* ID (R8.4)
- `ux_conventions.md` — §C-x refs cho cột Conventions refs
- PRD — primary user story, FR/BR liên quan; HLD §3.2.2 sequence diagrams (reference)

## 3. Chỉ thị thực thi

### 3.1. §4.1 Flow Diagram (Mermaid)

`flowchart TD` cho toàn primary journey. Verb set + end states theo archetype §2.1:

| Archetype | Verb sequence | End states |
|:---|:---|:---|
| MAKER_CHECKER | input → validate → submit → await review | submitted/awaiting-review, draft-saved |
| WIZARD | step → validate → next-step → finalize | completed, abandoned |
| DASHBOARD | view → filter → drill-down → embedded action | action-executed, navigated-away |
| TRANSACTIONAL | input → validate → submit → confirm | success-confirmed, failure |
| CONTENT_MGMT | create → edit → save-draft → publish | published, drafted, archived |
| OTHER | (custom per §2.1) | — |

Rules: decision node diamond; critical/terminal node color = token reference (không hex); cover happy path + major branches; KHÔNG vẽ branch ngoài archetype; recovery path chỉ khi archetype có draft/long-form.

### 3.2. §4.1 Journey Screen Table (R2 canonical — 5 cột, không thêm không bớt)

Mỗi screen/step trong Mermaid → đúng 1 hàng:

```markdown
| Screen (SCR-*) | Purpose (1 dòng) | Key states | Entry ← / Exit → | Conventions refs |
|:---|:---|:---|:---|:---|
| SCR-RECON-LIST | Duyệt danh sách đối soát cần xử lý | Empty / Loading / Error / Loaded | ← nav §3.1; → SCR-RECON-DETAIL | §C3 transition, §C4 evt `recon-assigned` |
```

- `SCR-*` từ WBS (R8.4). `Key states` từ taxonomy §2.3 — ràng buộc tối thiểu Stage 4a PHẢI cover; auto-populated field → ghi `auto-badge từ {source}` vào Key states.
- **Sketch preview link (chỉ khi sketch tồn tại):** screen kế thừa từ frame sketch — tra bảng **Preview Index** cuối §4 `ux_sketch.md` (match theo screen name/purpose; tên 3b thường kế thừa sketch) → append vào CUỐI cell `Purpose`: ` ([sketch]({path}#{screen_slug}))` với path repo-relative resolve từ folder `{ux_sketch_path}` (vd `NTAPP-output/Stage_1_Discovery/ux_sketch/previews/{feature_slug}_ux_sketch_preview.html#compose-message`). Link nằm TRONG cell Purpose — vẫn ĐÚNG 5 cột (R2), KHÔNG thêm cột. Screen không có frame khớp / không có sketch → bỏ qua, không placeholder.
- **CẤM** thêm cột Regions/Components/wireframe (R2 — leo thang về per-screen spec là tái tạo drift đã cắt). Chi tiết màn = DD Stage 4a.
- Step count minimum theo archetype: MAKER_CHECKER/WIZARD/CONTENT_MGMT ≥3; DASHBOARD ≥2; TRANSACTIONAL ≥1+confirm.

### 3.3. Layout self-audit (journey/IA-level — L5/L6/L9, warn-only)

Theo catalog `{design_system_path}/_shared/layout-best-practices.md` (ngưỡng/detection lấy nguyên từ catalog): **L5** progressive disclosure (nhóm advanced/hiếm trên journey), **L6** reading order (primary CTA position trong flow), **L9** IA depth (nesting §3.1). Ghi 1 dòng cuối §4.1: `L5/L6/L9: OK` hoặc warning + đề xuất. KHÔNG audit L1-L4/L7-L8/L10-L11 (owner feature-design).

## 4. Đầu ra yêu cầu

- **Lưu trữ:** `{intermediate_folder}/ux0_journeys_part.md` (phần §4.1)
- Báo cáo: "§4.1 hoàn tất. {X} steps, {Y} screens (WBS OK), {Z} decision points, L5/L6/L9: {OK/warnings}."

**Next:** Read fully and follow `./step-10-secondary-journeys.md`
