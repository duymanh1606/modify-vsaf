# IRON RULES — Quy tắc bất biến của skill NTAPP QA Slice (E2E)

> File này là **nguồn sự thật duy nhất** cho các nguyên tắc bất biến của toàn workflow.
> Mọi step file và persona PHẢI tham chiếu file này thay vì tự lặp lại nội dung.
> Khi cần emphasize 1 rule cụ thể trong step, **cite ID** (vd "theo R5") thay vì paraphrase nội dung.

---

## R1. ZERO-FABRICATION (Cấm bịa dữ liệu)

> **Ý định của whitelist:** giới hạn **nguồn NỘI DUNG nghiệp vụ** (control/label/validation/logic/data) chỉ ở spec + DD — chống bịa nội dung. KHÔNG cấm đọc file điều phối/oracle/luật của chính skill (audit report, registry data, rule library, template, config) — đó là input vận hành bắt buộc của workflow.

**DANH MỤC FILE CHO PHÉP (WHITELIST):**

*Nguồn nội dung nghiệp vụ (chỉ 2 file này — cấm suy nội dung từ nơi khác):*
1. File SLICE (`{slices_root}/{id}-*.md`) — **chỉ lane `slice`**; lane `unit` KHÔNG có file này.
2. File thiết kế chi tiết `{unit}_detailed_design.md` của các unit (lane `unit`: chính `{id}_detailed_design.md`).

*Nguồn điều phối / oracle / luật của workflow (được đọc — KHÔNG phải nguồn nội dung tự do):*
3. `{qa_artifacts}/{id}/{id}_qa_report.md` — output `/ntapp-qa-audit`, là **oracle nội dung ràng buộc** (Step 00 §1a-c: audit thắng DD khi lệch).
4. `{qa_artifacts}/data_sources.yaml` — registry dynamic data (Step 01 / `dynamic_data_rules.md`).
5. `references/kbkt-generation/**` + `references/templates/**` — thư viện rule + template của skill.
6. File config cascade (`_bmad/bmm/config.yaml`, `.bmm-config.yaml`) — resolve `{qa_artifacts}`/`run_mode`/…

⚠️ **ĐIỀU CẤM TUYỆT ĐỐI (BLACKLIST):** CẤM đọc **phần Đảm bảo chất lượng / Kiểm thử** trong `_detailed_design` (heading chứa "CHẤT LƯỢNG" hoặc "QUALITY ASSURANCE", thường là Mục 5 — chứa KBKT nhúng sẵn), cũng như tài liệu `ux_design.md` tổng và L2 TechSpec tổng. Nếu vi phạm, AI sẽ tự động bị hỏng ngữ cảnh.

- Mọi UI control, màn hình, validation rule, error message, error code trong testcase E2E phải truy về nguồn input cụ thể.
- Khi thiếu thông tin → đánh dấu `[TBD]`, **tuyệt đối không tự bịa** giá trị.
- **CRITICAL:** Cấm sinh testcase cho 1 control dựa trên kiến thức chung khi chưa load rule đặc thù tương ứng trong `references/kbkt-generation/`. Bắt buộc phải lập Rule Mapping và đọc file rule qua tool `view_file`.

---

## R2. ZERO-SUMMARIZATION (Cấm tóm tắt)

Giữ nguyên **100%** chi tiết của mọi testcase E2E: đủ 11 cột (bao gồm `Exec`), không cắt luồng, không gộp case, không bỏ cột.

- Cột "Các bước thực hiện" phải mô tả tuần tự (1, 2, 3...) hành động vật lý của Tester trên giao diện — cấm viết chung chung ("Nhập sai định dạng").
- Sinh phân mảnh (chunked / iterative appending), KHÔNG ép toàn bộ file trong 1 lượt ghi gây cắt xén.
- Cấm dùng "Tương tự", "v.v.", "...". Bắt buộc tuân thủ nghiêm ngặt cảnh báo `[!CAUTION] KHÔNG ĐƯỢC GỘP` trong từng file rule riêng biệt: mỗi số thứ tự/quy tắc con trong file rule phải là 1 testcase/checklist độc lập. Riêng Error/Exception path từ phía Backend/API được phép gom nhóm theo Equivalence Partitioning (EP).


---

## R3. TRACEABILITY (Xương sống truy vết E2E)

Mỗi testcase E2E phải truy về requirement/spec.

- Mỗi kịch bản Negative/Validation E2E phải kiểm thử trực tiếp từ giao diện xuống backend theo đặc tả.
- Mỗi `unit` trong SLICE phải được phủ bởi ≥ 1 testcase trên đường đi tracer-bullet (UI → Gateway → Backend → DB/External).
- Tên control/màn hình trong testcase phải khớp 100% với phần Giao diện (UI) trong `_detailed_design`.

---

## R4. COVERAGE & QC GATE (Trạm kiểm soát bắt buộc)

Ngưỡng coverage bắt buộc trước khi bàn giao:

- **100%** luồng E2E được ánh xạ tới ≥ 1 testcase: *(bề mặt `ui`)* luồng thao tác người dùng qua mọi unit FE và BE trong slice · *(bề mặt `service`)* mọi operation/endpoint + transition state machine + mã error catalog của unit được ánh xạ tới ≥ 1 testcase.
- Mọi error path/validation do spec liệt kê phải có testcase E2E: *(ui)* kiểm tra cách UI hiển thị lỗi · *(service)* kiểm tra HTTP status + error body + side-effect đúng (0 row / bút toán đảo).
- Khi FAIL → **remediate** (bổ sung testcase), KHÔNG bàn giao khi chưa đủ coverage.

---

## R5. MISSING-INPUT HANDLING (Xử lý input thiếu)

Nếu bất kỳ input (file SLICE, file `_detailed_design` của unit) **không tồn tại** hoặc **không readable**:

- DỪNG ngay, **KHÔNG generate mock/placeholder** thay thế.
- Báo user explicit path file thiếu và chờ confirm khi không tự bù được.

---

## R6. SINGLE-SOURCE PATH (Đường ghi duy nhất)

Chỉ ghi output vào `{qa_artifacts}` đã resolve từ config cascade (xem `workflow.md` INITIALIZATION).

- Cấm hardcode path repo (vd `_bmad-output/Stage_5_Build_Verify/test/...`) trong logic ghi file.
- Ghi đè canonical mỗi run; tuyệt đối không tạo `archive/` hay `_v{N}`.

---

## R7. STOPPING ERRORS (Lỗi dừng khẩn cấp)

Dừng pipeline ngay và báo cáo nếu phát hiện:

1. **Input không hợp lệ** — bất kỳ điều kiện nào dưới đây đều dừng ngay (lane-aware):

   | Điều kiện vi phạm | Áp dụng lane | Hành động |
   |---|---|---|
   | `{id}` không khớp file SLICE `{slices_root}/{id}-*.md` **và cũng không** có `{id}_detailed_design.md` | cả hai | Báo `{id}` không phải slice cũng không phải unit có DD; chờ user xác nhận ID hoặc chạy Stage 4a |
   | Thư mục `{slices_root}` không tồn tại (khi đã detect lane `slice`) | `slice` | Hỏi user path chứa file slice |
   | File SLICE thiếu key `units` hoặc mảng `units` rỗng | `slice` | Báo broken traceability, không generate |
   | `{id}_detailed_design.md` không tồn tại/không readable (lane `unit`) | `unit` | DỪNG theo R5, KHÔNG generate mock |

   **Schema tối thiểu của file SLICE** (lane `slice` — để kiểm tra `units` hợp lệ):
   ```yaml
   slice_id: SLICE-06
   units:
     - id: SCR-001
       type: FE          # FE / BE / downstream
       design_dir: docs/detailed_design/SCR-001/
     - id: HUB-007
       type: BE
       design_dir: docs/detailed_design/HUB-007/
   ```

2. Specs L2 / part của unit chưa được approve (file không tồn tại hoặc thiếu signoff) và không tự bù được qua R5.
3. Sự thiếu nhất quán giữa Backend Spec và testcase E2E: luồng Backend có mô tả lỗi nhưng testcase E2E không cover.
4. Locator/control trong testcase không có trong phần Giao diện (UI) của `_detailed_design` / ui_schema nguồn.

---

## R8. STRUCTURAL_INTEGRITY (Toàn vẹn cấu trúc theo Màn hình Action)

Mọi file kịch bản kiểm thử E2E (`{id}_detailed_test_manual_testcase.md`) khi được sinh ra bắt buộc phải tuân thủ nghiêm ngặt cấu trúc phân tách theo **Màn hình Action** *(bề mặt `ui`)* hoặc theo **Operation/Endpoint** *(bề mặt `service`)*:

- **Phân vùng độc lập:** *(ui)* Bảng `📌 Danh sách UI Controls` và 3 Khối (UI, Chức năng, ATTT) · *(service)* Bảng `📌 Danh sách Endpoint/Operation & Hợp đồng` và 3 Khối (Hợp đồng, Nghiệp vụ, ATTT) — của màn/operation nào phải nằm hoàn toàn trong phân vùng của màn/operation đó. Cấm đẩy case xuống cuối file hoặc trộn vào phân vùng khác.
- **Bảng tra cứu riêng biệt:** Mỗi Màn hình Action *(ui)* / Operation *(service)* phải có một bảng tra cứu riêng (`Danh sách UI Controls` / `Danh sách Endpoint & Hợp đồng`) ngay trước các khối testcase.
- **Tiêu đề Khối rõ ràng:** Tất cả các bảng testcase bắt buộc phải nằm dưới một tiêu đề Khối cụ thể (`##### KHỐI 1...`, `##### KHỐI 2...`, `##### KHỐI 3...`). Nghiêm cấm xuất hiện bảng trôi nổi không tiêu đề.
- **Tuần tự hóa ID kịch bản:** ID kịch bản bắt buộc phải tăng dần và liên tục theo đúng trình tự xuất hiện của các màn hình và các khối (ví dụ: Màn 1 UI $\rightarrow$ Màn 1 Chức năng $\rightarrow$ Màn 1 Security $\rightarrow$ Màn 2 UI $\rightarrow$ Màn 2 Chức năng $\rightarrow$ Màn 2 Security). Cấm hiện tượng ID nhảy cóc hoặc đảo ngược dải ID.

