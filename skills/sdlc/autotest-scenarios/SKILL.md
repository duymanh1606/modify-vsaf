---
name: autotest-scenarios
description: Tạo mới hoặc cập nhật kịch bản kiểm thử cho một chức năng hoặc toàn bộ project — từ tài liệu domain knowledge, từ file Excel, hoặc chỉnh sửa file TC đã có.
user-invocable: true
argument-hint: "<yêu cầu bất kỳ>"
disable-model-invocation: true
---

# Test Scenarios Agent

Tạo mới hoặc cập nhật file kịch bản kiểm thử chuẩn TC-NNN markdown, sẵn sàng dùng với `/autotest-web`, `/autotest-android`, `/autotest-ios`, `/autotest-api`.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user trong lúc làm việc — tiến trình, câu hỏi, cảnh báo, tóm tắt kết quả — viết bằng **tiếng Việt**. Giữ nguyên thuật ngữ kỹ thuật (TC, Excel, mapping...) không dịch.

> **Commit message:** Chỉ commit khi user yêu cầu (đúng git safety protocol chung). Khi commit, viết message bằng **tiếng Việt** theo format `<type>: <mô tả ngắn gọn>` (feat/fix/refactor/docs/test) — giữ nguyên thuật ngữ kỹ thuật không dịch.

## Argument Parsing

Nhận **structured argument** hoặc **ngôn ngữ tự nhiên** — không cần đúng format cố định.

```
/autotest-scenarios login                                  # structured — feature cụ thể
/autotest-scenarios viết kịch bản cho chức năng giỏ hàng  # ngôn ngữ tự nhiên
/autotest-scenarios thêm TC cho order                      # ngôn ngữ tự nhiên
/autotest-scenarios                                        # trống → toàn bộ project
```

Parse `$ARGUMENTS`:
- **Trống** → hỏi: "Bạn muốn tạo kịch bản cho chức năng nào? (hoặc mô tả yêu cầu)"
- **Có argument** → trích xuất tên chức năng (`SCOPE`) từ text; nếu mơ hồ → hỏi: "Chức năng nào?"

---

## Step 0 — Kiểm tra TC file đã tồn tại chưa

```python
import glob
hits = glob.glob(f'automation_test/docs/features/**/test-cases.md', recursive=True)
matches = [p for p in hits if SCOPE.lower() in p.lower()] if SCOPE != 'project' else hits
```

**Nếu chưa có TC file** → hỏi user một câu:

> Chưa có kịch bản kiểm thử cho **`<SCOPE>`**. Tạo bằng cách nào?
>
> **1** — AI tự viết từ tài liệu (domain knowledge)
> **2** — Convert từ file Excel có sẵn

- Chọn **1** → **Mode A: AI Generate**
- Chọn **2** → **Mode B: Excel Import**

**Nếu đã có TC file** → hỏi user một câu:

> Đã có kịch bản kiểm thử tại `<path>` (**N TCs**). Bạn muốn làm gì?
>
> **1** — Thêm TC mới vào file hiện có
> **2** — Sửa / cập nhật TC đã có (chỉ định TC-NNN cần sửa)
> **3** — Xoá TC (chỉ định TC-NNN cần xoá)
> **4** — Tạo lại hoàn toàn (xoá và viết mới)

- Chọn **1** → **Mode A: AI Generate** (chỉ thêm, không đụng TC cũ)
- Chọn **2** → **Mode E: Edit TC**
- Chọn **3** → **Mode D: Delete TC**
- Chọn **4** → xoá file cũ, quay lại hỏi nguồn (Mode A hoặc B)

---

## Mode A — AI tự viết từ tài liệu

### Step A1 — Kiểm tra domain knowledge

```bash
python3 -c "
import glob
common = ['global-data.md', 'product-overview.md', 'api-reference.md', 'system-overview.md']
hits = [f'automation_test/docs/{f}' for f in common if glob.glob(f'automation_test/docs/{f}')] + glob.glob('automation_test/docs/features/**/*.md', recursive=True)
print('\n'.join(hits) or 'NONE')
"
```

**Nếu có docs** → đọc tất cả file liên quan đến `<feature>` (hoặc toàn bộ nếu không có feature):
- `business-scenario.md` — user flows, màn hình, business rules
- `detail-design.md` — API contracts, DB schema, constraints kỹ thuật
- `global-data.md` — URL, môi trường
- `product-overview.md` — mô tả sản phẩm tổng quan
- `api-reference.md` — danh sách endpoints (API project)

**Nếu không có docs** → hỏi user:

> Chưa tìm thấy tài liệu domain knowledge.
>
> Bạn có thể:
> - **A** — Paste nội dung tài liệu trực tiếp vào đây
> - **B** — Cung cấp link Confluence để tôi tự fetch (chạy `/autotest-project-docs <project>` trước)
> - **C** — Trả lời vài câu hỏi để tôi tạo domain knowledge cơ bản

Xử lý theo lựa chọn của user.

**Đọc bài học tích luỹ** — nếu `automation_test/docs/scenario-learnings.md` tồn tại, đọc toàn bộ trước khi sang Step A1.5. Đây là các bài học rút ra từ những lần user chỉnh sửa scenarios trước đó (xem mục "Scenario Learnings" ở cuối file) — áp dụng khi thiết kế TC ở Step A2 để không lặp lại lỗi cũ.

Sau đó tiếp tục Step A1.5.

### Step A1.5 — Đối chiếu tài liệu (consistency check)

Trước khi thiết kế TC, đối chiếu `business-scenario.md` (nghiệp vụ) với `detail-design.md` (kỹ thuật) — nếu cả hai đều tồn tại cho feature này:

- **Orphan** — business rule/flow nói trong business-scenario.md nhưng không có API/field/constraint tương ứng trong detail-design.md (hoặc ngược lại).
- **Conflict** — cùng 1 field/rule nhưng hai tài liệu mô tả khác nhau (vd maxlength, enum values, error code khác nhau).
- **Missing relationship** — một bước trong flow không rõ gọi API nào / field nào chịu trách nhiệm.
- **Logic Issues** — mâu thuẫn logic nội tại ngay trong 1 tài liệu (vd min > max, required=true nhưng enum liệt kê rỗng).
- **Completeness Gaps** — field/API/error thiếu metadata bắt buộc để viết TC (field không nêu kiểu dữ liệu, API không nêu method/path, error code không có message/điều kiện trigger).

Quét **toàn bộ** cả 2 tài liệu trước (không dừng ở phát hiện đầu tiên). Nếu có từ 1 điểm trở lên ảnh hưởng đến việc viết TC (không phải lỗi chính tả nhỏ) → DỪNG một lần duy nhất, gộp hết các điểm phát hiện được vào 1 câu hỏi:

> Phát hiện **N điểm** mâu thuẫn/thiếu nhất quán giữa tài liệu khi chuẩn bị viết TC cho `<feature>`:
>
> **1. <mô tả điểm 1: field/rule nào, hai tài liệu nói gì>**
> **2. <mô tả điểm 2>**
> ...
>
> Với mỗi điểm, xử lý thế nào? (trả lời theo số, vd `1: chọn A`, `2: chọn C`)
> **A** — `business-scenario.md` là nguồn chính, bỏ qua phần liên quan trong detail-design.md
> **B** — `detail-design.md` là nguồn chính, bỏ qua phần liên quan trong business-scenario.md
> **C** — Tôi sẽ sửa lại tài liệu — dừng ở đây, chờ tôi cập nhật rồi chạy lại
> **D** — Bỏ qua, không viết TC cho phần này

Ghi nhớ quyết định của user cho từng điểm thành 1 **decision log** giữ suốt phiên làm việc (điểm nào, user chọn gì). Trước khi viết bất kỳ TC nào ở Step A2 liên quan tới field/flow đã có quyết định, rà lại decision log để áp dụng nhất quán — không quay lại dùng thông tin đã bị user bác bỏ. Sau đó tiếp tục Step A2.

### Step A2 — Tạo kịch bản theo 6 góc nhìn

Áp dụng đủ 6 lenses cho mỗi feature (hoặc toàn project nếu không chỉ định):

| Lens | Câu hỏi |
|---|---|
| Happy Path | Luồng thành công bình thường là gì? |
| Business Rules | Quy tắc nghiệp vụ nào cần kiểm tra? |
| Security | Người dùng trái phép có thể làm gì? |
| Negative / Error | Dữ liệu sai, trạng thái sai xảy ra thế nào? |
| Edge Cases | Giá trị biên, giới hạn, trường hợp ngoại lệ? |
| UI State | Hiển thị có điều kiện, loading, empty state? |

Numbering: TC-001–099 Happy Path · TC-100–199 Business Rules · TC-200–299 Security · TC-300–399 Negative · TC-400–499 Edge Cases · TC-500–599 UI State

**Kỹ thuật thiết kế bổ sung** (áp khi điền Negative / Edge Cases / Business Rules, không thay thế 6 lens mà làm dày thêm coverage):
- **Equivalence Partitioning (EP)** — mỗi field có ràng buộc (kiểu dữ liệu, enum, bắt buộc/không) → ít nhất 1 TC valid class + 1 TC invalid class.
- **Boundary Value Analysis (BVA)** — mỗi field có giới hạn số/độ dài (min/max/length) → liệt kê đủ 4 case biên: `min-1`, `min`, `max`, `max+1` (không chỉ 1-2 case đại diện).
- **Use Case / Flow Testing (UCT)** — mỗi flow có nhánh phụ (alternate/exception flow nêu trong business-scenario.md) → ít nhất 1 TC cho nhánh chính, 1 TC cho mỗi nhánh phụ quan trọng.
- **Decision Table (DT)** — rule kết hợp nhiều điều kiện (AND/OR, vd "nếu loại KH = X và số tiền > Y thì...") → sinh TC cho các tổ hợp điều kiện có ý nghĩa nghiệp vụ, không chỉ test từng điều kiện riêng lẻ.
- **Pairwise (PW)** — ≥3 field độc lập, không có quan hệ nhân-quả (khác DT), mỗi field nhiều giá trị hợp lệ → sinh TC theo cặp giá trị (mọi cặp giữa 2 field bất kỳ xuất hiện ít nhất 1 lần), không cần test full combination.
- **State Transition (ST)** — entity có vòng đời trạng thái (vd đơn vay: `pending → approved → disbursed → overdue → closed`) → 1 TC cho mỗi transition hợp lệ, 1 TC cho mỗi transition bị cấm (vd `closed → disbursed`).
- **Error Guessing (EG)** — danh mục lỗi kinh nghiệm không nằm sẵn trong tài liệu: input null/rỗng bất ngờ, ký tự đặc biệt/Unicode, race condition khi thao tác đồng thời → thêm 1-2 TC cho field/flow rủi ro cao (xem bảng risk bên dưới).

**Checklist mở rộng theo đặc điểm feature** (áp dụng có điều kiện — chỉ khi feature có đặc điểm tương ứng):

| Đặc điểm feature | Case bắt buộc thêm |
|---|---|
| ≥2 field liên quan nhau (min<max, dropdown cha-con, field bắt buộc có điều kiện) | Cross-field: tổ hợp giá trị hợp lệ/không hợp lệ giữa các field, dropdown con reset khi đổi cha, tổng field con khớp field tổng |
| Flow ghi dữ liệu tiền/số dư/giao dịch | Concurrency: double-submit không tạo trùng bản ghi; 2 request đồng thời trên cùng tài nguyên (vd cùng tài khoản) xử lý đúng, không overdraft. **Expected Result phải nêu rõ trạng thái nghiệp vụ/dữ liệu sau hành động** (vd "trạng thái đơn chuyển thành DISBURSED", "số dư giảm đúng số tiền"), không chỉ thông báo hiển thị trên UI |
| Flow nhiều bước ghi DB | Rollback: fail giữa chừng → dữ liệu về đúng trạng thái trước giao dịch, không có record mồ côi |
| Có role/phân quyền | Permission matrix: mỗi cặp (role × action) — có quyền → thành công, không có quyền → bị chặn, đổi role → quyền cập nhật đúng |
| Màn hình danh sách/pagination | List rỗng, 1 item, đúng page size, vượt page size, trang cuối, page number invalid |
| Field text/date/currency | Tiếng Việt có dấu (search/sort/filter), format tiền tệ (dấu chấm ngăn nghìn, "đ"/VND), ký tự Unicode/emoji |

**Test pyramid — tránh trùng case biên qua nhiều layer**: nếu feature có cả TC lớp API và lớp App/Web (vd domain docs có cả `api-reference.md` và luồng UI trong `business-scenario.md`) cho cùng 1 rule/boundary, test **đủ toàn bộ biên/tổ hợp tại lớp API** (rẻ, nhanh, xác định); lớp App/Web chỉ cần 1 TC happy + 1 TC reject để chứng minh UI hiển thị đúng — không lặp lại toàn bộ case biên ở UI.

**Priority & Severity theo risk** — với mỗi TC, ước lượng Likelihood (1–3: hiếm khi / thỉnh thoảng / thường xuyên xảy ra) và Impact nếu bug xảy ra (1–3: nhỏ / trung bình / nghiêm trọng — mất tiền, sai số dư, lộ dữ liệu). `risk = Likelihood × Impact`: 6–9 → Priority P0 + Severity Critical; 3–5 → P1 + Major; 1–2 → P2/P3 + Minor. Severity đo mức độ hậu quả nếu fail, độc lập với Priority (1 edge case hiếm gặp vẫn có thể Severity Critical nếu liên quan tiền/bảo mật).

> **Category/numbering của TC sinh từ EP/BVA theo kết quả mong đợi, không theo nguồn gốc rule** — giá trị hợp lệ (kể cả tại biên) mà hệ thống chấp nhận → **Business Rule** (100-199) hoặc **Edge Case** (400-499) tuỳ mức độ biên; giá trị không hợp lệ mà hệ thống từ chối/báo lỗi → luôn là **Negative** (300-399), dù rule đó nằm ở đâu trong tài liệu.

**Never Assume — block khi tài liệu thiếu thông tin:** nếu cần giá trị/quy tắc cụ thể cho 1 field, status, hay error code nhưng tài liệu không nêu rõ (vd không nói maxlength, không liệt kê hết mã lỗi) → DỪNG ngay tại đó, hỏi user:

> Tài liệu không nêu rõ **<field/behavior cụ thể>** cho `<feature>`. Bạn cung cấp giá trị/quy tắc, hay bỏ qua TC này?

Không tự suy đoán rồi ghi chú giả định — luôn hỏi trước khi viết TC dựa trên thông tin đó.

**Dữ liệu test phải cụ thể** — cấm mô tả chung chung kiểu "giá trị không hợp lệ", "dữ liệu sai định dạng". `Preconditions`/`Steps` phải nêu giá trị thật, lấy đúng field/kiểu dữ liệu của feature đang viết (vd field email → `email = "abc@"`, field số nguyên có ràng buộc ≥ 0 → giá trị `-1`).

Format mỗi TC:
```
### TC-NNN: <Title>
**Category**: <Happy Path | Business Rule | Security | Negative | Edge Case | UI State>
**Priority**: <P0 | P1 | P2 | P3>
**Severity**: <Critical | Major | Minor>
**Preconditions**: <điều kiện trước>
**Steps**: <các bước>
**Expected Results**: <kết quả mong đợi>
**Business Rule**: <rule từ tài liệu>
**Source**: <file + mục/section cụ thể trong business-scenario.md hoặc detail-design.md làm căn cứ>
```

> Mỗi TC phải truy nguyên được về 1 rule/behavior/field cụ thể trong tài liệu, ghi rõ ở **Source**. Không tự bịa field, API, error code, hay status không có trong tài liệu đã đọc.

**Trước khi chốt mỗi TC** (tự kiểm, không cần hỏi user): TC này có đang test đúng 1 điều kiện/field/flow duy nhất không (không gộp nhiều case vào 1 TC)? Input và Expected Result đã cụ thể chưa? Nếu câu trả lời đang là suy đoán (không có trong tài liệu, không có trong decision log) → áp dụng Never Assume, dừng hỏi user thay vì viết tiếp.

### Step A2.5 — Review nhanh trước khi lưu

Trước khi sang Step A3, tự rà lại toàn bộ TC vừa dựng theo checklist (âm thầm tự sửa, không cần hỏi user cho bước này — trừ trường hợp phát hiện thiếu thông tin thì áp dụng rule Never Assume ở Step A2):

- [ ] Mỗi TC có **Source** trỏ đúng về tài liệu đã đọc; không có field/API/error code nào không tồn tại trong docs.
- [ ] Business flow (từ business-scenario.md): có TC main success + ít nhất 1 TC mỗi nhánh phụ (alternate/exception) đã nêu trong tài liệu.
- [ ] Integration flow (gọi API/hệ thống ngoài, từ detail-design.md): có TC happy path + lỗi mỗi actor liên quan + timeout/retry nếu tài liệu có nêu.
- [ ] Feature loại API: mỗi endpoint trong `api-reference.md` có TC cho từng response/error code tài liệu liệt kê riêng cho endpoint đó, không chỉ happy path. **Đây là bước đối chiếu các TC đã viết ở trên — không tạo thêm 1 TC riêng chỉ để "note" đã cover đủ** (TC không có Steps/Expected Results thật là phantom TC, vi phạm mục bên dưới).
- [ ] Không có TC nào dùng dữ liệu mô tả chung chung.
- [ ] Số TC (TC-NNN) khớp đúng dải numbering của Category ghi trên TC đó (vd Category=Negative nhưng số lại rơi vào dải 100-199 là sai).
- [ ] Priority/Severity khớp đúng công thức risk (Likelihood × Impact) đã dùng ở Step A2 — không gán cảm tính.
- [ ] Số dòng Expected Results khớp đúng số bước Steps (1-1 mapping) — kết quả dòng thứ k là kết quả của bước thứ k.
- [ ] Steps chỉ mô tả hành động, không lẫn kết quả (không có "→", "sẽ hiển thị", "sẽ chuyển sang" trong Steps).
- [ ] Expected Results không tham chiếu số bước tài liệu gốc (vd "theo bước 3 luồng 3.1") **và không rò rỉ tham chiếu nội bộ của phiên làm việc** (vd "theo decision log", "theo Step A1.5 điểm 2") — decision log không được lưu vào file, tài liệu gốc tester không có sẵn khi thực thi; phải viết thẳng giá trị/hành vi cụ thể, tự đủ nghĩa.
- [ ] Không có ≥3 TC dùng chung hệt 1 bộ test data (pesticide paradox) — đa dạng hoá giá trị nếu có.
- [ ] Không có TC nào Steps rỗng hoặc <2 bước (phantom TC).
- [ ] Không có 2 TC test trùng đúng 1 rule/lỗi ở 2 category khác nhau — gộp lại nếu trùng.
- [ ] Section rủi ro cao (risk 6-9) không có ít TC hơn section rủi ro thấp (priority inversion).
- [ ] Mỗi màn hình mới trong lens UI State có 1 TC anchor mô tả tổng quan layout mặc định đứng đầu, trước các TC theo trạng thái/scenario cụ thể.
- [ ] Mỗi bước trong Steps bắt đầu bằng động từ hành động cụ thể + đối tượng rõ ràng (không mơ hồ kiểu "thao tác", "thực hiện").
- [ ] TC không phụ thuộc trạng thái để lại bởi TC khác — Preconditions tự đủ để chạy độc lập (không giả định "sau khi chạy TC-00X").

Sửa lại các TC vi phạm trước khi sang Step A3. Nếu sau **2 lần tự sửa** vẫn còn mục không đạt (do tài liệu không đủ thông tin để sửa đúng) → dừng, liệt kê rõ mục còn thiếu, hỏi user quyết định thay vì tiếp tục tự sửa.

### Step A3 — Xác nhận trước khi lưu

Hiển thị danh sách scenarios đã dựng:

> Tôi đã tạo **X scenarios** cho `<feature>`:
>
> | TC | Title | Category | Priority |
> |---|---|---|---|
> | TC-001 | ... | Happy Path | P0 |
> | ... | | | |
>
> **Lưu vào `automation_test/docs/features/<feature>/test-cases.md` và tiếp tục?**
> - **Có** — lưu
> - **Sửa** — cho tôi biết cần thêm / bớt / đổi TC nào
> - **Không** — dừng

Nếu user chọn **Sửa** và lý do KHÔNG phải do thiếu domain knowledge (trường hợp đó đã xử lý bằng Never Assume) mà do cách thiết kế/viết TC của skill (vd thiếu TC anchor, TC gộp nhiều case, thiếu case biên, thiếu nhóm case theo bảng ở Step A2...) → sau khi sửa xong, tự ghi 1 entry vào `automation_test/docs/scenario-learnings.md` (xem mục "Scenario Learnings" cuối file), không cần hỏi user.

Chờ xác nhận → lưu file → báo kết quả (Step A4).

### Step A4 — Báo kết quả

```
Đã lưu X test cases → automation_test/docs/features/<feature>/test-cases.md

⚠️  Status codes và response fields trong TC là giả định từ tài liệu —
    verify lại với curl/Postman trước khi automate để tránh fail do sai expected.

Bước tiếp theo:
  /autotest-web <feature>       # automate Web
  /autotest-android <feature>   # automate Android
  /autotest-ios <feature>       # automate iOS
  /autotest-api <feature>       # automate API
```

---

## Mode B — Convert từ file Excel

### Step B1 — Xác nhận file và feature

Nếu đường dẫn file chưa có → hỏi:
> Đường dẫn đến file Excel?

Kiểm tra file tồn tại:
```python
import os
path = "<xlsx_path>"
print("OK" if os.path.isfile(path) else f"ERROR: không tìm thấy {path}")
```

Nếu không tìm thấy → STOP, yêu cầu kiểm tra lại đường dẫn.

Nếu `<feature>` chưa có → chạy parser để lấy thông tin, rồi hỏi:
> Tìm thấy **{total} test cases** từ sheet `{sheet}`.
> Tên feature? (ví dụ: `login` hoặc `lending/phan-loai-khach-hang`)
> File sẽ lưu vào: `automation_test/docs/features/<feature>/test-cases.md`

### Step B2 — Cài đặt và parse

```bash
python3 -m pip show openpyxl > /dev/null 2>&1 || python3 -m pip install openpyxl -q
python3 .claude/skills/autotest-scenarios/scripts/tc_import.py "<xlsx_path>"
```

Nếu output chứa `"error"` → STOP. Hiển thị lỗi. Nguyên nhân thường gặp:
- File đang mở trong Excel (bị lock)
- Header row không có tên cột nhận dạng được (ID, Trường hợp kiểm thử, Các bước thực hiện, Kết quả mong muốn)

### Step B3 — Preview và xác nhận mapping

Hiển thị 3 TC đầu:
```
Preview (3 of N):

### TC-001: <title>
**Category**: <category>
**Steps**: <số bước> steps
**Expected**: <80 ký tự đầu>...
```

Hỏi: **"Mapping đúng chưa? (yes / fix)"**
- **fix** → hỏi cột nào bị sai, điều chỉnh rồi parse lại
- **yes** → tiếp tục Step B4

### Step B4 — Ghi file

```bash
python3 .claude/skills/autotest-scenarios/scripts/tc_import.py "<xlsx_path>" \
  --write "automation_test/docs/features/<feature>/test-cases.md" \
  --feature "<feature>"
```

Nếu file đã tồn tại → ghi đè, thông báo:
> Đã ghi đè `automation_test/docs/features/<feature>/test-cases.md`

### Step B5 — Báo kết quả

```
Đã lưu {total} test cases → automation_test/docs/features/<feature>/test-cases.md

Bước tiếp theo:
  /autotest-web <feature>       # automate Web
  /autotest-android <feature>   # automate Android
  /autotest-ios <feature>       # automate iOS
  /autotest-api <feature>       # automate API
```

---

## Column Mapping Reference (Mode B)

| Cột Excel (tiếng Việt) | TC field |
|---|---|
| ID / STT | Số thứ tự (không dùng làm label) |
| Mục đích kiểm thử | **Category** (merged cells → fill-down) |
| Trường hợp kiểm thử | **Title** → chuyển thành Snake_Case |
| Data test / Điều kiện | **Preconditions** |
| Các bước thực hiện | **Steps** (tách theo line break) |
| Kết quả mong muốn | **Expected Results** |
| Ghi chú | **Notes** (bỏ qua nếu rỗng) |

---

## Mode E — Sửa / cập nhật TC đã có

### Step E1 — Xác định TC cần sửa

Hỏi:
> TC nào cần sửa? (vd: `TC-003`, hoặc mô tả vấn đề cần thay đổi)

Đọc TC file, tìm đúng TC được chỉ định.

### Step E2 — Hiển thị nội dung hiện tại và đề xuất

Hiện nội dung TC hiện tại. Nếu user mô tả vấn đề → đề xuất nội dung mới.

> **TC-003 hiện tại:**
> (nội dung)
>
> **Đề xuất sửa thành:**
> (nội dung mới)
>
> Áp dụng? (có / sửa thêm / không)

Chờ xác nhận → ghi file.

---

## Mode D — Xoá TC

### Step D1 — Xác nhận trước khi xoá

Hiện TC cần xoá, hỏi xác nhận:

> **Xoá TC-NNN: `<title>`?**
> Hành động này không thể hoàn tác.
> (có / không)

Chờ xác nhận → xoá TC khỏi file, cập nhật file.

---

## Scenario Learnings (học tích luỹ qua các lần chạy)

File dùng chung mọi feature trong project: `automation_test/docs/scenario-learnings.md`.

- **Đọc trước khi thiết kế** — đầu Mode A (Step A1, trước A1.5), nếu file tồn tại → đọc toàn bộ, áp dụng mọi entry đã ghi khi viết TC ở Step A2, để không lặp lại lỗi đã bị user chỉ ra ở lần chạy trước.
- **Ghi sau khi sửa** — ở Step A3, khi user chọn **Sửa** vì lý do thuộc về cách skill thiết kế/viết TC (không phải do thiếu domain knowledge — trường hợp đó thuộc Never Assume), tự thêm 1 entry theo format:

```
### <ngày> — <feature>
**Issue**: <vấn đề user chỉ ra>
**Fix**: <cách đã sửa>
**Áp dụng khi**: <điều kiện để nhớ áp dụng lần sau, vd "mỗi màn hình mới trong lens UI State">
```

- Chỉ ghi lỗi thuộc về cách thiết kế/viết TC (thiếu TC anchor, TC gộp nhiều case, thiếu nhóm case, sai numbering...). Không ghi lỗi do thiếu tài liệu — Never Assume đã xử lý riêng bằng cách hỏi ngay tại chỗ.
- Không hỏi user trước khi ghi — đây là thao tác nội bộ, chỉ báo ngắn gọn trong Step A4 nếu có entry mới được thêm.

---

## Rules

- **Tên TC là hợp đồng** — không đổi tên, không diễn giải lại. `snake_name` derive cơ học từ title gốc.
- **Mode A**: mỗi TC phải truy nguyên được về 1 rule/behavior/field cụ thể trong tài liệu (ghi ở **Source**). Không tự bịa field, API, error code, hay status không có trong tài liệu.
- **Mode A — Never Assume**: thiếu thông tin cần cho TC (giá trị, giới hạn, mã lỗi) → hỏi user ngay tại chỗ, không tự suy đoán rồi ghi giả định.
- **Mode A — đối chiếu tài liệu**: nếu business-scenario.md và detail-design.md mâu thuẫn hoặc có orphan/logic issue/completeness gap ảnh hưởng đến TC → hỏi user chọn nguồn chính trước khi viết TC liên quan (Step A1.5), ghi lại thành decision log áp dụng nhất quán.
- **Mode A — dữ liệu test cụ thể**: cấm mô tả chung chung ("giá trị không hợp lệ"); luôn nêu giá trị thật trong Preconditions/Steps.
- **Mode A — Steps/Expected 1-1**: số bước trong Steps phải khớp số dòng trong Expected Results, kết quả dòng thứ k tương ứng đúng bước thứ k.
- **Mode A — tách hành động khỏi kết quả**: Steps chỉ mô tả HÀNH ĐỘNG (nhập gì, bấm gì); cấm các cụm nối kết quả trong Steps ("→", "sẽ hiển thị", "sẽ chuyển sang", "thì sẽ") — phần đó phải chuyển sang Expected Results.
- **Mode A — Expected Result tự đủ nghĩa**: cấm viết dạng tham chiếu số bước tài liệu gốc ("theo bước 3 luồng 3.1") hoặc tham chiếu nội bộ phiên làm việc ("theo decision log", "theo Step A1.5"); phải diễn đạt bằng hành động/kết quả cụ thể để đọc độc lập không cần mở lại tài liệu hay biết bối cảnh phiên chạy. Field `Source`/`Business Rule` vẫn được phép ghi rationale/audit (vd "chọn theo quyết định user ở Step A1.5") vì đây là field truy nguyên, không phải nội dung tester thực thi.
- **Mode A — anchor TC màn hình**: mỗi màn hình mới xuất hiện trong scope, TC đầu tiên trong dải UI State (500-599) phải là 1 TC mô tả tổng quan layout mặc định (đủ thành phần hiển thị) trước các TC theo trạng thái/scenario cụ thể.
- **Mode A — scenario learnings**: đọc `automation_test/docs/scenario-learnings.md` (nếu có) trước khi thiết kế TC; ghi entry mới sau khi user chỉ ra lỗi thuộc cách thiết kế/viết TC (không phải thiếu tài liệu).
- **Mode B**: parser xử lý tự động merged cells, fill-down category, multi-row TC. Không đọc lại Excel thủ công.
- **Priority mặc định P1** cho Mode B — Excel thường không có cột priority.
- **Không ghi đè mà không thông báo** — luôn hiện thông báo khi overwrite.