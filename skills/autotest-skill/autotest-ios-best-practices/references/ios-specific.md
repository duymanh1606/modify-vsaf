# iOS-Specific Patterns Reference

## Alert & Permission Handling

### `Common - Handle Alert` (Standard Wrapper)

```robotframework
# In feature keyword — after Open App, before waiting for first screen element
Login - Open Screen
    Common - Open App
    Common - Handle Alert             # default: taps "Allow"
    Common - Wait For Element Visible    ${inp_username}

# Custom button name
Settings - Enable Camera
    Common - Click Element    ${btn_camera_access}
    Common - Handle Alert     While Using App

# Multiple sequential alerts
Onboarding - Complete Permissions
    Common - Handle Alert    Allow
    Common - Handle Alert    Allow While Using App
    Common - Handle Alert    OK
```

`Common - Handle Alert` is a no-op if no alert is present — safe to call preemptively.

### Manual Alert Handling

```robotframework
# Accept alert by exact button name
Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == 'Allow'`]

# Dismiss alert
Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == 'Cancel'`]
Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == "Don't Allow"`]

# Get alert message text
${alert_text}=    Get Text    class=XCUIElementTypeAlert

# Loop to handle multiple permission dialogs
*** Keywords ***
Handle All Permission Alerts
    FOR    ${i}    IN RANGE    5
        ${present}=    Run Keyword And Return Status
        ...    Wait Until Page Contains Element    class=XCUIElementTypeAlert    timeout=${TIMEOUT_MIN}
        IF    not ${present}    BREAK
        Click Element    ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[1]
    END
```

---

## Navigation Bar

```robotframework
# Tap navigation back (first button = back button by convention)
Common - Tap Navigation Back

# Tap named button in navigation bar
Common - Click Element    ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[`name == 'Done'`]
Common - Click Element    ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[`name == 'Cancel'`]

# Get navigation title text
${title}=    Common - Get Text    ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeStaticText[1]
```

---

## Tab Bar

```robotframework
# By accessibility_id (preferred — developer sets accessibilityIdentifier)
Common - Click Element    ${tab_home}             # ${tab_home} = accessibility_id=homeTab

# By class chain
Common - Click Element    ios=**/XCUIElementTypeTabBar/XCUIElementTypeButton[`name == 'Home'`]

# By index
Common - Click Element    ios=**/XCUIElementTypeTabBar/XCUIElementTypeButton[1]
```

---

## Table / List Navigation

```robotframework
# Select cell by name contains
Common - Click Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${item_name}'`]

# Select cell by index
Common - Click Element    ios=**/XCUIElementTypeTable/XCUIElementTypeCell[1]

# Scroll to find cell (preferred pattern)
Common - Swipe Up To Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${item_name}'`]
Common - Click Element          ios=**/XCUIElementTypeCell[`name CONTAINS '${item_name}'`]

# Get all visible cells
@{cells}=    Get WebElements    class=XCUIElementTypeCell
FOR    ${cell}    IN    @{cells}
    ${text}=    Get Text    ${cell}
    Log    ${text}
END
```

---

## Picker Wheel

```robotframework
*** Keywords ***
Form - Select Country
    [Arguments]    ${country}
    Common - Click Element    ${btn_country_picker}
    Common - Wait For Element Visible    class=XCUIElementTypePicker
    ${wheel}=    Get WebElement    class=XCUIElementTypePickerWheel
    Input Text    ${wheel}    ${country}
    Common - Click Element    accessibility_id=Done

Form - Select Date Of Birth
    [Arguments]    ${month}    ${day}    ${year}
    Common - Click Element    ${btn_dob_picker}
    Common - Wait For Element Visible    xpath=//XCUIElementTypeDatePicker
    @{wheels}=    Get WebElements    class=XCUIElementTypePickerWheel
    Input Text    ${wheels}[0]    ${month}
    Input Text    ${wheels}[1]    ${day}
    Input Text    ${wheels}[2]    ${year}
    Common - Click Element    ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[`name == 'Done'`]
```

---

## Keyboard Handling

```robotframework
*** Keywords ***
Search - Enter Query
    [Arguments]    ${query}
    Common - Click Element    ${inp_search}
    Common - Wait For Element Visible    class=XCUIElementTypeKeyboard
    Common - Input Text    ${inp_search}    ${query}
    # Tap Return/Search key
    Run Keyword And Ignore Error
    ...    Click Element    ios=**/XCUIElementTypeKey[`name == 'Search'`]
    Run Keyword And Ignore Error
    ...    Click Element    ios=**/XCUIElementTypeKey[`name == 'Return'`]

Form - Dismiss Keyboard
    Run Keyword And Ignore Error    Click Element    ios=**/XCUIElementTypeButton[`name == 'Done'`]
    Run Keyword And Ignore Error    Click Element    ios=**/XCUIElementTypeKey[`name == 'Done'`]
    Run Keyword And Ignore Error    Hide Keyboard
```

---

## Switch / Toggle

```robotframework
# Tap to toggle
Common - Click Element    ${sw_notifications}    # accessibility_id=notificationsSwitch

# Get current state (value: "0" = off, "1" = on)
${state}=    Get Element Attribute    ${sw_notifications}    value
Should Be Equal    ${state}    1    # assert on

# Toggle only if currently off
${value}=    Get Element Attribute    ${sw_notifications}    value
IF    '${value}' == '0'
    Common - Click Element    ${sw_notifications}
END
```

---

## Checking Element State

```robotframework
# Is element enabled?
${enabled}=    Get Element Attribute    ${btn_submit}    enabled
Should Be Equal    ${enabled}    true

# Is element selected?
${selected}=    Get Element Attribute    ${btn_tab}    selected
Should Be Equal    ${selected}    true

# Get value (works on TextField, Switch, Slider)
${value}=    Get Element Attribute    ${inp_username}    value
Should Be Equal    ${value}    testuser@example.com
```

---

## Swipe Gesture on iOS

`Swipe By Percent` is preferred over absolute coordinates — works on any screen size.

```robotframework
# Swipe UP (finger bottom → top, reveals content below)
Swipe By Percent    50    80    50    20    800

# Swipe DOWN (finger top → bottom, reveals content above)
Swipe By Percent    50    20    50    80    800

# Swipe LEFT (next page/carousel item)
Swipe By Percent    80    50    20    50    500

# Swipe RIGHT (previous page/carousel item)
Swipe By Percent    20    50    80    50    500

# Pull to refresh (slow swipe down from top edge)
Swipe By Percent    50    15    50    70    1200
```

Duration in ms: slower swipe (800–1200ms) gives iOS more time to register the gesture correctly.

---

## Device Orientation

```robotframework
# Set orientation
Set Orientation    LANDSCAPE
Set Orientation    PORTRAIT

# Get current
${orientation}=    Get Appium Attribute    orientation
```

---

## Biometric (Simulator Only)

```robotframework
# Requires capability: allowTouchIdEnroll=True

# Simulate successful Face ID
Execute Script    mobile: sendBiometricMatch    {"type": "faceId", "match": true}

# Simulate failed Face ID
Execute Script    mobile: sendBiometricMatch    {"type": "faceId", "match": false}

# Touch ID
Execute Script    mobile: sendBiometricMatch    {"type": "touchId", "match": true}
```

Only works on iOS Simulator — not on real devices.

---

## Debugging

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
    Log    text="${text}" location=${location} size=${size} enabled=${enabled}    console=True
```

---

## `bundleId` vs `app=` Path

| When | Use | Effect |
|---|---|---|
| App already installed on simulator/device | `bundleId=com.example.app` | Fast session start, preserves data |
| Installing fresh build (.app file) | `app=/abs/path/to/App.app` | Reinstalls app before session |
| Real device with IPA | `app=/abs/path/to/App.ipa` + signing caps | Fresh install |

In `common_variables.resource`:
```robotframework
${BUNDLE_ID}    com.example.app
${APP_PATH}     ${EMPTY}    # set to absolute path only when fresh install needed
```

`Common - Open App Local` uses `bundleId` by default; switches to `app=` automatically if `${APP_PATH}` is set.

---

## Real Device Extra Capabilities

For real physical devices, add to `Common - Open App Local` or pass via `-v`:

```robotframework
# In common_variables.resource
${XCODE_ORG_ID}        TEAM1234ABC
${XCODE_SIGNING_ID}    iPhone Developer
```

```robotframework
# In Common - Open App Local, inside ${caps} dict
IF    '${DEVICE_UDID}' != '${EMPTY}'
    Set To Dictionary    ${caps}    udid=${DEVICE_UDID}
    Set To Dictionary    ${caps}    xcodeOrgId=${XCODE_ORG_ID}
    Set To Dictionary    ${caps}    xcodeSigningId=${XCODE_SIGNING_ID}
END
```

Get UDID: Finder → device → summary; or `xcrun xctrace list devices`.
