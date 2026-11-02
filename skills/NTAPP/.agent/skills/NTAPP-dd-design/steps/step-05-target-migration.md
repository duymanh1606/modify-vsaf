# STEP 05: TARGET-STATE & MIGRATION (TO-BE BLUEPRINT + ROADMAP)

> **Acting as:** [Agent D4 — Target-State & Migration Architect](../agents/agent_d4_target_migration.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — R8 (Model Alignment), R10 (As-is ≠ To-be), R4 (lane-mapped).

**Input:** `maturity.md` (remediation seeds) + `CONTEXT-MAP.md`.
**Output:** `TARGET.md` + `MIGRATION.md` + `adr/NNNN-*.md`.
**Template:** [target_template.md](../templates/target_template.md), [migration_template.md](../templates/migration_template.md).

> 🧭 **R10 — đây là ranh giới to-be.** Mọi thứ ở Step 05 ghi vào `TARGET.md`/`MIGRATION.md`/ADR. TUYỆT ĐỐI không sửa artifact as-is (CONTEXT-MAP, AGGREGATES, EVENTS, maturity).

---

## 5.1 Thiết kế To-Be Blueprint (`TARGET.md`)

Từ các ⚠️/❌, thiết kế trạng thái đích per BC — mỗi mục **trỏ ngược về finding** (BC + trục):

| Khía cạnh to-be | Mô tả đích | Sửa finding |
| :--- | :--- | :--- |
| Ranh giới BC | Tách `Inventory` khỏi `Ordering` thành BC riêng | T1, T5 |
| Aggregate | `Order` chỉ giữ line item; `Shipment` thành aggregate riêng | T3 |
| Model | Đưa rule định giá vào `Order` (rich) | T4 |
| Integration | Thay shared-DB read bằng `InventoryChecked` event + ACL | T5, T6 |
| Layering | Tách repository thành interface ở domain (ports & adapters) | T7 |

> **R8 — gắn nhãn đụng-kiến-trúc:** Mục nào làm **đổi service boundary / contract Module 0** → đánh dấu `[needs /ntapp-architecture-design]`. To-be được phép đề xuất, nhưng hiện thực hoá phải qua architecture-design + cascade Module 0. KHÔNG coi như đã xong.

## 5.2 Lập Migration Roadmap (`MIGRATION.md`)

Mỗi remediation seed → một **migration item** có cấu trúc:

| Field | Nội dung |
| :--- | :--- |
| `id` | MIG-NN |
| `target` | trỏ mục to-be + finding (BC·trục) |
| `lane` | `express` / `quick-dev` / `slice` / `ad-hoc` / `refactor-ADR` |
| `blocked_by` | MIG khác (DAG, no cycle) |
| `effort` | S/M/L |
| `risk` | thấp/trung/cao (core + đụng contract = cao) |
| `dod` | definition of done (1 câu kiểm chứng được) |

**Phân pha:** nhóm item thành P1/P2/... theo phụ thuộc + ưu tiên:
- **P1**: core subdomain ở level thấp (L0–L1) + nền tảng (tách shared DB, dựng ACL) — gỡ coupling trước.
- **P2+**: làm rich model, refactor aggregate, chuyển sang event.
- `generic` subdomain ở level thấp → cân nhắc **mua/thay** thay vì refactor (ghi rõ).

## 5.3 Ghi ADR cho quyết định strategic

Với mỗi quyết định khó đảo ngược + có trade-off (tách/gộp BC, đổi integration pattern, đổi ownership, mua-vs-build generic), ghi `adr/NNNN-slug.md` (format [grill-with-docs ADR](../../grill-with-docs/ADR-FORMAT.md) nếu có, hoặc tối giản: context + decision + why). Đánh số kế tiếp bằng cách scan `adr/`.

## 5.4 Đối chiếu ưu tiên với SA (qua D0)

Trình roadmap cho SA xác nhận thứ tự ưu tiên + lane. Đặc biệt: mục `[needs /ntapp-architecture-design]` cần SA đồng ý đây là thay đổi kiến trúc thật.

## 5.5 Ghi part + bơm artifacts

Ghi `part_05_target.md`; bơm vào `TARGET.md` + `MIGRATION.md`; ghi ADR. Dual-write archive.

---

## ⛔ [GATE — G4: LANE-MAPPED] (D0 self-check)

- [ ] **Mỗi** remediation seed (từ maturity) có một migration item tương ứng.
- [ ] **Mỗi** migration item có `lane` hợp lệ + `dod` kiểm chứng được.
- [ ] Roadmap DAG: `blocked_by` trỏ MIG thật, **không cycle**.
- [ ] Mục đụng contract/boundary đánh dấu `[needs /ntapp-architecture-design]` (R8).
- [ ] To-be tách bạch hoàn toàn khỏi as-is (R10) — không artifact as-is nào bị sửa.

FAIL → ở lại Step 05. PASS → Next.

**Next:** Read fully and follow `./step-06-assembly.md`
