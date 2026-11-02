---
cases_count: 5
---

# Required Field Rule

## Mục đích

Sinh testcase kiểm tra trường bắt buộc nhập.

## Điều kiện kích hoạt

Kích hoạt khi field có một trong các dấu hiệu:

- Có dấu `*`.
- DD ghi bắt buộc.
- API request field là required.
- DB column NOT NULL và UI cho nhập.
- Existing KBKT đã có testcase bắt buộc cho field.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Không nhập dữ liệu.
2. Nhập toàn khoảng trắng.
3. Xóa dữ liệu đang có rồi submit.
4. Submit form khi field required nằm trong block đang hidden/disabled.
5. Trigger lỗi required bằng focus-in → blur-out (click vào field rồi click ra ngoài).

## Expected chuẩn

- Nếu bỏ trống: hiển thị inline error ngay dưới field.
- Nếu nhập toàn khoảng trắng và field có rule trim/chặn space: hiển thị lỗi bắt buộc.
- Message lỗi phải lấy từ spec/Q&A/rule project.
- Không tự bịa message lỗi.

## Cách trigger lỗi (BẮT BUỘC)

Lỗi required/empty chỉ nổi khi field ở trạng thái `touched`. Bước trigger chuẩn:

- (1) Click vào `<field>`. (2) Click ra ngoài (blur).

KHÔNG dùng bước "Bấm Lưu/Tạo/Submit" để trigger lỗi required nếu nút submit disabled khi form invalid (nút disabled không click được). Xem `06-validation/inline-error-rule.md` §"Chọn cách trigger đúng".

## Template expected

```text
Hiển thị báo lỗi inline ngay dưới trường dữ liệu với nội dung: <Tên field> là bắt buộc.
```

## Điều kiện cần Q&A

Tạo Q&A nếu:

- Field bắt buộc nhưng không có message lỗi.
- Không rõ lỗi hiển thị inline, toast hay modal.
- Không rõ validate khi focus out hay khi nhấn Lưu.
