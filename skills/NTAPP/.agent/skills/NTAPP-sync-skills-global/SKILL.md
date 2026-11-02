---
name: NTAPP-sync-skills-global
description: Đồng bộ toàn bộ skill NTAPP + rule coding mới nhất (nhánh main trên Bitbucket) từ repo template ntapp-vsaf-blended-template ra global cho mọi công cụ (Claude Code ~/.claude/skills, Gemini ~/.gemini/config/skills, Antigravity ~/.codeium/skills) và ~/.claude/rules — KHÔNG cần clone/giữ bản project template trên máy, gọi được từ bất kỳ project nào. Use when the user says "đồng bộ skill global", "cập nhật skill từ bitbucket", "sync skill lên global", "pull skill mới nhất", "update skill toàn máy", "refresh global skill".
user-invocable: true
argument-hint: [--dry-run] [--clean] [--skills-only] [--rules-only]
allowed-tools: [Bash]
---

# /NTAPP-sync-skills-global — Đồng bộ skill + rule mới nhất ra global

## Arguments

`$ARGUMENTS` — optional, forward nguyên cho `scripts/sync-skills-to-user.sh` bên trong repo template:
- (không truyền gì) — sync đầy đủ skill + rule
- `--dry-run` — chỉ xem trước, không ghi gì
- `--clean` — xóa skill global đã bị gỡ khỏi nguồn
- `--skills-only` — chỉ đồng bộ skill, bỏ qua rule
- `--rules-only` — chỉ đồng bộ rule, bỏ qua skill

## Mục tiêu

Lấy code mới nhất (nhánh `main`) của repo template `ntapp-vsaf-blended-template` trên
Bitbucket, rồi đẩy `.agent/skills/` + `rules/` của nó ra các thư mục skill/rule global
trên máy — để mọi project khác dùng được skill/rule mới nhất mà không phải tự clone/pull
tay repo template.

> **Ephemeral — không cần clone thường trực.** Mỗi lần chạy sẽ clone tạm (`--depth 1`)
> vào thư mục temp, chạy sync, rồi tự xóa. Vì vậy gọi được từ project bất kỳ trên máy,
> không cần biết trước đường dẫn repo template nằm ở đâu.

## Cách chạy

Chạy script bundled kèm skill này, forward nguyên `$ARGUMENTS`:

```bash
bash "<thư mục skill này>/sync-global.sh" $ARGUMENTS
```

Sau khi chạy xong, in lại nguyên output của script cho người dùng thấy đã đồng bộ những
skill/rule nào (hoặc những gì sẽ đồng bộ, nếu `--dry-run`).

## Xử lý lỗi

Nếu `git clone` lỗi (mất mạng, không có quyền truy cập Bitbucket, sai VPN, ...) → báo lỗi
rõ ràng cho người dùng, DỪNG lại. KHÔNG tự retry, KHÔNG tự chuyển sang cách tải khác (vd
tải zip qua REST API).

## Important Constraints

- Luôn clone nhánh `main` — KHÔNG bao giờ đổi sang branch khác, kể cả khi máy đang đứng ở
  project/branch khác lúc gọi skill này. Global phải luôn nhận bản đã merge/ổn định.
- Ephemeral only — clone tạm ở `mktemp -d`, xóa ngay sau khi sync xong kể cả khi lỗi (qua
  `trap`). KHÔNG để lại clone nào trên máy sau khi chạy xong.
- KHÔNG sửa gì bên trong repo template — chỉ đọc và chạy script sync sẵn có của nó
  (`scripts/sync-skills-to-user.sh`), không tự ý thay đổi logic sync ở đây.
- URL Bitbucket hardcode trong `sync-global.sh` là chủ đích: khác các skill portable khác
  của project (không được hardcode path/thông tin cá nhân), skill này vốn chỉ có ý nghĩa
  gắn với chính repo template cụ thể này.
- **Vòng lặp self-hosting:** lần đầu tiên, skill này phải được đẩy lên global thủ công
  bằng cách chạy `./scripts/sync-skills-to-user.sh` ngay trong repo template (giống mọi
  skill khác của project). Từ sau đó, gọi lại `/NTAPP-sync-skills-global` từ project bất
  kỳ sẽ tự cập nhật nó (và mọi skill khác) theo `main` mới nhất.
