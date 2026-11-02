---
cases_count: 7
---

# File Upload Rule

## Mục đích

Sinh testcase kiểm tra chức năng tải lên tệp tin (File Upload).

## Điều kiện kích hoạt

Kích hoạt khi màn hình có nút Upload file, Kéo thả file, hoặc đính kèm tài liệu.

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

1. Upload file đúng định dạng cho phép.
2. Upload file sai định dạng (extension không hợp lệ).
3. Upload file vượt quá dung lượng tối đa (Max size).
4. Upload file có dung lượng 0 bytes (Empty file).
5. Kéo thả file vào khu vực upload (nếu có hỗ trợ).
6. Upload vượt quá số lượng file tối đa (nếu cho phép multiple upload).
7. Xóa file đã upload thành công.

## Expected chuẩn

- File hợp lệ phải hiển thị preview hoặc tên file rõ ràng sau khi upload.
- Hệ thống báo lỗi rõ ràng về định dạng hoặc dung lượng nếu vi phạm.
- Cho phép xóa file đã tải lên.

## Điều kiện cần Q&A

Tạo Q&A nếu không rõ:
- Định dạng file nào được phép?
- Dung lượng tối đa là bao nhiêu?
- Có cho upload nhiều file cùng lúc không?
