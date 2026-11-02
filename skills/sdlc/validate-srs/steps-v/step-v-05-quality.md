# Step V-05: Quality — Kiểm tra chất lượng nội dung

---
# model: haiku
# findingsOutput: '{output_folder}/_validation_temp/findings-quality.yaml'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
# grepPatterns: '../data/grep-patterns-srs.yaml'
---

## 0. Load Context and Patterns

Read `{contextFile}` → get `srs_path`, `srs_section_index`, `uc_cache`.
Read `{grepPatterns}` → load `vague_vietnamese`, `vague_english`, `ac_format`, `srs_structure`, `diagram_syntax` pattern groups.

**ALL checks in this step use Grep tool. Do NOT use Read on the SRS file.**
**Exception: Section 3 (cross-file duplicate detection) may use targeted Read.**

---

## 1. Ambiguous Language Check (Grep-only)

Run Grep patterns from `vague_vietnamese` and `vague_english` groups against `srs_path`:
- Each pattern: output_mode="content", -n=true to get line numbers
- For each match, check context: is this in a BR/NFR/AC statement (flag) or a capability description (OK)?
- Count flagged violations by category

**Scoring (same as before):**
- > 10 flagged → Score 0.0
- 5–10 → Score 0.5
- 1–4 → Score 0.75
- 0 → Score 1.0

Item ID: `no_ambiguous_language`

---

## 2. Acceptance Criteria Format Check (Grep-only)

Run patterns from `ac_format` group against `srs_path`:
- `gherkin_gwt` pattern → count GWT ACs
- `vietnamese_conditional_ac` pattern → count Vietnamese-style ACs
- `ac_id_pattern` → count AC IDs (confirms ACs are formally defined)

Also check from `uc_cache` in context.yaml: count UCs → expected ≥ 1 AC per UC.

**Scoring:** Same as before (GWT+measurable=1.0, AC no GWT=0.5, text only=0.25, none=0.0)

Item ID: `acceptance_criteria_format`

---

## 3. Duplicate requirements check

Tìm requirements trùng lặp:

### 3.1 Intra-file
- Cùng requirement xuất hiện ở nhiều UC trong 1 file?

### 3.2 Cross-file (nếu batch/full)
- Cùng requirement xuất hiện ở nhiều SRS files?
- VD: Consent management overlap giữa FR-1 và FR-15

**Nếu phát hiện overlap:**
- Đánh giá mức độ: identical (0.0) vs complementary (0.75)
- Gợi ý file nào nên own requirement

Item ID: `no_duplicate_requirements`

---

## 4. Scope clarity check

Kiểm tra mỗi SRS file có:

- Section "Phạm vi chức năng" hoặc In-scope?
- Section "Ngoài phạm vi" hoặc Out-of-scope?
- Ranh giới rõ ràng với FRs liên quan?

**Scoring:**
- Có cả In + Out scope → 1.0
- Có In scope nhưng thiếu Out scope → 0.5
- Có "Flow liên quan" nhưng không explicit scope → 0.5
- Không có gì → 0.0

Item ID: `clear_scope`

---

## 5. Opaque rule check

Kiểm tra các Business Rule và policy statements trong SRS:

- Rule phải tự giải thích được mà không cần PO interpret. Dấu hiệu rule mơ hồ:
  - Tham chiếu undefined term: "sensitive details not exposed until acceptance" — "acceptance" là event gì?
  - Điều kiện không rõ ràng: "khi phù hợp", "tùy context", "nếu cần thiết"
  - Rule thiếu subject: "không exposed" — ai không exposed? service nào? endpoint nào?
- Mỗi rule mơ hồ → ghi finding với suggestion rewrite rõ ràng
- Phân biệt với `no_ambiguous_language` (mục 1): mục này focus vào rule semantics, không chỉ từ vựng

**Scoring:**
- Tất cả rule self-explanatory → 1.0
- 1-2 rule cần clarify nhỏ → 0.75
- 3+ rule mơ hồ, hoặc 1 rule core không hiểu được → 0.5
- Rule core hoàn toàn không interpret được → 0.0 (HIGH)

Item ID: `rules_self_explanatory`

---

## 5b. Cross-Role Readability Check

Kiểm tra requirement có thể hiểu giống nhau bởi BA, Dev, và QA không:

**Dấu hiệu viết sai:**
- Dùng thuật ngữ nghiệp vụ chưa được định nghĩa trong Glossary (section 1.2)
- Câu có thể hiểu theo 2 cách tuỳ người đọc — VD: "hệ thống kiểm tra hợp lệ" → BA hiểu là validate UI, Dev hiểu là DB check, QA hiểu là API check
- Subject không rõ — "sẽ gửi thông báo" → ai gửi? đến ai?
- Điều kiện dạng "nếu cần" / "nếu phù hợp" → Dev và QA không thể ra testcase

**Cách kiểm tra:**
- Với mỗi UC step có hành động quan trọng (validate, send, update, check): subject + verb + object có đủ không?
- Với mỗi business rule: trigger condition → action → result có viết đủ 3 phần không?
- Có term nào trong flow tables không có trong Glossary? → flag để bổ sung

**Scoring:**
- Tất cả requirements rõ subject/verb/result, dùng term đã glossarized → 1.0
- 1-3 steps có subject mơ hồ hoặc term chưa glossarize → 0.75
- Nhiều steps thiếu subject/result rõ ràng → 0.5
- Core flow steps không thể viết testcase vì quá mơ hồ → 0.25 (HIGH)

Item ID: `cross_role_readability`

---

## 5c. Testability per Requirement

Kiểm tra mỗi UC/AC có thể viết testcase độc lập không:

- Mỗi AC có exactly 1 expected outcome cụ thể không?
  - BAD: "hệ thống xử lý phù hợp" / "hệ thống phản hồi kịp thời"
  - GOOD: "hệ thống trả HTTP 200 với body `{status: 'CREATED'}` trong < 2s"
- Có AC nào kết quả phụ thuộc vào external state không rõ ràng không?
  - VD: "nếu insurer accept" — điều kiện này có thể simulate trong test không?
- Có UC nào không có AC hoặc chỉ có AC chung chung → không thể viết test → CRITICAL

**Scoring:**
- Tất cả AC có expected outcome rõ, testable → 1.0
- Phần lớn rõ, 1-2 AC cần clarify expected result → 0.75
- Nhiều AC thiếu expected result cụ thể → 0.5
- AC chỉ describe behavior mà không có measurable outcome → 0.25 (HIGH)
- Không có AC → 0.0 (CRITICAL)

Item ID: `testability_per_requirement`

---

## 5d. Section Numbering Consistency (Grep-only)

Kiểm tra heading số thứ tự nhất quán với cấu trúc template mới:

**Template expected heading structure:**
```
## 1. Mô tả chung
### 1.1 / 1.2 / 1.3
## 2. Đặc tả Use Cases
### 2.1 / 2.2 ...
## 3. Danh sách mã lỗi
## 4. Chức năng ảnh hưởng
## 5. Business Rules
## 6. Yêu cầu phi chức năng
### 6.1 / 6.2 ... (not 7.1 / 7.2)
## 7. Ràng buộc, Giả định & Phụ thuộc
### 7.1 / 7.2 / 7.3 / 7.4 (not 8.1 / 8.2)
## 8. State Diagrams
## 9. Ma trận truy xuất
```

**Grep checks:**
1. Grep `^### [78]\.\d` in srs_path → if found inside a `## 6.` section (NFR section) → MEDIUM: section 6 has wrong sub-headings
2. Grep `^### [89]\.\d` in srs_path → if found inside a `## 7.` section → MEDIUM: section 7 has wrong sub-headings

**Scoring:**
- Không có heading mismatch → 1.0
- 1 section có sub-heading dùng số section cha sai → 0.75 (MEDIUM finding)
- Nhiều sections bị mismatch → 0.5

Item ID: `section_numbering_consistent`

---

## 6. Flow Step Quality (Grep-only)

- Grep `^\d+\.\s` in `srs_path` → check step numbering exists and is sequential
- Grep `→ chuyển bước|→ kết thúc|→ hiển thị lỗi|→ bước` → verify steps have outcomes
- Grep `Nhánh [A-Z]|Branch [A-Z]` → verify branching is explicit

Item IDs: `flow_step_numbering`, `flow_clarity`, `branching`

---

## 6. Diagram Syntax Check (Grep-only)

Run patterns from `diagram_syntax` group:
- Count `@startuml` occurrences vs `@enduml` occurrences → must be equal
- Grep `unfilled_placeholder_in_diagram` → any {{...}} still in diagrams? → CRITICAL

Item ID: `diagram_syntax_valid`

---

## 6c. Atomicity Check (LLM analysis)

Kiểm tra mỗi requirement/UC có chứa đúng 1 ý duy nhất — có thể dev/estimate/test độc lập:

### 6c.1 Single Responsibility per UC

- Mỗi UC title và scope có chỉ mô tả 1 hành vi duy nhất không?
- **Dấu hiệu vi phạm:**
  - Title dạng "Mua bảo hiểm và thanh toán và nhận HĐ" → compound UC, nên tách
  - UC mô tả cả happy path lẫn admin flow trong cùng 1 UC → scope quá rộng
  - UC vừa handle user action vừa xử lý background job cùng lúc

**Item ID:** `requirement_single_responsibility`

**Scoring:**
- Tất cả UC có scope đơn → 1.0
- 1-2 UC bị compound nhưng minor (dễ tách) → 0.75
- Nhiều UC compound → 0.5
- Core UC gộp nhiều flow không thể tách scope → 0.25 (HIGH)

---

### 6c.2 No Compound Requirements

- Mỗi Business Rule, AC, hoặc NFR statement có chỉ phát biểu 1 điều kiện → 1 kết quả không?
- **Dấu hiệu vi phạm:**
  - "Hệ thống validate form **và** gửi email **và** cập nhật DB" trong 1 câu requirement
  - BR dùng "đồng thời", "cùng lúc đó", "và cũng" → 2 hành vi trong 1 rule
  - AC có nhiều `Then` cho 1 `When` → nên tách thành 2 AC

**Item ID:** `no_compound_requirement`

**Scoring:**
- Tất cả BR/AC là single-statement → 1.0
- Vài BR có 2 điều kiện nhưng logic liên quan chặt → 0.75
- Nhiều BR/AC compound → 0.5
- Core BR không thể phân tách rõ → 0.25

---

### 6c.3 Independently Estimable

- Mỗi UC có thể được Dev estimate và implement mà không cần UC khác chưa done không?
- **Dấu hiệu vi phạm:**
  - UC A hardcode phụ thuộc UC B nhưng UC B chưa trong sprint
  - UC A chỉ có ý nghĩa khi UC C cũng deploy cùng lúc → không thể ship độc lập
  - UC giả định API từ service khác đã sẵn sàng nhưng không nêu dependency rõ

**Lưu ý:** Có dependency ≠ vi phạm. Vi phạm là dependency KHÔNG ĐƯỢC GHI RÕ hoặc dependency chưa confirmed.

**Item ID:** `independently_estimable`

**Scoring:**
- Tất cả UC hoặc có dependency ghi rõ (và confirmed) hoặc independent → 1.0
- 1-2 UC có implied dependency chưa document → 0.75
- Nhiều UC phụ thuộc chéo nhau không rõ → 0.5
- Sprint không thể plan được vì UC entangled → 0.25 (HIGH)

---

## 7. Tính Quality dimension score

```
quality_score = round(sum(item_scores.values()) / 15 × 100, 1)
```

Canonical item IDs (N = 15, fixed):
`no_ambiguous_language`, `acceptance_criteria_format`, `no_duplicate_requirements`, `clear_scope`, `rules_self_explanatory`, `cross_role_readability`, `testability_per_requirement`, `section_numbering_consistent`, `flow_step_numbering`, `flow_clarity`, `branching`, `diagram_syntax_valid`, `requirement_single_responsibility`, `no_compound_requirement`, `independently_estimable`

⚠️ MANDATORY: N = 15 (fixed). N/A items → score = 1.0 (do not skip from denominator). No post-hoc calibration. dimension_score in YAML = formula result only.

---

## 8. Append findings vào report

Append CRITICAL/HIGH → section "4. Critical & High Findings". Append MEDIUM/LOW → section "5. Medium & Low Findings".

Update frontmatter: thêm `step-v-05-quality` vào `stepsCompleted`.

---

## [NEW] Write Structured Findings

Write file `{findingsOutput}`:
```yaml
# findings-quality.yaml — generated by step-v-05
# model: haiku | weight: 1.0

dimension: quality
weight: 1.0
dimension_score: 0   # calculated: sum(scores)/count × 100
status: OK           # OK | WARN | FAIL
findings:
  []  # list of {item_id, severity, score, evidence, suggestion, source}
summary:
  total: 0
  critical: 0
  high: 0
  medium: 0
  low: 0
item_scores:
  no_ambiguous_language: 0.0
  acceptance_criteria_format: 0.0
  no_duplicate_requirements: 0.0
  clear_scope: 0.0
  rules_self_explanatory: 0.0
  cross_role_readability: 0.0
  testability_per_requirement: 0.0
  section_numbering_consistent: 0.0
  flow_step_numbering: 0.0
  flow_clarity: 0.0
  branching: 0.0
  diagram_syntax_valid: 0.0
  requirement_single_responsibility: 0.0
  no_compound_requirement: 0.0
  independently_estimable: 0.0
```

---

## 9. Menu

```
Quality Score: {X}% ({status})
- CRITICAL: {count}
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}

[C] Continue — Sang System & NFR (Step V-06)
[D] Detail — Xem chi tiết findings
[X] Cancel
```

**Chờ user chọn.**

Khi user chọn **C**: đọc fully và follow `./step-v-06-system-nfr.md`
