# Step 1: Design System Auditing
> 🎭 Hoá thân **Design System Architect**. Đọc persona đầy đủ: `../agents/design_system_agent.md` trước khi thực thi.
> Không có cổng user ở step này — chạy xong trỏ thẳng step kế. Global rules (U1–U5) ở `../workflow.md`.

## GOAL
Audit L3 UI Controls (Section 2.3) đối chiếu Master Design System để xác định DS updates cần thiết (NEW / MODIFIED / DUPLICATE).

## 1. Load Persona

Adopt role **Design System Architect** tại `../agents/design_system_agent.md`. Persona declare: role + responsibilities + decision policies + output format. Procedural pipeline (orchestration, lookup procedures, decision tree) ở step file này.

## 2. Inputs

- L3 Detailed Design §2.3 (UI Control Matrix, kèm cột `DS candidate` nếu có) — primary source.
- `master_token.json` + `components_metadata.json` (Master DS state — bao gồm `usage`, `recipes[]`).
- `{design_system_root}/_shared/pattern-matcher.md` — **SSoT thuật toán matching** (4-signal scoring + threshold + LLM evaluator prompt).
- `{design_system_root}/_shared/best-practices.md` — công thức WCAG contrast (Stage 3.4 cite).
- `{design_system_root}/_reference/visual-notes.md` (nếu có — Step 3b bootstrap) — style character đối chiếu khi viết `Semantic intent`/`Rationale`.
- `stack-profile.json` — block `ui_library` (lib + version để scan `library_apis/`), block `component_convention.selector_prefix` (cross-screen warning context).
- `{design_system_root}/_reference/figma/figma-ds-map.md` (nếu có — `/ntapp-figma-ingest` đã chạy) — bậc **C-1** của reuse ladder (Stage 3.2). Thiếu file → skip im lặng, ladder chạy C0→C3 như cũ.
- Sibling folders `{design_system_root}/feature_deltas/{other_id}/` — scan in-flight proposals (chưa có `build_report.md`) cho cross-screen consistency check.

## 3. Pipeline

### Stage 3.1: Harvest + Procedural Pattern Match (pattern-matcher.md là SSoT thuật toán)

1. Đọc L3 §2.3 (UI Control Matrix) — extract toàn bộ control entries. Đọc kèm cột `DS candidate` (nếu F3 đã hint từ `component_catalog.md` ở Stage 4a) — hint là **non-binding**: vẫn phải score, nhưng candidate được ưu tiên vào shortlist.
2. Với mỗi control, chạy **matching THEO THỦ TỤC** `{family_root}/_shared/pattern-matcher.md` §5 (Practical workflow — `_shared/` luôn ở family root) đối chiếu **TOÀN BỘ** `components_metadata.json` **của DS đã resolve cho unit** (multi-DS: KHÔNG match chéo sang metadata của DS khác — component DS khác không import được, xem `_shared/ds-resolution.md` nhánh B) — mọi category trừ `layout-primitive` (xử lý riêng theo persona §3.1), mọi status `active`. KHÔNG giới hạn subset (vd chỉ strict-facade) — inventory đầy đủ mới thấy hết reuse candidates:
   - Filter shortlist: cùng category HOẶC tags overlap ≥1 (≤10 candidates).
   - Score 4-signal (§3): intent 0.40 + structural 0.25 + tags 0.20 + a11y 0.15.
   - Output **top-3 candidates với score** cho MỖI control → ghi vào bảng `Reuse Audit` trong proposal (xem §5 Output).
3. Threshold hành động (pattern-matcher §2, override qua `.bmm-config.yaml`):
   - Top-1 **≥ 0.95** → reuse trực tiếp (alias) — KHÔNG proposal.
   - Top-1 **0.70–0.94** → mặc định hướng `[MODIFIED]` (extend existing); tạo `[NEW]` chỉ khi có `Reuse rejection` rationale rõ vì sao không extend được + warning `FUNCTIONAL_DUPLICATE` đi kèm.
   - Top-1 **0.50–0.69** → cân nhắc extend; `[NEW]` phải kèm `Reuse rejection` cho từng candidate ≥0.50.
   - Top-1 **< 0.50** → `[NEW]` hợp lệ (vẫn ghi top-3 vào Reuse Audit để DSO thấy đã xét gì).

### Stage 3.2: 3-Way Branching Decision (schema v1.1 decision tree)

Cho mỗi control sau pattern match, đi theo nhánh A→D theo thứ tự:

**A. Component đã tồn tại + match thuộc tính** → ✅ Match (reuse, KHÔNG propose).

**B. Component đã tồn tại NHƯNG thiếu thuộc tính cần** → check primitive API trước khi tạo variant:

1. Đọc `components_metadata.{component_id}.stack_specific.{fw}.library_wrap.primitive_api` (path tới parsed primitive API JSON).
2. Nếu file tồn tại → đọc theo schema `_shared/library-api-schema.md`. Search prop primitive thoả nhu cầu (vd cần button bo tròn lớn → tìm prop có `tier_hint: radius`).
   - **Tìm thấy** → Propose `[MODIFIED]` với `change_type: EXPOSE_PRIMITIVE_PROP`. Field `Primitive prop ref`: `{lib}@{ver}.{Component}.{prop}`. **KHÔNG tạo variant mới hay CSS custom.**
   - **Không tìm thấy** → Propose `[MODIFIED]` với `change_type: ADD_VARIANT` / `ADD_PROP` (custom prop wrapper). Justify trong Rationale tại sao primitive không cover.
3. Nếu `primitive_api` không tồn tại (parser skip/fail, lib non-TS) → fallback propose `ADD_VARIANT` / `ADD_PROP` trực tiếp. Note trong Rationale: *"primitive API chưa parsed, có thể prop tồn tại sẵn — DSO verify"*.

**C. Component chưa tồn tại** → đi **reuse ladder** theo đúng thứ tự, chỉ rớt xuống bậc dưới khi bậc trên thất bại CÓ lý do ghi lại:

**C-1. Figma-mapped (chỉ khi `figma-ds-map.md` tồn tại)** — designer đã dùng component nào thì đó là bằng chứng mạnh nhất về ý định reuse. Tra `figma-ds-map.md` §[COMPONENT] theo `figma_component` của control (specs ingest đã gắn ở `control_hint[]`, F3 đã chuyển vào cột `DS candidate` §2.3):

| `Status` trong map | Hành động |
|---|---|
| `mapped` (score ≥ 0.95) | **Reuse trực tiếp** — ghi note `Reuse via figma-map: {component_id} (score {s})`. KHÔNG proposal, KHÔNG score lại toàn inventory cho control này |
| `likely` (0.70–0.94) | Đưa candidate lên **đầu shortlist** Stage 3.1, vẫn score đủ 4-signal. Kết quả lệch map → ghi cả hai vào `[REUSE AUDIT]` |
| `unmapped` (< 0.70) hoặc không có entry | Không dùng bậc này → xuống C0 |

Giới hạn có chủ ý của bậc này: score trong `figma-ds-map.md` **thiếu signal a11y** (Figma không cung cấp) nên trần điểm thấp hơn score của bạn. Vì vậy `mapped` là hint **đủ mạnh để reuse** nhưng KHÔNG được dùng để biện minh cho `[NEW]` — mọi `[NEW]` vẫn phải đi qua C0-C3 và có `Reuse rejection`.

**C0. Project composite/recipe** — check `components_metadata.json` `recipes[]` (+ `component_catalog.md` §Recipes): control cluster trong wireframe có khớp recipe đã quan sát không (vd hàng search + dropdown + button ↔ recipe `filter-bar-row`)? Khớp → KHÔNG tạo NEW composite; ghi note `Reuse via recipe: {name}` — schema Stage 3 compose từ member components sẵn có. Đây là bậc chặn lỗi "màn hình mới có filter nhưng không reuse filter bar + input + dropdown đã có".

**C1. Project atom + variant** — atom gần nhất (score 0.50-0.69) extend được qua `[MODIFIED]` ADD_VARIANT/EXPOSE_PRIMITIVE_PROP? → ưu tiên hơn NEW.

**C2. Library primitive wrap** — chỉ khi C0/C1 fail:
1. Đọc `stack-profile.json.ui_library.name` + `version`.
2. Scan `{design_system_root}/library_apis/{lib}@{ver}/` xem có primitive match semantic không (vd cần "alert banner" → check antd `Alert`, primeng `p-message`, mui `Alert`).
3. **Tìm thấy primitive phù hợp** → Propose `[NEW]` với field `Library primitive: {lib}.{Component}`. Scaffold (ở `/ntapp-ds-build-component`) sẽ wrap primitive + forward đầy đủ prop, style theo sibling exemplar.

**C3. Build-from-scratch** — không có primitive phù hợp → Propose `[NEW]` với `Library primitive: none`.

Mọi `[NEW]` (C2/C3) bắt buộc field `Reuse rejection:` — vì sao C-1 (Figma map nói gì, nếu có), C0 (recipe nào đã xét) và C1 (candidate ≥0.50 nào đã xét) không dùng được.

**D. Trùng lặp chức năng / Ontology** → emit warning `FUNCTIONAL_DUPLICATE` vào `[WARNINGS]` section.

### Stage 3.3: Cross-screen Consistency Check (in-flight scan)

Sau khi build proposal items, scan sibling proposals đang in-flight:

1. Iterate `{design_system_root}/feature_deltas/{other_id}/` — **CHỈ trong DS root đã resolve cho unit** (multi-DS: proposal của DS khác là hệ style độc lập — so chéo sẽ ra `STYLE_FRAGMENTATION` giả). Chỉ chọn folder **chưa có `build_report.md`** (proposal chưa qua `/ntapp-ds-build-component`). Folder đã có `build_report.md` = đã apply vào Master DS, drift sẽ surface qua audit lần sau.
2. Cho mỗi `proposed_ds_updates.md` in-flight, parse `[NEW]` + `[MODIFIED]` entries.
3. Nếu cùng component class (vd `app-button` — prefix theo `stack-profile.component_convention.selector_prefix`) bị propose `[NEW]` variant hoặc `[MODIFIED]` với style spec khác nhau ở 2+ proposals → emit warning `STYLE_FRAGMENTATION`. DSO quyết định consolidate.

### Stage 3.4: Contrast pre-check (producer của `WCAG_CONTRAST_FAIL`)

Với **mọi cặp fg/bg** xuất hiện trong proposal — (a) `[NEW]` TOKEN color tạo cặp nền/chữ (vd `*.tag.bg` + `*.tag.text`), (b) `[NEW]`/`[MODIFIED]` COMPONENT có variant/state khai báo cặp fg+bg trong `Tokens`, (c) cặp resolve từ token sẵn có mà item reference:

1. Resolve cả 2 vế sang hex qua `master_token.json` (+ giá trị đang propose nếu token mới).
2. Tính contrast ratio theo công thức WCAG **owned bởi** `_shared/best-practices.md` (accessibility section) — KHÔNG restate công thức ở đây.
3. Ratio < **4.5:1** (normal text) / < **3:1** (large text + UI component) → emit entry `[WARNINGS]` type `WCAG_CONTRAST_FAIL` (severity high): pair, ratio đo được, ngưỡng cần, suggested fix (token thay thế gần nhất đạt chuẩn). Consumer `/ntapp-ds-build-component` warning-blocker **block** cho tới khi DSO resolve.
4. Không resolve được hex (reference orphan) → note `UNRESOLVED_PAIR` trong Rationale — Step 4 (A5) sẽ chặn tiếp ở tầng schema.

> Đây là producer duy nhất của `WCAG_CONTRAST_FAIL` ở Stage 4b proposal-time. Step 4 (aesthetic critique A5) là tầng thứ 2, check trên schema đã compose. Cả 2 tầng cùng cite ngưỡng từ `best-practices.md`.

### Decision Flow tóm tắt

```
For each UI Control trong L3 §2.3:
  ├── Score toàn bộ inventory (pattern-matcher §5, top-3 → Reuse Audit table)
  │   ├── ≥0.95 → reuse (no proposal)
  │   ├── 0.70-0.94 → [MODIFIED] extend (NEW cần Reuse rejection + FUNCTIONAL_DUPLICATE warning)
  │   │   ├── library_wrap có? → đọc primitive_api
  │   │   │   ├── primitive có prop tương đương → [MODIFIED] EXPOSE_PRIMITIVE_PROP
  │   │   │   └── primitive không có → [MODIFIED] ADD_VARIANT / ADD_PROP
  │   │   └── library_wrap không → [MODIFIED] ADD_VARIANT / ADD_PROP
  │   └── <0.50 (hoặc 0.50-0.69 có Reuse rejection) → reuse ladder C-1→C3:
  │       ├── C-1 figma-ds-map status=mapped → reuse trực tiếp (no proposal, no re-score)
  │       ├── C0 recipe/composite project khớp cluster → compose từ member sẵn có (no NEW)
  │       ├── C1 atom + variant extend được → [MODIFIED]
  │       ├── C2 library_apis/ có primitive → [NEW] wrap + Reuse rejection
  │       └── C3 không có primitive → [NEW] from-scratch + Reuse rejection
  └── Sau khi build proposal items:
      ├── Contrast pre-check mọi cặp fg/bg → [WARNINGS] WCAG_CONTRAST_FAIL nếu < AA
      └── Cross-screen scan in-flight → [WARNINGS] STYLE_FRAGMENTATION nếu drift
```

## 4. Decision Points

- **`primitive_api` file missing/parse-fail** → fallback Stage 3.2 B path 3 (propose ADD_VARIANT/ADD_PROP với note DSO verify). KHÔNG STOP.
- **`library_apis/{lib}@{ver}/` empty hoặc missing** → fallback Stage 3.2 C path 4 (propose NEW với `Library primitive: none`). KHÔNG STOP.
- **In-flight proposal conflict** (cùng component class spec khác) → emit warning `STYLE_FRAGMENTATION`, tiếp tục build proposal. DSO consolidate tại Step 2 HITL.
- **L3 §2.3 trống** (control matrix chưa fill) → STOP: *"L3 §2.3 UI Control Matrix trống. Quay lại Stage 4a (`/ntapp-feature-design`) fill control matrix trước."*

## 5. Output

- `{design_system_root}/feature_deltas/{id}/proposed_ds_updates.md` — path khớp consumer `/ntapp-ds-build-component`. KHÔNG ghi vào cwd.
- File follow schema `{design_system_root}/_shared/proposal-schema.md` v1.2 (3 section bắt buộc: `[NEW]`, `[MODIFIED]`, `[WARNINGS]` + dòng `[SUMMARY] tokens=N, components=M` + section `[REUSE AUDIT]`).
- **Section `[REUSE AUDIT]` (bắt buộc từ v1.2):** bảng per-control `control_id | top-3 candidates (score) | quyết định (reuse/MODIFIED/NEW-C2/NEW-C3/recipe) | Reuse rejection (nếu NEW)`. Đây là bằng chứng "đã xét reuse" cho DSO — proposal `[NEW]` mà không có hàng tương ứng trong bảng này = invalid.
- Format spec chi tiết (front matter, H3 per item, field list per TYPE) ở persona §4.

**Next:** Read fully and follow `./step-02-hitl-review.md`
