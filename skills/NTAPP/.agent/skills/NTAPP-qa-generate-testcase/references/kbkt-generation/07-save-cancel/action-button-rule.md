---
cases_count: 9
---

# Action / Navigation Button Rule

## Mục đích

Sinh testcase cho **MỌI button/nút bấm hiển thị trong chức năng** kích hoạt điều hướng hoặc một hành vi nghiệp vụ — mà **không** thuộc nhóm Lưu/Submit (dùng `save-button-rule.md`) hay Hủy/Đóng/Back (dùng `cancel-button-rule.md`).

Ví dụ: "Xem chi tiết", "Tiếp tục", "Bước tiếp theo", "Duyệt", "Từ chối", "Xuất file/Tải xuống", "Thêm mới" (mở màn/dialog), CTA điều hướng, nút chuyển tab, nút áp dụng bộ lọc, icon-action trên hàng lưới (kết hợp `09-data-grid/grid-base-rule.md`).

## Điều kiện kích hoạt

Áp dụng **cho từng button riêng lẻ** xuất hiện trong màn hình/dialog/khu vực đang test mà ở trạng thái **enable** có thể click được. Không có ngoại lệ: mỗi button enable = một cụm testcase độc lập theo danh sách dưới đây.

> [!IMPORTANT]
> **Quy tắc vét cạn button:** Trong Step 02, sau khi ánh xạ nhãn giao diện, phải **liệt kê đầy đủ mọi button** của bề mặt đang test và gắn mỗi button với rule tương ứng (Lưu → `save-button-rule`; Hủy → `cancel-button-rule`; còn lại → rule này). Cấm bỏ sót bất kỳ button enable nào.
>
> **Bao gồm button trong STATE điều kiện (BẮT BUỘC):** button chỉ hiện trong state lỗi/degraded/timeout/empty/loading/dialog — điển hình **[Thử lại]/Retry**, CTA empty-state (**[Tạo mới]**, **[Tinh chỉnh bộ lọc]**), nút trong confirm-dialog — thường **không có trong bảng UI-Controls** (DD mô tả chúng như hành vi của banner/state cha). Vẫn phải enroll vào danh sách button và chạy đủ cụm dưới đây. KHÔNG được coi là "hiển thị của state" rồi chỉ assert render qua `screen-default-display-rule`.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng, và **lặp cho TỪNG button** enable. Không được gộp chung nhiều button vào một dòng, không viết "tương tự".

1. Kiểm tra hiển thị button (nhãn/icon/vị trí đúng thiết kế).
2. Kiểm tra điều kiện enable/disable theo nghiệp vụ (khi nào enable, khi nào disable, mặc định là gì).
3. **Click khi button ENABLE → điều hướng/xử lý đúng nghiệp vụ:** xác minh đích đến (màn hình/dialog mở đúng, API đúng được gọi, trạng thái/dữ liệu thay đổi đúng) theo spec.
4. Click khi ở trạng thái DISABLE (nếu button vẫn hiển thị dạng mờ) → không phát sinh hành động nào.
5. **Click nhiều lần liên tiếp (double-click / spam click):** chỉ xử lý MỘT lần — không tạo request trùng, không mở chồng dialog, không điều hướng lặp/nhân bản bản ghi (idempotency + chống double-submit).
6. Click khi thiếu điều kiện tiên quyết nghiệp vụ (nếu có) → chặn và thông báo phù hợp, không điều hướng.
7. Kiểm tra trạng thái loading/disable trong lúc xử lý bất đồng bộ (nếu button gọi hành động async).
8. Kiểm tra hành vi khi hành động/API lỗi (nếu button gọi Backend) → hiển thị thông báo lỗi, giữ nguyên màn/trạng thái, không điều hướng nhầm.
9. Kiểm tra dữ liệu E2E / trạng thái sau khi hành động thành công (nếu button tạo tác động nghiệp vụ — tuân thủ `e2e-traceability-rule.md`).

## Cụm bổ sung cho nút Retry ("Thử lại") — BẮT BUỘC khi có

Nút retry trên banner lỗi/degraded/timeout hoặc toast phải có tối thiểu 3 dòng độc lập (ngoài các mục 1-9 ở trên):

10. **Click retry → hành động lặp lại THÀNH CÔNG:** banner/thông báo lỗi biến mất, dữ liệu/panel render đúng; đối soát API được gọi lại.
11. **Click retry mà VẪN lỗi lần nữa:** banner/thông báo lỗi **giữ nguyên** (không biến mất), trạng thái an toàn được duy trì (panel giữ trạng thái lỗi/rỗng, control chính vẫn dùng được), nút retry vẫn bấm được lần tiếp theo.
12. **Giới hạn số lần retry (nếu spec nêu):** vd "retry thủ công tối đa N lần" → sau N lần lỗi liên tiếp, lần thứ N+1 bị chặn không cho retry; đối soát đúng N request phát sinh, không có request thứ N+1. Nếu spec KHÔNG nêu giới hạn → Q&A, không tự đoán.

## Expected chuẩn

- Button hiển thị và enable/disable đúng điều kiện nghiệp vụ trong spec.
- Khi click enable: điều hướng đến đúng đích hoặc thực thi đúng hành vi nghiệp vụ mô tả trong spec (đích đến phải ghi cụ thể, cấm ghi "điều hướng đúng"/"theo thiết kế").
- Click nhiều lần: hệ thống chỉ xử lý một lần, không nhân bản request/bản ghi, không mở chồng nhiều màn/dialog.
- Khi lỗi: giữ nguyên trạng thái an toàn và thông báo rõ ràng.

## Điều kiện cần Q&A

Tạo Q&A (không tự đoán) nếu spec không nói rõ:

- Đích điều hướng cụ thể sau khi click là màn/dialog nào?
- Hành vi nghiệp vụ khi click là gì (gọi API nào, đổi trạng thái ra sao)?
- Hành vi khi click nhiều lần liên tiếp (có khóa nút/idempotency không)?
- Điều kiện enable/disable của button.

## Điều kiện reject

- Thiếu testcase click → điều hướng/xử lý cho **bất kỳ button enable nào** hiển thị trong chức năng (kể cả button lồng trong state lỗi/degraded/empty/dialog).
- Bỏ sót button chỉ xuất hiện trong state điều kiện (retry, CTA empty-state, nút trong dialog) khỏi danh sách vét cạn.
- Có nút retry nhưng thiếu dòng "retry vẫn lỗi lần nữa" (mục 11) hoặc thiếu dòng giới hạn retry khi spec có nêu (mục 12).
- Thiếu testcase click nhiều lần liên tiếp cho button gây tác động nghiệp vụ.
- Cột Kết quả mong muốn ghi mơ hồ ("điều hướng đúng", "xử lý theo thiết kế") thay vì đích đến/hành vi cụ thể.
