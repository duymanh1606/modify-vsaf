<!-- diátaxis: reference -->
<!-- lang: vi -->

# Bitbucket Orchestrator

> Tương tác Bitbucket: clone repo, đọc file, kiểm tra PR, chạy pipeline.

## Phạm vi
- Clone/mirror repository.
- Liệt kê branch, đọc nội dung file.
- Kiểm tra PR và trigger pipeline.

## CLI
```bash
vds-cli bitbucket --help
vds-cli bitbucket-cli --help
```

## Lệnh chính
| Lệnh | Mục đích | Flags |
|------|----------|-------|
| `clone` | Clone repo | `--repo`, `--branch` |
| `list-branches` | Liệt kê branch | `--repo` |
| `read-file` | Đọc file | `--repo`, `--path` |
| `list-prs` | Liệt kê PR | `--repo` |
| `trigger-pipeline` | Chạy pipeline | `--repo` |

## Related (Tiếng Anh)
- [git-orchestrator.md](git-orchestrator.md)
- [jira-orchestrator.md](jira-orchestrator.md)
