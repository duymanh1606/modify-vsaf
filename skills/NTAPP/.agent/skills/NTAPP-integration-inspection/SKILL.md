---
name: ntapp-integration-inspection
description: "Trợ lý BA phân tích & đặc tả tích hợp hệ thống với đối tác/bên thứ ba, end-to-end. Hỗ trợ 2 chiều tích hợp (mình gọi đối tác / đối tác gọi mình / hai chiều) và đa loại tích hợp (REST API, File-based SFTP/CSV, Message Queue Kafka/RabbitMQ, SOAP). Sinh bộ tài liệu 14 mục: tổng quan, mapping dữ liệu, danh sách thay đổi thực thể, luồng E2E, sequence diagram (Mermaid), đặc tả API/file/message chi tiết, ERD đa đối tác, NFR, rủi ro, bộ câu hỏi elicitation và HTML prototype. Sử dụng khi người dùng nói 'phân tích tích hợp đối tác', 'đặc tả integration', 'integration spec', 'tích hợp API bên thứ ba', 'phân tích tích hợp hệ thống'."
---

# NTAPP Integration Inspection Skill (Stage 1 sub-step)

Sinh bộ tài liệu phân tích & đặc tả tích hợp end-to-end với đối tác — forcing function buộc BA chốt rõ **dữ liệu** (mapping, ERD), **luồng** (E2E 3 giai đoạn, sequence) và **giao kèo kỹ thuật** (đặc tả API, NFR, go-live) trước khi dev/SA vào việc. Điều khiển qua 2 tham số `direction` + `mode`.

Chạy trong **Stage 1 Discovery** khi xuất hiện nhu cầu tích hợp đối tác/bên thứ ba — làm input cho contract surface của HLD/Module 0 (Stage 2).

## Instructions

Read fully and follow: `./workflow.md`
