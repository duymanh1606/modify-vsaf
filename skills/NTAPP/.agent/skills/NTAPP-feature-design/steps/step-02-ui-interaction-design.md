# STEP 02: UI & INTERACTION DESIGN

> **Acting as:** [Agent F3 — UI Specialist](../agents/agent_f3_ui_specialist.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R5 (Consistency naming), R10 (Inheritance từ UX Spec).

## 0. Skip Condition (theo Execution Matrix)

| `id_type` | Action |
|---|---|
| `feature_id` (BE) | **SKIP** — BE feature không có UI. F0 SKIP action (không tạo `f3_ui_part.md`), tiếp tục **Next**. |
| `screen_id` (FE) | ✅ RUN — design wireframe + UI controls cho cả screen. |
| `widget_id` (FE) | ✅ RUN — design widget component spec (input/output/state/style). |

## 1. Mục tiêu
Thiết kế kiến trúc thông tin, bản vẽ khung xương (Blueprint) và đặc tả chi tiết các thành phần giao diện cho đơn vị (screen hoặc widget) tại Section 2.

## 0b. Mode: AUTHOR vs TRANSCRIBE (quyết định TRƯỚC §2)

Có Figma vẽ trước hay không đổi **bản chất công việc** của F3: sáng tác bố cục, hay chép lại trung thực bố cục đã có.

Đọc `{design_system_root}/_reference/figma/figma-manifest.yaml` (thiếu file → AUTHOR mode, bỏ qua toàn bộ mục này):

| `units[].figma_status` của unit này | Mode | Nghĩa |
|---|---|---|
| `mapped` | **TRANSCRIBE** | Figma là SSoT của layout → chép trung thực, mọi chỗ lệch phải ghi lý do |
| `missing` / `stale` / `ignored` / không có entry | **AUTHOR** | Như cũ — F3 tự sáng tác (§2 bên dưới không đổi) |
| `not_in_scope` | **AUTHOR + WARN** | Lần ingest gần nhất **không xét** unit này (scope hẹp) → không có spec/frame để chép. Author mode, nhưng ghi WARN: *"unit có thể đã có Figma — chạy `/ntapp-figma-ingest --feature <tên>` để phủ nó rồi làm lại DD nếu muốn transcribe"*. KHÔNG block |

**TRANSCRIBE mode — 6 nghĩa vụ thêm:**

1. **Load nguồn Figma** (thay vì tự sáng tác bố cục):
   - `_reference/figma/frames/{id}.png` + mỗi `states[].frame` — **MỞ TỪNG FILE bằng tool đọc file (vision), xem tất cả state, không chỉ default.** Đây là nghĩa vụ *xem*, không phải nghĩa vụ *biết đường dẫn*: liệt kê tên file rồi đi tiếp là vi phạm, và nghĩa vụ 6 dưới đây tồn tại để chuyện đó không đi lọt.
   - `_reference/figma/specs/{id}.json` — `layout_groups_hint[]`, **`surface[]`**, **`geometry[]`**, `control_hint[]`, `icon_candidates[]`, `copy[]`.
   - `_reference/figma/figma-ds-map.md` **§[SURFACE]** — ánh xạ `radius_role`/`border`/`elevation` sang **tên token**. Đây là chỗ lấy giá trị điền vào Props, không phải tự chọn token.
   - ⛔ **CẤM đọc khoá `raw`** trong specs (px/hex thô, cờ `raw_only: true`). Đó là input của step-05 ingest để snap token, không phải input của bạn. Đọc rồi viết vào §2 sẽ đẩy giá trị hardcode xuống Stage 5 và pre-commit Rule 4 sẽ block.
     - **Lệnh cấm này KHÔNG áp cho tầng ngoài.** `surface[]` (`radius_role`, `border.style`, `border.sides`, `elevation`), `geometry[].box`, và `sizing`/`justify`/`align`/`effective_align` trong `layout_groups_hint[]` là **ý định thiết kế**, bạn PHẢI đọc và PHẢI mang vào §2.2. Cấm là cấm *giá trị đo được*, không phải *ý định*.
2. **§2.2 Layout Groups = verify, không sáng tác.** `figma_ingest_report.md` §Layout Groups hint đã render sẵn bảng 4 cột đúng format. Verify từng dòng rồi dán. Dòng `confidence: LOW`/`MEDIUM` (`Grid` suy luận, hoặc `Box` suy từ `geometry[]` vì frame không có Auto Layout) → tự thẩm định lại **từ ảnh**.
   - **Giữ nguyên 3 nhóm khoá khi dán, đừng lược cho gọn:** `sizing=` + hậu tố `(fill)` ở cột Members (mất nó là mất canh giữa kiểu 3-cột-cân-bằng); `justify=` và `align=` là **hai trục khác nhau** (thấy `align=` hai lần trong một cell → dữ liệu lỗi, báo lại chứ đừng đoán); `radius=` / `border=` / `elevation=`.
   - `effective_align=center-full-width` nghĩa là **phần tử giữa canh giữa theo toàn bề ngang**, kể cả khi `justify=start`. Dán cả khoá này — Stage 4b đọc nó để dựng `layout` tree, và Stage 5 không có nguồn nào khác để biết.
   - **ASCII không chở được radius/viền/tỉ lệ.** Bản vẽ chỉ định vị; ba thứ đó sống ở cột `Props` của Layout Groups và ở §2.5. Hộp `┌──┐` trông y hệt nhau cho thẻ-có-viền và thẻ-chỉ-có-bóng, nên đừng dùng nó để truyền đạt "có viền".
3. **§2.3 lấy từ `control_hint[]`.** `control_id` giữ nguyên nếu đã semantic; `<TODO: F3 đặt tên>` → bạn đặt. `figma_component` → điền cột `DS candidate` **qua `figma-ds-map.md`** (status `mapped`/`likely` → dùng tên DS component; `unmapped` → `-`). Icon Legend lấy từ `icon_candidates[]`. Bảng Validation lấy `copy[]` `role: error` — **nguyên văn từng ký tự**, không dịch, không sửa chính tả.
4. **§2.5 Deviation log (BẮT BUỘC ở mode này).** Mọi chỗ §2 **khác** Figma phải có 1 dòng: `{control/group} | Figma làm gì | DD làm gì | Lý do`. Lý do hợp lệ đúng 3 loại — **thứ tự thắng khi xung đột**:

   | Xung đột | Bên thắng |
   |---|---|
   | Figma dùng màu/spacing/component không có trong Master DS | **Master DS** — Figma lệch đi qua `[NEW]`/`[MODIFIED]` ở Stage 4b, không hardcode |
   | Figma vẽ field/data không có trong contract | **DD §3 + Module 0** — escalate, KHÔNG tự thêm field |
   | Figma dùng error message / status label khác conventions | **`ux_conventions.md`** (project singleton) |
   | Layout, hierarchy, density, thứ tự, copy | **Figma** |

   Deviation log rỗng mà wireframe khác Figma rõ ràng = lỗi transcribe, không phải "sạch".
5. **Ghi `figma_ref` vào §1** (assembly step-07 giữ nguyên dòng này): `` `{file_key}` / node `{node_id}` / version `{figma_version}` / checksum `{checksum}` ``. Đây là nguồn so sánh của Hook 3 — thiếu dòng này thì drift gate vô hiệu và designer sửa Figma sẽ đi vào build âm thầm.
6. **§2.5 phải mở đầu bằng bảng `[FRAMES VIEWED]`** — bằng chứng đã xem ảnh, 1 dòng/state:

   ```markdown
   **[FRAMES VIEWED]**
   | State | Frame | Quan sát thị giác (KHÔNG suy được từ JSON) |
   | :--- | :--- | :--- |
   | default | `frames/{id}.png` | Cụm nhận diện canh GIỮA thanh đầu trang, control phụ neo phải · CTA chính bo **pill** hết hai đầu · thẻ nội dung **không viền**, chỉ bóng mềm · tổng số và CTA **cùng một hàng** |
   | success | `frames/{id}__success.png` | Hình minh hoạ canh giữa, chiếm ~40% chiều cao · không có thanh neo đáy |
   ```

   **Cột thứ 3 là phần có giá trị duy nhất** và có 3 điều kiện hợp lệ:
   - Phải là thứ **chỉ thấy được bằng mắt**: canh lề thực tế, vai trò bo góc, có/không viền, tỉ lệ, thứ tự thị giác, phần tử nào cùng hàng.
   - **CẤM** viết lại thứ đã có trong JSON (`gap=16px`, `direction=row`, danh sách control) — đó là chép, không phải xem.
   - **CẤM** câu rỗng kiểu *"đã xem, khớp specs"* / *"bố cục như mô tả"*. Không tìm được gì đáng ghi cho một state thì ghi thẳng *"không quan sát thêm được gì ngoài specs"*.

   State nào `frame_exported: false` (PNG lỗi) → vẫn 1 dòng, cột Frame ghi `— (export fail)`, cột 3 ghi *"chỉ transcribe từ specs JSON, độ tin cậy bố cục thấp hơn"* + 1 dòng Deviation log.

   **Vì sao bắt buộc:** ảnh là kênh duy nhất chở được radius/viền/canh lề/tỉ lệ, và nó **rời khỏi pipeline sau bước này** — Stage 4b đọc DD, Stage 5 đọc `ui_schema` + DD, không ai mở lại PNG. Bỏ bước xem ảnh ở đây thì không tầng nào phía sau phát hiện được: DD vẫn đủ section, code vẫn chạy, chỉ giao diện là sai. Hook 4 (`stage4a_complete.sh`) chặn DD thiếu bảng này khi `figma_status: mapped`.

**Composition self-audit ở mode TRANSCRIBE:** §2.4 vẫn chạy đủ L1-L11 nhưng **warn-only tuyệt đối** — kể cả khi `layout_rules.enforce_hard: true`. Lý do: rule fail ở đây là phát hiện về **design của designer**, không phải lỗi của bạn; block build vì Figma có 2 nút primary là sai địa chỉ. Fail → ghi WARN + đưa vào Deviation log dạng `escalate designer`, KHÔNG tự sửa layout cho "đạt rule".

## 2. Chỉ thị thực thi

> AUTHOR mode: làm đủ 1→6. TRANSCRIBE mode: §0b thay chỗ cho phần "sáng tác" của bước 1/2/3; các bước còn lại (4, 5, 6) không đổi.

1. **Structural Scan + DS vocabulary load**: Load 3 nguồn grounding (đường dẫn resolve qua `bmad.design_system_root` — workflow.md Layer 1):
   - **`{design_system_root}/component_catalog.md`** (digest ~1-2k token, KHÔNG load full components_metadata.json): vocabulary component thật của project + §Recipes (cụm composition đã quan sát từ code). Thiếu file → WARN *"catalog chưa có — chạy `/ntapp-ds-bootstrap` để sinh; tiếp tục nhưng cột DS candidate để trống"*.
   - **`{design_system_root}/_reference/visual-notes.md`** (+ screenshots `_reference/pages/` nếu cần soi): style character thật — density, elevation, table/card treatment — grounding tỉ lệ & mật độ khi vẽ wireframe. Thiếu → proceed.
   - Journey Spec `ux_design.md` + `ux_conventions.md` (theo R10 source table) — journey/IA + conventions tương tác/error/content.
   - **Sketch preview frame (optional — Stage 1):** hàng Journey Screen Table của unit (`ux_design.md` §4) có link `([sketch](...#{screen_slug}))` → mở ĐÚNG anchor đó trong `{stage_1_discovery}/ux_sketch/previews/{feature_slug}_ux_sketch_preview.html` — frame Stage 1 của CHÍNH màn này (seed bố cục + branch indicator trước khi vẽ §2.2). Preview mặc định **hi-fi** (`sketch_preview: lavish`) nên đọc được cả content blocks / CTA label / branch từ `data-block`/`data-cta`/`data-branch`; kèm bảng Screen Intent Table §4 `ux_sketch.md` cho cùng screen. Row không có link → tra bảng **Preview Index** cuối §4 `ux_sketch.md` theo tên screen. Không có sketch/preview → skip im lặng (sketch optional). **Hi-fi KHÔNG có nghĩa là đã approve:** preview là seed intent, chưa qua DS audit — component/token thật do §2.3 `DS candidate` + Stage 4b `[REUSE AUDIT]` chốt; ràng buộc thật vẫn là Journey Spec Key states + conventions + DD contract.
2. **Information Architecture (2.1)**: Định nghĩa cây thông tin và sơ đồ điều hướng của màn hình.
3. **Wireframe Blueprint (2.2)**: Vẽ khung xương giao diện (Skeleton) bằng **ASCII Art**. Bắt buộc mô tả rõ bố cục (Navigation, Header, Sidebar, Content, Actions) để định vị các thành phần kỹ thuật. CẤM dùng Mermaid cho nội dung này.
   - **Recipe-first composition (BẮT BUỘC check trước khi tự sáng tác bố cục):** control cluster trong wireframe khớp một recipe trong `component_catalog.md` §Recipes (vd hàng search + dropdown + nút tìm ↔ `filter-bar-row`) → compose theo ĐÚNG recipe đó (đúng members, đúng thứ tự) và ghi chú `<!-- recipe: {name} -->` cạnh group tương ứng trong Layout Groups. Product đã giải bài toán đó rồi thì wireframe mới phải giống cách product đang làm — không phát minh arrangement khác.
   - **Control ID annotation (BẮT BUỘC):** Mỗi control trong wireframe phải có `[control_id]` annotation (snake_case, khớp 1:1 cột "Tên control" §2.3). Ví dụ: `[input_merchant_code] [button_search 🔍[search]]`. ID là semantic identifier cho Stage 4b build `layout` tree + data binding.
   - **Emoji = visual hint, KHÔNG phải UI element thực.** Mọi emoji trong wireframe phải kèm annotation `🔍[search]` (cú pháp: emoji + `[icon-name]`, name kebab-case semantic intent). Emoji là content thực (chat message, emoji picker) → prefix `content:` vd `🎉[content:celebration]`.
   - **Icon Legend (BẮT BUỘC nếu có ≥1 emoji):** Ngay dưới wireframe, thêm bảng 3 cột:
     ```markdown
     **Icon Legend:**
     | Emoji | Icon name | Mục đích |
     | :--- | :--- | :--- |
     | 🔍 | search | Trigger global search bar |
     | ✖ | close | Đóng modal/dialog |
     | ⬇ | chevron-down | Expand dropdown |
     ```
     Bảng này là machine-readable contract — Stage 4b `ui_schema_agent` đọc cột `Icon name` để map sang component cụ thể của icon library trong stack (vd `lucide-react → Search`). Stage 5 dev agent KHÔNG copy emoji sang code.
   - **Layout Groups (BẮT BUỘC nếu có ≥2 sibling controls / form multi-field):** Ngay dưới Icon Legend, thêm bảng 4 cột declarating composition tree:
     ```markdown
     **Layout Groups:**
     | Group ID | Type | Members | Props |
     | :--- | :--- | :--- | :--- |
     | R1 | Stack | F1, F2, G2 | direction=column, gap=md, align=stretch |
     | F1 | FormField | input_name | label="Tên hồ sơ", required=true |
     | F2 | FormField | textarea_description | label="Mô tả" |
     | G2 | Stack | input_merchant_code, input_product_code, button_search | direction=row, align=center, gap=sm |
     ```
     - Convention IDs: `R1`=root, `G*`=generic group, `F*`=FormField (chỉ phân loại đọc, parser không enforce prefix).
     - `Type` lấy từ inventory 10 canonical primitives (`Stack`, `Cluster`, `Grid`, `Spacer`, `Center`, `Box`, `FormField`, `FieldGrid`, `Sidebar`, `Switcher`). Xem `_shared/component-metadata-schema.md` §12.
     - `Members` nested: reference control_id (leaf) hoặc Group ID (recursive). Thứ tự = thứ tự render.
     - `Props` value: token ref giữ tên token (`gap=md`), enum lowercase (`align=center`).
     - Bảng này là machine-readable contract — Stage 4b `ui_schema_agent` đọc table build `layout` tree trong `ui_schema_{id}.json`. Stage 5 dev render qua layout primitive (Stack/Cluster/...) đã materialize bởi ds-build-component — KHÔNG tự đoán wrapper div / raw flex CSS.
     - **Missing table:** Stage 4b emit `LAYOUT_GROUPS_MISSING` warning (NON-BLOCKING), fallback root Stack flat — alignment intent có thể bị mất. Khuyến nghị F3 luôn declare table khi có sibling composition.
4. **UI Control Specification (2.3)**: Lập bảng đặc tả UI Controls mức độ **High-Fidelity**.:
   - Liệt kê 100% các thành phần tương tác (Textbox, Button, Selection...).
   - Cột "Tên control" = `control_id` snake_case, khớp annotation trong wireframe §2.2 và Members trong Layout Groups table.
   - **Cột `DS candidate` (BẮT BUỘC có cột, giá trị best-effort):** tên component từ `component_catalog.md` khớp control này. Match hiển nhiên (control "dropdown trạng thái" ↔ catalog `status-dropdown`) → điền tên; không chắc → `-`. Hint **non-binding** — Stage 4b audit vẫn score lại toàn inventory; hint đúng giúp match exact-name, cắt false-NEW. KHÔNG bịa tên ngoài catalog.
   - **Cột `intent` (BẮT BUỘC cho button/action control):** `primary` | `secondary` | `tertiary` | `destructive` — input cho L1/L7 composition audit (§2.4).
   - Định nghĩa trạng thái mặc định (Default values, Hidden/Visible/Disabled rules) + state interactive (hover/focus/disabled) — input cho L10.
   - **Quan trọng:** Trích xuất bảng Validation (Action -> Trường hợp lỗi -> Thông báo lỗi nguyên văn).
5. **Composition self-audit (2.4)**: Sau khi hoàn tất §2.2 (Layout Groups) + §2.3 (Control table + intent + state), Agent F3 **tự chấm** wireframe theo rule catalog `{design_system_root}/_shared/layout-best-practices.md` — **per-unit composition (L1, L2, L3, L4, L7, L8, L10, L11)**:

   | Rule | Self-check | Confidence |
   |:---|:---|:---|
   | **L1** Single primary action | Đúng 1 control `intent=primary` / view (hoặc / section nếu multi-section) | HIGH (HARD-able) |
   | **L2** Mandatory states | View có data khai báo đủ `empty`+`loading`+`error`; `success` nếu có mutation (submit/create/update/delete) | HIGH (HARD-able) |
   | **L3** Field grouping | ≥2 field cùng concern đã gom qua Layout Group, không rời rạc | MEDIUM |
   | **L4** Column density | ≤7 field flat (chưa nhóm) / column; vượt → gợi ý L3 (không fail) | MEDIUM |
   | **L7** Destructive separation | Control `intent=destructive` tách khỏi cụm primary + có confirm state | HIGH (HARD-able) |
   | **L8** Form linearity | Form nhập tuyến tính single-column (trừ field độc lập ngắn) | MEDIUM |
   | **L10** Affordance state | Control interactive khai báo hover/focus/disabled trong §2.3 | MEDIUM |
   | **L11** Consistency placement | Action bar / primary cùng vị trí cross-screen (cùng feature) | MEDIUM |

   - **KHÔNG** audit L5/L6/L9 ở đây — owner là `ux-design` (journey/IA-level), **inherit từ dòng self-audit cuối mỗi journey §4 của Journey Spec**. Phát hiện Journey Spec vi phạm L5/L6/L9 → **escalate ngược Journey Spec** (R10), KHÔNG tự sửa lệch. **HLD-fallback** (`ux_source: HLD-fallback`, journey chưa author): không có self-audit upstream → unit single-screen/reuse nên L5/L6 thường N/A, chỉ tự-check L9 (IA depth) theo HLD §3.2 (WBS tree + module breakdown).
   - **Mặc định warn-only toàn bộ** (`layout_rules.enforce_hard: false`). Ghi kết quả audit vào `f3_ui_part.md` §2.4 (mỗi rule: `OK` / `WARN: <đề xuất>`). Khi set `feature-design.layout_rules.enforce_hard: true` → **L1/L2/L7 (HARD-able) fail = block** tại gate "Wireframe Composition Audit" (R6).
   - Non-dogmatic: project có pattern composition nhất quán hợp lý (vd table data-heavy đã nhóm) → giữ. Override per-rule qua `ds-rules-overrides.md` section `## layout`.

6. **Wireframe visual preview (optional — `wireframe_preview: lavish`):** khi `.bmm-config.yaml` block `ntapp-feature-design` có `wireframe_preview: lavish` VÀ session interactive — render Layout Groups tree thành HTML lo-fi (box đúng tỉ lệ, gap/padding resolve từ spacing token, label control_id; KHÔNG style chi tiết) vào `{intermediate_folder}/preview/f3_wireframe_{id}.html` (disposable, không commit) → mở `npx -y lavish-axi <file>` + poll để reviewer annotate trực tiếp trên bản render thay vì đọc ASCII. Feedback → sửa §2.2/§2.3 rồi tiếp tục. Default off; headless bỏ qua. Guardrails như CLAUDE.md (không `share`, telemetry off).

## 3. Đầu ra yêu cầu
- Section 2 hoàn chỉnh trong Master Detailed Design (§2.1 IA + §2.2 Wireframe/Layout Groups + §2.3 Control matrix **kèm cột DS candidate** + **§2.4 Composition self-audit** + **§2.5 Deviation log — chỉ TRANSCRIBE mode, mở đầu bằng bảng `[FRAMES VIEWED]`**).
- TRANSCRIBE mode: cột `Props` của Layout Groups §2.2 phải mang `radius=` / `border=` / `elevation=` cho mọi group có entry `surface[]`, và `sizing=` + hậu tố `(fill)` ở cột Members. Đây là **nguồn duy nhất** để Stage 4b sinh `props.radius`/`props.border`/`props.elevation` trong `ui_schema`.
- **Lưu trữ:** File Markdown lưu tại `{intermediate_folder}/f3_ui_part.md`.
- Đảm bảo tính nhất quán với design token + component list đã được chọn trong UX Spec (theo R10) + vocabulary từ `component_catalog.md`.

## [GATE] — Skip-decision (⛔ quyết định trước khi sang Next)

- `id_type == feature_id` → **SKIP** action (không tạo `f3_ui_part.md`).
- `id_type ∈ {screen_id, widget_id}` → **RUN** action, đảm bảo Section 2 + `f3_ui_part.md` đã ghi, nhất quán design token/component đã chọn trong UX Spec (R10).
- Traversal tuyến tính: luôn sang Step 03 (Step 03 tự SKIP với FE theo Skip Condition §0 của nó).

**Next:** Read fully and follow `./step-03-logic-modeling.md`
