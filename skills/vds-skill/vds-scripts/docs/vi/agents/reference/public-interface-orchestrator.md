<!-- diátaxis: reference -->
<!-- lang: vi -->
<!-- draft-translation: needs-human-review -->

> ⚠️ **BẢN DỊCH NHÁP — CẦN CON NGƯỜI RÀ SOÁT**
>
> Đây là bản dịch tiếng Việt do máy tạo ra từ nguồn tiếng Anh tại `../../../agents/reference/public-interface-orchestrator.md`.
> Theo `.gpt-5.4/specs/who-project-documentation-enhancement/requirements.md`, tài liệu tiếng Việt phải do con người dịch trước khi được xem là chính thức. Người rà soát cần kiểm tra, chỉnh sửa thuật ngữ kỹ thuật, và xóa banner này trước khi file trở thành chính thức.
>
> Theo dõi: [`docs/vi/TRANSLATION-BACKLOG.md`](../../TRANSLATION-BACKLOG.md)

# Public interface orchestrator

> Trích xuất bằng chứng về ranh giới public interface phục vụ audit tuân thủ.

## Phạm vi

- **Làm:** Quét các repo để phát hiện import có khả năng vi phạm ranh giới (internal, impl, adapter, infrastructure), tạo bằng chứng heuristic cho các mục checklist audit.
- **Không làm:** Khẳng định chắc chắn việc vi phạm — kết quả cần được xác nhận thủ công kèm phân tích cú pháp.
- **Người dùng chính:** AI agent (thu thập bằng chứng audit), đội ngũ rà soát tuân thủ.

## Điểm vào CLI

```bash
# Qua router thống nhất
vds-cli public-interface --help

# Direct entry
vds-cli public-interface --help
```

## Lệnh chính

| Lệnh | Mục đích | Flag thường dùng |
|------|----------|------------------|
| `scan-repo` | Quét một repo cho các import ứng viên vi phạm ranh giới | `--json/--no-json`, `--output` |
| `scan-project` | Quét thư mục project chứa nhiều repo | `--json/--no-json`, `--output` |

## Heuristic phát hiện

Quét các file `.py`, `.java`, `.kt`, `.ts`, `.tsx`, `.js`, `.jsx` (trừ test) để tìm:

- Import `internal`
- Import `impl` / `adapter`
- Import `infrastructure`
- Import các ký hiệu `*Impl` / `*Implementation`

## Ví dụ quy trình

```bash
# Quét một repo
vds-cli public-interface scan-repo /path/to/repo

# Quét và lưu JSON
vds-cli public-interface scan-repo /path/to/repo --output boundary-evidence.json

# Quét thư mục project chứa nhiều repo
vds-cli public-interface scan-project /path/to/project --output project-boundary.json

# Output dạng người đọc (không JSON)
vds-cli public-interface scan-repo /path/to/repo --no-json
```

## Định dạng output

```json
{
  "command": "scan-repo",
  "scope": "repo",
  "shared_companion_only": true,
  "files_scanned": 150,
  "candidate_file_count": 3,
  "result_type": "evidence_gap",
  "reasoning": "...",
  "candidates": [...]
}
```

## Liên quan

- **Orchestrators:** [hexagonal](hexagonal-orchestrator.md), [structure](structure-orchestrator.md)
- **Confluence:** [WHO Public Interface](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
