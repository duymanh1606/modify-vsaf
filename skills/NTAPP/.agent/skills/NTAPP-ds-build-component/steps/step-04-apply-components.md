# Step 4: Apply Components

## GOAL
Scaffold NEW components theo `stack-profile.json` convention, patch MODIFIED components surgical edit. Atomic update `components_metadata.json` qua lock file. Apply order: NEW trước, MODIFIED sau (vì MODIFIED có thể depend NEW).

## 1. Load Personas (3 sub-agents)

- **Component Scaffolder:** `../agents/component-scaffolder.md` — declare role + layout-adapter output spec (§3.1) + stub templates (§3.2) + token reference convention (§3.3).
- **Component Patcher:** `../agents/component-patcher.md` — declare role + decision policies (§4.1 change_type table, §4.2 breaking taxonomy) + output spec (§5).
- **Metadata Registrar:** `../agents/metadata-registrar.md` — declare role + decision policies + schemas (§4.1 NEW entry, §4.2 library_wrap, §4.3 change_type dispatch, §4.4 semver) + output spec (§5).

## 2. Inputs

- Routing object (`components_to_scaffold`, `components_to_patch`) từ Step 1.
- `stack-profile.json` (spec repo).
- `master_token.json` (post Step 3).
- `components_metadata.json` (current latest).
- `_shared/component-metadata-schema.md`.
- `_shared/token-format-schema.md`.

## 3. Pipeline — Scaffold NEW (per component, alphabetical)

### Stage 3.1: Strategy decision tree

```
For each NEW component in components_to_scaffold:

  if metadata.abstract.category == "layout-primitive":
    → strategy = "layout-adapter" (xem Stage 3.2)
  elif metadata.library_wrap is set:
    → strategy = "wrap" (wrapper component import lib, expose abstract API)
  else:
    → strategy = "custom" (build-from-scratch)
```

### Stage 3.2: Layout-adapter dispatch (per `stack-profile.layout_library.strategy`)

| Strategy | Hành vi |
|---|---|
| `native-component` | Re-export thin file. Set `library_wrap = { library, primitive, library_version }`. |
| `utility-class` | Wrapper áp utility class per `primitive_mapping[primitive]` template. |
| `generated-component` | Full standalone component dùng CSS vars (resolve từ `master_token.json`). |
| `raw-utility` | KHÔNG generate file. Set `stack_specific.<fw> = { raw_utility: true, no_component_file: true }`. |

**Layout primitive missing trong `primitive_mapping`:** fallback `generated-component` strategy + log warning.

**Lazy materialization:**
- Core 8 (Stack/Cluster/Grid/Spacer/Center/Box/FormField/FieldGrid): metadata pre-populated bởi bootstrap, code file CHỈ generate khi có ≥1 `ui_schema_*.json` reference primitive đó.
- Advanced 2 (Sidebar/Switcher): cả metadata lẫn code file đều lazy.
- Scaffolder check `ui_schema_root` references trước khi generate; primitive trong routing nhưng KHÔNG có reference → skip, log `[LAYOUT-PRIMITIVE SKIPPED] {name}: no ui_schema reference yet`.

### Stage 3.3: Compute file paths

Theo `stack-profile.component_convention.location_pattern`. Pattern relative — resolve theo Universal Rule U2: `absolute = {code_repo_root}/{rendered_pattern}`. Apply U3 (spec-repo guard).

Pattern substitutions:
- `{name}` — raw component name (kebab-case).
- `{Name}` — PascalCase transform.
- `{ext}` — extension cho file role (ts/html/scss/tsx/...).

Convention case transformation theo `component_convention.naming` (kebab-case-folder-pascal-class / pascal-case-folder / etc.).

Override: nếu `.bmm-config.yaml` `ds-build.component_target_root` set → override phần đầu của pattern.

Examples (Angular kebab + React Pascal): xem `component-scaffolder.md` §3.2 output spec.

### Stage 3.4: Generate stub content

Per `strategy + framework + role`:
- `custom` strategy + Angular: emit ts/html/scss theo template ở `component-scaffolder.md` §3.2 (Angular custom block).
- `wrap` strategy + Angular: emit ts dùng lib component (vd PrimeNG `<p-message>`) — template ở `component-scaffolder.md` §3.2 (Angular wrap block).
- `custom` strategy + React: emit tsx + scss module per §3.2 (React custom block).
- Vue/Svelte/Solid: framework idiom; stack-profile.component_convention guide.

Token references trong style theo `component-scaffolder.md` §3.3 (decision policy):
- SCSS: `var(--<token-css-var-name>)`
- Tailwind: utility class match theme.colors path
- CSS-in-JS: `${theme.color.action.danger}` object path

Verify mỗi `tokens_used` resolve trong `master_token` (post Step 3). Fail → STOP `"missing token reference {path}"`.

### Stage 3.5: Module registration (Angular only)

Nếu framework = angular:
1. Đọc `components_metadata[name].stack_specific.angular.module` (vd `SharedModule`). Resolve path U2.
2. Append component vào module's `declarations` + `exports`.
3. Edit module file atomic (U1). Preserve existing format.
4. Module not found → STOP `"module not found, configure in stack-profile hoặc verify {code_repo_root}"`.

### Stage 3.6: Optional test/story stub

- `stack-profile.story_framework` set (vd `storybook`) VÀ `.bmm-config.yaml` `ds-build.scaffold_stories: true` → tạo `{name}.stories.ts` với 1 default + per-variant story.
- `stack-profile.test_framework` set (vd `jest`) VÀ `ds-build.scaffold_tests: true` → tạo `{name}.spec.ts` placeholder render test.

### Stage 3.7: Emit `[COMPONENTS SCAFFOLDED]` section

Append vào `build_report_sections[]` per `component-scaffolder.md` §4 output format.

## 4. Step-level decision points (Scaffold)

- Component name conflict existing file → Drift (Universal Rule U5), Agent 1 miss duplicate → STOP.
- `library_wrap` lib không trong code repo `package.json` → Warning, fallback custom strategy + log.
- Selector_prefix không config (Angular) → default `app`.
- Component có `external: true` (re-exported lib) → skip scaffold, chỉ register metadata.
- Stack-profile thiếu `component_convention.location_pattern` → STOP, hint rerun `/ntapp-ds-bootstrap`.

## 5. Pipeline — Patch MODIFIED (per component, alphabetical)

### Stage 5.1: Locate file

Đọc `components_metadata.json[name].stack_specific.{framework}.file_path`. Resolve U2: `absolute = {code_repo_root}/{file_path}`. Apply U3 (spec-repo guard). Verify file tồn tại.

Apply U5 drift check: parse class/component name, verify match metadata. Mismatch → STOP `"drift detected"`.

### Stage 5.2: Apply theo `change_type`

Dispatch theo `component-patcher.md` §4.1 table. `change_type` ngoài list → STOP `"unknown change_type"`.

### Stage 5.3: Breaking detection

Per `component-patcher.md` §4.2 taxonomy. Mismatch declaration → STOP (default) hoặc log warning (lenient mode `ds-build.breaking_declaration_mode: lenient`).

### Stage 5.4: Edit operation guidelines

- Atomic per-file edit theo U1.
- Preserve formatting (indentation, comments, import order). Insert vị trí khớp neighbor.
- KHÔNG chạy prettier/linter (để pre-commit hook xử lý).

### Stage 5.5: Multi-file transactional edit

MODIFIED component thường touch nhiều file (ts + html + scss + module + story). Apply tất cả hoặc rollback toàn bộ. Fail giữa chừng → restore từ in-memory snapshot pre-edit.

### Stage 5.6: Token reference update (change_type = `change_token`)

- Replace `var(--<old-token>)` → `var(--<new-token>)` trong style file.
- Verify new token exist trong `master_token` (post Step 3).
- Old token còn ai khác dùng (grep occurrence) → log informational, KHÔNG block.

### Stage 5.7: Emit `[COMPONENTS PATCHED]` section

Append vào `build_report_sections[]` per `component-patcher.md` §5 output format.

## 6. Step-level decision points (Patch)

- File đã bị dev edit manual sau Stage 4b proposal generated → drift via re-parse → STOP.
- `change_token` target token chưa apply → ordering bảo đảm Step 3 chạy trước, không xảy ra trong normal flow.
- add_input collision (input name đã tồn tại) → STOP.
- remove_input có consumer (grep template) → warning informational, không block.
- Selector change → out of scope, đề xuất proposal split NEW + delete old.
- File thiếu 1 phần (vd thiếu .scss) → tạo file thiếu, log info.

## 7. Pipeline — Register metadata (atomic + lock)

### Stage 7.1: Acquire lock

```
lock_path = {design_system_root}/components_metadata.lock

try:
  create lock_path exclusive (O_CREAT | O_EXCL)
  write content: pid + timestamp + id (screen_id hoặc widget_id)
catch FileExists:
  - read existing lock
  - if older than .bmm-config.yaml ds-build.lock_timeout_seconds (default 60s) → assume stale, override + log warning
  - else STOP "concurrent run blocked, lock holder: {pid} since {ts}"
```

Pid still alive → wait 5s grace, retry. Sau 3 retry → STOP với lock holder detail.

### Stage 7.2: Load + parse current metadata

Đọc `components_metadata.json`. Parse JSON. Fail → STOP với hint rollback.

Greenfield (file không tồn tại) → tạo từ template tối thiểu (schema_version + empty components object).

### Stage 7.3: Apply NEW entries

Build `component_entry` theo `metadata-registrar.md` §4.1 schema. Populate `library_wrap` theo §4.2.

### Stage 7.4: Apply MODIFIED entries

Dispatch `change_type` per §4.3. Bump semver per §4.4. Set `metadata.last_modified_by = { id, id_type }`.

### Stage 7.5: Validate full metadata post-apply

Theo `_shared/component-metadata-schema.md`:
- Mọi component có 2 layers (abstract + stack_specific).
- `tokens_used` đều resolve trong `master_token`.
- `file_path` resolve được theo U2.
- Không duplicate component name (case-insensitive).

Fail → STOP `"metadata validation failed"` + dump `{design_system_root}/_failed_components_metadata.json`. KHÔNG ghi đè latest.

### Stage 7.6: Atomic write

Theo U1 + U4. Pretty 2-space indent, sorted keys.

### Stage 7.7: Release lock

`unlink lock_path` trong finally block (success hoặc exception).

### Stage 7.8: Dual-write archive

Sau latest write thành công:
- Tạo `{design_system_root}/archive/_v{N+1}_{timestamp}/`.
- Copy: `master_token.json`, `components_metadata.json`, `stack-profile.json` (snapshot coherent restore point), `feature_deltas/{id}/build_report.md` (sau Step 5 ghi xong).
- N = count existing `archive/_v*/` folders + 1.
- Timestamp collision (cùng second) → suffix `_a`, `_b`, ...
- Disk full → vẫn report apply success cho latest, cảnh báo archive skip, không exit fail.

### Stage 7.9: Emit `[METADATA REGISTERED]` section

Append vào `build_report_sections[]` per `metadata-registrar.md` §5 output format.

## 8. OUTPUT

**Spec repo:**
- `{design_system_root}/components_metadata.json` updated (latest).
- `{design_system_root}/archive/_v{N+1}_{timestamp}/` snapshot.
- In-memory build report sections (Step 5 ghi vào `feature_deltas/{id}/build_report.md`): `[COMPONENTS SCAFFOLDED]`, `[COMPONENTS PATCHED]`, `[METADATA REGISTERED]`, `[LAYOUT-PRIMITIVE SKIPPED]` (lazy).

**Code repo:**
- New component files trong `{code_repo_root}/{component_target_root}/{name}/` (per stack convention).
- Modified existing files (git diff visible trong code repo).

> **[GATE]** Mọi STOP ở **Step-level decision points** (§4 scaffold, §6 patch) + metadata validation (Stage 7.5) + lock acquire (Stage 7.1) phải clear. Lock conflict / drift / validation fail → STOP, KHÔNG đọc step kế.

**Next:** Read fully and follow `./step-05-archive-report.md`
