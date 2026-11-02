# iOS Gestures Reference

## Swipe By Percent (Recommended — Cross-Device Safe)

`Swipe By Percent` uses screen-percentage coordinates — works on any iPhone/iPad size.

```robotframework
# Swipe UP (finger moves bottom → top, reveals content below)
Swipe By Percent    50    80    50    20    800

# Swipe DOWN (finger moves top → bottom, reveals content above)
Swipe By Percent    50    20    50    80    800

# Swipe LEFT (finger moves right → left, next carousel/page item)
Swipe By Percent    80    50    20    50    500

# Swipe RIGHT (finger moves left → right, previous carousel/page item)
Swipe By Percent    20    50    80    50    500
```

Parameters: `start_x%  start_y%  end_x%  end_y%  duration_ms`

**iOS Note:** Slower duration (800–1200ms) lets XCUITest properly register the gesture. Speeds below 300ms may be ignored.

---

## Common - Swipe Up To Element (Built-in Wrapper)

For elements that are off-screen and require scrolling:

```robotframework
# Swipe up until element appears (default 15 swipes)
Common - Swipe Up To Element    ${btn_submit}

# Increase swipes for very long pages
Common - Swipe Up To Element    ${btn_submit}    max_swipes=25

# Swipe down for elements above the fold
Common - Swipe Down To Element    ${lbl_heading}
```

The wrapper checks visibility before each swipe — stops as soon as the element appears.

---

## Scroll to Table Row (iOS Table / UITableView)

iOS does not have `UiScrollable` (Android-only). Use swipe loop or predicate class chain.

```robotframework
*** Keywords ***
Table - Scroll To Row And Tap
    [Arguments]    ${row_name}    ${max_swipes}=20
    Common - Swipe Up To Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${row_name}'`]    max_swipes=${max_swipes}
    Common - Click Element          ios=**/XCUIElementTypeCell[`name CONTAINS '${row_name}'`]

Table - Collect All Rows By Scrolling
    [Arguments]    ${max_swipes}=20
    @{all_items}=    Create List
    ${prev_count}=    Set Variable    0
    FOR    ${i}    IN RANGE    ${max_swipes}
        @{visible}=    Get WebElements    class=XCUIElementTypeCell
        FOR    ${cell}    IN    @{visible}
            ${text}=    Get Text    ${cell}
            ${exists}=    Evaluate    '${text}' in ${all_items}
            IF    not ${exists}    Append To List    ${all_items}    ${text}
        END
        ${curr}=    Get Length    ${all_items}
        IF    ${curr} == ${prev_count}    BREAK
        ${prev_count}=    Set Variable    ${curr}
        Swipe By Percent    50    80    50    20    800
    END
    RETURN    ${all_items}
```

---

## Pull to Refresh

```robotframework
*** Keywords ***
Common - Pull To Refresh
    Swipe By Percent    50    15    50    70    1200
    Wait Until Element Is Not Visible    ${icon_loading}    timeout=${TIMEOUT_MAX}
    Common - Wait For Element Visible    ${lbl_content_heading}
```

Use a slow, long downward swipe starting from near the top edge — XCUITest requires this to trigger pull-to-refresh.

---

## Horizontal Swipe (Carousel / Onboarding)

```robotframework
*** Keywords ***
Onboarding - Swipe To Next Slide
    Swipe By Percent    80    50    20    50    600

Onboarding - Swipe To Previous Slide
    Swipe By Percent    20    50    80    50    600

Onboarding - Complete Onboarding
    Onboarding - Swipe To Next Slide
    Common - Wait For Element Visible    ${lbl_slide_2}
    Onboarding - Swipe To Next Slide
    Common - Wait For Element Visible    ${lbl_slide_3}
    Common - Click Element    ${btn_get_started}
```

---

## Long Press

```robotframework
*** Keywords ***
List - Long Press Row
    [Arguments]    ${row_locator}
    Long Press    ${row_locator}    duration=2000
    Common - Wait For Element Visible    ${menu_context}

List - Delete Row Via Context Menu
    [Arguments]    ${row_locator}
    List - Long Press Row    ${row_locator}
    Common - Click Element    accessibility_id=deleteMenuItem
    Common - Handle Alert     Delete
```

`Long Press` with `duration` in milliseconds. 1500–2000ms is typical for iOS context menus.

---

## Tap by Coordinates (Fallback)

When `Common - Click Element` fails because XCUITest considers the element non-interactable:

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

Use as a last resort. Add a comment explaining why `Click Element` failed.

---

## Drag and Drop

```robotframework
*** Keywords ***
Common - Drag Element To Element
    [Arguments]    ${source_locator}    ${target_locator}
    ${src}=     Get Element Location    ${source_locator}
    ${src_sz}=  Get Element Size       ${source_locator}
    ${tgt}=     Get Element Location    ${target_locator}
    ${tgt_sz}=  Get Element Size       ${target_locator}
    ${start_x}=    Evaluate    int(${src['x']} + ${src_sz['width']} / 2)
    ${start_y}=    Evaluate    int(${src['y']} + ${src_sz['height']} / 2)
    ${end_x}=      Evaluate    int(${tgt['x']} + ${tgt_sz['width']} / 2)
    ${end_y}=      Evaluate    int(${tgt['y']} + ${tgt_sz['height']} / 2)
    Swipe    ${start_x}    ${start_y}    ${end_x}    ${end_y}    1500
```

Use a slow swipe (1500ms+) for drag-and-drop — XCUITest needs time to register the hold before the drag.

---

## Pinch and Zoom

```robotframework
# Zoom in on element (200% = 2x zoom)
Zoom    ${locator}    percent=200    steps=10

# Pinch out on element (zoom out to 50%)
Pinch    ${locator}    percent=50    steps=10
```

```robotframework
*** Keywords ***
Map - Zoom In
    Zoom    ${lbl_map}    percent=200    steps=10
    Common - Wait For Element Visible    ${lbl_map_detail}

Map - Zoom Out
    Pinch    ${lbl_map}    percent=50    steps=10
```
