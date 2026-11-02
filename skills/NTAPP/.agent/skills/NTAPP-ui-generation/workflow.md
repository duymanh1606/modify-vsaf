# Workflow: Autonomous UI Schema Generation

**Goal:** Transform L3 designs into UI Semantic Schemas while auditing the Design System.

---

## WORKFLOW ARCHITECTURE — Progressive disclosure

- File này giữ KHUNG điều phối (bản đồ + cổng + rule). Chi tiết thực thi nằm TRONG từng step file.
- ⛔ Đọc ĐÚNG MỘT step mỗi lần. Hoàn tất step hiện tại (gồm mọi PAUSE/HALT) RỒI mới đọc step kế.
  KHÔNG đọc trước nhiều step. State chuyển tiếp qua artifact file (`proposed_ds_updates.md`,
  `ui_schema_{id}.json`, `drift_report.md`), không qua việc giữ instruction trong context.

---

## INITIALIZATION

> **⚠️ Spec-repo-only direction:** Skill chạy **trong spec repo** (cwd có `NTAPP-output/`, KHÔNG có `package.json`); READ source (L3 DD, L2 TechSpec, Master DS, library_apis) từ spec repo, WRITE proposal + UI schema + drift report về spec repo. KHÔNG touch code repo. Direction guard chi tiết: §U3.

### Config & Paths

> **Section anchor convention:** Mọi reference `L3 §X.X` trong skill này theo cấu trúc `NTAPP-feature-design/templates/master_detailed_design_v4_template.md` (vd §2.2 = Wireframe Blueprint, §2.3 = UI Control Matrix, §3.2 = Logic Matrix, §4.1 = UI↔DB Mapping, §4.2 = Integration Error Codes, §6 = Interaction Sync Matrix). Mọi reference `L2 §X.X` theo `NTAPP-technical-design/templates/master_techspec_v3_template.md` (vd §12 = Interface Contracts, §12.1 = Schema Spec, §12.2 = Field Deep-Dive, §12.3 = Error Contract). Nếu template renumber section → skill phải re-pin anchors trong patch cùng.

Load `.bmm-config.yaml` ở **spec repo root** — extract:
- `bmad.spec_repo_root` — root spec repo (default cwd nếu cwd có `NTAPP-output/`).
- `bmad.design_system_root` — **family root** DS (default `{spec_repo_root}/NTAPP-output/design-system`).
- Block `planning_artifacts` cho `ui_schema` (default `{spec_repo_root}/NTAPP-output/Stage_4_Design/ui_schema`) và `detailed_design` (default `{spec_repo_root}/NTAPP-output/Stage_4_Design/detailed_design`).
- Block skill `ntapp-ui-generation`: `aesthetic_critique` (default **on** — Step 4 opt-out) + `hitl_surface` (`markdown` default | `lavish` — Step 2 Stage 2.1b visual delta preview).

**Resolve DS root per unit (multi-DS aware):** đặt `{family_root}` = giá trị `bmad.design_system_root` vừa load. Sau khi `{id}` bound ở LAUNCH, resolve `{design_system_root}` THẬT của unit theo `{family_root}/_shared/ds-resolution.md` **nhánh B**: không có `{family_root}/registry.yaml` → `{design_system_root}` = `{family_root}` (legacy, y hệt cũ); 1 system → system đó; ≥2 systems → **thẻ `repo:` ở Cluster Header WBS của module chứa unit** (primary — WBS đã load ở Pre-flight 4; match `systems.*.code_repo`) → `id_prefixes` (longest-prefix) → `modules` → `default_ds` → STOP hỏi HITL (liệt kê ds_id + framework, KHÔNG đoán); thẻ WBS mâu thuẫn registry hints → STOP báo config drift. Từ đây mọi `{design_system_root}` trong skill = DS root đã resolve (riêng `_shared/*` LUÔN đọc từ `{family_root}/_shared/`); ghi `ds_id` (nếu multi-DS) vào header proposal + `_drift_notes` để audit.

### Context Loading (parameterized by `{id}` — resolve `{id}` ở LAUNCH trước)

Load inputs theo 2 tiers để giữ per-step context lean, align với HITL wait points (prompt cache TTL = 5min < typical Step 2 human approval wait).

**Tier 1 — Required now (used by Step 1-3):**
- `spec_file`: L3 Detailed Design document (`{detailed_design_root}/{id}_detailed_design.md`).
- `master_token`: Path tới `{design_system_root}/master_token.json`.
- `component_metadata`: Path tới `{design_system_root}/components_metadata.json`.

**Tier 2 — Path verified now, content loaded at Step 3:**
- `l2_techspec`: L2 Technical Specification document của BE module mà screen/widget consume API (chỉ load nếu unit có data binding).
  - **Precheck (do now):** Assert path tồn tại và file readable. Fail-fast với error rõ nếu thiếu — KHÔNG proceed sang Step 1.
  - **Why deferred:** L2 chỉ consume ở Step 3 (Schema Agent) để map data contract + Phase A drift detection. Pre-load lãng phí context Step 1-2 và prompt cache không sống qua HITL wait ở Step 2.
  - **Skip condition:** Widget không có state riêng (pure presentational — vd icon-only badge, divider, label) → không cần L2 TechSpec.

### Pre-conditions (pre-flight — chạy SAU khi `{id}` bound ở LAUNCH)

**Pre-flight 1 — Cwd phải là spec repo:** verify `{spec_repo_root}/NTAPP-output/` tồn tại tại cwd VÀ KHÔNG có `package.json` tại cwd. Nếu cwd có `package.json` (= code repo) → STOP: *"Skill ghi UI schema vào spec repo, phải chạy trong spec repo. Mở multi-root workspace, switch sang spec repo, chạy lại."*

**Pre-flight 2 — Master DS state exist:** verify `master_token.json`, `components_metadata.json`, `stack-profile.json` tồn tại trong `{design_system_root}` (= DS root ĐÃ resolve cho unit — multi-DS thì là `{family}/{ds_id}`). Thiếu → STOP với hint chạy `/ntapp-ds-bootstrap` từ code repo tương ứng DS đó trước.

**Pre-flight 3 — L3 Detailed Design exist:** verify `{detailed_design_root}/{id}_detailed_design.md` tồn tại. Thiếu → STOP với hint chạy `/ntapp-feature-design {id}` (Stage 4a) trước.

**Pre-flight 4 — WBS entry exist:** verify `{id}` xuất hiện trong cột đầu của bảng tại `NTAPP-output/Stage_2_Architecture/project_wbs.md` (markdown table). Không có → STOP: *"`{id}` chưa được declare trong project_wbs.md. Verify Stage 2 đã chạy xong + WBS đã update."* Skip nếu repo chưa có WBS file (Stage 2 chưa chạy) — log warning thay vì STOP.

**Pre-flight 5 — L2 TechSpec path (Tier 2 deferred):** đã specify trong Context Loading Tier 2. Pre-flight chỉ verify path resolvable (skip nếu widget pure presentational); content load ở Step 3.

---

## PIPELINE MAP (neo thường trực — 1 dòng/step, KHÔNG chi tiết)

| # | Step file | Persona / Owner | Output |
|---|---|---|---|
| 1 | steps/step-01-audit.md             | design_system_agent          | `feature_deltas/{id}/proposed_ds_updates.md` |
| 2 | steps/step-02-hitl-review.md       | DSO / approver (HITL)        | approval gate (no new file) |
| 3 | steps/step-03-schema-gen.md        | ui_schema_agent              | `ui_schema_{id}.json` (+ `drift_report.md` nếu BLOCKING drift) |
| 4 | steps/step-04-aesthetic-critique.md *(optional)* | visual_composition_auditor | `aesthetic_review_{id}.md` + patch `_rubric_score` |

Chuỗi: **[GATE intake: id] → 1 → [GATE DSO approve] → 3 → [GATE flag/drift] → 4 (default ON, TERMINAL)**.
Cổng người-dùng: **trước step-1** (intake id), **trong step-2** (DSO approve DS proposal — surface `markdown` hoặc `lavish` theo config `hitl_surface`), **trong step-3** (HALT khi BLOCKING drift), **trong step-4** (HITL visual gate khi rubric FAIL). Step 4 gated bởi flag `aesthetic_critique` (default **ON**, opt-out) → flag OFF thì step-3 là output cuối.

---

## GLOBAL RULES — UNIVERSAL SUB-AGENT RULES (bất biến — áp dụng mọi step/persona)

Mọi persona/sub-agent của skill này tuân thủ các convention sau (declared **ONCE** ở đây, persona không lặp lại):

### U1. Atomic file write
Mọi write filesystem (`proposed_ds_updates.md`, `ui_schema_{id}.json`, `drift_report.md`) PHẢI dùng pattern **tempfile → fsync → rename**. Không append-write, không partial write. Tránh corrupt nếu process interrupted giữa write.

### U2. Path resolution
- File trong spec repo: path relative tới `{spec_repo_root}` hoặc `{design_system_root}` tuỳ context (vd: `NTAPP-output/Stage_4_Design/ui_schema/ui_schema_{id}.json`, `feature_deltas/{id}/proposed_ds_updates.md`). KHÔNG absolute, KHÔNG hardcode user-specific path.
- Lý do relative: portability cross-machine (dev clone spec repo paths khác nhau).

### U3. Spec-repo-only direction guard
UI Generation là spec-repo-only operation: **READ-only spec repo, WRITE-only spec repo, NO code repo touch**.

- KHÔNG modify hoặc đọc source trong code repo (không scan `src/`, không đọc `node_modules/`, không edit component files). `library_apis/{lib}@{ver}/*.json` đọc từ spec repo (đã parsed offline bởi `/ntapp-ds-bootstrap` Step 1b).
- Mọi resolve target path phải check: nếu resolved absolute path bắt đầu bằng `{code_repo_root}/...` HOẶC có `package.json` ở parent chain → STOP *"UI Generation không write code repo. Target `{path}` sai. Verify `.bmm-config.yaml` `bmad.spec_repo_root` + multi-root workspace setup."*
- Áp dụng cho: design_system_agent (Step 1 proposal write), ui_schema_agent (Step 3 schema + drift_report write).

### U4. Deterministic output
Output phải reproducible: same `(L3 DD, L2 TechSpec, Master DS state)` → same output. Áp dụng:
- JSON pretty-print: 2-space indent, sorted keys alphabetical.
- Array stable ordering: drift entries sort theo severity (BLOCKING trước NON-BLOCKING) rồi alphabetical theo type code; `layout.children` theo wireframe Layout Groups order; `data_bindings.inputs/outputs` theo L3 §4.1 row order.
- Timestamps chỉ trong metadata fields định trước (`generated_at`), không scatter trong body.

### U5. Drift = STOP, not auto-correct
BLOCKING drift (data contract L3↔L2, layout primitive unknown, control unresolved, group unresolved) → STOP + emit `drift_report.md` + HITL gate per `steps/step-03-schema-gen.md` §3. Sub-agent KHÔNG được auto-correct bằng cách silently prefer 1 source, KHÔNG được silent-skip. NON-BLOCKING drift → record vào `_drift_notes` array, tiếp tục.

---

## FAIL CONDITIONS

Mọi STOP condition document tại DECISION POINTS của step tương ứng (step-01 đến step-04). workflow.md không liệt kê chi tiết tránh drift. Generic categories:

- **Pre-flight fail** — cwd sai (code repo thay vì spec repo), missing Master DS state, missing L3 DD, missing WBS entry, missing L2 path khi unit có data binding.
- **BE feature_id input** — `id` không phải `SCR-*` / `WGT-*` → Stage 4b skip, hint đi thẳng Stage 4c.
- **BLOCKING drift không resolve** — L3↔L2 data contract drift, `LAYOUT_PRIMITIVE_UNKNOWN`, `LAYOUT_CONTROL_UNRESOLVED`, `LAYOUT_GROUP_UNRESOLVED` → HITL gate `drift_report.md`, KHÔNG generate schema.
- **U3 guard violation** — sub-agent attempt write code repo.

## OUTPUTS

Tất cả output ghi về **spec repo**. Code repo KHÔNG bị skill ghi vào (đọc cũng không):

- `{design_system_root}/feature_deltas/{id}/proposed_ds_updates.md` — DS delta proposal (Step 1; consumer = `/ntapp-ds-build-component` cho `[NEW]` items).
- `{spec_repo_root}/NTAPP-output/Stage_4_Design/ui_schema/ui_schema_{id}.json` — UI Semantic Schema (Step 3, sau khi DSO approve Step 2 + BLOCKING drift reconciled). Pre-commit Rule 6 enforce file phải tồn tại trước khi commit UI code.
- `{spec_repo_root}/NTAPP-output/Stage_4_Design/ui_schema/{id}/drift_report.md` HOẶC `drift_report_{id}.md` (sibling) — chỉ khi Phase A phát hiện BLOCKING drift. Schema JSON KHÔNG generated cho đến khi reconciliation hoàn tất.
- `{spec_repo_root}/NTAPP-output/Stage_4_Design/ui_schema/{id}/aesthetic_review_{id}.md` — **chỉ khi Step 4 chạy** (flag `aesthetic_critique` bật). Verdict 7 trục + self-correct trace + override log. Step 4 đồng thời patch `visual_intent._rubric_score` (`PASS`/`FAIL`) vào `ui_schema_{id}.json`. Schema vẫn 100% token reference (no hardcode).

> **Commit:** sau khi skill chạy xong, DSO commit spec repo. Code repo không bị động chạm — không cần commit code repo cho Stage 4b.

---

## LAUNCH — [GATE: INTAKE] (bắt buộc dừng)

### Bước 1 — Resolve `id`

Hỏi user `id` của đơn vị work (lấy từ `project_wbs.md`). Cung cấp placeholder ví dụ theo prefix convention:

- `SCR-{NAME}` — màn hình FE (vd: `SCR-LOGIN`)
- `WGT-{NAME}` — widget FE dùng chung (vd: `WGT-AVATAR`)

> 👉 **[PAUSE & WAIT FOR USER INPUT]** — KHÔNG đọc step-01 trước khi user cung cấp `id`.

### Bước 2 — Auto-derive `id_type`

Từ prefix, xác định `id_type` ∈ {`screen_id`, `widget_id`}:

| Prefix | `id_type` |
|---|---|
| `SCR-*` | `screen_id` |
| `WGT-*` | `widget_id` |
| Khác (`BE-*` / `INT-*` / ...) | **STOP** — không phải FE unit |

> **Stage 4b chỉ chạy cho FE đơn vị (screen/widget).** Nếu user cung cấp `feature_id` (prefix `BE-*` hoặc `INT-*`) → DỪNG, báo: *"`{id}` là BE feature, không có UI artifact. Stage 4b skip — đi thẳng Stage 4c (`/bmad-create-story`)."*

### Bước 3 — Bind context + pre-flight

Sau khi `{id}` bound + `id_type` derived (không phải BE):
- Resolve Config & Paths với `{id}`, load Context Loading Tier 1 (verify Tier 2 path).
- Chạy Pre-flight 1–5. Bất kỳ pre-flight FAIL → STOP theo message tương ứng, KHÔNG proceed.

Pre-flight pass →
**Next:** Read fully and follow `./steps/step-01-audit.md`
