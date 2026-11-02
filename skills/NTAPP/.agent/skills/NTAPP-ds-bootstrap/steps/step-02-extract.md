# Step 2: Raw Style Extraction

## GOAL

Quét toàn bộ file style trong `style_roots` từ `stack-profile.json`, extract raw values (color, spacing, font, shadow, ...) — chưa normalize, chưa phán xét. Output `master_token_parts/01_raw_extracted.json`.

## 1. Load Persona

Adopt role của **Raw Style Extractor** sub-agent tại `../agents/raw-style-extractor.md`. Persona declare: role + decision policies (§4.1 SCSS/CSS/SASS, §4.2 Tailwind, §4.3 CSS-in-JS) + JSON output spec (§5) + edge cases (§6) + constraints (§7).

## 2. Inputs

- `{design_system_root}/stack-profile.json` (Step 1 output) — `discovery_hints.style_roots`, `discovery_hints.ignore_patterns`, `styling.strategy`.
- Style files dưới `{code_repo_root}/{style_roots}/...` (READ).

## 3. Pipeline

### Stage 3.1: Resolve style files

Quét recursive `{code_repo_root}/{style_roots}` với glob theo `styling.strategy`:
- SCSS/CSS/SASS → `**/*.{scss,css,sass}`.
- Tailwind → template files (`.html` / `.tsx` / `.jsx` / `.vue`) + `tailwind.config.*`.
- CSS-in-JS → `**/*.{ts,tsx,js,jsx}` chứa `styled.` / `css\`...\`` / `theme.` reference.

Filter `discovery_hints.ignore_patterns` (vd `node_modules`, `dist`, `*.spec.*`).

### Stage 3.2: Parser dispatch per `styling.strategy`

Dispatch theo `raw-style-extractor.md` §4:
- SCSS/CSS/SASS → §4.1 — parse variable + direct values trong rules.
- Tailwind → §4.2 — đọc `tailwind.config.*` + scan utility class usage.
- CSS-in-JS → §4.3 — parse template literals trong `.ts/.tsx`.

### Stage 3.3: Extract per category

Categories (output spec ở persona §5): `colors`, `spacings`, `font_sizes`, `font_families`, `font_weights`, `shadows`, `radii`, `z_indexes`, `breakpoints`.

### Stage 3.4: Sort + dedupe (U4)

Per category: sort theo `occurrences` descending, alphabetical tie-break. Dedup giá trị trùng (giữ list `files` merged). Category `spacings`: khi dedup cùng value, **merge `by_property`** (cộng dồn count per canonical-key, §4.4 persona) — giữ invariant `sum(by_property) == occurrences`.

### Stage 3.5: Atomic write

Theo U1 + U2: `{design_system_root}/master_token_parts/01_raw_extracted.json`.

## 4. Decision Points

- **Style root path không tồn tại** trong `{code_repo_root}/...` — skip với warning. Tất cả style_roots đều không có → STOP với hint verify cwd + `.bmm-config.yaml` `bmad.code_repo_root`.
- **Greenfield** (không có style file nào) — output empty `raw_values`, log info. Normalizer sẽ áp full best-practice MEDIUM.

## 5. Output

- `{design_system_root}/master_token_parts/01_raw_extracted.json`.

**Next:** Read fully and follow `./step-03-discover.md`
