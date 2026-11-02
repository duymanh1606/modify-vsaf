# Component Metadata Schema

**Schema version:** 1.2
**File:** `{design_system_root}/components_metadata.json`
**Producer:** `/ntapp-ds-bootstrap` (sub-agent: `component-discoverer`), `/ntapp-ds-build-component` (sub-agent: `metadata-registrar`)
**Consumers:** `/ntapp-ui-generation` Stage 4b agents, `/bmad-quick-dev` Stage 5, retrieval by AI agents

> **Scope per-DS:** 1 file / 1 design system. Multi-DS: mỗi DS root có metadata + `component_catalog.md` riêng; matcher Stage 4b chỉ đối chiếu inventory CỦA DS unit thuộc về (component DS khác không import được). Xem [ds-registry-schema.md](ds-registry-schema.md).

---

## 1. Mục đích

Catalog tất cả component trong DS. Có **2 layer**:
- **Abstract** (cross-stack): semantic info để retrieval và planning.
- **Stack-specific**: implementation details cho code generation.

Tách layer cho phép cùng 1 component có nhiều implementation theo framework (Angular, React, Vue) — chia sẻ semantic, khác implementation.

## 2. Vòng đời

| Event | Hành vi |
|---|---|
| Bootstrap repo | `component-discoverer` quét `discovery_hints.component_roots` từ stack-profile, tạo file. |
| Stage 4b approve delta | `/ntapp-ds-build-component` chạy `metadata-registrar` → atomic update. |
| Component bị xoá / deprecate | Update `metadata.status: deprecated`, KHÔNG xoá entry (giữ history cho reference). |

## 3. Cấu trúc top-level

```json
{
  "$schema_version": "1.0",
  "generated_at": "2026-05-08T10:30:00Z",
  "stack_profile_ref": "./stack-profile.json",
  "master_token_ref": "./master_token.json",
  "components": {
    "<component-id>": { ... },
    "<component-id-2>": { ... }
  }
}
```

`<component-id>`: kebab-case, unique. Khớp với `Name` trong proposal `[NEW]` (xem `proposal-schema.md`).

## 4. Cấu trúc per-component

```json
{
  "abstract": {
    "semantic_intent": "Hiển thị tiến độ upload file dạng linear progress với label %.",
    "category": "feedback",
    "variants": ["linear", "circular"],
    "states": ["idle", "uploading", "success", "error"],
    "inputs": [
      { "name": "value", "type": "number", "required": true, "description": "0-100" },
      { "name": "label", "type": "string", "required": false },
      { "name": "variant", "type": "'linear' | 'circular'", "required": false, "default": "linear" }
    ],
    "outputs": [],
    "accessibility": {
      "role": "progressbar",
      "aria": ["aria-valuenow", "aria-valuemin", "aria-valuemax"],
      "keyboard": "none"
    },
    "tags": ["progress", "upload", "feedback", "loading"]
  },

  "stack_specific": {
    "angular": {
      "selector": "app-progress-bar",
      "class_name": "ProgressBarComponent",
      "module": "SharedModule",
      "file_path": "src/app/lib/components/progress-bar/progress-bar.component.ts",
      "library_wrap": {
        "library": "primeng",
        "library_version": "16.0.0",
        "primitive": "p-progressbar",
        "primitive_api": "./library_apis/primeng@16.0.0/p-progressbar.json"
      },
      "dependencies": ["@angular/common", "primeng/progressbar"]
    }
  },

  "tokens_used": [
    "semantic.color.action.primary",
    "semantic.color.status.success",
    "semantic.color.status.error",
    "semantic.layout.radius-base"
  ],

  "style_property_inventory": {
    "<css-property-name>": [
      {
        "value": "<resolved-or-raw-value>",
        "source": "<{token.reference.path}>" | "literal",
        "tokenized": true | false,
        "file": "<style-root>/<component>.<ext>",
        "line": <int>
      }
    ]
  },

  "metadata": {
    "version": "1.0.0",
    "status": "active",
    "last_updated": "2026-05-08T10:30:00Z",
    "source": "build-skill",
    "related_features": ["ING_05_PROG_01"],
    "deprecation": null
  }
}
```

## 5. Field reference

### `abstract` (cross-stack, required cho mọi component)

| Field | Required | Mô tả |
|---|---|---|
| `semantic_intent` | ✅ | 1-2 câu mô tả mục đích. Dùng cho semantic search. |
| `category` | ✅ | `input` \| `display` \| `feedback` \| `navigation` \| `layout` \| `layout-primitive` (v1.2+, see §12) \| `overlay` \| `data` \| `media` |
| `variants` | ✅ | array string. `[]` nếu không có. |
| `states` | ✅ | array string. Không bao giờ rỗng (ít nhất `idle`). |
| `inputs` | ✅ | array of `{ name, type, required, description?, default? }`. `[]` nếu không có prop. |
| `outputs` | ✅ | array of `{ name, payload_type, description? }`. `[]` nếu không emit event. |
| `accessibility` | ✅ | object: `{ role, aria, keyboard }` |
| `tags` | ✅ | array kebab-case keywords cho search. ≥3 tag. |

### `stack_specific` (object keyed by framework name)

Key trùng với `framework.name` trong stack-profile (`angular`, `react`, `vue`, `svelte`, ...). Mỗi key chứa object framework-specific.

#### `angular`
| Field | Required | Mô tả |
|---|---|---|
| `selector` | ✅ | element selector, theo `selector_prefix` từ stack-profile |
| `class_name` | ✅ | TypeScript class name (PascalCase) |
| `module` | optional | NgModule import path (legacy modules) |
| `file_path` | ✅ | path từ repo root |
| `library_wrap` | optional | Object spec wrap UI lib — xem §4.1 dưới |
| `dependencies` | ✅ | array npm package paths |

#### `library_wrap` object (cross-framework — schema)

| Field | Required | Mô tả |
|---|---|---|
| `library` | ✅ | Tên lib, khớp `stack-profile.ui_library.name` (vd `antd`, `primeng`) |
| `library_version` | ✅ (v1.1+) | semver exact của lib đang wrap, khớp `library_apis/{lib}@{ver}/` folder |
| `primitive` | ✅ | Tên primitive component của lib (vd `Button`, `p-progressbar`) |
| `primitive_api` | optional | Relative path tới parsed API JSON (vd `"./library_apis/antd@5.12.0/Button.json"`). Producer `library-api-parser` ghi file, `metadata-registrar` populate ref. NULL nếu parser skip/fail (lib không TS, shadcn source-copy, ...) |

→ Khi `primitive_api` populated, Stage 4b Agent 1 và `component-scaffolder` đọc file để biết primitive expose prop gì → quyết định "expose prop xuống wrapper" thay vì "tạo variant mới với CSS custom".

#### `react`
| Field | Required | Mô tả |
|---|---|---|
| `component_name` | ✅ | PascalCase |
| `file_path` | ✅ | path từ repo root |
| `export_type` | ✅ | `default` \| `named` |
| `props_interface_name` | optional | tên TypeScript interface/type (vd: `ProgressBarProps`). Required khi `language=typescript`. |
| `module_format` | optional | `esm` \| `cjs` (default `esm`) |
| `style_strategy` | optional | `css-modules` \| `styled-components` \| `emotion` \| `tailwind` \| `vanilla-css`. Override stack-profile per-component. |
| `style_file_path` | optional | path tới file style nếu `css-modules` (vd: `Button.module.scss`) |
| `library_wrap` | optional | Object spec — xem §4.1 (`{library, library_version, primitive, primitive_api}`) |
| `dependencies` | ✅ | array npm package paths |

#### `vue`
| Field | Required | Mô tả |
|---|---|---|
| `component_name` | ✅ | PascalCase, khớp `name` option hoặc filename |
| `file_path` | ✅ | path tới `.vue` file (SFC) hoặc `.ts`/`.js` (setup script-only) |
| `sfc` | ✅ | boolean — true nếu Single File Component (`.vue`), false nếu split |
| `script_setup` | optional | boolean — true nếu dùng `<script setup>` syntax (Vue 3) |
| `template_path` | optional | path tới template file nếu `sfc=false` |
| `style_path` | optional | path tới style file nếu `sfc=false` |
| `composition_api` | optional | `composition` \| `options` (default `composition` cho Vue 3) |
| `library_wrap` | optional | Object spec — xem §4.1 (`{library, library_version, primitive, primitive_api}`) |
| `dependencies` | ✅ | array npm package paths |

#### `svelte`
| Field | Required | Mô tả |
|---|---|---|
| `component_name` | ✅ | PascalCase, khớp filename `.svelte` |
| `file_path` | ✅ | path tới `.svelte` file |
| `runes` | optional | boolean — true nếu dùng Svelte 5 runes ($state, $derived) |
| `kit_route` | optional | boolean — true nếu component nằm trong SvelteKit `+page.svelte` / `+layout.svelte` |
| `library_wrap` | optional | Object spec — xem §4.1 (`{library, library_version, primitive, primitive_api}`) |
| `dependencies` | ✅ | array npm package paths |

#### `solid`
| Field | Required | Mô tả |
|---|---|---|
| `component_name` | ✅ | PascalCase |
| `file_path` | ✅ | path từ repo root |
| `export_type` | ✅ | `default` \| `named` |
| `props_interface_name` | optional | tên TypeScript interface (Required khi `language=typescript`) |
| `library_wrap` | optional | Object spec — xem §4.1 (`{library, library_version, primitive, primitive_api}`) |
| `dependencies` | ✅ | array npm package paths |

#### `other` / custom framework
Schema cho phép framework key tự do. Bắt buộc tối thiểu: `component_name` (hoặc tương đương identifier), `file_path`, `dependencies`. Bổ sung field theo nhu cầu — skill validate qua `_shared/stack-profile-schema.md` `framework: other` definition.

### Multi-stack example

1 component implement ở cả Angular + React (vd: design system mono-repo phục vụ 2 app):

```json
{
  "abstract": {
    "semantic_intent": "Hiển thị tiến độ upload file dạng linear progress với label %.",
    "category": "feedback",
    "variants": ["linear", "circular"],
    "states": ["idle", "uploading", "success", "error"],
    "inputs": [
      { "name": "value", "type": "number", "required": true, "description": "0-100" },
      { "name": "variant", "type": "'linear' | 'circular'", "required": false, "default": "linear" }
    ],
    "outputs": [],
    "accessibility": {
      "role": "progressbar",
      "aria": ["aria-valuenow", "aria-valuemin", "aria-valuemax"],
      "keyboard": "none"
    },
    "tags": ["progress", "upload", "feedback", "loading"]
  },
  "stack_specific": {
    "angular": {
      "selector": "app-progress-bar",
      "class_name": "ProgressBarComponent",
      "module": "SharedModule",
      "file_path": "packages/ds-angular/src/lib/progress-bar/progress-bar.component.ts",
      "library_wrap": {
        "library": "primeng",
        "library_version": "16.0.0",
        "primitive": "p-progressbar",
        "primitive_api": "./library_apis/primeng@16.0.0/p-progressbar.json"
      },
      "dependencies": ["@angular/common", "primeng/progressbar"]
    },
    "react": {
      "component_name": "ProgressBar",
      "file_path": "packages/ds-react/src/components/ProgressBar/ProgressBar.tsx",
      "export_type": "named",
      "props_interface_name": "ProgressBarProps",
      "module_format": "esm",
      "style_strategy": "css-modules",
      "style_file_path": "packages/ds-react/src/components/ProgressBar/ProgressBar.module.scss",
      "dependencies": ["react"]
    }
  },
  "tokens_used": [
    "semantic.color.action.primary",
    "semantic.color.status.success",
    "semantic.color.status.error",
    "semantic.layout.radius-base"
  ],
  "metadata": {
    "version": "1.0.0",
    "status": "active",
    "last_updated": "2026-05-09T10:30:00Z",
    "source": "build-skill",
    "related_features": ["ING_05_PROG_01"],
    "deprecation": null
  }
}
```

**Lưu ý multi-stack:** abstract layer **giống hệt** giữa các framework. Nếu inputs/variants/states khác biệt → 2 component riêng (vd: `progress-bar-angular` + `progress-bar-react`), KHÔNG mix vào 1 entry.

### `tokens_used` (cross-stack)

Array path token tham chiếu trong implementation. Build skill auto-populate khi scaffold. Dùng để:
- Reverse lookup: "đổi token X thì component nào ảnh hưởng?"
- Validation: token đã xoá khỏi master nhưng component vẫn reference → drift warning.

### `style_property_inventory` (cross-stack)

Object keyed by CSS property name. Mỗi key map sang array các occurrence của property đó trong file style của component. Mỗi occurrence ghi:

| Field | Required | Mô tả |
|---|---|---|
| `value` | ✅ | Raw value declared in source (vd `"4px"`, `"#ee0033"`, `"1px solid currentColor"`). Nếu source là token reference, ghi value sau resolve nếu khả thi, else giữ raw reference syntax. |
| `source` | ✅ | `"{tier.path.to.token}"` (token reference, kể cả CSS var / SCSS var / theme path) hoặc `"literal"` (hardcode). |
| `tokenized` | ✅ | `true` nếu `source` là token reference resolve được sang `master_token.json`; `false` nếu hardcode hoặc reference orphan. |
| `file` | ✅ | Path tới style file relative repo root (theo U2). |
| `line` | ✅ | Số dòng property xuất hiện. |

**Purpose:** Cho phép `normalizer` (sub-agent của `/ntapp-ds-bootstrap`) chạy Rule 4.14 (component-tier coverage) — cluster wrappers cùng primitive, detect inconsistent / un-tokenized properties, propose `component.<primitive>.<property>` token. Khác với `tokens_used` (chỉ list token đã match), field này list **mọi** style property occurrence — kể cả hardcode — để rule reason được về coverage gap.

**Producer:** `component-discoverer` populate khi parse style file (xem `/ntapp-ds-bootstrap/agents/component-discoverer.md` §4.2).

**Consumer:** `normalizer` Rule 4.14 (xem `_shared/best-practices.md`).

**Strip rule:** field này strip khi ghi `components_metadata.json` latest (Step 7) — chỉ giữ trong `components_metadata_parts/01_discovered.json` để pipeline nội bộ dùng. Tránh bloat file canonical.

### `metadata` (per-component lifecycle)

| Field | Required | Mô tả |
|---|---|---|
| `version` | ✅ | semver. Bump khi có MODIFIED. |
| `status` | ✅ | `active` \| `deprecated` \| `experimental` |
| `last_updated` | ✅ | ISO 8601 timestamp |
| `source` | ✅ | `bootstrap` \| `build-skill` \| `manual` |
| `related_features` | optional | array feature_id (BMAD mode) hoặc proposal_id |
| `deprecation` | optional | `null` hoặc `{ replaced_by, deprecated_at, removal_target_version }` |

## 6. Cross-stack support

1 component có thể implement ở nhiều framework. Ví dụ `progress-bar` có cả `stack_specific.angular` + `stack_specific.react`.

**Convention:** abstract phải đồng nhất giữa các implementation. Nếu Angular có `variants: linear|circular` thì React cũng phải hỗ trợ (hoặc explicit declare khác biệt qua `metadata.deprecation` hay component split).

→ Skill validate: với mỗi component, parse `stack_specific` keys, đảm bảo abstract đáp ứng được cho từng stack.

## 7. Validation rules

Skill reject `components_metadata.json` nếu:
- Component id không kebab-case.
- 2 component cùng id.
- Thiếu `abstract.semantic_intent` hoặc rỗng.
- Tokens trong `tokens_used` không tồn tại trong `master_token.json`.
- `stack_specific` rỗng (component không có implementation nào và không phải `metadata.status = experimental`).
- File path trong `stack_specific.<fw>.file_path` không tồn tại trên disk (trừ khi `metadata.status = deprecated`).
- `library_wrap` populated nhưng thiếu `library_version`.
- `primitive_api` populated nhưng file ref không tồn tại trên disk (drift với `library_apis/` folder).
- `library_wrap.library_version` không match folder version trong `primitive_api` path.

## 8. Atomic update protocol

`metadata-registrar` (sub-agent của build skill) update file theo transaction:

```
1. Read current components_metadata.json + lock file via .bmm-build.lock
2. Validate input (delta to apply)
3. Snapshot current → archive/components_metadata_v(N+1).json
4. Apply changes in-memory
5. Re-validate (rules ở mục 7)
6. Atomic write: tmp file → rename to components_metadata.json
7. Release lock
```

Nếu validate fail ở step 5 → discard changes, không ghi đè. Build skill exit ≠ 0.

## 9. Versioning (dual-write)

```
{design_system_root}/
├── components_metadata.json                ← LATEST
├── components_metadata_parts/              ← atomic outputs gần nhất
│   ├── 01_discovered.json                  (component-discoverer)
│   └── 02_validated.json                   (after validation)
└── archive/
    ├── components_metadata_v1.json
    ├── components_metadata_v2.json
    └── ...
```

## 10. Migration từ format hiện tại (pre-schema)

Nếu repo đã có `components_metadata.json` không theo schema v1.0 → bootstrap chạy:
1. Backup file cũ → `archive/components_metadata_v0_legacy.json`.
2. Best-effort parse (heuristic theo key có/không có).
3. Output report các field cần DSO bổ sung manual (vd: `accessibility`, `tags` thường thiếu trong format cũ).
4. Generate file v1.0-conformant với placeholder cho field thiếu.

DSO review + fill placeholder trước khi commit.

## 11. Edge cases

| Case | Xử lý |
|---|---|
| Component có abstract nhưng `stack_specific = {}` | `metadata.status: experimental`. Cho phép — DS có "spec" trước implement. |
| Component có nhiều framework nhưng abstract khác nhau | Reject. Force unify abstract. |
| Token trong `tokens_used` bị xoá khỏi master | Bootstrap warn, không reject. Add to drift report. |
| 2 component có cùng `semantic_intent` (functional duplicate) | Bootstrap warn (vào `bootstrap_report.md` warnings section). |

---

## 12. Layout primitive canonical inventory (v1.2+)

Category `layout-primitive` định nghĩa thành phần composition (compose siblings với alignment/gap) — tách biệt khỏi component nghiệp vụ (`input`, `display`, `data`, ...). 10 primitives chuẩn dưới đây phải có entry trong mọi `components_metadata.json` (auto-populate khi bootstrap; ds-build-component lazy-materialize implementation code theo `stack-profile.layout_library.strategy`).

**Tại sao tách category:** Layout primitive là framework-portable contract (Row/Stack/Grid là khái niệm CSS Flexbox/Grid universal), KHÔNG phụ thuộc UI library. Component nghiệp vụ wraps UI library primitive (vd `c-button` wraps `nz-button`); layout primitive map qua `layout_library.primitive_mapping` (vd `Stack → Chakra HStack`, `Stack → flex flex-row gap-md` cho Tailwind).

**Naming convention:** PascalCase (vd `Stack`, `FormField`). KHÔNG kebab-case như component nghiệp vụ — để phân biệt nguồn gốc + match convention component framework (React `<Stack>`, Vue `<Stack>`, Angular selector cần thêm prefix: vd `<app-stack>` resolve qua `stack_specific.angular.selector` theo `selector_prefix` từ stack-profile).

### 12.1. Core primitives (always-present, 8)

```json
"Stack": {
  "abstract": {
    "semantic_intent": "Single-axis composition (vertical default, horizontal qua direction prop). Composer chủ lực cho mọi screen.",
    "category": "layout-primitive",
    "variants": [],
    "states": ["idle"],
    "inputs": [
      { "name": "direction", "type": "'column' | 'row'", "required": false, "default": "'column'" },
      { "name": "gap", "type": "TokenRef<spacing>", "required": false, "default": "'md'", "description": "Reference token spacing.xs/sm/md/lg/xl/2xl" },
      { "name": "align", "type": "'start' | 'center' | 'end' | 'baseline' | 'stretch'", "required": false, "default": "'stretch'", "description": "Cross-axis alignment" },
      { "name": "justify", "type": "'start' | 'center' | 'end' | 'between' | 'around' | 'evenly'", "required": false, "default": "'start'", "description": "Main-axis alignment" },
      { "name": "wrap", "type": "boolean", "required": false, "default": "false" }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "none", "aria": [], "keyboard": "none" },
    "tags": ["layout-primitive", "composition", "flex"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

```json
"Cluster": {
  "abstract": {
    "semantic_intent": "Wrap-horizontal composition cho chip / tag / multi-button toolbar. Wrap mặc định = true (khác Stack).",
    "category": "layout-primitive",
    "variants": [],
    "states": ["idle"],
    "inputs": [
      { "name": "gap", "type": "TokenRef<spacing>", "required": false, "default": "'sm'" },
      { "name": "align", "type": "'start' | 'center' | 'end' | 'baseline'", "required": false, "default": "'center'" }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "none", "aria": [], "keyboard": "none" },
    "tags": ["layout-primitive", "composition", "wrap", "toolbar"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

```json
"Grid": {
  "abstract": {
    "semantic_intent": "Explicit column grid (form 2-col, dashboard tile). CSS Grid based.",
    "category": "layout-primitive",
    "variants": [],
    "states": ["idle"],
    "inputs": [
      { "name": "columns", "type": "number | string", "required": true, "description": "Number (vd 2) hoặc template string (vd '1fr 2fr 1fr')" },
      { "name": "gap", "type": "TokenRef<spacing>", "required": false, "default": "'md'" },
      { "name": "row_gap", "type": "TokenRef<spacing>", "required": false, "description": "Override row-axis gap (default = gap)" },
      { "name": "min_item_width", "type": "TokenRef<spacing> | string", "required": false, "description": "Auto-responsive: dùng minmax(min_item_width, 1fr)" }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "none", "aria": [], "keyboard": "none" },
    "tags": ["layout-primitive", "grid", "column"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

```json
"Spacer": {
  "abstract": {
    "semantic_intent": "Flex-grow filler (đẩy siblings ra 2 đầu của Stack/Cluster).",
    "category": "layout-primitive",
    "variants": [],
    "states": ["idle"],
    "inputs": [
      { "name": "min", "type": "TokenRef<spacing>", "required": false, "description": "Min size khi không có flex space" }
    ],
    "outputs": [],
    "accepts_children": false,
    "accessibility": { "role": "presentation", "aria": [], "keyboard": "none" },
    "tags": ["layout-primitive", "spacer", "flex-grow"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

```json
"Center": {
  "abstract": {
    "semantic_intent": "Center children trên 1 hoặc 2 axes.",
    "category": "layout-primitive",
    "variants": [],
    "states": ["idle"],
    "inputs": [
      { "name": "axis", "type": "'both' | 'horizontal' | 'vertical'", "required": false, "default": "'both'" },
      { "name": "min_height", "type": "TokenRef<spacing> | string", "required": false }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "none", "aria": [], "keyboard": "none" },
    "tags": ["layout-primitive", "center", "alignment"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

```json
"Box": {
  "abstract": {
    "semantic_intent": "Generic styled container (padding/margin/border/background) — atomic styling primitive, không phải layout primitive đúng nghĩa nhưng đặt cùng category để adapter pipeline xử lý chung.",
    "category": "layout-primitive",
    "variants": [],
    "states": ["idle"],
    "inputs": [
      { "name": "padding", "type": "TokenRef<spacing>", "required": false },
      { "name": "margin", "type": "TokenRef<spacing>", "required": false },
      { "name": "border", "type": "TokenRef<border>", "required": false },
      { "name": "radius", "type": "TokenRef<radius>", "required": false },
      { "name": "background", "type": "TokenRef<color>", "required": false, "description": "Semantic color token, vd 'surface.subtle'" }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "none", "aria": [], "keyboard": "none" },
    "tags": ["layout-primitive", "box", "container", "styling"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

```json
"FormField": {
  "abstract": {
    "semantic_intent": "Atomic form field — label + control + helper text + error binding. Standard form composition unit.",
    "category": "layout-primitive",
    "variants": [],
    "states": ["idle", "error", "disabled"],
    "inputs": [
      { "name": "label", "type": "string", "required": true },
      { "name": "label_position", "type": "'top' | 'left'", "required": false, "default": "'top'" },
      { "name": "required", "type": "boolean", "required": false, "default": "false", "description": "Render '*' marker next to label" },
      { "name": "helper", "type": "string", "required": false },
      { "name": "error_ref", "type": "string", "required": false, "description": "Bind to error state in data_bindings (resolve runtime)" },
      { "name": "gap", "type": "TokenRef<spacing>", "required": false, "default": "'xs'", "description": "Gap between label/control/helper" }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "group", "aria": ["aria-labelledby", "aria-describedby", "aria-invalid"], "keyboard": "Tab through control" },
    "tags": ["layout-primitive", "form", "field", "label"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

```json
"FieldGrid": {
  "abstract": {
    "semantic_intent": "Multi-column form layout với shared label baseline (multiple FormField cùng row, label aligned).",
    "category": "layout-primitive",
    "variants": [],
    "states": ["idle"],
    "inputs": [
      { "name": "columns", "type": "number", "required": false, "default": "2" },
      { "name": "gap", "type": "TokenRef<spacing>", "required": false, "default": "'md'" },
      { "name": "row_gap", "type": "TokenRef<spacing>", "required": false },
      { "name": "label_alignment", "type": "'top' | 'left'", "required": false, "default": "'top'", "description": "Force consistent label_position across all child FormFields" }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "group", "aria": [], "keyboard": "Tab through controls in grid order" },
    "tags": ["layout-primitive", "form", "grid", "field-row"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

### 12.2. Advanced primitives (lazy-materialize on first reference, 2)

```json
"Sidebar": {
  "abstract": {
    "semantic_intent": "Fixed-width + fluid-content split với responsive collapse tại breakpoint. Composition primitive cho dashboard / detail-pane layout.",
    "category": "layout-primitive",
    "variants": [],
    "states": ["expanded", "collapsed"],
    "inputs": [
      { "name": "side", "type": "'start' | 'end'", "required": false, "default": "'start'", "description": "Which side is the fixed-width pane" },
      { "name": "side_width", "type": "TokenRef<spacing> | string", "required": true, "description": "Width of fixed pane (vd '240px' hoặc 'sidebar.md' token)" },
      { "name": "content_min", "type": "TokenRef<spacing> | string", "required": false, "description": "Min width content pane trước khi collapse" },
      { "name": "gap", "type": "TokenRef<spacing>", "required": false, "default": "'md'" },
      { "name": "breakpoint", "type": "TokenRef<breakpoint>", "required": false, "description": "Width below which side collapses" }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "none", "aria": [], "keyboard": "none" },
    "tags": ["layout-primitive", "sidebar", "responsive", "advanced"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

```json
"Switcher": {
  "abstract": {
    "semantic_intent": "Auto-flip row → column khi container width < threshold. Container-query based responsive primitive (không dùng viewport media query).",
    "category": "layout-primitive",
    "variants": [],
    "states": ["row", "column"],
    "inputs": [
      { "name": "threshold", "type": "TokenRef<breakpoint> | string", "required": true, "description": "Container width threshold để flip axis" },
      { "name": "gap", "type": "TokenRef<spacing>", "required": false, "default": "'md'" },
      { "name": "limit", "type": "number", "required": false, "description": "Max children trước khi force column ngay cả trên wide screens" }
    ],
    "outputs": [],
    "accepts_children": true,
    "accessibility": { "role": "none", "aria": [], "keyboard": "none" },
    "tags": ["layout-primitive", "switcher", "responsive", "container-query", "advanced"]
  },
  "tokens_used": [],
  "metadata": { "version": "1.0.0", "status": "active", "source": "canonical-inventory" }
}
```

### 12.3. Materialization rules (ds-build-component)

- **Always-present (8 core):** Bootstrap auto-populate entry vào `components_metadata.json` từ inventory này. Implementation code (file component) chỉ generate khi có ≥1 `ui_schema_*.json` reference primitive đó trong `layout` tree.
- **Lazy (2 advanced — Sidebar, Switcher):** Entry vào metadata + code đều lazy — chỉ tạo khi reference đầu tiên.
- **Strategy quyết định code generation:**
  - `native-component` (vd Chakra) → KHÔNG generate file, `stack_specific.<fw>.library_wrap` trỏ tới component native, scaffolder chỉ wrap re-export.
  - `utility-class` (vd Tailwind) → generate wrapper component file áp utility class theo `primitive_mapping` template.
  - `generated-component` (vd CSS vanilla) → generate full component file dùng CSS vars cho gap/align (resolve từ master_token.json).
  - `raw-utility` → KHÔNG generate component file; ui_schema_agent emit `layout` tree với primitive name, Stage 5 dev apply utility class trực tiếp vào first child (legacy escape hatch).
- **Custom primitive (vd `Cover`, `Reel` từ Every Layout)**: Không trong inventory chuẩn → DSO add manual qua proposal `[NEW]` với `category: layout-primitive`. ds-build-component xử lý theo strategy mặc định.

### 12.4. Validation rules cho layout-primitive

Bổ sung quy tắc validate trong §7:
- Primitive name không trong inventory §12 + không có proposal `[NEW]` declaring it → warn (có thể là typo).
- `category: layout-primitive` nhưng `inputs` thiếu prop chuẩn (vd Stack thiếu `direction`) → warn (component có thể không tương thích với generic layout tree).
- `category: layout-primitive` không cần `library_wrap` (KHÔNG enforce — strategy `native-component` mới có library_wrap, các strategy khác không).
- `category: layout-primitive` `tokens_used` thường rỗng cho `generated-component` (token resolve runtime qua CSS vars, không hard-link compile-time).

---

**End of component metadata schema v1.2.**
