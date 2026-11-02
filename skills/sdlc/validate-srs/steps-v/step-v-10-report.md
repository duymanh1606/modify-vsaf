---
# model: haiku
# findingsDir: '{output_folder}/_validation_temp'
# contextFile: '{output_folder}/_validation_temp/context.yaml'
---

# Step V-10: Tổng hợp Report

---

## 0. Load All Findings from YAML Files

**Read all findings YAML files from `{findingsDir}` (do NOT re-read the report prose):**
- `findings-business-alignment.yaml` (weight 1.2)
- `findings-completeness.yaml` (weight 1.0)
- `findings-consistency.yaml` (weight 1.0)
- `findings-quality.yaml` (weight 1.0)
- `findings-system-nfr.yaml` (weight 1.0)
- `findings-delivery-readiness.yaml` (weight 1.0)
- `findings-risk-analysis.yaml` (weight 0.8)
- `findings-user-impact.yaml` (weight 0.7)

Extract `dimension_score` and `findings` array from each file. These 8 YAML files (~400 lines total) replace re-reading the entire prose report.

**Score verification (MANDATORY — unconditional):**

Canonical N per dimension: BA=11, COMP=29, CONS=19, QUAL=15, NFR=7, DR=13, RA=13, UI=13

For each findings YAML file:
1. Read ALL `item_scores` values (must have exactly N entries per dimension above)
2. Compute `verified_score = round(sum(item_scores.values()) / N × 100, 1)` using canonical N
3. **ALWAYS use `verified_score` as the authoritative score — unconditionally, regardless of diff size**
   - If verified ≠ header: log "⚠ {dimension}: header={X}%, calculated={Y}%, using {Y}%"
   - If verified = header: log "✓ {dimension}: {Y}% (verified)"
4. Use verified scores for ALL subsequent calculations

Do NOT use `dimension_score` from YAML header under any circumstance — headers are informational only.
Do NOT apply any post-hoc adjustment or calibration to verified scores.

## 1. Tính Overall Score & Confidence Level

Lấy scores từ các steps trước:

| Dimension | Weight | Score | Status |
|---|---|---|---|
| Business Alignment | 1.2 | {biz_alignment_score}% | {OK/WARN/FAIL} |
| Completeness | 1.0 | {completeness_score}% | {OK/WARN/FAIL} |
| Consistency | 1.0 | {consistency_score}% | {OK/WARN/FAIL} |
| Quality | 1.0 | {quality_score}% | {OK/WARN/FAIL} |
| System & NFR | 1.0 | {system_nfr_score}% | {OK/WARN/FAIL} |
| Delivery Readiness | 1.0 | {delivery_readiness_score}% | {OK/WARN/FAIL} |
| Risk Analysis | 0.8 | {risk_score}% | {OK/WARN/FAIL} |
| User Impact | 0.7 | {user_impact_score}% | {OK/WARN/FAIL} |

```
overall_score = (biz×1.2 + comp×1.0 + cons×1.0 + qual×1.0 + nfr×1.0 + ready×1.0 + risk×0.8 + user×0.7)
               / 7.7 × 100%
```

Overall status: OK ≥ 80%, WARN 60–79%, FAIL < 60%

**Confidence Level:**
- **High**: ≥ 5 dimensions có Full evidence (score ≥ 0.75)
- **Medium**: 3–4 dimensions có Full evidence
- **Low**: ≤ 2 dimensions có Full evidence hoặc có nhiều TBD/Missing

---

## 2. GO / NO-GO Decision

Xác định:

- **GO**: overall_score ≥ 80% AND không có CRITICAL findings
- **CONDITIONAL GO**: overall_score 60–79% OR có HIGH findings nhưng không CRITICAL
- **NO-GO**: overall_score < 60% OR có CRITICAL findings

---

## 3. Viết Executive Summary (section 1)

Thay nội dung section "1. Executive Summary" trong report file:

```markdown
## 1. Executive Summary

**Decision: {GO / CONDITIONAL GO / NO-GO}**
**Overall Score: {overall_score}% — {overall_status}**
**Confidence: {High / Medium / Low}**

| Metric | Value |
|---|---|
| Files reviewed | {count} |
| Total findings | {total} |
| CRITICAL | {count_critical} |
| HIGH | {count_high} |
| MEDIUM | {count_medium} |
| LOW | {count_low} |
| Unresolved Questions | {count_questions} |

### Tóm tắt
{2-3 câu tổng quan về chất lượng SRS, highlight vấn đề lớn nhất}

### Top 3 Risks
1. {risk 1 — 1 dòng}
2. {risk 2 — 1 dòng}
3. {risk 3 — 1 dòng}
```

---

## 4. Viết Overall Score & Confidence (section 2)

```markdown
## 2. Overall Score & Confidence

**Score: {overall_score}% ({overall_status}) | Confidence: {level}**

| Dimension | Weight | Score | Status |
|---|---|---|---|
| Business Alignment | 1.2 | {X}% | {status} |
| Completeness | 1.0 | {X}% | {status} |
| Consistency | 1.0 | {X}% | {status} |
| Quality | 1.0 | {X}% | {status} |
| System & NFR | 1.0 | {X}% | {status} |
| Delivery Readiness | 1.0 | {X}% | {status} |
| Risk Analysis | 0.8 | {X}% | {status} |
| User Impact | 0.7 | {X}% | {status} |
| **Overall** | **7.7** | **{X}%** | **{status}** |
```

---

## 5. Viết Heatmap (section 3)

```markdown
## 3. Heatmap — Score by Dimension

| Dimension | Score | Bar |
|---|---|---|
| Business Alignment | {X}% | {████░░░░░░} |
| Completeness | {X}% | {████████░░} |
| Consistency | {X}% | {██████░░░░} |
| Quality | {X}% | {███████░░░} |
| System & NFR | {X}% | {████░░░░░░} |
| Delivery Readiness | {X}% | {██████░░░░} |
| Risk Analysis | {X}% | {████████░░} |
| User Impact | {X}% | {█████░░░░░} |

Legend: █ = 10%, OK ≥ 80%, WARN 60–79%, FAIL < 60%
```

Use █ for filled blocks and░ for empty, 10 blocks total per row.

---

## 6. Viết Top Missing Areas (section 6)

Phân tích findings và liệt kê top areas bị thiếu nhất:

```markdown
## 6. Top Missing Areas

| Priority | Area | Dimensions Affected | Severity |
|---|---|---|---|
| 1 | {VD: NFR / Performance targets} | System & NFR | CRITICAL |
| 2 | {VD: API contracts thiếu schema} | Delivery Readiness | HIGH |
| 3 | {VD: Business KPI chưa có} | Business Alignment | HIGH |
| ... | | | |
```

---

## 7. Viết Action Plan (section 8)

```markdown
## 8. Action Plan

### Fix ngay — Trước Sprint (CRITICAL)
1. {action} — Ref: finding #{n}
2. ...

### Fix trước Dev — Sprint 1 (HIGH)
1. {action} — Ref: finding #{n}
2. ...

### Fix sau Release — Sprint 2+ (MEDIUM/LOW)
1. {action}
2. ...

### Cần PO/Stakeholder quyết định
1. {question} — Ref: question #{n}
2. ...
```

---

## 7b. Regression Analysis

Read `regression` from context.yaml.

If `previous_report` exists:
1. **Score trend:** `{previous_score}% → {current_score}%` (↑/↓/→)
2. **Fixed findings:** For each previous CRITICAL/HIGH finding ID, check if it still appears in current findings. If not → "FIXED ✓"
3. **Recurring findings:** Present in both → "RECURRING ⚠ — not fixed since {previous_date}"
4. **New findings:** Current findings not in previous → "NEW"

Write regression table in report:

```markdown
## 7b. Regression Analysis

Previous: {previous_report} — {previous_score}% {previous_status}
Current: {current_score}% {current_status}
Trend: {↑X% | ↓X% | →}

| Finding | Previous | Current | Status |
|---|---|---|---|
| C-001 (service boundary) | CRITICAL | CRITICAL | RECURRING ⚠ |
| DR-002 (API specs) | HIGH | HIGH | RECURRING ⚠ |
| RISK-001 (appeal flow) | — | HIGH | NEW |
```

If `previous_report` is null: write "First validation run — no regression baseline available."

---

## 8. Viết Appendix: Full Scoring Matrix (section 9)

```markdown
## 9. Appendix: Full Scoring Matrix

### Per-File Summary

| File | Biz Align | Completeness | Consistency | Quality | Sys NFR | Readiness | Risk | User Impact | Average |
|---|---|---|---|---|---|---|---|---|---|
| {file1} | {X}% | {X}% | {X}% | {X}% | {X}% | {X}% | {X}% | {X}% | {X}% |

### All Findings

| # | Severity | Dimension | File | Item ID | Score | Evidence | Suggestion | Source |
|---|---|---|---|---|---|---|---|---|
| {complete findings table from all steps} |
```

---

## 9. Update frontmatter

Update report file frontmatter:

```yaml
overall_score: {overall_score}%
overall_status: {OK/WARN/FAIL}
confidence_level: {High/Medium/Low}
go_nogo: {GO/CONDITIONAL GO/NO-GO}
stepsCompleted:
  - step-v-01-discovery
  - step-v-02-business-alignment
  - step-v-03-completeness
  - step-v-04-consistency
  - step-v-05-quality
  - step-v-06-system-nfr
  - step-v-07-delivery-readiness
  - step-v-08-risk-analysis
  - step-v-09-user-impact
  - step-v-10-report
```

---

## 10. Final Output

Thông báo cho user:

```
SRS Validation Report (V2) hoàn tất!

Decision: {GO / CONDITIONAL GO / NO-GO}
Overall Score: {overall_score}% — {overall_status}
Confidence: {High / Medium / Low}
Report: {output_path}

Findings: {total} (CRITICAL: {c}, HIGH: {h}, MEDIUM: {m}, LOW: {l})
Unresolved Questions: {count}

Dimension scores:
  Business Alignment: {X}% {status} [w:1.2]
  Completeness:       {X}% {status} [w:1.0]
  Consistency:        {X}% {status} [w:1.0]
  Quality:            {X}% {status} [w:1.0]
  System & NFR:       {X}% {status} [w:1.0]
  Delivery Readiness: {X}% {status} [w:1.0]
  Risk Analysis:      {X}% {status} [w:0.8]
  User Impact:        {X}% {status} [w:0.7]

Action Required:
  - {count} CRITICAL issues → Fix trước Sprint
  - {count} HIGH issues → Fix trước implementation
  - {count} questions → Cần PO decision
```

**Workflow hoàn tất. Không có step tiếp theo.**

## [NEW] Cleanup

After report is complete:
- Delete all `{findingsDir}/findings-*.yaml` temp files
- Keep `{findingsDir}/context.yaml` for potential re-runs
