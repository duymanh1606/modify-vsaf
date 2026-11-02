---
name: NTAPP-kbnt-to-confluence
description: "Sinh và đồng bộ KBNT (Kịch bản nghiệm thu) của MỘT ĐỢT nghiệm thu lên Confluence — người dùng cuối thao tác và ký trực tiếp trên trang. Dò delta từ mốc đợt trước (git 6 repo + spec + demo_status), dò ảnh hưởng (ripple) để gom luồng E2E xuyên nhiều slice, fetch template KBNT từ Confluence, sinh case theo AC/DD (+KBKT nếu có), rồi tạo hoặc cập nhật trang đợt với merge giữ nguyên ô người dùng đã ký. Triggers: viết KBNT, kịch bản nghiệm thu, tạo đợt nghiệm thu, đẩy KBNT lên confluence, nghiệm thu ảnh hưởng, UAT script."
user-invocable: true
argument-hint: "\"<tên đợt>\" [--since YYYY-MM-DD] [--local]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - Skill
  - mcp__atlassian32__confluence_get_page
  - mcp__atlassian32__confluence_get_page_children
  - mcp__atlassian32__confluence_search
  - mcp__atlassian32__confluence_create_page
  - mcp__atlassian32__confluence_update_page
  - mcp__atlassian__confluence_get_page
  - mcp__atlassian__confluence_get_page_children
  - mcp__atlassian__confluence_search
  - mcp__atlassian__confluence_create_page
  - mcp__atlassian__confluence_update_page
---

# NTAPP — KBNT → Confluence

Sinh và đồng bộ **KBNT (Kịch bản nghiệm thu)** của **một đợt nghiệm thu** lên Confluence, theo template KBNT fetch từ Confluence. KBNT là tài liệu **người dùng cuối ký**, khác KBKT (kịch bản kiểm thử của QA) và khác KBNV/SRS (đặc tả yêu cầu) — xem `CONTEXT.md` mục *Acceptance documentation* của spec repo.

## Nguyên tắc cốt lõi

- **1 đợt = 1 trang.** Tên trang theo **convention của nhánh KBNT** đọc từ các trang con hiện có (ví dụ `KBNT - <nội dung đợt>`); nhánh rỗng thì dùng mặc định `KBNT — YYYY-MM — <tên đợt>`. Đợt do người dùng đặt tên, KHÔNG suy từ sprint/release. Gọi lại cùng tên đợt trong cùng tháng thì UPDATE trang đó; đợt khác thì CREATE trang khác. Trang đợt cũ đóng băng, không đụng lại.
- **Trang là nơi có chữ ký — KHÔNG bao giờ ghi đè mù.** Publish lần 2 trở đi bắt buộc đọc trang live trước, merge theo mã case, giữ nguyên các ô người dùng đã điền. Parse bảng thất bại thì DỪNG, không ghi. Luật đầy đủ: `references/merge-rules.md`.
- **Mã case bất biến.** `NT-<target>-<nn>` nằm trong ô đầu (`STT`) của dòng, cấp một chiều từ `case-registry.yaml`, không renumber, không tái sử dụng. Registry là ledger, không phải cache — mất là đứt truy vết. Trạng thái đúng bốn giá trị: `active` / `deferred` / `done` / `huy`.
- **Case chưa làm được đi vào `kbnt-backlog.md`, không tan biến.** Đợt nào chốt dời case thì ghi case đó vào backlog kèm lý do và đợt cấp mã; đợt kế tiếp **đọc backlog ở bước dò nội dung** và mang case sang bằng đúng mã cũ. Nghiệm thu xong thì xóa khỏi backlog và đổi trạng thái registry thành `done`. Ledger đợt `kbnt-publish-history.md` phải **liệt kê ID target**, không chỉ đếm số — nếu không thì không tra được phần nào đã nghiệm thu.
- **Chỉ đẩy bảng thông tin đầu tài liệu + bảng case lên Confluence.** Skill sinh hai file: bản đầy đủ (cảnh báo, chuẩn bị dữ liệu, phụ lục — giữ ở repo) và bản `{dot_slug}_kbnt_cases.md` chỉ chứa bảng case, là nguồn duy nhất để build storage. Hai khối đẩy lên đúng là bề mặt tick và ký của người dùng cuối; thêm nội dung khác vào chỉ làm loãng và tạo ra bản thứ hai phải merge. **Cột 2 của bảng thông tin là khối chữ ký** — publish lần 2+ carry nguyên văn từ snapshot (`--carry-info`), sinh lại là xoá chữ ký người phê duyệt.
- **Không tự dời case.** Đánh dấu dời chỉ khi người dùng chốt rõ đúng case đó. Câu trả lời "chưa hiểu câu hỏi" là yêu cầu giải thích lại, KHÔNG phải đồng ý — suy diễn từ quyết định của case khác là làm case biến mất khỏi đợt mà không ai quyết.
- **Đánh số mục bắt đầu từ A.** Hai mục đầu là `A` (cảnh báo) và `B` (chuẩn bị dữ liệu), hai phụ lục là `Phụ lục 1` / `Phụ lục 2`. Đừng đặt mục thân bài là `C`, `D` rồi phụ lục lại `A`, `B` — người đọc tưởng thiếu mục.
- **Trang KBNT đã có trên Confluence là nguồn thứ tư, đọc TRƯỚC khi chốt phạm vi.** Git nói "đã làm gì", chỉ trang đã điền ô kết quả mới nói "đã nghiệm thu gì". `kbnt-publish-history.md` rỗng nghĩa là *skill* chưa chạy, KHÔNG nghĩa là chưa ai ký — đội thường đã viết KBNT tay nhiều đợt. Trang lạ thì backfill vào ledger. Bỏ bước này thì người dùng phải nghiệm thu lại thứ đã ký.
- **Ô bảng phải bullet hóa, không viết dồn một dòng.** Dùng đúng ngưỡng đã chốt ở skill SRS: ô ≥ 2 câu và ≥ 80 ký tự → `<ul><li>`; `Các bước thực hiện` → `<ol><li>` bỏ tiền tố số; tầng kết quả → `<li><strong>Giao diện:</strong> …`; một `<li>` không gánh hai ý (tách cả vế sau dấu chấm phẩy). Kèm `<colgroup>` đặt bề rộng cột.
- **Ô `Version tài liệu KBNV` của header chứa page-link tới các trang KBNV/SRS đã viết**, nhóm theo mục — map duyệt từ nhánh KBNV của dự án (header DD chỉ có lác đác dòng `Confluence SRS`, không đủ), ghi ở khối `tai_lieu_kbnv` của `dot-manifest.yaml`. Mục không tra ra chắc chắn thì bỏ trống, KHÔNG đoán.
- **Header bảng tự viết, KHÔNG copy byte từ template.** PowerShell decode response Confluence thành Latin-1 khi thiếu `charset` → copy byte là dán mojibake lên trang; và template có thể tự lệch ô. Validator phải kiểm cả hàng header.
- **Mục đã nghiệm thu ở đợt khác thì giữ hàng mục + nhãn ĐÃ NGHIỆM THU, chỉ bỏ hàng case.** Xoá hẳn làm số La Mã hụt và mất lý do. Danh sách mục cắt nằm trong `dot-manifest.yaml`, không hardcode trong script.
- **Nhánh KBNT resolve một lần rồi cache vào `kbnt-branch.json` của dự án**, kèm convention tiêu đề đọc từ các trang con — đặt tên lệch convention làm trang mới trông như của dự án khác. CQL `title ~` xếp theo relevance và cắt theo `limit` nên KHÔNG đủ để kết luận "không có nhánh"; phải duyệt children. Nhánh KBNT hay nằm cạnh tài liệu yêu cầu, không nằm dưới nhánh Test.
- **Nguồn hybrid:** AC (story Stage 5) + DD (Stage 4) là xương quyết định case nào tồn tại; KBKT (`{id}_detailed_test_manual_testcase.md`, `{id}_fixtures.yaml`) là thịt bổ sung dữ liệu và bước đã kiểm chứng. KBKT KHÔNG phải điều kiện bắt buộc.
- **Soft gate per-target:** target thiếu DD hoặc thiếu story vẫn viết case, từ git diff + code + KBKT + mô tả người dùng, và đánh dấu `nguon: code-only` để review kỹ. Không chặn cả đợt vì một hotfix không có story.
- **Case là việc người dùng cuối làm được và tự phán xử được.** CẤM case validate field-level (maxlength, required, format, tab-order) và case an toàn thông tin — những thứ đó thuộc KBKT. Unit backend không có màn thì ưu tiên diễn đạt qua bề mặt người dùng nhìn thấy; không có bề mặt nào thì vẫn viết case nhưng ghi rõ cần hỗ trợ kỹ thuật để kích hoạt.
- **Kết quả mong đợi nêu đủ tầng hệ quả nhưng bằng lời nghiệp vụ** — nhãn `Giao diện:` / `Dữ liệu:` / `Gửi đi:` / `Log:` (đội gọi là "log", xem `terminology.md` của skill SRS), mỗi tầng một dòng, diễn đạt nghiệp vụ chứ không phải tên bảng/cột thô.
- **Dữ liệu mô tả bằng đặc tính phân biệt, không bịa định danh.** "Một giao dịch của TCTC X ngày đối soát T-1, lệch số tiền, chưa từng gửi xử lý" là đúng; "một giao dịch lệch bất kỳ" là sai; bịa mã merchant cụ thể cũng sai.
- **Nghiệm thu ảnh hưởng là mục bắt buộc xét, không phải tùy chọn.** Dò ripple cơ học rồi để người dùng tick, gom thành luồng E2E đặt tên theo nghiệp vụ.
- **Mọi thao tác ghi Confluence DỪNG preview và chờ xác nhận.** Không đoán trang đích, không tự tạo nhánh KBNT khi không tìm thấy.
- **Không hardcode host/pageId trong nội dung sinh ra.** Điểm vào cố định duy nhất là index dự án; mọi thứ khác resolve lúc chạy — `references/confluence-resolve.md`.

## Instructions

Đọc đầy đủ và làm theo: `./workflow.md`

Tài liệu tham chiếu (đọc khi tới bước cần):
- `./references/delta-detection.md` — dò nội dung đợt (4 nguồn, gồm cả trang KBNT đã có trên Confluence) + dò ripple để dựng luồng E2E.
- `./references/kbnt-authoring.md` — **(đọc TRƯỚC khi viết case đầu tiên)** luật viết case: độ mịn, cách viết bước, kết quả mong đợi 4 tầng, dữ liệu, case cần hỗ trợ kỹ thuật, case hồi quy.
- `./references/merge-rules.md` — **(bắt buộc cho bước publish lần 2+)** đọc lại trang, khớp mã case, so 3 chiều, khóa lạc quan, đánh dấu hủy.
- `./references/confluence-resolve.md` — resolve host và trang cha, fetch template, storage format, cách publish.

Script của skill (dùng thay vì viết lại tay — chính chỗ viết lại tay đã sinh ra lỗi font header và ô không bullet ở lần chạy đầu):
- `./scripts/build-kbnt-storage.py --cases <…_kbnt_cases.md> --manifest <dot-manifest.yaml> --out <…storage.xhtml>` — build bảng case: header tự viết, `<colgroup>`, bullet hóa ô, cắt mục theo khối `da_nghiem_thu_o_dot_khac` của manifest, và tự chạy 3 phép kiểm (lệch cột kể cả hàng header / mojibake / số mục-case). Cần `pyyaml`.
- `./scripts/confluence-create.ps1` — POST tạo trang mới (body > 150KB, MCP không tải nổi).
- `./scripts/confluence-update.ps1` — PUT cập nhật trang, **có khóa lạc quan** (`-ExpectVersion`, lệch thì throw, không ghi).

Tái dùng từ skill anh em (resolve đường dẫn lúc chạy bằng Glob, KHÔNG hardcode):
- `**/NTAPP-srs-to-confluence/references/terminology.md` — từ điển thuật ngữ, giữ tiếng Anh cho `version` / `log` / `transaction`.
- `**/NTAPP-srs-to-confluence/scripts/confluence-get.ps1` — đọc host `.32` bằng REST khi MCP `.32` chết.
- `**/NTAPP-srs-to-confluence/scripts/confluence-publish.ps1` — PUT body bằng REST khi trang quá lớn cho MCP.
- `**/NTAPP-dd-to-confluence/references/storage-format.md` — map Markdown sang storage format XHTML.
