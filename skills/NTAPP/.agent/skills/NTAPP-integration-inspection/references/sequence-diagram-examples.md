---
Version: 1.0.0
Author: M2MBA
Last Updated: 2026-06-09
Description: Sequence Diagram Mermaid mẫu theo từng loại tích hợp — cho Mục 6 của NTAPP-integration-inspection
---

# Sequence Diagram Examples — Tham chiếu cho Mục 6

> Mọi sequence PHẢI: dùng `autonumber`, dùng `Note over` phân nhóm 3 giai đoạn **[AUTH] → [DATA MAPPING] → [INTEGRATION FLOWS]**, KHÔNG đưa Database object vào diagram. Tập trung luồng thành công; nhánh lỗi dùng `alt/else`; retry dùng `loop`. Chi tiết payload mô tả ở bảng đặc tả (Mục 8), không inline vào message.

Participant theo loại: xem [`integration-types.md`](integration-types.md) §3.

---

## 🌐 Ví dụ REST API

```mermaid
sequenceDiagram
autonumber
participant App as 🧩 App (Client)
participant BE as ⚙️ Backend
participant Partner as 🌐 Partner API
participant Core as 🗄️ Core System

Note over App,Partner: [AUTH] — Xác thực
App->>Partner: Lấy token (OAuth2 / API Key)
Partner-->>App: access_token / 401

Note over App,Core: [DATA MAPPING] — Master data tiền đề
App->>BE: Gửi yêu cầu tạo đơn tích hợp
BE->>Core: Kiểm tra mã KH & cấu hình tích hợp
alt Đã có mã KH & cấu hình đối tác
    Core-->>BE: ✅ partnerCustomerId, partnerConfig

    Note over BE,Partner: [INTEGRATION FLOWS] — Luồng nghiệp vụ chính
    BE->>Partner: Gửi request tạo đơn hàng
    Partner-->>BE: Kết quả (mã đối tác, trạng thái)
    alt Thành công
        BE->>Core: Lưu mapping & trạng thái tích hợp
        BE-->>App: ✅ Tạo đơn tích hợp thành công
    else Lỗi nghiệp vụ từ đối tác
        BE-->>App: ⚠️ Thông báo lỗi tích hợp
    end
else Chưa có mã KH/cấu hình
    BE-->>App: ⚠️ Yêu cầu thiết lập cấu hình trước
end
```

---

## 📁 Ví dụ File-based (SFTP)

```mermaid
sequenceDiagram
autonumber
participant Scheduler as ⏰ Scheduler
participant BE as ⚙️ Backend
participant SFTP as 📁 SFTP Server (Đối tác)
participant Core as 🗄️ Core System

Note over Scheduler,SFTP: [AUTH] — Kết nối SFTP (key pair / credential)
Scheduler->>BE: Trigger job theo lịch (vd: 02:00 hàng ngày)
BE->>SFTP: Kết nối SFTP & kiểm tra file mới trong /inbox
alt Có file mới
    SFTP-->>BE: Download file (CSV/Excel)

    Note over BE,Core: [DATA MAPPING] → [INTEGRATION FLOWS]
    BE->>BE: Validate cấu trúc file, header, encoding
    alt File hợp lệ
        BE->>Core: Parse & import dữ liệu vào hệ thống nội bộ
        Core-->>BE: ✅ Import thành công (N records)
        BE->>SFTP: Move file sang /processed
    else File lỗi cấu trúc
        BE->>SFTP: Move file sang /error
        BE-->>BE: ⚠️ Gửi alert & ghi log lỗi
    end
else Không có file mới
    BE-->>BE: ℹ️ Ghi log "no file", kết thúc job
end
```

---

## 📨 Ví dụ Message Queue (Kafka)

```mermaid
sequenceDiagram
autonumber
participant Partner as 🌐 Đối tác (Producer)
participant Broker as 📨 Message Broker
participant Consumer as ⚙️ Consumer (Backend)
participant Core as 🗄️ Core System

Note over Partner,Broker: [AUTH] — SASL/SSL credential tới broker
Partner->>Broker: Publish message (vd: OrderStatusChanged)
Broker-->>Consumer: Deliver message (at-least-once)

Note over Consumer,Core: [DATA MAPPING] → [INTEGRATION FLOWS]
Consumer->>Consumer: Deserialize & validate message schema
alt Message hợp lệ
    Consumer->>Core: Xử lý nghiệp vụ & cập nhật trạng thái
    Core-->>Consumer: ✅ Đã cập nhật
    Consumer->>Broker: Acknowledge message (ACK)
else Message lỗi schema / nghiệp vụ
    Consumer->>Broker: NACK → vào Dead Letter Queue
    Consumer-->>Consumer: ⚠️ Gửi alert, ghi log lỗi
end
```

---

## 🔧 Ví dụ SOAP / Web Service

```mermaid
sequenceDiagram
autonumber
participant App as 🧩 App
participant BE as ⚙️ Backend
participant GW as 🔧 SOAP Gateway (Đối tác)
participant Core as 🗄️ Core System

Note over App,GW: [AUTH] — WS-Security (UsernameToken / Certificate)
App->>BE: Yêu cầu tra cứu/tạo dữ liệu
BE->>GW: SOAP Envelope + WS-Security header

Note over BE,Core: [DATA MAPPING] → [INTEGRATION FLOWS]
GW-->>BE: SOAP Response / SOAP Fault
alt Response hợp lệ
    BE->>Core: Parse XML, map field, lưu nội bộ
    BE-->>App: ✅ Kết quả
else SOAP Fault
    BE-->>App: ⚠️ FaultCode / FaultString
end
```

---

## 📨 Ví dụ `direction: inbound` (đối tác gọi mình — REST API mình expose)

```mermaid
sequenceDiagram
autonumber
participant P as Hệ thống Đối tác
participant GW as API Gateway
participant BE as Backend Service

Note over P,BE: [AUTH] — Đối tác xác thực với API mình
P->>GW: [Method] /endpoint (Header: API-Key / Bearer token)
GW-->>P: 200 OK / 401 Unauthorized

Note over P,BE: [DATA MAPPING] — Master data tiền đề
P->>BE: [Method] /setup-endpoint {master data}
BE-->>P: 200 OK {partner_ref_id}

Note over P,BE: [INTEGRATION FLOWS] — Luồng nghiệp vụ chính
P->>BE: [Method] /endpoint {payload}
BE-->>P: 200 OK {response}

Note over P,BE: Xử lý lỗi
P->>BE: [Method] /endpoint {payload lỗi}
BE-->>P: 4xx/5xx {error envelope}
```
