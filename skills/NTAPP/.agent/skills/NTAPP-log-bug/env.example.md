# Mẫu env.md cho nhánh "đẩy bug lên Jira" của skill NTAPP-log-bug
#
# KHÔNG commit env.md thật vào repo. File này chỉ là mẫu.
#
# Script `jira_bug.py` dò env.md theo thứ tự:
#   $NTAPP_JIRA_ENV -> ./env.md -> <skill-dir>/env.md -> ~/Documents/.env/env.md -> ~/env.md
# Hoặc truyền trực tiếp: python jira_bug.py --env "/duong/dan/env.md" probe --project KEY
#
# Block Jira = block có dòng header (bắt đầu bằng `#`) chứa chữ "jira".
# Base URL lấy theo thứ tự: --url > dòng `JIRA_URL=` > URL nằm trong header của block.
# Trong block đó dùng Username + Pass (basic auth) HOẶC token (Personal Access Token -> Bearer).

## http://jira.example.com/:
Username: your_jira_user
Pass: your_jira_password
# token: your_personal_access_token     (tuỳ chọn — có token thì không cần Username/Pass)

# (tuỳ chọn) override base URL nếu header không chứa URL
# JIRA_URL=http://jira.example.com
