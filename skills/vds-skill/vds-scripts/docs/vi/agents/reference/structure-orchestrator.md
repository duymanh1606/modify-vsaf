<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/structure-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# Structure orchestrator

> Xác thực cấu trúc tài liệu VDS và tính nhất quán thư mục project.

## Phạm vi

- **Làm:** Xác thực cấu trúc tài liệu target-state, kiểm tra tính nhất quán thư mục giữa các project, và sinh báo cáo tuân thủ cấu trúc.
- **Không làm:** Tự động tạo thư mục thiếu hoặc xác thực nội dung file.
- **Người dùng chính:** AI agent (kiểm tra sẵn sàng docs), người bảo trì project.

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli structure --help

# Direct entry
vds-structure --help
```

## Lệnh chính

| Lệnh | Mục đích | Flag thường dùng |
|------|----------|------------------|
| `validate` | Xác thực cấu trúc (target-state hoặc tính nhất quán thư mục) | `--mode`, `--root`, `--report` |

## Chế độ xác thực

- `target-state` — xác thực cây tài liệu target-state
- `folder-consistency` — so sánh cấu trúc thư mục giữa các project và chấm điểm nhất quán

## Ví dụ quy trình

```bash
# Xác thực target-state
vds-structure validate --mode target-state

# Xác thực với root tuỳ chỉnh
vds-structure validate --mode target-state --root ./docs

# Kiểm tra nhất quán thư mục giữa các project
vds-structure validate --mode folder-consistency --root ./projects

# Ghi báo cáo JSON
vds-structure validate --mode target-state --report structure-report.json

# JSON-only
vds-structure --json-only validate --mode target-state
```

## Nội dung báo cáo

Báo cáo folder-consistency gồm:
- Tổng số project và số project được phân tích
- Điểm nhất quán (tính theo phần trăm)
- Danh sách project bị thiếu
- Các thư mục và file chung
- Chi tiết mismatch theo từng project

## Biến môi trường

- `VDS_INSURANCE_DOCS_ROOT` — ghi đè gốc discovery tài liệu mặc định

## Liên quan

- **Orchestrators:** [links](links-orchestrator.md), [brd](brd-orchestrator.md)
- **Confluence:** [WHO Structure](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
