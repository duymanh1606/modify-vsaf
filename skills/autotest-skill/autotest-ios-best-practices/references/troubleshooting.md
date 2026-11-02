# iOS Automation Troubleshooting

## Error Reference Table

| Error | Likely Cause | First Step |
|---|---|---|
| `Could not connect to Appium` | Appium not running | `appium` to start; `curl http://127.0.0.1:4723/status` to verify |
| `No simulator found` / `device not found` | Simulator not booted | `xcrun simctl list devices`, then `xcrun simctl boot "iPhone 15"` |
| `WebDriverAgent failed to start` | WDA build/launch timeout | Increase `wdaLaunchTimeout=180000`; rebuild WDA if persistent |
| `Code signing error` | Real device missing team ID | Add `xcodeOrgId` and `xcodeSigningId` capabilities |
| `bundleId not found` (simulator) | App not installed | Install app with `xcrun simctl install booted /path/to/App.app` or use `app=` path |
| `bundleId not found` (real device, app trông như đã cài) | Dùng sai lệnh để tra bundleId | `xcrun devicectl device info apps` chỉ thấy app dev-provisioned/MDM, bỏ sót app cài từ App Store — dùng `timeout 20 ideviceinstaller -u <udid> --list-apps` thay thế (xem "Finding bundleId of an Installed App" bên dưới) |
| `XCTRunnerDaemonSession` / session error | WDA crashed | Restart Appium server and simulator |
| `Element not found` / timeout | Wrong locator | Dump `Get Source`, use Appium Inspector |
| Alert blocking test | System permission dialog | Add `Common - Handle Alert` after `Common - Open App` |
| Element visible but click fails | XCUITest interaction issue | Use `Common - Tap Center` workaround |
| `NoSuchSessionException` | Session dropped | Increase `newCommandTimeout=300` |
| `StaleElementReferenceException` | Stored element ref stale | Use locator string, not stored element |
| `401 Unauthorized` on farm | Wrong MCloud credentials | Re-check `FARM_USERNAME` / `FARM_ACCESS_KEY` env vars |
| `No device with udid <id>` on farm | Wrong or stale UDID | Get fresh UDID from MCloud web UI |
| Device busy on farm | Another session holds device | Choose a different `DEVICE_UDID` |
| Connection timeout to farm | VPN not connected | Connect to company VPN and retry |
| `ENV_MISSING: FARM_USERNAME` | Env vars not exported | `export FARM_USERNAME=xxx` before running |

---

## Appium Server

```bash
# Start Appium
appium

# Verify running
curl http://127.0.0.1:4723/status

# Custom port
appium --port 4724
```

Default URL: `http://127.0.0.1:4723`

---

## Simulator Not Found

```bash
# List all simulators and their states
xcrun simctl list devices

# Boot specific simulator
xcrun simctl boot "iPhone 15"

# Open Simulator app to see booted devices
open /Applications/Xcode.app/Contents/Developer/Applications/Simulator.app

# List available runtime versions
xcrun simctl list runtimes
```

Simulator must be in **Booted** state before running tests. The `deviceName` in capabilities must match exactly.

---

## WebDriverAgent (WDA) Fails to Start

WDA is the XCTest component Appium uses to drive iOS. First session startup can be slow (60–120s).

### Increase timeouts first

```robotframework
...    wdaLaunchTimeout=180000      # 3 minutes
...    wdaConnectionTimeout=300000  # 5 minutes
```

### Rebuild WDA manually

```bash
# Find WDA location
ls ~/.appium/node_modules/appium-xcuitest-driver/node_modules/appium-webdriveragent/

# Build for simulator
xcodebuild -project WebDriverAgent.xcodeproj \
  -scheme WebDriverAgentRunner \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  build

# Check build output for errors
```

### Kill stale WDA process

```bash
# Kill any WDA processes
pkill -f WebDriverAgentRunner
pkill -f XCTRunner
```

### Reset simulator state

```bash
xcrun simctl shutdown "iPhone 15"
xcrun simctl erase "iPhone 15"   # WARNING: clears all simulator data
xcrun simctl boot "iPhone 15"
```

---

## Real Device — Code Signing

```bash
# List valid signing identities
security find-identity -v -p codesigning

# Check Team ID (in Apple Developer account or Xcode)
# Xcode → Preferences → Accounts → Team details
```

```robotframework
# Capabilities for real device
...    udid=00008030-001234567890002E
...    xcodeOrgId=TEAMABC123
...    xcodeSigningId=iPhone Developer
```

Real device must have:
1. Developer Mode enabled: Settings → Privacy & Security → Developer Mode
2. Mac trusted on device (plug in, tap "Trust This Computer")
3. Valid provisioning profile with device UDID registered

---

## Finding `bundleId` of an Installed App (Real Device)

**Không dùng `xcrun devicectl device info apps`** để tra bundleId của app đã cài theo tên — đã tự xác nhận lỗi thật: lệnh này chỉ liệt kê app cài qua Xcode/MDM (dev-provisioned), **bỏ sót hoàn toàn app cài từ App Store** dù quét lại nhiều lần. Hệ quả: báo sai "không tìm thấy app" dù app rõ ràng đang có trên máy, phải hỏi lại user nhiều lượt để xác định đúng app.

Dùng `ideviceinstaller` thay thế — đọc thẳng database cài đặt của thiết bị (qua `libimobiledevice`), không phụ thuộc kênh cài (App Store, TestFlight, Xcode, ad-hoc):

```bash
# Cài nếu chưa có (idempotent)
which ideviceinstaller >/dev/null 2>&1 || brew install ideviceinstaller

# Liệt kê TOÀN BỘ app do user cài trên thiết bị — luôn bọc timeout, xem cảnh báo bên dưới
timeout 20 ideviceinstaller -u <udid> --list-apps -o list_user

# Lọc theo tên app (case-insensitive)
timeout 20 ideviceinstaller -u <udid> --list-apps -o list_user | grep -i "<tên app>"
```

> **Không phải `list --user`** (cú pháp subcommand) — bản `ideviceinstaller` chuẩn cài qua `brew install ideviceinstaller` dùng flag `-l`/`--list-apps` với option `-o list_user` (mặc định nếu không truyền `-o`). Chạy `ideviceinstaller -h` để xác nhận nếu nghi ngờ version khác.
>
> **Đã tự xác nhận thật:** bản `ideviceinstaller`/`libimobiledevice` cũ (vd 1.1.1, brew hiện có sẵn bản mới hơn 1.2.0) **treo vô hạn** khi chạy `--list-apps` với **iOS 17+** — log debug cho thấy lặp "initial read failed!" liên tục qua `installation_proxy`, không phải do trust/pairing (pairing vẫn valid, `ideviceinfo` vẫn trả nhanh bình thường). **Luôn bọc `timeout`**. Nếu timeout → chạy `brew upgrade ideviceinstaller libimobiledevice` để fix (có thể phải build từ source nếu không có bottle cho macOS đang dùng — có thể mất nhiều phút, chạy riêng ngoài phiên automation).

Output mỗi dòng gồm bundleId + tên hiển thị — khớp theo tên (gần đúng, không phân biệt hoa/thường) để lấy đúng `bundleId`. Chỉ hỏi lại user nếu app thực sự không xuất hiện trong danh sách này.

---

## Element Not Found

### Step 1: Dump view hierarchy

```robotframework
${source}=    Get Source
Log    ${source}    level=DEBUG
Create File    ${OUTPUT_DIR}/screen_source.xml    ${source}
```

### Step 2: Check screenshot

Read the failure screenshot PNG — shows exactly what was on screen when the error occurred.

### Step 3: Try alternative locators in priority order

```robotframework
# Try accessibility_id first
Wait Until Page Contains Element    accessibility_id=loginButton    timeout=5s

# Try name (accessibility label)
Wait Until Page Contains Element    name=Login    timeout=5s

# Try predicate
Wait Until Page Contains Element    ios=type == 'XCUIElementTypeButton' AND name == 'Login'    timeout=5s

# Try class chain
Wait Until Page Contains Element    ios=**/XCUIElementTypeButton[`name == 'Login'`]    timeout=5s

# Try xpath as last resort
Wait Until Page Contains Element    xpath=//XCUIElementTypeButton[@name='Login']    timeout=5s
```

### Step 4: Check if element is off-screen

If element exists in `Get Source` but `Wait Until Element Is Visible` times out → may be off-screen:

```robotframework
Common - Swipe Up To Element    ${your_locator}
```

### Step 5: Use Appium Inspector

Connect Appium Inspector to the running session for interactive element inspection.

---

## Alert Blocking Test

```robotframework
# Handle single alert in Open Screen keyword
Login - Open Screen
    Common - Open App
    Common - Handle Alert             # Allow (default)
    Common - Wait For Element Visible    ${inp_username}

# Handle multiple sequential alerts (e.g., location + notifications)
Onboarding - Handle All Alerts
    FOR    ${i}    IN RANGE    5
        ${present}=    Run Keyword And Return Status
        ...    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=${TIMEOUT_MIN}
        IF    not ${present}    BREAK
        Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[1]
    END
```

---

## Click Fails on Visible Element

XCUITest sometimes considers elements non-interactable even when visible (overlapped by transparent layer, animating).

```robotframework
# Option 1: Wait for any overlay to disappear
Wait Until Element Is Not Visible    ${icon_loading}    timeout=${TIMEOUT_MAX}
Common - Click Element    ${btn_confirm}

# Option 2: Tap center coordinates
Common - Tap Center    ${btn_confirm}

# Option 3: Use Execute Script mobile tap (nuclear option)
Execute Script    mobile: tap    {"element": null, "x": 200, "y": 400}
```

---

## Session Timeout

```robotframework
# Increase in capabilities
...    newCommandTimeout=600    # 10 minutes
```

Common cause: a test that runs too long between Appium commands (e.g., waiting for a slow animation without a proper wait keyword).

---

## Useful Debug Keywords

```robotframework
*** Keywords ***
Debug - Log Current Screen
    ${source}=    Get Source
    Log    ${source}    level=DEBUG
    Capture Page Screenshot    debug_${TEST_NAME}.png
    Create File    ${OUTPUT_DIR}/debug_source.xml    ${source}

Debug - Log Element Details
    [Arguments]    ${locator}
    ${text}=        Get Text                  ${locator}
    ${location}=    Get Element Location      ${locator}
    ${size}=        Get Element Size          ${locator}
    ${enabled}=     Get Element Attribute     ${locator}    enabled
    Log    text="${text}" | location=${location} | size=${size} | enabled=${enabled}    console=True
```
