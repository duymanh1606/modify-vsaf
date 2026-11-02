# Aesthetic Rubric

**Schema version:** 1.0
**Type:** Rules library cho visual composition lint (post-schema, Stage 4b)
**Twin của:** `layout-best-practices.md` (structure/composition) + `best-practices.md` (token-value normalization). File này = **thẩm mỹ thị giác trên schema đã resolve token-value**, KHÔNG cấu trúc, KHÔNG normalize token.
**Producer:** `/ntapp-ui-generation` Step 4 (sub-agent: `visual_composition_auditor`)
**Consumers:** `visual_composition_auditor` (chấm), DSO (review `aesthetic_review_{id}.md`), HITL visual gate.

---

## 1. Mục đích

Encoding best-practice **thẩm mỹ thị giác** của một `ui_schema_{id}.json` **đã resolve token reference sang giá trị thật** (`master_token.json`). Rubric chấm **bố cục đã assemble** (layout tree + visual_intent + data_bindings) trên 7 trục đo được, deterministic, TRƯỚC khi schema bàn giao Stage 5 — thay vì để mắt người phát hiện sau khi code render.

> **Tại sao tách 3 file (chống drift + single owner):**
> - `best-practices.md` — value-level: 1 token spacing/color/type **có hợp lệ** không (bootstrap-time). Owner WCAG contrast + type-scale ratio + spacing multiplier.
> - `layout-best-practices.md` — structure-time: wireframe **cấu trúc** có đúng pattern không (single primary, field grouping, IA depth). Owner composition intent.
> - `aesthetic-rubric.md` (file này) — assembly-time: schema đã **ghép + resolve token-value** render ra **có cân nhịp/hài hòa** không. Owner visual rhythm + density balance + emphasis materialization.
>
> Khi 1 trục cần rule đã sở hữu ở file khác (vd contrast WCAG) → **cite ID**, KHÔNG copy logic. Trục 5 (Color & contrast) và trục 6 (Typographic scale) delegate phần value-validity về `best-practices.md`; rubric này chỉ kiểm **cách dùng** trong bố cục cụ thể.

## 2. Triết lý

> **"Chấm trên giá trị đã resolve, không chấm trên gu."**

- Rubric chỉ chạy khi token đã resolve sang **giá trị thật** (px/hex/ratio) trong bộ nhớ — nên 100% deterministic, same input → same verdict (U4).
- **KHÔNG dogmatic về aesthetics chủ quan** (không chấm "màu này đẹp không"). Mỗi trục là **rule đo được** trên giá trị đã resolve (đếm, so scale, tính ratio contrast).
- **Hard-pass policy:** PASS ⟺ **cả 7 trục pass**; bất kỳ trục FAIL → trigger self-correct loop (Step 4 §3). Hard-pass thay vì score ≥N/7 vì điểm số ngầm cho phép ship 1 lỗi visual rõ ràng. HITL có thể override per-axis (file này editable).
- **Token vẫn là SSoT.** Rubric KHÔNG đẻ giá trị mới. FAIL do thiếu token (vd thiếu density level) → emit gap note → đề xuất `[NEW]` qua proposal hiện hữu, KHÔNG tự thêm.

## 3. Tiền điều kiện — Token Resolution

Trước khi chấm, `visual_composition_auditor` resolve toàn bộ token reference sang giá trị thật, **chỉ trong artifact preview / bộ nhớ — KHÔNG ghi ngược vào `ui_schema_{id}.json`** (giữ no-hardcode, Rule 4 pre-commit):

| Nguồn trong schema | Resolve sang | Đọc từ |
|---|---|---|
| `layout[].props.gap = "md"` | px thật (vd `16px`) | `master_token.json` `global.spacing.scale` |
| `visual_intent.vertical_rhythm = "tokens.spacing.scale.4"` | px thật | `global.spacing.scale.4` |
| `visual_intent.grouping[].separation` | px thật | `semantic`/`global` spacing |
| Component fg/bg token (từ `components_metadata.json`) | hex thật | `master_token.json` color tiers |
| Text size/weight token | px + ratio | `global.font.size` / `global.font.weight` |

Token reference KHÔNG resolve được (orphan / thiếu tier) → **không chấm trục đó là PASS**; emit `RESOLVE_GAP` finding (xem §5) → gap note proposal, KHÔNG fabricate giá trị.

## 4. 7 trục chấm

Mỗi trục: **Tiêu chí pass (đo được trên giá trị đã resolve) → Detection → Cite owner (nếu có)**. Verdict mỗi trục ∈ `{PASS, FAIL}` + lý do + token liên quan.

### A1 — Alignment

**Pass:** Mọi control trong cùng một layout group share **đúng 1 trục căn** (`align` prop nhất quán); không node con nào lệch khỏi grid cha.

**Detection:** Walk `layout` tree. Với mỗi primitive node có ≥2 children leaf, đọc `props.align`. FAIL nếu trong cùng group có children declare align mâu thuẫn không qua một wrapper trung gian hợp lệ, hoặc một leaf có offset/margin token phá trục chung.

**Cite:** structure-level grouping đã audit ở `layout-best-practices.md` L3 (field grouping) — A1 chỉ kiểm **trục căn đã resolve**, không re-audit grouping intent.

### A2 — Spacing rhythm

**Pass:** Mọi khoảng cách giữa section/group (resolved px từ `gap`, `vertical_rhythm`, `grouping[].separation`) ∈ **{spacing scale steps}** của `master_token.json`. Không giá trị lẻ ngoài scale. Nhịp dọc giữa các section ngang hàng **nhất quán** (cùng 1 step, trừ khi `visual_intent` khai báo intent khác).

**Detection:** Resolve mọi gap/separation sang px. So với `global.spacing.scale` value set. FAIL nếu: (a) px ∉ scale set, hoặc (b) các section sibling dùng ≥3 step khác nhau không có `visual_intent.grouping` lý giải (chaotic rhythm).

**Cite:** spacing multiplier validity → `best-practices.md` §4.1. A2 kiểm **rhythm consistency trong bố cục**, không re-validate scale.

### A3 — Visual hierarchy

**Pass:** `visual_intent.emphasis_order` tồn tại và có **đúng 1** entry `level: "primary"`; control `primary` resolve sang token weight (color emphasis / font weight / size) **trội hơn** mọi control `tertiary` trong cùng view.

**Detection:** Đếm `level: primary` trong `emphasis_order`. Resolve component token weight của primary vs tertiary. FAIL nếu: 0 hoặc ≥2 primary; hoặc primary control resolve sang visual weight ≤ một tertiary (hierarchy đảo / phẳng).

**Cite:** single-primary-action intent → `layout-best-practices.md` L1 (owner, structure). A3 kiểm hierarchy **đã materialize sang token weight** — phần L1 không chạm (L1 đếm intent, A3 đo weight đã resolve).

### A4 — Density balance

**Pass:** Mật độ control (số leaf control / tổng vertical space đã resolve) khớp `visual_intent.density` đã chọn (`compact` | `comfortable` | `spacious`); không quá chật (gap < min step cho density) cũng không quá rỗng (gap > max step).

**Detection:** Đếm leaf controls trong layout tree. Tính tổng resolved gap. So tỉ lệ với band kỳ vọng của `density` level (band lấy từ token group density nếu có, fallback spacing scale). FAIL nếu density declared = `comfortable` nhưng resolved gap rơi vào band `compact`/`spacious` (mismatch intent ↔ giá trị).

**Gap note:** Thiếu token group "density levels" tường minh → emit `RESOLVE_GAP` (density band undefined) → propose `[NEW]` token group, fallback dùng spacing scale band. KHÔNG block nếu fallback resolve được.

### A5 — Color & contrast

**Pass:** Mọi cặp `fg`/`bg` token dùng trong schema (component states + text) resolve sang hex đạt **WCAG AA** (≥4.5:1 normal text, ≥3:1 large/UI); số màu accent dùng đồng thời ≤ ngưỡng DS (`semantic.action.*` count).

**Detection:** Với mỗi component state declare fg+bg token, resolve hex, tính contrast ratio. Đếm distinct accent token. FAIL nếu bất kỳ cặp < ngưỡng AA, hoặc accent count > ngưỡng DS.

**Cite:** WCAG ratio rule **owned bởi** `best-practices.md` (accessibility section) — A5 KHÔNG redefine công thức, chỉ **apply lên cặp fg/bg đã resolve trong schema cụ thể** và đếm accent. Ratio < AA → FAIL (đây là hard, không override kể cả hard-pass exception).

### A6 — Typographic scale

**Pass:** Mọi text token dùng (size + weight) ∈ **type scale** của `master_token.json` (`global.font.size`); bước nhảy giữa các cấp text liền kề trong cùng view không "nhảy cấp bất thường" (skip >1 scale step không có hierarchy intent).

**Detection:** Resolve mọi text size token sang px. So với `global.font.size` scale set. Kiểm sequence cấp text trong layout (heading → body → caption) không skip cấp vô lý. FAIL nếu size ∉ scale, hoặc jump bất thường không khớp `emphasis_order`.

**Cite:** type-scale ratio validity → `best-practices.md` (type scale section). A6 kiểm **cách dùng scale trong bố cục**, không re-validate ratio.

### A7 — Affordance clarity

**Pass:** Mọi interactive control (button, input, link, toggle... — leaf có FSM transition) declare đầy đủ **state token** cho `hover` / `focus` / `disabled` (và `error` nếu control có validation) trong component composition.

**Detection:** Cross-ref `state_machine` + `data_bindings.controls[]` interactive set với component states declared. FAIL nếu một control interactive thiếu ≥1 state token bắt buộc (focus luôn bắt buộc — a11y; hover bắt buộc cho pointer affordance; disabled bắt buộc nếu FSM có disabled state).

**Cite:** state completeness intent → `layout-best-practices.md` (mandatory states). A7 kiểm **state token đã declare ở tầng component** cho control đã resolve, không re-audit wireframe state list.

## 5. Findings schema

`visual_composition_auditor` emit findings list, mỗi finding:

```json
{
  "axis": "A2",
  "verdict": "FAIL",
  "reason": "section_gap giữa R1.G1 và R1.G2 resolve = 18px, không thuộc spacing scale {4,8,12,16,24,32}",
  "tokens": ["tokens.spacing.section_gap"],
  "suggested_fix": "đổi visual_intent.grouping[0].separation sang tokens.spacing.scale.6 (=24px)",
  "kind": "AXIS_FAIL"
}
```

`kind` ∈:
- `AXIS_FAIL` — trục fail, fixable bằng đổi token reference trong `visual_intent` → self-correct loop xử lý.
- `RESOLVE_GAP` — token reference cần thiết chưa tồn tại trong DS (vd density band) → emit gap note → proposal `[NEW]`, KHÔNG tự thêm; nếu có fallback resolve được thì không block.
- `NEEDS_NEW_TOKEN` / `NEEDS_NEW_COMPONENT` — rubric phát hiện cần token/component mới để pass → escalate Step 1 proposal (đúng cơ chế hiện hữu), KHÔNG fabricate.

## 6. Verdict tổng

```
PASS  ⟺ mọi trục A1..A7 = PASS
FAIL  ⟺ ≥1 trục = FAIL (hoặc RESOLVE_GAP/NEEDS_NEW_* không fallback được)
```

- FAIL với chỉ `AXIS_FAIL` → Step 4 self-correct loop (đổi token reference, re-lint), cap N=3 vòng.
- FAIL với `RESOLVE_GAP` không fallback / `NEEDS_NEW_*` → escalate (proposal `[NEW]` hoặc HITL gate) — không tự fix bằng fabricate.
- Sau N=3 vòng vẫn FAIL → HITL visual gate (Step 4 §4).

Verdict + findings ghi vào `aesthetic_review_{id}.md`; điểm tổng (`PASS`/`FAIL`) điền vào `ui_schema_{id}.json` key `visual_intent._rubric_score`.

## 7. Override & tinh chỉnh

Rubric là `_shared/` editable. HITL có thể:
- Override 1 trục FAIL → PASS với lý do ghi vào `aesthetic_review_{id}.md` (vd: density intentional cho domain data-heavy). **Ngoại lệ:** A5 contrast < WCAG AA **không override** (a11y hard floor).
- Tinh chỉnh tiêu chí (vd accent count threshold) — sửa file này, version bump.
