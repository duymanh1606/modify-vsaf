# Robot Automation Standards (Facade)

Tài liệu này là Mục lục tiêu chuẩn dành cho việc Sinh mã nguồn Kiểm thử Tự động bằng Robot Framework.

Mọi Agent liên quan đến việc viết code Automation **bắt buộc** phải tuân thủ các quy định được định nghĩa chi tiết tại thư viện lõi:

1. **Coding Convention:** [auto_coding_convention.md](./auto_coding_convention.md)

2. **Framework Structure:** [auto_framework_structure.md](./auto_framework_structure.md)

3. **Locator Strategy:** [auto_locator_strategy.md](./auto_locator_strategy.md)

4. **Robot Rules:** [auto_robot_rules.md](./auto_robot_rules.md)

5. **DB Oracle Rules:** [auto_db_oracle_rules.md](./auto_db_oracle_rules.md) — wire tầng `@oracle:db` (query + assert thật thay stub `Verify DB`)

6. **Các phép kiểm bắt buộc:** [auto_gate_commands.md](./auto_gate_commands.md) — **bản DUY NHẤT**: mỗi phép kiểm ghi rõ *phải đúng gì · đọc file nào · dấu hiệu sai là gì · ghi bằng chứng thế nào* (chờ tĩnh/nhảy URL, lách bằng Python-JS, headless, mã trùng testcase tay, file test sạch, `[Template]`, nhãn phân loại, phân tầng POM, DRY). **Kiểm bằng ĐỌC CODE, không chạy lệnh.** Đọc ở **Step 02 + 03**; cấm copy sang file khác, cấm tự nới phạm vi.

*(Lưu ý cho AI Agent: Khi được yêu cầu sinh mã nguồn, bạn phải chủ động truy cập các link trên để đọc tiêu chuẩn trước khi viết code).*
