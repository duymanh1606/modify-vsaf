# NTAPP Review Anti-Patterns

## Mục đích
Tài liệu này liệt kê các hành vi "chống mẫu" (cấm kỵ) khi thực hiện Review kịch bản kiểm thử (KBKT).

---

## Quy Tắc Chống Mẫu Khi Review (Anti-Patterns)

Nghiêm cấm các hành vi sau khi Review kịch bản:

- ❌ **Đánh giá hời hợt, chỉ kiểm tra Happy Path:** Phải rà soát cực kỳ kỹ lưỡng các kịch bản Negative, Boundary, Regression, Performance và Security.
- ❌ **Chấp nhận dữ liệu placeholder:** Bất kỳ dữ liệu nào dạng `{username}`, `abc`, `...` đều phải bị đánh lỗi chất lượng và trừ điểm, yêu cầu làm rõ thành dữ liệu thực tế.
- ❌ **Chấp nhận expected result chung chung:** Không chấp nhận kiểu ghi `Hệ thống xử lý thành công`. Phải ghi rõ UI hiển thị gì, Database thay đổi bảng nào, Log ghi nhận mã gì, và chi tiết ghi nợ/ghi có đối với tài khoản ví/ngân hàng.
- ❌ **Bỏ qua lỗi gộp Validation:** Nếu thấy testcase gộp validation nhiều trường, bắt buộc phải đánh lỗi và yêu cầu tách ra.
- ❌ **Thiếu kịch bản bảo mật cơ bản:** Bỏ qua kiểm tra XSS, SQLi, CSRF và Manipulation URL trên các trường nhập liệu tự do và API endpoints.
