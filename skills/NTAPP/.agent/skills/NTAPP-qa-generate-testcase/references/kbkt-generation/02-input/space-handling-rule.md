---
cases_count: 4
---

# Space Handling Rule

## Mục đích

Sinh testcase kiểm tra xử lý khoảng trắng trong textbox/searchbox.

## Điều kiện kích hoạt

Áp dụng cho các field nhập text, đặc biệt là mã/code/name.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Nhập toàn khoảng trắng.
2. Nhập khoảng trắng ở đầu chuỗi.
3. Nhập khoảng trắng ở giữa chuỗi.
4. Nhập khoảng trắng ở cuối chuỗi.

## Expected theo loại field

### Field dạng mã/code không cho khoảng trắng

```text
Hệ thống chặn không cho phép nhập khoảng trắng; giá trị khoảng trắng không hiển thị trong trường đang nhập liệu.
```

### Field dạng searchbox cho nhập khoảng trắng

```text
Hệ thống cho phép nhập khoảng trắng.
```

### Field paste có trim đầu/cuối

```text
Hệ thống cho phép copy/paste và tự động trim space đầu/cuối.
```

## Điều kiện reject

- Không được áp dụng cùng một expected cho mọi field.
- Phải phân biệt `input trực tiếp` và `copy/paste` vì hệ thống có thể xử lý khác nhau.
- Phải phân biệt khoảng trắng đầu/cuối và khoảng trắng giữa chuỗi.
