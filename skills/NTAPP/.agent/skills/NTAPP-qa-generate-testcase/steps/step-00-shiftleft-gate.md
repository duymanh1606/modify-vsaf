# STEP 00: SHIFT-LEFT GATE (Tiền kiểm chất lượng spec + khung charter)

> **Acting as:** [Senior QA Engineer](../agents/agent_generate_manual_testcase.md)
> **Tuân thủ:** [principles/iron_rules.md](../principles/iron_rules.md) (R1, R5, R7) · [principles/run_mode_rules.md](../principles/run_mode_rules.md)
> **Vị trí:** Chạy ĐẦU TIÊN, TRƯỚC [Step 01](step-01-init-slice.md). Là cổng shift-left của School B + cổng định tuyến `run_mode`.

## 1. Mục tiêu
Bắt sự mơ hồ của spec **trước khi** thiết kế testcase (không sinh test trên nền mơ hồ), lập khung cho phần `exploratory`, **detect `input_type`** (slice vs unit đứng riêng) + **`surface_type`** (ui vs service/no-UI), và **resolve `run_mode` + định tuyến lane** (full / batch / delta).

## 2. Các Bước Thực Hiện

0a. **Detect `input_type` (GATE nhận diện — chạy TRƯỚC mọi thứ):** Với `{id}` người dùng truyền vào:
   - Tìm file SLICE `{slices_root}/{id}-*.md`. **Tồn tại** → `input_type=slice` (nhiều unit, có xếp thứ tự E2E).
   - Không có file SLICE nhưng tồn tại `{id}_detailed_design.md` (đơn vị trong WBS: HUB/WGT/SCR/MPF…) → `input_type=unit` (coi như "slice một unit" — Step 01 chạy nhánh unit, bỏ bước xếp thứ tự liên-unit).
   - Không có cả hai → **DỪNG**, hỏi user: `{id}` không khớp file SLICE cũng không có `_detailed_design`; yêu cầu xác nhận ID hoặc chạy Stage 4a (DD) trước.
   - In `input_type` đã chọn ra chat. Biến này quyết định nhánh ở Step 01 và được ghi vào Context Ledger.

0a-bis. **Detect `surface_type` (GATE bề mặt — QUYẾT ĐỊNH Ở CẤP TEST-TARGET, KHÔNG per-unit):** Xác định **cả test-target** (nguyên slice, hoặc unit đứng riêng) là **`ui`** hay **`service`** — dựa trên: target có chứa **BẤT KỲ unit UI nào** (`SCR-*`/`WGT-*`, tức có phần Giao diện render được) hay không.
   - **Target CÓ ≥1 unit UI → `surface_type=ui` cho TOÀN luồng.** E2E đi **tích hợp qua màn** (như cũ — [slice_planning_rules.md](../principles/slice_planning_rules.md) + [unit_classification_rules.md](../principles/unit_classification_rules.md)). **MỌI unit BE (HUB/MPF/INT/PMT-EXT…) là BACKEND của màn** — map theo story-code, verify bằng oracle API/DB **nhúng trong testcase của màn** (BE không map màn nào → nhóm Background). **TUYỆT ĐỐI KHÔNG** tách BE thành "service surface" riêng, **KHÔNG** chèn BE vào thứ tự E2E như một bề mặt độc lập.
   - **`units:` không có unit UI → chạy [borrowed_surface_rules.md §1](../principles/borrowed_surface_rules.md) TRƯỚC khi kết luận `service`:** nếu `## What to build`/`demoable` nêu một màn `SCR-*`/`WGT-*` và cross-check host pass → `surface_type=ui`, màn đó = `[Nav]`, **bề mặt test = cụm hành động (KHÔNG phải màn)**. Cross-check fail → hỏi user, không đoán.
   - **Target KHÔNG có unit UI nào và KHÔNG có bề mặt mượn → `surface_type=service`.** (Thuần BE: unit `HUB/MPF/INT` đứng riêng, hoặc slice toàn BE — batch/integration pipeline không màn.) Khi đó các unit BE mới thành operation ([service_surface_rules.md](../principles/service_surface_rules.md)). Đây chính là luật **"không có giao diện thì mới test API BE riêng"**.
   - `input_type=unit`: 1 unit BE không màn → `service`; `SCR-*`/`WGT-*` → `ui`. Muốn test API 1 HUB riêng → chạy skill với chính `{id}` của HUB đó (target no-UI → service).
   - Prefix ID chỉ là tín hiệu phụ — **đọc DD mới quyết định**. DD mơ hồ không rõ có UI hay không → **hỏi user 1 lần** (đừng đoán).
   - **1 lần chạy generate = 1 target = MỘT `surface_type` duy nhất** (không có "slice trộn per-unit"). In `surface_type` (1 giá trị cho cả target) ra chat; ghi vào Context Ledger.

0. **Resolve `run_mode` + định tuyến (GATE đầu):** Theo [run_mode_rules.md](../principles/run_mode_rules.md) §1–2.
   - Resolve lane theo ưu tiên: ý định người dùng → `.bmm-config.yaml` `run_mode` → auto-detect → default `full`.
   - **Auto-detect delta:** nếu **đã tồn tại đủ 3 artifact** của `{id}` (`{id}_testspec.feature` + `{id}_detailed_test_manual_testcase.md` + `{id}_fixtures.yaml`) tại `{qa_artifacts}/{id}/` → **đề xuất `delta`** và hỏi 1 lần. Người đồng ý → **BỎ QUA toàn bộ Step 00–03**, vào thẳng [Step 05 Nhánh A](step-05-roundtrip.md) (delta map + patch). Người từ chối → tiếp tục `full`/`batch`.
   - Lane `batch`: ghi nhận "auto-proceed giữa các màn, gộp HITL về Step 04" để các step sau áp dụng.
   - Lane `full`: hành vi như cũ, đầy đủ 4 HITL gate.
   - In lane đã chọn ra chat trước khi tiếp tục.

1. **Kiểm tra delegation tới `ntapp-qa-audit` + DỰNG BẢNG OVERRIDE (GATE precedence — bắt buộc):**
   - Nếu đã tồn tại `{qa_artifacts}/{id}/{id}_qa_report.md` (output của `/ntapp-qa-audit`) → đọc TOÀN BỘ, nạp các quyết định đã chốt. **Scope + gap đã chốt trong audit là ràng buộc độ phủ bắt buộc — testcase KHÔNG được thu hẹp hơn audit.** Rồi làm 1a–1c dưới đây TRƯỚC khi sang bước 4.
   - **1a. Dựng "Bảng Override" (audit → nội dung canonical):** Quét mọi GAP có trạng thái **`Resolved`** + mọi verdict gắn nhãn **`stale-docs`** / **`stale`** + phần intro/bối cảnh (vd "DD parts sinh trước CR → stale, chốt theo TechSpec/code"). Với mỗi mục, trích ra dòng: `{control / field / feature / enum} → {quyết định canonical}` (vd `composite.status → 5 enum, KHÔNG Draft`; `SCR-COMPOSE auto-save/localStorage draft → ĐÃ GỠ v3.0`; `merchantCode regex → ^[A-Za-z0-9_-]{0,20}$`). **In bảng này ra chat.**
   - **1b. LUẬT PRECEDENCE (nội dung, không chỉ độ phủ):** Với bất kỳ control/field/feature nào có trong Bảng Override, **nội dung canonical của audit THẮNG `_detailed_design` (DD) tuyệt đối khi mâu thuẫn**. DD chỉ là nguồn cho phần audit *chưa* đụng tới. ⚠️ "Nạp làm context" KHÔNG đủ — audit là **oracle nội dung ràng buộc**, DD thua khi lệch.
   - **1c. CẤM sinh case từ DD stale:** Nếu DD mô tả một tính năng/nhánh/trạng thái mà một GAP `Resolved` (hoặc verdict stale-docs) nói **đã gỡ / đã đổi**, thì **CẤM** sinh testcase theo mô tả DD đó. Chỉ được: (i) ghi case theo quyết định canonical của audit, hoặc (ii) đánh dấu `❌ REMOVED` (giữ slot ID cho R8, exec=N/A) nếu tính năng không còn. Ghi 1 dòng "GAP-DRIFT-*" vào Coverage Debt Ledger (Mục 5.6) nêu rõ DD nào stale so với CR/verdict nào. **KHÔNG bao giờ tin DD mù quáng khi audit đã phán DD stale.**
   - Nếu **chưa** có và config `shiftleft_required: true` (Layer 3, mặc định `true`) → **DỪNG**, khuyến nghị user chạy `/ntapp-qa-audit {id}` trước. (Skill này KHÔNG tự làm audit — tránh trùng chức năng; chỉ là cổng kiểm tra.)
   - Nếu config `shiftleft_required: false` → chạy **mini-audit nội bộ** (bước 2).
2. **Mini-audit nội bộ (chỉ khi không có qa-audit):** Quét nhanh file `_detailed_design` các unit tìm nhập nhằng. **Bề mặt `ui`** — 4 loại: (a) error message thiếu, (b) nhánh logic chưa định nghĩa, (c) ràng buộc data mơ hồ, (d) UI-logic mâu thuẫn. **Bề mặt `service`** — thay (d) bằng nhập nhằng hợp đồng: (a) error catalog thiếu mã lỗi / HTTP status, (b) nhánh logic/decision chưa định nghĩa, (c) request contract mơ hồ (field required?/ràng buộc/enum), (d) state machine hoặc idempotency chưa khai (transition hợp lệ? xử lý request/message trùng?). Liệt kê mục `[TBD]` ra chat.
3. **Gate quyết định:** Nếu số `[TBD]` chặn-luồng-chính > 0 → khuyến nghị làm rõ trước. Cho phép user chủ động bỏ qua (ghi nhận rủi ro).
4. **Khung rủi ro "explore" (để MATERIALIZE, không charter):** Đánh dấu sẵn các vùng bất thường (timing/đồng thời/phiên, UX mới, spec còn `[TBD]` không chặn). Các vùng này **KHÔNG** đi charter — Step 02b/03 sẽ phân tích ra oracle xác định và viết thành **case scripted trong KHỐI 2/3** (gap-spec → dòng `[BR]` + Coverage Debt), theo [explore_and_consistency_rules.md](../principles/explore_and_consistency_rules.md) §3–§5. `exploratory` chỉ chừa cho quan sát thẩm mỹ thuần trong KHỐI 1.
5. **Chuyển tiếp:** Đọc và thực thi [Step 01](step-01-init-slice.md). (Trừ khi đã định tuyến `delta` ở bước 0 → đã sang Step 05.)

> **Quan hệ ecosystem:** Đây là vai trò shift-left tối thiểu *trong* skill. Nguồn chuẩn vẫn là `/ntapp-qa-audit` (Q&A handshake đầy đủ). Step 00 chỉ đảm bảo không bỏ qua shift-left và không scripted-hóa vùng bất định.
