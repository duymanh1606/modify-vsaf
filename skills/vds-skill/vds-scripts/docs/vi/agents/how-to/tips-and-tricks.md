---
diátaxis: how-to
audience: human
complexity: basic
last_updated: 2026-04-30
phase_ref: 180
language: vi
---

# Mẹo & Thủ thuật

## Shell tải nhanh từ thư mục làm việc

```bash
./scripts/worktree_uv.sh
```

Chạy lệnh trong môi trường uv từ worktree hiện tại mà không cần cd.

## Di chuyển giữa worktree

```bash
vds-cli worktree list
vds-cli worktree switch <branch>
```

## Quản lý mật khẩu

Lưu trữ tất cả bí mật trong `~/.vds/.env`. Không bao giờ commit bí mật.

## Xem thêm

- Tiếng Anh: [tips-and-tricks.md](../../agents/how-to/tips-and-tricks.md)
- [Hệ sinh thái WHO](../../explanation/who-ecosystem-introduction.md)
