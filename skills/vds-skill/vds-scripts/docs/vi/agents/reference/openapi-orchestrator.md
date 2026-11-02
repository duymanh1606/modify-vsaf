<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/openapi-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# OpenAPI Orchestrator

> Kiểm tra, chuyển đổi schema OpenAPI, và sinh client.

## Phạm vi

- **Thực hiện:** Kiểm tra spec OpenAPI 3.x, chuyển đổi giữa các định dạng (JSON/YAML), sinh stub client, và trích xuất tài liệu endpoint.
- **Không thực hiện:** Thiết kế API, thay thế Swagger UI, hay quản lý API gateway.
- **Đối tượng sử dụng chính:** AI agent (rà soát API), lập trình viên (sinh client), QA (kiểm thử hợp đồng).

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli openapi --help

# Điểm vào trực tiếp
vds-cli openapi --help
```

## Lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `validate` | Kiểm tra spec OpenAPI | `--input`, `--strict` |
| `convert` | Chuyển đổi giữa JSON/YAML | `--input`, `--output` |
| `generate` | Sinh stub client | `--input`, `--language`, `--output` |
| `extract` | Trích xuất tài liệu endpoint | `--input`, `--path` |

## Quy trình thường gặp

### Quy trình: Kiểm tra spec API

1. Chạy `vds-cli openapi validate --input api.yaml --strict`
2. Xem lại các lỗi kiểm tra
3. Sửa vấn đề và chạy kiểm tra lại

### Quy trình: Sinh client Python

1. Chạy `vds-cli openapi generate --input api.yaml --language python --output client/`
2. Xem lại mã client được sinh
3. Thêm vào dependency của dự án

## Liên quan

- **Orchestrator:** [schema](schema-orchestrator.md), [public_interface](public-interface-orchestrator.md)
- **Confluence:** [WHO OpenAPI](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Xử lý sự cố

| Vấn đề | Nguyên nhân | Cách khắc phục |
|-------|-------|------------|
| Không tìm thấy lệnh | Orchestrator chưa được cài đặt | Chạy `uv sync --all-packages` |
| Thiếu cấu hình | Chưa đặt `~/.vds/.env` | Thêm thông tin xác thực cần thiết theo [AGENTS.md](../../../AGENTS.md) |
| Từ chối quyền truy cập | Không đủ quyền | Kiểm tra phạm vi token Bitbucket/Confluence |
