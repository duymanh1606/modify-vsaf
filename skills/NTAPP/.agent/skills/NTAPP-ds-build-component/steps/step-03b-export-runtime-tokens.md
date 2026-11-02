# Step 3b: Export Runtime Tokens

## GOAL

Serialize `master_token.json` (vừa patched ở Step 3) sang file token runtime trong code repo theo `stack-profile.json` — để Step 4 (Apply Components) scaffold component reference `var(--token)` được FE resolve compile-time.

**Bắt buộc giữa Step 3 và Step 4** — nếu skip, component scaffold sẽ broken: SCSS/TS file emit reference token không tồn tại trong code repo → FE compile fail.

## 1. Load Persona

Adopt role của **Runtime Token Exporter** sub-agent tại `../agents/runtime-token-exporter.md`. Persona declare: role + 5 format-specific serializer templates (§5 — output spec) + header format (§6) + multi-output spec (§7) + edge cases (§9) + constraints (§10). Pipeline + dispatch logic ở step file này.

## 2. Inputs

- `master_token.json` (latest, từ Step 3 output spec repo).
- `stack-profile.json` (spec repo).
- `.bmm-config.yaml` block `stack` (code repo) — override layer cho `runtime_token_path` / `runtime_token_format`.
- `code_repo_root` (cwd).
- `id` (cho header trace).

## 3. Pipeline

### Stage 3.0: Pre-flight check

**Pre-flight runtime token config** đã chạy tại workflow.md INITIALIZATION. Step này assume `runtime_token_path` + `runtime_token_format` đã resolve (từ stack-profile hoặc .bmm-config.yaml override). KHÔNG re-prompt.

Sanity check:
- Format enum match `runtime-token-exporter.md` §5 (`css-variables` / `scss-variables` / `tailwind-config` / `ts-export` / `js-export`). Mismatch → STOP (xem DECISION POINTS).
- CSS vars compatibility: format ∈ {`css-variables`, `scss-variables`} VÀ `stack-profile.styling.css_vars_supported = false` → STOP.

### Stage 3.1: Load + resolve effective config

```
1. Load master_token.json (latest).
2. Read stack-profile.json.styling.
3. Merge .bmm-config.yaml stack.styling override (code repo).
4. Resolve effective:
   - format: enum
   - path: relative to code_repo_root
   - theme_strategy: optional (cho multi-output trigger)
   - runtime_token_path_css: optional (cho multi-output thứ 2)
```

### Stage 3.2: Format dispatch

Dispatch theo `format`:

| Format | Serializer reference | Reference resolution |
|---|---|---|
| `css-variables` | `runtime-token-exporter.md` §5.1 | Giữ var indirection (`var(--global-...)`) |
| `scss-variables` | §5.2 | Resolve raw value (SCSS compile-time) |
| `tailwind-config` | §5.3 | Resolve raw value |
| `ts-export` | §5.4 | Resolve raw value, nested 3-tier |
| `js-export` | §5.5 | Như `ts-export` không type export |

Serializer block ở persona là output spec — agent produce file content theo template. Universal Rule U4: 2-space indent, sort tokens alphabetical TRONG mỗi tier, tier order global → semantic → component.

### Stage 3.3: Header injection

Prepend header comment AUTO-GENERATED theo `runtime-token-exporter.md` §6. Comment syntax tự động theo extension:
- `.css` / `.scss` / `.js` / `.ts` → `/* ... */`
- `.scss` variables block → `//` line comments
- `tailwind.config.js` → `/** ... */`

Header body: source path, producer, build id + timestamp, master DS version, regenerate hint.

### Stage 3.4: Atomic write

Theo Universal Rule U1: tempfile → fsync → rename. Target: `{code_repo_root}/{runtime_token_path}` (Universal Rule U2, U3 — spec-repo guard).

**File collision check** (pre-write): nếu file đích đã tồn tại VÀ KHÔNG có header AUTO-GENERATED trong 10 dòng đầu → HITL prompt Y/N overwrite. N → STOP, dev move file ra path khác.

**Parent dir missing:** tạo recursive, log info.

### Stage 3.5: Multi-output (edge case)

Nếu `format = tailwind-config` VÀ `theme_strategy = css-vars`:
- Emit `tailwind.config.js` (đã làm Stage 3.2-3.4) cho design-time IntelliSense.
- ALSO emit `.css` file thứ 2 tại `{styling.runtime_token_path_css}` (optional field, fallback `src/styles/design-tokens.css`) — dùng serializer `css-variables` cho runtime theme switching.

### Stage 3.6: Post-write verify + checksum

- Read back file, byte count > 0, header present (10 dòng đầu chứa "AUTO-GENERATED").
- Compute sha256 checksum cho build_report tracking.

### Stage 3.7: Emit build_report section

Append `[RUNTIME TOKENS EXPORTED]` vào `build_report_sections[]` theo format ở `runtime-token-exporter.md` §8.

## 4. Output

- File `{code_repo_root}/{runtime_token_path}` (atomic write).
- (Optional multi-output) file thứ 2 nếu `tailwind-config + theme_strategy=css-vars`.
- In-memory `exporter_result` cho Step 5 archive + build_report.
- In-memory build report section `[RUNTIME TOKENS EXPORTED]`.

## DECISION POINTS

- **File đích đã có nội dung DSO viết tay (không có header AUTO-GENERATED):** HITL prompt Y/N overwrite. N → STOP, dev move file ra path khác trước khi chạy lại.
- **Format không support (enum mismatch):** STOP với hint update `runtime-token-exporter.md` mục 5 thêm format-specific block.
- **CSS vars mismatch:** format yêu cầu CSS vars nhưng `css_vars_supported=false` → STOP.
- **Filesystem read-only / parent dir không create được:** STOP "cannot write runtime token file".

## CROSS-REPO NOTE

Step này ghi vào **code repo** (`{code_repo_root}/{runtime_token_path}`), không phải spec repo. Khác Step 3 (ghi spec repo `master_token.json`) và Step 4 (cũng ghi code repo). File sẽ vào commit code repo cùng với component files scaffold ở Step 4.

> **[GATE]** File collision HITL (Stage 3.4) — nếu file đích có nội dung không AUTO-GENERATED, DSO phải confirm overwrite (N → STOP). Format enum / CSS-vars mismatch → STOP. Clear gate rồi mới đọc step kế.

**Next:** Read fully and follow `./step-04-apply-components.md`
