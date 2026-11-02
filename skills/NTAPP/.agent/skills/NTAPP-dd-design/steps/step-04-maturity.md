# STEP 04: MATURITY — CHẤM 7 TRỤC (CÁI GÌ TỐT / CÁI GÌ SAI)

> **Acting as:** [Agent D3 — Maturity Assessor](../agents/agent_d3_maturity_assessor.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R3 (evidence-or-not-green), R7 (stopping errors), R10 (As-is ≠ To-be). **Rubric SSoT:** [maturity_rubric.md](../principles/maturity_rubric.md).

**Input:** `CONTEXT-MAP.md` + per-BC `AGGREGATES.md` + `EVENTS.md`.
**Output:** `{intermediate_folder}/part_04_maturity.md` → `maturity.md`.
**Template:** [maturity_template.md](../templates/maturity_template.md).

---

## 4.1 Chấm 7 trục mỗi BC

Với mỗi BC, chấm đủ 7 trục theo [rubric](../principles/maturity_rubric.md) — mỗi trục một mức ✅(2)/⚠️(1)/❌(0) + **evidence bắt buộc** (trích HLD/Module 0/code path/câu SA) + finding 1 câu:

| # | Trục | Hỏi gì |
| :-: | :--- | :--- |
| T1 | Boundary Integrity | BC cohesive, ít coupling, một chủ sở hữu? |
| T2 | Ubiquitous Language | Term nhất quán, một nghĩa/BC, khớp code? |
| T3 | Aggregate Design | Aggregate nhỏ, root rõ, consistency = transaction? |
| T4 | Model Richness | Hành vi trong domain hay transaction script? |
| T5 | Integration Hygiene | ACL ở biên, không shared mutable DB? |
| T6 | Domain Events | Event tường minh, đặt tên nghiệp vụ, decoupled? |
| T7 | Layer/Persistence | Domain độc lập infra, dependency inverted? |

> **R3:** Không evidence → KHÔNG ✅. Mơ hồ → ⚠️ + câu hỏi SA (qua D0). KHÔNG đoán mức cao.

## 4.2 Composite level + safety override

Cộng điểm 7 trục → level L0–L4 (bảng "Composite" trong rubric). Áp **safety rule**: BC là `core` mà có **bất kỳ** trục ❌ → trần level = **L2** (dù tổng điểm cao hơn). Ghi rõ override trong maturity.md.

## 4.3 Cross-cutting findings

Quét vấn đề không thuộc riêng BC nào (thường là R7 stopping errors):
- Shared mutable DB: ≥2 BC cùng **ghi** một bảng không qua ACL → ❌ Critical.
- Orphan event: event không producer/consumer.
- Vòng phụ thuộc BC (A→B→A).
- Aggregate không xác định được root (đã chặn ở G2, nhưng re-confirm).

## 4.4 Remediation seed (con trỏ tới to-be — KHÔNG tự sửa)

Với mỗi ⚠️/❌, sinh một seed: `{BC} · {trục} · "đổi gì" (1 câu) · lane gợi ý`:
- ❌ trên `core` subdomain → ưu tiên cao, thường `slice` hoặc `refactor-ADR`.
- ⚠️ giữ-contract → `quick-dev`.
- Lỗi config/typo ngôn ngữ nhỏ → `express`.

> **R10:** Seed chỉ là **con trỏ**. KHÔNG sửa AGGREGATES/CONTEXT-MAP cho đẹp. Việc thiết kế to-be là của Step 05 (D4).

## 4.5 Ghi part + bơm maturity.md

Ghi `part_04_maturity.md`; bơm vào `maturity.md` (roll-up table + chi tiết per-BC + cross-cutting + seeds). Dual-write archive.

---

## ⛔ [GATE — G3: SCORED & EVIDENCED] (D0 self-check)

- [ ] **Mọi** BC in-scope chấm đủ **7 trục**; mỗi mức có **evidence** (không evidence → không ✅).
- [ ] Composite level tính đúng + safety override (core có ❌ → ≤L2) đã áp + ghi chú.
- [ ] **Mỗi** ⚠️/❌ có một remediation seed (BC · trục · đổi gì · lane).
- [ ] Cross-cutting findings đã quét (shared DB, orphan event, vòng phụ thuộc).

FAIL → ở lại Step 04. PASS → Next.

**Next:** Read fully and follow `./step-05-target-migration.md`
