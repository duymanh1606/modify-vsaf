# STEP 06: ASSEMBLY — QUANTITATIVE AUDIT + HITL SIGN-OFF (TERMINAL)

> **Acting as:** [Agent D0 — Domain Orchestrator](../agents/agent_d0_orchestrator.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R1 (Verbatim), R2 (Zero-summarization), R5 (Consistency), R10.

**Input:** mọi `part_*.md` + artifact canonical đã bơm ở Step 02–05.
**Output:** bộ `domain/` hoàn chỉnh (canonical + archive) + sign-off.

---

## 6.1 Verify bộ artifact đã đủ (Verbatim — R1/R2)

D0 KHÔNG viết lại/tóm tắt. Chỉ verify các file canonical đã được bơm nguyên văn:

| File | Có? | Nội dung tối thiểu |
| :--- | :-: | :--- |
| `CONTEXT-MAP.md` | ✓/✗ | BC inventory + map + integration pattern + open conflicts |
| `contexts/<bc>/CONTEXT.md` | ✓/✗ | ubiquitous language mỗi BC in-scope |
| `contexts/<bc>/AGGREGATES.md` | ✓/✗ | aggregate + root + invariant mỗi BC |
| `EVENTS.md` | ✓/✗ | domain event catalog (producer→consumer) |
| `maturity.md` | ✓/✗ | 7-trục mỗi BC + level + cross-cutting + seeds |
| `TARGET.md` | ✓/✗ | to-be blueprint trỏ finding |
| `MIGRATION.md` | ✓/✗ | roadmap lane-mapped + DAG |
| `adr/` | ✓/✗ | ADR cho quyết định strategic (nếu có) |

Thiếu file → quay về step owner tương ứng bơm lại. KHÔNG tự sinh nội dung thay (R3).

## 6.2 Quantitative Audit (G5)

Đếm + kiểm chéo nhất quán (R5):
- **Coverage:** #module trong WBS == #module được map vào BC (no orphan, R4).
- **Traceability:** mỗi `core` BC có ≥1 entry maturity + ≥1 migration item nếu level < L3.
- **Consistency:** tên BC khớp 100% across CONTEXT-MAP / per-BC / maturity / TARGET (R5). Term không dùng alias `_Avoid:`.
- **Event integrity:** mỗi event trong AGGREGATES xuất hiện trong EVENTS catalog; orphan đánh dấu.
- **As-is purity (R10):** maturity/CONTEXT-MAP/AGGREGATES KHÔNG chứa câu "nên/đề xuất/sẽ đổi" (to-be rò rỉ). Có → tách về TARGET.
- **Alignment (R8):** không quan hệ Context Map nào mâu thuẫn Module 0 mà chưa được ghi là finding/target.

FAIL bất kỳ mục → fix (bơm lại phần thiếu), re-audit. KHÔNG sign-off khi còn FAIL.

## 6.3 Index + header

Tạo/cập nhật `{domain_artifacts}/README.md` (index trỏ mọi artifact + version + ngày) để business mở vào đọc đầu tiên. Mỗi file canonical có header trạng thái (AS-IS / TO-BE) + version + `approved_by: [TBD]`.

## 6.4 HITL Sign-off (Pause & Wait)

Trình SA bản tóm tắt: #BC, phân bố level, top findings ❌, P1 roadmap. Yêu cầu ký:

```markdown
## ✅ DOMAIN MODEL READY — chờ SA sign-off

- {N} bounded context · core trung bình L{x}
- Top violations: {liệt kê 3-5 ❌ nặng nhất}
- P1 roadmap: {liệt kê}

SA xác nhận → tôi ghi `approved_by: <tên>` + `date` vào CONTEXT-MAP.md + maturity.md.
Đây là SSoT domain sống — cập nhật qua `--refresh <bc>` mỗi khi slice chạm BC.
```

Sau khi SA ký → ghi `approved_by:` vào front-matter CONTEXT-MAP.md + maturity.md. Bump archive version cuối.

## 6.5 Downstream notice (nhắc — KHÔNG tự chạy)

- **Mirror:** nếu dùng multi-repo, re-mirror `domain/` artifact + skill sang code repo / spec repo liên quan.
- **Remediation:** mở work theo `MIGRATION.md` qua lane đã map (`/ntapp-feature-triage` đọc maturity để route).
- **Living:** đăng ký `--refresh <bc>` vào Definition-of-Done của `slice-loop`.

---

## ĐIỀU KIỆN HOÀN TẤT (Exit Criteria — TERMINAL)

- [ ] Mọi artifact canonical đủ + bơm nguyên văn (6.1) + Quantitative Audit G5 PASS (6.2).
- [ ] `README.md` index + header trạng thái có (6.3).
- [ ] SA đã ký `approved_by:` (6.4).
- [ ] Archive version bump cuối.

> ⛔ Đây là step TERMINAL — KHÔNG có pointer `**Next:**`. Workflow kết thúc sau sign-off. Cập nhật về sau dùng REFRESH mode.
