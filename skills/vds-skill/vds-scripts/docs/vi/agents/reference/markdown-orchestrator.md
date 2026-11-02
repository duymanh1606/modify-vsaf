<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/markdown-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# Markdown Orchestrator

> Định dạng và kiểm tra markdown cho tài liệu VDS.

## Phạm vi

- **Thực hiện:** Định dạng file markdown với cách ngắt dòng nhất quán, kiểm tra cú pháp markdown, và kiểm tra các file đã staged hoặc được chỉ định về mức độ tuân thủ định dạng.
- **Không thực hiện:** Render markdown sang HTML hay kiểm tra mục tiêu liên kết (dùng [links-orchestrator](links-orchestrator.md) cho việc đó).
- **Đối tượng sử dụng chính:** AI agent (vệ sinh tài liệu), lập trình viên (kiểm tra pre-commit).

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli markdown --help

# Điểm vào trực tiếp
vds-cli markdown --help
```

## Lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `check` | Kiểm tra định dạng markdown; thoát với mã khác 0 nếu cần thay đổi | `--staged`, `--wrap` |
| `format` | Định dạng file markdown tại chỗ | `--staged`, `--wrap` |
| `version` | Hiển thị phiên bản orchestrator | — |

## Ví dụ quy trình

```bash
# Kiểm tra mọi file markdown đang được theo dõi
vds-cli markdown check

# Kiểm tra các file cụ thể
vds-cli markdown check docs/*.md README.md

# Chỉ kiểm tra các file đã staged
vds-cli markdown check --staged

# Định dạng với độ rộng ngắt dòng tùy chỉnh
vds-cli markdown format --wrap 100

# Định dạng các file đã staged
vds-cli markdown format --staged
```

## Liên quan

- **Orchestrator:** [links](links-orchestrator.md), [pdf](pdf-orchestrator.md)
- **Confluence:** [WHO Markdown](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
