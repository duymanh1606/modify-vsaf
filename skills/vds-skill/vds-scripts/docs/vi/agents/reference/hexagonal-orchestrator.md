<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/hexagonal-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# Hexagonal Orchestrator

> Kiểm tra tính tuân thủ kiến trúc hexagonal trong các repository Python và Java.

## Phạm vi

- **Thực hiện:** Phân tích repository về chiều phụ thuộc, ranh giới port/adapter, cô lập domain, và vi phạm tầng lớp thông qua analyzer dựa trên AST.
- **Không thực hiện:** Tự động refactor mã nguồn hay kiểm tra hiệu năng.
- **Đối tượng sử dụng chính:** AI agent (rà soát kiến trúc), tech lead (cổng kiểm soát tuân thủ trong CI).

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli hexagonal --help

# Điểm vào trực tiếp
vds-cli hexagonal --help
```

## Lệnh chính

| Lệnh | Mục đích | Cờ thường dùng |
|---------|---------|-------------|
| `analyze` | Chạy phân tích tuân thủ hexagonal | `--config`, `--verbose`, `--timing`, `--cache-dir`, `--no-cache` |

## Pipeline phân tích

1. **Hồ sơ repository** — phát hiện các file nguồn (`.py`, `.java`, `.kt`)
2. **Phân loại tầng** — ánh xạ file vào tầng domain, application, infrastructure
3. **Điều hướng tới analyzer** — Python AST, Java AST, hoặc analyzer dự phòng
4. **Sinh báo cáo** — danh sách vi phạm kèm đường dẫn file, số dòng, và mức độ nghiêm trọng

## Mã thoát

| Mã | Ý nghĩa |
|------|---------|
| 0 | Phân tích hoàn tất thành công |
| 1 | Lỗi thời gian chạy (không tìm thấy file, lỗi parse) |
| 2 | Lỗi cấu hình |
| 3 | Phát hiện vi phạm (cổng CI) |

## Ví dụ quy trình

```bash
# Phân tích cơ bản
vds-cli hexagonal analyze /path/to/repo

# Với config tùy chỉnh và đầu ra chi tiết
vds-cli hexagonal analyze /path/to/repo --config hexagonal.yaml --verbose --timing

# Đầu ra chỉ JSON dành cho CI
vds-cli hexagonal analyze /path/to/repo --json-only --quiet

# Tắt cache
vds-cli hexagonal analyze /path/to/repo --no-cache
```

## Liên quan

- **Orchestrator:** [structure](structure-orchestrator.md), [circular-dependency](circular-dependency-orchestrator.md)
- **Skill:** [code-review-graph-skill](../../../../vds-skills/skills/code-review-graph-skill/SKILL.md)
