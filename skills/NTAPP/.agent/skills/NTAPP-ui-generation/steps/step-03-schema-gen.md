# Step 3: UI Schema Construction
> 🎭 Hoá thân **UI Semantic Schema Agent**. Đọc persona đầy đủ: `../agents/ui_schema_agent.md` trước khi thực thi.
> ⛔ Chứa HALT gate (BLOCKING drift, §3/§4) — chỉ đọc step kế SAU KHI qua [GATE] ở cuối file. Global rules (U1–U5) ở `../workflow.md`.

## GOAL
Construct UI Semantic Schema (FSM + Data Mapping) dựa trên L3 design và approved Design System, với explicit L3↔L2 drift detection trước mapping.

## 1. Load Persona

Adopt role **UI Semantic Schema Agent** tại `../agents/ui_schema_agent.md`. Persona declare: role + responsibilities + decision policies + output format.

## 2. Inputs

- **L3 Detailed Design:** §2.2 (Wireframe Blueprint + **Icon Legend table + Layout Groups table** dưới wireframe), §3.2 (Logic Matrix), §4.1 (UI↔DB Mapping), §4.2 (Integration Error Codes), §6 (Interaction Sync Matrix).
- **Approved DS files:** `master_token.json` và `components_metadata.json` (updated ở Step 2). Category `layout-primitive` cung cấp 10 canonical primitives + DSO-added — consume cho Layout Parsing phase.
- **Stack profile:** `stack-profile.json` — block `icon_library` (v1.2+) cho Icon Binding, block `layout_library` (v1.3+) cho Layout Parsing.
- **L2 Technical Specification — load NOW (deferred từ INITIALIZATION):** §12 (Interface Contracts), specifically §12.1 (Schema Spec Proto/JSON), §12.2 (Field Deep-Dive & Validation), §12.3 (Error Contract & Mapping). Treat L2 §12 là **canonical SSoT** cho data contracts; L3 §4.x là UI-side view.
  - **Skip nếu:** unit là widget pure presentational (không có data binding) — không có L2 contract để đối soát.

## 3. Pipeline

Execute Phase A trước Phase B. Phase A drift checks PURE từ docs (L3 + L2) → clear trước khi build schema. Phase B icon/layout drift surface khi parse §2.2 wireframe — cùng severity rubric, cùng HITL gate (`drift_report.md`), nhưng phase khác nhau.

### Phase A — Data Contract Drift Detection (L3↔L2)

Chạy data-contract drift checks (L3 §4.x ↔ L2 §12.x) trước khi Phase B bắt đầu. Phân loại mỗi finding theo Drift Rubric dưới — rubric này là **SSoT** cho toàn skill, bao gồm cả drift codes phát sinh trong Phase B (icon, layout).

#### Drift Rubric

**BLOCKING (phải reconcile trước Phase B — UI Schema sẽ sai nếu không fix):**
- L3 §4.1 declare API Param KHÔNG có trong L2 §12.1 schema.
- L3 §4.1 field type contradicts L2 §12.1/§12.2 type hoặc hard constraint (vd: L3 nói `string`, L2 nói `int32`).
- L3 §4.2 error code KHÔNG defined trong L2 §12.3 (hoặc ngược lại, cho codes UI phải surface).
- L3 §3.2 logic branch reference field/state absent khỏi L2 contract.
- Validation rule conflict thay đổi UI behavior (vd: L2 max=10, L3 max=100).
- **`LAYOUT_PRIMITIVE_UNKNOWN`** — L3 §2.2 Layout Groups table reference primitive name không có trong `components_metadata.json` category `layout-primitive` (10 canonical + DSO-added). UI Schema không emit `layout` tree đến khi DSO add primitive (qua `[NEW]` proposal `category: layout-primitive`) hoặc rename về primitive đã có.
- **`LAYOUT_CONTROL_UNRESOLVED`** — Layout Groups Members reference `control_id` không khớp `data_bindings.controls[].id` từ §2.3 (UI Control Matrix). Layout tree không thể bind.
- **`LAYOUT_GROUP_UNRESOLVED`** — Layout Groups Members reference nested `Group ID` không có entry trong table. Tree composition broken.

**NON-BLOCKING (record vào `_drift_notes`, tiếp tục):**
- L2 §12.1 có fields KHÔNG consume bởi UI (intentional UI subset — informational only).
- L2 §12.4 example payload optional fields không surface trong L3.
- L2 §12.2 validation rule **stricter** hơn L3 note mà không thay đổi UI affordance (L2 wins silently; record cho traceability).
- Naming variance khi mapping unambiguous (record canonical L2 name vào schema).
- **`LAYOUT_GROUPS_MISSING`** — L3 §2.2 không có Layout Groups table dù wireframe có ≥2 sibling controls. ui_schema_agent fallback root `Stack(column, gap=md)` flat list theo wireframe order. HITL prompt khuyến nghị F3 bổ sung table.
- **`LAYOUT_PROP_INVALID`** — Layout Groups Props value không khớp primitive's `inputs` schema (vd `align=invalidvalue`). Apply default + record. Miễn trừ surface/sizing props (Stage 4.5 bước 4).
- **`LAYOUT_PROP_AMBIGUOUS`** — một khoá khai hai lần trong cùng `Props` cell (`align=center, align=stretch`). DD viết theo format cũ gộp 2 trục. Lấy giá trị đầu, note tên group, KHÔNG đoán trục.
- **`SURFACE_PROPS_DROPPED`** — `figma_status: mapped` + `figma-ds-map.md` §[SURFACE] có `radius`/`border` cho group mà DD §2.2 không khai. Record tên group vào HITL prompt; KHÔNG tự bù (DD là SSoT của §2.2).
- **`LAYOUT_LIBRARY_MISSING`** — `stack-profile.json` legacy không có `layout_library` block. Fallback giả định `css-vanilla` + `generated-component`. Khuyến nghị DSO chạy `/ntapp-ds-bootstrap --refresh-stack`.
- **`ICON_UNRESOLVED`** — Icon Legend semantic name không match trong `library_apis/{icon_library}@{ver}/_index.json`. HITL fallback chọn closest hoặc enter manual.

#### Action khi gặp BLOCKING drift

1. **STOP** pipeline trước Phase B.
2. **Emit** `drift_report.md` vào working directory. Structure bắt buộc:
   ```markdown
   # L3↔L2 Drift Report — {id}

   ## [BLOCKING]
   - **Item N**
     - L3 ref: §4.1 row "{field}"
     - L2 ref: §12.1 message "{name}"
     - Conflict: {one-line description}
     - Suggested resolution: {update L3 | update L2}

   ## [NON-BLOCKING]
   - (same shape, included for full visibility)
   ```
3. **Present** report content cho user với USER MENU (xem §4 Decision Points).
4. **KHÔNG** proceed Phase B cho đến khi reconciliation được confirm.

> [!IMPORTANT]
> **HALT on BLOCKING drift.** KHÔNG auto-resolve bằng cách silently prefer 1 source. BLOCKING drift nghĩa là contract ambiguous và human owner phải quyết. Auto-resolution risk ship UI Schema contradicts backend.

#### Action khi chỉ có NON-BLOCKING drift

Continue Phase B. Include NON-BLOCKING drift entries như `_drift_notes` array trong final schema output cho downstream traceability.

---

### Phase B — Schema Construction

Execute 6 stages tuần tự. Apply Drift Rubric (Phase A) tại mỗi stage emit drift codes. Output format spec ở `../agents/ui_schema_agent.md` §4.

#### Stage 4.1: ID Binding
Lấy `id` (workflow Bước 1) và `id_type` (Bước 2) làm key gốc cho schema. Set `id`, `id_type`, `component_name` (kebab-case selector từ Master DS).

#### Stage 4.2: FSM Construction
- Đọc L3 §3.2 (Logic Matrix) + §6 (Interaction Sync Matrix).
- Convert mọi rẽ nhánh logic thành state rõ ràng (vd `IDLE`, `UPLOADING`, `ERROR_TIMEOUT`).
- **Logic Gap check** (per persona §2 Disconfirming Evidence): mỗi branch trong §3.2 phải có UI state tương ứng trong §6. Gap → HALT với `"Logic Gap Detected"`, KHÔNG tự đoán UI.

#### Stage 4.3: Component Composition
Tại mỗi state FSM, declare danh sách `selectors` render. Mỗi selector phải khớp 1 component đã approved trong `components_metadata.json` (post Step 2). Không được self-create component.

#### Stage 4.4: Icon Binding
**Skip nếu** Icon Legend (L3 §2.2) trống. **Required** nếu có ≥1 emoji (loại trừ entry prefix `content:` — đó là UI content thật, giữ emoji nguyên trong code).

1. Đọc bảng **Icon Legend** dưới wireframe L3 §2.2. Schema: `| Emoji | Icon name | Mục đích |`.
2. Đọc `stack-profile.json.icon_library` (block v1.2+). Extract `name`, `version`, `import_style`, `component_pattern`, `available_icons_ref`.
3. Với mỗi entry trong legend (skip `content:` prefix):
   - Resolve semantic name → component name của library:
     - Đọc `available_icons_ref` (`library_apis/{lib}@{ver}/_index.json`) nếu tồn tại — tìm closest match (exact, hoặc fuzzy với synonym chuẩn: `search`→`Search`/`SearchOutlined`/`Magnifier`, `close`→`X`/`Close`/`Cancel`, ...).
     - Apply `component_pattern` template: vd `<{name}Outlined />` + `{name}=Search` → `<SearchOutlined />`; `pi pi-{name}` + `{name}=search` → `pi pi-search`.
   - Không match được → emit `ICON_UNRESOLVED` (NON-BLOCKING), HITL fallback prompt: *"Wireframe §2.2 dùng icon `{semantic-name}` (emoji `{emoji}`) nhưng không match trong `{icon_library.name}@{version}`. Available closest: [top 3]. Chọn 1 hoặc nhập tên component cụ thể."*
4. Build `icon_bindings` object: key = `Icon name` từ legend, value = `{ library, component, import_path, usage_context, render }`.

#### Stage 4.5: Layout Parsing
**Skip nếu** Layout Groups table (L3 §2.2) trống VÀ wireframe có <2 sibling controls. **Required** nếu ≥2 sibling controls (table có hoặc miss).

1. Đọc bảng **Layout Groups** dưới wireframe L3 §2.2. Schema: `| Group ID | Type | Members | Props |`.
   - `Group ID`: convention `R1` cho root, `G1`/`G2`/... nested group, `F1`/`F2`/... FormField (convention đọc người, parser không enforce).
   - `Type`: primitive name PascalCase, ∈ `components_metadata.json` category `layout-primitive`.
   - `Members`: comma-separated; mỗi entry hoặc là `control_id` (khớp `data_bindings.controls[].id`) hoặc nested `Group ID` (recursive).
   - `Props`: comma-separated `key=value`. Token refs giữ nguyên (`gap=md`); literal lowercase enum (`direction=row`).
   - **`Members` có thể mang hậu tố sizing** — `Left(fill)`, `text_title(hug)`. Strip hậu tố khi resolve `control_id`/`Group ID`, nhưng **giữ giá trị** vào `props.sizing_children` (array cùng thứ tự Members) — Stage 5 cần nó để dựng flex đúng.
   - **3 khoá Props đặc biệt** (surface, hợp lệ trên mọi primitive — spec ở `../agents/ui_schema_agent.md` §4): `radius=<token>` → `props.radius`; `elevation=<token>` → `props.elevation`; `border=<style>-<sides>` (vd `solid-top`, `none`) → `props.border = { style, sides }`, thêm `width` nếu Props có `border_width=`. **KHÔNG** chạy qua validate `inputs` của primitive (xem Stage 4.5 bước 4).
   - **`effective_align=center-full-width`** → `props.justify = "start"` **và** `props.center_full_width = true`. Đây là idiom "3 cột cân bằng" (2 member `(fill)` kẹp 1 member `hug`): Figma không có thuộc tính nào ghi "canh giữa", nó là hệ quả của sizing — bỏ khoá này thì Stage 5 dựng canh trái. Biến thể `push-start`/`push-end` → `props.justify = "between"`.
2. Đọc `stack-profile.json.layout_library` (block v1.3+). Extract `name`, `strategy`, `primitive_mapping`.
3. Build `layout` tree:
   - Root = group ID `R1` (hoặc group đầu tiên nếu không declare `R1`).
   - Walk Members:
     - Match control_id → leaf `{ "ref": "<control_id>" }`.
     - Match nested Group ID → recurse → `{ "type": "<primitive>", "props": {...}, "children": [...] }`.
   - FormField special: Type=FormField + Members=1 control → `{ "type": "FormField", "props": {...}, "child": { "ref": "..." } }` (singular `child`).
4. **Validate** (drift codes per Drift Rubric):
   - `Type` ∉ inventory → `LAYOUT_PRIMITIVE_UNKNOWN` (BLOCKING). Entry shape: `{ type, group_id, primitive, suggested }`.
   - `control_id` ∉ `data_bindings.controls[].id` → `LAYOUT_CONTROL_UNRESOLVED` (BLOCKING).
   - Nested `Group ID` ∉ table → `LAYOUT_GROUP_UNRESOLVED` (BLOCKING).
   - Prop value ∉ primitive `inputs` schema → `LAYOUT_PROP_INVALID` (NON-BLOCKING, apply default). **Miễn trừ:** `radius` / `border` / `elevation` / `sizing_children` / `center_full_width` — surface + sizing props hợp lệ trên mọi primitive, không cần khai trong `inputs`.
   - **Cùng một khoá xuất hiện hai lần trong một `Props` cell** (vd `align=center, align=stretch`) → `LAYOUT_PROP_AMBIGUOUS` (NON-BLOCKING nhưng **ghi vào `_drift_notes` và HITL prompt**). Đây là dấu hiệu DD được viết theo format cũ gộp 2 trục vào một tên khoá: `justify=` (trục chính) và `align=` (trục vuông góc) phải là hai khoá riêng. Resolution: lấy giá trị **đầu tiên** cho `align`, giá trị thứ hai bỏ + note *"§2.2 group {id}: `align=` khai hai lần — không suy được trục nào; kiểm lại DD, có thể cần chạy lại `/ntapp-figma-ingest` để lấy Props format mới"*. KHÔNG đoán.
   - `figma_status: mapped` (đọc `figma-manifest.yaml`) mà group **có** `radius`/`border` trong `figma-ds-map.md` §[SURFACE] nhưng DD §2.2 **không** khai → `SURFACE_PROPS_DROPPED` (NON-BLOCKING) + note tên group. Không tự bù từ §[SURFACE] — DD là SSoT của §2.2, việc của bước này là **nêu tên chỗ mất**, để 4a sửa chứ không phải 4b vá.
5. **Fallback paths:**
   - **Layout Groups table missing** + ≥2 sibling controls: emit `LAYOUT_GROUPS_MISSING` (NON-BLOCKING). Wrap toàn bộ controls trong root `{ "type": "Stack", "props": { "direction": "column", "gap": "md" }, "children": [...] }` — flat list theo wireframe order. HITL prompt log: *"Wireframe §2.2 không có Layout Groups table. Fallback Stack(column, gap=md) flat. Bổ sung table nếu intent khác."*
   - **`stack-profile.layout_library` missing** (legacy v1.0-v1.2): emit `LAYOUT_LIBRARY_MISSING` (NON-BLOCKING). Fallback `{ name: "css-vanilla", strategy: "generated-component" }`. Khuyến nghị DSO chạy `/ntapp-ds-bootstrap --refresh-stack`.

#### Stage 4.6: Data Contract Mapping
**Pre-condition:** Phase A drift clear (BLOCKING reconciled hoặc chỉ NON-BLOCKING) + Stage 4.5 không BLOCKING (control IDs đã layout).

1. Map L3 §4.1 (UI↔DB Mapping) + L2 §12.1/§12.2 → `data_bindings.inputs` và `data_bindings.outputs`. Mỗi field declare: `name`, `type`, `cardinality`, `validation`, `binding_mode: input|output|two-way`.
2. Output **framework-neutral** — KHÔNG dùng tên reactive primitive cụ thể (Signal/Observable/ref/...). Stage 5 dev agent map sang target framework qua `stack-profile.json`.
3. **L2 §12 wins khi overlap** với L3 §4.x (per persona §2 Source Precedence).
4. NON-BLOCKING drift entries → inject vào `_drift_notes` (mỗi entry `{ l3_ref, l2_ref, type, resolution_applied }`).

#### Stage 4.7: Visual Intent Capture (optional, additive)

**Mục đích:** capture quyết định thẩm mỹ dưới dạng **token-resolved reference** vào root key `visual_intent` (spec ở `../agents/ui_schema_agent.md` §4) — biến hierarchy/rhythm/density từ implicit thành explicit & review được. Đây là **input cho Step 4** (Aesthetic Self-Critique). Capture luôn chạy (cheap, additive); việc **chấm** mới gated bởi flag `aesthetic_critique`.

**Skip nếu:** unit là widget pure presentational HOẶC layout có <2 sibling control (không có hierarchy/rhythm thật để khai báo) — KHÔNG sinh `visual_intent`.

1. **`density`** — suy từ số control + grouping của L3 §2.2/§2.3: form dày field → `compact`; trang nội dung thoáng → `spacious`; mặc định `comfortable`. Chỉ chọn 1 trong 3 enum (map sang spacing scale, KHÔNG hardcode).
2. **`vertical_rhythm`** — chọn **token reference** spacing scale làm nhịp dọc nhất quán giữa section (vd `tokens.spacing.scale.4`). Lấy step nhịp khớp với `gap` chủ đạo trong `layout` tree. KHÔNG đẻ giá trị mới.
3. **`emphasis_order`** — xếp hạng visual weight từ L3 §2.3 control intent: control `intent: primary` → `level: "primary"` (**đúng 1**); `secondary` → `secondary`; còn lại `tertiary`. `ref` trỏ `data_bindings.controls[].id`.
4. **`grouping`** — với mỗi section divider / callout trong L3 §2.2 (Layout Groups có separation intent) → `{ group_id, separation }` với `separation` là token reference spacing (vd `tokens.spacing.section_gap`). `group_id` trỏ `layout` group ID.
5. **`responsive_intent`** — nếu L3 §2.2 note breakpoint behavior (stack/reflow) → `{ stack_below: "tokens.breakpoint.md" }` (token ref). Bỏ qua nếu L3 không khai báo.
6. **`_rubric_score`** — để `null`. Step 4 điền (`PASS`/`FAIL`). Agent 2 KHÔNG tự chấm.

> **Ràng buộc:** mọi value là **token path reference** (no hardcode, Rule 4). Capture = *chọn token đúng cho nhịp thị giác từ tín hiệu L3*, KHÔNG đẻ giá trị. Thiếu token group "visual scale" tường minh (density band, section_gap) → vẫn capture bằng spacing scale sẵn có; Step 4 sẽ emit gap note nếu cần `[NEW]`.

## 4. Decision Points

### USER MENU (drift reconciliation — khi gặp BLOCKING drift Phase A hoặc Phase B)

- **[L3]** L3 đúng → user update L2 contract, sau đó re-run Step 3.
- **[L2]** L2 đúng → user update L3 §4.1/§4.2, sau đó re-run Step 3.
- **[S]** Stop → abort workflow.

> Không có override option. BLOCKING drift = contract ambiguous; safe paths duy nhất là fix source of truth (L3 hoặc L2) hoặc stop. Proceed với one-off precedence sẽ silently ship UI Schema contradicts backend.

### Auxiliary STOPs

- **Logic Gap Detected** (Stage 4.2) — branch §3.2 không có UI state §6 → HALT, hint quay lại L3 fill §6.
- **Component không match** `components_metadata.json` post-Step 2 (Stage 4.3) → STOP, hint quay lại Step 1/2 add proposal `[NEW]` cho component thiếu.
- **L2 path missing** khi unit có data binding (Pre-flight 5 / Bước 3 Tier 2) → STOP, đã document workflow.md Pre-conditions.

## 5. Output

- **`ui_schema_{id}.json`** — root keys bắt buộc: `id`, `id_type`, `component_name`, `data_bindings`, `state_machine`.
  - Root keys tuỳ chọn: `_drift_notes` (NON-BLOCKING drift), `icon_bindings` (nếu wireframe có emoji ≠ `content:`), `layout` (composition tree, bắt buộc khi screen/widget có ≥2 sibling controls), `visual_intent` (Stage 4.7 capture — hierarchy/rhythm/density token-resolved; skip nếu pure presentational / <2 sibling control).
  - File path: `{ui_schema_root}/ui_schema_{id}.json` (resolve qua `.bmm-config.yaml`).
  - Naming convention này khớp pre-commit Rule 6 (file `ui_schema_{screen_id|widget_id}.json` phải tồn tại trước khi commit UI code).
- **`drift_report.md`** — chỉ khi BLOCKING drift trigger HITL (bao gồm data contract drift + `LAYOUT_PRIMITIVE_UNKNOWN` / `LAYOUT_CONTROL_UNRESOLVED` / `LAYOUT_GROUP_UNRESOLVED`). Schema JSON KHÔNG generated cho đến khi reconciliation complete.

## NEXT

UI Semantic Schema sẵn sàng cho frontend implementation. Output là **framework-neutral** — Stage 5 dev agent map sang target framework (Angular Signals/Observables, React hooks, Vue refs, Solid signals, ...) dựa trên `stack-profile.json`.

Downstream (không thuộc forward chain):
- Nếu `proposed_ds_updates.md` có `[NEW]` items → trigger `/ntapp-ds-build-component` (Stage 4b hard gate) trước khi merge feature code.
- Stage 4c (`/bmad-create-story`) consume `ui_schema_{id}.json` làm input cho story scoping.

## [GATE: BLOCKING DRIFT + FLAG] — ⛔ kiểm trước khi tiếp
> - BLOCKING drift (Phase A/B) chưa reconcile → HALT tại drift HITL (§3/§4), KHÔNG có forward edge cho tới khi resolve.
> - Step 4 (Aesthetic Self-Critique) gated bởi flag `aesthetic_critique` (default **ON**, opt-out):
>   - flag ON (default) VÀ unit có bố cục đáng kể → chấm `visual_intent` đã capture theo `_shared/aesthetic-rubric.md`, self-correct ≤3 vòng, điền `visual_intent._rubric_score` (chi tiết ở step-04 §0).
>   - flag OFF (user/config tắt tường minh) / pure presentational → `ui_schema_{id}.json` là **output cuối** (TERMINAL ở đây).

**Next:** Mặc định (flag ON + bố cục đáng kể) → Read fully and follow `./step-04-aesthetic-critique.md`. Flag OFF / pure presentational → DỪNG (schema là output cuối).
