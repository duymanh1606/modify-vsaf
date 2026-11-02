---
name: autotest-ios-best-practices
description: Robot Framework iOS (AppiumLibrary + XCUITest) test automation standards — locator strategy, FOM structure, common wrappers, alert handling, wait strategies, gesture patterns, and anti-patterns. Use when writing, reviewing, or debugging RF iOS tests.
user-invocable: false
---

# Robot Framework iOS Test Automation Best Practices

## Overview

This document defines the testing standards, patterns, and best practices for writing E2E tests using Robot Framework with AppiumLibrary on iOS (XCUITest driver). All agents and code reviewers MUST follow these guidelines. They supersede anything else if there is a conflict.

## When to Load Additional References

For deep troubleshooting or edge cases, read the relevant file in `.claude/skills/autotest-ios-best-practices/references/`:

| Situation | Reference file |
|---|---|
| iOS locator strategies, predicate string, class chain | `locators.md` |
| XCUITest element types, alerts, picker, keyboard, biometric | `ios-specific.md` |
| Swipe, scroll, long press, drag-and-drop | `gestures.md` |
| Appium server, simulator/device not found, WDA errors | `troubleshooting.md` |
| Capabilities, simulator vs real device, signing setup | `capabilities.md` |
| MCloud device farm setup, UDID, parallel runs | `device-farm.md` |

Example files are in `.claude/skills/autotest-ios-best-practices/examples/`.

---

## 1. Project Test Setup

### Documentation & Commenting Standards

- **Max 1–2 sentences** per `[Documentation]` block. Focus on *why*, not *how*.
- **Inline comments**: only when the *why* is non-obvious. Under 10 words. No "tap the button" comments.

### Config Reference

- **Test directory**: `./tests` — `.robot` suites only
- **Features directory**: `./features` — keywords & variables per feature
- **Common directory**: `./common` — shared wrappers and global variables
- **Config directory**: `./config` — `imports.resource` (libraries + keyword files only)
- **Data directory**: `./data` — YAML test data, one file per feature
- **Results directory**: `./results` — robot output (gitignored)
- **Appium server URL**: defined in `global-data.md` (default `http://127.0.0.1:4723`)
- **Device config**: `bundleId`, `deviceName`, `platformVersion`, `deviceUDID` — stored in `common_variables.resource`, values sourced from `global-data.md`
- **Timeouts**: `${TIMEOUT_MIN}=5s`, `${TIMEOUT_DEFAULT}=15s`, `${TIMEOUT_MAX}=30s` — XCUITest is inherently slower than web; always use explicit waits
- **Screenshots**: `AppiumLibrary` captures automatically on any keyword failure via `run_on_failure=Capture Page Screenshot` (default). Do NOT add screenshot calls in `Test Teardown` or test steps.

### Naming Conventions

#### File Naming — `underscore_case` Only

All `.robot` and `.resource` files MUST use lowercase `underscore_case`.

| File type | Convention | Example |
|---|---|---|
| Test suite | `<feature>.robot` | `login.robot`, `profile.robot` |
| Keyword resource | `<feature>_keywords.resource` | `login_keywords.resource` |
| Variables resource | `<feature>_variables.resource` | `login_variables.resource` |
| Common keywords | `common_keywords.resource` | `common_keywords.resource` |
| Common variables | `common_variables.resource` | `common_variables.resource` |
| Test data | `<feature>.yaml` | `login.yaml`, `profile.yaml` |

#### Test Case Names
`Snake_Case_With_Capitalization` — e.g., `User_Can_Login_With_Valid_Credentials`

#### Keyword Names — `<Noun> - <Verb> <Object>`

The prefix MUST be a noun (module/feature name). Never a verb.

```
Login - Fill Credentials         ✅
Profile - Select Avatar          ✅
Common - Click Element           ✅
Do Login - Fill Form             ❌  verb prefix
Handle Profile - Select          ❌  verb prefix
```

The entire keyword name uses **spaces only** — never underscores in any part (prefix or action):

```
Product Listing Page By Category - Dismiss Welcome Modal   ✅  spaces throughout
Product Listing Page By Category - Dismiss_Welcome_Modal   ❌  underscore in action — wrong
Auth - Login_With_Credentials                              ❌  underscore in action — wrong
```

#### Variable Names — Type Prefix Required

| Prefix | Element type | Example |
|---|---|---|
| `btn_` | Button (`XCUIElementTypeButton`) | `${btn_login}`, `${btn_confirm}` |
| `inp_` | TextField / SecureTextField | `${inp_username}`, `${inp_password}` |
| `lbl_` | StaticText label | `${lbl_balance}`, `${lbl_error}` |
| `txt_` | Expected text string value | `${txt_success}`, `${txt_welcome}` |
| `icon_` | Image / icon | `${icon_loading}`, `${icon_avatar}` |
| `sw_` | Switch (XCUIElementTypeSwitch) | `${sw_notifications}` |
| `tab_` | Tab bar item | `${tab_home}`, `${tab_profile}` |
| `cell_` | Table cell (XCUIElementTypeCell) | `${cell_settings_row}` |
| `nav_` | Navigation bar element | `${nav_btn_back}`, `${nav_title}` |

### Formatting — `robotframework-tidy`

Always format `.robot` and `.resource` files after every write, before running, before committing.

```bash
pip install robotframework-tidy    # one-time install

python -m robotidy automation_test/features/login/
python -m robotidy automation_test/tests/login.robot
python -m robotidy automation_test/features/          # entire directory
```

---

## 2. Locator Strategy (Priority Order)

Always choose locators in this priority order. **Never guess or assume a locator works** — verify with `Get Source` or Appium Inspector before using.

### Priority 1: `accessibility_id` (Most Preferred — Stable)

Maps to the iOS `accessibilityIdentifier` property set by developers. Most stable across app versions. Ask developers to add `accessibilityIdentifier` to all interactive elements.

```robotframework
${btn_login}        accessibility_id=loginButton
${inp_username}     accessibility_id=usernameTextField
${lbl_home}         accessibility_id=homeScreenTitle
```

### Priority 2: `name` (Accessibility Label)

Maps to the `accessibilityLabel` (displayed text). Use when `accessibility_id` is not set.

```robotframework
${btn_submit}    name=Submit
${lbl_welcome}   name=Welcome to FreshMart
```

### Priority 3: `ios=` Predicate String

Powerful XCUITest native selector. Use when `accessibility_id` and `name` are unavailable.

```robotframework
# By type + name
${btn_login}     ios=type == 'XCUIElementTypeButton' AND name == 'Login'

# By label (displayed text)
${lbl_error}     ios=label == 'Invalid credentials'

# Contains match
${cell_row}      ios=type == 'XCUIElementTypeCell' AND name CONTAINS 'Settings'

# Visibility check
${btn_active}    ios=type == 'XCUIElementTypeButton' AND name == 'Submit' AND visible == 1
```

Predicate operators: `==`, `!=`, `CONTAINS`, `BEGINSWITH`, `ENDSWITH`, `MATCHES` (regex), `AND`, `OR`, `NOT`

### Priority 4: `ios=**/XCUIElementType...` (Class Chain)

Faster than xpath. Use for structural queries (nth child, nested path).

```robotframework
# By attribute in backtick expression
${btn_back}      ios=**/XCUIElementTypeButton[`name == 'Back'`]

# By index in table
${cell_first}    ios=**/XCUIElementTypeTable/XCUIElementTypeCell[1]

# Navigation bar button
${nav_btn_back}  ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[1]
```

### Priority 5: `xpath` — Last Resort

Only when all above fail. Never use absolute xpath.

```robotframework
# Acceptable — relative xpath with meaningful attributes
${btn_ok}     xpath=//XCUIElementTypeButton[@name='OK']
${lbl_total}  xpath=//XCUIElementTypeStaticText[contains(@name,'Total')]

# NEVER — absolute xpath starting at root
xpath=//XCUIElementTypeApplication/XCUIElementTypeWindow/...   # FORBIDDEN
```

### NEVER Use on iOS

- `id=` (resource-id) — Android only
- `android=` UiSelector — Android only
- CSS selectors — native app only; valid in Safari webview only
- Absolute xpath

### `contains(@label, ...)` / `contains(@name, ...)` — Danger of Matching System Chrome

A broad `contains()` predicate on `label`/`name` can match an element that has **nothing to do with the screen you're testing** — most commonly the status bar (Wi-Fi/cellular/battery icons), keyboard, or system alerts, which are present on almost every screen and often carry accessibility labels containing common words like "Wi-Fi", "battery", "signal".

```robotframework
# DANGEROUS — also matches the always-present status bar Wi-Fi icon, not just real search results
${lbl_search_result_wifi}    xpath=//*[contains(@label,'Wi-Fi')]

# BETTER — scope to the actual results container, or assert count > 0 within that container,
# or match a more specific attribute (cell type + exact label) instead of a bare substring
${lbl_search_result_wifi}    xpath=//XCUIElementTypeTable[@name='SpotlightSearchResults']//*[contains(@label,'Wi-Fi')]
```

A test that passes with this kind of locator **may be a false positive** — it confirms the XPath found *something*, not that it found the *right* thing. Before finalizing this kind of assertion, confirm in the live UI tree that the matched element actually sits inside the expected results/content area, not in a persistent system region (status bar, nav bar, keyboard) that renders on every screen regardless of the action under test.

### Verify Locators Before Using

**Never hardcode a locator without verifying it exists in the view hierarchy — and that it uniquely identifies the intended element, not a decoy.**

```robotframework
${source}=    Get Source
Log    ${source}    level=DEBUG
Create File    ${OUTPUT_DIR}/ios_source.xml    ${source}
```

Use Appium Inspector on the live simulator/device for interactive inspection. If using RobotMCP (`.claude/skills/autotest-mcp-assist/SKILL.md`), `get_session_state`/live inspection confirms the locator **resolves** — it does not confirm the resolved element is the *semantically correct* one. For any `contains()`-based locator, manually check the surrounding parent hierarchy for exactly this reason before trusting a live-session PASS.

If a locator is uncertain → mark it `# TODO: verify with Get Source or Appium Inspector`.

---

## 3. Assertion Patterns

### Element Visibility

```robotframework
Common - Wait For Element Visible    ${lbl_success}
Wait Until Element Is Not Visible    ${icon_loading}    timeout=${TIMEOUT_MAX}
Page Should Not Contain Element      ${lbl_error}
```

### Screen Transition

Verify screen change by waiting for a landmark element unique to the destination screen:

```robotframework
# After tapping "Transfer" tab — wait for transfer screen heading
Common - Wait For Element Visible    ${lbl_transfer_heading}

# After successful login — wait for home screen element
Common - Wait For Element Visible    ${lbl_home_welcome}
```

### Content Assertions

```robotframework
Element Text Should Be       ${lbl_status}       Success
Element Should Contain Text  ${lbl_name}         ${expected_name}
Page Should Contain Text     ${txt_welcome}
Page Should Not Contain Text ${txt_error_msg}
```

### Always Assert After Every Important Action

```robotframework
# Wrong — no assertion
Login - Tap Login Button

# Correct — verify the outcome
Login - Tap Login Button
Common - Wait For Element Visible    ${lbl_home_welcome}
```

---

## 4. Project Structure & Feature Object Model (FOM)

### Project Layout

```
automation_test/tests/                              # .robot test suites only
automation_test/features/
  login/
    login_keywords.resource
    login_variables.resource
  profile/
    profile_keywords.resource
    profile_variables.resource
automation_test/common/
  common_keywords.resource          # 11+ standard wrappers
  common_variables.resource         # timeouts + capability variables
automation_test/config/
  imports.resource                  # Libraries + keyword files only
automation_test/data/
  login.yaml
  profile.yaml
automation_test/results/                            # gitignored
```

### File Size Limits

| File type | Limit | Action when exceeded |
|---|---|---|
| `*_keywords.resource` | ≤ 300 lines | Split by sub-feature |
| `*_variables.resource` | ≤ 150 lines | Move shared vars to `common_variables.resource` |
| `*.robot` | ≤ 200 lines | Split into separate files by scenario group |

### Centralized Imports

`automation_test/config/imports.resource` declares all libraries and keyword files. Test suites import only this file plus their YAML data.

```robotframework
# automation_test/config/imports.resource
*** Settings ***
Library     AppiumLibrary
Library     OperatingSystem
Library     Collections
Library     yaml
Library     String

Resource    ../common/common_keywords.resource
Resource    ../features/login/login_keywords.resource
Resource    ../features/profile/profile_keywords.resource
# Add a Resource line here whenever a new feature is created
```

Each keyword file imports `automation_test/config/imports.resource` and its own variables file:

```robotframework
# automation_test/features/login/login_keywords.resource
*** Settings ***
Resource    ../../config/imports.resource
Resource    login_variables.resource
```

Variable files (`_variables.resource`) have no imports — locators only.

### Feature Object Model (Strict Separation)

**Variables file — locators only, no imports:**

```robotframework
# automation_test/features/login/login_variables.resource
*** Variables ***
${inp_username}     accessibility_id=usernameTextField
${inp_password}     accessibility_id=passwordTextField
${btn_login}        accessibility_id=loginButton
${lbl_home}         accessibility_id=homeScreenTitle
${txt_invalid}      Invalid username or password
```

**Keywords file — actions only, using Common wrappers:**

```robotframework
# automation_test/features/login/login_keywords.resource
*** Settings ***
Resource    ../../config/imports.resource
Resource    login_variables.resource

*** Keywords ***
Login - Open Screen
    Common - Open App
    Common - Handle Alert
    Common - Wait For Element Visible    ${inp_username}

Login - Fill Credentials
    [Arguments]    ${username}    ${password}
    Common - Input Text       ${inp_username}    ${username}
    Common - Input Text       ${inp_password}    ${password}

Login - Tap Login Button
    Common - Click Element    ${btn_login}
    Common - Wait For Element Visible    ${lbl_home}

Login - Verify Login Success
    Common - Wait For Element Visible    ${lbl_home}
    Page Should Contain Element    ${lbl_home}
```

### Keyword Size Limit — ≤ 20 Lines

If a keyword exceeds 20 lines, split into focused sub-keywords.

### The "Common" Boundary Rule

- `common_variables.resource` — ONLY global timeouts and capability variables. NEVER feature-specific locators.
- `common_keywords.resource` — ONLY the standard wrappers. NEVER feature-specific flows.

### Unused Variable / Keyword / Argument Rule

Delete everything not referenced. If a variable, keyword, or argument is declared but never used, remove it.

### Strict DRY Principle

Zero duplication. Identical sequences → extract into a shared keyword.

### Two-Step Minimum Rule

Every custom keyword MUST contain at least two underlying keyword calls. No single-call wrappers.

---

## 5. Common Wrappers — Standard Keywords

**NEVER** use raw AppiumLibrary keywords (`Click Element`, `Input Text`, etc.) directly inside feature keyword files. Always use the Common wrappers.

`common_keywords.resource` MUST contain these keywords:

```robotframework
# automation_test/common/common_keywords.resource
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
    ${username}=    Get Environment Variable    FARM_USERNAME
    ${access_key}=  Get Environment Variable    FARM_ACCESS_KEY
    ${farm_url}=    Set Variable    http://${username}:${access_key}@${FARM_HOST}${FARM_PATH}
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

**Usage in feature keywords:**

```robotframework
# DO — use Common wrappers
Login - Fill Credentials
    [Arguments]    ${username}    ${password}
    Common - Input Text       ${inp_username}    ${username}
    Common - Input Text       ${inp_password}    ${password}
    Common - Click Element    ${btn_login}

# DON'T — raw AppiumLibrary bypasses retry and wait handling
Login - Fill Credentials
    Input Text      ${inp_username}    ${username}    # BAD
    Click Element   ${btn_login}                      # BAD
```

---

## 6. Capability Variables

All device capabilities and execution target MUST be declared as variables in `common_variables.resource`. Never hardcode capability values or credentials.

```robotframework
# automation_test/common/common_variables.resource
*** Variables ***
${TIMEOUT_MIN}          5s
${TIMEOUT_DEFAULT}      15s
${TIMEOUT_MAX}          30s

# --- Execution target: local | device_farm ---
${EXECUTION_TARGET}     local

# --- Local device/simulator ---
${APPIUM_URL}           http://127.0.0.1:4723
${DEVICE_NAME}          iPhone 15
${PLATFORM_VERSION}     17.0
${BUNDLE_ID}            com.example.app
${APP_PATH}             ${EMPTY}    # set to absolute .app/.ipa path to install fresh; leave empty to launch by bundleId
${NO_RESET}             ${TRUE}

# --- Shared (local + device farm) ---
${DEVICE_UDID}          ${EMPTY}    # optional for simulator; required for real device / device farm

# --- MCloud Device Farm config ---
${FARM_HOST}            10.207.247.201
${FARM_PATH}            /mcloud/wd/hub
# Credentials via environment variables ONLY (never in this file):
#   macOS/Linux:  export FARM_USERNAME=<username> && export FARM_ACCESS_KEY=<key>
#   Windows CMD:  set FARM_USERNAME=<username> && set FARM_ACCESS_KEY=<key>
#   PowerShell:   $env:FARM_USERNAME="<username>"; $env:FARM_ACCESS_KEY="<key>"
```

Values come from the project's `global-data.md`. Switch execution target at runtime:

```bash
# Run on local simulator (default)
robot --loglevel TRACE -d automation_test/results/ automation_test/tests/<feature>.robot

# Run on local real device
robot --loglevel TRACE -d automation_test/results/ -v DEVICE_UDID:00008030-001234567890002E automation_test/tests/<feature>.robot

# Run on MCloud device farm — set credentials first:
# macOS/Linux:  export FARM_USERNAME=myuser && export FARM_ACCESS_KEY=mykey
# Windows CMD:  set FARM_USERNAME=myuser && set FARM_ACCESS_KEY=mykey
# PowerShell:   $env:FARM_USERNAME="myuser"; $env:FARM_ACCESS_KEY="mykey"
robot --loglevel TRACE -d automation_test/results/ -v EXECUTION_TARGET:device_farm -v DEVICE_UDID:00008030-001234567890002E automation_test/tests/<feature>.robot
```

---

## 7. Timeout Variable Rule

**Never hardcode timeout values directly in keyword calls.**

```robotframework
# Wrong
Wait Until Element Is Visible    ${btn_login}    timeout=15s

# Correct
Wait Until Element Is Visible    ${btn_login}    timeout=${TIMEOUT_DEFAULT}
```

| Variable | Value | When to use |
|---|---|---|
| `${TIMEOUT_MIN}` | 5s | Optional elements, quick alert checks |
| `${TIMEOUT_DEFAULT}` | 15s | Standard elements (default) |
| `${TIMEOUT_MAX}` | 30s | Slow screens, loading states, WDA warm-up |

---

## 8. Locator and Text Variable Rule

**Never hardcode locators or text strings inline in keyword calls.**

```robotframework
# Wrong — hardcoded inline
Click Element            accessibility_id=loginButton
Wait Until Page Contains    Welcome

# Correct — declared as variables
*** Variables ***
${btn_login}      accessibility_id=loginButton
${txt_welcome}    Welcome

*** Keywords ***
Login - Tap Login
    Common - Click Element               ${btn_login}
    Common - Wait For Element Visible    ${txt_welcome}
```

---

## 9. Screenshot Rule

AppiumLibrary's `run_on_failure=Capture Page Screenshot` captures a screenshot the moment any keyword fails. No code needed. Do NOT add `Capture Page Screenshot` to `Test Teardown`.

```robotframework
# Correct — teardown only closes app
Test Teardown    Common - Close App

# Wrong — redundant with run_on_failure
Test Teardown    Run Keywords
...    Run Keyword If Test Failed    Capture Page Screenshot    # REMOVE THIS
...    AND    Common - Close App
```

---

## 10. iOS Alert Handling Rule

iOS alerts (permission dialogs, system prompts) MUST be handled with `Common - Handle Alert`, not by setting `autoAcceptAlerts=True` in capabilities (which bypasses all alerts including unexpected ones and can mask bugs).

```robotframework
# Correct — explicit handling at the right point in the flow
Login - Open Screen
    Common - Open App
    Common - Handle Alert             # handle initial permission dialog if present
    Common - Wait For Element Visible    ${inp_username}

# Correct — handle multiple dialogs with known button names
Settings - Enable Location
    Common - Click Element    ${btn_enable_location}
    Common - Handle Alert     While Using App
    Common - Handle Alert     OK

# Wrong — blindly auto-accepting all alerts in capabilities
Open Application    ${APPIUM_URL}
...    autoAcceptAlerts=${TRUE}    # BAD — masks unexpected alerts
```

---

## 11. Wait Strategies

### DO: Common wrappers (already include retry)

```robotframework
Common - Click Element               ${btn_submit}
Common - Wait For Element Visible    ${lbl_success}
Wait Until Element Is Not Visible    ${icon_loading}    timeout=${TIMEOUT_MAX}
```

### DO: `Wait Until Keyword Succeeds` for extra retry on flaky elements

```robotframework
# XCUITest can be slow to settle; retry on animation-heavy transitions
Wait Until Keyword Succeeds    5x    2s
...    Element Text Should Be    ${lbl_status}    Completed
```

### DO: `Common - Swipe Up To Element` for off-screen elements

```robotframework
Common - Swipe Up To Element    ${btn_confirm}    max_swipes=15
```

### DON'T: Use `Sleep` without comment

```robotframework
Sleep    3s    # BAD — flaky, wastes time
```

**Exception**: brief `Sleep 0.3s` after `Common - Tap Navigation Back` to let the transition settle — and always add a comment.

### DON'T: Override global timeout

```robotframework
Set Appium Timeout    10s    # BAD — use per-keyword timeout= param instead
```

---

## 12. Test Case Standards

### App Lifecycle — Per Test (Not Per Suite)

Each test case opens a fresh app session in `Test Setup` and closes it in `Test Teardown`. Full isolation — no shared state.

```robotframework
*** Settings ***
Resource     ../config/imports.resource
Variables    ../data/login.yaml

Test Setup      Login - Open Screen
Test Teardown   Common - Close App

*** Test Cases ***
User_Can_Login_With_Valid_Credentials
    [Tags]    login    smoke    TC-001
    Login - Login With Valid Credentials    ${data["${TEST_NAME}"]}
```

Feature keyword called from `Test Setup` always uses `Common - Open App`:

```robotframework
Login - Open Screen
    Common - Open App
    Common - Handle Alert             # allow any initial permission
    Common - Wait For Element Visible    ${inp_username}
```

| Hook | Runs | Purpose |
|---|---|---|
| `Suite Setup` | Once before all tests | Non-app only: load YAML, prepare API state |
| `Suite Teardown` | Once after all tests | Non-app cleanup; omit if nothing to do |
| `Test Setup` | Before each test | Open fresh app session + navigate to feature screen |
| `Test Teardown` | After each test | Close app (`run_on_failure` handles screenshots) |

### Tags — Required on Every Test Case

```robotframework
*** Test Cases ***
User_Can_Login_With_Valid_Credentials
    [Tags]    login    smoke    TC-001
    Login - Login With Valid Credentials    ${data["${TEST_NAME}"]}
```

| Tag | Purpose |
|---|---|
| `smoke` | Critical path — run on every build |
| `regression` | Full regression suite |
| `<feature>` | Feature name: `login`, `profile` |
| `known-bug` | Known app bug — test will fail at expected step |

### One Keyword Per Test Case

```robotframework
*** Test Cases ***
User_Can_Login_With_Valid_Credentials
    [Tags]    login    smoke
    Login - Login With Valid Credentials    ${data["${TEST_NAME}"]}

User_Cannot_Login_With_Wrong_Password
    [Tags]    login    regression
    Login - Login With Wrong Password    ${data["${TEST_NAME}"]}
```

### Tests Must Be Self-Contained

Never rely on state left by a previous test.

### Control Flow Belongs in Keywords

```robotframework
# Wrong — IF in test case
User_Can_Select_Tab
    IF    ${tab} == 'profile'    Profile - Click Tab

# Correct — moved to keyword
User_Can_Select_Tab
    Profile - Select Tab    ${tab}
```

---

## 13. YAML Test Data

Same pattern as web / Android FOM — one file per feature, top-level key `data:`.

```yaml
# automation_test/data/login.yaml
data:
  User_Can_Login_With_Valid_Credentials:
    username: "testuser@example.com"
    password: "Test@1234"

  User_Cannot_Login_With_Wrong_Password:
    username: "testuser@example.com"
    password: "wrongpass"
    expected_error: "Invalid username or password"
```

```robotframework
# Scenario keyword receives the data dict
Login - Login With Valid Credentials
    [Arguments]    ${td}
    Login - Fill Credentials    ${td}[username]    ${td}[password]
    Login - Verify Login Success
```

**Rules:**
- Top-level key MUST be `data:`
- Child keys must match test case names exactly
- Never store passwords/tokens in YAML — use environment variables

---

## 14. Advanced Patterns

### iOS Table Navigation

```robotframework
# Select cell by name
Common - Click Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${item_name}'`]

# Navigate back after entering detail screen
Common - Tap Navigation Back
Common - Wait For Element Visible    ${lbl_list_heading}
```

### iOS Picker Wheel

```robotframework
*** Keywords ***
Profile - Select Date Of Birth
    [Arguments]    ${month}    ${day}    ${year}
    Common - Click Element    ${btn_date_picker}
    Common - Wait For Element Visible    xpath=//XCUIElementTypeDatePicker
    @{wheels}=    Get WebElements    class=XCUIElementTypePickerWheel
    Input Text    ${wheels}[0]    ${month}
    Input Text    ${wheels}[1]    ${day}
    Input Text    ${wheels}[2]    ${year}
    Common - Click Element    accessibility_id=Done
```

### iOS Keyboard

```robotframework
*** Keywords ***
Login - Hide Keyboard After Input
    Common - Input Text    ${inp_search}    ${query}
    # Tap Done key or Return key on keyboard
    Run Keyword And Ignore Error
    ...    Click Element    ios=**/XCUIElementTypeKey[`name == 'Done'`]
    Run Keyword And Ignore Error
    ...    Click Element    ios=**/XCUIElementTypeButton[`name == 'Done'`]
```

### Coordinate Tap (Workaround)

When `Common - Click Element` fails because XCUITest considers an element non-interactable:

```robotframework
*** Keywords ***
Common - Tap Center
    [Arguments]    ${locator}
    Wait Until Page Contains Element    ${locator}
    ${location}=    Get Element Location    ${locator}
    ${size}=        Get Element Size    ${locator}
    ${x}=    Evaluate    int(${location['x']} + ${size['width']} / 2)
    ${y}=    Evaluate    int(${location['y']} + ${size['height']} / 2)
    Tap With Positions    ${1}    ${x}    ${y}
```

### `Run Keyword And Return Status` vs `Run Keyword And Ignore Error`

| | `Run Keyword And Return Status` | `Run Keyword And Ignore Error` |
|---|---|---|
| Returns | `${True}` / `${False}` | Tuple: `('PASS'/'FAIL', value)` |
| Use when | You need to branch on pass/fail | Step is optional, outcome irrelevant |

---

## 15. Environment & Dynamic Data

**Never hardcode credentials or environment-specific values.** Read from `global-data.md`.

```robotframework
*** Keywords ***
Login - Generate Unique Email
    ${timestamp}=    Get Current Date    result_format=%Y%m%d%H%M%S
    RETURN    testuser_${timestamp}@example.com
```

---

## 16. Device Farm (MCloud)

The project uses an internal MCloud device farm at `http://10.207.247.201/mcloud/wd/hub`.

**URL pattern**: `http://${FARM_USERNAME}:${FARM_ACCESS_KEY}@${FARM_HOST}${FARM_PATH}`

Credentials MUST come from environment variables:
```bash
# macOS / Linux
export FARM_USERNAME=<your_username>
export FARM_ACCESS_KEY=<your_access_key>

# Windows CMD
set FARM_USERNAME=<your_username>
set FARM_ACCESS_KEY=<your_access_key>

# Windows PowerShell
$env:FARM_USERNAME = "<your_username>"
$env:FARM_ACCESS_KEY = "<your_access_key>"
```

Switch via CLI variable — no code changes needed:
```bash
robot --loglevel TRACE -d automation_test/results/ -v EXECUTION_TARGET:device_farm -v DEVICE_UDID:<udid_from_mcloud_ui> automation_test/tests/<feature>.robot
```

For deep setup guidance, UDID lookup, and parallel execution, read `references/device-farm.md`.

---

## 17. Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Do Instead |
|---|---|---|
| Raw AppiumLibrary in feature keywords | Bypasses retry/wait | Use `Common - Click Element` / `Common - Input Text` |
| `Sleep 5s` without comment | Flaky, wastes time | Use `Common - Wait For Element Visible` |
| Absolute xpath `//XCUIElementTypeApplication/...` | Breaks on any layout change | Use `accessibility_id` or relative `xpath` |
| Hardcoded locator inline in steps | Hard to maintain | Declare as `*** Variables ***` |
| Hardcoded timeout value (e.g., `timeout=15s`) | Inconsistent waits | Use `${TIMEOUT_DEFAULT}` etc. |
| Hardcoded capabilities inline in `Open Application` | Hard to maintain | Use dict-based `Common - Open App` with variables |
| `autoAcceptAlerts=True` in capabilities | Masks unexpected alerts | Use `Common - Handle Alert` explicitly |
| Using `id=` locator on iOS | Android-only (resource-id) | Use `accessibility_id` or `name` |
| Using `android=` UiSelector on iOS | Android-only | Use `ios=` predicate or class chain |
| Credentials (`FARM_USERNAME`, `FARM_ACCESS_KEY`) hardcoded | Security risk | Use `Get Environment Variable` in `Common - Open App Device Farm` |
| Using `EXECUTION_TARGET=device_farm` without `DEVICE_UDID` | Wrong device | Always specify UDID for device farm |
| Feature keyword imports only `automation_test/config/imports.resource` without variables file | Missing locators | Import `automation_test/config/imports.resource` + own `_variables.resource` |
| Thin 1-line keyword wrappers | Zero value | Two-step minimum rule |
| No `[Tags]` on test cases | Can't filter in CI | Tag every test case |
| No assertion after action | Test always passes, proves nothing | Always assert the outcome |
| Unused variables / keywords / arguments | Dead code | Delete what is not used |
| Hardcoded test data in test steps | Breaks across environments | Use YAML data files |
| `Set Appium Timeout` globally | Overrides centralized config | Use per-keyword `timeout=` param |
| `FOR`/`IF` directly in test cases | Logic belongs in keywords | Move control flow to feature keyword |
| CSS selectors in native app context | Not supported on native iOS | Use `accessibility_id`, `name`, `ios=` |
