---
name: autotest-project-docs
description: Tạo mới hoặc cập nhật domain knowledge cho project — từ Confluence, từ file/text, hoặc AI tự tạo từ câu hỏi. Quản lý cấu trúc automation_test/docs/ cho các skill autotest-*.
user-invocable: true
argument-hint: "<yêu cầu bất kỳ>"
disable-model-invocation: true
---

# Project Docs Agent

Khởi tạo domain knowledge cho project mới. Chạy **một lần duy nhất** khi bắt đầu project.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user trong lúc làm việc — tiến trình, câu hỏi, cảnh báo, tóm tắt kết quả — viết bằng **tiếng Việt**. Giữ nguyên thuật ngữ kỹ thuật (Confluence, API, endpoint...) không dịch.

> **Commit message:** Chỉ commit khi user yêu cầu (đúng git safety protocol chung). Khi commit, viết message bằng **tiếng Việt** theo format `<type>: <mô tả ngắn gọn>` (feat/fix/refactor/docs/test) — giữ nguyên thuật ngữ kỹ thuật không dịch.

> **Vị trí lưu trữ:** Toàn bộ domain knowledge nằm trong `automation_test/docs/` — file chung (`global-data.md`, `product-overview.md`, `api-reference.md`, `system-overview.md`) nằm ngay trong `automation_test/docs/`; file riêng cho từng chức năng (`business-scenario.md`, `detail-design.md`) nằm trong `automation_test/docs/features/<feature>/`. Thư mục này độc lập với `.vsaf/` của VSAF framework (`planning-artifacts/`, `srs/`, `testcases/`...) — autotest-project-docs chỉ quản lý `automation_test/docs/`, không đụng tới `.vsaf/`.
>
> **Feature identifier có thể lồng nhau** (vd: `farm/product-management`, không chỉ `<feature>` phẳng) khi module hierarchy của project cần — các skill đọc `automation_test/docs/features/` sẽ duyệt dần các prefix ngắn hơn để tìm doc gần nhất, nên độ sâu nesting linh hoạt.

### Ví dụ mẫu (tham khảo cấu trúc)

Layout thật của `automation_test/docs/` cho một project B2B Agritech (Freso — kết nối nhà cung cấp nông sản với nhà hàng):

```
automation_test/docs/
  global-data.md              # Environment, credentials, test accounts
  system-overview.md          # Kiến trúc & luồng tổng quan
  api-reference.md            # Endpoint catalog
  features/
    farm/product-management/
      business-scenario.md    # Business rules & test scenarios
      detail-design.md        # Technical specs, API & DB schema
    restaurant/home-page/product-listing-page-by-category/
      business-scenario.md
      detail-design.md
```

Đoạn mẫu ngắn cho từng loại file:

**`global-data.md`**
```markdown
# Global Test Data & Environment Configurations

## 1. Staging Environment
### Restaurant Module (Buyer)
- **Login URL:** `http://gw-staging.digital.vn/freso/buyer/chon-chi-nhanh`
- **Credentials:** Login Name `NHNGA2`, Phone `0338952995`, Password `123456Aa@`
```

**`api-reference.md`**
```markdown
## Authentication (No Auth Required)
| Method | Endpoint            | Body                 | Response                       |
|--------|----------------------|----------------------|--------------------------------|
| POST   | /api/auth/login      | { email, password }  | { token, user: { id, email } } |
```

**`system-overview.md`**
```markdown
## 2. General Description & Target Users
Nền tảng thương mại điện tử nông sản với 3 nhóm user chính:
* **Farm/Supplier:** phân phối & bán nông sản trên platform.
* **Restaurant:** mua nông sản qua app/web.
* **VDS (Viettel Digital Services):** admin, CSKH, phát triển kinh doanh.
```

**`features/<feature>/business-scenario.md`**
```markdown
## Luồng nghiệp vụ: Farm Onboarding
1. Business staff khởi tạo danh mục hồ sơ yêu cầu.
2. Farm đăng ký tài khoản, upload hồ sơ.
3. Business staff review & ký hợp đồng.
4. Hệ thống tạo admin account, gửi credentials cho Farm.
```

**`features/<feature>/detail-design.md`**
```markdown
## Data Entities
* **PRODUCT:** `product_id`, `name`, `description`, `category_id`, `wallet_id`.
* **FARM:** `farm_id`, `name`, `address`, `category`.
```

> Đây chỉ là ví dụ minh hoạ cấu trúc — không phải nơi lưu domain knowledge thật của project hiện tại.

## Argument Parsing

Nhận **tên project** hoặc **ngôn ngữ tự nhiên** — không cần đúng format cố định.

```
/autotest-project-docs viettelmoney                              # structured
/autotest-project-docs tạo tài liệu cho project shopee          # ngôn ngữ tự nhiên
/autotest-project-docs                                           # trống → hỏi tên project
```

Parse `$ARGUMENTS`:
- **Trống** → hỏi: "Tên project là gì? (vd: viettelmoney, shopee, saucedemo)"
- **Có argument** → trích xuất `PROJECT_NAME` (chỉ dùng để hiển thị/label, không ảnh hưởng đường dẫn lưu file); nếu không xác định được → hỏi như trên

---

## Step 0 — Kiểm tra domain docs đã tồn tại chưa

```python
import glob
existing = (
    glob.glob('automation_test/docs/global-data.md')
    + glob.glob('automation_test/docs/product-overview.md')
    + glob.glob('automation_test/docs/api-reference.md')
    + glob.glob('automation_test/docs/system-overview.md')
    + glob.glob('automation_test/docs/features/**/*.md', recursive=True)
)
print('\n'.join(existing) or 'NONE')
```

**Nếu đã có** → hỏi:

> Đã tìm thấy domain docs trong `automation_test/docs/`
>
> **1** — Cập nhật / bổ sung thêm tài liệu
> **2** — Tạo mới hoàn toàn (xoá và tạo lại)

- Chọn **1** → bỏ qua Step 1, vào Step 2 ngay (thêm tài liệu vào docs hiện có)
- Chọn **2** → xoá các file domain docs cũ trong `automation_test/docs/`, tạo lại từ đầu (thư mục `.vsaf/` của VSAF framework — `planning-artifacts/`, `srs/`, `testcases/`, `KNOWLEDGE.md`, `STATUS.md`... — nằm ngoài `automation_test/docs/` nên không bị ảnh hưởng)

**Nếu chưa có** → tạo thư mục và bảo vệ credentials, rồi tiếp tục Step 1:

```bash
mkdir -p automation_test/docs/features
grep -qxF 'automation_test/docs/global-data.md' .gitignore 2>/dev/null || echo 'automation_test/docs/global-data.md' >> .gitignore
```

(Tạo `.gitignore` ở root project nếu chưa có.)

---

## Step 1 — Chọn nguồn tài liệu

Hỏi user **một câu**:

> Khởi tạo domain knowledge cho **`<PROJECT_NAME>`** — bạn có tài liệu spec không?
>
> **1** — Có trên Confluence (truyền link, tôi tự fetch)
> **2** — Có file hoặc text (paste nội dung vào đây, hoặc cho đường dẫn file)
> **3** — Chưa có — để AI hỏi và tạo

- Chọn **1** → **Mode A: Confluence**
- Chọn **2** → **Mode B: File / Text**
- Chọn **3** → **Mode C: AI Generate**

---

## Mode A — Từ Confluence

### Step A1 — Thu thập credentials (nếu chưa có)

Đọc `automation_test/docs/global-data.md` tìm section `## Confluence`.

**Nếu chưa có credentials** → hỏi một lần:

> **Confluence Setup** — cần thông tin để kết nối:
>
> 1. **Base URL** — vd: `http://10.254.136.35:8090`
> 2. **Personal Access Token** — Settings → Personal Access Tokens

Lưu vào `global-data.md`:
```markdown
## Confluence
- **Base URL:** `<base_url>`
- **Token:** `<token>`
```

Bảo vệ token (idempotent, phòng trường hợp Step 0 chưa chạy):
```bash
grep -qxF 'automation_test/docs/global-data.md' .gitignore 2>/dev/null || echo 'automation_test/docs/global-data.md' >> .gitignore
```

### Step A2 — Nhận link và fetch

Hỏi:
> Paste link Confluence (có thể nhiều link, mỗi link 1 dòng):

Với mỗi link → chạy fetch script:

```bash
python3 .claude/skills/autotest-project-docs/scripts/confluence_fetch.py \
  --base-url "<base_url>" --token "<token>" \
  --url "<url>"
```

Nếu kết quả `"is_index": true` → tự fetch tất cả trang con:
```bash
python3 .claude/skills/autotest-project-docs/scripts/confluence_fetch.py \
  --base-url "<base_url>" --token "<token>" \
  --page-ids <id1> <id2> ...
```

Với mỗi trang fetched → auto-classify và lưu (xem Step A3).

### Step A3 — Classify và lưu

Auto-classify dựa trên title + ancestors + content:

| Tín hiệu | Doc type | Lưu vào |
|---|---|---|
| "API", "endpoint", "REST", "Swagger" | `api-reference` | `automation_test/docs/api-reference.md` |
| "tổng quan", "overview", "giới thiệu sản phẩm" | `product-overview` | `automation_test/docs/product-overview.md` |
| "kiến trúc", "architecture" | `system-overview` | `automation_test/docs/system-overview.md` |
| "nghiệp vụ", "luồng", "user story", "kịch bản" | `business-scenario` | `automation_test/docs/features/<feature>/business-scenario.md` |
| "thiết kế kỹ thuật", "technical design", "DB schema" | `detail-design` | `automation_test/docs/features/<feature>/detail-design.md` |

**Nếu ambiguous** → hỏi user classify. **Nếu rõ ràng** → lưu thẳng, thông báo:
> Auto-saved: `<path>` (classified as `<type>`)

Sau khi fetch hết → báo tổng kết và tiếp tục Step 3.

---

## Mode B — Từ file hoặc text

### Step B1 — Nhận nội dung

Hỏi:
> Paste nội dung tài liệu vào đây, hoặc cho đường dẫn file (`.md`, `.txt`, `.pdf`, `.docx`):

**Nếu là đường dẫn file:**
```python
import os
path = "<input>"
exists = os.path.isfile(path)
ext = os.path.splitext(path)[1].lower()
```

- `.md` / `.txt` → đọc trực tiếp
- `.pdf` → dùng `pdfminer` hoặc `pypdf2`:
  ```bash
  python3 -m pip install pypdf2 -q
  python3 -c "import PyPDF2; r=PyPDF2.PdfReader('<path>'); print('\n'.join(p.extract_text() for p in r.pages))"
  ```
- `.docx` → dùng `python-docx`:
  ```bash
  python3 -m pip install python-docx -q
  python3 -c "import docx; d=docx.Document('<path>'); print('\n'.join(p.text for p in d.paragraphs))"
  ```

**Nếu là text paste** → dùng trực tiếp.

### Step B2 — Classify và lưu

Phân tích nội dung → auto-classify → lưu vào đúng file trong `automation_test/docs/` (theo bảng phân loại ở Step A3).

Nếu một đoạn text chứa nhiều loại (vd: vừa có tổng quan vừa có API list) → tách thành nhiều file.

Thông báo mỗi file đã lưu. Hỏi:
> Bạn có thêm tài liệu nào khác không? (paste tiếp, hoặc gõ **xong**)

Lặp lại đến khi user gõ "xong" → tiếp tục Step 3.

---

## Mode C — AI tự tạo

### Step C1 — Hỏi 5 câu trong 1 message

> **Tạo domain knowledge cho `<PROJECT_NAME>`**
>
> Trả lời những gì bạn biết — gõ **skip** để bỏ qua:
>
> 1. **Mô tả sản phẩm** — sản phẩm này làm gì, đối tượng người dùng là ai?
> 2. **Base URL** — URL của môi trường test (vd: `https://staging.example.com`)
> 3. **Xác thực** — cách login: username/password? OAuth? API key? Không cần auth?
>    - Nếu có login: endpoint login, field username, field password, field token trong response
> 4. **Tính năng chính** — liệt kê các module/feature chính của project (vd: login, products, cart, checkout)
> 5. **Thông tin bổ sung** — platform (web/android/ios/api), môi trường, bất kỳ context nào thêm

Chờ user trả lời.

### Step C2 — Tạo domain files

Từ câu trả lời → tạo các file:

**`automation_test/docs/global-data.md`**:
```markdown
# Global Data — <PROJECT_NAME>

## Environment
- **Base URL:** `<base_url>`
- **Platform:** <web | android | ios | api>

## Authentication
- **Login endpoint:** `<ep_login>` (hoặc `none` nếu không cần)
- **Username field:** `<field>`
- **Password field:** `<field>`
- **Token field:** `<field>`

## Test Credentials
- **Username:** `<username>`
- **Password:** `<password>`
```

**`automation_test/docs/product-overview.md`** (nếu user cung cấp mô tả):
```markdown
# Product Overview — <PROJECT_NAME>

<tóm tắt từ câu trả lời Q1>

## Tính năng chính
<list từ Q4>
```

---

## Step 3 — Báo kết quả và hướng dẫn bước tiếp

```
✅ Domain knowledge đã sẵn sàng cho project <PROJECT_NAME>

Files đã tạo:
  automation_test/docs/
    global-data.md          ← credentials & environment (đã gitignore)
    product-overview.md     ← (nếu có)
    api-reference.md        ← (nếu có)
    system-overview.md      ← (nếu có)
    features/
      <feature>/
        business-scenario.md  ← (nếu có)
        detail-design.md      ← (nếu có)

Bước tiếp theo:
  /autotest-scenarios <feature>    ← tạo kịch bản kiểm thử
  /autotest-strategy <feature>       ← phân tích & chiến lược
  /autotest-web <feature>              ← automate (hoặc /autotest-api / /autotest-android / /autotest-ios)
```

---

## Rules

- **Không ghi đè global-data.md mà không xác nhận** — file này chứa credentials thật.
- **gitignore `automation_test/docs/global-data.md` ngay khi tạo** — không để token bị commit.
- **Auto-classify khi đủ tín hiệu** — chỉ hỏi user khi thực sự ambiguous.
- **Mode B hỗ trợ nhiều lần paste** — user có thể truyền từng tài liệu một cho đến khi gõ "xong".
- **Mode A có thể nhận nhiều link** — fetch và classify từng link, không giới hạn số lượng.
- **Đường dẫn cố định `automation_test/docs/`** — không tạo folder riêng theo tên project; một repo chỉ có một bộ domain docs. File chung ở top-level, file theo feature ở `automation_test/docs/features/<feature>/`.