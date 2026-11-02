<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/google-sheets-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# Google Sheets Orchestrator

> Tích hợp Google Sheets phục vụ xuất dữ liệu và báo cáo của VDS.

## Phạm vi

- **Thực hiện:** Đọc/ghi sheet, đồng bộ dữ liệu từ cơ sở dữ liệu, tạo báo cáo, và quản lý quyền truy cập sheet.
- **Không thực hiện:** Thay thế giao diện Google Sheets, quản lý Google Workspace, hoặc thiết lập OAuth.
- **Đối tượng sử dụng chính:** AI agent (tạo báo cáo), người vận hành (đồng bộ dữ liệu), các đội nhóm cần dashboard chia sẻ.

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli google-sheets --help

# Điểm vào trực tiếp
vds-cli google-sheets --help
```

## Lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `sync` | Đồng bộ dữ liệu vào sheet | `--sheet-id`, `--data`, `--range` |
| `read` | Đọc dữ liệu sheet | `--sheet-id`, `--range` |
| `export` | Xuất vào sheet | `--sheet-id`, `--input`, `--range` |
| `clear` | Xóa vùng trong sheet | `--sheet-id`, `--range` |

## Quy trình thường gặp

### Quy trình: Đồng bộ truy vấn CSDL vào sheet

1. Chạy truy vấn CSDL: `vds-cli db-query query --sql "SELECT * FROM metrics" --format json`
2. Đồng bộ vào sheet: `vds-cli google-sheets sync --sheet-id <id> --data results.json --range A1`
3. Chia sẻ sheet với đội

## Liên quan

- **Orchestrator:** [excel](excel-orchestrator.md), [db-query](db-query-orchestrator.md), [metabase](metabase-orchestrator.md)
- **Confluence:** [WHO Google Sheets](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Xử lý sự cố

| Vấn đề | Nguyên nhân | Cách khắc phục |
|-------|-------|------------|
| Không tìm thấy lệnh | Orchestrator chưa được cài đặt | Chạy `uv sync --all-packages` |
| Thiếu cấu hình | Chưa đặt `~/.vds/.env` | Thêm thông tin xác thực cần thiết theo [AGENTS.md](../../../AGENTS.md) |
| Từ chối quyền truy cập | Không đủ quyền | Kiểm tra phạm vi token Bitbucket/Confluence |
