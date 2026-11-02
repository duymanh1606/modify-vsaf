# STEP 05: QA & TEST PROTOCOL

> **Acting as:** [Agent F4 — QA Specialist](../agents/agent_f4_qa_specialist.md)
> **Tuân thủ:** [Iron Rules](../principles/iron_rules.md) — đặc biệt R4 (Traceability Logic→KBKT), R6 (Logic↔KBKT Coverage Gate).

## 1. Mục tiêu
Xây dựng lớp bảo mật chất lượng cho tính năng thông qua bộ KBKT chi tiết tại Section 5.

## 2. Nguyên liệu đầu vào (Input)
- **UI Blueprint (`f3_ui_part.md`)**: Để kiểm tra độ bao phủ giao diện.
- **Logic Matrix (`f1_logic_part.md`)**: Để kiểm tra độ bao phủ các nhánh rẽ BE.
- **Data Samples (`f2_data_part.md`)**: Để lấy dữ liệu mẫu chính xác cho cột "Data Test".

## 3. Chỉ thị thực thi
1. **Impact Analysis (5.1)**: Khoanh vùng các rủi ro hệ thống.
2. **Kịch bản KBKT (5.2)**:
   - Lập bảng theo đúng schema cột ở template §5.2, bao phủ 100% logic và giao diện.
   - Trích xuất Exact Sample Data cho từng case (Kế thừa từ F2).
   - Ánh xạ rõ kết quả kỳ vọng (UI changed, DB state sau ghi — §4.3).
   - ⛔ KHÔNG đặc tả setup môi trường/công cụ, quy trình review/defect.

## 3. Đầu ra yêu cầu
- Section 5 hoàn chỉnh.
- **Lưu trữ:** Bản thảo Markdown lưu tại `{intermediate_folder}/f4_qa_part.md`.
- Đảm bảo tính khả thi để thực thi test ngay lập tức.

## [GATE] — Coverage completion (⛔ kiểm trước khi sang Next)

- Step 05 **luôn RUN** — `f4_qa_part.md` PHẢI đã ghi (Section 5 hoàn chỉnh).
- Bảng KBKT (theo schema template §5.2) bao phủ 100% logic (nếu có f1) và giao diện (nếu có f3); Exact Sample Data kế thừa từ F2 (nếu có f2). Nếu coverage chưa đủ → bổ sung trước khi sang Next (R4, R6).

**Next:** Read fully and follow `./step-06-sync-audit.md`
