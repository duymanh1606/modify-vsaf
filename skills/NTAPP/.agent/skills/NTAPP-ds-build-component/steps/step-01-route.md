# Step 1: Delta Routing

## GOAL
Parse `proposed_ds_updates.md`, validate schema, drift check vs current state, idempotency check, build in-memory routing object phân loại 4 paths: `tokens_to_apply`, `components_to_scaffold`, `components_to_patch`, `warnings_pending`.

## 1. Load Persona

Adopt role của **Delta Router** sub-agent tại `../agents/delta-router.md`. Persona declare: role + responsibilities + decision policies + output spec (routing object JSON shape). Procedural pipeline ở step file này.

## 2. Inputs

- Proposal file path (DSO cung cấp tại INITIALIZATION; default lookup `{design_system_root}/feature_deltas/{id}/proposed_ds_updates.md`).
- `master_token.json` + `components_metadata.json` (current state cho idempotency + drift).
- `_shared/proposal-schema.md` (canonical schema).
- `_shared/delta-categorizer.md` (category logic).

## 3. Apply Order Definition

Output `apply_order` array là contract cho Step 3-4 consume. Thứ tự cố định:

1. **`tokens.global`** — global tier tokens NEW + MODIFIED.
2. **`tokens.semantic`** — semantic tier (chỉ ref được tier ≤).
3. **`tokens.component`** — component tier.
4. **`components.new`** — alphabetical theo `name` (deterministic).
5. **`components.modified`** — alphabetical.

Constraint: NEW token mới mà MODIFIED component depend → token-applier (Step 3) chạy xong rồi component-patcher (Step 4) mới chạy. Sub-agent KHÔNG xử lý cross-dependency phức tạp; circular → STOP.

## 4. Pipeline

### Stage 4.1: Parse markdown

Theo `_shared/proposal-schema.md` mục 3 (3 sections):

```
[NEW]
  - Tokens: list of NEW_TOKEN entries
  - Components: list of NEW_COMPONENT entries

[MODIFIED]
  - Tokens: list of MODIFIED_TOKEN entries
  - Components: list of MODIFIED_COMPONENT entries

[WARNINGS]
  - List of WARNING entries với status (PENDING / RESOLVED / ACK)
```

Parse-tolerant: section thiếu = empty list. Format tổng thể sai (section header sai, fence không close) → STOP với line number.

### Stage 4.2: Per-item schema validate

Theo `_shared/proposal-schema.md` field requirements. Tóm tắt:

| Entry type | Required fields |
|---|---|
| NEW_TOKEN | `path`, (`value` HOẶC `reference`), `tier` (phải khớp path prefix) |
| NEW_COMPONENT | `name` (kebab-case), `category`, `semantic_intent`, `inputs`, `outputs`, `tokens_used`, `library_wrap` (`<lib-name>` HOẶC explicit `null` — DECISION REQUIRED, KHÔNG default) |
| MODIFIED_TOKEN | `path`, `before`, `after`, `breaking` |
| MODIFIED_COMPONENT | `name`, `change_type`, `details`, `breaking` |
| WARNING | `id`, `message`, `status` (PENDING/RESOLVED/ACK), `resolved_by` (chỉ nếu RESOLVED) |

Field thiếu → STOP với message cụ thể: `"NEW_COMPONENT 'alert-banner' missing required field 'library_wrap'"`.

### Stage 4.3: Drift + idempotency cross-check

Đối chiếu với current state theo Universal Rule U5 (drift = STOP):

| Item | Check | Action |
|---|---|---|
| NEW_TOKEN path đã tồn tại trong `master_token` | Compare value | match → skip log (idempotent); mismatch → STOP (drift) |
| MODIFIED_TOKEN.before ≠ `master_token` current | Drift | STOP với drift detail (before/expected vs current) |
| NEW_COMPONENT name đã tồn tại trong `components_metadata` | Compare metadata | match → skip; mismatch → STOP |
| MODIFIED_COMPONENT.name không tồn tại | Drift | STOP "component đã bị xoá hoặc rename" |
| WARNING.status = PENDING | Block flag | route vào `warnings_pending`, Step 2 xử lý |

**Idempotent skip toàn bộ** (proposal đã apply trước, mọi item match) → log `"no-op"`, return early KHÔNG chạy Step 2-5.

### Stage 4.4: Build routing object

Apply Stage 4.1-4.3 outputs → routing object shape ở `agents/delta-router.md` §4. Bao gồm:

- 4 path arrays (`tokens_to_apply`, `components_to_scaffold`, `components_to_patch`, `warnings_pending`).
- `idempotent_skips` (informational cho build_report).
- `apply_order` (theo §3 trên).
- `proposal_checksum` — sha256 của `proposed_ds_updates.md` raw bytes (cho Step 5 pre-commit hook integration).
- `proposal_source` (`bmad-stage-4b` nếu folder match `feature_deltas/`, `manual` nếu DSO viết tay nơi khác).

### Stage 4.5: Cross-dependency check

Scan routing object cho circular dependencies:

- Token A reference B AND B reference A (across tier hoặc same tier) → STOP "circular token dependency".
- MODIFIED_COMPONENT.tokens_used ref NEW_TOKEN trong cùng proposal → OK (apply_order đảm bảo Step 3 chạy trước Step 4).
- Duplicate path trong cùng section (2 NEW_TOKEN cùng path) → STOP.

## 5. Output

- In-memory routing object (pass cho Step 2-5).
- `{design_system_root}/feature_deltas/{id}/_routing.json` (chỉ khi DSO yêu cầu inspect routing trước khi apply — agent prompt HITL "ghi routing JSON để inspect không?").

## DECISION POINTS

- Toàn bộ items idempotent → log "no-op", return early không chạy step sau.
- NEW_COMPONENT thiếu `library_wrap` (cả `null` cũng không có) → STOP "decision required".
- Duplicate path trong proposal → STOP với detail.
- Circular dependency (token A ref B ref A) → STOP với detail.
- Drift bất kỳ → STOP (Universal Rule U5, không auto-correct).

> **[GATE]** Mọi STOP ở **DECISION POINTS** trên phải clear trước khi tiếp. Toàn bộ items idempotent → log "no-op", return early — KHÔNG đọc step kế.

**Next:** Read fully and follow `./step-02-warning-gate.md`
