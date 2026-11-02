# STEP 03: ARCHITECTURAL MODELING

> **Acting as:** [Agent 2 — System Architect](../agents/agent_2_system_architect.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R4 (Traceability), R5 (Consistency), R10 (Inheritance Compliance).

## 1. Mục tiêu
Thiết kế mô hình chức năng (Functional Model) và các luồng tương tác kỹ thuật. Ưu tiên việc mô tả các cụm module nghiệp vụ thay vì chỉ tập trung vào hạ tầng.

## 2. Chỉ thị thực thi
1. **Mô hình chức năng tổng quan (Mục 4)**: BẮT BUỘC sử dụng **Mermaid graph TD** để vẽ sơ đồ khối chức năng.
   - Thể hiện đầy đủ Actors (trái), Hệ thống ngoại vi (phải) và Service Blocks (giữa).
   - BẮT BUỘC liệt kê bảng mô tả vai trò của từng thành phần trong sơ đồ sau khi vẽ.
2. **Phân rã chức năng (WBS) (Mục 5)**: Phân rã chức năng hành động và gán **ID WBS** chuẩn SSoT. Dùng động từ nghiệp vụ Tiếng Việt (vd: nhận yêu cầu → xử lý → trả kết quả) và phân rã tối thiểu 3 lớp.
3. **Quy trình tương tác & Logic (Mục 6)**:
   - Vẽ **Mermaid flowchart TD** (Swimlane - Mục 6.1) và **SequenceDiagram** (Mục 6.2). Độ chi tiết BẮT BUỘC tương xứng với WBS. Mỗi hành động prefix bằng WBS ID (vd: `[BE-MOD-01] Nhận request`).
   - Đặc tả logic Step-by-step rẽ nhánh IF-ELSE trong bảng Logic Matrix (Mục 6.3), tham chiếu WBS ID.
4. **Biểu đồ trạng thái (State Machine - Mục 7) — CONDITIONAL**: CHỈ vẽ khi module có **stateful entity** với vòng đời định nghĩa được từ source (ERD/Module 0/PRD). Mỗi state phải truy về một giá trị status bền vững của entity, **KHÔNG** map 1:1 từ WBS action. Module stateless → ghi `**Module stateless — không áp dụng State Machine.**` + lý do, không vẽ diagram. Source không có lifecycle → `[TBD]` + escalate Agent 0, cấm bịa chuỗi state (R3).
5. **Ghi vết**: Lưu nội dung vào file `part_2_modeling.md` trong thư mục `[Tên_Module].ts_parts/`.

## 3. Đầu ra yêu cầu
- Sơ đồ Khối chức năng, Sơ đồ Sequence và Bảng Logic.
- Nội dung chi tiết cho Mục 4, 5, 6, 7.
- Ghi dữ liệu vào `[Tên_Module].ts_parts/part_2_modeling.md`.

---

## [GATE — MODELING HANDOFF] ⛔

- BẮT BUỘC đã ghi `part_2_modeling.md` với đủ Mục 4, 5, 6 (6.1/6.2/6.3) và 7.
- **Mục 7 (R3):** stateful → StateDiagram truy về status entity từ source; stateless → khai báo `**Module stateless**`; source thiếu lifecycle → `[TBD]` + escalate Agent 0. CẤM bịa chuỗi state từ WBS action.
- Chỉ khi part_2 hoàn tất mới sang step kế.

**Next:** Read fully and follow `./step-04-implementation-contracts.md`