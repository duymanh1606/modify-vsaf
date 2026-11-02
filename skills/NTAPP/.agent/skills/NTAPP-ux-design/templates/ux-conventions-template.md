---
workflowType: 'ux-conventions'
---

# UX CONVENTIONS — {{project_name}}

**Scope:** PROJECT SINGLETON — 1 file cho cả project, viết lần đầu khi feature multi-screen-new đầu tiên qua Stage 3b, các feature sau chỉ **delta-update** (thêm pattern mới / sửa khi PRD-NFR đổi). KHÔNG regenerate từ đầu mỗi feature.
**Consumers:** `feature-design` Stage 4a (F3 tuân §C1-C7 khi vẽ wireframe/control states), QA skills (`ntapp-qa-*` — §C4/§C5 là testable spec cho notification/error), Stage 5 dev.
**Nguồn canonical:** status enum ↔ Module 0 §7 (R8.2); token/component ↔ Master DS (R8.3); shell/screens ↔ journey spec + WBS.

---

## CHANGE LOG

| Date | Section | A/M/D | Feature trigger | Description |
|:-----|:--------|:------|:----------------|:------------|
| {{date}} | All | A | {{feature_name}} | Initial conventions |

---

<!--
TEMPLATE v1.0 — PROJECT UX CONVENTIONS (tách từ ux-design-spec v3.1 §3/§5/§11-15)
Đây là artifact SỐNG (living doc): steps 04/06/11/12/13 của /ntapp-ux-design ghi TRỰC TIẾP vào đây
(bootstrap mode: fill đủ; delta mode: chỉ append/patch section có thay đổi + CHANGE LOG row).
Ngoại lệ R1 verbatim-injection: file này KHÔNG assemble từ parts — steps ghi thẳng (atomic write).
-->

## C1. UX PRINCIPLES
<!-- Step 04 — Agent UX0. Core principles table {# | Principle | Description | Application in project} — min 7 (Progressive Disclosure / Consistency / Error Prevention / Recognition over Recall / Feedback & Visibility / Flexibility & Efficiency / Minimal Input), Application cite UI element/flow cụ thể. + Domain-specific principles (min 4, theo archetype). Enforcement reference: layout-best-practices.md L1-L11 (cite rule ID, không chép). -->

## C2. CONTENT STRATEGY & MICROCOPY
<!-- Step 06 — Agent UX4. (a) Writing rules table {Rule | Good | Bad} ≥5 — verb-first, ngôi 2, nói rõ hệ quả, không mã lỗi kỹ thuật, guide-to-fix; ví dụ dùng domain terminology thật. (b) Empty/Loading state spec (structured, không ASCII) — component §Master DS canonical. (c) STATUS LABELS: bảng {Display Status | Color token path | Module 0 §7 enum | User Description} — 1-1 mapping enum (R8.2), cover lifecycle theo archetype, color token canonical không hex. -->

## C3. INTERACTION PATTERNS
<!-- Step 11 — Agent UX0. (a) Form validation timing (inline on-blur / on-submit / cross-section) + error surface spec (inline field + summary panel, token refs). (b) View/Tab/Section transition table — cover đủ state taxonomy journey-spec §2.3 (valid switch / error switch / locked / blocked / optional / rejected), tooltip giải thích dependency cụ thể. (c) Confirmation dialogs table {Action | Has dialog? | Content principle} — universal + archetype-conditional; irreversible → BẮT BUỘC dialog. (d) Keyboard shortcuts table — universal FORM-HEAVY + archetype-conditional, không đè browser default. -->

## C4. NOTIFICATION SYSTEM
<!-- Step 12 — Agent UX4. (a) Event Notification Matrix {Event | Recipient | Channel | Timing | Title ≤8 words | Detail} — single source of truth, event set theo archetype (không bịa event ngoài workflow), timing cite PRD NFR SLA, detail có entity ref + actionable guidance. (b) 4 standard notification components {Pattern | Component (Master DS canonical) | Trigger | Dismiss}: Loading / Success / Error (kèm guidance + retry) / Info. -->

## C5. ERROR HANDLING & RECOVERY
<!-- Step 12 — Agent UX0 + UX4. (a) Universal principles ≥6 (never lose input; cause+guidance không raw code; luôn ≥1 action button; localize failure scope; retry limit 2; severe error kèm reference code + timestamp). (b) Error classification {Type | User sees | Severity | Recovery | Applicable archetype} — universal 4 (validation / network 3 sub-state / session expiry / unexpected) + conditional theo archetype. (c) Archetype edge cases (chỉ archetype đã chọn): partial sync fail, duplicate detection, step dependency breakage, auto-save & session recovery, stale data, edit conflict, publish conflict. -->

## C6. RESPONSIVE & ACCESSIBILITY
<!-- Step 13 — Agent UX0. (a) Breakpoints: POINTER tới master_token.json tokens.breakpoint.* (không embed bảng, không hardcode px). (b) Responsive behavior per critical component (sidebar / section indicator / form / widget grid / data table) × 3 variants (desktop/tablet/mobile), touch target ≥44px. (c) WCAG AA checklist ≥8 mục: labels, tab order, screen-reader text, contrast ≥4.5:1 / ≥3:1, focus indicator, error→field linkage, keyboard nav, ARIA live, skip link, alt text, không color-only. (d) Shell layout blueprint chung (ASCII 1 khung — header/nav/content/action bar) nếu project chưa doc ở đâu khác. -->

## C7. AUDIT LOG UX RULES
<!-- Step 13 — Agent UX0. Applicable: archetype có persistent entity state (skip TRANSACTIONAL lookup / DASHBOARD read-only). RULES ONLY (screen chi tiết → DD Stage 4a của SCR-AUDITLOG): immutable (không edit/delete), chronological most-recent-first group-by-date, actor = name + role (system action → "System"), human + system actions đều log, pagination load-more. Cite PRD FR audit. -->

---

*Template version: 1.0 (tách từ ux-design-spec v3.1 — §3→C1, §5→C2, §11→C3, §12→C4, §13→C5, §14→C6, §15→C7) | Framework: NTAPP Method*
