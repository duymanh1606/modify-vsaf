---
Version: 1.0.0
Author: M2MBA
Last Updated: 2026-06-09
Description: Nhận diện loại tích hợp + cách điều chỉnh section đặc tả, participant sequence, câu hỏi theo loại — cho NTAPP-integration-inspection
---

# Loại tích hợp — Nhận diện & Điều chỉnh

## 1. Bảng nhận diện loại

| Dấu hiệu nhận biết | Loại tích hợp |
|---|---|
| Swagger/OpenAPI, Postman, endpoint URL, HTTP Method | **REST API** |
| WSDL, XML envelope, SOAPAction, XSD | **SOAP / Web Service** |
| Tên file, layout cột, SFTP/FTP/S3, schedule truyền file | **File-based** |
| Topic/Queue name, Broker, schema message, Producer/Consumer | **Message Queue** |
| Kết hợp nhiều dấu hiệu | **Hybrid** — phân tích từng phần riêng, mỗi loại có bảng/sequence riêng đặt cạnh nhau |

Nếu không đủ dấu hiệu → hỏi thẳng: *"Đối tác tích hợp theo kiểu nào: REST API / File / Message Queue / SOAP / Hybrid?"*

## 2. Tên section đặc tả (Mục 8) theo loại

| Loại | Tên section đặc tả | Nội dung phân tích |
|---|---|---|
| REST API | Bảng phân tích API chi tiết | Method, URL, Auth, Status code, mã lỗi — dùng template `api-spec-template.md` |
| File-based | Bảng đặc tả file tích hợp | Tên file, format, encoding, delimiter, layout cột, naming convention, lịch truyền |
| Message Queue | Bảng đặc tả message/event | Topic/Queue name, message format (JSON/Avro/Protobuf), schema version, delivery guarantee |
| SOAP | Bảng phân tích WSDL/Operation | Operation name, namespace, SOAPAction, Fault code |
| Hybrid | Chia thành nhiều bảng theo từng kiểu | Mỗi kiểu một bảng riêng, đặt cạnh nhau |

### Ví dụ bảng REST API

| Tên API | URL | Method | Mục đích | Auth | Status codes |
|---------|-----|--------|----------|------|-------------|
| Create Customer | `/v1/customers` | POST | Tạo KH tại đối tác | Bearer Token | 201, 400, 409 |
| Create Shipment | `/v1/shipments` | POST | Tạo đơn vận chuyển | Bearer Token | 201, 400, 422 |
| Get Tracking | `/v1/trackings/{id}` | GET | Tra cứu trạng thái | Bearer Token | 200, 404 |

### Ví dụ bảng File-based

| Tên file / Pattern | Format | Encoding | Delimiter | Tần suất | Chiều | Thư mục SFTP | Ghi chú |
|---|---|---|---|---|---|---|---|
| `ORDER_YYYYMMDD.csv` | CSV | UTF-8 | `,` | Hàng ngày 02:00 | Inbound | `/inbox/orders/` | Header row = dòng 1 |
| `RECONCILE_YYYYMMDD.xlsx` | Excel | — | — | Hàng tuần T2 | Outbound | `/outbox/recon/` | Sheet "Data", bỏ "Summary" |

### Ví dụ bảng Message Queue

| Topic / Queue | Broker | Format | Schema version | Producer | Consumer | Delivery | Retention | Ghi chú |
|---|---|---|---|---|---|---|---|---|
| `order.status.changed` | Kafka | JSON | v2 | Đối tác | BE nội bộ | At-least-once | 7 ngày | DLQ: `order.status.changed.dlq` |
| `shipment.created` | Kafka | Avro | v1 | BE nội bộ | Đối tác | Exactly-once | 3 ngày | Schema Registry tại đối tác |

## 3. Participant sequence (Mục 6) theo loại

| Loại | Participant điển hình |
|---|---|
| REST API | App (Client) · Backend · Partner API · Core System |
| File-based | Scheduler · Backend · SFTP/S3 Server · File Processor · Core System |
| Message Queue | Producer (BE) · Message Broker (Topic/Queue) · Consumer (BE) · Core System |
| SOAP | App · Backend · SOAP Gateway · Core System |
| Hybrid | Kết hợp — tách thành 2 sequence riêng nếu luồng phức tạp |

> Khi `direction: inbound` (đối tác gọi mình), participant nên có: **Hệ thống Đối tác · API Gateway · Backend Service** — không đưa Database vào diagram.

## 4. Quy tắc Source [IN] (Mục 2) theo loại

| Loại | Source [IN] |
|---|---|
| REST API | UI nhập / DB cấu hình / BE tự sinh / hệ thống khác |
| File-based | Cột file (ghi rõ tên cột/vị trí), giá trị cố định, hoặc từ cấu hình job |
| Message Queue | message header / message body field / metadata (offset, timestamp) |
| SOAP | XML element / attribute / SOAP header |

## 5. Bảng đặc thù ERD (Mục 9) nên thêm theo loại

| Loại | Bảng đặc thù nên có |
|---|---|
| REST API | `INTEGRATION_LOG` (log request/response raw), `PARTNER_CONFIG` (cấu hình per-partner) |
| File-based | `FILE_TRANSFER_LOG` (tên file, thời điểm, status, record count, lỗi), `FILE_PROCESSING_ERROR` |
| Message Queue | `MESSAGE_INBOUND_LOG` (offset, topic, payload raw, trạng thái), `DEAD_LETTER_LOG` |
| Tất cả | `PARTNER` (danh mục đối tác), `INTEGRATION_EVENT` (audit trail chung) |

## 6. Convention tên field theo loại (Mục 4-C)

- Tên field **DB**: `snake_case`.
- Tên field **API** đổi theo loại: **REST API** → `camelCase`; **File-based** → `snake_case` theo layout file; **Message Queue** → theo schema của broker; **SOAP** → theo định nghĩa WSDL.
