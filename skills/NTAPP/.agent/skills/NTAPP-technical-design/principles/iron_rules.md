# IRON RULES — Quy tắc bất biến của workflow NTAPP Technical Design (Layer 2)

> File này là **nguồn sự thật duy nhất** cho các nguyên tắc bất biến của toàn workflow.
> Mọi step file và persona PHẢI tham chiếu file này thay vì tự lặp lại nội dung.
> Khi cần emphasize 1 rule cụ thể trong step, **cite ID** (vd "theo R3") thay vì paraphrase nội dung.

---

## R1. VERBATIM INJECTION (Bơm dữ liệu nguyên văn)

Khi hợp nhất các file `part_*.md` trong `.ts_parts/` thành tài liệu TechSpec cuối cùng (Pass 2-4 của Step 05), **TUYỆT ĐỐI KHÔNG** thực hiện thao tác "Merge" truyền thống bằng cách đọc toàn bộ và viết lại bản tóm tắt.

**Tuân thủ:** Bơm dữ liệu thô từ các Part đơn lẻ vào các vị trí giữ chỗ trong Template `techspec_v3_ultimate_template.md` (placeholder injection).

**Vi phạm điển hình:** "Tóm tắt phần Modeling: module có 3 sequence diagram chính..." → SAI. Phải copy nguyên văn từng diagram + bảng.

---

## R2. ZERO-SUMMARIZATION (Cấm tóm tắt)

Mọi Bảng biểu, Mermaid Diagram (Sequence, Swimlane, State Machine, Class), Project Tree, Interface Contract từ file thô **PHẢI được giữ nguyên 100%** dung lượng và chi tiết khi đi vào TechSpec final.

**Vi phạm điển hình:** Cắt ngắn Sequence Diagram bỏ Loop/Alt; rút gọn bảng API Contract từ 6 cột thành 3 cột.

---

## R3. ZERO-FABRICATION / ZERO-HALLUCINATION (Cấm bịa)

Chỉ sử dụng thông tin từ các nguồn input đã được xác nhận:
- PRD/Epics đã user confirm.
- Architecture Design (L1) — `architecture_design.md` canonical.
- Module 0 Integration Map — `00_system_connectivity_integration.md` canonical.
- WBS SSoT — `project_wbs.md`.
- Tech Research thực tế (có nguồn URL) nếu Step 02 trigger.

Khi thiếu thông tin (vd: protocol cụ thể), PHẢI đánh dấu `[TBD]` — tuyệt đối không tự bịa.

**Zero Placeholder runtime:** TUYỆT ĐỐI KHÔNG để lại `[Data]`, `[VD: ...]`, `{placeholder}` trong output cuối cùng (trừ `[TBD]` có lý do rõ ràng).

---

## R4. TRACEABILITY (Chuỗi truy vết Layer 2)

Chuỗi truy vết bắt buộc xuyên TechSpec:

```
PRD/Epic ID → WBS ID (project_wbs.md) → L1 Container → Module 0 Contract ID
            → TechSpec Section 4-5 (Functional Model) → Section 6 (Sequence)
            → Section 8-10 (Project Tree, Data Model, Interface Contract)
```

- **Mọi WBS ID** thuộc module đang thiết kế phải xuất hiện trong **Coverage Matrix** (Step 01) và ít nhất một Sequence Diagram (Step 03).
- **Mọi Container Boundary** trong L1 cho module này phải có Sub-module tương ứng trong TechSpec Section 4.
- **Mọi external touchpoint** trong Module 0 (cho module này) phải có hàng API Contract tương ứng trong Section 10.
- **Mọi entity** trong Persistence (Section 9) phải có WBS ID hoặc Module 0 Contract ID làm origin.

---

## R5. CONSISTENCY (Đồng nhất xuyên L1 ↔ L2)

- Tên Container và Sub-module trong TechSpec PHẢI khớp 100% với tên đã chốt ở L1 Container Diagram.
- Tên Container ở Section 4 (Functional Model) phải khớp chính xác với tên Folder ở Section 8 (Project Tree).
- Schema entity trong Section 9 phải khớp 100% với ERD đã chốt trong L1 Module 0.
- Protocol/Topic/DB tên gọi phải đồng nhất giữa Module 0 và TechSpec Section 10.

---

## R6. QUALITY GATES (Trạm kiểm soát bắt buộc dừng)

Workflow có các quality gate **bắt buộc dừng** chờ pass trước khi đi tiếp:

| Gate | Sau step | Owner | Hành động khi FAIL |
|---|---|---|---|
| Coverage Gate | 01 | Agent 0 | Yêu cầu user bổ sung HLD/Module 0 hoặc rework WBS |
| Inheritance Compliance | 01 | Agent 0 | Trả lại L1 — không tự sửa boundary trong L2 |
| Pass 1-5 Quantitative Audit | 05 | Agent 0 | Bơm lại đoạn bị thiếu, không release TechSpec |

---

## R7. STOPPING ERRORS (Lỗi dừng khẩn cấp)

Dừng pipeline ngay và báo cáo nếu phát hiện:

1. WBS ID thuộc module nhưng không có hàng tương ứng trong **Coverage Matrix** (broken traceability).
2. Drift giữa L1 (HLD) và L2 (TechSpec): Container name/boundary/protocol khác nhau.
3. Module 0 đã xuất bản nhưng có ai đó cố sửa Schema/Protocol/Resilience trực tiếp trong L2 (vi phạm Contract Lock).
4. Sequence Diagram (Section 6.2) tham chiếu một external system **không có** trong Module 0.
5. Có 3+ Interface Contract ở trạng thái "Chưa xác định" mà không có quyết định Research/Clarify.

---

## R8. CONTRACT LOCK (Khoá hợp đồng tích hợp)

Module 0 canonical (`{planning_artifacts}/00_system_connectivity_integration.md`) là **read-only trong Layer 2**. Tuyệt đối:
- Không sửa Schema/Protocol/Resilience của Module 0 từ skill này.
- Mọi thay đổi Module 0 chỉ thực hiện ở Layer 1 (skill `/ntapp-architecture-design` Step 06) theo R8 logic của Layer 1: cascade từ HLD update HOẶC reconcile drift. Archive history lưu tại `{planning_artifacts}/archive/`.
- Nếu phát hiện Module 0 sai hoặc thiếu so với HLD → escalate qua R7 (Stopping Error #3), không tự fix trong Layer 2.

---

## R9. MISSING INPUT HANDLING (Xử lý input thiếu)

Nếu input file (PRD, Epics, `architecture_design.md`, `project_wbs.md`, `00_system_connectivity_integration.md`, `part_*.md`) **không tồn tại** hoặc **không readable**:

- DỪNG ngay, **KHÔNG generate placeholder content** (`[Data]`, `<TBD>`, mock value, "module Auth có 3 service tự bịa...") thay thế.
- Báo user explicit: "File `X` tại path `Y` không tìm thấy. Vui lòng cung cấp đường dẫn hoặc xác nhận file."
- Chỉ tiếp tục sau khi user confirm file tồn tại + readable.

**Vi phạm điển hình:** Agent đọc HLD không có rồi tự suy ra "module này có Container A, B, C..." → SAI. Phải hỏi user trước.

**Liên quan:** R9 bổ sung cho R3:
- R3 cấm bịa khi **đã có** context (chỉ extract từ context).
- R9 cấm bịa khi **thiếu** context (phải hỏi user thay vì tự fill).

---

## R10. INHERITANCE COMPLIANCE (Tuân thủ kế thừa Layer 1)

Layer 2 PHẢI kế thừa từ Layer 1 + Module 0 — không tự ý đổi ranh giới đã chốt:

- **Frozen External Interface:** Tuyệt đối không sửa boundary/protocol/schema đã khoá trong Module 0.
- **L1-L2 Integrity:** Container name, ranh giới module phải khớp 100% với HLD đã chốt ở Layer 1.
- **Internal Decomposition Only:** Agent 2 toàn quyền phân rã các bước xử lý nội bộ (sub-module, sequence, state machine), nhưng các điểm giao tiếp ngoại vi (external touchpoint) phải khớp tuyệt đối Module 0.

**Vi phạm điển hình:**
- Agent 3 đặt tên Container `AuthService` trong L2 khác `AuthSvc` trong L1 → SAI (vi phạm R5 + R10).
- Agent 2 vẽ sequence diagram có protocol `HTTP/2` trong khi Module 0 ghi `gRPC` → SAI (vi phạm R8 + R10).

**Khi cần đổi:** escalate qua R7 (Stopping Error #2 hoặc #3) → quay lại Layer 1 update HLD/Module 0 trước, không tự fix trong L2.
