---
cases_count: 14
---

# Save Button Rule

## Mục đích

Sinh testcase cho button Lưu của form.

## Điều kiện kích hoạt

Khi màn hình/form có button Lưu, Tạo mới, Cập nhật, Hoàn tất hoặc Submit.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Kiểm tra hiển thị button.
2. Kiểm tra trạng thái mặc định.
3. Khi form chưa thay đổi dữ liệu.
4. Khi form thiếu dữ liệu bắt buộc.
5. Khi form có dữ liệu không hợp lệ.
6. Khi form có dữ liệu hợp lệ tối thiểu.
7. Khi form có dữ liệu hợp lệ đầy đủ.
8. Click liên tục nhiều lần.
9. Kiểm tra loading/disable trong lúc submit nếu có.
10. Kiểm tra thông báo thành công.
11. Kiểm tra thông báo thất bại từ API.
12. **Retry thủ công sau lỗi (khi spec cho phép re-submit):** submit lỗi 5xx → thông báo lỗi + form giữ nguyên → bấm lại submit lần nữa thành công (đối soát chỉ tạo 1 bản ghi ở lần thành công). Nếu spec nêu **giới hạn số lần retry** (vd "retry thủ công tối đa N lần") → thêm 1 dòng: sau N lần lỗi liên tiếp, lần N+1 bị chặn, đối soát đúng N request phát sinh. Spec không nêu → Q&A, không tự đoán.
13. Kiểm tra dữ liệu E2E sau khi lưu (BẮT BUỘC tuân thủ `e2e-traceability-rule.md`).
14. **Kiểm lưu đủ trường trong DB sau khi tạo mới:** từng trường của bản ghi vừa tạo đều có dữ liệu (khác NULL/rỗng), gồm cả bảng phụ thuộc. Trường mã hóa/hash chỉ kiểm có giá trị, không so nguyên văn (`e2e-traceability-rule.md` §1.1).

## Expected chuẩn

- Button hiển thị đúng thiết kế.
- Button enable/disable đúng trạng thái form.
- Khi thiếu dữ liệu: không lưu và hiển thị lỗi validate.
- Khi hợp lệ: lưu thành công và hiển thị message thành công.
- Sau khi tạo mới: mọi trường của bản ghi trong DB đều đã được lưu, không trường nào rỗng ngoài đặc tả.
- Không tạo duplicate request khi click nhiều lần.

## Điều kiện reject

- Không được chỉ có testcase click Lưu thành công.
- Phải có testcase lỗi validate trước testcase thành công.
- Phải kiểm tra trạng thái button mặc định.
