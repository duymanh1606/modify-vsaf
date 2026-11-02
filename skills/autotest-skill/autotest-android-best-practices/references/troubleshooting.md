# Android Automation Troubleshooting

## Error Reference Table

| Error | Likely Cause | First Step |
|---|---|---|
| `Could not connect to Appium` | Appium server not running (local) | `appium` to start; `curl http://127.0.0.1:4723/status` to verify |
| `Device not found` | Device/emulator not connected (local) | `adb devices` to list; `adb kill-server && adb start-server` to restart |
| `Activity did not start` | Wrong `appActivity` | `adb shell dumpsys activity activities \| grep mCurrentFocus` |
| `UiAutomator2 server did not start` | Install timeout or stale server | Uninstall UIA2 server (see below), retry |
| `Element not found` / timeout | Wrong locator | `Get Source` to dump view hierarchy |
| Permission dialog blocking test | `autoGrantPermissions=True` not set | Add capability, or add `Common - Handle Permission Dialog` |
| Element visible but click fails | Element partially obscured | Use `Common - Tap Center` workaround |
| `NoSuchSessionException` | Session dropped | Increase `newCommandTimeout=300` |
| `StaleElementReferenceException` | Element reference stale | Use locator string instead of stored element ref |
| `401 Unauthorized` (device farm) | Wrong MCloud credentials | Re-check `FARM_USERNAME` / `FARM_ACCESS_KEY` env vars |
| `No device with udid <id>` (device farm) | Wrong or stale UDID | Get fresh UDID from MCloud web UI |
| Device busy on farm | Another session holds device | Choose a different `DEVICE_UDID` |
| Connection timeout to farm | VPN not connected | Connect to company VPN and retry |
| `ENV_MISSING: FARM_USERNAME` | Env vars not exported | `export FARM_USERNAME=xxx` before running robot |

---

## Appium Server

### Server not running

```bash
# Start Appium
appium

# Verify it's running
curl http://127.0.0.1:4723/status

# Custom port
appium --port 4724
```

Default URL: `http://127.0.0.1:4723` (Appium 2.x).
Legacy URL (Appium 1.x): `http://127.0.0.1:4723/wd/hub`.

---

## Device / Emulator Not Found

```bash
# List all connected devices and emulators
adb devices

# If device not listed — restart ADB
adb kill-server
adb start-server
adb devices

# List available AVDs (emulators)
emulator -list-avds

# Start a specific emulator
emulator -avd Pixel_6_API_33
```

Real device: enable USB debugging in Developer Options and accept the authorization prompt on the device.

---

## Element Not Found

### Step 1: Dump view hierarchy

```robotframework
${source}=    Get Source
Log    ${source}    level=DEBUG
Create File    ${OUTPUT_DIR}/screen_source.xml    ${source}
```

### Step 2: Check screenshot

Read the failure screenshot PNG — it shows exactly what was on screen when the error occurred.

### Step 3: Try alternative locators in order

```robotframework
# Try accessibility_id first
Wait Until Page Contains Element    accessibility_id=<element_name>    timeout=5s

# Try resource-id
Wait Until Page Contains Element    id=com.example.app:id/<element_id>    timeout=5s

# Try UIAutomator2 text
Wait Until Page Contains Element    android=new UiSelector().text("<visible text>")    timeout=5s

# Try xpath as last resort
Wait Until Page Contains Element    xpath=//android.widget.Button[@text='<text>']    timeout=5s
```

### Step 4: Check if element is off-screen

If the element exists in `Get Source` but `Wait Until Element Is Visible` times out → the element may be off-screen:

```robotframework
Common - Swipe Up To Element    ${your_locator}
```

---

## UIAutomator2 Server Install Errors

```bash
# Uninstall stale UIA2 server packages
adb uninstall io.appium.uiautomator2.server
adb uninstall io.appium.uiautomator2.server.test

# Then retry the test — Appium will reinstall them fresh
```

To increase install timeout in capabilities:
```robotframework
Open Application    ${APPIUM_URL}
...    uiautomator2ServerInstallTimeout=120000    # 2 minutes
...    # other capabilities
```

---

## Activity Not Starting

```bash
# Find the correct activity name
adb shell dumpsys package com.example.app | grep -i activity

# While app is open
adb shell dumpsys activity activities | grep "mCurrentFocus"
```

For apps with splash screens, set `appWaitActivity`:
```robotframework
Open Application    ${APPIUM_URL}
...    appPackage=com.example.app
...    appActivity=com.example.app.SplashActivity
...    appWaitActivity=com.example.app.MainActivity
```

---

## Permission Dialogs Blocking Tests

Option 1 — Auto-grant at session start (recommended):
```robotframework
# In Common - Open App capability
...    autoGrantPermissions=${TRUE}
```

Option 2 — Handle manually after Open App:
```robotframework
Login - Open Screen
    Common - Open App
    Common - Handle Permission Dialog    # handles single permission
    Common - Wait For Element Visible    ${inp_username}
```

Option 3 — Multiple permissions (loop):
```robotframework
Login - Open Screen
    Common - Open App
    FOR    ${i}    IN RANGE    5
        Common - Handle Permission Dialog
    END
    Common - Wait For Element Visible    ${inp_username}
```

---

## Session Timeout

```robotframework
# Increase session timeout in Common - Open App capabilities
...    newCommandTimeout=600    # 10 minutes (seconds)
```

---

## Element Visible but Click Fails

If `Common - Click Element` fails because the element is covered by an overlay (e.g., loading spinner fading out):

```robotframework
# Wait for overlay to disappear first
Wait Until Element Is Not Visible    ${icon_loading}    timeout=${TIMEOUT_MAX}
Common - Click Element    ${btn_confirm}
```

If the element is partially off-screen:
```robotframework
Common - Swipe Up To Element    ${btn_confirm}
Common - Click Element    ${btn_confirm}
```

If `Click Element` fails but element is clearly visible → use center-tap workaround (see gestures.md `Common - Tap Center`).

---

## Debugging — Useful Patterns

```robotframework
*** Keywords ***
Debug - Log Current Screen
    ${source}=    Get Source
    Log    ${source}    level=DEBUG
    Capture Page Screenshot    debug_${TEST NAME}.png
    Create File    ${OUTPUT_DIR}/debug_source.xml    ${source}

Debug - Log Element Details
    [Arguments]    ${locator}
    ${text}=        Get Text    ${locator}
    ${location}=    Get Element Location    ${locator}
    ${size}=        Get Element Size    ${locator}
    Log    Text: ${text} | Location: ${location} | Size: ${size}    console=True
```