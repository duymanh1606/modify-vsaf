# Step 1: Stack Detection

## GOAL

Phát hiện framework, language, UI library, icon library, layout library, styling, file convention, runtime token path của code repo. Output `stack-profile.json` theo schema canonical, kèm HITL prompts cho các field ambiguous.

## 1. Load Persona

Adopt role của **Stack Detector** sub-agent tại `../agents/stack-detector.md`. Persona declare: role + decision policies (§4.1 framework/UI lib enum, §4.2 naming, §4.3 layout strategy enum, §4.4 confidence mapping, §4.5 default discovery_hints) + output spec (§5 console summary template, JSON schema ref) + edge cases (§6) + constraints (§7).

## 2. Inputs

- `{code_repo_root}/package.json` + framework configs + `tsconfig.json` + lock files (READ).
- Sample component + style files dưới `{code_repo_root}/{discovery_hints.component_roots}/...` (READ).
- `.bmm-config.yaml` block `stack:` (manual override).
- `_shared/stack-profile-schema.md` (§5 detection order, §10 runtime token defaults, §11 icon library defaults, §12 layout library defaults).

## 3. Pipeline

### Stage 3.1: Manifest detection

Đọc `{code_repo_root}/package.json` → infer framework theo `stack-detector.md` §4.1 table. Confirm với framework config (`angular.json` / `nuxt.config` / `vite.config` / `next.config`).

### Stage 3.2: Lock file → package manager

| Lock file | Package manager |
|---|---|
| `package-lock.json` | npm |
| `yarn.lock` | yarn |
| `pnpm-lock.yaml` | pnpm |
| `bun.lockb` | bun |

### Stage 3.3: TypeScript config

Đọc `tsconfig.json` → infer language + version. Repo không có `tsconfig.json` → default JS.

### Stage 3.4: Sample component files (3-5 files đại diện)

Quét `discovery_hints.component_roots` (hoặc default từ `stack-detector.md` §4.5).
- Confirm naming convention (xem persona §4.2).
- Confirm file extension.
- Confirm location pattern (extract `{name}` placeholder).
- Confirm selector_prefix (Angular).

### Stage 3.5: Style files

Quét `*.scss`, `*.css`, `tailwind.config.*` → confirm styling strategy.

### Stage 3.6: Runtime token file detection

Quét `discovery_hints.style_roots` cho:
- Header `AUTO-GENERATED` → file đã được exporter ghi trước đó → suggest path đó.
- Block `:root { --... }` với nhiều CSS custom properties → suggest path đó.
- File `$<token-name>: ...` SCSS variables → suggest scss-variables format.
- Có `tailwind.config.*` → suggest `runtime_token_path = tailwind.config.<ext>` + `runtime_token_format = tailwind-config`.
- Không detect được → áp default từ `stack-profile-schema.md` §10.

**HITL prompt** (luôn confirm, confidence MEDIUM+ bắt buộc):
> *"Detect: `runtime_token_path = {suggested_path}`, `runtime_token_format = {suggested_format}`. Confirm Y/N hoặc nhập path khác?"*

### Stage 3.7: Icon library detection (v1.2+)

Quét `{code_repo_root}/package.json.dependencies` theo `stack-profile-schema.md` §11 default table (theo `ui_library.name` đã detect Stage 3.1).
- Match đầu tiên → propose `icon_library.name` + `version` (resolve từ lockfile).
- Resolve `import_style` + `component_pattern` từ default table.

**Multi-source HITL prompt** (multiple deps match):
> *"Repo có nhiều icon library: {list}. Chọn canonical: [1] {first} [2] {second} ... Nhập số hoặc tên path khác."*
DSO choice → `icon_library.name`. Others → `icon_library.secondary_allowed`.

**No-match HITL prompt** (không dep nào trong default table):
> *"Không detect được icon library. Repo dùng `none` (không icon, build inline SVG) hay icon library nào khác? Nhập tên npm package."*
DSO trả `none` → `icon_library.name = none`, các field khác `null`. DSO trả tên package → prompt tiếp `import_style` + `component_pattern` (free text).

Sau detect, set `available_icons_ref = "./library_apis/{name}@{version}/_index.json"` (path target cho parser Step 1b).

### Stage 3.8: Layout library detection (v1.3+)

Resolve default từ `stack-profile-schema.md` §12 theo `ui_library.name`. Quét `{code_repo_root}/package.json.dependencies` confirm:

| Dep pattern | `layout_library.name` | `strategy` |
|---|---|---|
| `@chakra-ui/react` (có Stack/HStack) | `chakra-ui-layout` | `native-component` |
| `@mantine/core` | `mantine-layout` | `native-component` |
| `@mui/material` | `mui-stack` | `native-component` |
| `antd` | `antd-space` | `native-component` |
| `@radix-ui/themes` | `radix-themes` | `native-component` |
| Tailwind config + `ui_library.name ∈ {none, shadcn, tailwindui, primeng}` | `tailwind-utility` | `utility-class` |
| Tailwind + UI lib có native layout | (HITL — multi-source) | — |
| `primeflex` (PrimeNG repo) | `primeng-flex` | `utility-class` |
| Không detect được | `css-vanilla` | `generated-component` |

Resolve `primitive_mapping` từ §12 default table cho 10 canonical primitives.

**HITL prompt** (confidence MEDIUM+):
> *"Detect: `layout_library = {name}` (strategy: {strategy}). 10 primitives sẽ map qua: Stack→{x}, Cluster→{y}, .... Confirm Y/N hoặc nhập tên library khác?"*

**Multi-source HITL** (multiple layout sources khả thi):
> *"Repo có {N} layout sources: {list}. Chọn canonical: [1] ... [2] ... Phụ (secondary_allowed) khai sau qua `.bmm-config.yaml` nếu cần."*

### Stage 3.9: Apply override

`.bmm-config.yaml` block `stack:` override field-level (override auto-detect). Override → confidence = HIGH (DSO declared).

### Stage 3.10: Write + console summary

Write `stack-profile.json` atomic (U1) tại `{design_system_root}/stack-profile.json`. Emit console summary theo template ở `stack-detector.md` §5.

## 4. Decision Points

- **Multi-framework conflict** (vd: monorepo Angular + React) → STOP. Yêu cầu DSO chỉ định trong `.bmm-config.yaml`. (Registry multi-DS KHÔNG phải cách lách luật này — 1 DS = 1 framework.)
- **`package.json` không tồn tại** → STOP với hint verify cwd + `bmad.code_repo_root`.
- **`stack-profile.json` đã tồn tại** → SO KHỚP trước khi hỏi: `framework.name` vừa detect (Stage 3.1) vs profile trên disk, + `code_repo` trong `registry.yaml` (nếu có) vs repo hiện tại.
  - **Khớp** (cùng repo/stack — re-run bình thường) → HITL 2 lựa chọn: *reuse* (load từ disk, log "reused existing stack-profile.json", skip Stage 3.1-3.10) / *re-detect* (archive cũ vào `archive/_v{N}_{ts}/` snapshot-before-overwrite rồi chạy full pipeline).
  - **KHÔNG khớp** (profile thuộc repo/stack KHÁC — dấu hiệu đang bootstrap FE repo thứ 2 vào DS root của repo thứ 1) → **CẤM overwrite im lặng.** HITL 3 nhánh:
    1. **Tạo DS mới (khuyến nghị):** hỏi DSO `ds_id` cho repo hiện tại (+ `ds_id` đặt cho DS cũ nếu registry chưa tồn tại). Sinh/update `{family_root}/registry.yaml` theo `_shared/ds-registry-schema.md` — DS cũ `root: "."` (giữ nguyên chỗ, zero-migration), DS mới `root: "{ds_id}/"`; tạo dir `{family_root}/{ds_id}/`; cập nhật `bmad.design_system_root` trong `.bmm-config.yaml` **code repo** → `{family_root}/{ds_id}`; log cả 2 thao tác. Từ đây `{design_system_root}` = root MỚI, chạy full pipeline. *(family_root = giá trị design_system_root cũ.)*
    2. **Re-detect đè DS hiện có** — CHỈ khi DSO xác nhận explicit repo này THAY THẾ DS cũ (vd rewrite app): archive + overwrite như nhánh khớp.
    3. **Abort.**
- **Registry đã có entry cho repo hiện tại nhưng `design_system_root` config trỏ chỗ khác** → STOP, hint sửa `.bmm-config.yaml` khớp registry (SSoT là registry).

## 5. Output

- `{design_system_root}/stack-profile.json` (latest, atomic overwrite).
- Console summary (1 dòng per field).
- (Optional) `archive/_v{N}_{ts}/stack-profile.json` snapshot nếu re-detect.

**Next:** Read fully and follow `./step-01b-library-api-parse.md` (parser cho UI library + icon library).
