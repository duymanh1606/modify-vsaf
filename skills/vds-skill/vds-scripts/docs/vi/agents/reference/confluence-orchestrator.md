<!-- diátaxis: reference -->
<!-- lang: vi -->

# Confluence Orchestrator

> Quản lý nội dung Confluence: tạo, cập nhật, copy, upload, đồng bộ.

## Phạm vi
- Tạo/cập nhật trang Confluence.
- Copy cây trang, upload file.
- Đồng bộ tài liệu markdown.

## CLI
```bash
vds-cli confluence --help
vds-cli confluence-cli --help
```

## Lệnh chính
| Lệnh | Mục đích | Flags |
|------|----------|-------|
| `create-page` | Tạo trang | `--space`, `--title` |
| `update-page` | Cập nhật trang | `--page-id` |
| `copy-tree` | Copy cây trang | `--src-page-id` |
| `upload-attachment` | Upload file | `--page-id`, `--file-path` |
| `get-page` | Lấy trang | `--page-id` |

## Related (Tiếng Anh)
- [jira-orchestrator.md](jira-orchestrator.md)
- [bitbucket-orchestrator.md](bitbucket-orchestrator.md)
