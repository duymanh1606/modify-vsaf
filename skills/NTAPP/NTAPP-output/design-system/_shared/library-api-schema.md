# Library API Schema

**Schema version:** 1.0
**File:** `{design_system_root}/library_apis/{library}@{version}/{Component}.json`
**Producer:** `/ntapp-ds-bootstrap` (sub-agent: `library-api-parser`)
**Consumers:** `/ntapp-ds-bootstrap` (sub-agent: `component-discoverer`), `/ntapp-ui-generation` (Stage 4b Agent 1), `/ntapp-ds-build-component` (sub-agents: `metadata-registrar`, `component-scaffolder`)

---

## 1. Mục đích

Capture API spec của primitive component từ UI library (vd: antd `Button`, PrimeNG `p-button`, Material `Button`) — props với type/enum values/defaults, slots, events. Source of truth là TypeScript declaration của library (`.d.ts` files trong `node_modules/`).

Wrapper component trong repo (`vt-button`, `app-button`, ...) reference file này để biết primitive có sẵn prop gì → expose minimal API, KHÔNG reinvent style. Stage 4b Agent 1 dùng để quyết định "thêm prop vào wrapper" (`[MODIFIED]`) thay vì "tạo variant mới" (`[NEW]`) khi primitive đã có solution.

## 2. Vòng đời

| Event | Hành vi |
|---|---|
| Bootstrap onboard repo | `library-api-parser` parse `node_modules/{lib}/**/*.d.ts` → emit 1 JSON file per primitive component |
| Library upgrade (semver bump) | DSO chạy `/ntapp-ds-bootstrap --refresh-library-api` → re-parse + diff report |
| Parse fail / lib không có TS types | HITL prompt DSO cung cấp curated file (fallback `parser_method: "manual-curated"`) |
| Lib downgrade / remove | Folder version cũ giữ lại làm reference (audit), folder mới sinh khi upgrade |

## 3. Path structure

```
{design_system_root}/library_apis/
├── antd@5.12.0/
│   ├── _manifest.json              (list components parsed + version + parser status)
│   ├── Button.json
│   ├── Input.json
│   ├── Modal.json
│   └── ...
├── primeng@16.0.0/
│   ├── _manifest.json
│   ├── p-button.json
│   └── ...
```

Version trong folder name = **exact version đã parse** (lấy từ `package.json`). Lib upgrade tạo folder mới, file cũ giữ làm reference (so sánh diff API).

Component file name: theo convention export của lib.
- React libs (antd, mui, chakra): PascalCase (`Button.json`).
- Angular libs (primeng): kebab-case theo selector (`p-button.json`).
- Vue libs: PascalCase component name.

## 4. JSON structure

```json
{
  "$schema_version": "1.0",
  "library": "antd",
  "library_version": "5.12.0",
  "component": "Button",
  "import_path": "antd",
  "source_d_ts": "node_modules/antd/lib/button/button.d.ts",
  "parsed_at": "2026-05-22T10:30:00Z",
  "parser_method": "auto",
  "props": { ... },
  "slots": [ ... ],
  "events": [ ... ],
  "notes": [ ... ]
}
```

### Top-level fields

| Field | Required | Mô tả |
|---|---|---|
| `$schema_version` | ✅ | `"1.0"` |
| `library` | ✅ | Tên lib khớp `stack-profile.ui_library.name` |
| `library_version` | ✅ | semver exact |
| `component` | ✅ | Tên primitive component (vd `Button`, `p-button`) |
| `import_path` | ✅ | Path để import (vd `"antd"`, `"primeng/button"`) |
| `source_d_ts` | ✅ nếu `parser_method=auto` | Path relative tới code repo root, trỏ `.d.ts` đã parse |
| `parsed_at` | ✅ | ISO timestamp |
| `parser_method` | ✅ | `"auto"` \| `"manual-curated"` |
| `props` | ✅ | Object keyed by prop name (xem §5) |
| `slots` | optional | Array slot spec (xem §6). Empty array nếu không có |
| `events` | optional | Array event spec (xem §7). Empty array nếu không emit |
| `notes` | optional | Array caveat từ parser (xem §8) |

## 5. `props` block

Object keyed by prop name (camelCase). Mỗi value là object spec.

```json
"shape": {
  "type": "enum",
  "values": ["default", "circle", "round"],
  "required": false,
  "default": "default",
  "description": "Set the shape of button",
  "since": "5.0.0"
}
```

### Prop spec fields

| Field | Required | Mô tả |
|---|---|---|
| `type` | ✅ | Enum: `enum` \| `string` \| `number` \| `boolean` \| `function` \| `ReactNode` \| `Slot` \| `TemplateRef` \| `object` \| `array` \| `unknown` |
| `values` | ✅ nếu `type=enum` | Array literal values (vd `["sm", "md", "lg"]`) |
| `required` | ✅ | bool |
| `default` | optional | Default value (chỉ ghi khi lib có explicit default) |
| `description` | optional | First sentence từ JSDoc |
| `since` | optional | Version added (từ JSDoc `@since`) |
| `deprecated` | optional | String reason (từ JSDoc `@deprecated`) |
| `signature` | ✅ nếu `type=function` | Function signature dạng TS string (vd `"(event: MouseEvent) => void"`) |
| `nested` | optional, chỉ nếu `type=object` | Recursive prop spec cho object shape |
| `tier_hint` | optional | Gợi ý "prop này control style nào": `radius` \| `color` \| `spacing` \| `size` \| `behavior` \| `content`. Để Stage 4b Agent 1 map: nhu cầu "bo góc" → tìm prop tier_hint=radius |

### Type semantics

- `enum`: union of literals (vd `'default' | 'circle' | 'round'`).
- `string`/`number`/`boolean`: primitive scalar.
- `function`: callback/handler — `signature` field bắt buộc.
- `ReactNode`/`Slot`/`TemplateRef`: content slot reference (framework-specific).
- `object`: complex shape — `nested` field optional với recursive spec.
- `array`: list type — không có spec sâu hơn (parser conservative).
- `unknown`: parser không resolve được (generic phức tạp, conditional type, ...) — vẫn ghi để biết prop tồn tại.

### `tier_hint` mapping (heuristic — parser auto-infer khi có thể)

Parser dùng tên prop để infer:

| Prop name pattern | `tier_hint` |
|---|---|
| `shape`, `rounded`, `pill`, `radius`, `cornerRadius` | `radius` |
| `color`, `variant`, `type`, `theme`, `tone` | `color` |
| `size`, `density`, `compact` | `size` |
| `padding`, `gap`, `margin`, `spacing` | `spacing` |
| `disabled`, `loading`, `autofocus`, `readonly` | `behavior` |
| `icon`, `prefix`, `suffix`, `children` | `content` |
| (other) | omit field |

Inference imperfect — Stage 4b Agent 1 vẫn phải xem `values` + `description` để confirm.

## 6. `slots` block

Array of slot spec. Cho React: chỉ `children` (default slot). Cho Vue/Angular: nhiều slot named.

```json
"slots": [
  { "name": "default", "type": "ReactNode", "description": "Button label content" },
  { "name": "icon", "type": "ReactNode", "description": "Leading icon" }
]
```

Per slot:
| Field | Required | Mô tả |
|---|---|---|
| `name` | ✅ | Slot name (`"default"` cho default slot) |
| `type` | optional | Type spec |
| `description` | optional | từ JSDoc / `<slot>` element comment |

Empty array nếu component không có content slot.

## 7. `events` block

Array of event spec. Chủ yếu cho Vue (`defineEmits`) và Angular (`@Output`). React: events biểu diễn dưới dạng prop với `on*` prefix → đã trong `props` block.

```json
"events": [
  { "name": "click", "payload_type": "MouseEvent", "description": "Fired when button clicked" }
]
```

Per event:
| Field | Required | Mô tả |
|---|---|---|
| `name` | ✅ | Event name |
| `payload_type` | optional | TS type payload |
| `description` | optional | từ JSDoc |

## 8. `notes` block

Array string. Parser ghi caveat hữu ích cho human review:

```json
"notes": [
  "Generic parameter `<T extends HTMLButtonElement>` flattened to HTMLButtonElement",
  "Prop `loading` type union `boolean | { delay: number }` — partial parse, see source d.ts for full spec",
  "Prop `htmlType` skipped — alias of HTML `type` attribute, low utility for DS audit"
]
```

## 9. Validation rules

Skill reject file nếu:
- Thiếu top-level required field (`library`, `library_version`, `component`, `props`, `parser_method`).
- `props` rỗng object (component không có prop nào — probably parse failed). Cho phép nếu component thực sự không prop (vd container) — note "intentionally empty".
- `type=enum` mà thiếu `values` hoặc `values` rỗng.
- `type=function` mà thiếu `signature`.
- `parser_method=auto` mà `source_d_ts` không trỏ file thật.
- `library_version` không khớp folder name (`antd@5.12.0/Button.json` có `library_version: "5.13.0"` → reject).

## 10. Cross-reference

- `components_metadata.json.{id}.stack_specific.{fw}.library_wrap.primitive_api` — relative path trỏ tới file này (vd `"./library_apis/antd@5.12.0/Button.json"`).
- `/ntapp-ui-generation` Stage 4b Agent 1: đọc file để biết primitive có prop gì → quyết định `[MODIFIED]` wrapper expose vs `[NEW]` variant.
- `/ntapp-ds-build-component` `component-scaffolder`: đọc file để emit code wrapper forward đầy đủ prop (không reinvent).

## 11. Manual-curated fallback

Nếu auto-parse fail (lib không TS, generic không resolve, parser exception), DSO viết file thủ công với cùng schema:
- `parser_method: "manual-curated"`
- `source_d_ts: null`
- DSO maintain tay khi lib upgrade (parser sẽ skip overwrite file marked manual-curated).
- Trong `_manifest.json`, component được mark `components_manual: [...]`.

## 12. `_manifest.json` (per folder)

```json
{
  "$schema_version": "1.0",
  "library": "antd",
  "library_version": "5.12.0",
  "parsed_at": "2026-05-22T10:30:00Z",
  "components_parsed_full": ["Button", "Input", "Checkbox"],
  "components_parsed_partial": ["Form"],
  "components_failed": ["Upload"],
  "components_manual": ["Tooltip"],
  "parser_warnings": [
    { "component": "Upload", "reason": "Heavy generic with conditional type" },
    { "component": "Form", "reason": "FormItem child type union too deep, parsed top-level only" }
  ],
  "total_components_in_lib": 56,
  "coverage_pct": 0.41
}
```

`coverage_pct` = `(full + partial + manual) / total_components_in_lib`. Audit metric, không enforce minimum.

## 13. Versioning

Schema dùng semver-like:

| Bump | Khi nào | Backward compat |
|---|---|---|
| Major (1.0 → 2.0) | Đổi cấu trúc field, đổi enum value của `type` | ❌ Consumer phải update |
| Minor (1.0 → 1.1) | Thêm field optional (vd `tier_hint`), thêm enum value mới | ✅ |
| Patch (1.0 → 1.0.1) | Wording, typo | ✅ |

## 14. Examples

### Antd Button (full parse)

```json
{
  "$schema_version": "1.0",
  "library": "antd",
  "library_version": "5.12.0",
  "component": "Button",
  "import_path": "antd",
  "source_d_ts": "node_modules/antd/lib/button/button.d.ts",
  "parsed_at": "2026-05-22T10:30:00Z",
  "parser_method": "auto",
  "props": {
    "type": {
      "type": "enum",
      "values": ["primary", "default", "dashed", "link", "text"],
      "required": false,
      "default": "default",
      "description": "Can be set to primary, default, dashed, link or text",
      "tier_hint": "color"
    },
    "shape": {
      "type": "enum",
      "values": ["default", "circle", "round"],
      "required": false,
      "default": "default",
      "description": "Set the shape of button",
      "tier_hint": "radius"
    },
    "size": {
      "type": "enum",
      "values": ["large", "middle", "small"],
      "required": false,
      "default": "middle",
      "description": "Set the size of button",
      "tier_hint": "size"
    },
    "danger": {
      "type": "boolean",
      "required": false,
      "default": false,
      "description": "Set the danger status of button",
      "tier_hint": "color"
    },
    "disabled": {
      "type": "boolean",
      "required": false,
      "default": false,
      "tier_hint": "behavior"
    },
    "loading": {
      "type": "unknown",
      "required": false,
      "description": "Set the loading status (boolean or { delay: number })"
    },
    "icon": {
      "type": "ReactNode",
      "required": false,
      "tier_hint": "content"
    },
    "onClick": {
      "type": "function",
      "signature": "(event: MouseEvent<HTMLElement>) => void",
      "required": false,
      "tier_hint": "behavior"
    }
  },
  "slots": [
    { "name": "default", "type": "ReactNode", "description": "Button label" }
  ],
  "events": [],
  "notes": [
    "Prop `loading` type union `boolean | { delay: number }` — marked unknown, see source d.ts for full spec"
  ]
}
```

### PrimeNG p-button (partial)

```json
{
  "$schema_version": "1.0",
  "library": "primeng",
  "library_version": "16.0.0",
  "component": "p-button",
  "import_path": "primeng/button",
  "source_d_ts": "node_modules/primeng/button/button.d.ts",
  "parsed_at": "2026-05-22T10:30:00Z",
  "parser_method": "auto",
  "props": {
    "label": { "type": "string", "required": false, "tier_hint": "content" },
    "icon": { "type": "string", "required": false, "tier_hint": "content" },
    "iconPos": {
      "type": "enum",
      "values": ["left", "right", "top", "bottom"],
      "required": false,
      "default": "left",
      "tier_hint": "content"
    },
    "rounded": { "type": "boolean", "required": false, "default": false, "tier_hint": "radius" },
    "raised": { "type": "boolean", "required": false, "default": false, "tier_hint": "color" },
    "severity": {
      "type": "enum",
      "values": ["secondary", "success", "info", "warning", "danger", "help"],
      "required": false,
      "tier_hint": "color"
    },
    "disabled": { "type": "boolean", "required": false, "default": false, "tier_hint": "behavior" },
    "loading": { "type": "boolean", "required": false, "default": false, "tier_hint": "behavior" }
  },
  "slots": [],
  "events": [
    { "name": "onClick", "payload_type": "MouseEvent" },
    { "name": "onFocus", "payload_type": "FocusEvent" }
  ],
  "notes": [
    "PrimeNG `p-button` selector. Inputs detected from @Input() decorators in button.d.ts",
    "Prop `style` typed as `any` — skipped (low utility)",
    "Prop `styleClass` typed as `string` — generic style escape hatch, included but tier_hint omitted"
  ]
}
```

---

**End of library API schema v1.0.**
