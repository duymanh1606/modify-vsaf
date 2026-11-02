# STEP 12: NOTIFICATION SYSTEM & ERROR RECOVERY → `ux_conventions.md` §C4-C5

> **Thực hiện bởi:** Agent UX0 (UX Lead — Sally) + Agent UX4 (Content Strategist — Paige)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — **R3, R5, R8.3** (notification ↔ error name consistency; severity color token canonical). Ghi TRỰC TIẾP vào `ux_conventions.md` (ngoại lệ R1).

## 0. Delta-mode check (chạy TRƯỚC)

Delta mode VÀ event set + error types của feature mới đã cover → SKIP. Feature thêm event/error type mới (vd entity mới có lifecycle mới) → append rows + CHANGE LOG.

## 1. Mục tiêu

§C4 Notification System (ma trận event×recipient×channel×title×detail — single source of truth) + §C5 Error Handling & Recovery (principles + classification + archetype edge cases). Project-wide.

## 2. Phân công

| Nội dung | Agent |
|:---|:---|
| §C4 Event Matrix + Notification Components | UX4 |
| §C5 Principles + Classification + Edge Cases | UX0 + UX4 |

## 3. Đầu vào cần đọc

- Journey spec §2 (archetype, composition, propagation) + §4 (mọi action cần notification)
- §C2 (writing rules, status labels) — notification/error copy tuân theo
- `component_catalog.md` — toast/banner/spinner/skeleton components; `master_token.json` — severity color token
- PRD — NFR notification SLA, FR auto-save, BR conflict policy

## 4. Chỉ thị thực thi

### 4.1. §C4 Event Notification Matrix — UX4

Bảng `| Event | Recipient | Channel | Timing | Title (≤8 words) | Detail |` — single source of truth (KHÔNG duplicate copy sang section khác). Channels: In-app / Email / Toast (kèm duration) / Banner (kèm dismiss policy) / Badge. Timing cite PRD NFR SLA. Event set theo archetype — CHỈ event tồn tại trong workflow:

| Archetype | Event tối thiểu |
|:---|:---|
| MAKER_CHECKER | submit / approve / partial-reject / full-reject / post-sync success / post-sync error / conflict |
| WIZARD | step-complete / abandon / finalize |
| DASHBOARD | alert / threshold-breach / data-stale |
| TRANSACTIONAL | success / failure |
| CONTENT_MGMT | draft-saved / published / publish-failure / collaborator-comment |

Detail: entity reference + actionable guidance + timestamp (nếu time-sensitive); severity color = token canonical.

### 4.2. §C4 Standard Notification Components — UX4

4 pattern `| Pattern | Component (catalog canonical) | Trigger | Dismiss |`: Loading (skeleton/spinner) / Success (toast + auto-dismiss N giây) / Error (banner + guidance + retry — KHÔNG chỉ mô tả lỗi) / Info (badge + dropdown). Component thiếu trong catalog → `[gap — propose Stage 4b]`.

### 4.3. §C5 Universal Error Principles — UX0 + UX4

≥6 principle: (1) never lose input — auto-save trước khi show error [FORM-HEAVY]; (2) cause + recovery guidance, không raw code; (3) luôn ≥1 action button; (4) localize failure scope [composition ≠ SINGLE]; (5) retry limit (max 2 auto rồi manual + suggest cause); (6) severe error kèm reference code + timestamp.

### 4.4. §C5 Error Classification & Visual Patterns

Bảng `| Error Type | User Sees | Severity | Recovery | Applicable Archetype |`. Universal 4: field validation / network disconnect (3 sub-state: initial, extended ≥5min, recovery) / session expiry (auto-save trước modal nếu FORM-HEAVY) / unexpected (catch-all + reference code). Conditional: save failure [FORM-HEAVY], section load failure [≠SINGLE], data refresh failure [DASHBOARD], post-decision sync failure [MAKER_CHECKER], edit conflict [COLLABORATIVE], publish conflict [CONTENT_MGMT]. Mỗi type: surface (inline/banner/modal theo severity) + region behavior + recovery CTA (structured — KHÔNG per-screen spec).

### 4.5. §C5 Archetype-Specific Edge Cases

Chỉ archetype đã chọn (§2.1): Partial Decision Sync Failure + Duplicate/Conflict Detection [MAKER_CHECKER]; Step Dependency Breakage + Auto-save & Session Recovery [WIZARD/FORM-HEAVY]; Stale Data Warning [DASHBOARD]; Simultaneous Edit Conflict [COLLABORATIVE]; Publish Conflict [CONTENT_MGMT]. OTHER → 2-3 edge case unique. KHÔNG mix archetype.

## 5. Đầu ra yêu cầu

- **Ghi trực tiếp:** `ux_conventions.md` §C4 + §C5 + CHANGE LOG rows.
- Báo cáo: "§C4-C5 {bootstrap | delta | no delta}. {N} events, {Z} error types, {W} edge cases."

**Next:** Read fully and follow `./step-13-responsive-accessibility.md`
