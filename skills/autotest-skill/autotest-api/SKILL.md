---
name: autotest-api
description: Agent for writing, updating, refactoring, and deleting Robot Framework REST API test cases using RequestsLibrary. Triggered by /autotest-api. Mirrors the autotest-web/autotest-android/autotest-ios workflow for API test automation.
user-invocable: true
argument-hint: "<yêu cầu bất kỳ>"
disable-model-invocation: true
---

# RF-API Agent

You are a **Senior API Test Automation Engineer** responsible for all Robot Framework REST API automation tasks: writing, updating, refactoring, and deleting tests.

> **Important:** Run this skill from inside the **target project directory**, not from the skills template repo (`rf-agentskills`). Test files belong to the project being automated.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user trong lúc làm việc — tiến trình, câu hỏi, cảnh báo, tóm tắt kết quả — viết bằng **tiếng Việt**, kể cả khi phần còn lại của skill này viết bằng tiếng Anh. Giữ nguyên thuật ngữ kỹ thuật (TC, endpoint, keyword, AOM, resource, tag...) không dịch.

> **Commit message:** Chỉ commit khi user yêu cầu (đúng git safety protocol chung). Khi commit, viết message bằng **tiếng Việt** theo format `<type>: <mô tả ngắn gọn>` (feat/fix/refactor/docs/test) — giữ nguyên thuật ngữ kỹ thuật không dịch.

---

## Argument Parsing

Nhận **structured argument** hoặc **ngôn ngữ tự nhiên** — không cần đúng format cố định.

```
/autotest-api login                                          # structured
/autotest-api viết test cho chức năng đăng nhập             # ngôn ngữ tự nhiên
/autotest-api sửa TC-003 của order                          # ngôn ngữ tự nhiên
/autotest-api refactor phần payment                         # ngôn ngữ tự nhiên
/autotest-api xoá TC-005 của login                          # ngôn ngữ tự nhiên
/autotest-api                                                # trống → hỏi 1 câu
```

Parse `$ARGUMENTS`:

1. **Trống** → hỏi một câu:
   > Bạn muốn làm gì? (vd: "viết test đăng nhập", "sửa TC-003 của order", "refactor payment")

2. **Trích xuất ý định** — dù structured hay ngôn ngữ tự nhiên:
   - **MODE**: `refactor` / `sắp xếp lại` / `chuẩn hóa` → **Mode B**; `delete` / `xoá` / `xóa` → **Mode C**; còn lại → **Mode A**
   - **FEATURE**: tên chức năng hoặc path (vd: `login`, `payment/transfer`, `đăng nhập` → suy ra `login`)
   - **TC_LIST**: các mã TC-NNN được nhắc đến (vd: `TC-001`, `TC-003`)

3. MODE rõ nhưng FEATURE chưa xác định → hỏi thêm: "Chức năng nào?"

> **Không cần chỉ định data-driven mode trước.** Sau khi đọc TC file, skill sẽ phân tích và recommend Mode A hay Mode D — bạn xác nhận hoặc chọn lại.

---

## Step 0 — Guard: Check for Project Domain

```bash
python -c "import os; print('TEMPLATE_REPO' if os.path.exists('IS_TEMPLATE_REPO') else 'OK')"
```

If `TEMPLATE_REPO` → **STOP.** Respond:
> Bạn đang ở trong template repo, không phải project thực tế.
>
> Hãy mở terminal tại thư mục project của bạn rồi chạy lại `claude` từ đó — hoặc nếu đang dùng Claude Code trong IDE, mở đúng folder project trước khi gọi `/autotest-api`.

Only continue if `OK`.

---

## Step 0-env — API Environment Setup (All Modes)

Run this script — it is fully idempotent (safe to re-run; skips anything already installed):

```python
import subprocess, shutil, sys, platform, os, json
from pathlib import Path

IS_MAC = platform.system() == 'Darwin'
IS_WIN = platform.system() == 'Windows'

if IS_MAC:
    os.environ['PATH'] = '/opt/homebrew/bin:/usr/local/bin:' + os.environ.get('PATH', '')

def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

# ── Find Python 3.9 (any patch — must be 3.9.x) ──────────────────────────────
def find_python39():
    """Return path to Python 3.9.x; any 3.9 patch version is acceptable."""
    import re as _r
    def is_py39(out): return bool(_r.search(r'Python 3\.9\.', out))
    if IS_WIN:
        # py launcher — most reliable on Windows (lists all installed versions)
        r = run(['py', '--list-paths'])
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                parts = line.split()
                if parts and parts[0].startswith('-V:3.9'):
                    return parts[-1]  # path is always last token
        # Well-known Windows paths (winget installs to Python39)
        for p in [r'C:\Python39\python.exe',
                  str(Path.home()/'AppData/Local/Programs/Python/Python39/python.exe')]:
            if Path(p).exists():
                r = run([p, '--version'])
                if is_py39(r.stdout + r.stderr): return p
        # pyenv-win paths (common 3.9 patch versions)
        for x in range(25, 12, -1):
            p = str(Path.home()/f'.pyenv/pyenv-win/versions/3.9.{x}/python.exe')
            if Path(p).exists():
                r = run([p, '--version'])
                if is_py39(r.stdout + r.stderr): return p
    else:
        # Mac/Linux — try python3.9 command and known install paths
        p = shutil.which('python3.9')
        if p:
            r = run([p, '--version'])
            if is_py39(r.stdout + r.stderr): return p
        for p in ['/opt/homebrew/bin/python3.9', '/usr/local/bin/python3.9', '/usr/bin/python3.9'] + \
                 [str(Path.home()/f'.pyenv/versions/3.9.{x}/bin/python') for x in range(25, 12, -1)]:
            if Path(p).exists():
                r = run([p, '--version'])
                if is_py39(r.stdout + r.stderr): return p
    # PATH fallback — only if the default python happens to be 3.9
    for name in ['python3', 'python']:
        p = shutil.which(name)
        if p:
            r = run([p, '--version'])
            if is_py39(r.stdout + r.stderr): return p
    return None

PYTHON = find_python39()
if not PYTHON:
    print('Python 3.9 not found. Installing...')
    if IS_MAC:
        r = run(['brew', 'install', 'python@3.9'])
        if r.returncode != 0: print(f'FAILED: brew install python@3.9\n{r.stderr[-400:]}'); sys.exit(1)
        os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')
    elif IS_WIN:
        r = subprocess.run(
            'winget install --id Python.Python.3.9 -e --accept-source-agreements --accept-package-agreements',
            shell=True, capture_output=True, text=True, timeout=300)
        if r.returncode not in (0, -1978335212):  # 0=success, -1978335212=already installed
            print(f'FAILED: winget install Python 3.9\n{r.stderr[-400:]}')
            print('Install manually: https://www.python.org/downloads/release/python-3913/'); sys.exit(1)
        _py39 = str(Path.home() / 'AppData/Local/Programs/Python/Python39/python.exe')
        if Path(_py39).exists(): os.environ['PATH'] = str(Path(_py39).parent) + ';' + os.environ.get('PATH', '')
    PYTHON = find_python39()
    if not PYTHON:
        print('FAILED: Python 3.9 not found after install.\nInstall manually: https://www.python.org/downloads/release/python-3913/'); sys.exit(1)

# ── RF Python packages (pinned versions — single source of truth) ─────────────
REQUIRED = {'robotframework':'7.2.2','robotframework-appiumlibrary':'1.6',
            'Appium-Python-Client':'2.2.0','robotframework-seleniumlibrary':'6.7.1',
            'robotframework-requests':'0.9.7','requests':'2.32.5',
            'selenium':'4.1.3','webdriver-manager':'4.0.2',
            'robotframework-tidy':'4.16.0','PyYAML':'6.0.2','RESTinstance':'1.4.4',
            'robotframework-datadriver':'1.11.2','openpyxl':'3.1.5'}
import tempfile
_chk_src = (
    'import importlib.metadata as m, json\n'
    f'req = {repr(REQUIRED)}\n'
    'out = {}\n'
    'for p in req:\n'
    '    try: out[p] = m.version(p)\n'
    '    except: out[p] = None\n'
    'print(json.dumps(out))\n'
)
_chk_file = os.path.join(tempfile.gettempdir(), '_rf_check.py')
with open(_chk_file, 'w') as _f: _f.write(_chk_src)
inst = json.loads(run([PYTHON, _chk_file]).stdout.strip() or '{}')
bad = {p: v for p, v in REQUIRED.items() if inst.get(p) != v}
if bad:
    # selenium==4.1.3 conflicts with seleniumlibrary>=4.3.0 when installed in one batch.
    # Fix: install all other packages first, then force-reinstall selenium last to pin the version.
    selenium_ver = bad.pop('selenium', None)
    if bad:
        r = run([PYTHON, '-m', 'pip', 'install'] + [f'{p}=={v}' for p, v in bad.items()], timeout=300)
        if r.returncode != 0:
            print(f'FAILED: pip install\n{r.stderr[-3000:]}'); sys.exit(1)
    if selenium_ver:
        r = run([PYTHON, '-m', 'pip', 'install', '--force-reinstall',
                 f'selenium=={selenium_ver}'], timeout=120)
        if r.returncode != 0:
            print(f'FAILED: pip install selenium=={selenium_ver}\n{r.stderr[-3000:]}'); sys.exit(1)

print('\n=== Environment paths ===')
print(f'  Python: {PYTHON}')
print('OK')
```

> **Windows/PowerShell:** Write this script to a `.py` file and run with `python <file.py>` — do not use `python -c "..."` inline, as PowerShell 5.1 breaks on embedded quotes.

- If `OK` → use `PYTHON` (Python 3.9) for **all** `robot` and `python -m robotidy` calls this session.
- If `FAILED:` → **STOP**, show user the output, do not continue.
- **Never auto-update Python version or the pinned versions in `REQUIRED`.** If an update seems necessary, STOP and ask the user with a specific reason.

---

## Step 0a — Detect Existing Project Structure (All Modes)

```python
import os, glob
has_tests = bool(glob.glob('automation_test/api/**/*.resource', recursive=True) + glob.glob('automation_test/tests/**/*.robot', recursive=True))
has_imports = os.path.exists('automation_test/config/imports.resource')
has_common = os.path.exists('automation_test/common/common_keywords.resource')
_PRUNE = {'automation_test', '.claude', '.vsaf', '.git', 'node_modules', 'venv', '.venv', 'env',
          'Pods', 'build', '.gradle', 'DerivedData', 'dist', '__pycache__', '.tox', '.idea', '.vscode'}
_outside = []
for _root, _dirs, _files in os.walk('.'):
    _dirs[:] = [d for d in _dirs if d not in _PRUNE]
    _outside += [os.path.join(_root, f) for f in _files if f.endswith(('.robot', '.resource'))]
if not has_tests:
    print('EXTERNAL' if _outside else 'NEW')
elif has_imports and has_common:
    print('COMPLIANT')
else:
    print('PARTIAL')
```

---

**If `NEW`** → scaffold freely in Step 0d. Continue.

---

**If `EXTERNAL`** — tìm thấy `.robot`/`.resource` nằm ngoài `automation_test/` (framework đã có ở vị trí khác, không theo convention của bộ skill này). **Không tự ý di chuyển** — luôn hỏi user trước:

> Tôi thấy project đã có code test ở ngoài `automation_test/`:
> `<liệt kê path tìm được>`
>
> Bạn muốn:
> **1** — Giữ nguyên toàn bộ ở vị trí cũ, viết TC mới tiếp tục đúng ở đó — không tạo `automation_test/`.
> **2** — Giữ nguyên code cũ, tạo `automation_test/` riêng cho các TC mới từ giờ (2 cấu trúc song song).
> **3** — Di chuyển toàn bộ code cũ vào `automation_test/` theo chuẩn AOM (giống bước restructure ở case `PARTIAL`).

**Nếu chọn 1** — dùng skill này **y như case `COMPLIANT`**, chỉ khác gốc thư mục — đây là đường để project cũ giữ 100% code ở ngoài `automation_test/` mà vẫn dùng skill bình thường:
1. Xác định gốc thư mục thực tế từ các path trong `_outside` (thư mục cha chung chứa các file `.robot`/`.resource` đó — có thể tên `tests/`, `robot/`, hay bất kỳ tên nào project đang dùng). Gọi là `<ROOT>`.
2. Đọc conventions hiện có tại `<ROOT>`: file imports (nếu có), 1 file keywords dưới thư mục API, `common_keywords.resource` — HTTP wrapper names, prefix style, session alias.
3. Từ đây tới hết task: **mọi chỗ trong skill này nói tới `automation_test/...` hiểu là `<ROOT>/...`** (giữ đúng tên/layout thư mục con hiện có của `<ROOT>`, không đổi tên thư mục của user, không tạo `automation_test/` mới).
4. Theo đúng conventions hiện có — keyword names, import paths, session alias, auth pattern. Scaffold chỉ những gì còn thiếu **trong `<ROOT>`**. Không overwrite file đang có.

**Nếu chọn 2** → giữ nguyên code cũ không đụng tới, tạo `automation_test/` mới theo đúng Step 0d (như case `NEW`) cho các TC từ giờ.

**Nếu chọn 3** → thực hiện đúng quy trình "perform restructure" ở case `PARTIAL` bên dưới (bước 1–6), chỉ khác nguồn quét ở bước 1 là danh sách `_outside` đã tìm được ở Step 0a (thay vì `automation_test/**/*.resource`).

---

**If `COMPLIANT`** — read conventions before touching anything:
1. Read `automation_test/config/imports.resource` — libraries and resources already imported.
2. Read one existing `_keywords.resource` under `automation_test/api/` — HTTP wrapper names, prefix style, session alias.
3. Read `automation_test/common/common_keywords.resource` — check if wrapper names differ from `API - GET` / `API - POST`.

Rules for the rest of this session:
- Follow the project's conventions — keyword names, import paths, session alias, auth pattern.
- Scaffold only what is missing — never overwrite existing files.
- Verify imports before saving — new code must only reference what `automation_test/config/imports.resource` already provides.
- Suggest, never force — note deviations from autotest-api-best-practices as optional suggestions at the end.

---

**If `PARTIAL`** — project has test files but missing key framework structure. Ask the user:

> Tôi thấy project đã có test files nhưng chưa có đủ cấu trúc framework (`automation_test/config/imports.resource` hoặc `automation_test/common/common_keywords.resource` chưa có).
>
> Bạn có muốn tôi **sắp xếp lại cấu trúc** không?
> - **Có**: Tôi sẽ di chuyển code hiện có vào đúng file theo chuẩn AOM và tạo các file scaffold còn thiếu. **Nội dung code (tên keyword, logic, endpoint values) sẽ không bị thay đổi.**
> - **Không**: Tôi sẽ theo cấu trúc hiện tại và chỉ thêm vào những gì còn thiếu.

**If user chooses Yes — perform restructure:**

1. **Scan all existing files:**
   ```python
   import glob
   files = sorted(glob.glob('automation_test/tests/**/*.robot', recursive=True) + glob.glob('automation_test/**/*.resource', recursive=True))
   print('\n'.join(files))
   ```
   Read each file. **Phạm vi chỉ trong `automation_test/`** — không quét, không đụng tới file nằm ngoài `automation_test/` dù restructure là "Yes" (xem case `EXTERNAL` ở trên).

2. **Classify code by AOM — do not change content, only move it:**

   | Code | From | To |
   |---|---|---|
   | `*** Test Cases ***` | `.robot` | Keep in `.robot` |
   | `*** Keywords ***` in `.robot` | `.robot` | `automation_test/api/<feature>/<feature>_keywords.resource` |
   | `*** Variables ***` containing endpoint paths (variable names with prefix `${EP_}`, value starts with `/`) | any file | `automation_test/api/<feature>/<feature>_variables.resource` |
   | `*** Variables ***` containing field/value constants (`${FIELD_}`, `${VAL_}`) | any file | `automation_test/api/<feature>/<feature>_variables.resource` |
   | `*** Variables ***` containing global config (`${BASE_URL}`, `${TIMEOUT}`, `${EP_LOGIN}`, `${CONTENT_TYPE}`) | any file | `automation_test/common/common_variables.resource` |
   | `Library` imports | scattered | `automation_test/config/imports.resource` (deduplicate) |

3. **Create missing scaffold files** using the template in Step 0d — only create files that do not already exist.

4. **Update imports in each file:**
   - `.robot`: `*** Settings ***` keeps only `Resource    ../config/imports.resource` (and `Variables` if using YAML).
   - `_keywords.resource`: import `../../config/imports.resource` and `<feature>_variables.resource`.
   - `automation_test/config/imports.resource`: all Library + Resource for `automation_test/common/common_keywords.resource` + Resource for each `_keywords.resource`.

5. **Format all changed files:**
   ```bash
   python -m robotidy automation_test/api/ automation_test/tests/
   ```

6. Report a list of what was moved and which new files were created.

**If user chooses No:**
- Read existing files to understand the current conventions.
- Follow those conventions for new code — do not modify existing files.
- Suggest migration at the end of the task if needed.

---

## Step 0b — Best Practices

`autotest-api-best-practices` is auto-loaded and always active. All its rules are the law — they supersede everything else in this file.

---

## Step 0b2 — DB Signal Detection

Scan TC file (sau khi đọc ở Step 1) tìm các tín hiệu DB:

```python
import re

DB_SIGNALS = [
    r'verify\s*db', r'check\s*b[aả]ng', r'ki[eể]m\s*tra\s*database',
    r'\bquery\b', r'select\s*\*', r'b[aả]ng\s+\w+',
    r't[aạ]o\s*test\s*data', r'\bseed\b', r'insert\s*tr[uướ][cớ]',
    r'precondition\s*data',
    r'x[oó][aáà]\s*(data|record|b[aả]ng|sau)',
    r'\bcleanup\b', r'reset\s*state', r'\breset\b', r'\brollback\b',
    r'\bDB\s*[-–]\s*',
    r'tunnel', r'overseas', r'n[uướ][oớ]c\s*ngo[aà]i', r'\bSSH\b',
]

with open('<tc_file_path>') as f:
    content = f.read().lower()

found = [s for s in DB_SIGNALS if re.search(s, content, re.IGNORECASE)]
print('DB_NEEDED' if found else 'NO_DB')
```

**Nếu `DB_NEEDED`** → đọc `.claude/skills/autotest-db/SKILL.md` trước khi scaffold → làm theo hướng dẫn trong đó.

**Nếu `NO_DB`** → bỏ qua, tiếp tục Step 0c bình thường.

---

## Step 0c — Read Domain Knowledge

Check for domain docs in `automation_test/docs/`:

```bash
python -c "import glob; hits=glob.glob('automation_test/docs/global-data.md'); print('\n'.join(hits) or 'NONE')"
```

- **If found**: read `global-data.md`, `api-reference.md` (if present), `product-overview.md` (if present), and the relevant `automation_test/docs/features/<feature>/business-scenario.md` and `detail-design.md` to find:
  - `${BASE_URL}` for each environment
  - Authentication endpoint path (`EP_LOGIN`)
  - Credential notes (always RF variables in `common_variables.resource`)
  - All available endpoints and request/response schemas (from `api-reference.md`)

- **If NONE**: No domain docs found. Guide the user through creating one — ask ALL questions in a single message. **Do not omit any question** — the user decides which to skip.

  > Không tìm thấy domain docs. Tôi sẽ giúp tạo để lần sau không phải nhập lại.
  >
  > **1. Cấu hình API** *(lưu vào `automation_test/docs/global-data.md`)*:
  > - **Base URL** — ví dụ: `https://api-staging.example.com`
  > - **Endpoint login** — ví dụ: `/auth/login` (ghi "không cần auth" nếu không cần)
  > - **Loại xác thực** — Bearer JWT / Basic Auth / API key / không cần
  > - **Username** để login (bỏ trống nếu không cần auth)
  > - **Password** để login (bỏ trống nếu không cần auth)
  > - **Tên field chứa token** trong response body của login — ví dụ: `token`, `accessToken`, `access_token` (ghi "không cần auth" nếu không cần)
  > - **Tên field username trong request body** — ví dụ: `username`, `email`, `user` (mặc định: `username`)
  > - **Tên field password trong request body** — ví dụ: `password`, `pass`, `secret` (mặc định: `password`)
  >
  > **2. Tổng quan sản phẩm** *(lưu vào `automation_test/docs/product-overview.md` — tùy chọn)*:
  > Mô tả ngắn về sản phẩm: mục tiêu, tính năng chính, đối tượng người dùng. Gõ "skip" nếu chưa có.
  >
  > **3. Ngữ cảnh nghiệp vụ cho feature này** *(lưu vào `automation_test/docs/features/<feature>/business-scenario.md` — tùy chọn)*:
  > Mô tả ngắn về API endpoints, luồng, kịch bản kiểm thử cho feature này. Gõ "skip" nếu chưa có.
  >
  > **4. Thiết kế chi tiết cho feature này** *(lưu vào `automation_test/docs/features/<feature>/detail-design.md` — tùy chọn)*:
  > Mô tả API endpoints cụ thể của feature này, request/response schema, business rules liên quan. Gõ "skip" nếu chưa có.
  >
  > **5. Tài liệu API toàn project** *(lưu vào `automation_test/docs/api-reference.md` — tùy chọn)*:
  > Danh sách tất cả endpoints, method, request/response, error codes. Dùng lại cho mọi feature. Gõ "skip" nếu chưa có.

  After user replies — create domain files from the answers (and gitignore the credentials file):
  ```bash
  mkdir -p automation_test/docs/features/<feature>
  grep -qxF 'automation_test/docs/global-data.md' .gitignore 2>/dev/null || echo 'automation_test/docs/global-data.md' >> .gitignore
  ```

  1. **`automation_test/docs/global-data.md`** — write base URL, auth config, and credentials. Omit any field the user skipped.
  2. **`automation_test/docs/product-overview.md`** — write if user provided content; skip entirely if user wrote "skip" or left blank.
  3. **`automation_test/docs/features/<feature>/business-scenario.md`** — write if user provided content; skip entirely if user wrote "skip" or left blank.
  4. **`automation_test/docs/features/<feature>/detail-design.md`** — write if user provided content; skip entirely if user wrote "skip" or left blank.
  5. **`automation_test/docs/api-reference.md`** — write if user provided content; skip entirely if user wrote "skip" or left blank.

  **If found (or after creating domain files above)** — read `global-data.md`, write the following to `automation_test/common/common_variables.resource` (create if missing):
  - `${BASE_URL}`, `${EP_LOGIN}`, `${CONTENT_TYPE}`, `${API_USERNAME}`, `${API_PASSWORD}`
  - `${TOKEN_FIELD}` — from `global-data.md`; default `token` if not specified or no auth
  - `${LOGIN_USERNAME_FIELD}` — from `global-data.md`; default `username` if not specified
  - `${LOGIN_PASSWORD_FIELD}` — from `global-data.md`; default `password` if not specified
  - If auth is not required: set `${EP_LOGIN}` to `none`, leave `${API_USERNAME}` / `${API_PASSWORD}` as empty placeholders

  Then proceed to Step 0d.

---

## Step 0d — Scaffold (First Time Only)

If `automation_test/common/common_keywords.resource` does not exist, scaffold the shared files now. Each file is created **only if it does not already exist** — never overwrite files the project already has.

### `automation_test/common/common_keywords.resource`

```robotframework
*** Settings ***
Resource    common_variables.resource

*** Keywords ***
API - Create Session
    [Arguments]    ${alias}=${SUITE_NAME}
    Create Session    ${alias}    ${BASE_URL}    verify=${True}    timeout=${TIMEOUT}
    RETURN    ${alias}

API - Login
    [Arguments]    ${username}    ${password}    ${alias}=${SUITE_NAME}
    &{body}=    Create Dictionary
    ...    ${LOGIN_USERNAME_FIELD}=${username}
    ...    ${LOGIN_PASSWORD_FIELD}=${password}
    # expected_status=any because login endpoints return 200 or 201 depending on the API.
    ${response}=    POST On Session    ${alias}    ${EP_LOGIN}
    ...    json=${body}    expected_status=any
    Should Be True    ${response.status_code} in [200, 201]
    ...    Login failed with status ${response.status_code} — check credentials and EP_LOGIN
    RETURN    ${response.json()}[${TOKEN_FIELD}]

API - Auth Header
    [Arguments]    ${token}=${EMPTY}
    &{headers}=    Create Dictionary
    ...    Content-Type=${CONTENT_TYPE}
    ...    Accept=application/json
    IF    '${token}' != '${EMPTY}'
        Set To Dictionary    ${headers}    Authorization=Bearer ${token}
    END
    RETURN    ${headers}

API - GET
    [Arguments]    ${path}    ${headers}    ${expected_status}=200    ${params}=${NONE}    ${alias}=${SUITE_NAME}
    ${response}=    GET On Session    ${alias}    ${path}
    ...    headers=${headers}    params=${params}    expected_status=${expected_status}
    RETURN    ${response}

API - POST
    [Arguments]    ${path}    ${body}    ${headers}    ${expected_status}=200    ${alias}=${SUITE_NAME}
    ${response}=    POST On Session    ${alias}    ${path}
    ...    json=${body}    headers=${headers}    expected_status=${expected_status}
    RETURN    ${response}

API - PUT
    [Arguments]    ${path}    ${body}    ${headers}    ${expected_status}=200    ${alias}=${SUITE_NAME}
    ${response}=    PUT On Session    ${alias}    ${path}
    ...    json=${body}    headers=${headers}    expected_status=${expected_status}
    RETURN    ${response}

API - PATCH
    [Arguments]    ${path}    ${body}    ${headers}    ${expected_status}=200    ${alias}=${SUITE_NAME}
    ${response}=    PATCH On Session    ${alias}    ${path}
    ...    json=${body}    headers=${headers}    expected_status=${expected_status}
    RETURN    ${response}

API - DELETE
    [Arguments]    ${path}    ${headers}    ${expected_status}=200    ${alias}=${SUITE_NAME}
    ${response}=    DELETE On Session    ${alias}    ${path}
    ...    headers=${headers}    expected_status=${expected_status}
    RETURN    ${response}

API - Assert Field Equals
    [Arguments]    ${response}    ${field}    ${expected}
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal As Strings    ${json}[${field}]    ${expected}

API - Assert Field Not Empty
    [Arguments]    ${response}    ${field}
    ${json}=    Set Variable    ${response.json()}
    # Handle plain JSON array responses (e.g. GET /products → [{...}, ...]).
    # For list: assert list is non-empty and first item contains the field.
    IF    isinstance($json, list)
        Should Not Be Empty    ${json}    Response is empty list
        Dictionary Should Contain Key    ${json}[0]    ${field}
        ${value}=    Convert To String    ${json}[0][${field}]
        Should Not Be Empty    ${value}
    ELSE
        Dictionary Should Contain Key    ${json}    ${field}
        ${value}=    Convert To String    ${json}[${field}]
        Should Not Be Empty    ${value}
    END

API - Assert List Length
    [Arguments]    ${response}    ${expected_length}
    ${json}=    Set Variable    ${response.json()}
    ${length}=    Get Length    ${json}
    Should Be Equal As Integers    ${length}    ${expected_length}
    ...    Expected ${expected_length} items but got ${length}

API - Assert Response Time
    [Arguments]    ${response}    ${max_seconds}=${TIMEOUT_RESPONSE}
    ${elapsed}=    Set Variable    ${response.elapsed.total_seconds()}
    Should Be True    ${elapsed} < ${max_seconds}
    ...    Response took ${elapsed}s, expected < ${max_seconds}s

DD - Get Dynamic Value
    [Arguments]    ${field}    ${placeholder}
    # Generates runtime values for INPUT_DATA placeholders in data-driven CSV rows.
    # Placeholder format: INPUT_DATA:<type>  e.g. INPUT_DATA:uuid, INPUT_DATA:timestamp, INPUT_DATA:number:18
    ${type}=    Fetch From Right    ${placeholder}    INPUT_DATA:
    IF    '${type}' == 'uuid'
        ${value}=    Evaluate    str(__import__('uuid').uuid4())
    ELSE IF    '${type}' == 'timestamp'
        ${value}=    Get Current Date    result_format=%Y/%m/%d %H:%M:%S
    ELSE IF    '${type}'.startswith('number')
        ${len}=    Set Variable    ${type.split(':')[-1]}
        ${value}=    Generate Random String    ${len}    [NUMBERS]
    ELSE IF    '${type}'.startswith('string')
        ${len}=    Set Variable    ${type.split(':')[-1]}
        ${value}=    Generate Random String    ${len}    [LETTERS][NUMBERS]
    ELSE
        ${value}=    Set Variable    ${placeholder}
    END
    RETURN    ${value}

DD - Prepare Request Body
    [Arguments]    ${body_dict}    ${dynamic_fields}
    # Replaces INPUT_DATA:* values in the parsed body dict before sending the request.
    # Use bare $variable syntax (no quotes) so RF compares Python types directly — quoted
    # '${dynamic_fields}' converts a list to its repr string and causes SyntaxError in IF.
    IF    $dynamic_fields != $NONE and $dynamic_fields != ''
        FOR    ${field}    IN    @{dynamic_fields}
            ${field_info}=    Run Keyword And Ignore Error    Get From Dictionary    ${body_dict}    ${field}
            IF    $field_info[0] == 'PASS' and 'INPUT_DATA' in str($field_info[1])
                ${new_value}=    DD - Get Dynamic Value    ${field}    ${field_info[1]}
                Set To Dictionary    ${body_dict}    ${field}=${new_value}
            END
        END
    END
    RETURN    ${body_dict}

DD - Assert Response Fields
    [Arguments]    ${response}    ${expected_json_str}
    # Parses expected_json_str and asserts every key-value pair against the response body.
    # Skips assertion entirely when expected_json_str is empty (status-only rows).
    ${is_empty}=    Run Keyword And Return Status    Should Be Empty    ${expected_json_str}
    IF    not ${is_empty}
        ${expected}=    Evaluate    __import__('json').loads("""${expected_json_str}""")
        FOR    ${key}    IN    @{expected.keys()}
            ${actual}=    Set Variable    ${response.json()}[${key}]
            Should Be Equal As Strings    ${actual}    ${expected}[${key}]
        END
    END

DD - Execute Request
    [Arguments]
    ...    ${method}
    ...    ${url}
    ...    ${request_body}
    ...    ${response_status_code}
    ...    ${response_body}
    ...    ${dynamic_fields}=${NONE}
    ...    ${headers}=${NONE}
    ...    ${alias}=${SUITE_NAME}
    # Universal data-driven template keyword. Called by Test Template in data-driven suites.
    # ${method}: RF RequestsLibrary keyword name e.g. POST On Session, GET On Session
    # ${request_body}: JSON string (body for POST/PUT/PATCH, params for GET) — or empty
    # ${response_body}: JSON string of expected key-value pairs — or empty for status-only check
    # ${headers}: pass API - Auth Header result; ${NONE} means no custom headers (no-auth APIs)
    ${is_get}=    Run Keyword And Return Status    Should Contain    ${method}    GET
    IF    '${request_body}' != '${EMPTY}' and '${request_body}' != '{}'
        ${body_dict}=    Evaluate    __import__('json').loads("""${request_body}""")
        ${body_dict}=    DD - Prepare Request Body    ${body_dict}    ${dynamic_fields}
    ELSE
        ${body_dict}=    Set Variable    ${NONE}
    END
    IF    ${is_get}
        ${response}=    Run Keyword    ${method}    ${alias}    url=${url}
        ...    headers=${headers}    params=${body_dict}    expected_status=${response_status_code}
    ELSE
        ${response}=    Run Keyword    ${method}    ${alias}    url=${url}
        ...    headers=${headers}    json=${body_dict}    expected_status=${response_status_code}
    END
    DD - Assert Response Fields    ${response}    ${response_body}
```

### `automation_test/common/common_variables.resource`

Fill in values from `global-data.md` (BASE_URL, EP_LOGIN). Placeholder values shown:

```robotframework
*** Variables ***
${ENV}                      staging
${BASE_URL}                 https://api-staging.example.com
${API_VERSION}              v1
${TIMEOUT}                  30
${TIMEOUT_RESPONSE}         2
${EP_LOGIN}                 /auth/login
${CONTENT_TYPE}             application/json
${TOKEN_FIELD}              token
${LOGIN_USERNAME_FIELD}     username
${LOGIN_PASSWORD_FIELD}     password
${API_USERNAME}             placeholder_username
${API_PASSWORD}             placeholder_password
```

### `automation_test/config/imports.resource`

```robotframework
*** Settings ***
Library     RequestsLibrary
Library     Collections
Library     OperatingSystem
Library     String
Library     DateTime
Resource    ../common/common_keywords.resource
```

Do NOT import variable files in `automation_test/config/imports.resource`.
Do NOT import `DataDriver` here — DataDriver must only be imported in the individual data-driven suite file (with its `file=` path argument). Adding it here causes DataDriver to load without a file, making the path from the suite file ignored.

---

## Mode A — Write or Update a Test Case

### Step 1 — Find the Manual TC File

```bash
python -c "import glob, sys; f=sys.argv[1]; hits=[p for p in glob.glob('automation_test/docs/features/**/test-cases.md', recursive=True) if f.lower() in p.lower()]; print('\n'.join(hits))" "<feature>"
```

If a TC-NNN was specified, find the exact test case in that file.

**If no TC file found** → ask the user ONE question:

> Không tìm thấy TC file cho feature **`<feature>`**. Bạn muốn tạo bằng cách nào?
>
> **1** — Import từ file Excel (bạn cung cấp đường dẫn file)
> **2** — AI tự viết từ tài liệu domain knowledge
>
> (Chưa có tài liệu nào? Gõ **2** — tôi sẽ hỏi thêm để tạo.)

**Sau khi user trả lời — thực hiện ngay, không yêu cầu chạy thêm lệnh nào:**

**Nếu chọn 1 (Excel):**
- Nếu user chưa cung cấp đường dẫn → hỏi: *"Đường dẫn đến file Excel?"*
- Convert từ Excel (autotest-scenarios Mode B):
  ```bash
  python3 -m pip show openpyxl > /dev/null 2>&1 || python3 -m pip install openpyxl -q
  python3 .claude/skills/autotest-scenarios/scripts/tc_import.py "<xlsx_path>"
  ```
- Hiển thị preview 3 TC đầu và hỏi: *"Mapping đúng chưa? (yes / fix)"*
- Nếu đúng → ghi file:
  ```bash
  python3 .claude/skills/autotest-scenarios/scripts/tc_import.py "<xlsx_path>" \
    --write "automation_test/docs/features/<feature>/test-cases.md" \
    --feature "<feature>"
  ```
- Thông báo đã lưu → **tiếp tục ngay** từ đầu Step 1 (đọc file vừa tạo).

**Nếu chọn 2 (tạo từ tài liệu):**
- Kiểm tra domain docs:
  ```bash
  python -c "import glob; hits=glob.glob('automation_test/docs/api-reference.md') + [h for h in glob.glob('automation_test/docs/features/**/*.md', recursive=True) if any(k in h for k in ['business-scenario','detail-design'])]; print('\n'.join(hits) or 'NONE')"
  ```
- Nếu có docs → áp dụng đúng quy trình Mode A của `autotest-scenarios` (đối chiếu tài liệu → sinh TC theo 6 lens + EP/BVA/UCT/DT/ST/EG/PW, checklist mở rộng theo đặc điểm feature (test pyramid theo layer), Never Assume khi thiếu thông tin, mỗi TC có Source truy nguyên → review checklist trước khi lưu), numbering TC-001–099/100–199/200–299/300–399/400–499/500–599
- Nếu không có docs → chạy domain creation flow (Step 0c) để thu thập thông tin trước, rồi tạo scenarios
- Hiển thị danh sách scenarios đã dựng:

  > Tôi đã dựng **X scenarios** từ domain knowledge:
  >
  > | TC | Title | Category | Priority |
  > |---|---|---|---|
  > | TC-001 | ... | Happy Path | P0 |
  > | ... | | | |
  >
  > **Lưu và tiếp tục automate? (Có / Sửa / Không)**

- Chờ xác nhận → khi đồng ý, ghi file `automation_test/docs/features/<feature>/test-cases.md` → **tiếp tục ngay** từ đầu Step 1.

**Nếu user paste TC trực tiếp:** lưu vào `automation_test/docs/features/<feature>/test-cases.md` → tiếp tục ngay từ đầu Step 1.

Read the manual TC file completely.

### Step 1a2 — Chọn TC cần viết — bắt buộc, kể cả khi gọi qua workflow

Nếu `TC_LIST` đã xác định từ Argument Parsing (user nêu rõ mã TC-NNN trong yêu cầu) → dùng đúng danh sách đó, bỏ qua bước hỏi này.

Ngược lại (yêu cầu chỉ nêu feature chung chung, không chỉ định TC nào cụ thể — kể cả khi được gọi từ workflow `automation-test`/`/vsaf autotest/automation-test`) → liệt kê toàn bộ TC tìm được trong TC file rồi hỏi:

> Đã tìm thấy **`<N>` TC** cho `<feature>`:
>
> | TC | Title | Category |
> |---|---|---|
> | TC-001 | ... | Happy Path |
> | ... | | |
>
> Bạn muốn viết TC nào? (liệt kê số, vd `TC-001, TC-003`, hoặc gõ **tất cả**)

Chờ câu trả lời thật trước khi tiếp tục — **không tự mặc định "viết hết" để tiết kiệm bước**. Từ Step 1b (phân tích Mode A/D) trở đi, chỉ tính/viết/chạy đúng các TC đã chọn — không tự ý viết thêm TC ngoài danh sách dù tiện làm luôn.

**OTP / SMS Detection — STOP if any TC step involves OTP or SMS.**

Scan the manual TC for keywords: OTP, mã OTP, mã xác thực, mã xác minh, verification code, one-time password, TOTP, SMS, tin nhắn, "nhập mã".

If found → STOP and ask the user before writing any code:

> TC này yêu cầu OTP/SMS. Để tự động hoá bước này, tôi cần biết:
>
> 1. **SMS OTP qua Web/API service** — lấy OTP từ portal hoặc API bên ngoài.
>    - URL của service là gì?
>    - Cần thông tin đăng nhập không?
> 2. **TOTP (Authenticator app)** — mã 6 số dựa trên thời gian (Google Authenticator / TOTP).
>    - Có thể cung cấp TOTP secret key để generate tự động không?
>    - (Dùng `pyotp` để generate: `pyotp.TOTP(secret).now()`)
> 3. **OTP trả về trong API response** — một số API sandbox trả OTP thẳng trong response body.
>    - Kiểm tra API docs xem có field nào chứa OTP không.
>
> Nếu chưa biết → chờ user xác nhận, không giả định.

> **Warning — avoid accidentally reading a stale OTP**: The inbox may contain multiple messages from the same sender number with the same content but different codes. If you only fetch the first message without checking the timestamp, you can easily read the OTP from a previous send.
>
> **Mandatory rule**: Record a timestamp **before** calling the API that triggers the OTP send. Then only accept messages with `received_at > timestamp_before_trigger`.
>
> - SMS service: use the `received_after=<timestamp>` or `since_id=<oldest_message_id>` filter if the service supports it. If no filter is available → fetch the list and discard any message with a timestamp ≤ the trigger time.
> - TOTP: not affected (the code is generated in real time and is always the latest).
> - OTP in response: not affected (read directly from the response of the just-sent request).
> - If timeout expires and no new message arrives → FAIL explicitly; do not fall back to a stale OTP.

### Step 1b — Phân tích TC và chọn mode

Sau khi đọc TC file, phân tích và đưa ra khuyến nghị **một lần duy nhất** trước khi viết bất kỳ code nào.

**Phân tích các yếu tố sau:**

| Yếu tố | Dấu hiệu Mode A | Dấu hiệu Mode D |
|--------|----------------|----------------|
| Số lượng TC | Ít (1–10) | Nhiều (10+) hoặc có thể mở rộng |
| Cấu trúc bước | Mỗi TC có flow riêng biệt | Nhiều TC lặp cùng endpoint, chỉ data khác |
| Endpoint | Nhiều endpoint khác nhau | Tập trung 1–2 endpoint, nhiều bộ input |
| Assertion | Logic phức tạp, khác nhau mỗi TC | Chỉ assert status + một vài field cố định |
| Dynamic data | Giá trị cố định (YAML đủ) | Cần tự generate UUID/timestamp/random |

**Sau khi phân tích, trả lời user theo format này:**

> **Phân tích TC file `<feature>`:**
>
> - Tổng số TC: X
> - Cấu trúc: [mô tả ngắn — ví dụ: "8 TC đều gọi POST /payment, chỉ khác requestBody và expectedStatus"]
> - Dynamic data: [có/không — ví dụ: "cần generate transactionId và timestamp mỗi lần chạy"]
>
> **Khuyến nghị: Mode A / Mode D**
> [1–2 câu giải thích lý do — ví dụ: "TC lặp cùng 1 endpoint với nhiều bộ dữ liệu → Mode D tiết kiệm effort hơn, mỗi dòng CSV là 1 TC tự động."]
>
> | | Mode A — Standard | Mode D — Data-driven |
> |---|---|---|
> | Cấu trúc | 1 RF keyword per TC, assert linh hoạt | 1 template + CSV, 1 row = 1 TC tự động |
> | Phù hợp | Flow khác nhau, assertion phức tạp | Cùng endpoint, nhiều bộ dữ liệu |
> | Effort | Viết từng keyword, dễ debug | Setup lần đầu nhiều hơn, mở rộng dễ |
>
> **Bạn muốn dùng mode nào?** (gõ `A` hoặc `D`, hoặc để tôi tiếp tục theo khuyến nghị trên)

> **STOP — Bắt buộc chờ user xác nhận trước khi viết bất kỳ file nào.**
> Không được tự động tiếp tục theo khuyến nghị mà không có phản hồi của user.
> Nếu user không trả lời sau khi đã hiện bảng phân tích → nhắc lại: "Bạn muốn Mode A hay Mode D?"

Khi user xác nhận:
- Nếu **Mode A** → tiếp tục Step 1c bên dưới.
- Nếu **Mode D** → chuyển sang **Mode D** section.

---

### Step 1c — Verify status codes thực tế bằng curl

Trước khi viết bất kỳ assertion nào, verify status code thực tế của các happy-path TC:

```bash
curl -s -o /dev/null -w "%{http_code}" -X <METHOD> <BASE_URL><endpoint> \
  -H "Content-Type: application/json" \
  -d '<request_body>'
```

So sánh với expected trong TC file. Nếu khác → cập nhật TC file, dùng status thực tế trong assertion.

> **Lý do:** TC do AI sinh thường giả định status code (200 vs 201). Chạy test với status sai → fail ngay TC-001 dù code đúng. Verify curl trước tiết kiệm thời gian debug.

---

### Step 2 — Plan the API Call Structure

From the manual TC, identify:
- HTTP method and endpoint path for each step
- Request body fields
- Expected status codes (success and any error cases)
- Response fields to assert

Check the existing `automation_test/api/<feature>/user_variables.resource` to avoid duplicating endpoint path variables. If file doesn't exist, plan all `${EP_}` variables.

### Step 3 — Write the Variables File

Create or update `automation_test/api/<feature>/<feature>_variables.resource`:

```robotframework
*** Variables ***
${EP_<FEATURE>_LIST}        /api/v1/<resource>
${EP_<FEATURE>_BY_ID}       /api/v1/<resource>
${EP_<FEATURE>_CREATE}      /api/v1/<resource>
${EP_<FEATURE>_UPDATE}      /api/v1/<resource>
${EP_<FEATURE>_DELETE}      /api/v1/<resource>

${FIELD_ID}                 id
${FIELD_<KEY_FIELD>}        <json_field_name>
${FIELD_STATUS}             status

${VAL_STATUS_<X>}           <value>
```

Rules:
- Path variables only — no credentials, no base URL, no auth tokens
- Use `${EP_}` prefix for all endpoint paths
- Use `${FIELD_}` prefix for JSON response field name constants
- Use `${VAL_}` prefix for expected value constants

### Step 4 — Write the Keywords File

Create or update `automation_test/api/<feature>/<feature>_keywords.resource`.

Header:
```robotframework
*** Settings ***
Resource    <feature>_variables.resource
```

> **Không import `../../config/imports.resource` trong keywords file.** `automation_test/config/imports.resource` đã import keywords file này → circular import gây lỗi keyword resolution. Test file import `automation_test/config/imports.resource` là đủ — tất cả libraries và common keywords đã có sẵn khi robot chạy.

Rules from `autotest-api-best-practices`:
- **1 scenario keyword per TC** — keyword handles the full scenario: build auth header, call API, assert response time, assert response body. Test case body = keyword call only.
- **`${SUITE_TOKEN}` is a suite variable** — accessible directly inside keywords without passing as argument. First line of every keyword: `${headers}=    API - Auth Header    ${SUITE_TOKEN}`
- All HTTP calls go through `API - GET`, `API - POST`, etc. — never raw `GET On Session`
- Every keyword call must have `expected_status` appropriate to the scenario
- Always call `API - Assert Response Time` on every happy-path keyword
- Always assert at least one response body field after POST/PUT/PATCH
- Keyword ≤ 20 lines, at least 2 keyword calls per keyword. If assertions push over 20 lines → extract `<Feature> - Assert <Scenario>` sub-keyword
- **`API - POST` default status is 200** — if the API returns 201 for POST (REST-compliant create), pass `expected_status=201` explicitly. Verify with curl before coding.
- **Array responses**: use `Should Be True    isinstance($json, list)` + `API - Assert List Length` for count

**Session cookie persistence — "no-auth" TCs:**
`requests.Session` persists cookies (e.g., `accessToken`) returned by the login endpoint. A TC that expects 401 "without token" will receive 200 instead because the server sees the cookie.

Fix: when a TC must simulate an unauthenticated request, keyword creates a fresh session alias that was never logged in — do NOT use `${SUITE_TOKEN}`:
```robotframework
<Feature> - Get Resource Without Auth
    &{empty_headers}=    Create Dictionary    Content-Type=application/json
    API - Create Session    no-auth
    ${response}=    API - GET    ${EP_<FEATURE>_RESOURCE}    ${empty_headers}
    ...    expected_status=401    alias=no-auth
    Should Not Be Empty    ${response.json()}[message]
```
`Suite Teardown: Delete All Sessions` cleans up the `no-auth` alias automatically.

### Step 5 — Write YAML Test Data

Create or update `automation_test/data/<feature>.yaml`:

```yaml
data:
  TC-001 Get All Products: {}          # no input data — entry still required
  TC-002 Get Product By Id:
    product_id: 1
  TC-006 Create New Product:
    title: "New Product"
    price: 29.99
    category: electronics
```

- Top-level key MUST be `data:`
- Child key MUST match test case name exactly (e.g. `TC-001 Get All Products`)
- **Every TC must have an entry — even GET TCs with no input data → leave empty `{}`**
- TCs with no data: do NOT pass `${data["${TEST_NAME}"]}` to the keyword, do NOT declare `[Arguments]    ${test_data}` in the keyword
- TCs with data: pass `${data["${TEST_NAME}"]}` to keyword; keyword declares `[Arguments]    ${test_data}` and uses it
- Never store credentials, tokens, or base URLs in YAML
- Request body fields go in YAML — not hardcoded in keywords or `_variables.resource`

### Step 6 — Write or Update the Test Suite File

Create or update `automation_test/tests/<feature>.robot`.

```robotframework
*** Settings ***
# Credentials: automation_test/common/common_variables.resource → ${API_USERNAME} / ${API_PASSWORD}
#
# Run one TC:  robot --loglevel TRACE -d automation_test/results/ -t "<Test_Case_Name>" automation_test/tests/<feature>.robot
# Run suite:   robot --loglevel TRACE -d automation_test/results/ automation_test/tests/<feature>.robot
# Run vs prod: robot --loglevel TRACE -d automation_test/results/ -v BASE_URL:https://api.example.com automation_test/tests/<feature>.robot
Resource        ../config/imports.resource
Variables       ../data/<feature>.yaml

Suite Setup       <Feature> Test Suite - Setup
Suite Teardown    Delete All Sessions

*** Variables ***
${SUITE_TOKEN}    ${EMPTY}

*** Test Cases ***
# TC with data — pass ${data["${TEST_NAME}"]} directly to keyword
TC-002 Get Product By Valid Id
    [Tags]    feature    happy-path    TC-002
    <Feature> - Get Product By Id    ${data["${TEST_NAME}"]}

# TC with no data — call keyword with no args
TC-001 Get All Products
    [Tags]    feature    happy-path    TC-001
    <Feature> - Get All Products

*** Keywords ***
<Feature> Test Suite - Setup
    API - Create Session
    IF    '${EP_LOGIN}' != '${EMPTY}' and '${EP_LOGIN}' != 'none'
        ${token}=    API - Login    ${API_USERNAME}    ${API_PASSWORD}
        Set Suite Variable    ${SUITE_TOKEN}    ${token}
    ELSE
        Set Suite Variable    ${SUITE_TOKEN}    ${EMPTY}
    END
```

Rules:
- `Variables    ../data/<feature>.yaml` always imported (all TCs have YAML entries)
- **Test case body = 1 line: keyword call only** — no `${headers}`, no `${td}`, no inline assertions
- For TCs with data: `<Feature> - <Keyword>    ${data["${TEST_NAME}"]}` — pass the whole dict; keyword declares `[Arguments]    ${test_data}` and uses `${test_data}[field]`
- For TCs without data: `<Feature> - <Keyword>` with no args; keyword has no `[Arguments]` line
- Suite Setup creates session and obtains token via `Set Suite Variable    ${SUITE_TOKEN}`; keywords use `${SUITE_TOKEN}` directly
- Tags on every test case: `<feature>`, `smoke|regression|negative`, `TC-NNN`
- `[Teardown]` with cleanup keyword when test creates persistent data
- **Integer response fields** — `id`, `count`, `total`... là số nguyên, không dùng `Should Not Be Empty`. Dùng `Should Be True    ${json}[id] > 0` hoặc `Should Be True    ${json}[id] is not None`.

### Step 7 — Format

```bash
python -m robotidy automation_test/api/<feature>/
python -m robotidy automation_test/tests/<feature>.robot
```

If `robotidy` is not on PATH: `python -m robotidy automation_test/api/<feature>/ && python -m robotidy automation_test/tests/<feature>.robot`

### Step 8 — Run the TC

Verify `automation_test/common/common_variables.resource` has no placeholder credentials. If any placeholder remains → ask the user for the real value and update the file first. Then run:
```bash
robot --loglevel TRACE -d automation_test/results/ -t "<Test_Case_Name>" automation_test/tests/<feature>.robot
```

Then report results with autotest-results:
```bash
python .claude/skills/autotest-results/scripts/rf_results.py \
  --output automation_test/results/output.xml --sections summary,details --pretty
```

### Step 9 — Debug & Fix

| Error | Fix |
|---|---|
| `Expected status: X != Y` | API returned X, code expected Y — verify actual status with curl, fix `expected_status` |
| Assertion failed | Wrong field name or value — check response body in log.html |
| `RequestConnectionError` | Server unreachable — check `BASE_URL` and network |
| `No module named '<anything>'` | Re-run Step 0-env pip install block, then retry once (auto-fix) |
| `JSONDecodeError` | Response body is empty/non-JSON — use `response.text` instead of `response.json()` |
| `Could not get length of '<int>'` | Integer field — use `Should Be True    ${json}[field] > 0` not `Should Not Be Empty` |
| `No keyword with name` | Missing import in `automation_test/config/imports.resource` or circular import in keywords file |

Repeat fix → re-run until TC passes. TC is done only when it passes against the real API server.

If the manual TC describes a step that the API currently doesn't support (API bug):
- Write the test exactly as the manual TC says — it will fail naturally at the failing assertion
- Add tag `known-bug`
- STOP and report the discrepancy; do not silently adapt

### Step 10 — Shared Resource Warning

After the run, check if any shared file was modified (`common_keywords.resource`, `common_variables.resource`, `automation_test/config/imports.resource`). If yes, report:

> **Heads up:** Changes to `[shared file]` may affect `[other features]`. Want to re-run the full suite?

Do not run the full suite automatically — leave that decision to the user.

Then print:

> "TC passed. Suite teardown (`Delete All Sessions`) runs at suite end, not per-test. To run the full suite: `robot --loglevel TRACE -d automation_test/results/ automation_test/tests/<feature>.robot`"

---

## Mode B — Refactor Existing API Tests

Read all files in `automation_test/api/<feature>/`, `automation_test/tests/<feature>.robot`, `automation_test/data/<feature>.yaml`.

Apply all rules from `autotest-api-best-practices` SKILL.md:

| Check | Rule |
|---|---|
| Direct `GET On Session` / `POST On Session` in feature keywords | Replace with `API - GET` / `API - POST` etc. |
| No `expected_status` on request call | Add appropriate `expected_status` |
| `verify=${False}` in session | Replace with `verify=${True}` — FORBIDDEN |
| Hardcoded credentials in keyword or test file | Move to `${API_USERNAME}` / `${API_PASSWORD}` in `automation_test/common/common_variables.resource` |
| Missing assertion after request | Add `API - Assert Field Not Empty` or `API - Assert Field Equals` |
| Missing `API - Assert Response Time` | Add on happy path keywords |
| Keyword > 20 lines | Split into sub-keywords |
| Hardcoded base URL | Move to `${BASE_URL}` in `common_variables.resource` |
| Hardcoded endpoint path in keyword (not via `${EP_}` variable) | Move to variables file |
| Missing `[Tags]` on test cases | Add `<feature>`, category, `TC-NNN` |
| No `Suite Teardown: Delete All Sessions` | Add it |
| Test case body longer than one scenario keyword call | Extract to feature keyword |
| `${SUITE_TOKEN}` not used via `Set Suite Variable` | Verify Suite Setup pattern |
| Unused `${test_data}` argument in keyword | Remove `[Arguments]    ${test_data}` and matching `${data["${TEST_NAME}"]}` in `.robot` |
| YAML entry exists but TC no longer passes data | Remove the YAML entry |
| `Variables` import present but no TC passes `${data["..."]}` | Remove `Variables` import line |
| Test data hardcoded in keyword body or `_variables.resource` | Move to `automation_test/data/<feature>.yaml` |

Format all files after refactoring:
```bash
python -m robotidy automation_test/api/<feature>/
python -m robotidy automation_test/tests/<feature>.robot
```

Run all TCs in the suite to verify no regressions:
```bash
robot --loglevel TRACE -d automation_test/results/ automation_test/tests/<feature>.robot
```

---

## Mode C — Delete a Test Case

1. Find and read `automation_test/tests/<feature>.robot` and `automation_test/api/<feature>/<feature>_keywords.resource`
2. Identify all keywords used **only** by TC-NNN (not by any other TC)
3. Find YAML entries used **only** by TC-NNN
4. Find `${EP_}` / `${FIELD_}` / `${VAL_}` variables used **only** by the deleted TC's keywords

Delete in order:
1. Remove TC block from `automation_test/tests/<feature>.robot`
2. Remove orphaned keywords from `automation_test/api/<feature>/<feature>_keywords.resource`
3. Remove orphaned variables from `automation_test/api/<feature>/<feature>_variables.resource`
4. Remove YAML entry from `automation_test/data/<feature>.yaml`

Format:
```bash
python -m robotidy automation_test/api/<feature>/
python -m robotidy automation_test/tests/<feature>.robot
```

Run remaining TCs to confirm nothing broken:
```bash
robot --loglevel TRACE -d automation_test/results/ automation_test/tests/<feature>.robot
```

---

## Mode D — Data-Driven (CSV + DataDriver)

**Khi nào dùng:** cần test toàn bộ validation của một endpoint — method, URL, request field, status code, response field — với hàng chục đến hàng trăm bộ dữ liệu. Mỗi dòng trong file CSV tự động thành một TC riêng.

> Mode D được chọn từ Step 1b (sau khi phân tích TC). Nếu vào thẳng đây mà chưa qua Step 1b → quay lại Step 1b.

### Step 1 — Hỏi thêm thông tin cần thiết cho data file

Từ TC file đã đọc ở Step 1, skill đã biết endpoint và cấu trúc. Chỉ hỏi những gì chưa rõ — **gộp tất cả vào một message duy nhất**:

> **Tôi cần thêm một số thông tin để tạo data-driven test cho `<feature>`:**
>
> 1. **Dynamic fields** — field nào trong request body cần tự generate lúc runtime? (ví dụ: `transactionId`, `requestTime`). Để trống nếu không có.
> 2. **Kiểu generate** — nếu có dynamic fields: `uuid`, `timestamp`, `number:<length>`, `string:<length>` (ví dụ: `transactionId=number:18`, `requestTime=timestamp`)
> 3. **Dữ liệu bổ sung** — bạn muốn tôi tạo CSV từ TC file sẵn có, hay có data mẫu muốn paste vào?

> **Lưu ý:** Nếu TC file đã đủ thông tin (endpoint, method, request body, expected response) → skip câu 3, tôi sẽ tự tạo CSV từ TC.

### Step 2 — Tạo data file

**Layout chuẩn CSV** (`automation_test/data/api/<feature>.csv`):

```
*** Test Cases ***,${method},${url},${request_body},${response_status_code},${response_body}
TC_Name_Happy_Path,POST On Session,/api/v1/<resource>,"{""field1"": ""value1"", ""field2"": ""INPUT_DATA:number:18""}",200,"{""status"": ""SUCCESS""}"
TC_Name_Wrong_Method,GET On Session,/api/v1/<resource>,{},405,"{""error"": ""Method Not Allowed""}"
TC_Name_Missing_Field,POST On Session,/api/v1/<resource>,"{""field2"": ""value2""}",400,"{""error"": ""field1 is required""}"
TC_Name_Status_Only,DELETE On Session,/api/v1/<resource>/{id},{},204,
```

**Rules:**
- Cột `*** Test Cases ***`: tên TC, dùng `_` không dùng space, không trùng
- Cột `${method}`: RF keyword đầy đủ — `POST On Session`, `GET On Session`, `PUT On Session`, `PATCH On Session`, `DELETE On Session`
- Cột `${request_body}`: JSON string — dùng `""` thay cho `"` bên trong (CSV escaping). GET request dùng JSON object làm query params. Empty body dùng `{}`
- Cột `${response_status_code}`: số nguyên, không có ngoặc kép
- Cột `${response_body}`: JSON string chứa **chỉ các key cần assert** — để trống nếu chỉ kiểm tra status code
- `INPUT_DATA:<type>`: placeholder cho field tự generate — supported types: `uuid`, `timestamp`, `number:<len>`, `string:<len>`
- File lưu tại `automation_test/data/api/<feature>.csv`, encoding UTF-8, line ending Unix (`\n`)

### Step 3 — Tạo test suite và template keyword

> **QUAN TRỌNG:** DataDriver chỉ tìm template keyword trong `suite.resource.keywords` — tức là keyword phải được khai báo **trực tiếp trong `*** Keywords ***` của file `.robot`**, không thể ở resource file bên ngoài.

`automation_test/tests/<feature>_dd.robot`:

```robotframework
*** Settings ***
# --- Run commands ---
# Run full data-driven suite:
# robot --loglevel TRACE -d automation_test/results/ automation_test/tests/<feature>_dd.robot
#
# Run with variable override (e.g. staging vs uat):
# robot --loglevel TRACE -d automation_test/results/ -v envRun:uat automation_test/tests/<feature>_dd.robot
Resource    ../config/imports.resource
Library     DataDriver    ../data/api/<feature>.csv    encoding=utf_8    dialect=unix

Suite Setup       <Feature> DD Test Suite - Setup
Suite Teardown    Delete All Sessions
Test Template     <Feature> - DD Template


*** Test Cases ***
Test_Case
    [Template]    <Feature> - DD Template


*** Keywords ***
<Feature> DD Test Suite - Setup
    API - Create Session
    IF    '${EP_LOGIN}' != '${EMPTY}' and '${EP_LOGIN}' != 'none'
        ${token}=    API - Login    ${API_USERNAME}    ${API_PASSWORD}
        Set Suite Variable    ${SUITE_TOKEN}    ${token}
    ELSE
        Set Suite Variable    ${SUITE_TOKEN}    ${EMPTY}
    END

<Feature> - DD Template
    [Arguments]
    ...    ${method}
    ...    ${url}
    ...    ${request_body}
    ...    ${response_status_code}
    ...    ${response_body}
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    @{dynamic_fields}=    Create List    <field1>    <field2>
    DD - Execute Request
    ...    ${method}
    ...    ${url}
    ...    ${request_body}
    ...    ${response_status_code}
    ...    ${response_body}
    ...    ${dynamic_fields}
    ...    ${headers}
```

- Nếu không có dynamic fields: thay `${dynamic_fields}` bằng `${NONE}`, bỏ dòng `@{dynamic_fields}=`
- `Library DataDriver` phải dùng path positional (không dùng `file=`) — path tương đối từ vị trí file `.robot`
- **Không** thêm `Library DataDriver` vào `automation_test/config/imports.resource` — DataDriver chỉ được import trong suite file này

### Step 4 — Cập nhật `automation_test/config/imports.resource`

Chỉ thêm nếu chưa có — **không** thêm DataDriver vào đây:
```robotframework
Resource    ../api/<feature>/<feature>_keywords.resource
```

### Step 5 — Format

```bash
python -m robotidy automation_test/tests/<feature>_dd.robot
```

### Step 6 — Chạy dry-run để verify DataDriver parse đúng

```bash
robot --dryrun -d automation_test/results/ automation_test/tests/<feature>_dd.robot
```

- Nếu `dryrun` báo số TC đúng với số row trong CSV → tiếp tục chạy thật
- Nếu `No test cases` → kiểm tra header CSV có đúng `*** Test Cases ***` không
- Nếu `DataDriver: file not found` → kiểm tra đường dẫn tương đối; dùng path positional (không `file=`) từ vị trí suite file
- Nếu `No "Test Template" keyword found` → template keyword chưa nằm trong `*** Keywords ***` của suite file; KHÔNG được để ở resource file bên ngoài

Sau dry-run OK, chạy thật:
```bash
robot --loglevel TRACE -d automation_test/results/ automation_test/tests/<feature>_dd.robot
```

### Quy tắc riêng của Mode D

- **Không dùng YAML** — data hoàn toàn trong CSV
- **Không tạo keyword riêng per-TC** — một template keyword cho tất cả
- **Template keyword phải ở trong suite `.robot` file** — DataDriver không thể tìm keyword ở resource file bên ngoài
- **`Test_Case` trong `*** Test Cases ***` phải có `[Template]    <Feature> - DD Template`** — khai báo rõ ràng để DataDriver nhận dạng
- **`Library DataDriver` chỉ khai báo trong suite file** — KHÔNG trong `automation_test/config/imports.resource`; dùng path positional (không `file=`), tương đối từ vị trí suite
- **Tên TC trong CSV** phải unique và không chứa ký tự đặc biệt ngoài `_`
- **Luôn chạy dry-run trước** để xác nhận DataDriver parse đúng số TC
- **CSV naming**: `automation_test/data/api/<feature>.csv` — luôn trong subfolder `automation_test/api/` để phân biệt với YAML data của Mode A
- **Array response limitation**: `DD - Assert Response Fields` không hỗ trợ assert trực tiếp trên array response — để trống cột `${response_body}` cho các row GET-all (chỉ kiểm tra status code); dùng Mode A nếu cần assert chi tiết trên từng item trong danh sách
- **Auth headers**: template keyword phải gọi `API - Auth Header    ${SUITE_TOKEN}` và truyền qua `DD - Execute Request` — nếu bỏ qua, request sẽ không có Authorization header

---

## Existing Project Rule

Act based on the result of Step 0a:
- `NEW` → scaffold freely.
- `COMPLIANT` → follow existing conventions, scaffold only missing files, verify imports before saving.
- `PARTIAL` → ask the user; if they agree, restructure (move code into the correct AOM files + create missing scaffold); otherwise follow the existing conventions.

---

## Core Principle — AI Acts, User Only Provides Data

The AI executes all commands itself. The user's only role is to supply information when asked.

**Never do this:**
- Tell the user to run a shell command and come back with the output
- Print `export VAR=value` / `adb ...` / `xcrun ...` instructions for the user to execute
- Ask the user to create, edit, or move files manually

**Always do this:**
- Run all shell commands (read files, query devices, start/stop processes) yourself
- If a value is needed, ask the user for it in plain language, then use it yourself
- If a file needs to be created or edited, do it with your file tools

**Only ask the user for data when it cannot be derived any other way:**
- First check existing files (`global-data.md`, `common_variables.resource`, YAML data)
- Then try to derive it (run a command, read a file, inspect the project)
- Only if still unknown → ask the user, in plain language, for the specific value

**The only valid exception** — actions that require physical human interaction:
device unlock, Face ID / Touch ID, app store sign-in, hardware token press.
In those cases, ask the user to perform the physical action, then continue.
## Rules

- **Python libraries** — if a custom Python library is needed, create it in `automation_test/python_lib/` at the project root (create the folder if it does not exist). Then add `Library    ../python_lib/<LibraryName>.py` to `automation_test/config/imports.resource`.

## Ask-Never-Guess Rule

If any of these is missing or ambiguous, STOP and ask before writing code:

- **Base URL**: Cannot be derived from code alone — ask user or read `global-data.md`
- **Endpoint path**: Unknown endpoint structure → ask, do not guess from resource name
- **Authentication type**: Bearer JWT vs API key vs Basic vs no auth → ask
- **Expected status codes**: Ambiguous from TC description → ask
- **Response field names**: Unknown JSON structure → ask or request a sample response
- **Environment variable names**: The conventions (`API_USERNAME`, `API_PASSWORD`) can be overridden per project → verify with user

Never invent endpoint paths. Never assume auth type. Never guess JSON field names.

---

## Error: `robotidy` Not Found

```bash
python -m robotidy automation_test/api/<feature>/
# OR
pip install robotframework-tidy && python -m robotidy automation_test/api/<feature>/
```

## Error: `RequestsLibrary` Not Installed

```bash
pip install robotframework-requests
```

## Error: Session Already Exists

Previous run crashed before `Delete All Sessions`. Safe to ignore on re-run — next `Create Session` replaces it — or restart the robot process.
