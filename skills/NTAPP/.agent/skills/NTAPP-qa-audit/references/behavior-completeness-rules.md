# Behavior & Completeness Gap Rules

Nhóm "hành vi / độ phủ" — chạy ĐỦ; im lặng / không tất định → GAP + `[TBD]`.

---

## 1. Cross-System State-Sync Gap

**Cross-System State-Sync Gaps (BẮT BUỘC khi trạng thái tài nguyên đọc ở một thời điểm rồi bị hành động ở thời điểm khác, hoặc đồng bộ bất đồng bộ giữa nhiều hệ thống):** Rà soát và cờ MỌI điểm sau, đối chiếu xuyên nguồn (phần Logic/sequence ↔ techspec ↔ Module 0 state registry/cache/event contract):

1. **Revalidate tại thời điểm ghi (TOCTOU):** giữa lúc đọc list/cache và lúc submit/bind/duyệt, trạng thái tài nguyên có thể đã đổi ở hệ nguồn — spec có bắt buộc **đọc lại trạng thái hiện tại trước khi ghi** không? Nếu tài nguyên không còn ở trạng thái hợp lệ mà vẫn cho tạo/bind = gap.
2. **Cửa sổ stale (cache TTL / list read-only):** dữ liệu trạng thái phục vụ hành động có đến từ cache có TTL / list không refresh không? Bao lâu? Trong cửa sổ đó hành động dựa trên trạng thái cũ được xử lý ra sao.
3. **Event-before-entity + đồng bộ lỡ:** event/callback đồng bộ trạng thái có thể đến **trước khi bản ghi đích tồn tại** (hoặc bị nuốt/ACK) → spec có backfill/reload/đối soát (reconciliation) để không mất trạng thái vĩnh viễn không? Thiếu đường phục hồi = gap.
4. **Snapshot vs source-of-truth:** trạng thái có bị copy/denormalize/seed cứng vào bản ghi local lúc tạo thay vì đọc live không? Sau khi nguồn đổi, giá trị local có được đồng bộ về khớp nguồn không.
5. **Terminal/ineligible state + state machine:** tài nguyên ở trạng thái kết thúc/không hợp lệ (đã duyệt/từ chối/hủy/hết hạn) có bị đưa vào luồng giả định trạng thái trước đó (double-process) không.

Mức mặc định **≥🟡**; lên **🔴** nếu làm "Kết quả mong muốn" mơ hồ, khiến trạng thái local lệch nguồn mà không tự sửa, hoặc gây double-process. KHÔNG gộp các điểm khác bản chất (TOCTOU / stale-cache / event-before-entity / snapshot-drift) thành một gap.

---

## 2. List/Collection Display Completeness

**List/collection display completeness (BẮT BUỘC cho MỖI màn danh sách / bảng / collection):** Chốt và đối chiếu xuyên nguồn (phần Giao diện ↔ techspec/API ↔ Module 0), cờ MỌI mâu thuẫn:

1. **Bao nhiêu bản ghi hiển thị** trên màn — page size cụ thể / giới hạn cứng / "hiển thị tất cả"; nguồn nào ghi số mấy (vd phần Giao diện nói 20/trang vs techspec nói 50).
2. **Điều kiện hiển thị / lọc mặc định** — status nào được liệt, cửa sổ thời gian mặc định, data-scope (partner/role), record nào bị ẩn. **Record thoả điều kiện nhưng không hiện = gap** (và ngược lại).
3. **Cơ chế tải thêm** — **phân trang** (page size, sort key/hướng, tổng số) **vs infinite/virtual scroll vs "scroll đến hết"**; và hành vi ở biên: **vượt trang cuối**, **danh sách rỗng** (empty-state vs 404), **đang tải**. Nguồn khác nhau chọn cơ chế khác nhau = gap.
4. **Count-consistency** — số ở badge/tổng ("(N)", "totalElements", tab count) phải **khớp số dòng thực tế + khớp tiêu chí lọc đang áp**. Lệch = gap (dễ lọt bug thật).
5. **Volume boundary** — phải phủ ca **0 / 1 / đúng 1 trang / tràn trang / rất lớn** khi viết testcase; nếu spec không nói giới hạn trên → `[TBD]`.

Mức mặc định **≥🟡**; lên **🔴** nếu làm "Kết quả mong muốn" của tiêu chí "thấy đủ/đúng danh sách" mơ hồ hoặc chặn demo.

---

## 3. Field-Level Expectation Gate

Với **mỗi trường nhập / tham số** và **mỗi cột hiển thị**, soi các câu dưới. Mức `≥🟡`; lên `🔴` nếu làm expected mơ hồ, hoặc là lỗ hổng bảo mật / sai tiền.

1. **Validation input (gọn):** hoa/thường, khoảng trắng, trống–rỗng–không nhập, ký tự đặc biệt → xử lý ra sao? *(chi tiết ở Contradiction & Core Gaps — Parameter Gaps.)*
2. **So khớp hoa/thường khi lọc:** gõ HOA mà dữ liệu lưu thường → lọc còn ra kết quả không?
3. **Tie-break:** cùng khóa sắp xếp thì dòng nào lên trước?
4. **Chuẩn hóa nhiều nguồn:** định dạng / múi giờ / đơn vị khác nhau có quy về một chuẩn không?
5. **Phân quyền theo vai trò:** vai trò nào được thao tác / xem?
6. **Phân quyền theo phạm vi dữ liệu (IDOR):** cùng vai trò, user có chỉ thấy dữ liệu của mình không?
7. **Đồng thời (lost update):** 2 người sửa cùng 1 bản ghi → có khóa version / atomic không?
