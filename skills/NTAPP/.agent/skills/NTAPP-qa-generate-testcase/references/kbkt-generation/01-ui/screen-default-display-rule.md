---
cases_count: 7
---

# Screen Default Display Rule

## Mục đích

Sinh testcase kiểm tra trạng thái hiển thị của màn/khối ở mọi STATE: mặc định (mở lần đầu), rỗng/không-kết-quả, lỗi, loading.

## Điều kiện kích hoạt

Kích hoạt rule này khi DD/PRD/UI mockup có màn hình hoặc form mới.

## Độ đầy đủ theo STATE (SSoT — dùng chung cho mọi rule có state hiển thị)

Với mỗi STATE hiển thị (mặc định / rỗng / không-kết-quả / lỗi / loading), Expected phải liệt kê ĐỦ mọi thành phần wireframe của state đó, mỗi thành phần 1 dòng:

- Message / illustration / icon.
- MỌI nút & CTA của state (kể cả CTA điều hướng phụ, vd "Tạo mới").
- Control hiển thị + trạng thái enable/disable.

Cấm assert 1 phần (vd chỉ message của empty state) rồi coi là đủ. **Cấm ghi "Empty state" trơ:** khi màn có ≥2 biến thể rỗng (no-data vs filter-no-result), mỗi case phải nêu rõ biến thể + message nguyên văn + CTA của biến thể đó (vd Empty 1 "chưa có dữ liệu" + CTA tạo ≠ Empty 4 "không tìm thấy phù hợp bộ lọc" + recap filter + [Xóa lọc]/[Tinh chỉnh]).

**Neo role khi hiển thị đổi theo role:** nếu DD nói role X ẩn/hiện cột/field khác nhau → case mặc định phải nêu rõ role (vd `token full-access`), KHÔNG viết "màn hiện N cột" trần. Biến thể role thu hẹp → tách case riêng theo [data-visibility-rule](../10-be/data-visibility-rule.md) #7.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Kiểm tra hiển thị mặc định của toàn màn hình.
2. Kiểm tra title màn hình.
3. Kiểm tra các khối thông tin chính.
4. Kiểm tra button mặc định.
5. Kiểm tra trạng thái enable/disable mặc định.
6. Kiểm tra control bắt buộc có dấu `*`.
7. Kiểm tra thông tin màu sắc, vị trí, căn chỉnh theo thiết kế.

## Expected chuẩn

Expected phải liệt kê rõ từng thành phần hiển thị:

```text
Hiển thị giao diện như KBNV bao gồm:
- Title: Thêm mới template sản phẩm
- Button Hủy: enable
- Button Lưu: disable
- Khối Thuộc tính gốc của sản phẩm
- Textbox Tên sản phẩm*: disable
- Combobox Mã đối tác: disable
- Combobox Mã hợp đồng: disable
```

## Lỗi cần chặn

- Không được viết expected chung chung: `Hiển thị đúng`.
- Không được bỏ qua trạng thái button chính.
- Không được bỏ qua các trường disable mặc định.
- Không được tự thêm field ngoài tài liệu.

## Checklist review

- [ ] Có title màn hình.
- [ ] Có button chính/phụ.
- [ ] Có các block/section chính.
- [ ] Có trạng thái mặc định từng control.
- [ ] Có dấu `*` cho field bắt buộc.
