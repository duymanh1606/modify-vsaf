# Pattern Matcher

**Schema version:** 1.0
**Type:** Logic guide for component/token similarity matching
**Used by:**
- `/ntapp-ds-bootstrap` (sub-agent: `component-discoverer`) — match discovered components vs existing metadata
- `/ntapp-ui-generation` Stage 4b Agent 1 (step-01 Stage 3.1) — **matching thủ tục chính**: score toàn inventory per control, top-3 shortlist → `[REUSE AUDIT]`, threshold §2 quyết reuse/MODIFIED/NEW + flag FUNCTIONAL_DUPLICATE
- `/ntapp-ds-build-component` (sub-agent: `delta-router`) — distinguish MODIFIED from NEW

---

## 1. Mục đích

Định nghĩa cách AI agent so sánh 2 component (hoặc 2 token) để xác định:
- Identical (same component, different name)
- Similar (functional duplicate)
- Variant relationship (one extends the other)
- Different

Output dùng cho: routing delta sang đúng category (NEW vs MODIFIED), cảnh báo duplicate, retrieval ranking.

## 2. Similarity score

Mọi comparison output 1 score `[0.0, 1.0]`:

| Score | Interpretation | Action |
|---|---|---|
| `≥ 0.95` | EXACT or ALIAS | Treat as same → MODIFIED không NEW |
| `0.70 - 0.94` | FUNCTIONAL_DUPLICATE | Flag warning, DSO clarify |
| `0.50 - 0.69` | VARIANT / EXTENSION | Đề xuất extend existing thay vì NEW |
| `< 0.50` | DIFFERENT | Treat as NEW |

Threshold có thể override qua `.bmm-config.yaml`.

## 3. Component matching — multi-signal scoring

Score là weighted average của 4 signal:

```
score = 0.40 * intent_similarity
      + 0.25 * structural_similarity
      + 0.20 * tag_overlap
      + 0.15 * accessibility_match
```

### 3.1 `intent_similarity` — semantic intent

So sánh `abstract.semantic_intent` của 2 component.

**Hướng dẫn cho LLM evaluator:**
- Đọc 2 đoạn `semantic_intent`.
- Hỏi: "2 component này giải quyết cùng UX problem không?"
- Output `[0.0, 1.0]`:
  - `1.0` — Cùng problem, cùng UX pattern (vd: cả 2 đều là "transient feedback message")
  - `0.7-0.9` — Cùng problem, UX pattern hơi khác (vd: Toast vs Banner — đều là feedback nhưng position khác)
  - `0.4-0.6` — Liên quan nhưng khác problem (vd: Toast vs Tooltip — cả 2 hiện ngắn nhưng intent khác)
  - `< 0.4` — Khác hẳn

### 3.2 `structural_similarity` — variants + states + inputs

So sánh structure:

```
structural = 0.4 * jaccard(variants_A, variants_B)
           + 0.4 * jaccard(states_A, states_B)
           + 0.2 * input_signature_match
```

`jaccard(A, B) = |A ∩ B| / |A ∪ B|` — % overlap của 2 set.

`input_signature_match`:
- 2 component có same set tên prop + compatible types → 1.0
- Subset relationship (A ⊂ B) → 0.7
- Khác hẳn → 0.0

### 3.3 `tag_overlap` — keyword tags

```
tag_overlap = jaccard(tags_A, tags_B)
```

Direct.

### 3.4 `accessibility_match` — role / aria

```
accessibility_match = 1.0  if role_A == role_B
                    = 0.5  if compatible roles (vd: button + link)
                    = 0.0  otherwise
```

Role giống → high signal là same component type. Role khác hẳn → khả năng cao là khác component.

## 4. Token matching — đơn giản hơn

Token chỉ match theo path + value:

```
exact_path_match           → score 1.0  → MODIFIED candidate
similar_value_diff_path    → score 0.6  → DUPLICATE warning candidate
different                  → score 0.0
```

`similar_value_diff_path`: vd 2 token cùng `#ee0033` ở 2 path khác nhau → có thể là duplicate, đề xuất consolidate.

## 5. Practical workflow — agent steps

Khi cần match 1 candidate vs catalog hiện có:

```
1. Filter shortlist:
   - Cùng category (vd: candidate là `feedback`, chỉ match với feedback components)
   - Tags overlap ≥ 1
   → Thường ≤10 component

2. Compute similarity score cho mỗi candidate:
   - Apply 4-signal scoring
   - Phase 1 (IDE-native): LLM tự đánh giá `intent_similarity` qua prompt
   - Phase 1.5 (MCP service): dùng embedding cosine cho `intent_similarity`

3. Sort theo score descending.

4. Output top-3 với score:
   - Top-1 ≥ 0.95 → tự classify MODIFIED, log alias
   - Top-1 trong 0.70-0.94 → output WARNING (FUNCTIONAL_DUPLICATE)
   - Top-1 trong 0.50-0.69 → output suggestion ("extend X thay vì NEW?")
   - Top-1 < 0.50 → classify NEW
```

## 6. Example — Toast vs NotificationBanner

```
Proposed Toast:
  semantic_intent: "Hiển thị transient feedback message với auto-dismiss."
  variants: ["success", "error", "info"]
  states: ["entering", "visible", "leaving"]
  inputs: [message, type, duration]
  accessibility: { role: "alert" }
  tags: ["notification", "feedback", "transient"]

Existing NotificationBanner:
  semantic_intent: "Hiển thị notification message ở top of page với manual dismiss."
  variants: ["success", "warning", "error"]
  states: ["visible", "dismissed"]
  inputs: [message, type, dismissable]
  accessibility: { role: "alert" }
  tags: ["notification", "banner", "feedback"]

Compute:
  intent_similarity     = 0.75    (cùng problem, UX pattern khác — transient vs persistent)
  structural_similarity = 0.4*(2/4) + 0.4*(1/4) + 0.2*0.7 = 0.2 + 0.1 + 0.14 = 0.44
  tag_overlap           = 2/4 = 0.5
  accessibility_match   = 1.0     (cùng role)

  score = 0.40*0.75 + 0.25*0.44 + 0.20*0.5 + 0.15*1.0
        = 0.30 + 0.11 + 0.10 + 0.15
        = 0.66

Classification: VARIANT/EXTENSION (0.50-0.69)
Action: Suggest "Extend NotificationBanner with auto-dismiss + transient mode" thay vì NEW Toast.
DSO override: nếu transient là use case khác hẳn → OVERRIDDEN warning, build NEW Toast.
```

## 7. LLM evaluator prompt template

Khi agent cần `intent_similarity`:

```
Hai component dưới đây có giải quyết cùng UX problem không?

Component A: {semantic_intent_A}
Component B: {semantic_intent_B}

Trả lời theo format:
- score: [0.0, 1.0]
- reason: <1 câu>
- differentiator: <khác biệt chính nếu có, hoặc "none">
```

LLM trả structured response, agent extract score.

## 8. Performance & caching

**Phase 1 (IDE-native):**
- Mỗi run, LLM evaluate similarity on-demand cho shortlist (<10 cặp).
- Cache trong memory của session, KHÔNG persist (reset mỗi run).

**Phase 1.5 (MCP service):**
- Pre-compute embedding cho all components trong catalog.
- Vector search shortlist.
- LLM chỉ verify top-3 chứ không full pairwise.

## 9. Edge cases

| Case | Xử lý |
|---|---|
| 2 component có cùng tên (rename trong proposal) | Treat as MODIFIED, không tính similarity. |
| Candidate có `semantic_intent` rỗng | Reject — không match được. |
| Catalog trống | Mọi candidate là NEW. |
| Toàn bộ catalog có score tương tự nhau (no clear winner) | Output top-3, DSO chọn. Không auto-decide. |

---

**End of pattern-matcher v1.0.**
