# STEP 01: TEST DATA & ENVIRONMENT SETUP

> **Acting as:** [Agent Robot Generator](../agents/agent_robot_generator.md)
> **Tuân thủ:** [Robot Rules](../references/auto_robot_rules.md) (§2 Test Data Management, §4 Anti-Patterns — Zero-Fabrication + isolation), [Automation Standards](../references/automation_standards.md).

**Nhiệm vụ:**
Phân tích yêu cầu dữ liệu mồi từ kịch bản kiểm thử Manual (10 cột) và thiết kế hệ thống Dữ liệu Mồi (Test Data) độc lập, có thể tái sử dụng để chuẩn bị cho quá trình chạy Kiểm thử tự động (Automation).

## 1. Input Required
- File kịch bản kiểm thử thủ công (Ví dụ: `{id}_detailed_test_manual_testcase.md`).
- Các cấu trúc CSDL tham khảo (nếu có trong phần Dữ liệu của `_detailed_design`).

## 2. Process
**2.1. Phân tích Dữ liệu Mồi (Data Extraction):**
- Đọc cột "Data Test" và "Precondition" trong file kịch bản 10 cột.
- Bóc tách toàn bộ các thực thể cần tạo trước khi chạy test (Ví dụ: Cần 1 User có role Admin, 1 User bị khóa, 1 Đơn hàng trạng thái Pending).
- Với MỖI thực thể, xác định rõ **điều kiện đầu vào (precondition)** cần khớp: thuộc tính định danh + **trạng thái mục tiêu** (Ví dụ: role=`admin`, status=`active`; hoặc order.state=`Pending`). Đây là tiêu chí chấm reuse ở §2.2.

**2.2. Reuse-Gate — Check-Before-Create (Get-Or-Create):**
> Mục tiêu: TRƯỚC khi sinh dữ liệu mới, tái sử dụng dữ liệu automation đã có nếu còn thỏa điều kiện — tiết kiệm thời gian, giữ Setup idempotent. Marker `auto` chỉ để khoanh vùng dữ liệu automation-owned, KHÔNG bao giờ đụng dữ liệu thật/manual.

Với mỗi thực thể ở §2.1, thiết kế bước kiểm tra tái sử dụng (chạy lúc runtime, trước bước CREATE):

1. **Query 5 bản ghi gần nhất mang tiền tố `auto_`:** lọc theo marker automation trên trường định danh (email/username/name/code **bắt đầu bằng** `auto_`, ví dụ `auto_admin_{timestamp}@test.com`), sắp xếp theo thời điểm tạo giảm dần, lấy **TOP 5**.
   - Override qua `AUTO_DATA_PREFIX` (default `auto_`). Dùng tiền tố để `LIKE 'auto\_%'` khoanh trọn dữ liệu automation-owned, không bắt nhầm dữ liệu thật chứa từ "auto".
2. **Chấm điều kiện:** với từng candidate trong 5 bản, đối chiếu **trạng thái + thuộc tính** với precondition ở §2.1.
   - THỎA = tất cả thuộc tính bắt buộc + trạng thái mục tiêu khớp, và bản ghi còn dùng được (chưa bị khóa/xóa ngoài ý muốn).
3. **Quyết định (không hỏi user):**
   - **Có ≥1 bản THỎA** → **REUSE**: chọn bản gần nhất (mới nhất) trong các bản thỏa; ghi lại định danh của nó làm seed cho thực thể này; **SKIP create**. KHÔNG đưa bản kế thừa này vào Teardown (không phải do run hiện tại tạo).
   - **Không bản nào trong 5 THỎA (hoặc query rỗng / không query được)** → **CREATE mới ngay** (rẽ sang §2.3), bản mới BẮT BUỘC mang tiền tố `auto_` ở đầu định danh để các run sau tìm lại được.
4. **Zero-fabrication:** chỉ chấm dựa trên dữ liệu THỰC SỰ query được — KHÔNG giả định bản ghi tồn tại. Không có kênh query lúc runtime → mặc định rẽ nhánh CREATE.

**2.3. Thiết kế Cơ chế Setup (Pre-condition):**
- Viết kịch bản sinh dữ liệu (Data Generation Script) dạng SQL Insert hoặc API Post tương ứng — **chỉ cho các thực thể rơi vào nhánh CREATE ở §2.2** (thực thể REUSE bỏ qua).
- Gói theo pattern **Get-Or-Create**: query-reuse (§2.2) → nếu miss thì create. Không tạo mù.
- Đảm bảo tính duy nhất của dữ liệu (Ví dụ: Dùng timestamp hoặc UUID cho Email/Số điện thoại để tránh lỗi Duplicate Entry), đồng thời **đặt tiền tố `auto_` ở ĐẦU** trường định danh kiểu chuỗi (ví dụ `auto_admin_{timestamp}@test.com`). **Trường chỉ nhận số** (số điện thoại, mã số thuế, số tài khoản) KHÔNG gắn tiền tố — giữ đúng định dạng số, unique bằng phần số ngẫu nhiên; ghi vào mục miễn trừ của file output.

**2.4. Thiết kế Cơ chế Teardown (Post-condition):**
- Viết kịch bản dọn dẹp dữ liệu (Clean Data Script) dạng SQL Delete hoặc API Delete để xóa **các bản ghi do run hiện tại tạo** (nhánh CREATE) sau khi test xong.
- KHÔNG teardown bản ghi REUSE kế thừa (tránh xóa nhầm data còn dùng cho run khác).
- Đảm bảo môi trường hoàn toàn sạch sẽ (Clean State) cho lần chạy Automation tiếp theo.

## 3. Output Format
Tạo file `{id}_test_data_setup.md` hoặc `{id}_test_data.sql` lưu vào `{qa_artifacts}/data/`.

```markdown
# Kịch bản Setup Test Data: {id}

## 1. Danh sách Dữ liệu Mồi (Entities) + Precondition
| Entity | Precondition (thuộc tính + trạng thái) | Định danh (tiền tố `auto_`) |
|---|---|---|
| User A | role=admin, status=active | `auto_admin_{timestamp}@test.com` |
| User B | status=locked | `auto_locked_{timestamp}@test.com` |

## 2. Reuse-Gate (Check-Before-Create)
Với mỗi entity: query 5 bản ghi `auto_` gần nhất → chấm trạng thái so với precondition → REUSE hoặc CREATE.

```sql
-- Ví dụ query reuse cho User A: 5 bản automation gần nhất + trạng thái
SELECT id, email, role, status, created_at
FROM users
WHERE email LIKE 'auto\_%'           -- tien to automation-owned (AUTO_DATA_PREFIX)
ORDER BY created_at DESC
LIMIT 5;
-- Nếu tồn tại bản role='admin' AND status='active' → REUSE id đó, SKIP create.
-- Nếu không có bản nào thỏa trong 5 bản → chạy Setup §3 (CREATE) ngay.
```

## 3. Setup Scripts (Pre-condition — chỉ nhánh CREATE)
```sql
-- Chỉ chèn khi Reuse-Gate không tìm được bản thỏa (Get-Or-Create)
INSERT INTO users (email, role, status)
VALUES ('auto_admin_{timestamp}@test.com', 'admin', 'active');
```

## 4. Teardown Scripts (Post-condition — chỉ bản do run tạo)
```sql
-- Chỉ dọn bản CREATE trong run này (giữ nguyên bản REUSE kế thừa)
DELETE FROM users WHERE email = 'auto_admin_{timestamp}@test.com';
```
```
