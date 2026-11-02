# STEP 11: INTERACTION PATTERNS → `ux_conventions.md` §C3

> **Thực hiện bởi:** Agent UX0 (UX Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R3, R5, R6**. Ghi TRỰC TIẾP vào `ux_conventions.md` (ngoại lệ R1).

## 0. Delta-mode check (chạy TRƯỚC)

Delta mode VÀ §C3 hiện có cover đủ state taxonomy + action set của feature mới → SKIP (log "§C3 no delta"). Feature thêm state/transition/dialog/shortcut mới → append rows tương ứng + CHANGE LOG.

## 1. Mục tiêu

"Luật chơi" tương tác project-wide: validation, transition, confirmation dialog, keyboard shortcut. Mọi screen (mọi feature) tuân theo.

## 2. Đầu vào cần đọc

- Journey spec §2 (archetype + composition + state taxonomy §2.3) + §4 (flows, decision points)
- §C1 (Error Prevention, Consistency, Flexibility) + §C2 (error message writing rules)
- `component_catalog.md` — form/dialog components; `master_token.json` — verify token (vd `semantic.color.border.danger`)
- PRD — BR validation, FR auto-save

## 3. Chỉ thị thực thi

### 3.1. §C3 Form Validation Rules

**Skip nếu** archetype không có input (DASHBOARD read-only). Timing 3 loại: inline on-blur (simple field) / on-submit (full form) / cross-section (composition ≠ SINGLE). Error surface spec (structured, token refs): inline field error (border `border.danger` + icon + message dưới field) + summary panel on submit (count + jump-link). Message theo §C2 guide-to-fix.

### 3.2. §C3 View / Tab / Section Transition

**Applicability:** composition ≠ SINGLE. Bảng `| Scenario | Behavior |` cover ĐỦ state taxonomy journey-spec §2.3: switch khi valid (auto-save + switch nếu có draft) / switch khi error (dialog keep-save-discard-stay) / click Locked (tooltip dependency cụ thể) / click Blocked (tooltip prerequisite) / click optional / click Rejected (prefill reason ở top). Skip state không tồn tại trong archetype.

### 3.3. §C3 Confirmation Dialogs

Bảng `| Action | Has dialog? | Content principle |`:
- Universal: Delete (YES — "không hoàn tác"), Cancel-with-unsaved (YES), Save draft (NO — toast silent), field edit (NO).
- Archetype-conditional: Submit-for-review / Approve-Reject (MAKER_CHECKER, reject cần reason), Finalize (WIZARD), Submit-tác-động-data (TRANSACTIONAL), Publish (CONTENT_MGMT), Execute-embedded-action (DASHBOARD).
- Nguyên tắc: irreversible → BẮT BUỘC dialog; undo dễ → silent + undo; dialog nói rõ HỆ QUẢ (§C2); destructive → button `danger`. KHÔNG bịa action ngoài archetype.

### 3.4. §C3 Keyboard Shortcuts

Universal FORM-HEAVY: Tab/Shift+Tab, Esc, Ctrl+S (archetype có draft), Ctrl+Enter (final review). Archetype-conditional: Alt+1..N (multi-section), Ctrl+A/Ctrl+R (MAKER_CHECKER reviewer), Ctrl+F / R (DASHBOARD), Ctrl+P (CONTENT_MGMT). Không đè browser default (Ctrl+T/W).

## 4. Đầu ra yêu cầu

- **Ghi trực tiếp:** `ux_conventions.md` §C3 + CHANGE LOG row.
- Báo cáo: "§C3 {bootstrap | delta | no delta}. {Y} transition scenarios (cover đủ taxonomy §2.3), {W} dialogs, {V} shortcuts."

**Next:** Read fully and follow `./step-12-notification-error.md`
