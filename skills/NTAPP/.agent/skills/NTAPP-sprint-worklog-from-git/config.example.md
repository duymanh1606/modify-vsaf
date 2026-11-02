# Mẫu config cho skill sprint-worklog-from-git
#
# File này CHỈ là mẫu. Copy thành `sprint-worklog.md` rồi điền giá trị của bạn.
# Skill dò `sprint-worklog.md` theo thứ tự:
#   1. thư mục hiện tại
#   2. thư mục skill này
#   3. ~/Documents/.env/sprint-worklog.md
#   4. ~/.sprint-worklog.md
#
# KHÔNG có config vẫn chạy được — skill sẽ tự dò rồi hỏi bạn.
# Config chỉ để nhớ câu trả lời, khỏi hỏi lại mỗi sprint.
#
# Cú pháp: mỗi mục là một header `# tên-mục`, bên dưới là các dòng giá trị.
# Dòng trống và dòng bắt đầu bằng `#` (ngoài header) đều bị bỏ qua.

# roots
# Các thư mục workspace chứa repo. Mỗi dòng một đường dẫn.
# Dùng dấu / kể cả trên Windows. Thư mục cha của cwd luôn được thêm tự động,
# không cần khai ở đây.
D:/work/repos
C:/Users/your_user/Documents/another-workspace

# identities
# Các git identity của BẠN (tên hoặc email), mỗi dòng một cái.
# Khai ở đây những identity mà `git config` KHÔNG trả về — ví dụ email cá nhân
# bạn từng dùng ở một số repo, hoặc identity từ máy cũ.
# Identity trong `git config --global` / `--local` được tự nhận, khỏi khai lại.
your_username
your_personal_email@example.com

# non-code-items
# Các dòng việc phi-code chèn sẵn đầu danh sách, ET để trống cho bạn tự điền.
# Chuỗi `<sprint>` sẽ được thay bằng mã sprint thật lúc chạy.
[Tên đội của bạn] Họp hành sprint <sprint>
Hỗ trợ support các hệ thống
