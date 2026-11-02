# No Hallucination Rule

## Mục đích

Chặn việc agent tự suy diễn field, button, message lỗi, API, trạng thái hoặc business rule không có trong tài liệu đầu vào.

## Nguyên tắc bắt buộc

Agent chỉ được sinh testcase dựa trên một trong các nguồn sau:

1. DD/PRD/SRS/KBNV được cung cấp.
2. KBKT cũ được cung cấp.
3. API spec/database spec/UI mockup được cung cấp.
4. Rule đã tồn tại trong repo `.agent/rules`.
5. Q&A đã được xác nhận.

## Khi thiếu thông tin

Nếu thiếu thông tin quan trọng, agent không được tự đoán.

Thay vào đó phải tạo Q&A với format:

| ID | Vùng thiếu thông tin | Câu hỏi cần làm rõ | Ảnh hưởng nếu không rõ | Người cần trả lời |
| --- | --- | --- | --- | --- |
| QA-001 | Message lỗi | Khi lưu thiếu Mã nhóm thuộc tính thì message chính xác là gì? | Không thể viết expected result chính xác | BA/PO/Dev |

## Ví dụ tình huống phải tạo Q&A

- File mẫu có expected `Báo lỗi: ???`.
- DD nói field bắt buộc nhưng không nêu message lỗi.
- DD nói maxlength nhưng không nêu giới hạn cụ thể.
- DD có button nhưng không mô tả onclick.
- Có conflict giữa UI mockup và API spec.
- Có rule cũ và rule mới mâu thuẫn.

## Điều kiện reject

Reject output nếu agent:

- Tự tạo message lỗi không có căn cứ.
- Tự thêm SQL/API/DB check khi tài liệu không có.
- Tự thêm field ngoài màn hình.
- Tự đổi trạng thái enable/disable khác với spec.
- Tự suy diễn flow thành công khi spec chưa mô tả.
