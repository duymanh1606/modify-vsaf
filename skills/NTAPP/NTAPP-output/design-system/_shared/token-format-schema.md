# Token Format Schema

**Schema version:** 1.0
**File:** `{design_system_root}/master_token.json`
**Producer:** `/ntapp-ds-bootstrap` (sub-agents: `normalizer`, `conflict-resolver`), `/ntapp-ds-build-component` (sub-agent: `token-applier`)
**Consumers:** all skills, pre-commit hook, CSS/SCSS build pipeline

---

## 1. Mục đích

Định nghĩa format chính thức của `master_token.json` (NTAPP v1 — status quo, không phải W3C). Đảm bảo:
- Skill produce/consume nhất quán.
- Validation rule rõ ràng (no orphan reference, no circular).
- Bidirectional convert sang W3C qua `w3c-converter.md` (edge converter, không thay thế format chính).

## 2. Vòng đời

| Event | Hành vi |
|---|---|
| Bootstrap repo | `raw-style-extractor` + `normalizer` (+ `conflict-resolver` nếu có external) → tạo file. |
| Stage 4b approve TOKEN delta | `token-applier` patch file (1 token / nhiều token). |
| Designer dùng AI ngoài (output W3C) | `w3c-converter` import → 3-way reconcile. |
| Export sang Tokens Studio / Style Dictionary | `w3c-converter` export. |

## 3. Cấu trúc tổng thể

```json
{
  "metadata": { ... },
  "global": { ... },
  "semantic": { ... },
  "component": { ... }
}
```

**3 tier bắt buộc:**
- **`global`** — primitives (raw color, raw spacing, raw type scale). Không reference tier khác.
- **`semantic`** — UX intent (`action.primary`, `status.success`). Reference vào `global`.
- **`component`** — component-specific (`toast.bg`, `upload.padding`). Reference vào `semantic` hoặc `global`.

→ **Reference chỉ đi xuống tier:** `component` → `semantic` → `global`. KHÔNG ngược.

## 4. `metadata` block

```json
{
  "metadata": {
    "name": "BMS Design System Tokens",
    "version": "1.1.0",
    "author": "System Architect",
    "last_updated": "2026-04-14",
    "schema_version": "1.0"
  }
}
```

| Field | Required | Mô tả |
|---|---|---|
| `name` | ✅ | tên DS, free text |
| `version` | ✅ | semver — content version (bump khi token đổi) |
| `author` | ✅ | tên cá nhân hoặc role |
| `last_updated` | ✅ | ISO date `YYYY-MM-DD` |
| `schema_version` | ✅ | version của schema này (1.0). Khác với `version` ở trên. |

## 5. `global` block — primitives

### Categories bắt buộc

```json
{
  "global": {
    "color": { ... },
    "font": { "family": {...}, "size": {...}, "weight": {...} },
    "spacing": { "unit": "...", "scale": {...} },
    "shadow": { ... },
    "z-index": { ... },
    "breakpoint": { ... }
  }
}
```

### `color`
- Mỗi color family là object với scale `100`, `200`, ..., `900` (hoặc `050`, `020` cho extreme light).
- Color scalar (white, black, transparent) là string trực tiếp.
- Color name: kebab-case (`viettel-red`, `pine-blue`).
- Value: hex `#rrggbb` hoặc `transparent` hoặc `rgba(...)`.

```json
{
  "viettel-red": {
    "500": "#ee0033",
    "400": "#f1335c",
    "100": "#fde5eb"
  },
  "white": "#ffffff",
  "transparent": "transparent"
}
```

### `font`
- `family` — object key→value (CSS font-family string).
- `size` — object numeric key → px value (vd `"16": "16px"`).
- `weight` — object name → numeric (vd `"medium": 500`).

### `spacing`
- `unit` — base unit (vd `"4px"`).
- `scale` — multiples object key → value.
- Naming: numeric key tương ứng multiplier (`"4": "16px"` = unit × 4).
- Best practice: tuân thủ multiplier nhất quán (4, 8). `normalizer` flag deviation.

### `shadow`, `z-index`, `breakpoint`
- `shadow`: name → CSS box-shadow string.
- `z-index`: name → integer.
- `breakpoint`: name → CSS length string.

## 6. `semantic` block — UX intent

```json
{
  "semantic": {
    "color": { "action": {...}, "status": {...}, "text": {...}, "background": {...}, "border": {...} },
    "typography": { "h1": {...}, "body-m": {...} },
    "layer": { ... },
    "elevation": { ... },
    "layout": { ... }
  }
}
```

### Categories bắt buộc

| Category | Mục đích | Ví dụ |
|---|---|---|
| `color` | Intent-based colors | `action.primary`, `status.success` |
| `typography` | Type combos | `h1: { size, weight }` |
| `layer` | Z-index intent | `toast`, `modal` |
| `elevation` | Shadow intent | `toast`, `modal`, `input-focus` |
| `layout` | Spacing/radius intent | `gap-xs/sm/md/lg`, `padding-main`, `gutter`, `prose-gap`, `radius-base` (coverage tối thiểu — best-practices.md §4.13a) |

### Reference syntax

```json
{
  "action": {
    "primary": "{global.color.viettel-red.500}",
    "primary-hover": "{global.color.viettel-red.400}"
  }
}
```

Cú pháp: `{<tier>.<path>.<to>.<token>}`. Path khớp với JSON path đầy đủ.

**Resolution:**
- Validator parse reference → tìm path target.
- Nếu target không tồn tại → orphan reference → reject.
- Nếu reference circular (a → b → a) → reject.

## 7. `component` block — component-specific tokens

```json
{
  "component": {
    "toast": {
      "bg": "{semantic.color.background.default}",
      "header-color": "{semantic.color.text.main}",
      "elevation": "{semantic.elevation.toast}",
      "radius": "{semantic.layout.radius-lg}"
    },
    "upload": {
      "border-color": "{semantic.color.action.primary}",
      "padding": "{global.spacing.scale.4}"
    }
  }
}
```

- Component name: kebab-case, khớp với `<component-id>` trong `components_metadata.json`.
- Property name: kebab-case (vd `bg`, `header-color`).
- Value: reference (preferred) hoặc raw (allowed nhưng `normalizer` warn).

> **Automated coverage:** `/ntapp-ds-bootstrap` Rule 4.14 (xem `_shared/best-practices.md`) cluster wrappers cùng primitive, scan `style_property_inventory` per wrapper (xem `_shared/component-metadata-schema.md`), và propose `component.<primitive>.<property>` token khi phát hiện coverage gap hoặc style fragmentation. Tier `component` được populate dần qua proposal flow này (HIGH/MEDIUM/LOW) — không cần DSO viết tay block `component` ban đầu.

## 8. Validation rules

Skill reject file nếu:
- Thiếu top-level key (`metadata`, `global`, `semantic`, `component`).
- Reference path không tồn tại (orphan).
- Reference circular.
- Reference vượt tier ngược (`global` → `semantic`, hoặc `semantic` → `component`).
- Color value không match `^#[0-9a-fA-F]{6}$`, `transparent`, hoặc `rgba(...)`.
- Spacing scale có giá trị không phải multiple của `unit` (warn, không reject).
- 2 token cùng path.

## 9. Naming conventions

| Element | Rule |
|---|---|
| Color family name | kebab-case (`viettel-red`, không `viettelRed`) |
| Color scale key | numeric string (`"500"`, không `500` raw) |
| Font size key | numeric string khớp px (vd `"16"` cho `16px`) |
| Font weight key | semantic name (`light`, `regular`, `medium`, `bold`) |
| Spacing scale key | numeric multiplier (`"4"` = 4 × unit) |
| Semantic category | kebab-case (`action`, `text-main`) |
| Component name | kebab-case, khớp components_metadata.json |
| Component property | kebab-case (`bg`, `border-color`) |

## 10. Type inference (no $type field)

Format hiện tại không có `$type` annotation như W3C. Skill infer type theo path pattern:

| Path pattern | Inferred type |
|---|---|
| `*.color.*` | color (hex / rgba / named) |
| `*.font.size.*` | dimension (px / rem) |
| `*.font.weight.*` | fontWeight (numeric) |
| `*.font.family.*` | fontFamily (string) |
| `*.spacing.*`, `*.layout.gap-*`, `*.layout.padding-*`, `*.layout.gutter`, `*.layout.prose-gap`, `*.layout.radius-*` | dimension |
| `*.shadow.*`, `*.elevation.*` | shadow (CSS box-shadow) |
| `*.z-index.*`, `*.layer.*` | number |
| `*.breakpoint.*` | dimension |
| `*.typography.*` | composite (size + weight) |

→ `w3c-converter.md` dùng inference này khi export sang W3C ($type field).

## 11. Edge converter — bidirectional W3C

Xem `w3c-converter.md` chi tiết. Tóm tắt:

| Direction | Use case |
|---|---|
| **NTAPP v1 → W3C** | Export cho Tokens Studio / Style Dictionary / Figma Variables |
| **W3C → NTAPP v1** | Import token từ designer dùng AI ngoài / Figma plugin |

Converter giữ tier metadata qua `$extensions.ntapp.tier` khi sang W3C. Chiều ngược lại đọc `$extensions.ntapp.tier` để place đúng vào `global` / `semantic` / `component`.

## 12. Atomic update protocol

`token-applier`:
```
1. Lock .bmm-build.lock
2. Snapshot current → archive/master_token_v(N+1).json
3. Patch in-memory (apply NEW TOKEN, UPDATE_TOKEN_VALUE từ proposal)
4. Validate (mục 8)
5. Atomic write: tmp file → rename
6. Bump metadata.version (semver minor cho add, patch cho update value, major cho rename/delete)
7. Update metadata.last_updated
8. Release lock
```

## 13. Versioning (dual-write)

```
{design_system_root}/
├── master_token.json                       ← LATEST
├── master_token_parts/                     ← atomic outputs gần nhất
│   ├── 01_raw_extracted.json               (raw-style-extractor)
│   ├── 02_normalized.json                  (normalizer)
│   └── 03_conflict_resolved.json           (conflict-resolver, nếu có external)
└── archive/
    ├── master_token_v1.json
    ├── master_token_v2.json
    └── ...
```

## 14. Migration từ format pre-schema

Nếu repo đã có `master_token.json` không khai báo `metadata.schema_version` → bootstrap:
1. Backup → `archive/master_token_v0_legacy.json`.
2. Validate theo rules mục 8 với best-effort.
3. Add `metadata.schema_version: 1.0`.
4. Report deviation (vd: spacing values không phải multiple of unit, color name không kebab-case) cho DSO trong `bootstrap_report.md`.

## 15. Runtime export — derivative file

`master_token.json` là **single source of truth** cho design tokens. Bất kỳ file token runtime nào trong code repo (vd Angular `src/styles/_design-tokens.scss`, React `tailwind.config.js`, `src/styles/tokens.ts`) đều là **derivative** sinh từ file này bởi sub-agent `runtime-token-exporter` (xem `/ntapp-ds-build-component/agents/runtime-token-exporter.md`).

**Rule:**
- KHÔNG manual edit runtime token file. File có header `AUTO-GENERATED — DO NOT EDIT`.
- Mọi thay đổi token phải đi qua `master_token.json` → `/ntapp-ds-build-component` regenerate.
- Cycle: designer/DSO sửa proposal → `token-applier` patch `master_token.json` → `runtime-token-exporter` overwrite runtime file → FE consume.
- Reference resolution behavior trong runtime file phụ thuộc format:
  - `css-variables` / `scss-variables` (CSS vars mode): giữ var indirection tier (`var(--semantic-color-action-primary)` ref `var(--global-color-...)`) — runtime theme switching được.
  - `scss-variables` (compile-time mode), `tailwind-config`, `ts-export`, `js-export`: resolve TỚI raw value compile-time (không có chain).

Path + format cụ thể khai báo trong `stack-profile.json.styling.runtime_token_path` + `runtime_token_format` (schema v1.1+).

---

**End of token format schema v1.0.**
