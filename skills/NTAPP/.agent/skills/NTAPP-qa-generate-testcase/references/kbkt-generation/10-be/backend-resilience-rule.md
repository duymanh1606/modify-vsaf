---
cases_count: 15
---

# General Backend Resilience Rules

## Mục đích

Sinh testcase kiểm tra khả năng kháng lỗi, timeout và phục hồi phía Backend nhằm bảo vệ tính toàn vẹn của giao dịch E2E và hệ thống.

## Điều kiện kích hoạt

Kích hoạt khi màn hình/chức năng có gọi API Backend, tương tác cơ sở dữ liệu (DB), ghi bộ nhớ đệm (Cache) hoặc tích hợp với các hệ thống con (downstream).

## Thành phần cần kiểm tra

- API Gateway & Các API Client.
- Cơ chế Resilience4j (Circuit Breaker, Timeout).
- Redis Cache.
- Database (Transaction, Connection Pool, Unique constraints).
- Authentication & Authorization (Session, RBAC Token).

## Danh sách Testcase Bắt Buộc (Mỗi mục là 1 hàng riêng biệt trong bảng)

> [!CAUTION]
> **KHÔNG ĐƯỢC GỘP:** Mỗi số thứ tự dưới đây **BẮT BUỘC PHẢI LÀ 1 DÒNG (1 TESTCASE) ĐỘC LẬP** trong bảng testcase cuối cùng. Không được gộp chung.

### Timeout & Downstream

1. **Timeout downstream**: Dịch vụ con phản hồi chậm quá cấu hình -> Hệ thống tự ngắt kết nối, trả mã lỗi timeout, không treo luồng.
2. **Downstream sập**: Dịch vụ con lỗi 5xx/mất kết nối -> Backend trả mã lỗi Gateway (502/504), UI hiển thị thông báo tường minh.
3. **Circuit Breaker**: Dịch vụ con lỗi liên tục -> Kích hoạt từ chối nhanh (fast-fail) lập tức để tránh treo hệ thống.

### Cache

4. **Lỗi đọc Cache**: Kết nối Cache lỗi/timeout ở chiều đọc -> Fallback tự động truy vấn DB gốc, không lỗi luồng.
5. **Lỗi ghi Cache**: Kết nối Cache lỗi ở chiều ghi -> Ghi nhận log lỗi hệ thống, giao dịch nghiệp vụ chính vẫn thành công.

### DB & Transaction

6. **Race Condition**: 2 Maker submit đồng thời trên cùng tài nguyên -> DB báo lỗi ràng buộc duy nhất, transaction thứ hai rollback hoàn toàn, trả lỗi 409.
7. **Cạn kết nối DB**: Số kết nối DB đạt giới hạn -> Chủ động trả lỗi quá tải 503 thay vì treo hàng đợi request.
8. **Lỗi ghi audit log/bảng phụ**: Lỗi ghi log phụ trợ -> Ghi nhận lỗi nhưng vẫn commit thành công giao dịch nghiệp vụ chính.

### Đồng bộ trạng thái xuyên hệ thống

11. **Revalidate tại thời điểm ghi (TOCTOU)**: Giữa lúc đọc list và lúc submit/bind/duyệt, trạng thái tài nguyên đổi ở hệ nguồn (được duyệt/từ chối/hết hạn) -> hệ thống PHẢI đọc lại trạng thái hiện tại trước khi ghi; nếu không còn hợp lệ -> chặn + báo lỗi tường minh, KHÔNG tạo/bind với trạng thái cũ.
12. **Stale-read trong cửa sổ cache/TTL**: Tài nguyên đổi trạng thái ở nguồn khi list/detail còn trong TTL cache -> sau refresh/hết TTL list phản ánh đúng; không cho phép hành động dựa trên trạng thái cũ đang hiển thị.
13. **Event-before-entity (sự kiện đến trước khi bản ghi tồn tại)**: Hệ nguồn phát event đồng bộ trạng thái TRƯỚC khi entity đích được tạo -> consumer không tìm thấy bản ghi -> verify trạng thái KHÔNG mất vĩnh viễn (có backfill/reload/đối soát) HOẶC entity tạo sau tự lấy trạng thái mới nhất. Chống "nuốt event + ACK" gây lệch vĩnh viễn.
14. **Snapshot vs source-of-truth drift + đối soát**: Trạng thái copy/denormalize vào bản ghi local lúc tạo; sau đó nguồn đổi -> verify bản ghi local được đồng bộ về khớp nguồn qua event/reload; nếu đồng bộ lỡ thì job đối soát (reconciliation) phát hiện và sửa. Chống seed cứng giá trị mặc định che mất trạng thái thật.
15. **Terminal/ineligible state đưa vào luồng sai**: Tài nguyên đã ở trạng thái kết thúc/không hợp lệ (đã duyệt/đã từ chối/đã hủy) bị đưa vào hành động giả định trạng thái trước đó -> phải bị chặn theo state machine, không double-process.

### Security & Session

9. **Hết hạn session**: Phiên đăng nhập hết hạn hoặc bị thu hồi giữa chừng -> Chặn API, trả lỗi 401 hướng dẫn đăng nhập lại.
10. **Vượt quyền (RBAC)**: Gửi request ngoài phạm vi phân quyền của tài khoản -> Chặn lập tức, trả lỗi 403 Forbidden.

## Expected chuẩn

Kỳ vọng phải mô tả rõ trạng thái của các tầng (UI, API, DB), ví dụ:

```text
Hệ thống ngắt kết nối sau <timeout_limit> giây, trả về mã lỗi timeout. UI hiển thị thông báo: "Dịch vụ phản hồi chậm, vui lòng thử lại sau".
```

```text
Hệ thống tự động bỏ qua lỗi kết nối Cache và thực hiện truy vấn trực tiếp từ cơ sở dữ liệu gốc để trả về kết quả 200 OK cho người dùng.
```

```text
Cơ sở dữ liệu thực hiện rollback toàn bộ tiến trình ghi của giao dịch thứ hai. Hệ thống trả về lỗi 409 Conflict. UI thông báo: "Hồ sơ đã tồn tại hoặc đang được xử lý".
```

## Điều kiện reject

- Tự ý suy đoán Expected mà không đối soát tài liệu thiết kế nghiệp vụ (`_detailed_design`) hoặc mã lỗi thực tế của hệ thống.
- Gộp chung các kịch bản lỗi Backend thành một case duy nhất.
- Bỏ qua các bước kiểm chứng DB (ví dụ: rollback kiểm tra bản ghi rác) trong Expected Result.
