<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/links-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# Links Orchestrator

> Kiểm tra liên kết trong tài liệu cho hệ sinh thái VDS.

## Phạm vi

- **Thực hiện:** Kiểm tra tính toàn vẹn liên kết trong tài liệu markdown, phát hiện liên kết nội bộ/ngoài bị hỏng, và xác minh các tham chiếu chéo trong tài liệu target-state.
- **Không thực hiện:** Tự động sửa liên kết hỏng hay kiểm tra nội dung không phải markdown.
- **Đối tượng sử dụng chính:** AI agent (kiểm tra chất lượng tài liệu), người bảo trì tài liệu.

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli links --help

# Điểm vào trực tiếp
vds-cli links --help
```

## Lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `validate` | Kiểm tra liên kết trong tài liệu | `--mode`, `--root`, `--max-files`, `--report` |

## Chế độ kiểm tra

- `target-state` — kiểm tra liên kết trong cây tài liệu target-state (mặc định)
- `docs` — kiểm tra liên kết trong tài liệu tổng quát với giới hạn số file có thể cấu hình

## Ví dụ quy trình

```bash
# Kiểm tra liên kết target-state (mặc định)
vds-cli links validate

# Kiểm tra tài liệu tổng quát với root tùy chỉnh
vds-cli links validate --mode docs --root ./docs --max-files 100

# Ghi báo cáo JSON
vds-cli links validate --report link-report.json

# Đầu ra chỉ JSON
vds-cli links --json-only validate --mode target-state
```

## Biến môi trường

- `VDS_INSURANCE_DOCS_ROOT` — ghi đè quá trình phát hiện thư mục tài liệu mặc định

## Liên quan

- **Orchestrator:** [structure](structure-orchestrator.md), [brd](brd-orchestrator.md)
- **Confluence:** [WHO Links](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
