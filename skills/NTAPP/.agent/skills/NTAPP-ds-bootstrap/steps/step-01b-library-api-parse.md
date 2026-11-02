# Step 1b: Library API Parsing

## GOAL

Parse `node_modules/{ui_library}/**/*.d.ts` để extract primitive API spec per component → ghi `library_apis/{lib}@{ver}/{Component}.json`. Cùng pipeline cho icon library (`--icon-index` mode) → emit `_index.json` chứa available icons.

Best-effort — parser fail / partial → log + continue, KHÔNG block bootstrap. Downstream Step 3 (component-discoverer) sẽ dùng parsed API cho `WRAPPER_PROP_HIDDEN` detection.

## 1. Load Persona

Adopt role của **Library API Parser** sub-agent tại `../agents/library-api-parser.md`. Persona declare: role + per-lib parsing strategies (§4 antd/primeng/material/chakra/mantine/shadcn/other) + JSON output schema ref (`_shared/library-api-schema.md`) + edge cases (§6) + constraints (§7).

## 2. Inputs

- `{design_system_root}/stack-profile.json` (Step 1 output) — `ui_library.name`, `ui_library.version`, optional `ui_library.d_ts_pattern`, `icon_library.name`, `icon_library.version`.
- `{code_repo_root}/node_modules/{lib}/` — READ.
- `{code_repo_root}/package.json` + lock file — confirm version.
- `_shared/library-api-schema.md` (output schema).

## 3. Pre-conditions (gated entry)

- **Skip điều kiện 1:** `ui_library.name = none` → skip toàn bộ step (log info, không output file).
- **Skip điều kiện 2:** `ui_library.name = shadcn` → skip parser (shadcn là source-copy, component-discoverer xử lý như primitive build-from-scratch). Mark trong manifest: `parser_method: "skipped-source-copy"`.
- **STOP điều kiện:** `ui_library.name ∉ {none, shadcn}` và `node_modules/{lib}` không tồn tại → STOP *"Lib `{name}` declared trong stack-profile nhưng `node_modules/{lib}` không tồn tại. Chạy `npm install` (hoặc tương đương) trong code repo trước."* (Pre-flight 5 ở INITIALIZATION cũng đã fail-fast.)
- **Version sync:** version mismatch giữa `package.json` và `stack-profile.json.ui_library.version` → warn, ưu tiên version trong `package.json` (= thực tế installed), update stack-profile.

## 4. Pipeline — UI library parsing

### Stage 4.1: Identify primitive component files

Heuristic per lib theo `library-api-parser.md` §4 (entry pattern table). Glob để liệt kê primitive components, filter trùng (vd antd có `lib/` + `es/` — chỉ parse 1 nguồn).

### Stage 4.2: Per component, parse Props interface

Dispatch theo lib + framework — chi tiết per-lib ở `library-api-parser.md` §4 (antd 5.1, primeng 5.2, material 5.3, shadcn 5.4 skip, chakra/mantine/radix 5.5, other 5.6).

Type mapping table (`library-api-parser.md` §4 Stage 2 — preserved trong persona):
- Union literals → `enum` + `values`
- Primitives → `string` / `number` / `boolean`
- Function → `function` + `signature`
- `ReactNode` / `JSX.Element` → `ReactNode`
- `Slot` / `TemplateRef` → `Slot` / `TemplateRef`
- Object literal → `object` + `nested` (recursive)
- Array → `array`
- Generic / conditional / mapped unresolvable → `unknown` + note (per U5 conservative)

Parse JSDoc: `@default`, `@since`, `@deprecated`, first sentence → description.
Detect required: `?` mark, `defaultProps`, Vue `default` factory.
Infer `tier_hint` theo `_shared/library-api-schema.md` §5.

Strip HTML attrs noise: Props extends `BaseHTMLAttributes<E>` / `HTMLAttributes` / `AriaAttributes` / `DOMAttributes` → KHÔNG ghi inherited props (chỉ lib-specific). Ngoại lệ: lib override prop tên HTML (vd antd Button override `type`) → giữ override.

### Stage 4.3: Extract slots + events

- React: prop prefix `on*` đã ở `props` (type=function). `children` → `slots: [{name: "default"}]`.
- Vue: `<slot name="X">` → `slots`. `defineEmits<{ click: [MouseEvent] }>()` → `events`.
- Angular: `@ContentChild` / `<ng-content select="...">` → `slots`. `@Output()` → `events`.

### Stage 4.4: Write per-component JSON

Atomic write (U1, U2): `{design_system_root}/library_apis/{lib}@{version}/{ComponentName}.json` per `library-api-schema.md` §4.

### Stage 4.5: Update `_manifest.json`

Format theo `library-api-schema.md` §12. Classify mỗi component:
- `components_parsed_full` — tất cả prop type resolve được, không `unknown`.
- `components_parsed_partial` — có ≥1 prop `type: "unknown"` hoặc fallback note.
- `components_failed` — Props interface không locate được hoặc exception khi parse.
- `components_manual` — file đã có `parser_method: "manual-curated"` (parser skip overwrite).

Compute `coverage_pct`.

### Stage 4.6: HITL on parse failure

Per component trong `components_failed`, prompt DSO:
> *"Component `<X>` của lib `<Y>@<V>` parse fail: `<reason>`. Lựa chọn:*
> *1. **Skip** — agent ignore primitive này khi audit. Hệ quả: Stage 4b Agent 1 (downstream skill) sẽ propose `[NEW]` variant khi gặp nhu cầu wrapper, không biết lib có sẵn.*
> *2. **Manual-curate** — DSO viết tay `{lib}@{ver}/{X}.json` theo `_shared/library-api-schema.md`. Agent reload sau khi DSO commit.*
> *3. **Retry với d_ts_pattern khác** — DSO chỉ định path khác trong `.bmm-config.yaml` `ui_library.d_ts_pattern`.*
> *Nhập 1/2/3."*

Skip → mark `components_failed`, continue. Manual → mark `components_manual`, exit parser cho component đó. Retry → loop trên path mới.

## 5. Pipeline — Icon library indexing

Áp dụng nếu `icon_library.name ∉ {none}`. Mode `--icon-index`.

### Stage 5.1: Detect parser mode per `import_style`

| `import_style` | Scan target | Output |
|---|---|---|
| `component` (vd `@ant-design/icons`, `lucide-react`) | `node_modules/{lib}/**/*.d.ts` | array icon names theo `component_pattern` |
| `css-class` (vd `primeicons`) | `node_modules/{lib}/{icons,css}/**/*.scss` hoặc `.css` | array class names |
| `font` (vd Font Awesome free legacy) | `node_modules/{lib}/css/*.css` font glyph map | array glyph names |

### Stage 5.2: Emit `_index.json`

Atomic write: `{design_system_root}/library_apis/{icon_library.name}@{version}/_index.json` chứa:
```json
{
  "library": "{name}",
  "version": "{version}",
  "import_style": "{style}",
  "component_pattern": "{pattern}",
  "available_icons": ["Icon1", "Icon2", ...]
}
```

## 6. Re-parse trigger (mode flag)

Re-parse chạy khi:
- DSO gọi `/ntapp-ds-bootstrap --refresh-library-api`.
- Stack-profile thay đổi `ui_library.name` hoặc `version` từ run trước (detect Stage 3.1 vs cache).
- DSO commit manual change vào `library_apis/` (parser skip files marked manual).

Re-parse flow:
1. Đọc manifest cũ, save `components_manual` list.
2. Re-parse tất cả components trừ `components_manual` (giữ nguyên file curated).
3. Re-compute manifest, update timestamp.
4. Diff vs version cũ → emit report section `[LIBRARY API DIFF]`:
   ```markdown
   ## [LIBRARY API DIFF] — {lib}@{old} → {new}
   - {Component}: prop `{name}` ADDED
   - {Component}: prop `{name}` DEPRECATED → use `{replacement}`
   ```
5. Diff được Stage 4b Agent 1 downstream skill (`ntapp-ui-generation`) đọc khi audit screen mới — biết feature mới có sẵn primitive.

## 7. Output

- `{design_system_root}/library_apis/{lib}@{ver}/{Component}.json` per primitive component (full hoặc partial).
- `{design_system_root}/library_apis/{lib}@{ver}/_manifest.json`.
- `{design_system_root}/library_apis/{icon_library.name}@{ver}/_index.json` (icon mode).
- Append `[LIBRARY APIs PARSED]` vào `report_sections[]` (concat-by-emit-order, xem step-06):
  ```markdown
  ## [LIBRARY APIs PARSED]

  ### {lib}@{version}
  - Total components: N
  - Full parse: X
  - Partial parse: Y
  - Failed: Z
  - Manual-curated: W
  - Coverage: P%
  - Path: library_apis/{lib}@{version}/
  ```
- (Re-parse mode) Append `[LIBRARY API DIFF]` section nếu có thay đổi vs version cũ.

## 8. Decision Points

- **Parser fail / partial** — log vào console + report section, KHÔNG block bootstrap. Downstream component-discoverer sẽ vẫn chạy với fallback HITL khi cần wrap primitive.
- **Lib không có TS types (CJS-only)** — check `node_modules/@types/{lib}` → parse từ DefinitelyTyped fallback. Vẫn không có → HITL Stage 4.6 manual-curate hoặc skip.
- **Multiple lib versions cùng tồn tại** (vd antd 4 + antd 5) → parse mỗi version riêng, folder khác nhau. Repo phải declare version dùng chính trong stack-profile.
- **`node_modules/{lib}` symlink (pnpm)** → resolve symlink, parse target.

**Next:** Read fully and follow `./step-02-extract.md`
