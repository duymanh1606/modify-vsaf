# STEP 13: RESPONSIVE, ACCESSIBILITY & AUDIT LOG RULES → `ux_conventions.md` §C6-C7

> **Thực hiện bởi:** Agent UX0 (UX Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R3, R5**. Ghi TRỰC TIẾP vào `ux_conventions.md` (ngoại lệ R1).

## 0. Delta-mode check (chạy TRƯỚC)

Delta mode VÀ §C6/§C7 hiện có vẫn đủ (feature không thêm component pattern responsive mới, không đổi a11y yêu cầu, không entity audit mới) → SKIP (log "§C6-C7 no delta").

## 1. Mục tiêu

§C6 Responsive & Accessibility (breakpoint pointer + adaptation + WCAG AA checklist + shell blueprint chung) + §C7 Audit Log UX rules. Project-wide.

## 2. Đầu vào cần đọc

- `master_token.json` — `tokens.breakpoint.*` canonical (thiếu → STOP, chạy `/ntapp-ds-bootstrap`)
- Journey spec §2 (composition — indicator adaptation) + §3 (shell placement) + §4 (key screens)
- PRD — NFR responsive, NFR accessibility, FR audit log

## 3. Chỉ thị thực thi

### 3.1. §C6 Breakpoints (pointer)

KHÔNG embed bảng: pointer `master_token.json → tokens.breakpoint.*`; mọi responsive behavior reference token path (`tokens.breakpoint.md`), KHÔNG hardcode px.

### 3.2. §C6 Responsive Behavior

Per critical component (sidebar / section indicator / form layout / dashboard widget grid / data table) × 3 variants (desktop/tablet/mobile) — adapt theo archetype + composition. Touch target ≥44px (token `tokens.spacing.touch-target`).

### 3.3. §C6 Accessibility Checklist (WCAG AA)

Checkbox list ≥8 mục: explicit labels; tab order logic; screen-reader text cho status icon (`aria-label`); contrast ≥4.5:1 text / ≥3:1 large+UI *(cùng ngưỡng `best-practices.md` mà Stage 4b enforce qua `WCAG_CONTRAST_FAIL` + A5 — cite, không redefine)*; focus indicator; error→field linkage (`aria-describedby`); keyboard nav (Tab/Enter/Esc); ARIA live regions (`role="status"`/`role="alert"`); skip link; alt text; không color-only signal.

### 3.4. §C6 Shell Layout Blueprint (chung)

Nếu project chưa có shell doc: 1 khung ASCII duy nhất (header / nav / breadcrumb / content / action bar / status bar) + region rules theo archetype. Journey specs (§3.2) từ nay chỉ REFERENCE khung này. Đã có từ trước → giữ, chỉ patch khi feature đòi region mới.

### 3.5. §C7 Audit Log UX Rules

**Applicable:** archetype có persistent entity state (skip TRANSACTIONAL lookup / DASHBOARD read-only). RULES ONLY — screen SCR-AUDITLOG chi tiết là việc DD Stage 4a:
- Immutable (không edit/delete control); chronological most-recent-first, group-by-date; actor = name + role (system → "System"); log cả human + system action (auto-save, sync, notification); pagination load-more (không render full history). Cite PRD FR audit (immutability).

## 4. Đầu ra yêu cầu

- **Ghi trực tiếp:** `ux_conventions.md` §C6 + §C7 + CHANGE LOG rows.
- Báo cáo: "§C6-C7 {bootstrap | delta | no delta}. {X} responsive components, {Y} a11y items, audit rules {set/skipped}."

**Next:** Read fully and follow `./step-14-traceability-assembly.md`
