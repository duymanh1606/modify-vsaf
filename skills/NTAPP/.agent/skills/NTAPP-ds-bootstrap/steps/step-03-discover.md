# Step 3: Component Discovery

## GOAL

Quét `component_roots` từ `stack-profile.json`, extract abstract metadata (semantic intent, variants, states, inputs/outputs, accessibility, tags) cho mỗi component có sẵn — theo schema 2-layer (abstract + stack_specific). **Enrich** metadata bằng inference có confidence (semantic_intent/tags) + **usage scan** (component dùng ở screen nào) + **composition recipes** (cụm component hay đi cùng nhau). Detect functional duplicates + `WRAPPER_PROP_HIDDEN` diff với parsed primitive API.

> **Vì sao enrichment bắt buộc:** `semantic_intent`/`tags` là chính xác các field mà Stage 4b (`/ntapp-ui-generation` Step 1) dùng để pattern-match reuse. Để nguyên `<TODO: DSO fill>` = inventory mù → downstream match fail → propose `[NEW]` trùng chức năng (component library-default thay vì reuse). Inference được phép vì có confidence mark + DSO batch-confirm ở Step 6 — không vi phạm U5.

## 1. Load Persona

Adopt role của **Component Discoverer** sub-agent tại `../agents/component-discoverer.md`. Persona declare: role + decision policies (§4.1 framework parser table, §4.2 tokens_used extraction, §4.3 placeholder marking, §4.4 duplicate detection, §4.5 WRAPPER_PROP_HIDDEN diff logic) + output spec (§5 JSON schema) + edge cases (§6) + constraints (§7).

## 2. Inputs

- `{design_system_root}/stack-profile.json` (Step 1 output).
- `{design_system_root}/library_apis/{lib}@{ver}/*.json` (Step 1b output) — primitive API spec cho diff.
- `_shared/component-metadata-schema.md`, `_shared/pattern-matcher.md`, `_shared/library-api-schema.md` (READ).
- Component files dưới `{code_repo_root}/{component_roots}/...` (READ).

## 3. Pipeline

### Stage 3.1: Discover files

Glob theo `component_convention.location_pattern`, filter `discovery_hints.ignore_patterns`. Mỗi component file → 1 candidate. Lưu `file_path` relative `{code_repo_root}` (U2).

### Stage 3.2: Parse abstract metadata per framework

Dispatch theo `component-discoverer.md` §4.1 (Angular / React / Vue-Svelte parser).

### Stage 3.3: Extract `tokens_used`

Theo persona §4.2 — quét template + style file cho CSS var / SCSS var / theme reference. Hardcoded value → KHÔNG add, flag warning trong console.

### Stage 3.4: Mark placeholder fields

Theo persona §4.3 — `<TODO: DSO fill>` cho `semantic_intent`, `accessibility.aria`, `accessibility.keyboard`, additional `tags`.

### Stage 3.4b: Semantic enrichment (inference có confidence — persona §4.6)

Với mỗi field vừa mark TODO ở Stage 3.4 (trừ `accessibility.*` — không infer a11y):

1. Infer `semantic_intent` (1-2 câu UX problem component giải quyết) từ: tên component + props/inputs + template structure + usage context (Stage 3.4c). Ghi đè placeholder bằng giá trị inferred, set `discovery_metadata.inferred_fields` + `confidence` per U6.
2. Infer thêm `tags` (synonym, category keyword) — phục vụ `pattern-matcher.md` §3.3 tag_overlap.
3. KHÔNG có signal đủ (component rỗng, tên vô nghĩa) → giữ `<TODO: DSO fill>` như cũ.
4. Append section `[INFERRED INTENTS]` vào `report_sections[]` — bảng `component | inferred intent | confidence` để DSO batch-confirm/sửa ở Step 6 (tick = accept).

### Stage 3.4c: Usage scan (persona §4.7)

Grep selector/import của mỗi component across screen/page files trong `{code_repo_root}` (roots từ `stack-profile.discovery_hints`). Populate `usage: { count, screens: [...] }` (≤5 screen paths, relative U2). Component 0 usage → `usage.count: 0` (candidate deprecated — note trong report).

### Stage 3.5: Pattern-match duplicate detection

Per category (xem `_shared/component-metadata-schema.md` category enum), apply `_shared/pattern-matcher.md` pairwise. Score ≥ 0.70 → emit `duplicate_warnings` entry trong output JSON + append `[FUNCTIONAL DUPLICATES]` section vào `report_sections[]`:

```markdown
## [FUNCTIONAL DUPLICATES]

### Pair: {name-a} ↔ {name-b}
- **Similarity score:** {score}
- **Recommendation:** Cân nhắc consolidate vào 1 component với variant prop.
```

### Stage 3.6: WRAPPER_PROP_HIDDEN diff

Per component có `stack_specific.{fw}.library_wrap.primitive` populated, apply `component-discoverer.md` §4.5 diff logic:

1. Lookup parsed primitive API path. Không tồn tại → skip + log info.
2. Diff wrapper inputs vs primitive props (sau normalize tên).
3. Filter style-relevant props (`tier_hint ∈ {radius, color, size, spacing}`).
4. Mỗi hidden prop → append warning entry vào `report_sections[]` per §4.5 markdown template.
5. Populate `library_wrap.library_version` + `library_wrap.primitive_api` field.

### Stage 3.6b: Composition recipes (persona §4.8)

Từ usage scan (Stage 3.4c), cluster co-occurrence: ≥2 component cùng xuất hiện trong ≥2 screen files → 1 recipe candidate. Mỗi recipe: `{ name (kebab, mô tả pattern — vd "filter-bar-row"), members: [component names], example_screens: [...], confidence }`. Recipe là **observation mô tả** (không phải component mới) — consumer: `component_catalog.md` digest (Step 7) + F3 wireframe composition (Stage 4a) + reuse audit (Stage 4b). Append `[COMPOSITION RECIPES]` vào `report_sections[]` để DSO confirm/rename ở Step 6.

### Stage 3.7: Atomic write

Theo U1 + U2: `{design_system_root}/components_metadata_parts/01_discovered.json` (bao gồm `usage` per component + top-level `recipes[]`).

## 4. Decision Points

- **Tất cả `component_roots` đều miss** trong `{code_repo_root}/...` → STOP với hint verify cwd + `bmad.code_repo_root`.
- **Greenfield** (không có component nào) — output empty `components` object, log info "no components discovered". Step 4 normalize chỉ áp lên tokens.
- **Component cùng tên ở 2 path** — output cả 2 với suffix path, DSO chọn merge hoặc rename ở Step 6.

## 5. Output

- `{design_system_root}/components_metadata_parts/01_discovered.json` (kèm `usage` + `recipes[]`).
- Append section vào `report_sections[]`:
  - `[INFERRED INTENTS]` (semantic_intent/tags inferred — DSO batch-confirm ở Step 6).
  - `[COMPOSITION RECIPES]` (recipe candidates — DSO confirm/rename ở Step 6).
  - `[FUNCTIONAL DUPLICATES]` (nếu có pair score ≥ 0.70).
  - `[WRAPPER PROP HIDDEN]` (nếu có discovered wrapper với primitive_api lookup success).

**Next:** Read fully and follow `./step-03b-visual-reference.md`
