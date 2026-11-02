# Android-Specific Features Reference

## Hardware Keys — `Press Keycode`

Use `Common - Press Back` (wraps `Press Keycode 4`) for hardware back button. Use raw `Press Keycode` for other keys.

```robotframework
# Via Common wrapper (preferred for back)
Common - Press Back    # Press Keycode 4 — Android hardware back

# Raw Press Keycode for other hardware buttons
Press Keycode    3     # HOME
Press Keycode    66    # ENTER / Return
Press Keycode    82    # MENU
Press Keycode    187   # APP_SWITCH (recent apps)
Press Keycode    24    # VOLUME_UP
Press Keycode    25    # VOLUME_DOWN
Press Keycode    84    # SEARCH
Press Keycode    67    # DELETE (backspace)
```

**Rule**: Always use `Common - Press Back` for back navigation. Use raw `Press Keycode` for other hardware keys only.

---

## Handling Android Permission Dialogs

### Auto-grant (capability — set at test startup)

In `common_variables.resource` / `Common - Open App`:
```robotframework
...    autoGrantPermissions=${TRUE}
```

Auto-grant silently approves all permissions before the app starts. Use this when tests don't need to verify permission dialog behavior.

### Manual handling with `Common - Handle Permission Dialog`

```robotframework
# In the feature's Open Screen keyword
Login - Open Screen
    Common - Open App
    Common - Handle Permission Dialog    # handles Android 11+ permission dialog
    Common - Wait For Element Visible    ${inp_username}
```

`Common - Handle Permission Dialog` handles the standard Android permission controller dialog. For apps with multiple permission dialogs, call it multiple times or loop:

```robotframework
Login - Open Screen
    Common - Open App
    FOR    ${i}    IN RANGE    5
        Common - Handle Permission Dialog
    END
    Common - Wait For Element Visible    ${inp_username}
```

### Custom permission dialogs

Some apps use custom permission dialogs (not system dialogs). Find and handle them by locator:

```robotframework
Login - Grant Camera Permission
    ${present}=    Run Keyword And Return Status
    ...    Wait Until Page Contains Element    accessibility_id=allow_camera_btn    timeout=${TIMEOUT_MIN}
    IF    ${present}
        Common - Click Element    accessibility_id=allow_camera_btn
    END
```

---

## Activity Management

### Launch Installed App

```robotframework
# common_variables.resource — use appPackage + appActivity (no `app` path needed)
${APP_PACKAGE}      com.example.app
${APP_ACTIVITY}     com.example.app.MainActivity
```

### Find appActivity for an app

```bash
# Method 1: adb dumpsys
adb shell dumpsys package com.example.app | grep -i activity

# Method 2: while app is running
adb shell dumpsys activity activities | grep "mCurrentFocus"

# Method 3: logcat during launch
adb logcat | grep "START"
```

### `appWaitActivity` for apps with splash screens

```robotframework
# App has a splash screen that transitions to the main screen
Open Application    ${APPIUM_URL}
...    appPackage=${APP_PACKAGE}
...    appActivity=com.example.app.SplashActivity
...    appWaitActivity=com.example.app.MainActivity
```

### Navigate to a specific activity

```robotframework
# Skip to a specific screen by starting its activity directly
Start Activity    com.example.app    com.example.app.SettingsActivity
Common - Wait For Element Visible    ${lbl_settings_heading}
```

---

## App State Management

```robotframework
# Background the app for N seconds (tests multitasking behavior)
Background Application    5

# Check if app is running
${state}=    Query App State    com.example.app
# 0=NOT_INSTALLED, 1=NOT_RUNNING, 3=RUNNING_IN_BACKGROUND, 4=RUNNING_IN_FOREGROUND
Should Be Equal As Integers    ${state}    4

# Terminate app (keeps Appium session active)
Terminate App    com.example.app

# Bring app back to foreground
Activate App    com.example.app
```

---

## `noReset` vs `fullReset`

| Capability | Effect | Use when |
|---|---|---|
| `noReset=True` (default) | Keeps app data between sessions; app re-launches but retains login state | Testing flows that require prior state (e.g., logged in) |
| `noReset=False` | Clears app data on session start | Testing fresh-install or login screen behavior |
| `fullReset=True` | Uninstalls and reinstalls app | Testing install/onboarding flows |

**Rule**: Use `noReset=True` (default) for most tests. Set `noReset=False` on `Common - Open App` call for TCs that require a clean state:

```robotframework
Login - Open Screen With Clean State
    Common - Open App    no_reset=${FALSE}    # override for fresh-install TCs
    Common - Wait For Element Visible    ${inp_username}
```

---

## Notifications

```robotframework
# Open notification shade
Open Notifications

# Interact with a notification
Common - Click Element    xpath=//android.widget.TextView[contains(@text,'Your notification')]

# Close notification shade
Common - Press Back
```

---

## Screen Orientation

```robotframework
# Get current orientation
${orientation}=    Get Appium Attribute    orientation
Log    Orientation: ${orientation}    # PORTRAIT or LANDSCAPE

# Set orientation
Set Orientation    LANDSCAPE
Set Orientation    PORTRAIT
```

---

## adb Commands for Debugging

```bash
# List connected devices and emulators
adb devices

# Get current screen
adb exec-out screencap -p > screenshot.png

# Get view hierarchy
adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml .

# Get current package and activity
adb shell dumpsys activity activities | grep "mCurrentFocus"

# Restart ADB when device not found
adb kill-server && adb start-server

# Install APK manually
adb install app.apk

# Check Android version on device
adb shell getprop ro.build.version.release
```