# KBKT Review Gate Rule (NTAPP & Core)

## Mục đích

Đánh giá chất lượng KBKT sau khi sinh testcase.

## Điều kiện kích hoạt

Bắt buộc chạy sau bước generate KBKT và trước khi chuyển sang tạo data test hoặc automation.

## Tiêu chuẩn Đánh giá (QC Checklist Thang 100 Điểm)

Review KBKT phải chấm theo các tiêu chí và tổng điểm tối đa là 100.
**Đạt khi tổng điểm >= 85.**

| Tiêu chí | Mô tả chi tiết (Tương đương thang điểm 10 cũ) | Điểm tối đa |
|---|---|---:|
| **Đúng nghiệp vụ** | - Đầy đủ nội dung Giao diện - Chức năng - ATTT đối với user cuối.<br>- Đầy đủ Chức năng - ATTT đối với kịch bản tiến trình/API.<br>- Đầy đủ thông tin môi trường triển khai (trình duyệt, version). | 25 |
| **Coverage đủ Slice** | - Bao phủ 100% yêu cầu nghiệp vụ trong specs (`_detailed_design`) và common testcase giao diện.<br>- Có kịch bản hồi quy (Regression) cho chức năng ảnh hưởng.<br>- Có đầy đủ kịch bản Hiệu năng (nếu có yêu cầu).<br>- Có đầy đủ kịch bản Bảo mật (SQLi, XSS, URL Manipulation, CSRF). | 25 |
| **Traceability rõ** | - Nguồn gốc từ đâu (`_detailed_design`, PRD).<br>- Mỗi kịch bản có đủ 5 thông tin: Mục đích, TH test, Data, Bước thực hiện, KQ mong muốn. | 15 |
| **Expected result chính xác** | - Mô tả rõ ràng luồng ghi nợ/ghi có tài khoản ví/ngân hàng.<br>- Phải rõ UI hiển thị gì, Database thay đổi bảng nào, Log ghi gì. | 10 |
| **Format đúng chuẩn** | - Bám sát định dạng 11 cột, rõ ràng, dễ đọc. | 10 |
| **Không hallucination** | - Dữ liệu thực tế, không dùng placeholder (`abc`, `{username}`). | 5 |
| **Automation readiness** | - Testcase có thể tự động hóa không?<br>- Expected có locator/điểm kiểm chứng rõ không?<br>- Data test có thể setup/teardown không? | 10 |

## Ngưỡng pass và Luật Vòng Lặp (Loop Rules)

- **>= 85**: đạt.
- **70-84**: cần chỉnh sửa nhỏ.
- **< 70**: phải update KBKT và review lại.

Nếu tổng điểm **Score < 85**:
- KBKT bị từ chối, bắt buộc quay lại bước **Update KBKT** (Auto-Remediation).
- Tự động khắc phục lỗi, tách validation, thay placeholder bằng data thật.
- Sau khi update bắt buộc phải review và tính điểm lại cho đến khi >= 85.

## Điều kiện reject ngay

- Có expected `???`.
- Có field/control không tồn tại.
- Có testcase thiếu steps hoặc expected.
- Có testcase tự bịa message lỗi.
