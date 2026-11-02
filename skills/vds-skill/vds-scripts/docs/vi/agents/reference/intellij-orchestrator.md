<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/intellij-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# IntelliJ Orchestrator

> Thao tác với plugin IntelliJ IDEA và cấu hình dự án.

## Phạm vi

- **Thực hiện:** Quản lý cấu hình IDE, chạy inspection, sinh run configuration, và đồng bộ cấu trúc dự án.
- **Không thực hiện:** Thay thế giao diện IDE, quản lý license, hoặc xử lý các thao tác trên plugin marketplace.
- **Đối tượng sử dụng chính:** Lập trình viên (tự động hóa IDE), DevOps (cấu hình chuẩn hóa).

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli intellij --help

# Điểm vào trực tiếp
vds-cli intellij --help
```

## Lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `inspect` | Chạy inspection mã nguồn | `--profile`, `--output` |
| `config` | Sinh run configuration | `--type`, `--output` |
| `sync` | Đồng bộ cấu trúc dự án | `--path` |

## Quy trình thường gặp

### Quy trình: Chạy inspection trong CI

1. Chạy `vds-cli intellij inspect --profile default --output inspection-results.xml`
2. Phân tích kết quả để tìm vi phạm
3. Đánh dấu build thất bại nếu có vấn đề nghiêm trọng

## Liên quan

- **Orchestrator:** [lsp](lsp-orchestrator.md), [structure](structure-orchestrator.md)
- **Confluence:** [WHO IntelliJ](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Xử lý sự cố

| Vấn đề | Nguyên nhân | Cách khắc phục |
|-------|-------|------------|
| Không tìm thấy lệnh | Orchestrator chưa được cài đặt | Chạy `uv sync --all-packages` |
| Thiếu cấu hình | Chưa đặt `~/.vds/.env` | Thêm thông tin xác thực cần thiết theo [AGENTS.md](../../../AGENTS.md) |
| Từ chối quyền truy cập | Không đủ quyền | Kiểm tra phạm vi token Bitbucket/Confluence |
