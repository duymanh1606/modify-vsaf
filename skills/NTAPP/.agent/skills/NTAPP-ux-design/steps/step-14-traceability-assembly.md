# STEP 14: PRD TRACEABILITY & FINAL ASSEMBLY (§5 + assembly)

> **Pre-requisite:** WBS đã lock (Step 01 Required). Journey screens đã sync WBS (gate sau step-10).

> **Thực hiện bởi:** Agent UX0 (UX Lead — Sally) + Agent UX2 (PM Liaison — John)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R1 (Verbatim Injection — journey spec), R2, R4 (PRD→§5 closure), R6**.

## 1. Mục tiêu

1. §5 PRD → UX mapping (closure check — không requirement nào bỏ sót).
2. Final assembly 5 part files → `ux_design.md` + verify `ux_conventions.md` state.
3. Dual-write archive cả 2 artifact.

## 2. Phân công

| Nội dung | Agent |
|:---|:---|
| §5 PRD→UX Mapping | UX2 |
| Assembly + Quantitative Audit + Archive | UX0 |

## 3. Đầu vào cần đọc

- PRD: TOÀN BỘ FR, BR, NFR (đọc lại từ đầu — không dựa memory)
- 5 part files: ux2_executive_summary, ux3_modular, ux3_ia, ux0_journeys, (file này sinh ux2_traceability)
- `ux_conventions.md` (current state — mapping NFR/BR pattern chung trỏ §C-x)
- `project_wbs.md` (cross-check screens)

## 4. Chỉ thị thực thi

### 4.1. §5 PRD → UX Mapping (UX2) — Closure Check

Extract đầy đủ FR/BR/NFR từ PRD. Mỗi requirement 1 hàng:

| PRD Requirement | UX Solution | Section |
|:---|:---|:---|
| **FR1:** {req} | {solution cụ thể} | §4.1 / §C3 / DD Stage 4a ({SCR-*}) |

**Quy tắc:** KHÔNG hàng trống; solution CỤ THỂ (không "implemented in UI"); Section trỏ chính xác — journey spec §N, conventions §C-x, hoặc "DD Stage 4a ({SCR-*})" cho chi tiết per-screen (hợp lệ từ v4.0 — per-screen là ownership 4a); requirement chưa có solution → 🔴 GAP + báo cáo.

### 4.2. Final Assembly — UX0 (Verbatim Injection R1)

1. Mở scaffold `{planning_artifacts}/ux_design.md` (Step 01).
2. Inject 1:1 từng part vào section đích:

| Order | Part file | Target |
|:---|:---|:---|
| 1 | `ux2_executive_summary_part.md` | §1 |
| 2 | `ux3_modular_part.md` | §2 |
| 3 | `ux3_ia_part.md` | §3 |
| 4 | `ux0_journeys_part.md` | §4 |
| 5 | `ux2_traceability_part.md` | §5 |

3. Xóa GENERATION comments; cập nhật frontmatter `stepsCompleted` + Change Log.
4. `ux_conventions.md` KHÔNG assemble (đã ghi trực tiếp) — chỉ verify CHANGE LOG có row cho mọi section vừa đổi.

### 4.3. Quantitative Audit (R6)

| Hạng mục | Đối soát |
|:---|:---|
| Journey spec sections | = 5 (§1-§5)? Không còn Screen Spec block / §17 / persona table chi tiết? |
| §1.3 personas | Chỉ references + khớp actor HLD §3.1.1? |
| §2.1 archetype | Đúng 1 archetype (không mix)? |
| §2.3 state taxonomy | Cover lifecycle archetype (nếu ≠ SINGLE)? |
| §3.1 nav | Brownfield → chỉ delta? Mỗi leaf mới ↔ WBS `SCR-*`? |
| §4 journeys | Mỗi journey: Mermaid + Journey Screen Table đủ 5 cột? Screen count ≥ min archetype? |
| §4 Key states | Mỗi screen có Key states từ taxonomy §2.3? (4a inherit field này) |
| §4 Conventions refs | Mọi §C-x được trỏ đều tồn tại trong `ux_conventions.md`? (gate Conventions Coverage) |
| L5/L6/L9 self-audit | Mỗi journey có dòng audit? |
| §5 mapping | Rows = tổng FR+BR+NFR? 0 hàng trống? |
| `ux_conventions.md` | C1-C7 đủ (bootstrap) / CHANGE LOG khớp delta (delta mode)? Status labels 1-1 Module 0 §7? |

Mục FAIL → quay lại step tương ứng bổ sung. KHÔNG release khi audit fail.

### 4.4. Dual-Write Archive

1. Auto-detect N: `ls {planning_artifacts}/archive/ux_design_v*.md` (empty → 1; max v3 → 4). `mkdir -p archive`.
2. Journey spec: canonical `ux_design.md` (overwrite) + `archive/ux_design_v{N}.md`.
3. Conventions: CHỈ khi run này có đổi §C-x → `archive/ux_conventions_v{M}.md` (đếm riêng).

## 5. Đầu ra yêu cầu

- Part: `{intermediate_folder}/ux2_traceability_part.md` (§5)
- Canonical: `ux_design.md` (5 sections) + `ux_conventions.md` (C1-C7 state hợp lệ)
- Archive: `archive/ux_design_v{N}.md` (+ `ux_conventions_v{M}.md` nếu delta)
- Audit table (§4.3) + Gap list (nếu có)

## 6. Bàn giao

Trình bày user: (1) paths 2 artifact + archive; (2) tóm tắt 1 đoạn (archetype, journeys, screens, conventions mode); (3) audit table; (4) gap list; (5) next: per-slice loop — `/ntapp-feature-design` per unit (Stage 4a inherit journey Key states + conventions §C-x), `/ntapp-ui-generation` (Stage 4b), stakeholder review.
