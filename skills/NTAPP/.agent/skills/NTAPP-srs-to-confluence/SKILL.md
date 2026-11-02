---
name: NTAPP-srs-to-confluence
description: "Use when publishing or syncing the SRS (Software Requirements Specification) of a feature ID (e.g. BE-RP-17, SCR-SEND-PARTNER, INT-EXT-15) from the spec workspace (Stage 4 DD + Stage 5 story/ATDD) up to Confluence — infer SRS type (api/consumer/web) from the DD, fetch the matching SRS template page from Confluence, generate reviewable parts, then create or update the target page. Triggers: đẩy SRS lên confluence, publish SRS confluence, sync SRS to confluence, tạo tài liệu SRS cho <ID>."
user-invocable: true
argument-hint: "<feature-id>   (vd: BE-RP-17)"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - Skill
  - mcp__atlassian32__confluence_get_page
  - mcp__atlassian32__confluence_get_page_children
  - mcp__atlassian32__confluence_search
  - mcp__atlassian32__confluence_create_page
  - mcp__atlassian32__confluence_update_page
  - mcp__atlassian32__confluence_upload_attachment
  - mcp__atlassian__confluence_get_page
  - mcp__atlassian__confluence_get_page_children
  - mcp__atlassian__confluence_search
  - mcp__atlassian__confluence_create_page
  - mcp__atlassian__confluence_update_page
  - mcp__atlassian__confluence_upload_attachment
---

# NTAPP — SRS → Confluence

Sinh & đồng bộ tài liệu **SRS (Software Requirements Specification)** của một mã tính năng (vd `BE-RP-17`) từ spec workspace (**Stage 4 DD + Stage 5 story/ATDD**) lên **Confluence**, theo **template SRS fetch từ Confluence** tương ứng type.

## Nguyên tắc cốt lõi

- **Nguồn sự thật = spec Stage 4 (DD) + Stage 5 (story/ATDD).** SRS là bản tổng hợp hướng yêu cầu; Confluence là bản xuất bản. Không bịa nội dung khi map.
- **1 SRS = 1 feature ID.** Type (`api`/`consumer`/`web`) suy từ DD; mơ hồ → hỏi. Contract `INT-EXT-*`/`INT-INT-*` có thể đứng riêng hoặc pair-merge vào SRS runtime — hỏi khi phát hiện cặp.
- **Bắt buộc đủ Stage 4 + Stage 5.** Thiếu Stage 5 → DỪNG, hoàn thành Stage 5 trước (không gen SRS từ nguồn thiếu).
- **Có link SRS → update; không → tìm nơi quản lý SRS của hệ thống rồi create** (hỏi tên trang khi tạo mới).
- **Mọi thao tác ghi Confluence DỪNG preview + chờ xác nhận.** Không đoán trang đích/hệ thống/nơi quản lý SRS.
- **Backend = MCP Atlassian** đọc page, 2 server theo host: `mcp__atlassian32` (.32) / `mcp__atlassian` (.35, live hiện tại — .32 token hết hạn). Không đọc env, không curl để đọc — trừ fallback `confluence-get.ps1` khi MCP host đó chết. Không tìm chéo host.
- **Attachment (draw.io/ảnh/HTML) KHÔNG upload được qua MCP trên Confluence Server** → agent TỰ chạy REST script `scripts/confluence-publish.ps1` đọc token từ `.confluence-auth` (gitignored). Không bắt user gõ lệnh. Thiếu token → DỪNG hỏi user setup.
- **Bám ĐÚNG template:** checkbox = `ac:task-list` (không `☑/☐`), ngày = date macro, §2.1 = activity diagram draw.io (sinh bằng `scripts/build-activity-diagram.mjs`), NFR dồn §1 — xem `references/confluence-server-publish.md`.
- **Thuật ngữ theo `references/terminology.md`** — giữ tiếng Anh cho từ đội vốn nói tiếng Anh (`version`, `log`, `cache`, `trace id`, `transaction`); CẤM tự dịch thuần Việt kiểu "khóa lạc quan" / "nhật ký kiểm toán" / "bộ nhớ đệm". Bảng này hồi tố cả trang đã publish.
- **Bước ghi DB phải nêu ĐỦ bảng + cột + giá trị NGAY tại bước đó** — bảng lồng `Trường nghiệp vụ | Cột trong CSDL | Giá trị ghi vào`, câu dẫn nêu tên bảng schema-qualified. CẤM mô tả chung chung kiểu "thêm 1 dòng vào bảng X" rồi trỏ sang mục 4. Áp cho MỌI bước ghi, kể cả bước ghi log và bước ghi khi thất bại.
- **Bảng ghi nhận thay đổi chỉ ghi thay đổi NGHIỆP VỤ** — publish chỉ để chuẩn hóa thuật ngữ, làm rõ mô tả sẵn có, sửa chính tả/format/sơ đồ hay sửa lỗi tự gây thì **KHÔNG thêm dòng**, chỉ ghi `versionMessage` + log sync. Version trang Confluence chạy tiếp còn dòng mới nhất dừng ở version cũ là bình thường. Chi tiết: `references/srs-mapping.md` §Map changelog.
- **Web → SRS skill TỰ render HTML màn hình** từ `ui_schema_{id}.json` (gọi `NTAPP-ui-generation` sinh ui_schema nếu thiếu — skill đó KHÔNG render HTML) + full-screen story; nhúng qua HTML macro (server .35 tắt HTML macro → fallback attachment + link tải). Render chưa sát → tham chiếu code FE thật.
- **Crosslink §9 (forward+reverse):** khi publish, nối link mục "Tài liệu liên quan" tới các trang SRS anh em đã có (map local-first: `srs-publish-history.md` + DD header); ID chưa có SRS → ghi ledger pending (`crosslink-pending.md`, append SAU publish khi đã có pageId), tới khi nó publish thì reverse-update trang chờ. Reverse ghi đè trang khác → qua HITL §8. Chi tiết: `references/srs-mapping.md`.
- **Chrome optional:** `build-activity-diagram.mjs` exit 2 (thiếu Chrome/PNG) → vẫn publish mxfile + macro drawio (macro live-render bình thường), KHÔNG dừng. PNG chỉ là bản tĩnh dự phòng (PDF/email/JS-off), best-effort — KHÔNG phải để chữa watermark (thuyết "license→watermark" đã bị refute; thủ phạm "diagram chưa update" là `revision` lệch version — xem `references/confluence-server-publish.md` §3).
- **Đọc `.32` không qua MCP:** MCP `.32` chết → REST Basic đọc `.32` qua `scripts/confluence-get.ps1` (user/pass trong `.confluence-auth`), chỉ đọc, chỉ khi MCP fail. Pre-flight §0 có 3 tầng: MCP `.32` → REST `.32` → `.35`.

## Instructions

Đọc đầy đủ và làm theo: `./workflow.md`

Tài liệu tham chiếu (đọc khi tới bước cần):
- `./references/confluence-server-publish.md` — **(quan trọng cho §8/§9)** publish thật lên Confluence Server: auth file + REST attachment (MCP fail), task-list checkbox, date macro, activity diagram draw.io, template fidelity.
- `./references/terminology.md` — **(đọc TRƯỚC khi sinh nội dung §4 + quét lại trước khi publish §9)** từ điển thuật ngữ: từ nào giữ tiếng Anh, từ nào giữ tiếng Việt.
- `./references/srs-mapping.md` — map spec (DD+story) → khung SRS theo 3 type + nhúng HTML macro + fallback + map changelog.
- `../NTAPP-dd-to-confluence/references/confluence-api.md` — cheat sheet MCP Atlassian (6 tool + xử lý lỗi + lưu ý host).
- `../NTAPP-dd-to-confluence/references/storage-format.md` — map Markdown → Confluence storage-format (XHTML) + nhúng macro.
- `../NTAPP-dd-to-confluence/references/mermaid-to-plantuml.md` — convert Mermaid → PlantUML house-style + fallback.

Script (agent chạy qua shell tool, đọc `.confluence-auth`):
- `./scripts/confluence-publish.ps1 -Manifest <manifest.json>` — upload attachment (REST multipart) + PUT body, atomic.
- `./scripts/build-activity-diagram.mjs <model.json> <out_dir> <base>` — 1 model → mxfile draw.io + PNG (Chrome headless).
