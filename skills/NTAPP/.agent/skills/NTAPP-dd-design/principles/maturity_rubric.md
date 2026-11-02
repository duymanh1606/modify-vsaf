# DDD MATURITY RUBRIC — Thước đo chấm điểm as-is (SSoT cho Agent D3)

> Rubric này là **nguồn sự thật duy nhất** cho cách chấm "cái gì tốt — giữ, cái gì sai — sửa".
> Agent D3 (Step 04) chấm **mỗi Bounded Context** theo 7 trục dưới đây. Step 05 (D4) đọc các ❌/⚠️ ở đây để sinh to-be + roadmap.

---

## Thang điểm mỗi trục

Mỗi trục chấm 1 trong 3 mức, kèm **evidence bắt buộc** (trích HLD/Module 0/code path/câu trả lời SA):

| Ký hiệu | Điểm | Nghĩa | Hệ quả |
|:--:|:--:|---|---|
| ✅ **KEEP** | 2 | Đạt chuẩn DDD — giữ nguyên | Không sinh remediation |
| ⚠️ **TIGHTEN** | 1 | Có hình hài đúng nhưng lỏng/chưa nhất quán | Sinh remediation **nhẹ** (lane-2 quick-dev) |
| ❌ **VIOLATION** | 0 | Vi phạm nguyên tắc DDD cốt lõi | Sinh remediation **nặng** (lane-3 slice / refactor có ADR) |

> ⚠️ Không có evidence → KHÔNG được chấm ✅. Mặc định khi mơ hồ là ⚠️ và ghi câu hỏi cho SA (R3).

---

## 7 trục đánh giá

### Trục 1 — Boundary Integrity (Toàn vẹn ranh giới)
*BC có cohesive, ít coupling, một chủ sở hữu (team) rõ ràng không?*
- ✅ BC đóng gói một subdomain mạch lạc; phụ thuộc ra ngoài đi qua contract tường minh; một team sở hữu.
- ⚠️ Ranh giới đúng nhưng rò rỉ vài chỗ (gọi thẳng nội bộ BC khác, chia sẻ vài type không qua contract).
- ❌ BC "bùn" — nhiều subdomain trộn lẫn, hoặc nhiều team cùng sửa lõi, hoặc phụ thuộc vòng giữa các BC.

### Trục 2 — Ubiquitous Language (Ngôn ngữ chung)
*Thuật ngữ nhất quán, một nghĩa/BC, khớp giữa doc và code không?*
- ✅ Glossary rõ; term khớp tên class/API/event trong code; alias bị loại (`_Avoid:`).
- ⚠️ Có glossary nhưng code dùng lẫn alias; vài term mơ hồ chưa chốt.
- ❌ Không có ngôn ngữ chung; cùng khái niệm gọi 3 tên khác nhau (vd User/Account/Customer lẫn lộn); code và business nói hai thứ tiếng.

### Trục 3 — Aggregate Design (Thiết kế aggregate)
*Aggregate nhỏ, root rõ, consistency boundary = transaction boundary không?*
- ✅ Mỗi aggregate có root rõ; invariant được bảo vệ trong boundary; transaction không vượt nhiều aggregate.
- ⚠️ Aggregate hơi to / nhiều entity; vài invariant kiểm ở tầng service thay vì trong aggregate.
- ❌ Không có khái niệm aggregate — entity thả nổi liên kết FK tuỳ ý; transaction ôm cả chục bảng; invariant rải khắp nơi.

### Trục 4 — Model Richness (Rich vs Anemic)
*Hành vi đi cùng dữ liệu, hay chỉ là transaction script trên data bag?*
- ✅ Domain object mang hành vi + bảo vệ invariant của chính nó; business rule sống trong domain layer.
- ⚠️ Một phần hành vi trong model, một phần rò ra service; có vài getter/setter trần.
- ❌ Anemic — entity chỉ là DTO getter/setter; toàn bộ rule nằm trong service/manager khổng lồ (transaction script).

### Trục 5 — Integration Hygiene (Vệ sinh tích hợp)
*Boundary có ACL, không chia sẻ DB mutable giữa các BC?*
- ✅ Mỗi BC sở hữu dữ liệu của mình; BC khác đọc qua API/event; có ACL dịch ngôn ngữ ở biên.
- ⚠️ Phần lớn qua contract nhưng còn vài shared read; ACL mỏng/không nhất quán.
- ❌ Nhiều BC ghi chung một DB/bảng; coupling qua schema dùng chung; đổi bảng vỡ nhiều BC.

### Trục 6 — Domain Events (Sự kiện miền)
*Sự kiện tường minh, đặt tên tốt, decoupled producer/consumer?*
- ✅ Domain event đặt tên theo nghiệp vụ (quá khứ: `OrderPlaced`); producer/consumer decoupled qua bus; có catalog.
- ⚠️ Có event nhưng đặt tên kỹ thuật (`OrderUpdated`); vài chỗ vẫn gọi đồng bộ lẽ ra nên event.
- ❌ Không có domain event; mọi tích hợp là RPC đồng bộ chuỗi; không truy được "chuyện gì đã xảy ra trong miền".

### Trục 7 — Layer/Persistence Separation (Tách tầng & hạ tầng)
*Domain layer độc lập với infra (DB/framework), dependency inverted?*
- ✅ Domain layer không import DB/framework; repository là interface ở domain, impl ở infra (ports & adapters).
- ⚠️ Phần lớn tách nhưng domain còn lệ thuộc vài annotation ORM / framework type.
- ❌ Domain trộn thẳng SQL/ORM/HTTP; không tách được logic nghiệp vụ khỏi hạ tầng để test.

---

## Tổng hợp mức trưởng thành mỗi BC (Composite Maturity Level)

Cộng điểm 7 trục (tối đa 14), quy về **level**:

| Tổng điểm | Level | Tên | Diễn giải |
|:--:|:--:|---|---|
| 0–2 | **L0** | Unaware | Không nhận thức DDD — CRUD/transaction script thuần |
| 3–6 | **L1** | Named | Có ranh giới mơ hồ + vài tên miền, nhưng model anemic |
| 7–9 | **L2** | Structured | Aggregate + event bắt đầu rõ; còn leak boundary/persistence |
| 10–12 | **L3** | Tactical | Tactical DDD vững; ngôn ngữ chung + ACL nhất quán |
| 13–14 | **L4** | Strategic | Strategic + tactical chín; boundary + event + ngôn ngữ đồng bộ |

> **Quy tắc chấm điểm an toàn:** Bất kỳ trục nào ❌ ở một **core subdomain** → trần level của BC đó tối đa **L2** (dù tổng điểm cao hơn), vì lõi nghiệp vụ không được phép vi phạm. Ghi rõ override này trong maturity.md.

---

## Đầu ra D3 phải sinh cho mỗi BC

1. Bảng 7 trục: mức (✅/⚠️/❌) + điểm + **evidence** + **finding** (1 câu mô tả).
2. Composite level + override note (nếu có).
3. Với mỗi ⚠️/❌: một **remediation seed** (mô tả ngắn "đổi gì" + lane gợi ý) — Step 05 (D4) sẽ nâng thành migration item có WBS/ADR.
