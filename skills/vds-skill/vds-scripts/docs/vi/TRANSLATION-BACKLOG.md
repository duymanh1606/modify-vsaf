<!-- diátaxis: reference -->
<!-- lang: vi -->

# Tồn đọng bản dịch tiếng Việt / Vietnamese Translation Backlog

> Quy tắc spec: tài liệu tiếng Việt phải do con người dịch (không dùng dịch máy). Xem `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md` — Non-Functional Requirements.

Cập nhật lần cuối: 2026-04-23 (đã điều chỉnh để phản ánh trạng thái thật sau khi 16 bản nháp LLM bị iCloud dọn dẹp)

## Trạng thái hiện tại

- Tổng tài liệu tiếng Anh dưới `docs/agents/`: 77
- Tổng tài liệu tiếng Việt dưới `docs/vi/agents/`: ~58 tài liệu đã được con người dịch + 3 bản nháp chờ rà soát = **61 tài liệu**
- Còn thiếu bản dịch tiếng Việt: **16 tài liệu** (liệt kê bên dưới)

## Bản nháp hiện có (chờ rà soát bởi con người — 3 mục)

Các bản nháp này mang chú thích `<!-- draft-translation: needs-human-review -->`. Người rà soát nên kiểm tra thuật ngữ kỹ thuật, loại bỏ cảm giác "dịch máy", và xóa banner sau khi duyệt.

- [`docs/vi/agents/reference/multi-agent-orchestrator.md`](./agents/reference/multi-agent-orchestrator.md) — nguồn: `../agents/reference/multi-agent-orchestrator.md`
- [`docs/vi/agents/how-to/orchestrator-workflows/research-spec-audit-workflow.md`](./agents/how-to/orchestrator-workflows/research-spec-audit-workflow.md) — nguồn: `../agents/how-to/orchestrator-workflows/research-spec-audit-workflow.md`
- [`docs/vi/agents/how-to/orchestrator-workflows/confluence-bitbucket-sync-workflow.md`](./agents/how-to/orchestrator-workflows/confluence-bitbucket-sync-workflow.md) — nguồn: `../agents/how-to/orchestrator-workflows/confluence-bitbucket-sync-workflow.md`

## Bản dịch còn thiếu (chờ người dịch — 16 mục)

Cho mỗi tài liệu dưới đây, người dịch tạo file tiếng Việt tại đường dẫn song song dưới `docs/vi/`, theo quy ước tên-file bằng chữ-hyphen (giữ nguyên CLI strings, code blocks, URL).

### `docs/agents/reference/` (12 mục)

- `excel-orchestrator.md`
- `google-sheets-orchestrator.md`
- `hexagonal-orchestrator.md`
- `intellij-orchestrator.md`
- `links-orchestrator.md`
- `lsp-orchestrator.md`
- `markdown-orchestrator.md`
- `openapi-orchestrator.md`
- `public-interface-orchestrator.md` _(tên file có underscore — được xem xét đổi tên trong pass riêng)_
- `schema-orchestrator.md`
- `sonarqube-orchestrator.md`
- `structure-orchestrator.md`

### `docs/agents/how-to/orchestrator-workflows/` (4 mục)

- `analytics-pipeline-workflow.md`
- `code-quality-gate-workflow.md`
- `document-delivery-workflow.md`
- `memory-progress-workflow.md`

## Quy trình dịch tài liệu (cho tài liệu mới)

1. Đọc tài liệu tiếng Anh tại `docs/agents/...`.
2. Tạo file song song tại đường dẫn tương ứng dưới `docs/vi/`.
3. Giữ header `<!-- diátaxis: X -->`, thêm `<!-- lang: vi -->`.
4. Dịch prose + headings + table cells; giữ nguyên CLI strings, code blocks, URL, tên biến môi trường.
5. Cập nhật tài liệu này — chuyển mục từ "Bản dịch còn thiếu" xuống "Lịch sử hoàn tất" bên dưới.

## Quy trình rà soát bản nháp (cho 3 mục hiện có)

1. Mở file, xác nhận có `<!-- draft-translation: needs-human-review -->`.
2. Đọc song song với nguồn tiếng Anh.
3. Sửa phần dịch sượng, thuật ngữ chuyên ngành, tên lệnh CLI.
4. Xóa dòng `<!-- draft-translation: needs-human-review -->` và khối banner cảnh báo (block `> ⚠️ ...`).
5. Chuyển mục xuống "Lịch sử hoàn tất".

## Lịch sử hoàn tất (rỗng — cập nhật khi người rà soát xác nhận)

_(Chưa có mục nào — cập nhật khi một bản nháp được duyệt hoặc một tài liệu mới được dịch.)_

## Sự cố đã biết (context)

- Ngày 2026-04-23: một lần dịch máy tạo ra 16 bản nháp, nhưng tất cả bị iCloud Drive đánh dấu `.nosync` và bị commit dọn dẹp `4e2cd398 fix(repo): remove invalid symlinks` xóa. Quyết định: KHÔNG tái tạo tự động — tôn trọng quy tắc spec "human-translated".
