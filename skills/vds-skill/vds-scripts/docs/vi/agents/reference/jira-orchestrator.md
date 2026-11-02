<!-- diátaxis: reference -->
<!-- lang: vi -->

# Jira Orchestrator

> Quản lý ticket Jira: tạo, cập nhật, truy vấn, chuyển trạng thái và comment.

## Phạm vi
- Truy vấn, tạo, cập nhật ticket Jira.
- Chuyển trạng thái và thêm ghi chú công việc.
- Tạo trang Confluence từ dữ liệu Epic.

## CLI
```bash
vds-cli jira --help
vds-cli jira-cli --help
```

## Lệnh chính
| Lệnh | Mục đích | Flags |
|------|----------|-------|
| `get-issue` | Lấy ticket | `--issue` |
| `search-issues` | Tìm kiếm JQL | `--jql` |
| `create-issue` | Tạo ticket | `--project`, `--summary` |
| `update-issue` | Cập nhật ticket | `--issue` |
| `transition-issue` | Chuyển trạng thái | `--issue` |
| `add-comment` | Thêm comment | `--issue`, `--text` |

## Related (Tiếng Anh)
- [confluence-orchestrator.md](confluence-orchestrator.md)
- [bitbucket-orchestrator.md](bitbucket-orchestrator.md)
- [spec-orchestrator.md](spec-orchestrator.md)
