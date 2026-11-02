---
Version: 1.0.0
Author: M2MBA
Last Updated: 2026-06-09
Description: Template đặc tả API/Message/File chi tiết + ví dụ — cho Mục 8 của NTAPP-integration-inspection
---

# Template Đặc tả Chi tiết — Tham chiếu cho Mục 8

Đặc tả theo **đúng thứ tự bảng mapping API↔Sequence (Mục 7)**. REST API dùng template đầy đủ dưới đây. File/Message/SOAP dùng bảng đặc tả tương ứng — xem [`integration-types.md`](integration-types.md) §2.

> **Lưu ý theo `direction`:** `inbound` (mình expose API) → cột "Hành động đề xuất cho đối tác" mô tả đối tác nên làm gì với từng status; nhấn data scoping + PII masking. `outbound` (mình gọi đối tác) → mô tả mình xử lý response/lỗi của đối tác thế nào.

---

## Template REST API

### API [#] — [Tên API]

**Thông tin cơ bản**

| Thuộc tính | Giá trị |
|-----------|--------|
| Mục đích | *(mô tả nghiệp vụ)* |
| Method | GET / POST / PUT / PATCH / DELETE |
| Endpoint | `/api/v1/[resource]` |
| Authentication | API Key (Header: `X-API-Key`) / Bearer Token / mTLS |
| Content-Type | `application/json` |
| Idempotency | Có / Không *(nếu có: header `Idempotency-Key`)* |

**Request Parameters**

*Path Parameters:*
| Field | Type | Required | Description | Example |
|-------|------|---------|-------------|---------|

*Query Parameters:*
| Field | Type | Required | Default | Description | Example |
|-------|------|---------|---------|-------------|---------|

*Request Body:*
| Field | Type | Required | Constraints | Description | Example |
|-------|------|---------|------------|-------------|---------|

**Response 200 OK**

| Field | Type | Nullable | Description | Example |
|-------|------|---------|-------------|---------|

> Nếu có pagination, bắt buộc thêm meta object:
> ```json
> "meta": { "total": 100, "page": 1, "per_page": 20, "total_pages": 5 }
> ```

**Ví dụ JSON**

```json
// Request
{ "field": "value" }

// Response 200 OK
{ "data": { ... }, "meta": { ... } }

// Response lỗi (error envelope chuẩn)
{ "error": { "code": "VALIDATION_ERROR", "message": "Mô tả lỗi", "details": [{ "field": "field_name", "issue": "required" }] } }
```

**HTTP Status Codes**

| Code | Tên | Nguyên nhân | Hành động đề xuất cho đối tác |
|------|-----|------------|-------------------------------|
| 200 | OK | Thành công | Xử lý dữ liệu |
| 201 | Created | Tạo mới thành công | Lưu id trả về |
| 400 | Bad Request | Sai định dạng / thiếu field | Kiểm tra payload trước khi gọi lại |
| 401 | Unauthorized | Token sai/hết hạn | Lấy token mới rồi retry |
| 403 | Forbidden | Không có quyền với resource | Liên hệ để được cấp quyền |
| 404 | Not Found | Resource không tồn tại | Bỏ qua, tiếp tục với item tiếp |
| 409 | Conflict | Trùng dữ liệu (idempotency) | Dùng Idempotency-Key |
| 429 | Too Many Requests | Vượt rate limit | Xem header `Retry-After`, chờ rồi retry |
| 500 | Server Error | Lỗi hệ thống | Retry sau 60s, tối đa 3 lần; báo nếu kéo dài |

**Rate Limiting** *(nếu có)*
- Giới hạn: `X request/phút` per API Key.
- Header trả về: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

**Security**
- Xử lý trường PII: *(che/mask thế nào, vd: `"phone": "090****789"`)*
- Token TTL & refresh: *(mô tả)*
- Log: *(ghi request/response ở đâu, lưu bao lâu)*

---

*(Lặp lại template trên cho từng API trong bảng mapping Mục 7.)*

---

## Ví dụ minh họa

### Mô tả quy trình (Mục 5) — `outbound`, REST API

```
Phần 1 — Chuẩn bị đầu vào  [AUTH]
Đối tác (hệ thống giao vận) cần: API Key onboarding; danh sách order_code / khoảng thời gian; biết endpoint môi trường.

Phần 2 — Xác thực  [AUTH]
Bước 1 — Gửi API Key: header `X-API-Key: [key]` trong mọi request.
Bước 2 — Hệ thống xác thực: kiểm tra key, định danh đối tác, kiểm tra partner scope.
Bước 3 — Từ chối: key sai → 401 + `INVALID_API_KEY`.

Phần 3 — Luồng chính  [DATA MAPPING] → [INTEGRATION FLOWS]
[DATA MAPPING] Bước 0 — Thiết lập partner scope (lần đầu): admin cấu hình partner_code/scope/rate limit → lưu PartnerConfig.
[INTEGRATION FLOWS] Bước 1 — GET /api/v1/orders?from_date&to_date&page → danh sách order_id + meta.
[INTEGRATION FLOWS] Bước 2 — GET /api/v1/orders/{order_id} với từng id từ Bước 1; 404 thì bỏ qua.

Phần 4 — Xử lý lỗi
401 INVALID_API_KEY → liên hệ admin cấp lại.
403 FORBIDDEN → đơn ngoài phạm vi, bỏ qua.
429 RATE_LIMIT_EXCEEDED → xem Retry-After, chờ rồi retry.
500 SERVER_ERROR → retry sau 60s, tối đa 3 lần exponential backoff; báo nếu > 5 phút.
```

### Đặc tả API ví dụ — Lấy danh sách đơn hàng

| Thuộc tính | Giá trị |
|-----------|--------|
| Mục đích | Trả danh sách đơn hàng trong khoảng thời gian, phân theo đối tác |
| Method | GET |
| Endpoint | `/api/v1/orders` |
| Authentication | API Key (Header: `X-API-Key`) |
| Idempotency | Không áp dụng (GET) |

*Query Parameters:*

| Field | Type | Required | Default | Description | Example |
|-------|------|---------|---------|-------------|---------|
| from_date | string (ISO 8601) | Có | — | Ngày bắt đầu lọc | `2026-01-01` |
| to_date | string (ISO 8601) | Có | — | Ngày kết thúc lọc | `2026-01-31` |
| status | string | Không | all | Lọc theo trạng thái đơn | `confirmed` |
| page | integer | Không | 1 | Trang hiện tại | `1` |
| per_page | integer | Không | 20 | Số bản ghi/trang (max 100) | `50` |

```json
// Response 200 OK
{
  "data": [
    { "orderId": "ORD-2026-001", "orderCode": "DH001", "status": "confirmed",
      "createdAt": "2026-01-15T08:30:00+07:00", "totalAmount": 250000 }
  ],
  "meta": { "total": 150, "page": 1, "per_page": 20, "total_pages": 8 }
}

// Response lỗi
{
  "error": {
    "code": "INVALID_DATE_RANGE",
    "message": "Khoảng thời gian không hợp lệ. from_date phải nhỏ hơn to_date.",
    "details": [ { "field": "from_date", "issue": "must be before to_date" } ]
  }
}
```
