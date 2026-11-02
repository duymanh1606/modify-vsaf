# IRON RULES — Quy tắc bất biến của workflow NTAPP DD-Design (DDD Reproduction)

> File này là **nguồn sự thật duy nhất** cho các nguyên tắc bất biến của toàn workflow.
> Mọi step file và persona PHẢI tham chiếu file này thay vì tự lặp lại nội dung.

---

## R1. VERBATIM INJECTION (Bơm dữ liệu nguyên văn)

Khi hợp nhất các file `part_*.md` thành bộ artifact cuối (`CONTEXT-MAP.md`, `maturity.md`, ...), **TUYỆT ĐỐI KHÔNG** "Merge" bằng cách đọc toàn bộ rồi viết lại bản tóm tắt. Bơm dữ liệu thô (context map, bảng aggregate, glossary, Mermaid diagram) vào đúng placeholder của template.

**Vi phạm điển hình:** "Tóm tắt: hệ thống có 3 bounded context chính..." → SAI. Phải copy nguyên văn bảng + diagram.

---

## R2. ZERO-SUMMARIZATION (Cấm tóm tắt)

Mọi bảng (context map, aggregate, invariant, domain event), glossary ubiquitous language, Mermaid diagram (context map, aggregate boundary, event flow) **PHẢI giữ nguyên 100%** dung lượng và chi tiết khi vào artifact canonical.

---

## R3. ZERO-FABRICATION / ZERO-HALLUCINATION (Cấm bịa)

- Chỉ mô hình hoá từ **evidence đã xác nhận**: HLD, Module 0, system-overview baseline, PRD/Epics, `CONTEXT.md` intent-level, hoặc câu trả lời trực tiếp của SA/Domain Expert trong interview.
- TUYỆT ĐỐI KHÔNG bịa bounded context, aggregate, invariant, hay domain event mà evidence/SA chưa xác nhận. Thiếu → đánh `[TBD — SA verify]`, KHÔNG tự fill.
- **Zero Placeholder runtime:** KHÔNG để `[Data]`, `{placeholder}` trong output cuối (trừ `[TBD]` có lý do rõ ràng).
- Interview-driven nghĩa là **SA là oracle của ngữ nghĩa miền** — khi code/doc nói một đằng và SA nói một nẻo, ghi nhận mâu thuẫn (R5), KHÔNG tự quyết.

---

## R4. TRACEABILITY (Xương sống truy vết DDD)

Chuỗi truy vết bắt buộc:

```
PRD/Epic ID → Bounded Context → Aggregate (root) → WBS unit (project_wbs.md) / Module 0 contract → code header (id: + bc: + agg:)
```

- **Mọi module/service** trong WBS phải thuộc **ít nhất một** Bounded Context (no orphan module).
- **Mọi Aggregate** phải map tới ≥1 WBS unit (backend feature) — aggregate không có code tương ứng phải đánh dấu `[TARGET-ONLY]` (chỉ thuộc to-be, không phải as-is).
- **Mọi Domain Event** phải có ≥1 **producer** BC và ≥1 **consumer** BC (hoặc đánh dấu `[orphan-event]` như một finding maturity, không im lặng).
- **Mọi term** trong ubiquitous language phải xuất hiện ít nhất một lần trong AGGREGATES hoặc EVENTS của BC đó.

---

## R5. CONSISTENCY (Đồng nhất xuyên tài liệu)

- Tên Bounded Context PHẢI khớp 100% giữa `CONTEXT-MAP.md`, per-BC `CONTEXT.md`, `AGGREGATES.md`, `EVENTS.md`, và `maturity.md`.
- Một **term** chỉ mang **một nghĩa trong một BC**. Nếu cùng từ mang nghĩa khác ở BC khác → đó là tín hiệu ranh giới (ghi rõ ở context map, KHÔNG ép về một nghĩa).
- Aggregate name + Domain Event name dùng đúng **ubiquitous language** đã chốt, không dùng alias trong `_Avoid:`.
- Mâu thuẫn giữa nguồn (HLD vs code vs SA) → **flag cho user reconcile**, KHÔNG tự chọn.

---

## R6. HANDSHAKE & GATE (Trạm kiểm soát)

| Gate | Sau step | Owner | Hành động khi FAIL |
|---|---|---|---|
| **G1** Boundary Coverage | 02 | D0 | Trả về D1 — còn module chưa thuộc BC nào |
| **G2** Tactical Completeness | 03 | D0 | Trả về D2 — aggregate thiếu root/invariant, event thiếu producer/consumer |
| **G3** Scored & Evidenced | 04 | D0 | Trả về D3 — BC chưa chấm đủ 7 trục, hoặc ❌ thiếu evidence/remediation |
| **G4** Lane-mapped | 05 | D0 | Trả về D4 — remediation chưa map lane, hoặc roadmap có cycle |
| **G5** Quantitative Audit | 06 | D0 + HITL | Bơm lại phần thiếu; chờ SA sign-off |

---

## R7. STOPPING ERRORS (Lỗi dừng khẩn cấp)

Dừng pipeline ngay và báo cáo nếu phát hiện:

1. Một module/service trong WBS không map về bất kỳ Bounded Context nào (orphan).
2. Một Bounded Context không chứa Aggregate nào (BC rỗng — sai phân rã hoặc thiếu interview).
3. Một Aggregate không xác định được **root** (vi phạm tactical DDD cốt lõi).
4. Hai BC cùng **ghi** (mutable) chung một thực thể/bảng mà không có Anti-Corruption Layer — phải nâng thành finding ❌, KHÔNG im lặng.
5. Domain model mâu thuẫn Module 0 contract đã lock (vi phạm R8) mà không escalate.
6. As-is artifact bị "làm đẹp" để giấu khuyết tật (vi phạm R10).

---

## R8. MODEL ALIGNMENT (Đồng bộ với kiến trúc đã lock)

Domain model là **downstream** của HLD + Module 0 đã lock, KHÔNG phải nguồn cạnh tranh. Bộ artifact `domain/` phải **nhất quán** với Module 0 contract + WBS.

**Cho phép domain model định nghĩa thêm KHI VÀ CHỈ KHI** không mâu thuẫn contract đã lock:
- **OK:** đặt tên BC, phân loại subdomain, mô hình aggregate/invariant nội bộ BC, catalog domain event — những thứ Module 0 không nói tới.
- **ESCALATE (không tự quyết):** đề xuất tách/gộp BC làm đổi service boundary, đổi integration pattern, hay đổi contract → đó là **to-be**, ghi vào `TARGET.md` + ADR, và muốn hiện thực hoá phải chạy `/ntapp-architecture-design`. As-is model KHÔNG được vẽ ranh giới mâu thuẫn Module 0 hiện tại.

**Vi phạm điển hình:** as-is CONTEXT-MAP vẽ 2 BC riêng trong khi Module 0 cho thấy chúng dùng chung 1 contract/DB → SAI. As-is phải phản ánh thực tại (1 BC bị trộn, là một finding ❌); đề xuất tách đặt ở TARGET.

---

## R9. MISSING INPUT HANDLING (Xử lý input thiếu)

Nếu input (HLD, Module 0, WBS, system-overview, PRD/Epics, hay `part_*.md`) **không tồn tại** hoặc **không readable**:

- DỪNG ngay, **KHÔNG generate placeholder content** thay thế.
- Báo user explicit path file thiếu, đề xuất skill tạo nó (vd HLD chưa có → `/ntapp-architecture-design` trước).
- Chỉ tiếp tục sau khi user confirm. R9 bổ sung R3: R3 cấm bịa khi **đã có** context; R9 cấm bịa khi **thiếu** context.

---

## R10. AS-IS ≠ TO-BE (Tách bạch thực tại và tương lai)

Đây là rule định danh của skill reproduction:

- **As-is artifacts** (`CONTEXT-MAP.md`, per-BC `CONTEXT.md` + `AGGREGATES.md`, `EVENTS.md`, `maturity.md`) mô tả hệ thống **NHƯ NÓ ĐANG LÀ** — kể cả anemic model, leaky boundary, shared DB, transaction script. KHÔNG sửa cho đẹp.
- **To-be artifacts** (`TARGET.md`, `MIGRATION.md`, ADR) mô tả hệ thống **NÊN TRỞ THÀNH** + đường đi tới đó.
- Mọi đề xuất "nên đổi" thuộc về to-be, KHÔNG được lén đưa vào as-is. Maturity assessment là **cầu nối**: nó chấm as-is và trỏ tới to-be, nhưng bản thân vẫn mô tả thực tại.

**Vì sao:** Giá trị của skill này = phơi bày gap giữa thực tại và DDD chuẩn. "Làm đẹp" as-is = phá huỷ chính lý do tồn tại của nó.
