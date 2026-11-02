# EXPLORE & CONSISTENCY RULES — Bắt bug hay lọt (School B)

> **Mục đích:** Đóng 3 lỗ hổng khiến bug tất định vẫn lọt qua automation dù skill đã có rule:
> (1) oracle chỉ *xác nhận happy-path* thay vì *phủ định bất biến*; (2) sàn integration `§6.2` không được áp đủ mọi bề mặt; (3) case bị đẩy `exploratory` vì spec gap rồi biến mất khỏi coverage.
> Cộng thêm 2 họ charter cho vùng automation vốn mù: so sánh giao diện + thao tác linh hoạt.
>
> **Nạp ở:** [step-02b](../steps/step-02b-risk-allocation.md) (Surface Invariant Gate + TBD-escape) · [step-04](../steps/step-04-finalize-testcase.md) (CH-CMP + CH-FLEX + coverage-debt).
> **Không nới** Iron Rules / Math Check — đây là lớp ép độ sâu oracle chồng lên [risk_based_allocation §6.2](./risk_based_allocation_rules.md), không thay thế.

---

## 1. Nguyên lý cốt lõi — Oracle phủ định bất biến (falsifying oracle)

> Automation chỉ "thấy" bug khi có ORACLE tường minh để assert, VÀ testcase gõ đúng input kích hoạt bug. Oracle happy-path ("list có row = pass") mù với đa số bug tích hợp.

**Đổi tư duy oracle:**

| Kiểu oracle | Câu hỏi oracle | Ví dụ (search) | Bắt bug? |
|---|---|---|---|
| ❌ Xác nhận (confirming) | "Có chạy không?" | list ≠ rỗng sau khi search | Không — trả ALL vẫn ≠ rỗng |
| ✅ Phủ định bất biến (falsifying) | "Có sai bất biến nào không?" | `count==kỳ vọng` **VÀ** mọi row khớp filter **VÀ** row không khớp vắng mặt | Có |

**2 điều kiện bắt buộc để oracle phủ định chạy được (ghi vào cột *Data test* + *Kết quả mong muốn*):**
1. **Data đối nghịch (adversarial seed):** cấm chỉ seed data đẹp (1 bản ghi, giá trị hợp lệ). Phải seed data *cố ý phá bất biến* — bản ghi không khớp filter, số lượng vượt page size, principal khác chủ sở hữu, giá trị biên vượt mốc.
2. **Kết quả mong muốn định lượng:** cấm "hiển thị đúng"/"theo thiết kế" (xem [expected-result no-vague — memory feedback]); phải nêu **con số + điều kiện phủ định** (vd "đúng 1 bản ghi, 2 bản ghi kia KHÔNG xuất hiện"). Spec im lặng → `[TBD]` + Q&A, không bịa.

---

## 2. SURFACE INVARIANT GATE (gate cứng — biến §6.2 thành checklist per-surface)

> Đây là **forcing function**: sàn `§6.2` hiện là văn mô tả nên agent hay bỏ. Gate này liệt kê MỌI bề mặt trong slice và ép mỗi bề mặt tick đủ bất biến bắt buộc. Thiếu 1 bề mặt × bất biến → **phải bổ sung case** (hoặc TBD-escape §3 nếu chặn vì spec gap) **trước khi sang Step 03** — không tự động cắt.

### 2.1 Bước 1 — Lập Surface Inventory (bắt buộc, ghi vào `implementation_plan.md`)

Quét toàn slice, liệt kê mọi bề mặt thuộc các loại dưới. Mỗi bề mặt = 1 dòng inventory:

> **Bề mặt mượn ([borrowed_surface_rules.md](./borrowed_surface_rules.md)):** chỉ liệt kê bề mặt **do cụm delta tạo/chạm**. Bề mặt thuộc màn host (grid/tab/filter/paging/empty-state) ghi 1 dòng `OUT — host {slice}`, KHÔNG tick bất biến, KHÔNG sinh case.

| Loại bề mặt | Nhận diện | Bất biến BẮT BUỘC | Data đối nghịch phải seed | Rule nguồn |
|---|---|---|---|---|
| **Search/Filter** | ô lọc gọi API trả danh sách | **filter-correctness:** mọi row khớp điều kiện; row không khớp vắng mặt; `count==kỳ vọng` | ≥1 bản ghi KHỚP + ≥2 bản ghi KHÔNG khớp (khác field, khác giá trị) | [11-independent-filter](../references/kbkt-generation/11-independent-filter/independent-filter-rule.md) · §6.2 |
| **List/Grid/Panel** | bảng/panel hiển thị nhiều bản ghi | **volume-boundary:** count > page size + > default framework hiển thị/phân trang đủ, KHÔNG im lặng cắt | seed **> page size** (vd 25 khi page=20; 11 khi cap nghi ngờ=10) | [09-data-grid](../references/kbkt-generation/09-data-grid/grid-base-rule.md) · §6.2 |
| **Có phân quyền/scope** | dữ liệu lọc theo role/owner | **cross-actor visibility:** ≥2 principal; phạm vi thấy đúng scope; principal A không thấy/thấy của B đúng luật | seed data của ≥2 owner/role, login lần lượt | [10-be/data-visibility](../references/kbkt-generation/10-be/data-visibility-rule.md) · §6.2 |
| **Action ghi (create/update)** | nút Lưu/Tạo gọi API ghi | **error-side-effect:** mỗi mã lỗi → 1 hành vi UI đúng; **đúng SỐ toast** (assert `count(error)==1`); DB side-effect khớp (0 row khi lỗi) | tái lập từng nhánh lỗi: duplicate/conflict (409), validation (400/422) | [error-response-behavior](../references/kbkt-generation/06-validation/error-response-behavior-rule.md) · [duplicate-data](../references/kbkt-generation/06-validation/duplicate-data-rule.md) |
| **Filter + list cùng màn** | search rồi có nút clear/reset | **stale-state:** sau clear/đổi filter/xóa bản ghi → list về trạng thái xác định (theo spec), KHÔNG đứng yên stale | search ra kết quả → clear → quan sát; xóa 1 bản ghi đang hiển thị | [11-independent-filter](../references/kbkt-generation/11-independent-filter/independent-filter-rule.md) · §6.2 |
| **Dependent select** | chọn cha (Merchant/LHKD) → tải con (Product) | **dependent-reset:** đổi cha SAU khi chọn con → con reset, không còn giá trị mồ côi | chọn con → đổi cha → assert con reset | [dependent-combobox](../references/kbkt-generation/03-selection/dependent-combobox-rule.md) |
| **Field có maxlength** | input có giới hạn độ dài | **attr-vs-spec consistency:** attr DOM `maxlength` == mốc spec; over-limit tại mốc spec | đọc attr + gõ `spec_max+1` | [maxlength-rule](../references/kbkt-generation/02-input/maxlength-rule.md) |

### 2.2 Bước 2 — Đối soát gate

- Mỗi bề mặt trong inventory PHẢI có ≥1 case scripted (`@exec:automate`, hoặc `manual` nếu oracle không tự động được) cho **từng** bất biến bắt buộc của loại đó. Không có bề mặt nào chỉ có case happy-path.
- **CẤM** thay bất biến integration bằng 1 case oracle nông ("list hiển thị"/"không rỗng") — vi phạm §6.2.
- In bảng đối soát ra chat: `<bề mặt> × <bất biến> → <@id case | THIẾU>`. Còn ô `THIẾU` → gate FAIL, bổ sung case rồi mới sang Step 03.

---

## 3. TBD-ESCAPE GUARD (case gap spec không được bốc hơi khỏi coverage)

> Lỗ to nhất: khi spec còn `[TBD]`/GAP, agent hạ case xuống `@exec:exploratory` rồi nó biến mất khỏi automation — mà đó đúng là chỗ dev code sai nhiều nhất.

Khi một case thuộc **bất biến bắt buộc §2** bị chặn vì spec gap:

1. **CẤM** xoá case hoặc hạ xuống `@exec:exploratory` cho biến mất khỏi coverage.
2. **Viết case scripted** (`@exec:automate`, hoặc `manual` nếu oracle không tự động được) **ngay trong KHỐI 2/3**, với **expected neo theo contract canonical** — đánh dấu `[BR]`/`[BugRecheck]` (case hiện FAIL tới khi code đạt contract). Nếu contract cũng chưa chốt → ghi `[TBD]` ở cột Kết quả mong muốn. Kèm **BẮT BUỘC**:
   - 1 mục Q&A blocking trong qa-report (spec/contract phải chốt),
   - 1 dòng trong **Coverage Debt Ledger** (Mục 5.6) đánh dấu bất biến đang nợ + gap-id.
3. Khi gap/contract được chốt (round-trip) → gỡ `[BR]`/`[TBD]`, xoá dòng nợ tương ứng.
4. **Coverage Debt Ledger là bắt buộc in ra chat ở Step 04** — user thấy rõ "bất biến X của bề mặt Y đang nợ vì GAP-Z", không bị ru ngủ bởi màu xanh automation.

> Pattern chuẩn: dòng `[BR]` scripted trong KHỐI 2/3 (vd `... → 400 BMS_HUB_033 [BR] (code hiện tạo rỗng)`), KHÔNG phải charter exploratory tách rời.

---

## 4. CH-CMP — Charter so sánh giao diện màn tương đồng (chỉ giao diện cơ bản, trong slice)

> Phạm vi hẹp có chủ đích: chỉ soi **khác biệt giao diện cơ bản** giữa các màn/widget tương đồng TRONG slice — KHÔNG đi sâu logic. Bắt lớp bug "empty-state thiếu nút", "màu/label nút lệch", "message không nhất quán".

**Kích hoạt:** slice có ≥2 màn/widget tương đồng (Create vs Edit; nhiều màn list anh em; cùng 1 widget lặp ở >1 màn; cùng 1 loại trạng thái xuất hiện ở nhiều nơi).

**Ma trận so sánh — chỉ các chiều giao diện cơ bản:**

| Chiều so sánh | Hỏi gì |
|---|---|
| Empty-state | Không có bản ghi thì hiển thị thế nào — có/thiếu nút CTA ("Tạo mới"), text, illustration; các màn có nhất quán không |
| Nút hành động | Màu, kiểu (primary/secondary), label, vị trí, trạng thái disabled của nút cùng vai trò |
| Thông báo | Style + nội dung toast/inline lỗi/thành công; message có đúng label field của chính nó không (sai kiểu "Mã sản phẩm" trên field "Mã merchant") |
| Layout | Bố cục tiêu đề/filter/bảng; spacing; breadcrumb |
| Loading/disabled | Trạng thái chờ + disabled khi request đang chạy |

Mỗi chiều so sánh phát hiện khác biệt cần kiểm → viết thành **case scripted trong KHỐI 1/2** với oracle định lượng (vd "empty-state màn A và màn B đều có nút CTA cùng label X"; "toast lỗi field Mã merchant hiển thị đúng tên field của nó, không phải 'Mã sản phẩm'"). Chỉ so-màu/spacing thuần không assert được thì để `@exec:manual` trong KHỐI 1 UI. **KHÔNG** tách charter CH-CMP riêng.

---

## 5. FLEX — Thao tác linh hoạt / case lạ → SCRIPTED trong KHỐI 2/3

> Chuỗi thao tác bất thường/timing. **Nguyên tắc mới: gần như TẤT CẢ đều deterministic → viết thành case scripted trong KHỐI 2 (Functional/E2E resilience) hoặc KHỐI 3 (Security), KHÔNG tách charter.** Với mỗi heuristic, hỏi "oracle xác định là gì?" — hầu hết có (đúng số bản ghi, mã HTTP, banner/header). Chỉ khi sau phân tích vẫn KHÔNG có oracle nào assert được (thuần cảm nhận timing/mắt người) mới để `@exec:manual`; tuyệt đối không sinh `@exec:exploratory` section riêng.

**Catalog heuristic (lọc theo control thực tế của slice, mỗi mục khớp → ≥1 case scripted với oracle bên phải):**

| Heuristic | Case lạ ví dụ | Rủi ro săn |
|---|---|---|
| Đổi ngữ cảnh cha sau khi thao tác con | Đổi Merchant sau khi đã chọn Product/sub-link | giá trị mồ côi, con không reset |
| Ngắt giữa chừng request | Refresh/đóng tab/back khi request đang xử lý (loading) | double-submit, state treo, dữ liệu mất |
| Đa tab / đa phiên trình duyệt | Mở cùng flow trên 2 tab trình duyệt, thao tác song song | stale state, ghi đè, thiếu optimistic-lock |
| Chuyển tab trong màn (in-page tab) qua lại nhanh | Chức năng có ≥2 tab: click liên tục qua lại giữa các tab nhiều lần | **tab kẹt/không click được nữa** (mất event listener), nội dung tab không đổi hoặc còn sót của tab trước, request tab cũ ghi đè tab mới (race), state/dữ liệu đang nhập của tab bị reset ngoài ý muốn, gọi lại API mỗi lần switch (không cache) |
| Thao tác sai thứ tự | Bấm Lưu trước khi điền; submit khi form chưa hợp lệ (bật nút qua devtools) | bypass validation FE |
| Double / rapid click | Bấm Lưu/Tạo nhiều lần nhanh | tạo trùng bản ghi |
| Back/forward trình duyệt | Điều hướng giữa các bước wizard | resubmit, dữ liệu bước trước còn/mất |
| Session/timeout | Idle hết phiên rồi thao tác tiếp | lỗi không thân thiện, mất data đang nhập |
| Mạng chập chờn | Throttle/offline giữa flow | UI không phản hồi, không báo lỗi |

Mỗi heuristic khớp → viết ≥1 **dòng testcase scripted** trong KHỐI 2/3, cột "Kết quả mong muốn" ghi **oracle định lượng** (double-submit → DB đúng 1 bản ghi + 1 audit; đa tab trình duyệt → 409 rollback, DB đúng 1; chuyển tab trong màn qua lại nhanh N lần → MỌI tab vẫn click được (không kẹt/không mất listener), mỗi tab hiển thị đúng nội dung của chính nó (không sót nội dung tab trước), không request treo/không lỗi console, dữ liệu đang nhập của tab được giữ hoặc reset đúng theo spec; session timeout → 401 + hướng dẫn; ngắt request → không double-submit/không state treo; mạng chập chờn → banner mất kết nối + auto re-fetch). Các case này **đếm vào Math Check** như mọi case scripted. Chỉ phần thật sự không assert được (thuần timing/mắt người sau khi đã phân tích) mới `@exec:manual` — không có charter, không có `exploratory` section.

---

## 6. Tóm tắt: bug lọt ↔ cơ chế đóng

| Lớp bug | Cơ chế đóng trong file này |
|---|---|
| Search trả sai phạm vi (ra ALL) | §2 filter-correctness + §1 data đối nghịch |
| List cắt im lặng (chỉ hiện N) | §2 volume-boundary (seed > page size) |
| Phân quyền/scope sai | §2 cross-actor (≥2 principal) |
| Xóa/clear filter không reload | §2 stale-state |
| Attr maxlength ≠ giới hạn thật | §2 attr-vs-spec + [maxlength-rule vá] |
| Duplicate → nhiều lỗi/side-effect sai | §2 error-side-effect (assert số toast + DB) |
| Case gap spec biến mất | §3 TBD-escape → dòng `[BR]` scripted KHỐI 2/3 + Coverage Debt Ledger |
| Empty-state / nút / message lệch | §4 → case scripted KHỐI 1/2 (oracle định lượng) |
| Chuỗi thao tác lạ / timing / đồng thời / phiên | §5 → case scripted KHỐI 2/3 (double-submit/đa tab/timeout...) |