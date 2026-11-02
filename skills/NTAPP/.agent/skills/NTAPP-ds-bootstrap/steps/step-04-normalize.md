# Step 4: Normalization

## GOAL

Áp `_shared/best-practices.md` rules lên raw extracted values + discovered components → output proposals grouped by confidence (HIGH / MEDIUM / LOW) + hard validation report (WCAG).

## 1. Load Persona

Adopt role của **Normalizer** sub-agent tại `../agents/normalizer.md`. Persona declare: role + decision policies (§4.1 hard validation vs soft proposal, §4.2 confidence assignment, §4.3 rule application order) + output spec (§5a JSON, §5b markdown section templates) + edge cases (§6) + constraints (§7).

## 2. Inputs

- `{design_system_root}/master_token_parts/01_raw_extracted.json` (Step 2 output) — `spacings[].by_property` cho Rule 4.13a (semantic-layout coverage).
- `{design_system_root}/components_metadata_parts/01_discovered.json` (Step 3 output) — `style_property_inventory` + `stack_specific.<fw>.library_wrap` cho Rule 4.14.
- `{design_system_root}/library_apis/{lib}@{ver}/*.json` (Step 1b output) — props với `tier_hint` cho Rule 4.14. Missing → Rule 4.14 emit INFO + skip cluster.
- `{design_system_root}/master_token.json` (latest snapshot, nếu có) — check `component.*` token coverage cho Rule 4.14.
- `_shared/best-practices.md` (rules library).
- `.bmm-config.yaml` block `ds-bootstrap.rules:` (overrides — bao gồm `component-tier-coverage.consensus_threshold`, `.excluded_primitives`, `.css_property_map`; `semantic-layout-coverage.dominant_threshold`, `.gap_range_px`, `.required_tokens`).
- (Optional) `{design_system_root}/ds-rules-overrides.md` (repo-specific rules).

## 3. Pipeline

### Stage 3.1: PATTERN DETECTION (Phase 1)

Áp `_shared/best-practices.md` mục 3 (Phase 1 rules):
- Spacing GCD detection (rule 4.1).
- Type scale ratio detection (rule 4.3).
- Color ramp grouping (ΔH ≤ 15° = same family) (rule 4.5).
- Border radius GCD (rule 4.8).
- Z-index tier check (rule 4.10).

Compute `consistency_score = % values tuân thủ pattern phổ biến nhất` per category.

### Stage 3.2: RULE EVALUATION (Phase 2)

Dispatch theo `normalizer.md` §4.3 rule application order:

1. Hard validation (rule 4.7 WCAG) — chỉ rule này block Step 7 apply khi `reject_on_fail: true`. Fail → emit vào `[HARD VALIDATION FAILURES]`.
2. Pattern detection rules (Phase 1 output đã có).
3. Naming normalization (rule 4.6, 4.12) — apply universally.
4. Coverage check:
   - 4a. Global / semantic coverage (rule 4.2, 4.13) — propose extend.
   - 4a'. **Semantic-layout coverage (rule 4.13a)** — map intent layer (`gap-xs/sm/md/lg`, `padding-main`, `gutter`, `prose-gap`, `radius-base`, `radius-pill`, `border-hairline`) lên `global.spacing.scale` đã normalize; anchor property-context từ `01_raw_extracted.json` `spacings[].by_property` (gap/column-gap/row-gap/padding), fallback scale-position khi `unknown`; emit Case A/B/C proposals theo `best-practices.md` §4.13a. Skip nếu < 5 distinct spacing values, scale < 4 step, hoặc đã đủ 10 token. Config override `ds-bootstrap.rules.semantic-layout-coverage`.
   - 4b. **Component-tier coverage (rule 4.14)** — cluster discovered components by `stack_specific.<fw>.library_wrap.primitive` (skip components không có `library_wrap`); per-cluster look up style-relevant props từ `library_apis/{lib}@{ver}/{primitive}.json` (filter `tier_hint`); per-prop scan `style_property_inventory` across wrappers; emit Case A/B/C/D proposals theo bảng trong `best-practices.md` §4.14. Skip toàn rule nếu `stack-profile.ui_library.name ∈ {none, shadcn}` (no library_apis surface) — emit INFO message vào report.
5. Outlier fix (rule 4.4 font-weight, 4.1 spacing) — MEDIUM/LOW (không block).
6. Consolidation (rule 4.5 similar color, 4.9 duplicate shadow, 4.2 overcrowded).

### Stage 3.3: PROPOSAL GENERATION (Phase 3)

Group proposals by confidence per U6 (workflow.md):
- HIGH — deviation rõ ràng + fix tự nhiên.
- MEDIUM — pattern conflict cần DSO chọn.
- LOW — opinion-based.

Per item populate: `rationale`, `proposed change`, `before/after`, `occurrences`, `files`.

Build `preliminary_master_token` (apply tất cả HIGH proposals tạm thời — Step 7 sẽ rebuild với approved set sau Step 6).

### Stage 3.4: Atomic write + section emission

Theo U1 + U2: write `{design_system_root}/master_token_parts/02_normalized.json`.

Append sections vào `report_sections[]` theo `normalizer.md` §5b template:
- `[HIGH CONFIDENCE]`
- `[MEDIUM CONFIDENCE]`
- `[LOW CONFIDENCE]`
- `[HARD VALIDATION FAILURES]` (nếu có entries blocker)

## 4. Decision Points

- **WCAG fail + `ds-bootstrap.rules.wcag-contrast.reject_on_fail: true`** → block Step 7 apply. DSO phải resolve trong Step 6 hoặc disable rule.
- **Tất cả values outlier** (greenfield) → skip pattern detection, áp full best-practice MEDIUM.
- **Override file conflict với built-in rule** → override file thắng. Log conflict trong report.
- **Rule 4.14 surface unavailable** (`ui_library.name ∈ {none, shadcn}` HOẶC `library_apis/{lib}@{ver}/{primitive}.json` missing/partial-parse) → skip cluster + emit INFO. KHÔNG fail run.
- **Rule 4.14 produces > N proposals** (DSO-tunable threshold trong config — default no cap) → group HIGH proposals per primitive, output 1 summary row + collapsible detail per primitive trong markdown để tránh DSO overload.

## 5. Output

- `{design_system_root}/master_token_parts/02_normalized.json`.
- Append vào `report_sections[]`: `[HIGH CONFIDENCE]`, `[MEDIUM CONFIDENCE]`, `[LOW CONFIDENCE]`, `[HARD VALIDATION FAILURES]`.

**Next:** DSO cung cấp external tokens path tại INITIALIZATION → Read fully and follow `./step-05-conflict-resolve.md`; nếu không → Read fully and follow `./step-06-human-approval.md`.
