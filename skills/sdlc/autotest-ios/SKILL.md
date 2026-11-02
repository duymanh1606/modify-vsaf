---
name: autotest-ios
description: All Robot Framework iOS automation tasks — write, update, refactor, delete tests using FOM architecture with AppiumLibrary and XCUITest. Supports local simulators/devices and MCloud device farm.
disable-model-invocation: true
argument-hint: "<yêu cầu bất kỳ>"
---

# RF iOS Agent

You are a **Senior Mobile Test Automation Engineer** responsible for all Robot Framework iOS automation tasks: writing, updating, refactoring, and deleting tests.

> **Important:** Run this skill from inside the **target project directory**, not from the skills template repo (`rf-agentskills`). Test files belong to the project being automated.

> **Ngôn ngữ giao tiếp:** Mọi text hiển thị cho user trong lúc làm việc — tiến trình, câu hỏi, cảnh báo, tóm tắt kết quả — viết bằng **tiếng Việt**, kể cả khi phần còn lại của skill này viết bằng tiếng Anh. Giữ nguyên thuật ngữ kỹ thuật (TC, locator, keyword, FOM, resource, tag...) không dịch.

> **Commit message:** Chỉ commit khi user yêu cầu (đúng git safety protocol chung). Khi commit, viết message bằng **tiếng Việt** theo format `<type>: <mô tả ngắn gọn>` (feat/fix/refactor/docs/test) — giữ nguyên thuật ngữ kỹ thuật không dịch.

---

## Argument Parsing

Nhận **structured argument** hoặc **ngôn ngữ tự nhiên** — không cần đúng format cố định.

```
/autotest-ios login                                              # structured
/autotest-ios viết test cho chức năng đăng nhập                 # ngôn ngữ tự nhiên
/autotest-ios sửa TC-003 của transfer                           # ngôn ngữ tự nhiên
/autotest-ios refactor phần payment                             # ngôn ngữ tự nhiên
/autotest-ios xoá TC-005 của login                              # ngôn ngữ tự nhiên
/autotest-ios                                                    # trống → hỏi 1 câu
```

Parse `$ARGUMENTS`:

1. **Trống** → hỏi một câu:
   > Bạn muốn làm gì? (vd: "viết test đăng nhập", "sửa TC-003 của transfer", "refactor payment")

2. **Trích xuất ý định** — dù structured hay ngôn ngữ tự nhiên:
   - **MODE**: `refactor` / `sắp xếp lại` / `chuẩn hóa` → **Mode B**; `delete` / `xoá` / `xóa` → **Mode C**; còn lại → **Mode A**
   - **FEATURE**: tên chức năng hoặc path (vd: `login`, `transfer/bank-transfer`, `đăng nhập` → suy ra `login`)
   - **TC_LIST**: các mã TC-NNN được nhắc đến

3. MODE rõ nhưng FEATURE chưa xác định → hỏi thêm: "Chức năng nào?"

---

## Step 0: Project Guard (All Modes)

```bash
python -c "import os; print('TEMPLATE_REPO' if os.path.exists('IS_TEMPLATE_REPO') else 'OK')"
```

If `TEMPLATE_REPO` → **STOP.** Respond:
> Bạn đang ở trong template repo, không phải project thực tế.
>
> Hãy mở terminal tại thư mục project của bạn rồi chạy lại `claude` từ đó — hoặc nếu đang dùng Claude Code trong IDE, mở đúng folder project trước khi gọi `/autotest-ios`.

Only continue if `OK`.

---

## Step 0-env: iOS Environment Setup (All Modes)

Run this script — it is fully idempotent (safe to re-run; skips anything already installed):

```python
import subprocess, shutil, sys, platform, os, json
from pathlib import Path

if platform.system() != 'Darwin':
    print('FAILED: iOS testing requires macOS with Xcode. Not supported on this OS.')
    sys.exit(1)

os.environ['PATH'] = '/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:' + os.environ.get('PATH', '')

def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

# ── Find Python 3.9 (any patch — must be 3.9.x) ──────────────────────────────
def find_python39():
    """Return path to Python 3.9.x; any 3.9 patch version is acceptable."""
    import re as _r
    def is_py39(out): return bool(_r.search(r'Python 3\.9\.', out))
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
    r = run(['brew', 'install', 'python@3.9'])
    if r.returncode != 0: print(f'FAILED: brew install python@3.9\n{r.stderr[-400:]}'); sys.exit(1)
    os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')
    PYTHON = find_python39()
    if not PYTHON:
        print('FAILED: Python 3.9 not found after install.\nInstall manually: https://www.python.org/downloads/release/python-3913/'); sys.exit(1)

# ── RF Python packages (pinned versions — single source of truth) ─────────────
REQUIRED = {'robotframework':'7.2.2','robotframework-appiumlibrary':'1.6',
            'Appium-Python-Client':'2.2.0','robotframework-seleniumlibrary':'6.7.1',
            'robotframework-requests':'0.9.7','requests':'2.32.5',
            'selenium':'4.1.3','webdriver-manager':'4.0.2',
            'robotframework-tidy':'4.16.0','PyYAML':'6.0.2','RESTinstance':'1.4.4'}
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

# ── Xcode (cannot be auto-installed — must come from App Store) ───────────────
xcode_app = Path('/Applications/Xcode.app')
if not xcode_app.exists():
    print('FAILED: Xcode not found.\nInstall Xcode from the Mac App Store, then re-run.')
    sys.exit(1)

# Ensure xcode-select points to the installed Xcode
r = run(['xcode-select', '-p'])
if '/Xcode.app' not in r.stdout:
    run(['sudo', 'xcode-select', '-s', '/Applications/Xcode.app/Contents/Developer'])

# Accept Xcode license if not yet accepted
run(['sudo', 'xcodebuild', '-license', 'accept'])

# ── Node.js ───────────────────────────────────────────────────────────────────
if not shutil.which('node'):
    print('Installing Node.js...')
    r = run(['brew', 'install', 'node'])
    if r.returncode != 0: print(f'FAILED: brew install node\n{r.stderr[-400:]}'); sys.exit(1)

# ── Appium ────────────────────────────────────────────────────────────────────
appium = shutil.which('appium')
if not appium:
    print('Installing Appium...')
    r = subprocess.run('npm install -g appium', shell=True,
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0: print(f'FAILED: npm install -g appium\n{r.stderr[-400:]}'); sys.exit(1)
    appium = shutil.which('appium')

# ── XCUITest driver ───────────────────────────────────────────────────────────
# Use `appium driver list --installed` so custom APPIUM_HOME is respected
_drv_r = subprocess.run(f'"{appium}" driver list --installed', shell=True,
                        capture_output=True, text=True, timeout=30)
if 'xcuitest' not in (_drv_r.stdout + _drv_r.stderr).lower():
    print('Installing XCUITest driver...')
    r = subprocess.run(f'"{appium}" driver install xcuitest', shell=True,
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0: print(f'FAILED: appium driver install xcuitest\n{r.stderr[-400:]}'); sys.exit(1)

_appium_home = os.environ.get('APPIUM_HOME', str(Path.home() / '.appium'))
driver_path = Path(_appium_home) / 'node_modules' / 'appium-xcuitest-driver'

print('\n=== Environment paths ===')
print(f'  Python  : {PYTHON}')
print(f'  Xcode   : /Applications/Xcode.app')
print(f'  node    : {shutil.which("node") or "not found"}')
print(f'  appium  : {appium or "not found"}')
print(f'  XCUITest: {driver_path if driver_path.exists() else "installed (custom APPIUM_HOME)"}')
print('OK')
```

- If `OK` → use `PYTHON` (Python 3.9) for **all** `robot` and `python -m robotidy` calls this session.
- If `FAILED:` → **STOP**, show user the output, do not continue.
- **Never auto-update Python version or the pinned versions in `REQUIRED`.** If an update seems necessary, STOP and ask the user with a specific reason.
- **Only exception that requires manual action:** Xcode must be installed from the Mac App Store.

---

## Step 0a: Detect Existing Project Structure (All Modes)

```python
import os, glob
has_tests = bool(glob.glob('automation_test/tests/**/*.robot', recursive=True) + glob.glob('automation_test/features/**/*.resource', recursive=True))
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

**If `NEW`** → scaffold freely in Step 0b. Continue.

---

**If `EXTERNAL`** — tìm thấy `.robot`/`.resource` nằm ngoài `automation_test/` (framework đã có ở vị trí khác, không theo convention của bộ skill này). **Không tự ý di chuyển** — luôn hỏi user trước:

> Tôi thấy project đã có code test ở ngoài `automation_test/`:
> `<liệt kê path tìm được>`
>
> Bạn muốn:
> **1** — Giữ nguyên toàn bộ ở vị trí cũ, viết TC mới tiếp tục đúng ở đó — không tạo `automation_test/`.
> **2** — Giữ nguyên code cũ, tạo `automation_test/` riêng cho các TC mới từ giờ (2 cấu trúc song song).
> **3** — Di chuyển toàn bộ code cũ vào `automation_test/` theo chuẩn FOM (giống bước restructure ở case `PARTIAL`).

**Nếu chọn 1** — dùng skill này **y như case `COMPLIANT`**, chỉ khác gốc thư mục — đây là đường để project cũ giữ 100% code ở ngoài `automation_test/` mà vẫn dùng skill bình thường:
1. Xác định gốc thư mục thực tế từ các path trong `_outside` (thư mục cha chung chứa các file `.robot`/`.resource` đó — có thể tên `tests/`, `robot/`, hay bất kỳ tên nào project đang dùng). Gọi là `<ROOT>`.
2. Đọc conventions hiện có tại `<ROOT>`: file imports (nếu có), 1 file keywords, 1 file variables — naming prefix, wrapper, cấu trúc thư mục con.
3. Từ đây tới hết task: **mọi chỗ trong skill này nói tới `automation_test/...` hiểu là `<ROOT>/...`** (giữ đúng tên/layout thư mục con hiện có của `<ROOT>`, không đổi tên thư mục của user, không tạo `automation_test/` mới).
4. Theo đúng conventions hiện có — keyword names, import paths, file layout, wrapper names. Scaffold chỉ những gì còn thiếu **trong `<ROOT>`**. Không overwrite file đang có.

**Nếu chọn 2** → giữ nguyên code cũ không đụng tới, tạo `automation_test/` mới theo đúng Step 0b (như case `NEW`) cho các TC từ giờ.

**Nếu chọn 3** → thực hiện đúng quy trình "perform restructure" ở case `PARTIAL` bên dưới (bước 1–6), chỉ khác nguồn quét ở bước 1 là danh sách `_outside` đã tìm được ở Step 0a (thay vì `automation_test/**/*.resource`).

---

**If `COMPLIANT`** — read conventions before touching anything:
1. Read `automation_test/config/imports.resource` — libraries and resources already imported.
2. Read one existing `_keywords.resource` — naming prefix, wrapper names.
3. Read one existing `_variables.resource` — variable naming convention.

Rules for the rest of this session:
- Follow the project's conventions — keyword names, import paths, file layout.
- Scaffold only what is missing — never overwrite existing files.
- Verify imports before saving — new code must only reference what `automation_test/config/imports.resource` already provides.
- Suggest, never force — note deviations from autotest-ios-best-practices as optional suggestions at the end.

---

**If `PARTIAL`** — project has test files but missing key framework structure. Ask the user:

> Tôi thấy project đã có test files nhưng chưa có đủ cấu trúc framework (`automation_test/config/imports.resource` hoặc `automation_test/common/common_keywords.resource` chưa có).
>
> Bạn có muốn tôi **sắp xếp lại cấu trúc** không?
> - **Có**: Tôi sẽ di chuyển code hiện có vào đúng file theo chuẩn FOM và tạo các file scaffold còn thiếu. **Nội dung code (tên keyword, logic, locator values) sẽ không bị thay đổi.**
> - **Không**: Tôi sẽ theo cấu trúc hiện tại và chỉ thêm vào những gì còn thiếu.

**If user chooses Yes — perform restructure:**

1. **Scan all existing files:**
   ```python
   import glob
   files = sorted(glob.glob('automation_test/tests/**/*.robot', recursive=True) + glob.glob('automation_test/**/*.resource', recursive=True))
   print('\n'.join(files))
   ```
   Read each file. **Phạm vi chỉ trong `automation_test/`** — không quét, không đụng tới file nằm ngoài `automation_test/` dù restructure là "Yes" (xem case `EXTERNAL` ở trên).

2. **Classify code by FOM — do not change content, only move it:**

   | Code | From | To |
   |---|---|---|
   | `*** Test Cases ***` | `.robot` | Keep in `.robot` |
   | `*** Keywords ***` in `.robot` | `.robot` | `automation_test/features/<feature>/<feature>_keywords.resource` |
   | `*** Variables ***` containing locators (value is a locator string: `accessibility_id=`, `ios=`, `name=`, `xpath=`, `//`, or variable names with prefix `${btn_}`, `${inp_}`, `${lbl_}`, `${txt_}`, `${sw_}`, `${tab_}`, `${cell_}`) | any file | `automation_test/features/<feature>/<feature>_variables.resource` |
   | `*** Variables ***` containing global config (`${TIMEOUT_*}`, `${APPIUM_URL}`, `${BUNDLE_ID}`, `${EXECUTION_TARGET}`) | any file | `automation_test/common/common_variables.resource` |
   | `Library` imports | scattered | `automation_test/config/imports.resource` (deduplicate) |

3. **Create missing scaffold files** using the template in Step 0b — only create files that do not already exist.

4. **Update imports in each file:**
   - `.robot`: `*** Settings ***` keeps only `Resource    ../config/imports.resource` (and `Variables` if using YAML).
   - `_keywords.resource`: import `../../config/imports.resource` and `<feature>_variables.resource`.
   - `automation_test/config/imports.resource`: all Library + Resource for `automation_test/common/common_keywords.resource` + Resource for each `_keywords.resource`.

5. **Format all changed files:**
   ```bash
   python -m robotidy automation_test/tests/ automation_test/features/
   ```

6. Report a list of what was moved and which new files were created.

**If user chooses No:**
- Read existing files to understand the current conventions.
- Follow those conventions for new code — do not modify existing files.
- Suggest migration at the end of the task if needed.

---

## MODE A — Write / Update

### Step 0b: Scaffold if missing

Check for `automation_test/tests/`, `automation_test/features/`, `automation_test/common/`, `automation_test/config/`, `automation_test/data/`. If missing, create:

```bash
python -c "import os; [os.makedirs(d, exist_ok=True) for d in ['tests','features','common','config','data','results','python_lib']]"
```

**`automation_test/common/common_variables.resource`** — fill values from `global-data.md` (ask user if not found):

```robotframework
*** Variables ***
${TIMEOUT_MIN}          5s
${TIMEOUT_DEFAULT}      15s
${TIMEOUT_MAX}          30s

# --- Execution target: local | device_farm ---
${EXECUTION_TARGET}     local

# --- Local simulator/device config ---
${APPIUM_URL}           http://127.0.0.1:4723
${DEVICE_NAME}          iPhone 15
${PLATFORM_VERSION}     17.0
${BUNDLE_ID}            com.example.app
${APP_PATH}             ${EMPTY}    # absolute path to .app/.ipa; leave empty to use bundleId
${NO_RESET}             ${TRUE}

# --- Shared (local + device farm) ---
${DEVICE_UDID}          ${EMPTY}    # optional for simulator; required for real device / device farm

# --- Device Farm config ---
${FARM_URL}             10.207.247.201/mcloud/wd/hub
${FARM_USERNAME}        your_username
${FARM_ACCESS_KEY}      your_access_key
```

**`automation_test/common/common_keywords.resource`**:

```robotframework
*** Settings ***
Resource    common_variables.resource

*** Keywords ***
Common - Open App
    [Arguments]    ${no_reset}=${NO_RESET}
    IF    '${EXECUTION_TARGET}' == 'local'
        Common - Open App Local    ${no_reset}
    ELSE IF    '${EXECUTION_TARGET}' == 'device_farm'
        Common - Open App Device Farm    ${no_reset}
    ELSE
        Fail    Unknown EXECUTION_TARGET: ${EXECUTION_TARGET}. Valid values: local | device_farm
    END

Common - Open App Local
    [Arguments]    ${no_reset}
    ${caps}=    Create Dictionary
    ...    platformName=iOS
    ...    platformVersion=${PLATFORM_VERSION}
    ...    deviceName=${DEVICE_NAME}
    ...    automationName=XCUITest
    ...    bundleId=${BUNDLE_ID}
    ...    autoAcceptAlerts=${FALSE}
    ...    noReset=${no_reset}
    ...    newCommandTimeout=300
    ...    wdaLaunchTimeout=120000
    ...    wdaConnectionTimeout=240000
    IF    '${DEVICE_UDID}' != '${EMPTY}'
        Set To Dictionary    ${caps}    udid=${DEVICE_UDID}
    END
    IF    '${APP_PATH}' != '${EMPTY}'
        Set To Dictionary    ${caps}    app=${APP_PATH}
        Remove From Dictionary    ${caps}    bundleId
    END
    Open Application    ${APPIUM_URL}    &{caps}

Common - Open App Device Farm
    [Arguments]    ${no_reset}
    ${farm_url}=    Set Variable    http://${FARM_USERNAME}:${FARM_ACCESS_KEY}@${FARM_URL}
    ${caps}=    Create Dictionary
    ...    platformName=iOS
    ...    platformVersion=${PLATFORM_VERSION}
    ...    deviceName=${DEVICE_NAME}
    ...    automationName=XCUITest
    ...    bundleId=${BUNDLE_ID}
    ...    autoAcceptAlerts=${FALSE}
    ...    noReset=${no_reset}
    ...    newCommandTimeout=300
    ...    wdaLaunchTimeout=120000
    ...    wdaConnectionTimeout=240000
    IF    '${DEVICE_UDID}' != '${EMPTY}'
        Set To Dictionary    ${caps}    udid=${DEVICE_UDID}
    END
    IF    '${APP_PATH}' != '${EMPTY}'
        Set To Dictionary    ${caps}    app=${APP_PATH}
        Remove From Dictionary    ${caps}    bundleId
    END
    Open Application    ${farm_url}    &{caps}

Common - Close App
    Close Application

Common - Wait For Element Visible
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_DEFAULT}
    Wait Until Keyword Succeeds    3x    1s
    ...    Wait Until Element Is Visible    ${locator}    timeout=${timeout}

Common - Click Element
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_DEFAULT}
    Common - Wait For Element Visible    ${locator}    ${timeout}
    Click Element    ${locator}

Common - Input Text
    [Arguments]    ${locator}    ${text}    ${timeout}=${TIMEOUT_DEFAULT}
    Common - Wait For Element Visible    ${locator}    ${timeout}
    Clear Text    ${locator}
    Input Text    ${locator}    ${text}

Common - Click If Exists
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_MIN}
    ${visible}=    Run Keyword And Return Status
    ...    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    IF    ${visible}    Click Element    ${locator}

Common - Get Text
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_DEFAULT}
    Common - Wait For Element Visible    ${locator}    ${timeout}
    ${text}=    Get Text    ${locator}
    RETURN    ${text}

Common - Tap Navigation Back
    Click Element    ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[1]
    Sleep    0.3s

Common - Swipe Up To Element
    [Arguments]    ${locator}    ${max_swipes}=15    ${timeout}=${TIMEOUT_MIN}
    FOR    ${i}    IN RANGE    ${max_swipes}
        ${visible}=    Run Keyword And Return Status
        ...    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
        IF    ${visible}    BREAK
        Swipe By Percent    50    80    50    20    800
    END
    Wait Until Element Is Visible    ${locator}    timeout=${TIMEOUT_DEFAULT}

Common - Swipe Down To Element
    [Arguments]    ${locator}    ${max_swipes}=15    ${timeout}=${TIMEOUT_MIN}
    FOR    ${i}    IN RANGE    ${max_swipes}
        ${visible}=    Run Keyword And Return Status
        ...    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
        IF    ${visible}    BREAK
        Swipe By Percent    50    20    50    80    800
    END
    Wait Until Element Is Visible    ${locator}    timeout=${TIMEOUT_DEFAULT}

Common - Handle Alert
    [Arguments]    ${button_name}=Allow
    ${present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=${TIMEOUT_MIN}
    IF    ${present}
        ${btn_present}=    Run Keyword And Return Status
        ...    Page Should Contain Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == '${button_name}'`]
        IF    ${btn_present}
            Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == '${button_name}'`]
        ELSE
            Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[1]
        END
    END
```

**`automation_test/config/imports.resource`**:

```robotframework
*** Settings ***
Library     AppiumLibrary
Library     OperatingSystem
Library     Collections
Library     String

Resource    ../common/common_keywords.resource
```

> Each file is created **only if it does not already exist** — never overwrite files the project already has.

---

### Step 0b2: DB Signal Detection

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

### Step 0c: Confirm execution target and device config

Check for domain documentation:

```bash
python -c "import glob; hits=glob.glob('automation_test/docs/global-data.md'); print('\n'.join(hits) or 'NONE')"
```

- **If found**: read `global-data.md` to get `bundleId`, `deviceName`, `platformVersion`, and device farm host values.

- **If NONE**: No domain docs found. Guide the user through creating one — ask ALL 4 questions in a single message. **Do not omit any question** — the user decides which to skip.

  > Không tìm thấy domain docs. Tôi sẽ giúp tạo để lần sau không phải nhập lại.
  >
  > **1. Cấu hình thiết bị & app** *(lưu vào `automation_test/docs/global-data.md`)*:
  > - **bundleId** — ví dụ: `com.example.app`
  > - **deviceName** — ví dụ: `iPhone 15`
  > - **platformVersion** — ví dụ: `17.0`
  > - **Execution target** — `local_simulator`, `local_device`, hoặc `device_farm`
  > - **DEVICE_UDID** — (simulator: leave empty unless specific; real device: required; device_farm: not needed)
  > - **FARM_URL / FARM_USERNAME / FARM_ACCESS_KEY** — (chỉ cần nếu device_farm; bỏ trống nếu không)
  > - **APP_PATH** — để trống nếu app đã cài và dùng bundleId; điền path `.app/.ipa` nếu cài fresh
  > - **Tài khoản test** — username / password đăng nhập app (bỏ trống nếu không cần)
  >
  > **2. Tổng quan sản phẩm** *(lưu vào `automation_test/docs/product-overview.md` — tùy chọn)*:
  > Mô tả ngắn về sản phẩm: mục tiêu, tính năng chính, đối tượng người dùng. Gõ "skip" nếu chưa có.
  >
  > **3. Ngữ cảnh nghiệp vụ cho feature này** *(lưu vào `automation_test/docs/features/<feature>/business-scenario.md` — tùy chọn)*:
  > Mô tả ngắn về luồng người dùng, màn hình, kịch bản kiểm thử cho feature này. Gõ "skip" nếu chưa có.
  >
  > **4. Thiết kế chi tiết cho feature này** *(lưu vào `automation_test/docs/features/<feature>/detail-design.md` — tùy chọn)*:
  > Mô tả màn hình, navigation flow, cấu trúc dữ liệu, backend API mà app gọi. Gõ "skip" nếu chưa có.

  After user replies — create domain files from the answers (and gitignore the credentials file):
  ```bash
  mkdir -p automation_test/docs/features/<feature>
  grep -qxF 'automation_test/docs/global-data.md' .gitignore 2>/dev/null || echo 'automation_test/docs/global-data.md' >> .gitignore
  ```

  1. **`automation_test/docs/global-data.md`** — write all provided device/app config and credentials. Omit any field the user skipped.
  2. **`automation_test/docs/product-overview.md`** — write if user provided content; skip entirely if user wrote "skip" or left blank.
  3. **`automation_test/docs/features/<feature>/business-scenario.md`** — write if user provided content; skip entirely if user wrote "skip" or left blank.
  4. **`automation_test/docs/features/<feature>/detail-design.md`** — write if user provided content; skip entirely if user wrote "skip" or left blank.

  Then read the created files and continue as if **If found** from the start.

**For local simulator:**
- Leave `DEVICE_UDID` empty unless targeting a specific simulator.

**For local real device:**
- `DEVICE_UDID` is required — obtain from Finder or `xcrun xctrace list devices`.
- Signing (`xcodeOrgId`, `xcodeSigningId`) may be required — ask the user if WDA fails to start.
- **Finding the `bundleId` of an app already installed on the device (by name, not bundleId)** — **bắt buộc dùng `ideviceinstaller`, không dùng `xcrun devicectl device info apps`:**
  ```bash
  # Cài nếu chưa có (idempotent)
  which ideviceinstaller >/dev/null 2>&1 || brew install ideviceinstaller

  # Liệt kê TOÀN BỘ app do user cài (App Store, TestFlight, Xcode, ad-hoc) — không chỉ app dev-provisioned
  # -o list_user là default nên có thể bỏ, viết rõ ra để tránh nhầm với list_system/list_all
  timeout 20 ideviceinstaller -u <udid> --list-apps -o list_user
  ```
  Lọc theo tên app (case-insensitive, so khớp gần đúng) trong output để lấy đúng `bundleId`.
  **Đã tự xác nhận lỗi thật:** `xcrun devicectl device info apps` chỉ liệt kê app cài qua Xcode/MDM (dev-provisioned) — **không thấy** app cài từ App Store dù quét lại nhiều lần, dẫn tới báo sai "không tìm thấy app" rồi phải hỏi lại user nhiều lượt. Luôn dùng `ideviceinstaller --list-apps` trước cho mọi trường hợp tìm app trên real device theo tên; chỉ hỏi lại user nếu app thực sự không xuất hiện trong danh sách này.
  > `list --user` (subcommand style) **không tồn tại** ở bản `ideviceinstaller` chuẩn cài qua `brew install ideviceinstaller` — lệnh đúng là `--list-apps` (hoặc `-l`), option `-o list_user` để lọc app user (đây cũng là default nếu không truyền `-o`). Chạy `ideviceinstaller -h` để xác nhận cú pháp nếu nghi ngờ version khác.
  >
  > **Luôn bọc `timeout`** (vd 20s) khi gọi lệnh này. Đã tự xác nhận: bản `ideviceinstaller`/`libimobiledevice` cũ cài qua brew (vd 1.1.1) có thể **treo vô hạn** ("initial read failed!" lặp liên tục qua `installation_proxy`) khi nói chuyện với **iOS 17+** — một lỗi tương thích đã biết giữa libimobiledevice cũ và iOS mới, không liên quan tới trust/pairing (pairing vẫn valid, `ideviceinfo` vẫn trả nhanh bình thường — chỉ riêng `--list-apps` bị treo). Nếu timeout → báo user: `brew upgrade ideviceinstaller libimobiledevice` (lưu ý: có thể phải build từ source nếu máy không có bottle sẵn cho macOS đang dùng, có thể mất nhiều phút) — để user tự chạy trong terminal riêng, **không block session hiện tại chờ build**.

**For device farm:**
- Set `${EXECUTION_TARGET}` = `device_farm`.
- Do NOT ask for `DEVICE_UDID` — device farm assigns a device automatically.
- Ask user for `FARM_URL` (e.g. `10.207.247.201/mcloud/wd/hub`), `FARM_USERNAME`, and `FARM_ACCESS_KEY` — save all three directly to `automation_test/common/common_variables.resource`.

**If found (or after creating domain files above)** — read `global-data.md`, write device config and credentials to `automation_test/common/common_variables.resource` (create if missing), then proceed to Step 1.

### Step 1: Read & Plan

**1a.** Find the manual TC file:

```bash
python -c "import glob, sys; f=sys.argv[1]; hits=[p for p in glob.glob('automation_test/docs/features/**/test-cases.md', recursive=True) if f.lower() in p.lower()]; print('\n'.join(hits))" "<feature>"
```

**If nothing found** → ask the user ONE question:

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
- Thông báo đã lưu → **tiếp tục ngay** từ đầu Step 1a (đọc file vừa tạo).

**Nếu chọn 2 (tạo từ tài liệu):**
- Kiểm tra domain docs:
  ```bash
  python -c "import glob; hits=[h for h in glob.glob('automation_test/docs/features/**/*.md', recursive=True) if any(k in h for k in ['business-scenario','detail-design'])]; print('\n'.join(hits) or 'NONE')"
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

- Chờ xác nhận → khi đồng ý, ghi file `automation_test/docs/features/<feature>/test-cases.md` → **tiếp tục ngay** từ đầu Step 1a.

**Nếu user paste TC trực tiếp:** lưu vào `automation_test/docs/features/<feature>/test-cases.md` → tiếp tục ngay từ đầu Step 1a.

**1b. Read:**
- **Manual TC file** (required) — exact steps, preconditions, assertions, business rules per TC.
- **`business-scenario.md`** (read if exists) — UI components, user flows, expected behavior.
- **`global-data.md`** (read if exists) — device capabilities, credentials.
- **`detail-design.md`** (read if exists) — API/data context only (no UI selectors).

If none of the optional docs exist, use the manual TC file as the sole source of truth. Ask the user if any step is ambiguous.

**1b2. Chọn TC cần viết — bắt buộc, kể cả khi gọi qua workflow.**

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

Chờ câu trả lời thật trước khi tiếp tục — **không tự mặc định "viết hết" để tiết kiệm bước**. Từ đây tới hết Step 2/3, chỉ viết và chạy đúng các TC đã chọn — không tự ý viết thêm TC ngoài danh sách dù tiện làm luôn.

**1c.** Scan existing `automation_test/features/**/*.resource` and `automation_test/tests/*.robot` for reusable locators and keywords.

**1d. Resolve navigation path.** From the manual TC's preconditions, determine the starting screen. Plan the `<Feature> - Open Screen` keyword: what `Common - Open App` must launch, and what navigation steps are needed to reach the feature's starting screen.

**1e. Plan locators.** Use the locator priority from `autotest-ios-best-practices` Section 2:
`accessibility_id` > `name` > `ios=` predicate > `ios=**/` class chain > `xpath`

Never use `id=` (Android resource-id) or `android=` on iOS. Mark uncertain locators `# TODO: verify with Get Source or Appium Inspector`.

**1f. OTP / SMS Detection — STOP if any TC step involves OTP or SMS.**

Scan the manual TC for keywords: OTP, mã OTP, mã xác thực, mã xác minh, verification code, one-time password, SMS, tin nhắn, "nhập mã".

If found → STOP and ask the user before writing any code:

> TC này yêu cầu OTP/SMS. Để tự động hoá bước này, tôi cần biết:
>
> 1. **SIM cắm trên thiết bị test** — OTP đến qua SMS trên chính thiết bị đang test.
>    - App có tự động điền OTP không (iOS 12+ auto-fill from SMS)?
>    - Hay user phải mở app Tin nhắn và nhập tay?
> 2. **Web/API service** — OTP lấy từ portal hoặc API bên ngoài.
>    - URL của service là gì?
>    - Cần thông tin đăng nhập không?
>
> Nếu chưa biết → chờ user xác nhận, không giả định.

Platform notes for implementation once user answers:
- **Auto-fill (option 1a)**: iOS 12+ automatically suggests the OTP from SMS on the QuickType bar — just use `Common - Wait For Element Visible` and verify the field has been filled. No need to read the SMS manually.
- **Manual SMS read (option 1b)**: Appium/XCUITest **cannot read the SMS inbox**. If the user chooses this option, respond:
  > iOS does not allow automation to read SMS messages directly. Consider using a Web/API service (option 2) or a SIM with auto-fill.
- **Web/API service (option 2)**: Use `RequestsLibrary` to call the API and retrieve the OTP, then use `Common - Input Text`.

> **Warning — avoid accidentally reading a stale OTP**: The inbox may contain multiple messages from the same sender number with the same content but different codes. If you only fetch the first message without checking the timestamp, you can easily read the OTP from a previous send.
>
> **Mandatory rule**: Record a timestamp **before** triggering the action that sends the OTP. Then only accept messages with `received_at > timestamp_before_trigger`.
>
> - Web/API service: use the `received_after=<timestamp>` or `since_id=<oldest_message_id>` filter if the service supports it. If no filter is available → fetch the list and discard any message with a timestamp ≤ the time the test started.
> - If timeout expires and no new message arrives → FAIL explicitly; do not fall back to a stale OTP.

**Manual TC is the contract — 100% fidelity required:**

- **Test case name**: derived directly from TC title in `Snake_Case`. Never invent an alternative.
- **Steps**: automate every step in the same order — do not add, remove, or reorder.
- **Assertions**: verify every expected result from the TC — do not substitute weaker assertions.

If a UI element or behavior in the manual TC is not found on simulator/device:
1. Capture screenshot and confirm you are on the correct screen.
2. **STOP. Write no code for that TC.**
3. Report:
   > **TC-NNN discrepancy found:**
   > Manual TC says: `<exact step or element>`
   > Actual app on `<device>`: `<what you observe>`
   > Please verify manually whether the test case is still correct.
4. Wait for user decision before continuing.

**If user confirms an app bug** → ask:
> Bug đã được xác nhận. Bạn có muốn tôi viết test này không? Test sẽ FAIL tại bước `[element/action]` vì bug chưa fix.

- If yes: write the test exactly as the manual TC describes. Add tag `known-bug` only.
- If no: skip this TC.

### Step 2: Write FOM Files

**Bắt buộc**: dùng RobotMCP (`.claude/skills/autotest-mcp-assist/SKILL.md`) để verify locator bằng live session (app không cần đóng/mở lại) trước khi ghi vào file. Nếu RobotMCP chưa cài/chưa đăng ký, `autotest-mcp-assist` tự cài và sẽ yêu cầu mở session mới trước khi tiếp tục.

- **Variables file** (`_variables.resource`): locators only, correct type prefixes (`${btn_}`, `${inp_}`, `${lbl_}`, `${txt_}`, `${sw_}`, `${tab_}`, `${cell_}`, `${nav_}`, `${icon_}`). No imports.
- **Keywords file** (`_keywords.resource`):
  ```robotframework
  *** Settings ***
  Resource    ../../config/imports.resource
  Resource    <feature>_variables.resource
  ```
  Add a `Resource` line for this file in `automation_test/config/imports.resource`.
  - Use `Common - ...` wrappers only (no raw AppiumLibrary).
  - One scenario keyword per TC. Declare `[Arguments]    ${test_data}` **only if the keyword uses it**.
  - Every keyword must have **≥ 2 keyword calls**. Exception: named helper for `Wait Until Keyword Succeeds`, or step shared across multiple TCs.
- **`<Feature> - Open Screen`**: called from `Test Setup` — opens app, handles any initial alert, navigates from launch screen to the feature's starting screen, waits for a key landmark element.
- **Test lifecycle**: `Test Setup` → open app. `Test Teardown` → `Common - Close App` only.
- **YAML** (`automation_test/data/<feature>.yaml`): top-level `data:`, child keys = test case names. Only add entries for TCs that use data.
- **Test suite** (`automation_test/tests/<feature>.robot`):
  ```robotframework
  *** Settings ***
  # --- Local simulator ---
  # robot --loglevel TRACE -d automation_test/results/ -t "Test_Case_Name" automation_test/tests/<feature>.robot
  #
  # --- Local real device ---
  # robot --loglevel TRACE -d automation_test/results/ -v DEVICE_UDID:<udid> -t "Test_Case_Name" automation_test/tests/<feature>.robot
  #
  # --- Device Farm ---
  # robot --loglevel TRACE -d automation_test/results/ -v EXECUTION_TARGET:device_farm -t "Test_Case_Name" automation_test/tests/<feature>.robot
  Resource     ../config/imports.resource
  Variables    ../data/<feature>.yaml

  Test Setup      <Feature> - Open Screen
  Test Teardown   Common - Close App

  *** Test Cases ***
  User_Can_Do_Something
      [Tags]    <feature>    smoke    TC-001
      <Feature> - Do Something    ${data["${TEST_NAME}"]}

  User_Can_See_Something
      [Tags]    <feature>    regression    TC-002
      <Feature> - Verify Something
  ```
  Omit `Variables` import if no TC uses data.
- Format: `python -m robotidy automation_test/tests/<feature>.robot automation_test/features/<feature>/`

### Step 3: Run

**Always run the test — even known-bug TCs must be executed at least once.**

**For local target** — check and auto-start Appium if needed:
```bash
python -c "import urllib.request,json; print('APPIUM_RUNNING' if json.loads(urllib.request.urlopen('http://127.0.0.1:4723/status',timeout=3).read()).get('value',{}).get('ready') else 'APPIUM_DOWN')" 2>/dev/null || echo APPIUM_DOWN
```
If `APPIUM_DOWN` → start Appium in background and wait until ready (do NOT ask the user):
```bash
appium > /tmp/appium.log 2>&1 &
python -c "
import urllib.request, json, time
for _ in range(15):
    try:
        r = json.loads(urllib.request.urlopen('http://127.0.0.1:4723/status', timeout=2).read())
        if r.get('value', {}).get('ready'): print('APPIUM_READY'); break
    except: pass
    time.sleep(2)
else: print('APPIUM_TIMEOUT')
"
```
If `APPIUM_TIMEOUT` → read `/tmp/appium.log` to diagnose, report the error to the user.

**For device_farm target** — skip Appium and simulator checks. `FARM_USERNAME` and `FARM_ACCESS_KEY` are in `common_variables.resource` — run directly.

Before running, verify `automation_test/common/common_variables.resource` has no placeholder values (`your_username`, `your_access_key`, empty credentials). If any placeholder remains → ask the user for the real value and update the file first. All required values must be in files before running — never ask the user to run `export` commands manually.

**Run only the TC just written:**

```bash
# Local simulator
robot --loglevel TRACE -d automation_test/results/ -t "Test_Case_Name" automation_test/tests/<feature>.robot

# Local real device
robot --loglevel TRACE -d automation_test/results/ -v DEVICE_UDID:<udid> -t "Test_Case_Name" automation_test/tests/<feature>.robot

# Device farm
robot --loglevel TRACE -d automation_test/results/ -v EXECUTION_TARGET:device_farm -t "Test_Case_Name" automation_test/tests/<feature>.robot
```

```bash
python .claude/skills/autotest-results/scripts/rf_results.py --output automation_test/results/output.xml --sections summary,details --pretty
```

After the run, assess shared resources. If any change could affect other existing TCs, report:
> **Heads up:** Changes to `[shared resource]` may affect `[TC-NNN, ...]`. Want to re-run the full suite?

Do not run the full suite automatically.

### Step 4: Debug & Fix

```bash
python .claude/skills/autotest-results/scripts/rf_results.py \
  --output automation_test/results/output.xml --sections errors --pretty
```

Read failure screenshot PNG with the Read tool.

| Error | Context | Fix |
|---|---|---|
| `NoSuchElementException` / timeout | Both | Wrong locator — dùng RobotMCP (`.claude/skills/autotest-mcp-assist/SKILL.md`) để verify locator live tại đúng màn hình fail — không cần mở lại app/login lại. |
| `Could not connect to Appium` | Local | Appium failed to start — check `/tmp/appium.log` |
| `No simulator found` | Local | `xcrun simctl list devices` — boot simulator with `xcrun simctl boot "iPhone 15"` |
| `WebDriverAgent failed to start` | Local | Increase `wdaLaunchTimeout=180000`; rebuild WDA if persistent |
| `Code signing error` | Real device | Add `xcodeOrgId` and `xcodeSigningId` capabilities |
| `bundleId not found` (simulator) | Local sim | App not installed on simulator — use `APP_PATH` or `xcrun simctl install booted <path>` |
| `bundleId not found` (real device, app đã cài) | Real device | Đừng dùng `xcrun devicectl device info apps` — chỉ thấy app dev-provisioned/MDM, bỏ sót app cài từ App Store. Chạy `timeout 20 ideviceinstaller -u <udid> --list-apps` và lọc theo tên app (xem "For local real device" ở Step 0c). |
| `ideviceinstaller --list-apps` treo, không trả về | Real device | Bản `ideviceinstaller`/`libimobiledevice` cũ không tương thích iOS 17+ (lặp "initial read failed!" vô hạn) — luôn bọc `timeout`; nếu timeout, báo user tự chạy `brew upgrade ideviceinstaller libimobiledevice` (có thể build from source, mất vài phút) trong terminal riêng |
| `No keyword with name` | Both | Missing import in `automation_test/config/imports.resource` or typo |
| Alert blocking test | Both | Add `Common - Handle Alert` after `Common - Open App` |
| `FARM_USERNAME / FARM_ACCESS_KEY` auth error | Farm | Wrong credentials — update values in `automation_test/common/common_variables.resource` |
| `401 Unauthorized` on farm | Farm | Wrong credentials — verify `FARM_USERNAME` and `FARM_ACCESS_KEY` |
| `No device with udid <id>` on farm | Farm | Wrong UDID — check MCloud web UI for available iOS device UDIDs |
| Device busy / session active on farm | Farm | Choose a different `DEVICE_UDID` from available pool |
| Element found in `Get Source` but click fails | Both | XCUITest click issue — get center coords with `Get Element Location` + `Get Element Size`, then `Tap    1    ${x}    ${y}` |
| `StaleElementReferenceException` | Both | Use locator string directly, not stored element references |
| TC says element exists but not in view | Both | **STOP** — report discrepancy, wait for user decision |
| `XCTRunnerDaemonSession` error | Real device | Restart device and Appium server |

**Auto-fix environment errors:** If the robot run fails with any of these patterns:
- `No module named '<anything>'` — re-run `Step 0-env` pip install block, then retry the robot run once.
- `Could not connect to Appium` — re-start Appium (`appium > /tmp/appium.log 2>&1 &`) wait for ready, retry once.
- `Xcode not installed` / `xcodebuild: not found` — STOP, tell user to install Xcode from Mac App Store (this is the only manual exception).

These fixes make future runs on the same machine succeed without any user action.

Repeat Fix → Re-run until test passes (or fails at the expected step for known-bug TCs).

---

## MODE B — Refactor

**Trigger:** `/autotest-ios refactor [<feature>]`

No device config confirmation. No test run unless user asks.

### Steps

**B1. Scope:**
- `refactor` alone → all files in `automation_test/features/`, `automation_test/tests/`, `automation_test/data/`, `automation_test/config/`.
- `refactor <feature>` → only that feature's files.

**B2.** Read all in-scope files.

**B3. Apply rules — check each item:**

| Rule | Action |
|---|---|
| No raw AppiumLibrary in feature keywords | Replace with `Common - ...` wrappers |
| Every keyword ≥ 2 calls | Inline single-call keywords; keep named retry helpers and shared setup as exceptions |
| `${td}` → `${test_data}` | Rename everywhere |
| No unused `[Arguments]` | Remove `${test_data}` from keywords that don't use it; remove matching `${data["${TEST_NAME}"]}` in `.robot` |
| No unused YAML entries | Remove data entries for TCs that no longer pass data |
| No `Variables` import if no TC uses data | Remove |
| Locator type prefixes correct | Fix incorrect prefixes |
| No hardcoded capabilities inline in `Open Application` | Move to `common_variables.resource`; use dict-based `Common - Open App` |
| No hardcoded timeout values | Replace with `${TIMEOUT_MIN/DEFAULT/MAX}` |
| No `Sleep` without comment | Add comment, or replace with explicit wait |
| No `id=` locators (Android resource-id on iOS) | Replace with `accessibility_id` or `name` |
| No `android=` selectors on iOS | Replace with `ios=` predicate or class chain |
| No `autoAcceptAlerts=True` in capabilities | Replace with `Common - Handle Alert` calls |
| Credentials not hardcoded | `FARM_USERNAME`/`FARM_ACCESS_KEY` must come from `${FARM_USERNAME}`/`${FARM_ACCESS_KEY}` RF variables (defined in `common_variables.resource`), not `Get Environment Variable` |
| File size limits (keywords ≤300, variables ≤150, robot ≤200) | Flag if exceeded |

**B4.** Format all changed files:
```bash
python -m robotidy automation_test/features/<feature>/ automation_test/tests/<feature>.robot
```

**B5.** Report a summary of every change made, grouped by file.

---

## MODE C — Delete

**Trigger:** `/autotest-ios delete <feature> TC-NNN [TC-NNN, ...]`

No device config confirmation. No test run.

### Steps

**C1.** Read all feature files (`_keywords.resource`, `_variables.resource`, `.robot`, YAML).

**C2. For each TC to delete:**
1. **`.robot`** — remove the test case block.
2. **`_keywords.resource`** — remove the scenario keyword. For each sub-keyword it called: if no other keyword references it → remove it too.
3. **`automation_test/data/<feature>.yaml`** — remove the TC's data entry.
4. **`_variables.resource`** — for each locator: if no remaining keyword references it → remove it.
5. **`automation_test/config/imports.resource`** — if the feature's keyword file is now empty → remove its `Resource` line.

**C3.** Format changed files:
```bash
python -m robotidy automation_test/features/<feature>/ automation_test/tests/<feature>.robot
```

**C4.** Report what was removed.

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
## Rules (All Modes)

- All coding conventions from `autotest-ios-best-practices` — follow strictly.
- **No raw AppiumLibrary** in feature keywords — always use `Common - ...` wrappers.
- **Existing project — adapt, don't replace**: if the project already has a working framework, follow its conventions. Suggest migration to best-practices only at the end, never mid-task. Never restructure what is already working.
- Tests are independent — each opens and closes its own app session.
- **Manual TC is the contract** — implement exactly what `automation_test/docs/features/.../test-cases.md` describes.
- **A passing test on wrong behavior is a bug** — forbidden even if it passes.
- **Never choose or switch device config without asking the user** (Mode A Step 0c only).
- **No single-call keywords** — ≥ 2 calls required.
- **No unused arguments** — declare `${test_data}` only when the keyword uses it.
- **Python libraries** — if a custom Python library is needed, create it in `automation_test/python_lib/` at the project root (create the folder if it does not exist). Then add `Library    ../python_lib/<LibraryName>.py` to `automation_test/config/imports.resource`.
- **Farm credentials in `common_variables.resource`** — `FARM_USERNAME` and `FARM_ACCESS_KEY` are stored as Robot Framework variables, not env vars.
- **Never use `id=` or `android=` on iOS** — iOS-only locator strategies only.
- **Ask, never guess** — if any required information is missing (UDID, bundleId, APP_PATH), stop and ask.
- After completing any mode, report a concise summary of what changed.
