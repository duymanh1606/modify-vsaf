<!-- diátaxis: reference -->
<!-- lang: vi -->

# Git Orchestrator

> Quản lý git operations: worktree, branch, log, merge, cherry-pick.

## Phạm vi
- Quản lý git worktrees.
- Kiểm tra branch, status, log.
- Rebase, cherry-pick, merge.

## CLI
```bash
vds-cli git --help
vds-cli git-orchestrator --help
```

## Lệnh chính
| Lệnh | Mục đích | Flags |
|------|----------|-------|
| `worktree-create` | Tạo worktree | `--branch`, `--path` |
| `worktree-list` | Liệt kê worktrees | `--repo` |
| `branch` | Quản lý branch | `--name` |
| `status` | Kiểm tra status | `--repo` |
| `log` | Xem commit log | `--limit` |
| `merge` | Merge branch | `--branch` |

## Related (Tiếng Anh)
- [bitbucket-orchestrator.md](bitbucket-orchestrator.md)
- [git-worktree-skill](../../../../vds-skills/skills/git-worktree-skill/SKILL.md)
