<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/schema-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# Schema orchestrator

> Chuyển đổi schema markdown sang Prisma, TypeORM, PlantUML, Mermaid, SQL DDL, JSON Schema.

## Phạm vi

- **Làm:** Chuyển đổi định nghĩa schema giữa các định dạng, xác thực theo chuẩn, sinh script migration và tạo sơ đồ ER.
- **Không làm:** Thiết kế schema từ đầu, thay thế công cụ ORM, hoặc quản lý migration database.
- **Người dùng chính:** AI agent (sinh mã), nhà phát triển (chuyển đổi schema), DBA.

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli schema --help

# Direct entry
vds-cli schema-convert --help
```

## Lệnh chính

| Lệnh | Mục đích | Flag thường dùng |
|------|----------|------------------|
| `convert` | Chuyển đổi định dạng schema | `--input`, `--output`, `--target` |
| `validate` | Xác thực schema | `--input`, `--standard` |
| `generate` | Sinh mã từ schema | `--input`, `--language`, `--output` |
| `diagram` | Sinh sơ đồ ER | `--input`, `--format` |

## Quy trình thường gặp

### Quy trình: Markdown sang Prisma

1. Định nghĩa schema trong markdown kèm frontmatter
2. Chạy `vds-cli schema-convert convert --input schema.md --target prisma --output schema.prisma`
3. Rà soát Prisma schema vừa sinh
4. Chạy `prisma validate` để kiểm chứng

### Quy trình: Sinh sơ đồ ER

1. Chạy `vds-cli schema-convert diagram --input schema.md --format mermaid`
2. Render bằng mermaid-cli hoặc nhúng vào docs

## Liên quan

- **Orchestrators:** [openapi](openapi-orchestrator.md), [diagrams](diagrams-orchestrator.md), [db-query](db-query-orchestrator.md)
- **Confluence:** [WHO Schema](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Xử lý sự cố

| Sự cố | Nguyên nhân | Cách khắc phục |
|-------|-------------|----------------|
| Command not found | Orchestrator chưa được cài | Chạy `uv sync --all-packages` |
| Config missing | `~/.vds/.env` chưa được cấu hình | Thêm credentials theo [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Quyền truy cập không đủ | Kiểm tra token scope Bitbucket/Confluence |
