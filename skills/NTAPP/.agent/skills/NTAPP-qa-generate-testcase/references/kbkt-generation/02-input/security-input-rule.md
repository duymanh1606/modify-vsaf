---
cases_count: 5
---

# Security Input Rule

## Mục đích

Đảm bảo testcase có kiểm tra dữ liệu có rủi ro bảo mật ở các field text/searchbox.

## Điều kiện kích hoạt

Áp dụng cho field cho nhập text hoặc paste text.

## Testcase nên có

1. Nhập HTML tag.
2. Nhập JavaScript snippet.
3. Nhập SQL-like string nếu field gửi xuống API truy vấn.
4. Nhập Unicode/ký tự đặc biệt.
5. Nhập chuỗi dài bất thường nếu không có maxlength rõ ràng.

## Expected chuẩn

Expected không được tự khẳng định hệ thống an toàn nếu chưa có spec kỹ thuật.

Có thể viết theo hướng quan sát:

```text
Hệ thống cho phép nhập nhưng khi hiển thị/lưu không được thực thi HTML/JavaScript; dữ liệu phải được encode/sanitize theo cơ chế hệ thống.
```

## Điều kiện cần Q&A

Tạo Q&A nếu tài liệu không nói rõ:

- Có sanitize input không?
- Có encode output không?
- Có chặn HTML/JS tại UI không?
- Có validate ở backend không?
