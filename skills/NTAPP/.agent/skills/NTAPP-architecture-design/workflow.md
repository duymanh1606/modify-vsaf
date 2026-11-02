# Architecture Design Workflow (NTAPP Multi-Agent Edition)

**Goal:** Tạo tài liệu Thiết kế Kiến trúc Tổng thể (HLD) hoàn chỉnh bằng chuẩn NTAPP Final Template thông qua hệ thống 6 Agent (A/B/C/D/E/F) chuyên biệt hoạt động tuần tự.

**Your Role:** Bạn đóng vai **Agent E (Orchestrator)** — điều phối tuần tự Agent A → B → C → D → F, vận hành các quality gate, và assembly bản HLD cuối cùng. Bạn là điểm chạm duy nhất với người dùng trong toàn workflow.

**Iron Rules:** Toàn workflow tuân thủ [principles/iron_rules.md](./principles/iron_rules.md). Đọc file này trước khi thực thi bất kỳ step nào.

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (mode + roster + bản đồ + rule + launch). Chi tiết thực thi nằm TRONG từng step file `./steps/`.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi PAUSE/GATE) RỒI mới đọc step kế qua pointer `**Next:**` ở cuối step. KHÔNG đọc trước nhiều step. State chuyển tiếp qua `part_*.md` trong `{intermediate_folder}`, không qua việc giữ instruction trong context.

---

## MODE SELECTION (Agent E đọc ĐẦU TIÊN)

Skill có 2 mode. Agent E xác định mode từ user message **trước khi** chạy bất kỳ step nào:

| Mode | Trigger | Khi nào dùng |
|---|---|---|
| **FULL** (default) | "thiết kế kiến trúc" / "tạo HLD" / không có flag | Lần đầu tạo HLD, hoặc overhaul toàn bộ kiến trúc |
| **APPEND** | `--append`, "thêm unit vào WBS", "amend WBS", "bổ sung feature vào kiến trúc" | Đã có HLD + WBS lock; cần thêm 1 vài unit mới mà **KHÔNG** đổi contract Module 0 |

- **FULL mode** → chạy full pipeline A→B→C→D→F (mục [EXECUTION](#execution)).
- **APPEND mode** → chạy luồng rút gọn ở mục [APPEND MODE EXECUTION](#append-mode-execution-incremental-wbs-amendment). **Bỏ qua** mục EXECUTION đầy đủ.

> **Vì sao có APPEND:** Sau khi WBS lock, mỗi feature unit mới (vd từ `/ntapp-feature-triage` hard-gate 6) trước đây phải re-run full pipeline (HLD → Module 0 → WBS → audit → assembly) — quá nặng và cascade Module 0 không cần thiết khi unit mới là leaf nằm gọn trong module sẵn có. APPEND là entry point nhẹ: chỉ merge WBS + audit + sync HLD §3.2.0, escalate FULL **chỉ khi** chạm contract/boundary.

---

## ROSTER & ROLES

| Agent | Role | Steps Owned |
|---|---|---|
| **A** | Context Strategist | 02 |
| **B** | Research Scout (Conditional) | 03 |
| **C** | System Architect | 04.1, 04.2 |
| **D** | Implementation & Security Lead | 05 |
| **E** | Orchestrator + QA Gatekeeper | 01, 04.1b, 07 |
| **F** | Integration Architect | 06 |

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

Mỗi step là một file độc lập trong `./steps/`, mở đầu bằng `> **Acting as:** [Agent X]` trỏ persona, kết thúc bằng pointer `**Next:**` tới step kế (step cuối là TERMINAL).

| # | Step file | Agent | Output | Gate |
|---|---|---|---|---|
| 01 | steps/step-01-init.md | E | Context Summary (clarify gaps) | intake — user confirm Context + Tech Stack |
| 02 | steps/step-02-strategy.md | A | part_02_context_strategy.md | **G1** NFR Completeness |
| 03 | steps/step-03-research.md | B (conditional) | part_03_tech_research.md | user confirm tech stack (nếu research) |
| 04.1 | steps/step-04.1-architecture-global.md | C | part_04.1_global_architecture.md + project_wbs.md | handshake → 04.1b; **G3** L1/L2 self-check |
| 04.1b | steps/step-04.1b-wbs-audit.md | E | project_wbs.md "Audited & Locked" | **G2** WBS Coverage |
| 04.2 | steps/step-04.2-architecture-modules.md | C | part_04.2_modular_deepdive.md | — |
| 05 | steps/step-05-implementation-security.md | D | part_05_implementation_security.md | — |
| 06 | steps/step-06-module0.md | F | 00_system_connectivity_integration.md (+ archive) | R8 Sync Check |
| 07 | steps/step-07-assembly.md | E | architecture_design.md (+ archive) | **G4** Quantitative Audit (TERMINAL) |

Chuỗi (FULL mode): **01 → [G1] 02 → 03 (conditional — tự pass-through nếu không kích hoạt) → 04.1 → [G2] 04.1b → 04.2 → 05 → 06 → 07 [G4]**.
Cổng người-dùng: **intake** (Step 01) + **xác nhận tech stack** (Step 03 nếu research) + **trình bày HLD cuối** (Step 07). Các gate G1–G4 + R8 là QA/self-check (FAIL → loop về owner — KHÔNG phải pointer `**Next:**`).

---

## INITIALIZATION

### Phân giải cấu hình (Configuration Resolution)

Trước khi chạy bất kỳ step nào, Agent E PHẢI resolve config theo cascade 3 layer (ưu tiên cao → thấp).

#### Bước 0 — Resolve `{project-root}`

Walk up từ `cwd` tìm marker folder:
1. Nếu thấy `_bmad/` → đó là `{project-root}`.
2. Nếu thấy `.git/` → đó là `{project-root}`.
3. Nếu lên đến `/` không thấy gì → fallback `cwd` + log warning: "⚠️ Không tìm thấy marker (`_bmad/` hoặc `.git/`), dùng cwd làm project-root".

#### Layer 1 — BMad project config

Đọc `{project-root}/_bmad/bmm/config.yaml` nếu tồn tại. Lookup keys:
- `project_name`
- `planning_artifacts`

BMad dùng placeholder `{project-root}` trong values → Agent E thay bằng absolute path đã resolve ở Bước 0.

#### Layer 2 — Skill family config (override)

Đọc `{project-root}/.bmm-config.yaml` nếu tồn tại. Tìm section `ntapp-architecture-design:`. Override giá trị từ Layer 1 nếu có.

Schema mong đợi:
```yaml
ntapp-architecture-design:
  project_name: <string>          # optional, override Layer 1
  planning_artifacts: <path>      # optional, override Layer 1
```

#### Layer 3 — Default + Interactive (fallback)

Khi cả Layer 1 và Layer 2 đều miss biến cần → DỪNG, hỏi user (Pause & Wait):

```markdown
## ⚙️ SKILL CONFIG MISSING — Setup lần đầu

Tôi không tìm thấy config (`_bmad/bmm/config.yaml` hoặc `.bmm-config.yaml`).
Cần xác định 2 thông tin sau (ENTER để chấp nhận default):

[Q1] **project_name** (default: `{tên folder của project-root}`)?
[Q2] **planning_artifacts** path cho artifact thiết kế
     (default: `{project-root}/output/architecture/`)?

→ Sau khi anh trả lời, tôi sẽ ghi vào `{project-root}/.bmm-config.yaml`
   để lần sau không hỏi lại.
```

Sau khi user trả lời:
- Tạo/append vào `{project-root}/.bmm-config.yaml` section `ntapp-architecture-design:`.
- mkdir -p `{planning_artifacts}/architecture_design_parts/`.

#### Biến runtime cuối cùng

Sau cascade, các biến phải có giá trị:

| Biến | Nguồn | Ghi chú |
|---|---|---|
| `project_name` | Layer 1/2/3 | Tên dự án — hiển thị trong header HLD |
| `planning_artifacts` | Layer 1/2/3 | Absolute path (đã resolve `{project-root}`) |
| `intermediate_folder` | Auto-derive | = `{planning_artifacts}/architecture_design_parts/` |
| `template_path` | Hardcode | `./templates/architecture_design_final_template.md` — resolve relative to **skill root** (folder chứa workflow.md), KHÔNG phải cwd |
| `agent_personas_path` | Hardcode | `./agents/` — relative to skill root |
| `iron_rules_path` | Hardcode | `./principles/iron_rules.md` — relative to skill root |
| `date` | System | Format ISO 8601 `YYYY-MM-DD` |

### Output Naming Convention (Dual-Write)

Mọi output cuối cùng (HLD + Module 0) đều ghi 2 bản: canonical (latest) + archive (versioned snapshot).

| Output | Canonical (latest) | Archive (history) |
|---|---|---|
| HLD final | `{planning_artifacts}/architecture_design.md` | `{planning_artifacts}/archive/architecture_design_v{N}.md` |
| Module 0 | `{planning_artifacts}/00_system_connectivity_integration.md` | `{planning_artifacts}/archive/00_system_connectivity_integration_v{N}.md` |
| Intermediate parts | `{intermediate_folder}/part_*.md` | (không archive — overwrite mỗi run) |

**Versioning logic:** Detect `N_next` bằng `ls archive/{base}_v*.md` → `max(N) + 1` (hoặc `1` nếu archive rỗng).

**Module 0 write constraint:** Tuân thủ [Iron Rules R8](./principles/iron_rules.md#r8-contract-lock-khoá-hợp-đồng-tích-hợp) — Module 0 chỉ được write theo cascade từ HLD hoặc reconcile drift.

### Quality Gates Map

Bảng định nghĩa Gate (G1-G4) tại [`principles/iron_rules.md`](./principles/iron_rules.md#r6-handshake--gate-trạm-kiểm-soát) **R6 — Handshake & Gate** (SSoT). Không lặp body ở đây để tránh drift.

---

## GLOBAL RULES (bất biến — áp dụng mọi step FULL mode)

- ✅ Toàn workflow tuân thủ [Iron Rules R1–R9](./principles/iron_rules.md) — đọc trước khi thực thi bất kỳ step nào.
- ✅ Agent E là điểm chạm duy nhất với người dùng; mỗi step hoá thân đúng persona trong [`./agents/`](./agents/).
- ✅ **NO FABRICATION (R3):** không bịa số liệu/thực thể/giao thức ngoài input đã xác nhận — thiếu thì đánh `[TBD]` hoặc hỏi user.
- ✅ **Dual-write (R8):** mọi output cuối (HLD + Module 0) ghi 2 bản — canonical (latest) + archive versioned.
- ⛔ Đọc đúng MỘT step file mỗi lần; chỉ đọc step kế qua pointer `**Next:**` khi step hiện tại xong + qua cổng (nếu có). State chuyển tiếp qua `part_*.md` trong `{intermediate_folder}`, KHÔNG qua việc giữ instruction trong context.

---

## APPEND MODE EXECUTION (Incremental WBS Amendment)

> **Acting as:** Agent E điều phối; Agent C thực thi merge WBS; Agent F **không** tham gia (không có contract change ở mode này).
> **Tuân thủ:** [Iron Rules](./principles/iron_rules.md) — R1 (Verbatim), R2 (Zero-summarization), R4 (Traceability), R5 (Consistency), R8 (Contract Lock).
> **Mục tiêu:** Thêm 1 vài work unit mới vào `project_wbs.md` đã lock + sync HLD §3.2.0, **KHÔNG** re-run toàn pipeline. Entry point nhẹ cho `/ntapp-feature-triage` hard-gate 6.

### A1 — Pre-flight (Agent E)

1. Resolve config theo cascade 3 layer — **giống FULL mode** [INITIALIZATION](#initialization) (cùng `project_name`, `planning_artifacts`, `intermediate_folder`).
2. Verify `{planning_artifacts}/project_wbs.md`:
   - **KHÔNG tồn tại** → STOP: *"Chưa có WBS để append. Chạy FULL mode (`/ntapp-architecture-design`) trước."*
   - **Tồn tại + invalid format** (thiếu Function Decomposition Tree hoặc Coverage Matrix) → escalate như [step-04.1 §3.1](./steps/step-04.1-architecture-global.md) (backup `.bak` / user tự sửa). KHÔNG đụng file trước khi user confirm.
   - **Tồn tại + valid** → tiếp A2.
3. Verify HLD canonical `{planning_artifacts}/architecture_design.md` tồn tại (cần để re-inject §3.2.0 ở A5). Thiếu → WARN: append WBS được nhưng HLD chưa có để sync — gợi ý chạy FULL.

### A2 — Clarify new unit(s) (Agent E — Pause & Wait)

Hỏi user cho **mỗi** unit mới (cheap → expensive). KHÔNG tự suy đoán (R3):

- `module_type` ∈ 4-type (`backend-service` / `frontend-app` / `integration-contract` / `infrastructure`).
- `id` theo prefix convention tương ứng (`BE-{MOD}-NN` / `SCR-{NAME}` / `WGT-{NAME}` / `INT-{SRC}-NN`). Verify id **chưa** tồn tại trong WBS (append, không overwrite).
- `parent_module` — **phải** ∈ module list declared trong WBS hiện tại. Module **MỚI** → STOP, escalate FULL mode (Agent C cần re-cluster + redraw L1/L2). Đây là biên giới append.
- `parent_epic` / story ID từ PRD/Epics (Traceability R4).
- Relations: screen ghi `consumes:`, widget cross-screen ghi `used_by:`, contract ghi `provider:` + `consumers:` (format ở [template mục 0](./templates/coverage_matrix_wbs.md)).
- Mô tả ngắn + data domain chính.

### A3 — CONTRACT-IMPACT GATE (Agent E — biên giới append vs full cascade)

APPEND **chỉ** hợp lệ khi unit mới KHÔNG đổi contract/boundary đã lock. Refuse → escalate FULL khi BẤT KỲ điều kiện sau:

- `module_type = integration-contract` (INT-*) → contract mới = Module 0 surface change.
- Unit mới đổi response shape / field của contract INT-* đã có.
- Unit mới thêm External System chưa có trong sơ đồ L1/L2 (đổi system boundary).

→ Output: *"❌ Unit này chạm contract/boundary Module 0 → KHÔNG append được. Chạy FULL mode để cascade HLD + Module 0 (Step 06)."* (mirror `/ntapp-feature-triage` hard-gate 4 + Iron Rule R8.)

Pass gate → unit là **leaf nằm gọn trong container/module sẵn có** → A4.

### A4 — Merge WBS + Audit (Agent C → Agent E)

1. Agent C áp **WBS File Management Rule** ([step-04.1 §3.1](./steps/step-04.1-architecture-global.md), nhánh *"File ĐÃ tồn tại + valid"*): giữ nguyên row cũ, **append** row mới vào CẢ Function Decomposition Tree + Coverage Matrix. TUYỆT ĐỐI KHÔNG overwrite toàn file.
2. Agent E chạy **[Step 04.1b WBS Audit (G2)](./steps/step-04.1b-wbs-audit.md)** trên WBS đã merge — scope: coverage của unit mới + consistency toàn cục (relations không orphan, prefix khớp `module_type`, traceability về epic). FAIL → loop về Agent C sửa, KHÔNG đi A5.

### A5 — Sync HLD + version bump (Agent E)

1. WBS là SSoT cho HLD §3.2.0 → re-inject **Tree + Bảng verbatim** vào `architecture_design.md`, **chỉ** §3.2.0; KHÔNG đụng section khác (R1 Verbatim + R2 Zero-summarization).
2. Dual-write archive: bump `archive/architecture_design_v{N+1}.md` (versioning logic ở [INITIALIZATION → Output Naming](#output-naming-convention-dual-write)).
3. **Module 0 KHÔNG re-run** — đã gate ở A3 (không có contract change). Nếu cần cascade Module 0 thì A3 đã escalate FULL, không tới đây.

### A6 — Downstream notice (Agent E — nhắc, KHÔNG tự chạy)

- **Slice plan:** chạy `/ntapp-slice-planning` (re-run mode) để assign unit mới vào slice — slice-planning đã có re-run mode cho *"WBS thêm unit mới"*.
- **Re-run triage:** `/ntapp-feature-triage` cho unit mới (giờ đã có `wbs_id_match` → triage route được lane).

### Exit Criteria (APPEND)

- [ ] Unit mới xuất hiện trong CẢ Tree + Bảng của `project_wbs.md`; row cũ nguyên vẹn.
- [ ] WBS Audit G2 PASS trên file đã merge.
- [ ] HLD §3.2.0 đã re-inject + archive version bump (chỉ khi HLD tồn tại).
- [ ] KHÔNG có contract/Module 0 change (nếu có → đã escalate FULL ở A3).

---

## EXECUTION

> **Áp dụng cho FULL mode.** APPEND mode dùng mục [APPEND MODE EXECUTION](#append-mode-execution-incremental-wbs-amendment) ở trên.

Sau khi resolve config ([INITIALIZATION](#initialization)) và xác nhận **mode = FULL** → khởi động pipeline tuần tự theo PIPELINE MAP. Đọc đúng MỘT step mỗi lần; mỗi step tự trỏ step kế qua `**Next:**` ở cuối file. KHÔNG đọc trước nhiều step.

**Next:** Read fully and follow `./steps/step-01-init.md`
