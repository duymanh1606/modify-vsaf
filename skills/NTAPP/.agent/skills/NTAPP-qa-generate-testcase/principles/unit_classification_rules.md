# UNIT CLASSIFICATION & SCOPE RULES — Phân loại Unit + Kiểm soát phạm vi SLICE

> **Mục đích:** Quy định cách phân loại các Unit, sắp xếp thứ tự luồng E2E, **và giới hạn phạm vi kiểm thử** trong file SLICE (§4).
>
> **Phạm vi bề mặt:** File này áp cho bề mặt **`ui`** (unit có màn hình — nhãn Action/Verify/Nav). Với bề mặt **`service`** (không giao diện: API/service/job/consumer) dùng bộ nhãn `[Operation]`/`[Effect]`/`[Downstream]` tại [service_surface_rules.md §1](./service_surface_rules.md) — KHÔNG áp §2 dưới đây.
>
> **⚠️ Áp dụng theo lane (từ Step 00):** File này chủ yếu cho lane `slice` (nhiều unit). **Lane `unit`** — chỉ có MỘT đơn vị `{id}`: **BỎ QUA §1 (khảo sát nhiều unit) và §3 (xếp thứ tự E2E liên-unit)**; §2 rút gọn (unit `{id}` mặc định `[Action]`); §4 phạm vi thu về chính `{id}` (mọi màn/logic ngoài `{id}` là "Out of scope").

---

## 1. Khảo sát Unit *(lane `slice`)*
- Đọc danh sách `units` trong file SLICE (`{slices_root}/{id}-*.md`).
- Đếm số lượng các Frontend Unit (bao gồm cả `SCR-` và `WGT-`). Cần đảm bảo Danh sách luồng E2E và Bảng Mapping liệt kê đầy đủ số lượng này, không được gộp chung các unit với nhau.
- **[BẮT BUỘC ĐỐI CHIẾU PHẠM VI]:** Thực hiện đối chiếu phạm vi của tất cả Frontend và Backend Unit với mảng `units` của file SLICE và tuân thủ nguyên tắc giới hạn tại **§4** bên dưới.

## 2. Đọc hiểu & Phân loại Unit
- Dùng `view_file` đọc phần Tổng quan trong `_detailed_design` của **tất cả** Frontend Unit để nắm mục đích nghiệp vụ.
- **[PHÂN LOẠI BẮT BUỘC]:** Đánh nhãn từng Frontend Unit thành 1 trong 3 loại:
  - `[Action]` (Màn hành động chính): Chạy đầy đủ vòng lặp **Step 02 → Step 03**.
  - `[Verify]` (Màn xác nhận kết quả): Xuất hiện sau khi submit để xác nhận (vd: hiển thị trên list). **KHÔNG chạy Step 02-03**; embed kết quả verify vào testcase của màn `[Action]` trước đó.
  - `[Nav]` (điều hướng thuần — `WGT-`, **hoặc `SCR-` khi là màn host của bề mặt mượn**): Không own logic riêng của slice này. **KHÔNG chạy Step 02-03**; đưa vào Precondition. Vẫn phải dùng `list_dir` để liệt kê tài liệu (`_detailed_design`) của Unit này, nếu thiếu phải thông báo rõ.
  - `[Delta Action]` (cụm hành động của slice chạy trên màn host của slice khác — **bề mặt mượn**): bề mặt test là **CỤM** (nút/modal/banner), KHÔNG phải màn. Chạy đầy đủ Step 02 → Step 03 cho cụm; màn host là `[Nav]`. Luật: [borrowed_surface_rules.md](./borrowed_surface_rules.md).
  - **[CONTEXTUAL ROLE SHIFT]:** Nếu một Unit đóng vai trò hỗn hợp (vừa là màn xem danh sách `[Verify]` nhưng lại có chứa các tính năng tương tác độc lập như bộ lọc, phân trang, hoặc hành động riêng biệt), bắt buộc phải đánh nhãn kết hợp là `[Action / Verify]` để vừa đóng vai trò màn kiểm chứng kết quả của màn trước, vừa chạy đầy đủ Step 02 → Step 03 cho phần logic độc lập của chính nó (nhận diện qua việc đọc phần Tổng quan trong `_detailed_design`).

## 3. Xác định Thứ tự E2E & Mapping Backend *(lane `slice` — lane `unit` bỏ qua)*
- **[ORDERING RULE]:** Dựa vào chuỗi `demoable` trong file SLICE, xếp các unit `[Action]` và `[Verify]` theo đúng **chuỗi hành động**. TUYỆT ĐỐI KHÔNG suy diễn thứ tự dựa trên luồng UX Navigation (vd: Cấm xếp A trước B chỉ vì A có nút mở B, nếu A là màn xem kết quả còn B là màn tạo).
- **[BẮT BUỘC KHỚP MÀN HÌNH ĐÍCH TỪ DEMOABLE]**: Phải phân tích từng bước chuyển hướng ký hiệu bằng mũi tên "→" trong chuỗi "demoable" của file SLICE. Ví dụ: "tạo composite → thấy nó trong list" nghĩa là màn hình danh sách (SCR-COMPOSITE-LIST) bắt buộc phải được khai báo là Màn hình đích (Target Screen) của màn hình tạo (SCR-COMPOSE). Mọi màn hình đích xuất hiện trong chuỗi demoable phải được kiểm tra việc quay về/hiển thị dữ liệu thành công trong kịch bản kiểm thử của màn trước đó.
- Rà soát trường `story` trong file SLICE: Gán Backend Unit cho Frontend Unit có chung chính xác Epic/Story code. Backend nào không map thì đưa vào nhóm "Background".

## 4. Kiểm soát phạm vi SLICE (Scope Boundary)

> Tránh AI đi lạc sang màn hình ngoài phạm vi Vertical Slice.

### 4.1 Đối chiếu phạm vi (Scope Checking)
*   **[BẮT BUỘC ĐỐI CHIẾU PHẠM VI]**: *(lane `slice`)* Đối chiếu trực tiếp ID của màn hình đích với danh sách `units` trong file mô tả SLICE (tìm file bắt đầu bằng `{id}` trong thư mục `{slices_root}`, ví dụ: `SLICE-06-composite-create-list.md`). *(lane `unit`: phạm vi = chính `{id}`; mọi màn/logic ngoài `{id}` là "Out of scope".)*
*   Nếu màn hình/unit đích KHÔNG nằm trong mảng `units` đó -> Bắt buộc gán nhãn `"Out of SLICE scope"` cho màn hình này.
*   Cấm tuyệt đối việc lập test plan độc lập (Step 02/03) cho màn hình ngoài phạm vi đó.

### 4.2 Kiểm thử hành động chuyển hướng (Redirection Verification)
*   Đối với màn hình hành động (Màn trước): Nếu hành động đó dẫn đến sự chuyển hướng sang màn hình đích nằm ngoài SLICE, kịch bản kiểm thử của màn trước **vẫn phải có bước kiểm tra việc chuyển hướng thành công** trong Kết quả mong muốn (UI).
    *   *Ví dụ:* Hiển thị thông báo toast success, hoặc URL trình duyệt thay đổi đúng địa chỉ màn hình đích.
*   **TUYỆT ĐỐI KHÔNG** đi sâu vào lập testcase kiểm tra chi tiết các UI control hay logic nội tại của màn hình đích ngoài phạm vi đó.

### 4.3 Bề mặt mượn (màn host của slice khác)

*   Màn được `## What to build`/`demoable` nêu nhưng KHÔNG có trong `units:` → `[Nav]` host, **không phải** `"Out of SLICE scope"`; bề mặt test là cụm hành động trên đó.
*   Màn host vào Precondition **đúng 1 dòng** (`Mở màn X thành công (đã có <state cần thiết>)`). **CẤM** case kiểm layout / bảng / tab / filter / empty-state của màn host.
*   Phạm vi liên-slice + Delta Manifest + override 9 chốt: [borrowed_surface_rules.md](./borrowed_surface_rules.md).

