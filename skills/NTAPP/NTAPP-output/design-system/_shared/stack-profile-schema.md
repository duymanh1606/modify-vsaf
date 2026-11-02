# Stack Profile Schema

**Schema version:** 1.3
**File:** `{design_system_root}/stack-profile.json`
**Producer:** `/ntapp-ds-bootstrap` (sub-agent: `stack-detector`)
**Consumers:** `component-discoverer`, `component-scaffolder`, `component-patcher`, `raw-style-extractor`, `runtime-token-exporter`, `ui_schema_agent` (Stage 4b)

> **Scope per-DS:** 1 file / 1 design system (1 framework). Project multi-DS (nhiều FE repo): MỖI DS root có stack-profile riêng (`{family}/{ds_id}/stack-profile.json` theo `registry.yaml`) — KHÔNG share/append chéo. Xem [ds-registry-schema.md](ds-registry-schema.md) + [ds-resolution.md](ds-resolution.md).

---

## 1. Mục đích

Mô tả stack technical của repo (framework, UI library, styling, file convention) để skill thích ứng cross-stack mà không hardcode framework-specific logic. Đây là **portability layer** cho L2.

## 2. Vòng đời

| Event | Hành vi |
|---|---|
| Onboard repo lần đầu | `/ntapp-ds-bootstrap` chạy `stack-detector` → ghi file. |
| Stack thay đổi (migrate FW, đổi UI lib) | DSO chạy `/ntapp-ds-bootstrap --refresh-stack`. |
| Override per-field | Sửa `.bmm-config.yaml` block `stack:` — KHÔNG sửa `stack-profile.json` thủ công. |

Snapshot version theo dual-write pattern (xem mục 8).

## 3. Cấu trúc JSON

```json
{
  "$schema_version": "1.0",
  "generated_at": "2026-05-08T10:30:00Z",

  "framework": {
    "name": "angular",
    "version": "16.2.0",
    "module_system": "esm"
  },

  "language": {
    "primary": "typescript",
    "version": "5.1.0"
  },

  "ui_library": {
    "name": "primeng",
    "version": "16.0.0",
    "wrap_strategy": "default"
  },

  "icon_library": {
    "name": "primeicons",
    "version": "6.0.1",
    "import_style": "css-class",
    "component_pattern": "pi pi-{name}",
    "available_icons_ref": "./library_apis/primeicons@6.0.1/_index.json"
  },

  "layout_library": {
    "name": "css-vanilla",
    "version": null,
    "strategy": "generated-component",
    "primitive_mapping": {
      "Stack":     "<generated>",
      "Cluster":   "<generated>",
      "Grid":      "<generated>",
      "Spacer":    "<generated>",
      "Center":    "<generated>",
      "Box":       "<generated>",
      "FormField": "<generated>",
      "FieldGrid": "<generated>",
      "Sidebar":   "<generated>",
      "Switcher":  "<generated>"
    },
    "fallback": "css-vanilla"
  },

  "styling": {
    "strategy": "scss",
    "css_vars_supported": true,
    "theme_strategy": "css-vars",
    "runtime_token_path": "src/styles/_design-tokens.scss",
    "runtime_token_format": "css-variables"
  },

  "build_tool": {
    "name": "angular-cli",
    "config_file": "angular.json"
  },

  "component_convention": {
    "file_extension": ".component.ts",
    "template_extension": ".component.html",
    "style_extension": ".component.scss",
    "naming": "kebab-case-folder-pascal-class",
    "location_pattern": "src/app/lib/components/{name}/{name}.component.ts",
    "selector_prefix": "app-",
    "decorator_pattern": "@Component"
  },

  "test_framework": {
    "name": "jasmine-karma",
    "spec_pattern": "*.component.spec.ts"
  },

  "story_framework": {
    "name": "storybook",
    "enabled": true,
    "story_pattern": "*.stories.ts"
  },

  "package_manager": "npm",

  "discovery_hints": {
    "component_roots": [
      "src/app/lib/components",
      "src/app/shared/components"
    ],
    "style_roots": [
      "src/styles",
      "src/app/lib/components"
    ],
    "ignore_patterns": [
      "node_modules",
      "dist",
      "*.spec.ts"
    ]
  }
}
```

## 4. Field reference

### `framework`
| Field | Required | Enum / Format |
|---|---|---|
| `name` | ✅ | `angular` \| `react` \| `vue` \| `svelte` \| `solid` \| `other` |
| `version` | ✅ | semver |
| `module_system` | ✅ | `esm` \| `commonjs` \| `mixed` |

### `language`
| Field | Required | Enum |
|---|---|---|
| `primary` | ✅ | `typescript` \| `javascript` \| `dart` \| `swift` \| `kotlin` |
| `version` | optional | semver |

### `ui_library`
| Field | Required | Mô tả |
|---|---|---|
| `name` | ✅ | `primeng` \| `material` \| `mantine` \| `shadcn` \| `chakra` \| `antd` \| `tailwindui` \| `none` \| `other` |
| `version` | optional | semver |
| `wrap_strategy` | ✅ | `default` (wrap khi có primitive) \| `wrap-only` (luôn wrap) \| `build-from-scratch` (không dùng library) |

### `icon_library` (v1.2+)
| Field | Required | Mô tả |
|---|---|---|
| `name` | ✅ (v1.2+) | `primeicons` \| `lucide-react` \| `lucide-vue-next` \| `@ant-design/icons` \| `@mui/icons-material` \| `@chakra-ui/icons` \| `@tabler/icons-react` \| `react-icons` \| `material-icons` \| `font-awesome` \| `heroicons` \| `phosphor` \| `none` \| `other` |
| `version` | optional | semver — resolve từ `package.json` |
| `import_style` | ✅ (v1.2+) | `component` (JSX/Vue component, vd `<SearchOutlined />`) \| `css-class` (CSS class, vd `<i class="pi pi-search">`) \| `inline-svg` (raw SVG markup) \| `font` (icon font, vd Material Icons ligature) |
| `component_pattern` | ✅ (v1.2+) | Template string với `{name}` placeholder. Ví dụ: `<{name}Outlined />` (antd), `<{name} />` (lucide), `pi pi-{name}` (primeicons), `material-icons:{name}` (MUI ligature). `{name}` placeholder = icon name resolved từ wireframe emoji legend. |
| `available_icons_ref` | optional | Relative path từ `stack-profile.json` đến file index liệt kê icon names khả dụng (vd `./library_apis/lucide-react@0.290/_index.json`). Producer: `library-api-parser` (extension Step 9). Consumer: `ui_schema_agent` dùng để validate icon name từ wireframe legend tồn tại trong library. Nếu missing → ui_schema_agent fallback HITL prompt DSO. |

> **Quan hệ với `ui_library`:** Một số UI library bundle sẵn icon set (vd PrimeNG ↔ primeicons, antd ↔ @ant-design/icons). Stack-detector vẫn extract `icon_library` thành block riêng vì: (a) icon library có thể version độc lập với UI library, (b) repo có thể dùng icon library KHÁC với default của UI library (vd antd repo dùng lucide thay vì @ant-design/icons), (c) một số stack chỉ dùng icon library mà không có UI library full (vd shadcn + lucide).

### `layout_library` (v1.3+)
| Field | Required | Mô tả |
|---|---|---|
| `name` | ✅ (v1.3+) | `chakra-ui-layout` \| `mui-stack` \| `mantine-layout` \| `radix-themes` \| `primeng-flex` \| `antd-space` \| `tailwind-utility` \| `unocss-utility` \| `css-vanilla` \| `none` \| `other`. Library cung cấp layout primitives (Stack/Cluster/Grid/...) cho framework. `css-vanilla` = không dùng library, ds-build-component generate primitive component bằng CSS thuần. `none` = repo không dùng layout primitive (raw flex everywhere) — không recommend nhưng cho phép. |
| `version` | optional | semver resolve từ lockfile |
| `strategy` | ✅ (v1.3+) | `native-component` (library có component sẵn — Chakra HStack, Material Stack) \| `utility-class` (Tailwind/UnoCSS — adapter wrap utility classes thành component) \| `generated-component` (vanilla CSS — ds-build-component generates `<Stack>` component file dùng CSS vars) \| `raw-utility` (đặt utility class trực tiếp vào first child, không wrapper — dùng khi project dứt khoát không muốn wrapper component). |
| `primitive_mapping` | ✅ (v1.3+) | Object map từ 10 canonical primitive names (`Stack`, `Cluster`, `Grid`, `Spacer`, `Center`, `Box`, `FormField`, `FieldGrid`, `Sidebar`, `Switcher`) sang component thực tế của library. Mỗi value là string template hoặc `<generated>` (cho `strategy=generated-component`). Ví dụ Chakra: `"Stack": "Stack"`, Mantine: `"Stack": "Stack"`, Tailwind: `"Stack": "<wrapper:flex flex-col gap-{gap}>"`, CSS vanilla: `"Stack": "<generated>"`. |
| `fallback` | optional | Primitive name fallback khi `primitive_mapping[X] = null` (vd library không support `Switcher` → fallback `Stack`). Default `css-vanilla` nếu không khai. |
| `secondary_allowed` | optional | Array. Multi-layout-library edge case — legacy library cho phép tồn tại song song với canonical. |

> **Mối quan hệ với `ui_library` và `styling`:** Layout library tách block riêng vì: (a) một số UI library không cung cấp layout primitive (vd shadcn, primeng) → dev tự dùng Tailwind / vanilla, (b) Tailwind utility-class strategy khác hẳn native-component strategy về cách adapter generate code, (c) project pure CSS không có UI library vẫn cần layout primitive — `strategy=generated-component` sinh từ token.

> **Phạm vi 10 canonical primitives:** Stack, Cluster, Grid, Spacer, Center, Box, FormField, FieldGrid, Sidebar, Switcher. Distilled từ Every Layout + Mantine + Chakra consolidation trend. Direction-prop pattern (Stack với `direction=row|column`) thay cho dual HStack/VStack. Chi tiết schema props mỗi primitive xem `components_metadata.json` category `layout-primitive`.

### `styling`
| Field | Required | Enum |
|---|---|---|
| `strategy` | ✅ | `scss` \| `sass` \| `css` \| `css-modules` \| `tailwind` \| `styled-components` \| `emotion` \| `vanilla-extract` |
| `css_vars_supported` | ✅ | bool — nếu true, theme switching qua `:root { --token: ... }` được. |
| `theme_strategy` | ✅ | `css-vars` \| `js-runtime` \| `build-time-replacement` |
| `runtime_token_path` | ✅ (v1.1+) | Relative path từ `code_repo_root` đến file token runtime do `runtime-token-exporter` ghi. File này là **derivative** của `master_token.json` — overwrite full mỗi run, không edit thủ công. Default per stack ở mục 9 examples. |
| `runtime_token_format` | ✅ (v1.1+) | `css-variables` \| `scss-variables` \| `tailwind-config` \| `ts-export` \| `js-export`. Quyết định format serialize. Phải tương thích với `strategy` + `theme_strategy` (vd `theme_strategy=css-vars` → chỉ `css-variables` hoặc `tailwind-config`+multi-output). |
| `runtime_token_path_css` | optional | Path file thứ 2 dùng cho multi-output edge case: `runtime_token_format=tailwind-config` + `theme_strategy=css-vars` (cần thêm file CSS vars song song với tailwind config). |

### `component_convention`
| Field | Required | Mô tả |
|---|---|---|
| `file_extension` | ✅ | extension chính của component file (`.tsx`, `.component.ts`, `.vue`) |
| `template_extension` | optional | nếu framework tách template (Angular `.html`) |
| `style_extension` | optional | nếu framework tách style (Angular `.scss`) |
| `naming` | ✅ | `pascal-case-file` \| `kebab-case-file` \| `kebab-case-folder-pascal-class` (Angular) |
| `location_pattern` | ✅ | template path với `{name}` placeholder |
| `selector_prefix` | optional | Angular only |
| `decorator_pattern` | optional | Angular `@Component` / Vue `defineComponent` / etc. |

### `test_framework`, `story_framework`
| Field | Required | Mô tả |
|---|---|---|
| `name` | ✅ | tool name (`jest`, `vitest`, `jasmine-karma`, `storybook`, `none`) |
| `enabled` | optional | bool |
| `spec_pattern` / `story_pattern` | optional | glob để discover existing |

### `discovery_hints`
| Field | Required | Mô tả |
|---|---|---|
| `component_roots` | ✅ | array path — nơi `component-discoverer` quét component có sẵn |
| `style_roots` | ✅ | array path — nơi `raw-style-extractor` quét SCSS/CSS |
| `ignore_patterns` | optional | gitignore-style patterns |

## 5. Detection priority

`stack-detector` chạy theo thứ tự sau, dừng khi đủ confident:

1. **Manifest files:** `package.json` (deps), `angular.json`, `nuxt.config`, `vite.config`, `next.config`, etc.
2. **Lock files:** `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lockb` → infer package manager.
3. **TypeScript config:** `tsconfig.json` → infer language.
4. **Sample files:** quét vài component file đại diện → confirm naming + location convention.
5. **Style files:** quét `*.scss`, `*.css`, hoặc Tailwind config → confirm styling strategy.
6. **Override:** `.bmm-config.yaml` block `stack:` overrides bất kỳ field nào (auto-detect dùng làm default).

## 6. Override mechanism

`.bmm-config.yaml`:

```yaml
stack:
  framework:
    name: react              # override auto-detect
  ui_library:
    name: shadcn
    wrap_strategy: wrap-only
  component_convention:
    location_pattern: "src/components/ui/{name}.tsx"
```

Field nào không khai báo → giữ giá trị auto-detect.

## 7. Validation rules

Bootstrap skill reject `stack-profile.json` nếu:
- Thiếu field required.
- `framework.name = other` mà không có `discovery_hints` đầy đủ (skill không biết quét đâu).
- `component_convention.location_pattern` không chứa `{name}` placeholder.
- `discovery_hints.component_roots` rỗng.
- `styling.runtime_token_path` rỗng / leading `/` / chứa `..` (path traversal).
- `styling.runtime_token_format` không thuộc enum support.
- Combination invalid: `runtime_token_format=css-variables` nhưng `css_vars_supported=false` → reject.
- `runtime_token_format=tailwind-config` nhưng `strategy ≠ tailwind` → warn (cho phép edge case nhưng đáng nghi).
- `icon_library.component_pattern` thiếu `{name}` placeholder → reject.
- `icon_library.import_style = component` nhưng `component_pattern` không chứa `<>` markup → warn.
- `icon_library.available_icons_ref` khai báo nhưng file không tồn tại → warn (parser chưa chạy, không hard fail).
- `layout_library.primitive_mapping` thiếu canonical primitive name nào trong 10 chuẩn → warn (sub-agent fallback `<generated>` hoặc `fallback` value).
- `layout_library.strategy = utility-class` nhưng `styling.strategy ∉ {tailwind, unocss, vanilla-extract}` → warn (combination atypical).
- `layout_library.strategy = native-component` nhưng `name = css-vanilla` → reject (contradiction).
- `layout_library.strategy = generated-component` nhưng `styling.css_vars_supported = false` → warn (generated primitives dùng CSS vars cho gap/spacing token).

**Legacy v1.0/v1.1/v1.2 profile:** Nếu schema version cũ (thiếu `runtime_token_path` / `runtime_token_format` / `icon_library` / `layout_library`), sub-agent consumer sẽ HITL prompt DSO cung cấp value + ghi override `.bmm-config.yaml`. Không hard reject để giữ backward compat. Missing `icon_library` → `ui_schema_agent` (Stage 4b) emit warning thay vì block. Missing `layout_library` → `ui_schema_agent` emit warning `LAYOUT_LIBRARY_MISSING`, fallback giả định `name=css-vanilla, strategy=generated-component` để Stage 4b vẫn chạy; HITL prompt DSO confirm hoặc chạy `--refresh-stack`.

## 8. Versioning (dual-write)

```
{design_system_root}/
├── stack-profile.json                      ← LATEST
└── archive/
    ├── stack-profile_v1.json
    ├── stack-profile_v2.json
    └── ...
```

Mỗi run bootstrap với `--refresh-stack` (hoặc lần đầu) → bump `_v(N+1)`.

## 9. Examples

### Angular + PrimeNG (như BMS hiện tại)

(JSON ở mục 3 chính là ví dụ này.)

### React + shadcn/ui

```json
{
  "$schema_version": "1.0",
  "framework": { "name": "react", "version": "18.2.0", "module_system": "esm" },
  "language": { "primary": "typescript", "version": "5.2.0" },
  "ui_library": { "name": "shadcn", "wrap_strategy": "build-from-scratch" },
  "icon_library": {
    "name": "lucide-react",
    "version": "0.290.0",
    "import_style": "component",
    "component_pattern": "<{name} />",
    "available_icons_ref": "./library_apis/lucide-react@0.290.0/_index.json"
  },
  "layout_library": {
    "name": "tailwind-utility",
    "version": "3.4.0",
    "strategy": "utility-class",
    "primitive_mapping": {
      "Stack":     "<wrapper:flex flex-{direction} gap-{gap} items-{align} justify-{justify}>",
      "Cluster":   "<wrapper:flex flex-wrap gap-{gap} items-{align}>",
      "Grid":      "<wrapper:grid grid-cols-{columns} gap-{gap}>",
      "Spacer":    "<wrapper:flex-1>",
      "Center":    "<wrapper:flex items-center justify-center>",
      "Box":       "<wrapper:p-{padding} m-{margin} rounded-{radius} bg-{background}>",
      "FormField": "<generated>",
      "FieldGrid": "<wrapper:grid grid-cols-{columns} gap-{gap} items-baseline>",
      "Sidebar":   "<generated>",
      "Switcher":  "<generated>"
    },
    "fallback": "css-vanilla"
  },
  "styling": {
    "strategy": "tailwind",
    "css_vars_supported": true,
    "theme_strategy": "css-vars",
    "runtime_token_path": "tailwind.config.js",
    "runtime_token_format": "tailwind-config",
    "runtime_token_path_css": "src/styles/design-tokens.css"
  },
  "build_tool": { "name": "vite", "config_file": "vite.config.ts" },
  "component_convention": {
    "file_extension": ".tsx",
    "naming": "pascal-case-file",
    "location_pattern": "src/components/ui/{name}.tsx"
  },
  "test_framework": { "name": "vitest", "spec_pattern": "*.test.tsx" },
  "story_framework": { "name": "storybook", "enabled": true, "story_pattern": "*.stories.tsx" },
  "package_manager": "pnpm",
  "discovery_hints": {
    "component_roots": ["src/components/ui", "src/components/shared"],
    "style_roots": ["src/styles"],
    "ignore_patterns": ["node_modules", "dist"]
  }
}
```

### Vue 3 + native

(thêm khi có repo cụ thể — schema cho phép tự do)

## 10. Default `runtime_token_path` / `runtime_token_format` per stack (v1.1)

`stack-detector` đề xuất default theo bảng dưới. DSO có thể override qua `.bmm-config.yaml`.

| Framework + Styling | `runtime_token_path` (default) | `runtime_token_format` (default) | Note |
|---|---|---|---|
| Angular + SCSS + css-vars | `src/styles/_design-tokens.scss` | `css-variables` | Sass partial (leading `_`). Exporter ghi file mới riêng — KHÔNG đụng `src/styles.scss` của DSO. DSO phải add 1 dòng `@import './styles/design-tokens';` vào `src/styles.scss` (1 lần khi onboard). Emit `:root{--token: ...}` block. |
| Angular + SCSS + build-time | `src/styles/_design-tokens.scss` | `scss-variables` | Emit `$token: value;`. Reference resolve raw value compile-time. |
| React + Tailwind + css-vars | `tailwind.config.js` | `tailwind-config` | Multi-output: thêm `runtime_token_path_css` cho CSS vars file song song. |
| React + CSS Modules | `src/styles/tokens.css` | `css-variables` | |
| React + styled-components/emotion | `src/styles/tokens.ts` | `ts-export` | Object literal `export const tokens`. |
| Vue 3 + SCSS | `src/styles/_design-tokens.scss` | `css-variables` | |
| Vue 3 + native script setup | `src/styles/tokens.ts` | `ts-export` | |
| Svelte + native | `src/styles/tokens.css` | `css-variables` | |
| Solid + native | `src/styles/tokens.css` | `css-variables` | |

Nếu repo có config khác convention (vd Angular monorepo Nx có `libs/styles/...`) → DSO override `.bmm-config.yaml`:

```yaml
stack:
  styling:
    runtime_token_path: "libs/styles/src/lib/_design-tokens.scss"
    runtime_token_format: "css-variables"
```

## 11. Default `icon_library` per UI library (v1.2)

`stack-detector` đề xuất default dưới đây khi repo có `ui_library.name` quen thuộc + dep tương ứng có mặt trong `package.json`. DSO override qua `.bmm-config.yaml` block `stack.icon_library` nếu repo dùng icon set khác convention.

| UI library | Default icon library | `import_style` | `component_pattern` | Note |
|---|---|---|---|---|
| `primeng` | `primeicons` | `css-class` | `pi pi-{name}` | PrimeNG ship sẵn primeicons như peer dep. Name format kebab-case (`search`, `chevron-down`). |
| `antd` | `@ant-design/icons` | `component` | `<{name}Outlined />` | Suffix variant (`Outlined` / `Filled` / `TwoTone`). `{name}` PascalCase. |
| `material` (@mui/material) | `@mui/icons-material` | `component` | `<{name} />` | `{name}` PascalCase, suffix `Outlined` / `Rounded` / `Sharp` optional. |
| `chakra` | `@chakra-ui/icons` HOẶC `lucide-react` | `component` | `<{name}Icon />` HOẶC `<{name} />` | Chakra v2+ khuyến nghị lucide. DSO confirm. |
| `mantine` | `@tabler/icons-react` | `component` | `<Icon{name} />` | `{name}` PascalCase, prefix `Icon`. |
| `shadcn` | `lucide-react` | `component` | `<{name} />` | shadcn convention. |
| `tailwindui` | `@heroicons/react` | `component` | `<{name}Icon />` | Heroicons v2 ship outline + solid. Default outline. |
| `none` / `other` | (HITL prompt) | (HITL) | (HITL) | DSO khai trong `.bmm-config.yaml`. |

**Detect logic:** stack-detector quét `package.json.dependencies` theo thứ tự ưu tiên trong bảng. Match đầu tiên → propose. Nếu match nhiều icon library trong repo → emit warning + HITL prompt DSO chọn canonical.

**Multi-icon-library edge case:** Repo cho phép nhiều icon library cùng tồn tại (vd legacy + new). Schema chỉ ghi 1 canonical trong `icon_library`. DSO có thể allow-list các library phụ qua `.bmm-config.yaml`:

```yaml
stack:
  icon_library:
    name: lucide-react
    secondary_allowed:
      - "@ant-design/icons"   # legacy code chưa migrate, được phép tồn tại
```

`ui_schema_agent` mapping luôn ưu tiên `name` (canonical), chỉ fallback `secondary_allowed` khi canonical không có icon match.

## 12. Default `layout_library` per UI library (v1.3)

`stack-detector` đề xuất default dưới đây dựa trên `ui_library.name` đã detect + dep tương ứng trong `package.json`. DSO override qua `.bmm-config.yaml` block `stack.layout_library` nếu repo có convention khác.

| UI library | Default layout library | `strategy` | Note |
|---|---|---|---|
| `chakra` | `chakra-ui-layout` | `native-component` | Chakra ship `Stack`, `HStack`, `VStack`, `Wrap`, `Grid`, `Center`, `Spacer`, `Box`, `Flex`. Map `Stack(direction=row)` → Chakra `HStack`; `Stack(direction=column)` → `VStack` hoặc `Stack`. Cluster → `Wrap`. |
| `mantine` | `mantine-layout` | `native-component` | Mantine v7 ship `Stack`, `Group` (≈Cluster), `Grid`, `SimpleGrid`, `Center`, `Container`, `Flex`, `Box`. Map `Cluster` → `Group`. |
| `material` (@mui/material) | `mui-stack` | `native-component` | MUI ship `Stack` (direction prop native), `Grid`, `Box`. Cluster fallback dùng `Stack` + `flexWrap=wrap`. FormField → `FormControl`. |
| `antd` | `antd-space` | `native-component` | antd ship `Space` (≈Stack with direction prop) + `Row`/`Col` (grid). Map `Cluster` → `Space wrap`. FormField → `Form.Item`. |
| `primeng` | `primeng-flex` HOẶC `tailwind-utility` | `utility-class` HOẶC `generated-component` | PrimeNG dùng PrimeFlex CSS utility lib làm primary layout (`p-d-flex`, `p-flex-column`, `p-jc-center`). Hoặc fallback `<generated>` nếu repo không có PrimeFlex. |
| `radix` (Radix Themes) | `radix-themes` | `native-component` | Radix Themes ship `Flex`, `Grid`, `Box`, `Container`, `Section`. Stack = Flex direction prop. |
| `shadcn` | `tailwind-utility` | `utility-class` | shadcn = Tailwind first-class. Adapter wrap Tailwind utility thành primitive component. |
| `tailwindui` | `tailwind-utility` | `utility-class` | Tương tự shadcn. |
| `none` | `css-vanilla` HOẶC `tailwind-utility` | `generated-component` HOẶC `utility-class` | Repo không có UI library → fallback CSS thuần (ds-build-component generates primitives) hoặc Tailwind nếu repo có `tailwind.config.*`. |
| `other` | (HITL prompt) | (HITL) | DSO khai trong `.bmm-config.yaml`. |

**Detect logic:** stack-detector ưu tiên match theo `ui_library.name` (bảng trên). Nếu repo có Tailwind config mà `ui_library.name ∈ {none, primeng, shadcn, tailwindui}` → propose `tailwind-utility` thay cho default. Nếu match nhiều layout strategy khả thi → HITL prompt DSO chọn canonical.

**Multi-layout-library edge case:** Repo cho phép nhiều layout source cùng tồn tại (vd Chakra primitives + Tailwind utility cho 1 số screen). DSO allow-list qua `.bmm-config.yaml`:

```yaml
stack:
  layout_library:
    name: chakra-ui-layout
    secondary_allowed:
      - tailwind-utility   # legacy/edge screens dùng raw Tailwind, không buộc migrate
```

`ui_schema_agent` luôn ưu tiên `name` (canonical) khi emit `layout` tree; `secondary_allowed` chỉ tham khảo cho drift detection (không emit từ canonical).

**Lazy materialization (cho `generated-component` strategy):** ds-build-component chỉ generate file component cho primitive thực sự được reference trong ít nhất 1 `ui_schema_{id}.json` (`layout` tree). Primitive không dùng → không tạo file. Advanced primitives `Sidebar`, `Switcher` thường lazy.

---

**End of stack profile schema v1.3.**
