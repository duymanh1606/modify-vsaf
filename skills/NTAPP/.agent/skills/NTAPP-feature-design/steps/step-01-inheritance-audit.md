# STEP 01: INHERITANCE AUDIT & OVERVIEW

> **Acting as:** [Agent F0 — Lead Orchestrator](../agents/agent_f0_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R3 (Zero-Fabrication), R7 (Stopping Errors), R9 (Missing Input Handling), R10 (Inheritance Compliance).

## 1. Mục tiêu
Xác lập ranh giới kỹ thuật bằng cách kế thừa các tiêu chuẩn từ source primary tương ứng (L2 TechSpec cho BE; Master UX Spec cho FE), đồng thời định nghĩa bối cảnh tổng quan (Section 1 của DD) cho đơn vị work.

## 2. Pre-flight Check (BẮT BUỘC, theo R9)

Trước khi đọc input, Agent F0 PHẢI verify dependency theo `id_type`:

**Common (mọi `id_type`):**
- [ ] **`id`** + **`id_type`** đã resolve ở INITIALIZATION (workflow.md Bước 1-2).
- [ ] **WBS SSoT:** `{planning_artifacts}/project_wbs.md` tồn tại VÀ chứa entry `id` trong unit list tương ứng:
   - `id_type == feature_id` → lookup `features` list
   - `id_type == screen_id` → lookup `screens` list
   - `id_type == widget_id` → lookup `widgets` list

**Conditional theo `id_type`:**

| `id_type` | Dependencies bắt buộc |
|---|---|
| `feature_id` (BE) | **L2 TechSpec canonical:** `{planning_artifacts}/{module}_techspec.md`. `{module}` xác định bằng cách lookup `id` trong WBS. UX Spec optional (chỉ khi feature cần ref FE) |
| `screen_id` (FE) | **Identity (SSoT, luôn check):** `id` trong `project_wbs.md` screens list — vắng = orphan → DỪNG. **Journey Spec (chỉ feature multi-screen-new):** `{planning_artifacts}/ux_design.md` tồn tại + approved (screen không có trong journey table nào → WARN advisory, không dừng). **Conventions/Catalog:** `ux_conventions.md` + `component_catalog.md` (recommended — thiếu → WARN + hint bootstrap/3b). L2 TechSpec của BE module mà screen consume (optional). **HLD-fallback (gate SKIP):** feature thuộc nhánh gate-SKIP (single-screen/reuse — `ntapp-ux-design` step-01 §2.0) → không yêu cầu Journey Spec; source = WBS + HLD §3.1.1/§3.2 + conventions/catalog nếu có; ghi `ux_source: HLD-fallback`. |
| `widget_id` (FE) | Như `screen_id` — identity check trên `project_wbs.md` widgets list; journey usage lookup trong Journey Screen Tables (WARN nếu không thấy); conventions/catalog recommended; HLD-fallback như trên. |

**Nếu BẤT KỲ check nào fail** → DỪNG ngay (theo R9 + R7 Stopping Error #1/#2/#3), KHÔNG generate placeholder. Hỏi user explicit:

```markdown
❌ Pre-flight FAILED — thiếu input cần cho Layer 3 Detailed Design (id={id}, id_type={id_type}):
  - [ ] {liệt kê file/check thiếu}

Trước khi tiếp tục, vui lòng:
  (a) Cung cấp đường dẫn đến file thiếu, HOẶC
  (b) Quay lại Stage upstream để tạo:
      - WBS / `id` thiếu → quay Stage 2 (`/ntapp-architecture-design`)
      - L2 TechSpec thiếu/chưa approve (BE) → quay Stage 3a (`/ntapp-technical-design`)
      - Journey Spec thiếu/chưa approve (FE, feature multi-screen-new) → quay Stage 3b (`/ntapp-ux-design`).
        **NGOẠI LỆ gate-SKIP:** nếu feature thuộc nhánh SKIP (single-screen/reuse, gate ux-design §2.0) VÀ `id` có trong `project_wbs.md` screens/widgets list → KHÔNG bounce; dùng **HLD-fallback** (source = WBS + HLD + `ux_conventions.md`/catalog nếu có), ghi `ux_source: HLD-fallback`. Chỉ bounce khi `id` cũng KHÔNG có trong `project_wbs.md` (orphan thật → quay Stage 2).

Tôi sẽ KHÔNG generate content thay thế (R3 + R9).
```

## 3. Chỉ thị thực thi

> **Lưu ý chung:** Skill này KHÔNG load full Master DS (`master_token.json`/`components_metadata.json`) — component vocabulary đến từ **`component_catalog.md`** (digest derived, ~1-2k token) + patterns từ `ux_conventions.md` (theo R10). Token-level styling là việc Stage 4b.

### 3.1 Nếu `id_type == feature_id` (BE)

1. **Đọc L2 TechSpec:** Load `{planning_artifacts}/{module}_techspec.md` (canonical latest). Trích xuất:
    - §4-5 (Functional Model + WBS) cho `id` đang thiết kế.
    - §9 (Cấu trúc thư mục dự án) — folder structure chuẩn.
    - §11 (Logical Data Model — ERD §11.1 + Data Dictionary §11.2) — entity schema cần consume.
    - §12 (Interface Contracts) — API/protocol cần adapt.

2. **Đối soát WBS:** Verify `id` (vd `BE-{MOD}-NN`) tồn tại trong `features` list của `project_wbs.md` + lấy phạm vi feature.

3. **Inheritance Compliance Audit (R10):** Module boundary + entity schema phải khớp 100% L2 TechSpec.

### 3.2 Nếu `id_type ∈ {screen_id, widget_id}` (FE)

1. **Đọc UX Journey Spec + Conventions + Catalog:** Load `{planning_artifacts}/ux_design.md` (v4.0 slim) + `{planning_artifacts}/ux_conventions.md` + `{design_system_root}/component_catalog.md`. Trích xuất cho đơn vị:
    - Persona references (§1.3) + journey liên quan (**§4** — Mermaid + Journey Screen Table).
    - **Hàng Journey Screen Table của `id`** (§4): `Purpose`, **`Key states`** (ràng buộc tối thiểu cho §2.3 states — input audit L2 mandatory states / L10 affordance ở §2.4), `Entry/Exit`, `Conventions refs`. Cell `Purpose` có thể kèm link `([sketch](...#{screen_slug}))` → giữ lại cho F3 step-02 mở frame sketch preview (visual seed). *(Per-screen Regions/Components KHÔNG còn trong UX Spec từ v4.0 — F3 tự author wireframe, single owner.)*
    - Archetype + composition model + **state taxonomy (§2)** + IA placement (**§3**).
    - **Journey-level layout audit (L5/L6/L9)** ghi ở dòng self-audit cuối mỗi journey §4 — kế thừa làm **ràng buộc upstream** cho §2.4. Feature-design KHÔNG re-audit L5/L6/L9, chỉ inherit; phát hiện Journey Spec vi phạm → escalate ngược (R10).
    - Conventions áp cho unit: content rule + **status label** (`ux_conventions.md` §C2), interaction patterns (§C3), notification/error surfaces (§C4/§C5), responsive/a11y (§C6).
    - Component vocabulary + recipes từ `component_catalog.md` (cho §2.2 recipe-first + §2.3 cột DS candidate).
    - Verify `id` xuất hiện trong ≥1 Journey Screen Table (§4). KHÔNG xuất hiện (nhưng có trong WBS) → WARN advisory (screen ngoài journey chính — R7 #3), ghi note Section 1, tiếp tục.

    **Nếu Journey Spec không tồn tại cho feature (gate-SKIP / HLD-fallback):** lấy:
    - Screen/widget identity (+ module) từ **`project_wbs.md`** (SSoT); actor từ **HLD §3.1.1**; IA / module breakdown từ **HLD §3.2** (cho L9 IA-depth).
    - `ux_conventions.md` **nếu đã có** (conventions là project-wide — vẫn áp đầy đủ) + `component_catalog.md`; chưa từng có conventions → DS baseline + HLD §3.2.
    - Per-unit wireframe/composition do chính `feature-design` author ở Stage 4a §2.2. Đánh dấu `ux_source: HLD-fallback` ở Section 1.
    - **Không có journey self-audit để inherit** → §2.4 xử lý L5/L6/L9 theo nhánh HLD-fallback (chi tiết tại step-02 §2.4); composition audit L1-L4/L7/L8/L10/L11 chạy đầy đủ.

2. **Đối soát WBS:** Verify `id` tồn tại trong `screens` list (cho `screen_id`) hoặc `widgets` list (cho `widget_id`).

3. **Đọc L2 TechSpec (optional, cross-check only):** Nếu screen/widget consume API từ BE module → load `{module}_techspec.md` §12 (Interface Contracts, đặc biệt §12.3 Error Contract & Mapping) để **đối soát** mandatory states (empty/loading/error có fetch backing) + error-message §2.3 khớp error code. KHÔNG author field-mapping ở đây — data binding chính thức materialize ở **Stage 4b `ui_schema`** (đọc §12 làm SSoT). KHÔNG kéo §11 ERD vào FE (FE thấy response DTO qua §12, không thấy DB column — inherit ERD = leak persistence vào FE).

4. **Inheritance Compliance Audit (R10):** DD phải cover đủ Key states từ Journey Screen Table + tuân Conventions refs; component vocabulary từ `component_catalog.md` (không bịa tên). *Nếu `ux_source: HLD-fallback`:* không có journey table để khớp — audit thay bằng: `id` + module khớp `project_wbs.md`, conventions (nếu có) vẫn áp, component names ∈ catalog.

### 3.3 Điền Section 1 (Master Detailed Design) — mọi `id_type`

- Tham chiếu Parent source primary (L2 TechSpec hoặc UX Spec) + `id_type` rõ ràng.
- Định nghĩa Mục đích, Loại chức năng (Web/Mobile/API/UI...).
- Xác định Pre-condition và Post-condition.
- Note rõ scope: BE-only / UI-only / UI+local-state (widget own state).

### 3.4 Quyết định

- **Nếu đủ thông tin & khớp inheritance** → Chuyển sang Step 02 (hoặc skip theo Execution Matrix).
- **Nếu phát hiện Drift L2↔L3 hoặc UX-Spec↔L3** → DỪNG (theo R7 #2/#3), escalate user fix Stage upstream trước.

## 4. Đầu ra yêu cầu

- Section 1 hoàn chỉnh trong Master Detailed Design (tham chiếu Parent source theo `id_type`).
- **Lưu trữ:** Bản thảo Markdown lưu tại `{intermediate_folder}/f0_overview_part.md`.
- Báo cáo xác nhận theo `id_type`:
   - BE: "Feature `{id}` tuân thủ tiêu chuẩn module `{module}` (TechSpec v{N}). Inheritance audit PASS."
   - FE: "{Screen|Widget} `{id}` kế thừa Journey Spec §4 (Key states: {...}) + Conventions {§C-x list} + catalog OK. Inheritance audit PASS." (HLD-fallback: "... kế thừa WBS + HLD §3.2 + conventions/catalog, `ux_source: HLD-fallback`.")

## [GATE] — Pre-flight & Inheritance (⛔ kiểm trước khi sang Next)

- **Pre-flight (§2) PASS:** `id` tồn tại trong WBS unit list tương ứng + input bắt buộc theo `id_type` đầy đủ. Nếu FAIL → DỪNG, in block "❌ Pre-flight FAILED" (§2), KHÔNG generate placeholder (R9 + R7).
- **Không drift (§3.4):** Không phát hiện Drift L2↔L3 / UX-Spec↔L3. Nếu có drift → DỪNG (R7 #2/#3), escalate user fix Stage upstream trước.
- Traversal tuyến tính: luôn sang Step 02. Việc Step 02 RUN hay SKIP *action* do Skip Condition (§0) của Step 02 quyết định theo `id_type`.

**Next:** Read fully and follow `./step-02-ui-interaction-design.md`
