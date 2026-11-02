# Mẫu env.md cho skill jira-subtask-creator
#
# Script dò file env.md ở: thư mục hiện tại -> thư mục skill -> ~/Documents/.env/env.md -> ~/env.md
# Hoặc truyền trực tiếp: python jira_subtask.py --env "C:\duong\dan\env.md" ...
#
# Block Jira được nhận diện qua header có chứa URL "jira.digital.vn".
# Trong block đó, script đọc Username + Pass (basic auth) HOẶC token (Personal Access Token -> Bearer).

# http://jira.digital.vn/:
Username: your_jira_user
Pass: your_jira_password
# token: <PAT>            # (tuỳ chọn) nếu dùng Personal Access Token thì khỏi cần Username/Pass

# (tuỳ chọn) override base URL nếu khác mặc định http://jira.digital.vn
# JIRA_URL=http://jira.digital.vn
