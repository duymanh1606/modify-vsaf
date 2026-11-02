# IRON RULES — Quy tắc bất biến của workflow NTAPP Architecture Design

> File này là **nguồn sự thật duy nhất** cho các nguyên tắc bất biến của toàn workflow.
> Mọi step file và persona PHẢI tham chiếu file này thay vì tự lặp lại nội dung.

---

## R1. VERBATIM INJECTION (Bơm dữ liệu nguyên văn)

Khi hợp nhất các file `part_*.md` thành tài liệu HLD cuối cùng, **TUYỆT ĐỐI KHÔNG** thực hiện thao tác "Merge" truyền thống bằng cách đọc toàn bộ và viết lại bản tóm tắt. Hành động này gây mất mát dữ liệu Mermaid Diagram và bảng đặc tả.

**Tuân thủ:** Bơm dữ liệu thô từ các Part đơn lẻ vào các vị trí giữ chỗ trong Template (placeholder injection).

**Vi phạm điển hình:** "Tóm tắt phần 4.1: hệ thống có 3 container chính..." → SAI. Phải copy nguyên văn diagram + bảng.

---

## R2. ZERO-SUMMARIZATION (Cấm tóm tắt)

Mọi Bảng biểu, Mermaid Diagram (C4, Sequence, ERD, Class), Project Tree, danh sách tính năng từ file thô **PHẢI được giữ nguyên 100%** dung lượng và chi tiết khi đi vào HLD final.

**Vi phạm điển hình:** Cắt ngắn Sequence Diagram bỏ Loop/Alt; rút gọn bảng Container từ 8 cột thành 3 cột.

---

## R3. ZERO-FABRICATION / ZERO-HALLUCINATION (Cấm bịa)

- Chỉ sử dụng thông tin từ PRD/Epics, Context Summary đã được user xác nhận, hoặc kết quả Research thực tế (có nguồn URL).
- Khi lập Ma trận kết nối, chỉ trích xuất từ sơ đồ C4 và Sequence của Agent C. Nếu thiếu thông tin (vd: Protocol), PHẢI đánh dấu `[TBD]` — tuyệt đối không tự bịa.
- **Zero Placeholder runtime**: TUYỆT ĐỐI KHÔNG để lại `[Data]`, `[VD: ...]`, `{placeholder}` trong output cuối cùng (trừ `[TBD]` có lý do rõ ràng).

---

## R4. TRACEABILITY (Xương sống truy vết)

Chuỗi truy vết bắt buộc xuyên suốt workflow:

```
PRD/Epic ID → WBS ID (project_wbs.md) → C4 Container/Module → Sequence/Data Flow → Project Tree path → Module 0 connectivity row
```

- **Mọi WBS ID** (vd: `[BE-MOD-01]`) phải xuất hiện ít nhất một lần trong sơ đồ Sequence hoặc Data Flow tại đúng phân hệ của nó.
- **Mọi Epic** trong PRD phải có ít nhất 1 WBS ID tương ứng.
- **Mọi Container** trong L2 phải có hàng tương ứng trong bảng đặc tả Container.
- **Mọi thực thể** trong ERD phải có quan hệ (no orphan) và được lưu ở đúng Container.

---

## R5. CONSISTENCY (Đồng nhất xuyên tài liệu)

- Tên Container và Node trong Sub-module PHẢI khớp 100% với Container Diagram đã chốt ở Pha Global.
- Tên Container ở Section 3 (Architecture) phải khớp chính xác với tên Folder ở Section 4 (Implementation).
- ERD trong HLD chính (3.1.3) phải khớp 100% với ERD trong Module 0 (00_system_connectivity_integration).

---

## R6. HANDSHAKE & GATE (Trạm kiểm soát)

Workflow có các quality gate **bắt buộc dừng** chờ pass trước khi đi tiếp:

| Gate | Sau step | Owner | Hành động khi FAIL |
|---|---|---|---|
| NFR Completeness | 02 | Agent E | Kích hoạt Step 03 hoặc clarify với user |
| WBS Coverage Audit | 04.1 | Agent E | Trả về Agent C cập nhật `project_wbs.md` |
| L1/L2 Consistency | 04.1 | Agent C self-check | Tự sửa trước khi vào 04.2 |
| Quantitative Audit | 07 | Agent E | Bơm lại đoạn bị thiếu |

---

## R7. STOPPING ERRORS (Lỗi dừng khẩn cấp)

Dừng pipeline ngay và báo cáo nếu phát hiện:

1. Module trong WBS không có tiểu mục phân rã chi tiết.
2. Sơ đồ Level 1 (Context) và Level 2 (Container) không đồng nhất về Actors/Systems.
3. WBS ID xuất hiện ở bảng tính năng nhưng mất dấu trong Module 0 (broken traceability).
4. Có 3+ NFR ở trạng thái "Chưa xác định" mà không có quyết định Research/Clarify.
5. Module 0 đã xuất bản nhưng có ai đó cố sửa Ma trận kết nối hoặc Sequence Diagram gốc (Contract Lock vi phạm).

---

## R8. CONTRACT LOCK (Khoá hợp đồng tích hợp)

Module 0 (`{planning_artifacts}/00_system_connectivity_integration.md` canonical + archive history `_v{N}`) bị khoá theo logic:

**Cho phép write Module 0 KHI VÀ CHỈ KHI:**
- **Case 1 — Cascade từ HLD:** HLD vừa được update (Step 07 ghi canonical mới), Module 0 BẮT BUỘC re-run Step 06 để sync theo HLD.
- **Case 2 — Reconcile drift:** Module 0 hiện tại không khớp HLD canonical (lệch protocol/schema/connectivity) → cho phép update để đồng nhất với HLD.

**REJECT mọi edit độc lập khác:**
- HLD không đổi + Module 0 đã khớp HLD → **không có lý do** để bump version. User muốn đổi Schema/Protocol → phải update HLD trước, Module 0 sẽ cascade theo.

**Vi phạm điển hình:** User trực tiếp edit Module 0 canonical để thêm 1 protocol → SAI. Phải update HLD Section 3 (Container Spec) trước, Module 0 cascade ở Step 07.

**Versioning:** Mỗi lần write Module 0 → archive `_v{N+1}`. Canonical luôn = latest. Archive lưu history để track change.

---

## R9. MISSING INPUT HANDLING (Xử lý input thiếu)

Nếu input file (PRD, Epics, Project Brief, `project_wbs.md`, `part_*.md`, hoặc bất kỳ file dependency nào) **không tồn tại** hoặc **không readable**:

- DỪNG ngay, **KHÔNG generate placeholder content** (`[Data]`, `<TBD>`, mock value, "hệ thống có 3 module ABC..." tự bịa) thay thế.
- Báo user explicit: "File `X` tại path `Y` không tìm thấy. Vui lòng cung cấp đường dẫn hoặc xác nhận file."
- Chỉ tiếp tục sau khi user confirm file tồn tại + readable.

**Vi phạm điển hình:** Agent đọc PRD không có rồi tự suy ra "hệ thống có module Auth, Payment, Notification..." → SAI. Phải hỏi user trước.

**Liên quan:** R9 bổ sung cho R3 (Zero-Fabrication):
- R3 cấm bịa khi **đã có** context (chỉ extract từ context).
- R9 cấm bịa khi **thiếu** context (phải hỏi user thay vì tự fill).
