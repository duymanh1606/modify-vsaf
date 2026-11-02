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

## Truy vết giá trị ràng buộc (Value Provenance)

Mọi literal ràng buộc (min/max length, page-size, enum, mã lỗi, ngưỡng số) trong testcase phải là bản sao **verbatim** của một giá trị có thật trong nguồn, kèm trích dẫn vị trí (part + mục). Cấm:

- Suy/nhân bản giá trị từ control hoặc field khác (vd lấy maxlength của field A gán cho field B).
- Tự làm tròn/ước lượng khi nguồn không nêu.

Nguồn không nêu giá trị → `[TBD]` + Q&A, KHÔNG tự điền.

### Wireframe KHÔNG phải nguồn chuỗi hiển thị

Khối vẽ ASCII/mockup trong DD chỉ mô tả **bố cục**. Cấm chép chuỗi từ trong khung vẽ ra làm expected "verbatim":

- Emoji/icon trong wireframe là **gợi ý thị giác** → dịch sang `icon_bindings` ở `ui_schema`, KHÔNG phải ký tự của nhãn (vd `📨 Tạo Yêu cầu mới` → expected là `Tạo Yêu cầu mới` + icon riêng).
- Ký tự khung (`│ ─ + [ ]`), dấu căn lề, chữ rút gọn cho vừa khung đều không tính là nội dung.

Nguồn hợp lệ của chuỗi hiển thị, theo thứ tự: mô tả text của DD (bảng control/§ nội dung) → contract/i18n key → UX Spec. Chỉ có wireframe mà không có mô tả text → `[TBD]` + Q&A.

## Điều kiện reject

Reject output nếu agent:

- Tự đặt hoặc nhân bản giá trị ràng buộc (maxlength/page-size/enum/mã lỗi) từ nguồn khác thay vì trích đúng.
- Tự tạo message lỗi không có căn cứ.
- Tự thêm SQL/API/DB check khi tài liệu không có.
- Tự thêm field ngoài màn hình.
- Tự đổi trạng thái enable/disable khác với spec.
- Tự suy diễn flow thành công khi spec chưa mô tả.
