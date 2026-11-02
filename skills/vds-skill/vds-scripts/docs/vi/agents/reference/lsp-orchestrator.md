<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/lsp-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# LSP Orchestrator

> Thao tác Language Server Protocol phục vụ code intelligence.

## Phạm vi

- **Thực hiện:** Quản lý LSP server, truy vấn symbol, điều hướng tới định nghĩa, và lấy thông tin hover.
- **Không thực hiện:** Thay thế tính năng của IDE, quản lý vòng đời server ngoài phạm vi VDS, hoặc xử lý các extension LSP.
- **Đối tượng sử dụng chính:** AI agent (phân tích mã), lập trình viên (điều hướng), đội ngũ công cụ.

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli lsp --help

# Điểm vào trực tiếp
vds-cli lsp --help
```

## Lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `symbol` | Truy vấn symbol trong workspace | `--query` |
| `navigate` | Điều hướng tới định nghĩa | `--file`, `--line`, `--column` |
| `hover` | Lấy thông tin hover | `--file`, `--line`, `--column` |
| `server` | Quản lý LSP server | `--action`, `--language` |

## Quy trình thường gặp

### Quy trình: Tìm định nghĩa của symbol

1. Chạy `vds-cli lsp symbol --query "MyClass"`
2. Lấy file/dòng/cột từ kết quả
3. Điều hướng: `vds-cli lsp navigate --file path.py --line 10 --column 5`

## Liên quan

- **Orchestrator:** [intellij](intellij-orchestrator.md), [code-review](code-review-graph-skill.md), [structure](structure-orchestrator.md)
- **Confluence:** [WHO LSP](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Xử lý sự cố

| Vấn đề | Nguyên nhân | Cách khắc phục |
|-------|-------|------------|
| Không tìm thấy lệnh | Orchestrator chưa được cài đặt | Chạy `uv sync --all-packages` |
| Thiếu cấu hình | Chưa đặt `~/.vds/.env` | Thêm thông tin xác thực cần thiết theo [AGENTS.md](../../../AGENTS.md) |
| Từ chối quyền truy cập | Không đủ quyền | Kiểm tra phạm vi token Bitbucket/Confluence |
