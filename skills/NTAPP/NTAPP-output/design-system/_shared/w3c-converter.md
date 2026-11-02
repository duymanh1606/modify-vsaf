# W3C ↔ NTAPP v1 CONVERTER (shared spec)

## 1. Mục đích

Edge-only converter giữa **NTAPP v1** (internal canonical format) và **W3C Design Tokens Community Group spec**. Dùng bởi:
- `conflict-resolver` (sub-agent của `/ntapp-ds-bootstrap`): convert external W3C file sang NTAPP v1 trước khi 3-way diff.
- `/ntapp-ds-bootstrap` Phase 5 export: optional `--target-format w3c` flag để export master_token.json ra W3C JSON cho designer/Figma tool consumption.

**Tôn chỉ:**
- **Internal storage không thay đổi** — NTAPP v1 vẫn là canonical, không migrate W3C.
- **Lossless round-trip** — NTAPP v1 → W3C → NTAPP v1 phải produce byte-equivalent (sau normalize whitespace + key order).
- **Deterministic** — same input → same output luôn.

## 2. Format khác biệt key

| Aspect | NTAPP v1 | W3C |
|---|---|---|
| Tier system | 3-tier path-based (`global.X`, `semantic.X`, `component.X`) | Flat namespace, no tier concept |
| Type | Inferred từ path keyword | Explicit `$type` field |
| Value | Direct value hoặc reference `{path}` | `$value` field, reference `{path}` |
| Reference path | Match NTAPP path structure (`global.color.red.500`) | Match W3C structure path (full nested keys) |
| Metadata | Top-level `metadata` object | Per-token `$description`, top-level `$schema` |
| Extensions | None native | `$extensions.<vendor>.X` |

## 3. NTAPP v1 → W3C conversion

### 3.1 Structure mapping

NTAPP v1:
```json
{
  "metadata": { "name": "ds", "version": "1.0.0", "schema_version": "1.0" },
  "global": {
    "color": {
      "red": {
        "500": "#ee0033"
      }
    },
    "spacing": {
      "scale": {
        "4": "16px"
      }
    }
  },
  "semantic": {
    "color": {
      "action": {
        "primary": "{global.color.red.500}"
      }
    }
  },
  "component": {
    "button": {
      "primary": {
        "background": "{semantic.color.action.primary}"
      }
    }
  }
}
```

W3C output:
```json
{
  "$schema": "https://design-tokens.github.io/community-group/format/",
  "$extensions": {
    "ntapp": {
      "schema_version": "1.0",
      "name": "ds",
      "version": "1.0.0",
      "exported_from": "ntapp-v1",
      "exported_at": "2026-05-09T10:30:00Z"
    }
  },
  "global": {
    "color": {
      "red": {
        "500": {
          "$value": "#ee0033",
          "$type": "color",
          "$extensions": { "ntapp": { "tier": "global" } }
        }
      }
    },
    "spacing": {
      "scale": {
        "4": {
          "$value": "16px",
          "$type": "dimension",
          "$extensions": { "ntapp": { "tier": "global" } }
        }
      }
    }
  },
  "semantic": {
    "color": {
      "action": {
        "primary": {
          "$value": "{global.color.red.500}",
          "$type": "color",
          "$extensions": { "ntapp": { "tier": "semantic" } }
        }
      }
    }
  },
  "component": {
    "button": {
      "primary": {
        "background": {
          "$value": "{semantic.color.action.primary}",
          "$type": "color",
          "$extensions": { "ntapp": { "tier": "component" } }
        }
      }
    }
  }
}
```

**Note:** NTAPP tier (global/semantic/component) PRESERVE structure trong W3C (tier names trở thành top-level groups). Tier metadata DUPLICATE trong `$extensions.ntapp.tier` cho redundancy + để tools không hiểu structure tier vẫn có hint.

### 3.2 Type inference (NTAPP path → W3C $type)

| NTAPP path keyword | W3C $type |
|---|---|
| `.color.*` | `color` |
| `.spacing.*`, `.gap.*`, `.padding.*`, `.margin.*` | `dimension` |
| `.fontSize.*`, `.font_size.*`, `.typography.*.size` | `dimension` (W3C dùng dimension cho font size) |
| `.fontFamily.*`, `.font_family.*`, `.typography.*.family` | `fontFamily` |
| `.fontWeight.*`, `.font_weight.*`, `.typography.*.weight` | `fontWeight` |
| `.lineHeight.*`, `.line_height.*` | `number` (unitless) hoặc `dimension` (px-based) — auto-detect từ value |
| `.letterSpacing.*` | `dimension` |
| `.radius.*`, `.borderRadius.*`, `.border_radius.*` | `dimension` |
| `.shadow.*`, `.elevation.*` | `shadow` |
| `.zIndex.*`, `.z_index.*` | `number` |
| `.breakpoint.*` | `dimension` |
| `.duration.*` | `duration` |
| `.opacity.*` | `number` |
| `.border.*` (composite border) | `border` |
| `.gradient.*` | `gradient` |

Path không match list → `$type` omitted (W3C valid, type inferred bởi consumer).

### 3.3 Reference handling

NTAPP `{global.color.red.500}` → W3C `{global.color.red.500}` — syntax giống hệt, structure tier names giữ trong W3C nên path resolve OK.

### 3.4 Composite types

#### Shadow

NTAPP v1:
```json
"semantic": {
  "shadow": {
    "card": "0 2px 8px rgba(0,0,0,0.1)"
  }
}
```

W3C requires structured object cho `shadow` type. Convert:
```json
"semantic": {
  "shadow": {
    "card": {
      "$value": {
        "offsetX": "0",
        "offsetY": "2px",
        "blur": "8px",
        "spread": "0",
        "color": "rgba(0,0,0,0.1)"
      },
      "$type": "shadow",
      "$extensions": {
        "ntapp": {
          "tier": "semantic",
          "original_value": "0 2px 8px rgba(0,0,0,0.1)"
        }
      }
    }
  }
}
```

`original_value` PRESERVE để round-trip lossless (re-parse có thể lose precision).

#### Typography

NTAPP composite `typography.body`:
```json
"typography": {
  "body": {
    "size": "16px",
    "family": "Roboto",
    "weight": 400,
    "line_height": 1.5
  }
}
```

W3C có `typography` composite type:
```json
"typography": {
  "body": {
    "$value": {
      "fontFamily": "Roboto",
      "fontSize": "16px",
      "fontWeight": 400,
      "lineHeight": 1.5
    },
    "$type": "typography",
    "$extensions": { "ntapp": { "tier": "semantic", "composite": true } }
  }
}
```

#### Border (composite)

```json
"border": {
  "$value": { "color": "#000", "width": "1px", "style": "solid" },
  "$type": "border"
}
```

### 3.5 Metadata top-level

NTAPP `metadata.name`, `metadata.version` → `$extensions.ntapp.{name,version,schema_version}` ở root W3C.

`exported_at` thêm timestamp. `exported_from` = `"ntapp-v1"` (signal cho re-import).

## 4. W3C → NTAPP v1 conversion

### 4.1 Structure detection

Auto-detect tier từ:
1. `$extensions.ntapp.tier` (preferred, từ NTAPP-exported W3C)
2. Top-level group name (`global`, `semantic`, `component`)
3. Heuristic (nếu không có 1 hoặc 2):
   - Token value là literal (không reference) → `global`
   - Token value reference `{global.*}` → `semantic`
   - Token value reference `{semantic.*}` hoặc path có keyword `button|card|modal|...` → `component`

Không detect được → mặc định `global`, log warning.

### 4.2 Strip W3C wrapping

```
{ "$value": "#ee0033", "$type": "color", "$extensions": {...} }
  →
"#ee0033"
```

`$type` discarded (NTAPP infer từ path).
`$description` discarded (NTAPP v1 không support per-token description — nếu cần preserve, log warning).
`$extensions.ntapp.*` consumed (tier info), other extensions discarded with warning.

### 4.3 Composite expand back

#### Shadow

W3C:
```json
{ "$value": {"offsetX":"0","offsetY":"2px","blur":"8px","spread":"0","color":"rgba(0,0,0,0.1)"}, "$type": "shadow",
  "$extensions": { "ntapp": { "original_value": "0 2px 8px rgba(0,0,0,0.1)" } } }
```

→ Use `original_value` if present (lossless round-trip).
→ Else reconstruct: `"0 2px 8px 0 rgba(0,0,0,0.1)"` từ object fields.

#### Typography

W3C composite typography `$value` object → NTAPP nested object:
```json
{ "size": "16px", "family": "Roboto", "weight": 400, "line_height": 1.5 }
```

Naming: W3C dùng `fontSize/fontFamily/fontWeight/lineHeight` (camelCase), NTAPP v1 dùng `size/family/weight/line_height` (snake/short). Map cần explicit table.

| W3C field | NTAPP v1 field |
|---|---|
| fontFamily | family |
| fontSize | size |
| fontWeight | weight |
| lineHeight | line_height |
| letterSpacing | letter_spacing |

### 4.4 Metadata

`$extensions.ntapp.{name,version,schema_version}` → top-level `metadata`. Nếu absent (W3C từ external), tạo metadata mặc định:
```json
{
  "name": "external-import",
  "version": "0.0.0",
  "schema_version": "1.0",
  "imported_at": "<timestamp>",
  "imported_from": "w3c"
}
```

### 4.5 Reject conditions

- File parse fail → exit 3 trong conflict-resolver.
- Token value chứa `gradient` / `animation` / type W3C support nhưng NTAPP v1 không → skip với warning, list trong `summary.skipped`.
- Reference path không tồn tại sau convert → log warning, giữ nguyên reference (downstream validate sẽ catch).

## 5. Round-trip guarantee

### 5.1 Test invariants

Cho mọi NTAPP v1 valid file F:
- `w3c_to_ntapp(ntapp_to_w3c(F))` ≡ F (sau normalize: sort keys, strip whitespace, strip `imported_at`/`exported_at`).

Cho W3C file W được tạo bởi `ntapp_to_w3c`:
- `ntapp_to_w3c(w3c_to_ntapp(W))` ≡ W (sau normalize).

External W3C files (không có `$extensions.ntapp`) → KHÔNG guarantee round-trip về W3C identical (NTAPP có thể strip metadata không native).

### 5.2 Lossy fields (acceptable)

Trong direction NTAPP → W3C → NTAPP:
- Comments / formatting whitespace: normalized
- Key order: normalized (deterministic sort)

Trong direction W3C → NTAPP → W3C:
- `$description` field: LOST (cảnh báo user trước khi convert).
- `$extensions.<other-vendor>`: LOST (cảnh báo user).
- Composite type details (vd: shadow object precision): preserved via `original_value` ext.

## 6. CLI usage

```bash
# Convert NTAPP master_token → W3C export (bootstrap Phase 5)
/ntapp-ds-bootstrap --target-format w3c
  → output: {design_system_root}/master_token.w3c.json

# Conflict-resolver auto-detect và convert ngầm (không CLI riêng)
/ntapp-ds-bootstrap --external-tokens ./from-figma.json
  → if W3C detected: convert internal → 3-way diff với NTAPP master_token
```

## 7. Edge cases

| Case | Xử lý |
|---|---|
| W3C file dùng `$type: gradient` | Skip token, warning trong report. NTAPP v1 không support. |
| W3C reference syntax dùng `{group.token}` không match NTAPP tier | Convert as-is, downstream validate catch. |
| NTAPP value là plain number không unit (vd: zIndex 100) | W3C `$type: number`, $value: 100. |
| W3C `$value: null` | Skip token với warning. |
| Cyclic reference detected | Exit 3 (conflict-resolver), invalid input. |
| W3C file mixed: 1 phần có `$extensions.ntapp.tier`, 1 phần không | Apply per-token detection. |
| External W3C có nested deep > 5 levels | Convert OK, warning về complexity. |

## 8. Constraints

- **KHÔNG** modify NTAPP canonical format để fit W3C — converter phải bend, không format.
- **KHÔNG** auto-fix invalid W3C input (vd: missing $value) — exit error, để DSO sửa source.
- Output deterministic.
- Lossless round-trip cho NTAPP-source W3C.

## 9. Implementation note

Converter là pure function spec — không phải binary. Sub-agent đọc W3C JSON, áp logic mục 4 in-memory, output NTAPP v1 JSON object. Tương tự cho direction ngược lại.

LLM implement converter qua:
1. Parse JSON.
2. Walk tree recursively.
3. Per leaf: detect format (NTAPP value-only vs W3C `{$value, $type, $extensions}` object).
4. Apply mapping table.
5. Reconstruct output tree.
6. Validate output against `_shared/token-format-schema.md` (NTAPP direction) hoặc against W3C $schema (W3C direction).
