# STEP 04: IMPLEMENTATION, DATA & CONTRACTS

> **Acting as:** [Agent 3 — Implementation Lead](../agents/agent_3_implementation_lead.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R5 (Consistency), R8 (Contract Lock), R10 (Inheritance Compliance).

## 1. Mục tiêu
Ánh xạ kiến trúc logic xuống mã nguồn thực tế, thiết kế mô hình dữ liệu (Persistence) và xác lập các hợp đồng giao tiếp (Interface) bất biến theo chuẩn High-Fidelity.

## 2. Chỉ thị thực thi
1. **Traceability (Mục 8)**: Lập bảng ánh xạ Requirement -> Folder -> WBS ID.
2. **Directory Structure (Mục 9)**: BẮT BUỘC sử dụng **ASCII Art (ASCII Tree)** để vẽ cây thư mục.
3. **Boundaries (Mục 10)**: Đặc tả ranh giới API, Service và Data bằng sơ đồ Mermaid.
4. **Logical Data Model (Mục 11)**: Thiết kế cấu trúc lưu trữ nội tại.
    - BẮT BUỘC sử dụng Mermaid Diagram.
    - Phải tách biệt rõ vùng **Hot Data** và **Cold Data**.
    - Đặc tả Data Dictionary kèm theo Storage Class.
5. **Interface Contracts (Mục 12)**: Định nghĩa mã Proto hoặc JSON Schema.
    - BẮT BUỘC đối soát và tuân thủ tuyệt đối **Giao thức kết nối** và **Master Data Schema** từ tệp **Module 0 canonical** (`{planning_artifacts}/00_system_connectivity_integration.md`).
    - Liệt kê đầy đủ 100% fields mẫu (không dùng placeholder).
    - Phải có bảng Error Mapping và mẫu Payload JSON thực tế.
6. **Ghi vết**: Lưu nội dung vào file `part_3_implementation.md` trong thư mục `[Tên_Module].ts_parts/`.

## 3. Tiêu chí nghiệm thu (Acceptance Criteria)
- [ ] Bản đồ tích hợp (Module 0) đã được nạp làm bối cảnh (Context) chính.
- [ ] 100% các bảng dữ liệu trong ERD (Mục 11) được phân loại Hot/Cold Data.
- [ ] Bảng Data Dictionary mục 11 và Schema mục 12 khớp 100% với Module 0.
- [ ] 100% schema fields được định nghĩa kiểu dữ liệu và mô tả.
- [ ] Có bảng Error mapping sang gRPC Status/HTTP Code.
- [ ] Có tối thiểu 1 mẫu Payload thành công (Success Case).
- [ ] Không chứa bất kỳ placeholder dạng `// TODO` hoặc `[...]` nào.

## 4. Đầu ra yêu cầu
- Cấu trúc thư mục (ASCII Art Tree).
- Ranh giới kiến trúc (Mermaid).
- Nội dung chi tiết cho Mục 8, 9, 10, 11, 12 (High-Fidelity).
- Dữ liệu thô lưu tại `[Tên_Module].ts_parts/part_3_implementation.md`.

---

## [GATE — IMPLEMENTATION HANDOFF] ⛔

- BẮT BUỘC đã ghi `part_3_implementation.md` với đủ Mục 8, 9, 10, 11, 12 (High-Fidelity).
- Toàn bộ **Tiêu chí nghiệm thu (§3)** đã check: Module 0 loaded, 100% bảng ERD phân loại Hot/Cold, Data Dictionary + Schema khớp 100% Module 0, error mapping đầy đủ, ≥ 1 success payload, KHÔNG còn placeholder `// TODO` / `[...]`.
- Chỉ khi part_3 hoàn tất + AC pass mới sang step kế.

**Next:** Read fully and follow `./step-05-orchestration-qa.md`
