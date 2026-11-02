# iOS Appium Capabilities Reference

## Required Capabilities (Minimal)

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=iOS
...    automationName=XCUITest
...    deviceName=iPhone 15
...    bundleId=com.example.app        # launch installed app
```

---

## Full Capabilities Table

| Capability | Required | Description | Example |
|---|---|---|---|
| `platformName` | Yes | Always `iOS` | `iOS` |
| `automationName` | Yes | Always `XCUITest` | `XCUITest` |
| `deviceName` | Yes | Simulator/device name | `iPhone 15`, `My iPhone` |
| `bundleId` | Yes* | App bundle ID | `com.example.app` |
| `app` | Yes* | Absolute path to `.app` or `.ipa` | `/abs/path/to/App.app` |
| `platformVersion` | No | iOS version | `17.0`, `16.4` |
| `udid` | No | Device UDID (real device / specific simulator) | `00008030-001234567890002E` |
| `noReset` | No | Keep app data between sessions | `${TRUE}` |
| `fullReset` | No | Uninstall app before session | `${TRUE}` |
| `autoAcceptAlerts` | No | Auto-accept all system alerts | `${FALSE}` (recommended: handle manually) |
| `autoDismissAlerts` | No | Auto-dismiss all system alerts | `${FALSE}` |
| `newCommandTimeout` | No | Session inactivity timeout (seconds) | `300` |
| `wdaLaunchTimeout` | No | WebDriverAgent startup timeout (ms) | `120000` |
| `wdaConnectionTimeout` | No | WDA connection timeout (ms) | `240000` |
| `xcodeOrgId` | No* | Xcode Team ID (real device) | `TEAMABC123` |
| `xcodeSigningId` | No* | Signing identity (real device) | `iPhone Developer` |
| `webviewConnectTimeout` | No | Hybrid webview connection timeout (ms) | `90000` |

*Either `bundleId` OR `app` required. `xcodeOrgId`/`xcodeSigningId` required for real devices.

---

## `common_variables.resource` Template

```robotframework
*** Variables ***
${TIMEOUT_MIN}          5s
${TIMEOUT_DEFAULT}      15s
${TIMEOUT_MAX}          30s

# --- Execution target: local | device_farm ---
${EXECUTION_TARGET}     local

# --- Local simulator/device ---
${APPIUM_URL}           http://127.0.0.1:4723
${DEVICE_NAME}          iPhone 15
${PLATFORM_VERSION}     17.0
${BUNDLE_ID}            com.example.app
${APP_PATH}             ${EMPTY}    # leave empty to use bundleId (launch installed app)
${NO_RESET}             ${TRUE}

# --- Shared ---
${DEVICE_UDID}          ${EMPTY}    # optional for simulator; required for real device / farm

# --- MCloud Device Farm ---
${FARM_HOST}            10.207.247.201
${FARM_PATH}            /mcloud/wd/hub
# Credentials: set FARM_USERNAME and FARM_ACCESS_KEY as environment variables
```

Fill app-specific values from `global-data.md`. Never hardcode credential or UDID values.

---

## Simulator Setup

```robotframework
# Launch by bundleId (app must be pre-installed in simulator)
${caps}=    Create Dictionary
...    platformName=iOS
...    platformVersion=17.0
...    deviceName=iPhone 15
...    automationName=XCUITest
...    bundleId=com.example.app
...    autoAcceptAlerts=${FALSE}
...    noReset=${TRUE}
...    newCommandTimeout=300
...    wdaLaunchTimeout=120000
...    wdaConnectionTimeout=240000
Open Application    http://127.0.0.1:4723    &{caps}
```

```bash
# List available simulators
xcrun simctl list devices

# Boot a simulator (if not running)
xcrun simctl boot "iPhone 15"

# Install app into simulator
xcrun simctl install booted /path/to/App.app

# Get simulator UDID
xcrun simctl list devices | grep "iPhone 15"
```

---

## Real Device Setup

```robotframework
# Real device requires UDID + signing
${caps}=    Create Dictionary
...    platformName=iOS
...    platformVersion=17.0
...    deviceName=My iPhone
...    automationName=XCUITest
...    udid=00008030-001234567890002E
...    bundleId=com.example.app
...    xcodeOrgId=TEAMABC123
...    xcodeSigningId=iPhone Developer
...    autoAcceptAlerts=${FALSE}
...    noReset=${TRUE}
...    newCommandTimeout=300
...    wdaLaunchTimeout=180000
...    wdaConnectionTimeout=300000
Open Application    http://127.0.0.1:4723    &{caps}
```

```bash
# Get device UDID
xcrun xctrace list devices

# Or: Finder → select device → click device name to show UDID
```

For real devices: enable Developer Mode on device (Settings → Privacy → Developer Mode), trust the Mac.

---

## Install Fresh App vs Launch Installed

```robotframework
# Launch already-installed app (fast — no reinstall)
${caps}=    Create Dictionary
...    bundleId=com.example.app
...    noReset=${TRUE}
# Leave out 'app' key entirely

# Install fresh .app file (simulator)
${caps}=    Create Dictionary
...    app=/abs/path/to/MyApp.app
...    noReset=${FALSE}
# Leave out 'bundleId' or it will conflict
```

`Common - Open App Local` handles this automatically:
- If `${APP_PATH}` is set → switches to `app=` and removes `bundleId`
- If `${APP_PATH}` is empty → uses `bundleId` only

---

## `noReset` vs `fullReset`

| Mode | Effect |
|---|---|
| `noReset=${TRUE}` | Don't reset app state. Fastest — session reuses existing app data |
| `noReset=${FALSE}` (default) | Reset app state but keep app installed |
| `fullReset=${TRUE}` | Uninstall app before session, reinstall from `app=` path |

For test isolation: use `noReset=True` if tests handle their own state (login → logout). Use `noReset=False` or `fullReset=True` for clean-state tests.

---

## WDA Timeouts (iOS Only)

WebDriverAgent (WDA) is Apple's XCTest wrapper that Appium uses. It must build and launch before test execution.

```robotframework
# For simulator (faster build)
...    wdaLaunchTimeout=120000      # 2 minutes
...    wdaConnectionTimeout=240000  # 4 minutes

# For real device (slower — first build takes longer)
...    wdaLaunchTimeout=180000      # 3 minutes
...    wdaConnectionTimeout=300000  # 5 minutes
```

If WDA fails to start within the timeout: rebuild manually (see `troubleshooting.md`).
