---
cases_count: 11
---
# Filter Save Validation Rule

## Mục đích

Sinh testcase validate khi lưu cấu hình filter rule.

## Điều kiện kích hoạt

Kích hoạt khi khối filter có button Lưu và các field bắt buộc trong cụm filter.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Lưu khi chưa chọn cả 3 trường: Thuộc tính cha, Giá trị cha, Giá trị con cho phép.
2. Lưu khi chỉ chọn Thuộc tính cha.
3. Lưu khi chỉ chọn Giá trị cha.
4. Lưu khi chỉ chọn Giá trị con cho phép.
5. Lưu khi chọn Thuộc tính cha + Giá trị cha nhưng chưa chọn Giá trị con cho phép.
6. Lưu khi chọn Thuộc tính cha + Giá trị con cho phép nhưng chưa chọn Giá trị cha.
7. Lưu khi chọn Giá trị cha + Giá trị con cho phép nhưng chưa chọn Thuộc tính cha.
8. Lưu khi có nhiều cụm, trong đó một cụm thiếu dữ liệu.
9. Lưu khi tất cả cụm hợp lệ.
10. Lưu khi có quan hệ trùng lặp.
11. Lưu khi child value trùng giữa nhiều rule nếu business không cho phép.

## Expected chuẩn

- Case thiếu dữ liệu phải hiển thị lỗi cụ thể tại field/cụm thiếu.
- Case hợp lệ phải lưu thành công và hiển thị thông báo thành công.
- Nếu message lỗi chưa có trong tài liệu thì không tự đoán, phải tạo Q&A.

## Q&A bắt buộc nếu gặp `???`

Nếu KBKT cũ hoặc tài liệu ghi `Báo lỗi: ???`, agent phải sinh Q&A thay vì tự điền message:

```markdown
| ID | Vùng thiếu thông tin | Câu hỏi cần làm rõ | Ảnh hưởng |
| --- | --- | --- | --- |
| QA-FILTER-001 | Filter Rules / Button Lưu | Khi nhấn Lưu mà chưa chọn Thuộc tính cha/Giá trị cha/Giá trị con cho phép thì message lỗi chính xác là gì? | Không thể viết expected result chính xác cho testcase validate |
```

## Điều kiện reject

Reject testcase validate nếu expected vẫn còn `???`.
