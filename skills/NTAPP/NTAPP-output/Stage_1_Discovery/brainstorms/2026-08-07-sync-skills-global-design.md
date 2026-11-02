# Design: Skill đồng bộ skill NTAPP ra global (không cần clone thường trực)

**Ngày:** 2026-08-07
**Trạng thái:** Approved

## Vấn đề

`scripts/sync-skills-to-user.sh` đã đẩy được `.agent/skills/` + `rules/` của repo template
(`ntapp-vsaf-blended-template`) ra các thư mục skill/rule global (`~/.claude/skills`,
`~/.gemini/config/skills`, `~/.codeium/skills`, `~/.claude/rules`) — nhưng phải chạy tay
**từ trong repo template**. Muốn có một skill gọi được **từ bất kỳ project nào khác** để
tự lấy code mới nhất của repo template rồi chạy script sync đó, mà không bắt người dùng
phải giữ và quản lý một bản clone thường trực trên máy.

## Quyết định chính

1. **Ephemeral clone thay vì clone thường trực.** Mỗi lần skill chạy: tạo thư mục temp
   (`mktemp -d`) → `git clone --depth 1` repo template vào đó → chạy
   `scripts/sync-skills-to-user.sh` ngay trong temp dir → xóa temp dir (kể cả khi lỗi,
   qua `trap`). Loại bỏ hoàn toàn bài toán "skill ở project khác biết path repo template
   ở đâu trên máy" và bài toán "repo template có local changes/đang ở branch dở dang thì
   sao" — vì không có state nào tồn tại giữa các lần chạy.
2. **Luôn clone nhánh `main`**, bất kể máy đang đứng ở project/branch nào lúc gọi skill.
   Đảm bảo global luôn nhận bản đã merge/ổn định, không dính code cá nhân chưa xong.
3. **Không sửa `scripts/sync-skills-to-user.sh`.** Script này đã tự tính `REPO_ROOT` từ
   vị trí chính nó (`BASH_SOURCE`) nên chạy nguyên trạng từ temp dir vẫn đúng.
4. **URL Bitbucket hardcode có chủ đích** trong script bundle của skill mới — khác các
   skill portable khác của project, skill này vốn chỉ có ý nghĩa gắn với chính repo
   template này nên không áp nguyên tắc portable (không hardcode path) ở đây.

## Thiết kế

**File mới:** `.agent/skills/NTAPP-sync-skills-global/`
- `sync-global.sh` — bash script: mktemp → git clone --depth 1 --branch main --single-branch
  <bitbucket-url> <tmp> → `bash <tmp>/scripts/sync-skills-to-user.sh "$@"` (forward args) →
  cleanup qua trap.
- `SKILL.md` — frontmatter theo convention hiện có của project (`name`, `description`,
  `user-invocable: true`, `argument-hint`, `allowed-tools: [Bash]`), body hướng dẫn gọi
  `sync-global.sh` với `$ARGUMENTS`.

**Data flow:** user gọi `/NTAPP-sync-skills-global [flags]` từ project bất kỳ → skill chạy
`sync-global.sh` → clone tạm main → chạy sync script gốc (forward `--dry-run` / `--clean` /
`--skills-only` / `--rules-only`) → in output cho user → xóa temp.

**Error handling:** `set -euo pipefail` trong script; clone lỗi (mạng/quyền Bitbucket) →
dừng ngay, báo lỗi rõ, KHÔNG retry, KHÔNG tự fallback sang cách tải khác (vd zip). Vì
ephemeral nên không cần rollback state.

**Testing:** chạy `--dry-run` trước để xem trước không ghi gì; sau đó chạy thật và kiểm
tra `~/.claude/skills/NTAPP-sync-skills-global/` xuất hiện trên máy.

## Vòng lặp self-hosting (lưu ý một lần)

Lần đầu tiên, skill mới này phải được đẩy lên global **thủ công** bằng cách chạy
`./scripts/sync-skills-to-user.sh` ngay trong repo template hiện tại (giống mọi skill
khác của project). Từ sau đó, gọi lại chính `/NTAPP-sync-skills-global` từ project bất kỳ
sẽ tự cập nhật nó (và mọi skill khác) theo `main` mới nhất.

## Ngoài phạm vi (không làm)

- Không cache/tái sử dụng clone giữa các lần chạy (đã cân nhắc, user chọn ephemeral để
  tránh phải quản lý path/state).
- Không hỗ trợ pull nhánh khác `main`.
- Không tự động xử lý xác thực Bitbucket khác cách git đang dùng sẵn trên máy (credential
  helper hiện có của user).
