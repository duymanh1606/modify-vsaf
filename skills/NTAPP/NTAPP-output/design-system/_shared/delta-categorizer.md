# Delta Categorizer

**Schema version:** 1.0
**Type:** Routing logic for proposal items
**Used by:**
- `/ntapp-ds-build-component` (sub-agent: `delta-router`) — route mỗi item của proposal sang đúng path
- `/ntapp-ui-generation` Stage 4b Agent 1 — pre-categorize khi generate proposal

---

## 1. Mục đích

Cho mỗi item trong proposal (parsed theo `proposal-schema.md`), xác định **category** + **build path** tương ứng.

**5 category:**
- **NEW_COMPONENT** → `component-scaffolder` build code mới
- **NEW_TOKEN** → `token-applier` patch master_token.json
- **MODIFIED_COMPONENT** → `component-patcher` modify existing
- **MODIFIED_TOKEN** → `token-applier` update value (UPDATE_TOKEN_VALUE)
- **WARNING** → `warning-blocker` block, đợi DSO resolve

## 2. Decision tree

```
For each item in proposal:
  IF item.section == "[NEW]":
      LOOKUP item.Name in target catalog:
        IF item.TYPE == "COMPONENT":
            target = components_metadata.json
        IF item.TYPE == "TOKEN":
            target = master_token.json (path-based)

      IF item.Name EXISTS in target:
          → MODIFIED_COMPONENT or MODIFIED_TOKEN (auto-promote, log conflict)
            Reason: proposal nói "NEW" nhưng đã có → treat như UPDATE.
            Warn DSO: "Item {name} đã tồn tại. Auto-promote sang MODIFIED."

      ELSE:
          RUN pattern-matcher vs catalog:
            IF top score ≥ 0.95:
                → MODIFIED_COMPONENT (alias detected, link to top match)
            ELSE IF top score 0.70-0.94:
                → WARNING (FUNCTIONAL_DUPLICATE, override-able)
            ELSE IF top score 0.50-0.69:
                → WARNING (VARIANT_OF_EXISTING, override-able)
            ELSE:
                → NEW_COMPONENT or NEW_TOKEN

  ELSE IF item.section == "[MODIFIED]":
      LOOKUP item.Name:
        IF NOT EXISTS:
            → ERROR: reject proposal (DSO clarify, có thể intent là NEW)
        IF EXISTS:
            IF item.Change_type in ["ADD_STATE", "ADD_VARIANT", "ADD_PROP"]:
                → MODIFIED_COMPONENT
            IF item.Change_type == "UPDATE_TOKEN_VALUE":
                → MODIFIED_TOKEN
            IF item.Change_type == "DEPRECATE":
                → MODIFIED_COMPONENT (set status: deprecated)
                  hoặc MODIFIED_TOKEN (set deprecation marker)

  ELSE IF item.section == "[WARNINGS]":
      LOOKUP item.Resolution_status:
        IF "PENDING":
            → WARNING (block workflow)
        IF "RESOLVED":
            → SKIP (DSO đã quyết dùng existing, không build)
        IF "OVERRIDDEN":
            → continue route from corresponding [NEW] item (DSO accept duplicate)
```

## 3. Cascade detection

### 3.1 NEW TOKEN reference token chưa tồn tại

Khi route NEW_TOKEN:

```
Parse Value field:
  IF Value is reference (matches /^\{[^}]+\}$/):
      Resolve path
      LOOKUP target in master_token.json:
        IF NOT EXISTS:
            → ERROR: reject proposal
              Message: "Token {Name} reference {target} chưa tồn tại.
                        DSO phải thêm {target} vào [NEW] section trước
                        (manual cascade — không auto)."
```

(Theo decision lock: cascade = manual, không auto.)

### 3.2 MODIFIED COMPONENT reference token mới

Khi component-patcher add prop/state có dùng token mới:

```
Parse component patch:
  Extract token references mới
  FOR each new ref:
    LOOKUP in master_token.json:
      IF NOT EXISTS:
          IF proposal có entry NEW_TOKEN khớp:
              → DEPENDENCY (build NEW_TOKEN trước, sau đó build MODIFIED_COMPONENT)
          ELSE:
              → ERROR: reject. DSO thêm NEW_TOKEN vào proposal.
```

## 4. Tier violation detection

Khi route NEW_TOKEN:

```
Parse Tier field:
  IF Tier == "global":
      Value KHÔNG được là reference (global là primitive)
      IF Value matches /^\{.+\}$/ → ERROR

  IF Tier == "semantic":
      Value PHẢI là reference vào global (ưu tiên)
      Raw value cho phép nhưng warn (best-practices.md rule 4.6)

  IF Tier == "component":
      Value PHẢI là reference vào semantic (ưu tiên) hoặc global
      Raw value warn

  IF Value is reference:
      Verify direction: component → semantic → global (chỉ đi xuống)
      IF reference đi ngược (vd: semantic ref component) → ERROR
```

## 5. Order of operations — within 1 build run

Build skill apply theo thứ tự để tránh dangling reference:

```
1. NEW_TOKEN (global tier first, semantic, then component)
2. MODIFIED_TOKEN (UPDATE_TOKEN_VALUE)
3. NEW_COMPONENT (catalog updated, can reference new tokens)
4. MODIFIED_COMPONENT
5. DEPRECATE marks (cuối cùng)
```

Trong cùng tier, sort theo dependency (token với value `{...}` chạy sau token nó reference).

## 6. Output structure cho `delta-router`

`delta-router` output `01_delta_routed.json` (lưu trong `build_parts/{id}/`):

```json
{
  "$schema_version": "1.0",
  "proposal_id": "ING_05_PROG_01",
  "routed_items": [
    {
      "name": "progress-bar",
      "category": "NEW_COMPONENT",
      "build_path": "component-scaffolder",
      "source_section": "[NEW]",
      "dependencies": ["semantic.color.action.tertiary"],
      "metadata": { /* full item from proposal */ }
    },
    {
      "name": "semantic.color.action.tertiary",
      "category": "NEW_TOKEN",
      "build_path": "token-applier",
      "source_section": "[NEW]",
      "dependencies": [],
      "metadata": { /* full item */ }
    },
    {
      "name": "Toast vs NotificationBanner",
      "category": "WARNING",
      "build_path": "warning-blocker",
      "source_section": "[WARNINGS]",
      "resolution_status": "PENDING",
      "blocks": ["progress-bar"]
    }
  ],
  "execution_order": [
    "semantic.color.action.tertiary",
    "progress-bar"
  ],
  "blocked": true,
  "blocking_warnings": ["Toast vs NotificationBanner"]
}
```

`blocked: true` → build skill exit ≠ 0, không proceed.

## 7. Conflict resolution rules

### 7.1 NEW item đã tồn tại (auto-promote to MODIFIED)
- Log warning vào `build_report`.
- Treat như MODIFIED với change_type = inferred từ field khác biệt.
- Không reject.

### 7.2 MODIFIED component không tồn tại
- Reject. DSO clarify (có thể intent là NEW).
- Build skill exit ≠ 0.

### 7.3 NEW component có pattern-match score 0.7-0.94 (FUNCTIONAL_DUPLICATE)
- Output WARNING (treat như `[WARNINGS]` section item với type FUNCTIONAL_DUPLICATE, status PENDING).
- DSO phải resolve trước khi build.

### 7.4 Token name xung đột (NEW + MODIFIED cùng name)
- Reject. Không cho phép vừa NEW vừa MODIFIED 1 token trong 1 proposal.

## 8. Edge cases

| Case | Xử lý |
|---|---|
| Proposal trống (mọi section empty) | Output `routed_items: []`, `blocked: false`. Build skill exit 0, no-op. |
| Item trong [NEW] không khai TYPE | Reject (proposal-schema rule). |
| Component metadata corrupt (không parse được) | Reject với error rõ. DSO chạy lại bootstrap. |
| 2 NEW item có cùng `Name` | Reject (proposal-schema rule, nhưng router cũng check defensively). |
| MODIFIED_COMPONENT có `Breaking change: YES` | Pass to `component-patcher` với flag `--require-co-approve` — DSO co-approve riêng. |

---

**End of delta-categorizer v1.0.**
