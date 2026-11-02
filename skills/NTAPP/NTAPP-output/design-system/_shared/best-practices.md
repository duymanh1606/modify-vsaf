# Design System Best Practices

**Schema version:** 1.0
**Type:** Rules library cho normalization
**Used by:**
- `/ntapp-ds-bootstrap` (sub-agent: `normalizer`) — chấm điểm raw values, propose normalization
- `/ntapp-ds-build-component` (sub-agent: `token-applier`) — validate value mới khi add/update token
- `/ntapp-ui-generation` Stage 4b Agent 1 — soft reference khi propose new token

---

## 1. Mục đích

Encoding best practices của design system: spacing, type scale, color ramp, naming, accessibility. Tool dùng để **propose** normalization, KHÔNG auto-apply. DSO duyệt từng case.

## 2. Triết lý

> **"Detect existing pattern trước, áp best-practice sau."**

Tool **không dogmatic**. Nếu repo đã có pattern nhất quán + hợp lý (vd: dùng bội 5 thay vì bội 4) → giữ nguyên, formalize làm chuẩn cho repo. Chỉ khi:
- Existing pattern **không nhất quán** (chaotic), hoặc
- Existing pattern **vi phạm rule cứng** (vd: contrast WCAG fail)

→ tool đề xuất chuyển sang industry standard.

**3 confidence level cho mọi proposal:**
- **HIGH** — value rõ ràng deviate, fix tự nhiên (vd: padding 16.5px → 16px). Auto-apply OK nếu DSO bật.
- **MEDIUM** — có deviation nhưng có thể intentional (vd: scale 5px khi repo dùng bội 4 toàn bộ). Đề xuất + cần DSO duyệt.
- **LOW** — opinion-based (vd: "nên dùng base-4 không base-5"). Đề xuất nhưng default reject.

## 3. Pattern detection trước normalization

`normalizer` chạy 3 phase:

```
Phase 1: PATTERN DETECTION
  - Group raw values theo category (color, spacing, font-size, ...)
  - Tính consistency score (% values tuân thủ pattern phổ biến nhất)
  - Output: detected_patterns.json

Phase 2: RULE EVALUATION
  - Với mỗi rule trong best-practices:
    - Apply detection logic
    - Compare với detected_patterns
    - Compute deviation severity + confidence

Phase 3: PROPOSAL GENERATION
  - Generate proposal markdown
  - Group theo confidence
  - DSO duyệt
```

## 4. Rules catalog

### 4.1 SPACING — Multiplier consistency

**Best practice:** Spacing values là multiple của 1 base unit (typically 4px hoặc 8px).

**Detection:**
- Tính GCD (greatest common divisor) của tất cả spacing values phát hiện trong repo.
- Nếu GCD ≥ 4 → existing pattern detected, base = GCD.
- Nếu GCD = 1 hoặc 2 → chaotic, cần normalize.

**Proposal logic:**

| Case | Proposal | Confidence |
|---|---|---|
| GCD = 4 hoặc 8 | "Repo đang dùng bội của {GCD}px. Giữ làm chuẩn." | HIGH (detected) |
| GCD = 5 (intentional non-standard) | "Repo dùng bội 5. Cảnh báo: industry standard là 4 hoặc 8. Giữ?" | LOW |
| GCD = 1 hoặc 2 (chaos) | "Chaotic spacing. Đề xuất normalize sang bội 4 với scale [4, 8, 12, 16, 20, 24, 32, 48, 64]." | MEDIUM |
| Có 1-2 outliers (vd: 17px khi rest là bội 4) | "Outlier {value}px. Đề xuất → {nearest multiple}px." | HIGH |

**Skip:** Nếu < 5 spacing values trong repo (không đủ data để detect pattern).

### 4.2 SPACING — Scale extent

**Best practice:** Scale có ≥5 và ≤15 step. Quá ít = không đủ flexibility, quá nhiều = không cần thiết.

**Detection:** Đếm distinct spacing values sau khi normalize.

**Proposal:**
- < 5 step → đề xuất extend với standard scale `[4, 8, 12, 16, 24, 32]`. Confidence MEDIUM.
- > 15 step → đề xuất consolidate (gộp values gần nhau). Confidence MEDIUM.

### 4.3 TYPOGRAPHY — Type scale

**Best practice:** Font sizes follow modular ratio (1.125, 1.2, 1.25, 1.333, 1.5). Hoặc fixed scale phổ biến: 12, 14, 16, 18, 20, 24, 32, 48.

**Detection:**
- Sort font-size values ascending.
- Tính ratio giữa consecutive values.
- Nếu ratio nhất quán → modular scale detected.
- Nếu values match preset (12/14/16/...) → preset scale detected.

**Proposal:**

| Case | Proposal | Confidence |
|---|---|---|
| Modular ratio nhất quán | "Modular scale {ratio} detected. Giữ." | HIGH |
| Preset scale match | "Preset scale [12,14,16,...] detected. Giữ." | HIGH |
| Mostly preset + 1-2 outlier | "Outlier {value}px → {nearest preset}." | HIGH |
| Chaotic | "Chaotic type scale. Đề xuất normalize sang preset [12,14,16,18,20,24,32,48]." | MEDIUM |

### 4.4 TYPOGRAPHY — Weights

**Best practice:** Sử dụng weights chuẩn 100-900 step 100. Phổ biến: light(300), regular(400), medium(500), semibold(600), bold(700).

**Proposal:**
- Weight không phải multiple of 100 → reject (CSS font-weight spec).
- Có > 5 weights khác nhau → đề xuất consolidate. Confidence MEDIUM.

### 4.5 COLOR — Ramp completeness

**Best practice:** Mỗi color family có scale 100-900 (step 100), hoặc ít nhất 5 step. Lightness progression đều.

**Detection:**
- Group hex values theo hue (similar hue = same family, threshold ΔH ≤ 15°).
- Trong family, sort theo lightness.
- Check consistency của lightness step.

**Proposal:**

| Case | Proposal | Confidence |
|---|---|---|
| Family có ≥5 step, lightness đều | "Ramp {family-name} OK. Giữ." | HIGH |
| Family có 2-4 step, gaps lớn | "Ramp {family-name} thiếu step. Đề xuất generate intermediate." | MEDIUM |
| Family có 1 color | "Single color, không phải ramp. Đề xuất rename thành scalar (vd: white) hoặc extend." | LOW |
| Family có 2 color cùng hue gần nhau (ΔL < 5%) | "{color-A} và {color-B} chỉ khác {delta}%. Consolidate?" | MEDIUM |

### 4.6 COLOR — Naming

**Best practice:**
- Color family name = kebab-case, mô tả hue (`viettel-red`, `pine-blue`).
- KHÔNG đặt theo intent ở `global` tier (vd: `primary` thuộc `semantic.color.action.primary`, không phải `global.color.primary`).

**Detection:** Regex check + tier check.

**Proposal:**
- Camel/Pascal case → kebab-case. Confidence HIGH.
- Intent name ở global (vd: `global.color.primary`) → đề xuất move sang semantic + thay raw name. Confidence MEDIUM.

### 4.7 COLOR — WCAG Contrast

**Best practice:**
- Text contrast ≥ 4.5:1 với background (AA Normal).
- Large text (≥18pt regular hoặc ≥14pt bold) ≥ 3:1.
- Non-text UI element ≥ 3:1.

**Detection:**
- Với mỗi semantic pair (text + bg, action + bg, ...), resolve reference → raw hex → compute contrast ratio.

**Proposal:**

| Case | Proposal | Confidence |
|---|---|---|
| Pair fail AA Normal | "FAIL WCAG AA: text ratio {X}:1 < 4.5. Đề xuất darken text hoặc adjust bg." | HIGH (hard) |
| Pair fail AAA but pass AA | "Pass AA, fail AAA. Acceptable." | INFO only |

> **Hard rule:** Pair semantic.color (text + background) trong cùng context phải pass AA. Bootstrap reject nếu fail (force DSO clarify hoặc override).

### 4.8 BORDER RADIUS

**Best practice:** Radius là multiple của 2 hoặc 4. Thang **đo được** có 3-5 step (`none`, `xs`, `sm`, `md`, `lg`, `xl`) **cộng 2 token vai trò** không nằm trên thang đo:

| Token | Value **bắt buộc** | Vai trò | Sai thường gặp |
|---|---|---|---|
| `radius.full` | `9999px` | **Pill** — bo hết hai đầu trên hộp chữ nhật | `50%` → ra **hình bầu dục** trên hộp chữ nhật |
| `radius.circle` | `50%` | **Tròn** — chỉ đúng khi hộp vuông (avatar, icon button) | dùng cho nút chữ nhật |

**⛔ Hard rule — `radius.full` KHÔNG được là `50%`.** CSS tự kẹp `border-radius` xuống một nửa cạnh ngắn, nên `9999px`:
- trên hộp vuông 40×40 → **tròn hoàn hảo** (giống `50%`),
- trên nút 190×48 → **pill** (`50%` cho ra bầu dục méo).

Tức là `9999px` **bao trùm** `50%` về mặt kết quả trên hộp vuông, còn `50%` không bao trùm được pill. Giữ `radius.full: 50%` làm **idiom pill không biểu diễn được bằng token nào** — dev chỉ còn hai đường: hardcode radius (pre-commit Rule 4 chặn) hoặc lùi về bậc thấp hơn và bo thiếu.

Giữ `radius.circle: 50%` riêng để chỗ nào **cố ý** đòi tròn-theo-tỉ-lệ vẫn khai được ý định đó.

**Detection:** GCD của radius values trên thang đo. Value bằng `9999px`/`999px`/`50%` **loại khỏi phép GCD** — chúng là vai trò, không phải bậc thang, kéo GCD về 1 một cách vô nghĩa.

**Proposal:**
- GCD ≥ 2 + ≤ 5 step → giữ. HIGH.
- Outlier → snap to nearest multiple. HIGH.
- > 5 step → consolidate. MEDIUM.
- **`radius.full` hiện là `50%`** → proposal `[MODIFIED]` đổi thành `9999px` + thêm `radius.circle: 50%`. **HIGH.** Ghi rõ trong proposal: mọi usage đang trỏ `radius.full` trên hộp vuông **không đổi hình** sau khi sửa (CSS clamp), nên đây là sửa an toàn — chỉ hộp chữ nhật mới đổi, và đổi theo hướng đúng.
- **Không có token nào = `9999px`** → proposal `[NEW]` `radius.full: 9999px`. **HIGH.**
- Phát hiện radius `r` với `r >= min(w,h)/2` trên component chữ nhật mà DS không có token pill → cùng gap entry `RADIUS_PILL_MISSING` mà `ntapp-figma-ingest` step-05 emit.

### 4.9 SHADOW / ELEVATION

**Best practice:** Hệ elevation 3-5 level (sm, md, lg, xl, ...). Mỗi level có blur + spread + opacity tăng dần.

**Detection:**
- Parse box-shadow string → extract blur, spread, color, opacity.
- Sort theo intensity (composite score).
- Check progression đều.

**Proposal:**

| Case | Proposal | Confidence |
|---|---|---|
| 3-5 level, progression rõ | "Elevation system OK." | HIGH |
| > 5 level | "Quá nhiều elevation. Đề xuất consolidate." | MEDIUM |
| 2 shadows quá giống nhau (intensity delta < 10%) | "Duplicate elevation. Đề xuất gộp." | HIGH |

### 4.10 Z-INDEX

**Best practice:** Tiered system tránh "z-index war". Tier phổ biến:

```
popup     : 100
sidebar   : 200
overlay   : 1040
modal     : 1060
dropdown  : 2000
toast     : 10000
```

**Detection:**
- Z-index values dùng trong code.
- Check tier separation (≥ 100 between tiers).

**Proposal:**

| Case | Proposal | Confidence |
|---|---|---|
| Tiered system + tier separation OK | "Z-index system OK." | HIGH |
| Z-index values < 100 lẻ tẻ (vd: 1, 2, 5) | "Local z-index, không cần token. Inline OK." | INFO |
| Z-index values overlap (vd: modal=999, dropdown=1000) | "Overlap risk. Đề xuất tier rõ." | MEDIUM |

### 4.11 BREAKPOINTS

**Best practice:** 4-5 breakpoint chuẩn:
```
xs: 0
sm: 480px
md: 768px
lg: 1024px
xl: 1200px
```

**Proposal:**
- Match preset → giữ. HIGH.
- Custom set có ≥4 breakpoint, ascending → giữ với note. MEDIUM.
- < 3 breakpoint → đề xuất extend. MEDIUM.

### 4.12 NAMING — Kebab-case across

**Best practice:** Mọi token name (color family, semantic category, component) là kebab-case. Property name cũng kebab-case.

**Detection:** Regex `^[a-z][a-z0-9-]*$`.

**Proposal:**
- Camel/Pascal/snake_case → kebab-case. HIGH.

### 4.13 SEMANTIC TIER — Coverage

**Best practice:** `semantic.color` cover ít nhất 5 category:
- `action` (primary, secondary, disabled)
- `status` (success, error, warning, info)
- `text` (main, sub, muted, danger)
- `background` (default, subtle, surface)
- `border` (main, light, danger)

**Proposal:**
- Thiếu category → đề xuất add với reference vào global. MEDIUM.

### 4.13a SEMANTIC LAYOUT — Coverage

**Best practice:** `semantic.layout` cover một bộ intent token tối thiểu, map vào `global.spacing.scale` (gap/padding/gutter rhythm) + radius detection (4.8). Mục tiêu: code + layout-primitive (Row/Stack/Grid theo §4.14 layout category) + prose block dùng intent name (`gap-md`, `padding-main`) thay vì step số thô (`spacing.scale.16`) → resolve qua 1 nguồn, rename-safe.

Bộ token tối thiểu:

| Token | Ý nghĩa | Default reference |
|---|---|---|
| `gap-xs` `gap-sm` `gap-md` `gap-lg` | Inline/stack gap scale (4 step liên tiếp trong spacing scale; anchor `gap-md` = gap value dùng nhiều nhất) | `{global.spacing.scale.<n>}` |
| `padding-main` | Container/section padding chủ đạo | `{global.spacing.scale.<n>}` |
| `gutter` | Grid/row column gap | `{semantic.layout.gap-md}` nếu không tách được value riêng |
| `prose-gap` | Vertical rhythm giữa text block (paragraph stack) | `{semantic.layout.gap-md}` nếu không tách được |
| `radius-base` | Default border-radius của thẻ/hộp nội dung | most-common radius (rule 4.8) |
| `radius-pill` | Radius của control bo hết hai đầu (nút, chip, badge) | `{global.radius.full}` (= `9999px`, rule 4.8) |
| `border-hairline` | Độ dày viền/kẻ ngăn mảnh nhất dùng lặp lại | most-common `border-width` |

**Detection:**

Input:
- `master_token_parts/02_normalized.json` (preliminary) — `global.spacing.scale` đã normalize (rule 4.1/4.2) + radii (4.8) + existing `semantic.layout.*`.
- `01_raw_extracted.json` — `spacings` (`value` + `occurrences` + **`by_property`** canonical-key breakdown: `gap` / `column-gap` / `row-gap` / `padding` / `margin` / `unknown`, per raw-style-extractor §4.4). Đây là **nguồn property-context chính** — phân tách gap vs padding vs gutter trực tiếp từ usage, không cần heuristic.
- (cross-check, optional) `components_metadata_parts/01_discovered.json` `style_property_inventory` — đối chiếu property-context ở component level khi muốn xác nhận anchor.

Anchor precedence per property: `by_property` (chính xác, repo-wide) → nếu tất cả occurrence của value là `by_property["unknown"]` (var indirect chưa resolve property) → fallback scale-position heuristic.

Algorithm:
1. Lấy `global.spacing.scale` đã normalize (sort ascending). < 4 step → defer 4.2 (extend scale trước) + emit INFO "scale too small for layout intent mapping", skip rule.
2. **Anchor `gap-md`** = spacing value có `by_property["gap"]` cao nhất trong range gap (4–16px). `gap-sm` = step liền dưới, `gap-lg` = step liền trên, `gap-xs` = step nhỏ nhất của scale. (Không có `gap` context nào → fallback `occurrences` thô.)
3. **`padding-main`** = value có `by_property["padding"]` cao nhất; fallback = spacing value dùng nhiều nhất có giá trị ≥ `gap-md`.
4. **`gutter`** = value có `by_property["column-gap"]` cao nhất; không có column-gap context → reference `{semantic.layout.gap-md}`.
5. **`prose-gap`** = value có `by_property["row-gap"]` (hoặc `margin` trong vertical stack) cao nhất; không tách được → reference `{semantic.layout.gap-md}`.
6. **`radius-base`** = most-common radius (tái dùng 4.8 detection, **loại value vai trò** `9999px`/`50%`).
7. **`radius-pill`** = reference `{global.radius.full}`. Thang radius chưa có token `9999px` → chạy proposal 4.8 (`[MODIFIED]`/`[NEW]`) **trước**, rồi mới reference. KHÔNG reference `radius.lg` làm chỗ tạm — pill nửa vời là bug thị giác im lặng, còn token thiếu là thứ nhìn thấy trong proposal.
8. **`border-hairline`** = `border-width` dùng nhiều nhất (thường `1px`). Repo không có border-width nào → skip token này, KHÔNG bịa `1px`.
9. Per token **thiếu** trong `semantic.layout` → emit proposal add (bảng dưới). Token đã tồn tại → OK, không proposal.

**Skip conditions:**
- < 5 distinct spacing values trong repo (không đủ data — parity 4.1 skip) → emit INFO + skip.
- `master_token` đã có đủ 10 token (`gap-xs/sm/md/lg`, `padding-main`, `gutter`, `prose-gap`, `radius-base`, `radius-pill`, `border-hairline`) → OK, không proposal. *(`radius-pill`/`border-hairline` thêm ở bản này — DS bootstrap trước đó chỉ có 8; thiếu 2 token mới thì emit proposal add như thường, không coi là drift.)*
- DSO disable qua config `semantic-layout-coverage.enabled: false`.

**Proposal table:**

| Case | Trigger | Proposal | Confidence |
|---|---|---|---|
| **A** | `by_property` tách được + 1 value chiếm ≥ `dominant_threshold` (default 0.6) trong property → anchor rõ | "Add `semantic.layout.<token>` → `{global.spacing.scale.<n>}` (anchor `<value>`, `<count>`/`<total>` uses trong property `<canonical-key>`)." | **HIGH** |
| **B** | Property-context toàn `unknown` (var indirect) → fallback scale-position heuristic | "Add `semantic.layout.<token>` → `{global.spacing.scale.<n>}` (heuristic theo vị trí scale, no resolvable property-context)." | **MEDIUM** |
| **C** | Token thiếu nhưng không có anchor riêng (`gutter`/`prose-gap` collapse về gap-md) | "Add `<token>` reference `{semantic.layout.gap-md}` (no distinct value detected; DSO confirm tách riêng nếu cần)." | **LOW** |
| OK | Đủ 8 token, reference hợp lệ | — | — |

**Proposal output format:** Áp dụng `proposal-schema.md` §5.3 (`TYPE: TOKEN`) với `Tier: semantic`, `Source ref: semantic-layout-coverage rule 4.13a`, plus optional fields:
- `Anchor value:` — raw value + occurrences chọn làm anchor (case A/B).
- `Property context:` — css property tách ra (case A) hoặc `"(scale-position fallback)"` (case B) / `"(collapsed to gap-md)"` (case C).

### 4.14 COMPONENT TIER — Coverage

**Best practice:** Mỗi primitive (HTML/lib component) bị wrap bởi ≥2 wrapper trong codebase PHẢI có block `component.<primitive>` trong `master_token.json` cover mọi style-relevant property mà primitive expose (per Step 1b parsed `library_apis/{lib}@{ver}/{primitive}.json`). Mọi wrapper cùng primitive PHẢI resolve cùng style property qua cùng 1 `component.<primitive>.<property>` token (single source of truth) — không hardcode, không tokenize ra nhiều token khác nhau cho cùng property.

**Detection:**

Input:
- `components_metadata_parts/01_discovered.json` — đọc `stack_specific.<fw>.library_wrap.primitive` + `style_property_inventory` per component.
- `library_apis/{lib}@{ver}/{primitive}.json` — đọc props với `tier_hint ∈ {radius, color, size, spacing, elevation, shadow, opacity}` (style-relevant props).
- `master_token.json` (preliminary nếu Step 6 chưa apply) — check sự tồn tại của `component.<primitive>.<property>` tokens.

Algorithm:
1. **Cluster** discovered components by `stack_specific.<fw>.library_wrap.primitive` value. Components không có `library_wrap` → skip (custom-built; out of scope).
2. **Filter cluster size**: cluster size < `consensus_threshold` (default 3 — config `ds-bootstrap.rules.component-tier-coverage.consensus_threshold`) → emit MEDIUM only, không HIGH.
3. **Look up style-relevant props** cho primitive từ `library_apis/{lib}@{ver}/{primitive}.json`. File missing / partial-parse với prop list rỗng → emit INFO ("primitive_api unavailable / no style-relevant props parsed for `{primitive}` — Rule 4.14 skipped for this cluster") + skip cluster.
4. **Per style-relevant prop**, gather across cluster: list of (wrapper-name, value, source, tokenized) từ `style_property_inventory[<corresponding-css-property>]`. CSS property mapping từ lib prop name dùng heuristic table tại §4.14a hoặc `library-api-schema.md` `css_property_hint` field (nếu lib parser populate).
5. **Compare**:
   - All wrappers tokenize cùng `component.<primitive>.<property>` token → OK, không proposal.
   - Wrappers hardcode cùng value (đủ consensus threshold) + token chưa tồn tại → CASE A.
   - Wrappers tokenize ra **khác** token / mix tokenize + hardcode cho cùng property → CASE B (inconsistency).
   - Wrappers tokenize cùng semantic-tier token (chưa qua component tier) → CASE C.
   - Cluster size < threshold + hardcode → CASE D.

**Skip conditions:**
- `stack-profile.ui_library.name ∈ {none, shadcn}` → Step 1b không tạo `library_apis/`, rule không có reference surface → emit INFO + skip toàn bộ rule.
- Component cluster size = 1 → không consensus được, không HIGH proposal (nhưng vẫn xét CASE C/D nếu áp dụng cho 1-wrapper).
- Wrapper là `metadata.status = deprecated` → exclude khỏi cluster.

**Proposal table:**

| Case | Trigger | Proposal | Confidence |
|---|---|---|---|
| **A** | ≥ `consensus_threshold` wrappers hardcode CÙNG value cho cùng prop, `component.<primitive>.<prop>` chưa tồn tại | "Promote `<value>` lên `component.<primitive>.<prop>` reference tới nearest semantic-tier token. Update tất cả wrapper sang reference token mới." | **HIGH** |
| **B** | Wrappers resolve cùng prop ra **khác** token / mix tokenize+hardcode | Emit `STYLE_FRAGMENTATION` warning (per-wrapper dạng) — xem `proposal-schema.md` §7. "Wrappers `<list-A>` dùng `<token-A>`, wrappers `<list-B>` dùng `<token-B>` (hoặc hardcode `<value>`) cho cùng `<prop>`. Resolve sang 1 `component.<primitive>.<prop>`." | **HIGH** |
| **C** | Tất cả wrappers reference cùng semantic-tier token cho prop, nhưng `component.<primitive>.<prop>` chưa elevate | "Elevate sang `component.<primitive>.<prop>` (thêm 1 indirection). Cải thiện rename-safety + tách concern primitive vs semantic." | **LOW** |
| **D** | 1-2 wrappers hardcode prop, `component.<primitive>.<prop>` chưa tồn tại | "Propose `component.<primitive>.<prop>`. DSO quyết định value." | **MEDIUM** |
| OK | Tất cả wrappers reference cùng `component.<primitive>.<prop>` consistently | — | — |

**Proposal output format:** Áp dụng `proposal-schema.md` §5.3 (`TYPE: TOKEN`) với `Tier: component`, `Source ref: component-tier-coverage rule 4.14`, plus optional fields:
- `Wrappers using value:` — list wrapper names + value + tokenized? per case A/B/C/D.
- `Primitive ref:` — `<lib>@<ver>.<primitive>` (nếu wrap library).

CASE B emit thêm WARNING entry theo `proposal-schema.md` §7 với `Type: STYLE_FRAGMENTATION`, list wrappers + tokens divergent.

### 4.14a CSS property mapping per primitive prop

Khi `library_apis/{lib}@{ver}/{primitive}.json` không populate field `css_property_hint` cho prop (parser cũ / partial-parse), normalizer fall back heuristic table sau để map primitive prop name → CSS property name lookup trong `style_property_inventory`. Bảng generic, không bind 1 lib cụ thể:

| Primitive prop name pattern (case-insensitive substring) | CSS property |
|---|---|
| `radius`, `shape`, `rounded`, `corner` | `border-radius` |
| `padding`, `gutter` | `padding`, `padding-*` |
| `margin`, `spacing` | `margin`, `margin-*` |
| `color`, `text`, `fg` | `color` |
| `bg`, `background`, `fill` | `background-color`, `background` |
| `border`, `outline` | `border-color`, `border-width`, `border-style` |
| `size`, `height`, `width`, `min-*`, `max-*` | `width`, `height`, `min-*`, `max-*` |
| `shadow`, `elevation`, `depth` | `box-shadow` |
| `opacity`, `alpha` | `opacity` |
| `font-size`, `text-size` | `font-size` |
| `font-weight`, `weight` | `font-weight` |
| `line-height`, `leading` | `line-height` |

Heuristic match chấp nhận multiple hit (vd prop `padding` → cả `padding`, `padding-x`, `padding-y`). Match miss → skip prop, log INFO.

DSO override per-repo qua `ds-rules-overrides.md` block `component-tier-coverage.css_property_map`.

## 5. Rule application order

`normalizer` apply rules theo thứ tự:

1. **Validation hard rules** (4.7 contrast WCAG, 4.4 weight) — fail = reject.
2. **Pattern detection** (4.1, 4.3, 4.5, 4.8) — detect existing.
3. **Naming normalization** (4.6, 4.12) — apply universally.
4. **Coverage check** (4.2, 4.13, 4.13a, 4.14) — propose extend.
5. **Outlier fix** (mọi rule có outlier logic) — propose snap-to-standard.
6. **Consolidation** (4.5 similar color, 4.9 duplicate shadow, 4.2 overcrowded) — propose merge.

## 6. Confidence-based gating

Output proposal markdown grouped theo confidence:

```markdown
## [HIGH CONFIDENCE — auto-apply candidates]
(DSO có thể bulk-approve hoặc bật flag --auto-apply-high)

## [MEDIUM CONFIDENCE — DSO review required]

## [LOW CONFIDENCE — opinion-based, default skip]
(DSO opt-in từng case)
```

DSO flag trong `.bmm-config.yaml`:

```yaml
ds-bootstrap:
  auto_apply_high_confidence: true     # default false
  reject_on_wcag_fail: true             # default true
  preserve_existing_pattern: true        # default true
```

## 7. Override per-rule

DSO disable / customize rule riêng:

```yaml
ds-bootstrap:
  rules:
    spacing-multiplier:
      enabled: true
      base_unit: 4                      # override detection (force base 4)
    color-naming:
      enabled: false                     # disable rule này
    wcag-contrast:
      level: "AA"                        # AA | AAA
    component-tier-coverage:
      enabled: true                      # default true
      consensus_threshold: 3             # ≥N wrappers cùng hardcode value → HIGH (default 3)
      excluded_primitives: []            # array primitive name skip rule (vd: ["BaseLayout", "Portal"])
      css_property_map:                  # override §4.14a heuristic mapping
        # "<lib-prop-pattern>": "<css-property>"
    semantic-layout-coverage:
      enabled: true                      # default true — rule 4.13a
      dominant_threshold: 0.6            # ≥ tỷ lệ value chiếm trong property → HIGH anchor (default 0.6)
      gap_range_px: [4, 16]              # range px để anchor gap-md (default [4,16])
      required_tokens:                   # bộ token tối thiểu phải cover (override để thêm/bớt)
        - gap-xs
        - gap-sm
        - gap-md
        - gap-lg
        - padding-main
        - gutter
        - prose-gap
        - radius-base
```

## 8. Customization — repo-specific overrides

Nếu repo có domain-specific rules (vd: financial app cần specific color cho gain/loss), DSO viết file `{design_system_root}/ds-rules-overrides.md` theo schema này, `normalizer` load thêm và merge với rules built-in.

## 9. Edge cases

| Case | Xử lý |
|---|---|
| Repo trống (greenfield) | Skip pattern detection, áp full best-practice với confidence MEDIUM. |
| 2 rule conflict | Validation hard rules win. Pattern detection win over coverage check. |
| DSO override toàn bộ rules | Tool chỉ scan + report, không propose. |
| Repo brownfield với pattern không nhất quán hoàn toàn | Phase 1 output `consistency_score < 0.5` → flag "chaos detected" → áp full best-practice. |

---

**End of best-practices v1.0.**
