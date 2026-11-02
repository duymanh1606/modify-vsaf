# STEP 01: INPUT DISCOVERY & SCAFFOLD

> **Thực hiện bởi:** Agent UX0 (UX Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R3, R7, R8, R9, R10**.

## 1. Mục tiêu

Pre-flight Input Audit (R7+R9), Inheritance Audit (R8+R10), xác định **conventions mode** (bootstrap/delta), khởi tạo scaffold 2 artifact + parts dir + briefing cho Squad.

## 2. Chỉ thị thực thi

### 2.0. Applicability Gate (per-feature, batch run-once) — chạy TRƯỚC mọi việc khác

> **SSoT của tiêu chí "khi nào chạy `/ntapp-ux-design`".** Các surface khác (slice-planning handoff, Manual §3 Stage 3b, feature-triage) chỉ *reference* gate này, không tự định nghĩa lại.

**Bản chất:** `ux-design` thiết kế **trải nghiệm cross-screen cho TOÀN BỘ feature** — union mọi `SCR/WGT` trải rải rác qua **nhiều slice**. Vì trải nghiệm là mối quan tâm **ngang (horizontal)**, skill chạy **MỘT lần, batch, sau Stage 2b slice-planning, TRƯỚC khi mở vòng per-slice** — **KHÔNG** per-slice. Mỗi `feature-design` (Stage 4a) trong vòng sau đó **kế thừa** journey/IA liên quan từ Journey Spec + patterns từ Conventions (R10).

`/ntapp-ux-design` **chỉ áp dụng** khi **cả 2** điều kiện đúng:

1. **Lane 3 (full per-slice loop).** Các lane khác (Express hotfix / Path B quick-dev / Ad-hoc per-unit) KHÔNG chạy Stage 3b theo định nghĩa lane.
2. **Feature là multi-screen MỚI** (xét trên **union `SCR/WGT` của mọi slice** thuộc feature, không per-slice) — thoả **≥1**:
   - Feature giới thiệu **≥2 màn mới** (`SCR-*`) tạo thành journey nối nhau, HOẶC
   - Feature giới thiệu **actor / flow mới** chưa được cover bởi Journey Spec đã có.

**SKIP** khi thoả **≥1** (mỗi `feature-design` per-unit ở Stage 4a kế thừa IA từ Journey Spec đã có / HLD §3.2 — WBS §3.2.0 + module breakdown; conventions đã có vẫn áp bình thường):
- Feature **reuse** một UX journey đã có (chỉ sửa/mở rộng trong các màn đã spec, không actor/flow mới).
- Feature **single-screen** (đúng 1 `SCR-*` mới, hoặc chỉ `WGT-*`).
- Feature **BE-only / non-UI**.

**Hành động khi SKIP:** KHÔNG sinh/sửa `ux_design.md`. Báo user: *"Feature {name} không thoả gate multi-screen-new (lý do: {reason}) → skip Stage 3b. Vòng per-slice chạy thẳng `/ntapp-feature-design` per unit; wireframe per-unit kế thừa IA từ {Journey Spec đã có | HLD §3.2} + `ux_conventions.md` (nếu đã có)."* Rồi **DỪNG skill** (không proceed §2.1).

**Reuse một phần** (mở rộng journey đã có + thêm 1 màn đơn lẻ): vẫn SKIP full ux-design — ghi delta vào Journey Spec đã có thủ công ở Stage 4a. Chỉ re-qualify gate khi delta đủ lớn (≥2 màn mới nối journey).

> **Đơn vị đánh giá = feature (cả batch slice), KHÔNG per-slice.** Đánh giá MỘT lần sau khi slice plan emit. Screen inventory lấy từ `project_wbs.md` (SSoT); "reuse vs new" so với `ux_design.md` đã có (nếu brownfield per-feature). Triage Stage 0.5 chỉ advisory sớm.

### 2.1. Path Resolution

Load config cascade (xem `workflow.md` INITIALIZATION) để resolve: `{planning_artifacts}`, `{intermediate_folder}`, `{stage_1_discovery}`, `{stage_2_architecture}`, `{design_system_path}`, `{ux_sketch_path}`, `{project_knowledge}`.

### 2.2. Pre-flight Existence Check (R7 + R9)

Verify file tồn tại + format hợp lệ. KHÔNG đọc nội dung ở step này.

| Tài liệu | Phân loại | Đường dẫn | Action khi miss |
|:--|:--|:--|:--|
| **PRD** | ✅ Required | `{stage_1_discovery}/prd*.md` | DỪNG (R7 #1) |
| **Epics/Stories** | ✅ Required | `{stage_1_discovery}/epics*.md` | DỪNG (R7 #1) |
| **`project_wbs.md`** | ✅ Required | `{stage_2_architecture}/project_wbs.md` | DỪNG — Stage 3b chạy sau slice-planning, WBS phải lock (R9) |
| **HLD** | ⚠️ Recommended | `{stage_2_architecture}/architecture_design.md` | WARN — frontmatter `hld: missing` |
| **Module 0 §7** | ⚠️ Recommended | `{stage_2_architecture}/00_system_connectivity_integration.md` | WARN — `module_0_section_7: missing` |
| **`component_catalog.md`** | ⚠️ Recommended | `{design_system_path}/component_catalog.md` — multi-DS (`{design_system_path}/registry.yaml` tồn tại): load catalog của MỌI DS chứa screen của feature (`{design_system_path}/{root}/component_catalog.md` per system — resolve nhánh C `_shared/ds-resolution.md`), label vocabulary theo `ds_id` | WARN — `catalog: missing`, hint `/ntapp-ds-bootstrap` |
| **UX Sketch** | 💡 Optional | `{ux_sketch_path}` | Proceed — `ux_sketch: missing` |
| **`ux_conventions.md`** | 🔀 Mode switch | `{planning_artifacts}/ux_conventions.md` | Tồn tại → **DELTA MODE**; chưa có → **BOOTSTRAP MODE** |
| **`ux_design.md` (cũ)** | 🔀 Context | `{planning_artifacts}/ux_design.md` | Tồn tại → brownfield-per-feature: IA §3 vẽ DELTA, journey mới đặt cạnh journey cũ |
| **Project Docs** | 💡 Optional | `{project_knowledge}/` | Proceed |

**Format validation:** PRD có cấu trúc FR/BR/NFR rõ ràng? Nếu không → R7 #2, escalate PM/BA refine PRD trước.

### 2.3. Inheritance Audit & Contract Lock (R8 + R10)

Đọc nội dung từ file đã pass existence check, extract canonical contracts:

**Từ HLD** (nếu có): §1.2 In-scope modules + External Systems → seed §1; §3.1.1 Persons → **lock actor list** (§1.3 references + §4 journeys); §3.2.2 Sequence diagrams → reference cho §4.

**Từ `project_wbs.md`** (Required): screens/widgets của `frontend-app` module → **lock unit ID list** cho §3 nav leaf + §4 journey screen tables (R8.4 — UX không tự đặt ID).

**Từ Module 0 §7** (nếu có): state enum mỗi entity → **lock state list** cho `ux_conventions.md` §C2 status labels (1-1 mapping).

**Từ `component_catalog.md`** (nếu có): component vocabulary + recipes → reference khi journey/conventions gọi tên component (R8.3). KHÔNG load full `components_metadata.json`. **Multi-DS:** vocabulary lấy theo DS của screen đang nhắc — component 2 DS trùng tên nhưng khác implementation → luôn kèm label `*({ds_id})*`; screen không resolve được DS → dùng mô tả chung, WARN (không STOP — catalog recommended).

**Từ UX Sketch** (nếu có): personas (SSoT — §1.3 chỉ reference tên), rough IA, primary journey → seed. **Audit drift sketch ↔ HLD/Module 0** — sketch lệch → escalate (R7 #4), HLD/Module 0 thắng.

Lưu inheritance summary (actor list, unit ID count, state enum count, catalog status, conventions mode) vào briefing.

### 2.4. Xác nhận với User

Trình bày: (1) Pre-flight result; (2) Inheritance summary + **conventions mode (bootstrap/delta)**; (3) Drift report (nếu có sketch lệch).

**CHỜ USER XÁC NHẬN** trước khi tiếp tục.

### 2.5. Khởi tạo Scaffold + Briefing

1. **Journey spec:** đọc `../templates/ux-design-spec-template.md` (v4.0), điền `{{project_name}}`, `{{anchor_system}}`, `{{integrated_systems}}`, `{{date}}`, `{{user_name}}` → scaffold `{planning_artifacts}/ux_design.md`.
2. **Conventions:** BOOTSTRAP MODE → đọc `../templates/ux-conventions-template.md`, scaffold `{planning_artifacts}/ux_conventions.md`. DELTA MODE → giữ nguyên file hiện có (steps 04/06/11/12/13 sẽ tự check delta).
3. Tạo `{intermediate_folder}` (flat).
4. Frontmatter `ux_design.md`:
   ```yaml
   stepsCompleted: [step-01-init-discovery]
   inputDocuments: [...]
   conventions_mode: bootstrap | delta
   inheritance:
     hld: present | missing
     module_0_section_7: present | missing
     wbs: present
     catalog: present | missing
     ux_sketch: present | missing
   ```
5. Briefing cho Squad: anchor system, locked actor list, locked unit ID list (WBS), locked state enum, catalog status + recipes count, UX goals từ PRD, conventions mode, input paths, sketch reference + drift status.

## 3. Đầu ra yêu cầu

- [ ] **Applicability Gate (§2.0) PASS** — nếu FAIL → đã DỪNG, không sinh artifact
- [ ] Pre-flight pass (R7+R9) — WBS bắt buộc có
- [ ] Inheritance Audit hoàn tất, contracts locked (R8.1-R8.4)
- [ ] Conventions mode xác định (bootstrap/delta)
- [ ] Scaffold `ux_design.md` (+ `ux_conventions.md` nếu bootstrap) + `{intermediate_folder}`
- [ ] Briefing chuẩn bị + User xác nhận

## [GATE] — ⛔ DỪNG TRƯỚC KHI SANG STEP KẾ
- **§2.0 Applicability Gate:** FAIL → đã DỪNG skill (không đọc step-02).
- **§2.4:** Đã trình kết quả và **CHỜ USER XÁC NHẬN**. KHÔNG đọc step-02 trước khi user xác nhận.

**Next:** Read fully and follow `./step-02-executive-summary.md`
