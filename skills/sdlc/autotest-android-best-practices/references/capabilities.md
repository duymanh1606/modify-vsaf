# Android Appium Capabilities Reference

## Minimal Required Capabilities

```robotframework
Open Application    http://127.0.0.1:4723
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=emulator-5554
...    appPackage=com.example.app        # use appPackage+appActivity for installed apps
...    appActivity=com.example.app.MainActivity
```

---

## Full Capabilities Table

| Capability | Required | Description | Example |
|---|---|---|---|
| `platformName` | Yes | Always `Android` | `Android` |
| `automationName` | Yes | Always `UiAutomator2` | `UiAutomator2` |
| `deviceName` | Yes | Device or emulator | `emulator-5554`, `R3CR80XXXXX` |
| `appPackage` | Yes* | App package name | `com.example.app` |
| `appActivity` | Yes* | Main activity | `com.example.app.MainActivity` |
| `app` | Yes* | Path to APK | `/path/to/app.apk` |
| `platformVersion` | No | Android version string | `13`, `14` |
| `udid` | No | Device serial (real device) | `R3CR80XXXXX` |
| `noReset` | No | Keep app data | `True` |
| `fullReset` | No | Uninstall before session | `True` |
| `autoGrantPermissions` | No | Auto-grant all permissions | `True` |
| `appWaitActivity` | No | Activity to wait for after launch | `.SplashActivity` |
| `avd` | No | AVD name to auto-launch | `Pixel_6_API_33` |
| `newCommandTimeout` | No | Seconds before session timeout | `300` |
| `uiautomator2ServerInstallTimeout` | No | ms to wait for UIA2 install | `120000` |

*Either `app` OR both `appPackage`+`appActivity` required.

---

## Emulator vs Real Device

### Emulator

```robotframework
# Already running emulator
Open Application    ${APPIUM_URL}
...    platformName=Android
...    platformVersion=13
...    deviceName=emulator-5554          # from `adb devices` output
...    automationName=UiAutomator2
...    appPackage=${APP_PACKAGE}
...    appActivity=${APP_ACTIVITY}
...    autoGrantPermissions=${TRUE}
...    noReset=${TRUE}
...    newCommandTimeout=300

# Auto-launch specific AVD
Open Application    ${APPIUM_URL}
...    platformName=Android
...    deviceName=emulator-5554
...    automationName=UiAutomator2
...    appPackage=${APP_PACKAGE}
...    appActivity=${APP_ACTIVITY}
...    avd=Pixel_6_API_33
...    avdLaunchTimeout=120000
```

### Real Device

```robotframework
Open Application    ${APPIUM_URL}
...    platformName=Android
...    platformVersion=13
...    deviceName=Samsung Galaxy S23     # friendly name
...    udid=R3CR80XXXXX                  # `adb get-serialno` or `adb devices`
...    automationName=UiAutomator2
...    appPackage=${APP_PACKAGE}
...    appActivity=${APP_ACTIVITY}
...    autoGrantPermissions=${TRUE}
...    noReset=${TRUE}
...    newCommandTimeout=300
```

---

## Install Fresh APK vs Launch Installed App

```robotframework
# Install fresh APK (always reinstalls)
Open Application    ${APPIUM_URL}
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=${DEVICE_NAME}
...    app=/absolute/path/to/app.apk     # absolute path required
...    noReset=${FALSE}                  # clean install

# Launch already-installed app (faster — no install step)
Open Application    ${APPIUM_URL}
...    platformName=Android
...    automationName=UiAutomator2
...    deviceName=${DEVICE_NAME}
...    appPackage=${APP_PACKAGE}
...    appActivity=${APP_ACTIVITY}
...    noReset=${TRUE}
```

For CI pipelines, use `app=` with `noReset=False` to always test a fresh install. For local development, use `appPackage`+`appActivity` with `noReset=True` for faster session startup.

---

## `common_variables.resource` Template

```robotframework
*** Variables ***
${TIMEOUT_MIN}          5s
${TIMEOUT_DEFAULT}      15s
${TIMEOUT_MAX}          30s

# --- Execution target: local | device_farm ---
${EXECUTION_TARGET}     local

# --- Local device ---
${APPIUM_URL}           http://127.0.0.1:4723
${DEVICE_NAME}          emulator-5554
${PLATFORM_VERSION}     13
${APP_PACKAGE}          com.example.app
${APP_ACTIVITY}         com.example.app.MainActivity
${NO_RESET}             ${TRUE}

# --- Shared ---
${DEVICE_UDID}          ${EMPTY}

# --- MCloud Device Farm ---
${FARM_HOST}            10.207.247.201
${FARM_PATH}            /mcloud/wd/hub
# Credentials via env vars: FARM_USERNAME, FARM_ACCESS_KEY
```

Fill app-specific values from `global-data.md`. Never hardcode capability values inline in `Open Application` or credentials in any file. See `device-farm.md` for MCloud setup details.

---

## Finding Device Information

```bash
# List all connected devices and emulators
adb devices

# Get device serial number (for udid)
adb get-serialno

# Get Android version
adb shell getprop ro.build.version.release

# Get app package and activity while app is open
adb shell dumpsys activity activities | grep "mCurrentFocus"

# List all activities of an app
adb shell dumpsys package com.example.app | grep -i "activity"

# List available emulators
emulator -list-avds
```

---

## W3C Capability Format (Appium 2.x)

Appium 2.x uses W3C capabilities. Non-standard capabilities need the `appium:` prefix. AppiumLibrary typically adds this automatically, but explicit usage avoids surprises:

```robotframework
Open Application    ${APPIUM_URL}
...    platformName=Android
...    appium:automationName=UiAutomator2
...    appium:deviceName=${DEVICE_NAME}
...    appium:appPackage=${APP_PACKAGE}
...    appium:appActivity=${APP_ACTIVITY}
...    appium:autoGrantPermissions=${TRUE}
...    appium:noReset=${TRUE}
...    appium:newCommandTimeout=300
```

`platformName` is standard W3C — no prefix needed.