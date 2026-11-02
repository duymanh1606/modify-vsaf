# <PROJECT_NAME> — con trỏ tri thức cho agent

**Chỉ dẫn THẬT nằm ở `<output_folder>/.okf/index.md`** (bundle OKF, tự mô tả chính nó). File này chỉ là con trỏ — **đừng chép nội dung vào đây**; hướng dẫn nhân bản ra nhiều file là cách repo này đã phân kỳ một lần rồi.

Tìm bundle:
- **Spec repo:** `<output_folder>` khai trong `.bmm-config.yaml` (mặc định `NTAPP-output`).
- **Code repo:** đi qua `spec_repo_root` trong `.bmm-config.yaml` của repo này → `<spec_repo_root>/<output_folder>/.okf/index.md`. **Không hardcode đường dẫn.**
- Chưa có `.okf/` → chưa chiếu lần nào. Chạy `/NTAPP-okf-refresh`, đừng đoán.

## Giao thức 3 tầng

1. **Định hướng** — hai bước, đừng bỏ bước đầu:
   - `.okf/status.md` — **chọn loại**. Mục "Mỗi loại trả lời câu hỏi gì" liệt kê từng loại kèm số node và câu hỏi nó tồn tại để trả lời. Không đọc mục này thì cách duy nhất để chọn loại là mở thử rồi đoán.
   - `.okf/<type>/_index.md` — **chọn node** trong loại đó: mã, tiêu đề, chi phí đọc từng node. Máy sinh mỗi lượt chiếu.
2. **Duyệt** — lọc và đi theo cạnh bằng trường frontmatter (`implements`, `derives_from`, `governed_by`, `consumes`/`used_by`, `built_as`). Card ~300 token, thường trả lời thẳng được.
3. **Resolve** — chỉ khi card không đủ: theo `resource` + `anchor` vào master, đọc **nguyên văn**.

> **Ràng buộc bất di bất dịch:** node card là **chỉ mục truy hồi, KHÔNG BAO GIỜ là nguồn để viết**. Iron Rules R1/R2 cấm thay chi tiết nguồn bằng tóm tắt — mọi quyết định đặc tả/hợp đồng phải resolve về master và đọc nguyên văn ở tầng 3. Đồ thị thu hẹp **phạm vi** của một lần đọc nguyên văn, không thay thế nó bằng diễn giải.
>
> `content_sha` lệch hoặc `anchor` không resolve → node đã cũ. Báo ra và chạy `/NTAPP-okf-refresh`; không dùng card cũ để viết.
