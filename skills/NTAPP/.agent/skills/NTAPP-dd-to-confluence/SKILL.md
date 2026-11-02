---
name: NTAPP-dd-to-confluence
description: Use when publishing or syncing the Detailed Design (DD) of a feature ID (e.g. HUB-01, MPF-20, SCR-COMPOSE) from the spec workspace up to Confluence — either the spec DD already has a Confluence link (update the page to match) or it has none (find the system's DD management page and create a new page under it), following the Template DD Core. Triggers: "đẩy DD lên confluence", "publish DD confluence", "cập nhật DD confluence cho <ID>", "sync detailed design to confluence".
user-invocable: true
argument-hint: "<feature-id>   (vd: HUB-01)"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# NTAPP — DD → Confluence

Đồng bộ tài liệu **Detailed Design (DD)** của một mã tính năng (vd `HUB-01`) từ spec workspace lên **Confluence**, theo đúng **Template DD Core**.

## Nguyên tắc cốt lõi

- **Spec DD là nguồn sự thật (source of truth)**; Confluence là bản xuất bản. Skill đọc DD spec → map sang cấu trúc Template DD Core → ghi lên Confluence.
- **Có link → update; không link → tìm nơi quản lý DD của hệ thống rồi create.**
- **Mọi thao tác ghi (create/update) đều DỪNG preview + chờ người dùng xác nhận** — ghi lên Confluence là thao tác ra ngoài, khó hoàn tác.
- **Không đoán, không tự chế link**: nếu không xác định được hệ thống / nơi quản lý DD / trang đích → DỪNG, hỏi người dùng.
- **2 host Confluence** (`10.254.136.32:8090` và `10.254.136.35:8090`): dùng **đúng host trong link đang xử lý**, không tìm chéo host. Lỗi/không thấy → DỪNG, hỏi người dùng.

## Instructions

Đọc đầy đủ và làm theo: `./workflow.md`

Tài liệu tham chiếu (đọc khi tới bước cần):
- `./references/confluence-api.md` — curl mẫu GET/POST/PUT + duyệt cây trang + xử lý lỗi + credentials.
- `./references/storage-format.md` — map Markdown → Confluence storage-format (XHTML): bảng, heading, list, link, code/macro.
- `./references/mermaid-to-plantuml.md` — convert Mermaid → PlantUML (house-style) nhúng PlantUML Macro + quy tắc fallback.
