<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/excel-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# Excel Orchestrator

> Xử lý file Excel và tạo báo cáo.

## Phạm vi

- **Thực hiện:** Đọc/ghi file Excel, định dạng ô, tạo báo cáo từ template, và chuyển đổi giữa các định dạng.
- **Không thực hiện:** Thay thế giao diện Excel, chỉnh sửa công thức phức tạp, hoặc quản lý add-in Excel.
- **Đối tượng sử dụng chính:** AI agent (tạo báo cáo), người vận hành (xuất dữ liệu), đội ngũ tài chính.

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli excel --help

# Điểm vào trực tiếp
vds-cli excel --help
```

## Lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `read` | Đọc file Excel | `--input`, `--sheet` |
| `write` | Ghi file Excel | `--output`, `--data` |
| `template` | Tạo từ template | `--template`, `--data`, `--output` |
| `convert` | Chuyển đổi sang CSV/JSON | `--input`, `--format` |

## Quy trình thường gặp

### Quy trình: Tạo báo cáo từ template

1. Chuẩn bị dữ liệu dạng JSON
2. Chạy `vds-cli excel template --template report.xlsx --data data.json --output report-filled.xlsx`
3. Rà soát và phân phối

## Liên quan

- **Orchestrator:** [google-sheets](google-sheets-orchestrator.md), [pdf](pdf-orchestrator.md)
- **Confluence:** [WHO Excel](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Xử lý sự cố

| Vấn đề | Nguyên nhân | Cách khắc phục |
|-------|-------|------------|
| Không tìm thấy lệnh | Orchestrator chưa được cài đặt | Chạy `uv sync --all-packages` |
| Thiếu cấu hình | Chưa đặt `~/.vds/.env` | Thêm thông tin xác thực cần thiết theo [AGENTS.md](../../../AGENTS.md) |
| Từ chối quyền truy cập | Không đủ quyền | Kiểm tra phạm vi token Bitbucket/Confluence |
