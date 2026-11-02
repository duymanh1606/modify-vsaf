# STEP 02: STRATEGY & GLOBAL RULES

> **Acting as:** [Agent 1 — Business Strategist](../agents/agent_1_business_strategist.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R2 (Zero-Summarization), R3 (Zero-Fabrication).

## 1. Mục tiêu
Thiết lập bối cảnh nghiệp vụ và mô hình hóa quy trình nghiệp vụ tổng thể (Business Process Flow) giúp stakeholder hình dung được cách hệ thống phục vụ con người.

## 2. Chỉ thị thực thi
1. **Phân tích bối cảnh & Actor**: Liệt kê đầy đủ Actor và ranh giới quyền hạn.
2. **Quy trình nghiệp vụ & Hành trình người dùng (Mục 6.1)**: 
   - BẮT BUỘC sử dụng **Mermaid `flowchart TD`** để vẽ sơ đồ quy trình.
   - Sử dụng `subgraph` để giả lập các Swimlanes tượng trưng cho các Actor tham gia vào quy trình. Đính kèm ID WBS cho mỗi node.
   - Thể hiện rõ hành trình của người dùng từ khi bắt đầu đến khi kết thúc một chu trình nghiệp vụ.
3. **Xác lập Global Invariants (Mục 3.4)**: Đúc kết các quy tắc bất biến (Hiến pháp) áp dụng cho toàn bộ Module/Service.
4. **Ghi vết**: Lưu nội dung vào file `part_1_strategy.md` trong thư mục `[Tên_Module].ts_parts/`.

## 3. Đầu ra yêu cầu
- Nội dung chi tiết cho Mục 1, 2, 3 và **Mục 6.1 (Sơ đồ Swimlane)**.
- Ghi dữ liệu vào `[Tên_Module].ts_parts/part_1_strategy.md`.

---

## [GATE — STRATEGY HANDOFF] ⛔

- BẮT BUỘC đã ghi `part_1_strategy.md` với đủ Mục 1, 2, 3 và **Mục 6.1** (Mermaid `flowchart TD` Swimlane, mỗi node gắn ID WBS).
- Chỉ khi part_1 hoàn tất mới sang step kế.

**Next:** Read fully and follow `./step-03-architectural-modeling.md`
