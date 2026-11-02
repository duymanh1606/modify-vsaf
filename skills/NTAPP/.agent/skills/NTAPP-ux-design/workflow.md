# WORKFLOW: NTAPP UX DESIGN (Stage 3b — Journey Spec + Project Conventions)

Luồng công việc này điều phối **NTAPP UX Design Squad** (4 agents) để tạo **2 artifact tách vai**:

1. **`ux_design.md` — UX Journey Specification** (per-feature-batch, slim): phần cross-screen KHÔNG stage nào khác own — archetype + information model, IA/navigation delta, journey flows (Mermaid + journey screen table), PRD mapping. **KHÔNG chứa per-screen Screen Spec** (owner duy nhất: `feature-design` Stage 4a), **KHÔNG chứa §17 inventory** (SSoT: `project_wbs.md`), **KHÔNG chứa personas chi tiết** (§1.3 chỉ reference — actor lock HLD §3.1.1; chi tiết `ux_sketch.md` nếu có / PRD §User Stories nếu không).
2. **`ux_conventions.md` — Project UX Conventions** (PROJECT SINGLETON, living doc): principles, content strategy + status labels, interaction patterns, notification matrix, error handling, responsive/a11y, audit-log rules. Viết đủ lần đầu (bootstrap mode), các feature sau chỉ **delta-update**.

Skill chạy ở **Stage 3b** sau slice-planning (Stage 2b), TRƯỚC vòng per-slice — gate applicability ở step-01 §2.0 (SSoT).

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (bản đồ + cổng + rule). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi PAUSE / user-confirm) RỒI mới đọc step kế qua pointer `**Next:**` ở cuối step đó. KHÔNG đọc trước nhiều step. State chuyển tiếp qua part files trong `{intermediate_folder}` (journey spec) hoặc ghi trực tiếp `ux_conventions.md` (conventions — ngoại lệ R1 khai báo trong iron_rules), không qua việc giữ instruction trong context.

---

## INITIALIZATION

### Config resolution (paths)

Skill này tuân theo cùng cascade 3-layer như các NTAPP skill khác (xem chi tiết trong `NTAPP-architecture-design/workflow.md` Step 0):

- **Layer 1** — `{project-root}/_bmad/bmm/config.yaml`: cung cấp default `planning_artifacts`, `stage_1_discovery`, `stage_2_architecture`, `project_knowledge`, `output_folder`, `document_output_language`.
- **Layer 2** — `{project-root}/.bmm-config.yaml` section `ntapp-ux-design:`: override `planning_artifacts` cho UX (mặc định `{project-root}/NTAPP-output/Stage_3_Specs/ux/`).
- **Layer 3** — Interactive fallback nếu cả 2 layer đều miss biến cần.

Biến runtime sau cascade:

| Biến | Nguồn | Dùng cho |
|:---|:---|:---|
| `planning_artifacts` | Layer 1/2/3 | OUTPUT — chứa `ux_design.md` + `ux_conventions.md` + parts + archive (vd: `NTAPP-output/Stage_3_Specs/ux/`) |
| `intermediate_folder` | Derived = `{planning_artifacts}/ux_design_parts/` | OUTPUT — part files của journey spec (flat) |
| `stage_1_discovery` | Layer 1 | INPUT — nơi đọc PRD/Epics (vd: `NTAPP-output/Stage_1_Discovery/`) |
| `stage_2_architecture` | Layer 1 | INPUT — nơi đọc HLD/Module 0 + `project_wbs.md` |
| `design_system_path` | Layer 1 `design_system_root` (thống nhất key với mọi skill khác; fallback legacy `output_folder` + `/design-system/`) hoặc Layer 2 `bmad.design_system_root` | INPUT — **family root**. Multi-DS (`registry.yaml` tồn tại): resolve theo `_shared/ds-resolution.md` **nhánh C** — feature trải screen trên nhiều DS → load `component_catalog.md` của MỌI DS liên quan (resolve từng SCR-*/WGT-* qua **thẻ `repo:` ở Cluster Header WBS** — primary, WBS đã required ở step-01 — rồi `id_prefixes`/`modules`), label vocabulary theo `ds_id` (vd "`DataTable` *(web-admin)*"); screen không resolve được → vocabulary chung + WARN, KHÔNG STOP (catalog là recommended). Legacy: 1 catalog như cũ. Dùng cho `component_catalog.md` (digest — KHÔNG load full metadata), `_reference/` visual notes, `master_token.json` chỉ khi cần verify token path |
| `ux_sketch_path` | Derived = `{stage_1_discovery}/ux_sketch/ux_sketch.md` | INPUT (optional) — personas + rough IA seed |
| `project_knowledge` | Layer 1 | INPUT — domain docs (vd: `docs/`) |

### Paths & Storage

```
{planning_artifacts}/
├── ux_design.md                          (journey spec — canonical, overwrite latest per feature-batch)
├── ux_conventions.md                     (PROJECT SINGLETON — living doc, delta-update, steps ghi trực tiếp)
├── ux_design_parts/                      (intermediate parts của journey spec — flat)
│   ├── ux2_executive_summary_part.md     (Step 02 → §1)
│   ├── ux3_ia_part.md                    (Step 07 → §3)
│   ├── ux3_modular_part.md               (Step 08 → §2)
│   ├── ux0_journeys_part.md              (Step 09-10 → §4)
│   └── ux2_traceability_part.md          (Step 14 → §5)
│
└── archive/
    ├── ux_design_v{N}.md                 (versioned snapshot journey spec)
    └── ux_conventions_v{N}.md            (versioned snapshot conventions — chỉ khi có delta)
```

**Quy tắc:**
- `ux_design.md` (journey spec): assembly từ 5 part files bằng Verbatim Injection (R1) ở Step 14.
- `ux_conventions.md`: steps 04/06/11/12/13 ghi TRỰC TIẾP (atomic write, U-rule) — bootstrap mode fill đủ C1-C7; delta mode chỉ patch section thay đổi + CHANGE LOG row. Đây là ngoại lệ R1 có khai báo.
- `{planning_artifacts}` resolved từ config, KHÔNG hardcode.

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

| Layer | # | Step file | Agent | Target | Output |
|:--|:--|:--|:--|:--|:--|
| A | 01 | steps/step-01-init-discovery.md | UX0 | — | scaffold 2 file + briefing + conventions mode (bootstrap/delta) |
| A | 02 | steps/step-02-executive-summary.md | UX2 | ux_design §1 | ux2_executive_summary_part.md |
| A | 04 | steps/step-04-ux-principles.md | UX0 | ux_conventions §C1 | direct write (skip nếu delta-mode không đổi) |
| A | 06 | steps/step-06-content-strategy.md | UX4 | ux_conventions §C2 | direct write (status labels 1-1 Module 0 §7) |
| B | 07 | steps/step-07-information-architecture.md | UX3 | ux_design §3 | ux3_ia_part.md (IA delta — brownfield chỉ vẽ node mới) |
| B | 08 | steps/step-08-information-hierarchy.md | UX3 | ux_design §2 | ux3_modular_part.md (archetype + info model) |
| C | 09 | steps/step-09-primary-journey.md | UX0 | ux_design §4.1 | ux0_journeys_part.md (Mermaid + journey screen table) |
| C | 10 | steps/step-10-secondary-journeys.md | UX0 | ux_design §4.2-4.3 | append ux0_journeys_part.md |
| D | 11 | steps/step-11-interaction-patterns.md | UX0 | ux_conventions §C3 | direct write |
| D | 12 | steps/step-12-notification-error.md | UX0+UX4 | ux_conventions §C4-C5 | direct write |
| E | 13 | steps/step-13-responsive-accessibility.md | UX0 | ux_conventions §C6-C7 | direct write |
| E | 14 | steps/step-14-traceability-assembly.md | UX0+UX2 | ux_design §5 + assembly | ux2_traceability_part.md + Final Assembly + archive |

Chuỗi: **01 → 02 → 04 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 (TERMINAL)**.
*(Step 03 personas + step 05 design-system đã RETIRED từ v4.0 — §1.3 chỉ reference personas: actor lock HLD §3.1.1 (bắt buộc) + chi tiết ux-sketch (optional) / PRD fallback; DS vocabulary đi qua `component_catalog.md` digest, không cần section riêng.)*

**Delta mode (conventions đã tồn tại):** steps 04/06/11/12/13 chỉ chạy khi feature mới introduce pattern chưa có / thay đổi pattern cũ (check ở đầu mỗi step — không đổi → log "no conventions delta" + đi tiếp). Journey spec (02/07/08/09/10/14) luôn chạy đủ cho feature mới.

Cổng người-dùng: **step-01 §2.0** (Applicability Gate — có thể SKIP toàn skill) + **step-01 §2.4** (xác nhận pre-flight + inheritance) + **step-08** (conditional — xác nhận scope split nếu PRD chứa 2 archetype). step-14 là step cuối → bàn giao.

### Đội ngũ Agent (UX Design Squad)

| Agent | Vai trò | Persona BMAD | Chuyên môn | Steps phụ trách |
|:------|:--------|:-------------|:-----------|:----------------|
| **UX0** | UX Lead & Orchestrator | Sally (bmad-agent-ux-designer) | Journey mapping, interaction design, conventions, final assembly | 01, 04, 09, 10, 11, 13, 14 |
| **UX2** | PM Liaison | John (bmad-agent-pm) | PRD context, goals, traceability audit | 02, 14 |
| **UX3** | IA & System Architect | Winston (bmad-agent-architect) | Information architecture, archetype, module integration | 07, 08 |
| **UX4** | Content Strategist | Paige (bmad-agent-tech-writer) | Microcopy, status labels, notification copy, error messaging | 06, 12 |

*(UX1 Research — Mary — retired cùng step 03: Stage 3b không author personas — §1.3 reference theo actor lock HLD §3.1.1, chi tiết từ ux-sketch nếu có / PRD nếu không.)*

---

## GLOBAL RULES (bất biến — áp dụng mọi step)

### Nguyên tắc Sắt (Iron Rules)

Workflow này tuân thủ 10 quy tắc bất biến (R1–R10) định nghĩa trong [principles/iron_rules.md](./principles/iron_rules.md):

| # | Tóm tắt | Áp dụng chính ở Step |
|:--|:--|:--|
| R1 | Verbatim Injection (journey spec; conventions = ngoại lệ khai báo — direct write) | 14 |
| R2 | Zero-Summarization (kèm Journey Screen Table fidelity) | 14, 09-10 |
| R3 | Zero-Fabrication (PRD + HLD + Module 0 §7 + Master DS + WBS) | toàn bộ |
| R4 | Traceability (PRD → §5) | 14 |
| R5 | Consistency (token / component / status / actor naming) | 04, 06, 09-13 |
| R6 | Quality Gates | 01, 09-10, 14 |
| R7 | Stopping Errors | 01, 14 |
| R8 | Contract Lock (HLD + Module 0 §7 + Master DS + WBS read-only) | 01, 07 |
| R9 | Missing Input Handling | 01 |
| R10 | Inheritance Compliance (PRD / HLD / Module 0 §7 / Master DS / WBS / UX Sketch optional) | 01, 14 |

Khi step file cite "tuân thủ Rx" — đọc iron_rules.md để biết chi tiết, KHÔNG tự suy diễn.

### Quy chuẩn tài liệu

- **Templates:** `./templates/ux-design-spec-template.md` (journey spec v4.0) + `./templates/ux-conventions-template.md` (conventions v1.0)
- **Ngôn ngữ tài liệu:** `{document_output_language}` (từ config)
- **Trọng tâm:**
  - **Đúng vai (Separation):** journey spec = cross-screen intent; per-screen chi tiết là việc Stage 4a. Không spec 2 nơi.
  - **Tính truy ngược (Traceability):** Mọi quyết định UX → PRD requirement (§5) hoặc conventions §C-x.
  - **Tính nhất quán (Consistency):** status label ↔ Module 0 §7; component vocabulary ↔ `component_catalog.md`; screen ID ↔ WBS.

---

## LAUNCH

Bắt đầu pipeline ở Layer A. Step-01 tự canh **Applicability Gate (§2.0)** — nếu feature không thoả gate multi-screen-new thì step-01 sẽ SKIP và DỪNG skill ngay (không sinh artifact).

**Next:** Read fully and follow `./steps/step-01-init-discovery.md`
