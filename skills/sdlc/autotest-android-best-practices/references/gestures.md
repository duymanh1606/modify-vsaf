# Android Gestures Reference

## Swipe By Percent (Recommended — Cross-Device Safe)

`Swipe By Percent` uses screen percentage coordinates — works on any screen resolution.

```robotframework
# Swipe UP (finger moves bottom → top, to scroll DOWN and reveal content below)
Swipe By Percent    50    80    50    20    1000

# Swipe DOWN (finger moves top → bottom, to scroll UP and reveal content above)
Swipe By Percent    50    20    50    80    1000

# Swipe LEFT (finger moves right → left, to go to next item/page)
Swipe By Percent    80    50    20    50    500

# Swipe RIGHT (finger moves left → right, to go to previous item/page)
Swipe By Percent    20    50    80    50    500
```

Parameters: `start_x%  start_y%  end_x%  end_y%  duration_ms`

---

## Common - Swipe Up To Element (Built-in Wrapper)

Use this for elements that are off-screen and require scrolling:

```robotframework
# Swipe up until element appears (max 10 swipes by default)
Common - Swipe Up To Element    ${btn_submit}

# Override max swipes for long pages
Common - Swipe Up To Element    ${btn_submit}    max_swipes=20

# Swipe down for elements above the fold
Common - Swipe Down To Element    ${lbl_heading}
```

---

## UIAutomator2 Auto-Scroll (Best for RecyclerView / ListView)

For lists, UIAutomator2 `scrollIntoView` is more reliable than manual swipe looping:

```robotframework
# Auto-scroll any scrollable container to find element by text
Common - Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("${item_name}"))

# Scroll in specific container
Common - Click Element    android=new UiScrollable(new UiSelector().resourceId("com.example:id/list_view")).scrollIntoView(new UiSelector().text("${item_name}"))

# Horizontal scroll (tab bar)
Common - Click Element    android=new UiScrollable(new UiSelector().scrollable(true).horizontal(true)).scrollIntoView(new UiSelector().text("${tab_name}"))
```

---

## Pull to Refresh

```robotframework
Pull - Refresh Screen
    Swipe By Percent    50    20    50    80    1000    # swipe down from top
    Wait Until Element Is Not Visible    ${icon_loading}    timeout=${TIMEOUT_MAX}
    Common - Wait For Element Visible    ${lbl_content_heading}
```

---

## Long Press (Context Menu, Hold Actions)

AppiumLibrary v3.x: use `Tap` with `duration`.

```robotframework
# Long press for 2 seconds (context menu)
Tap    ${lbl_list_item}    duration=0:00:02

# Then interact with context menu
Common - Wait For Element Visible    ${menu_delete}
Common - Click Element    ${menu_delete}
```

---

## Swipe Left/Right on Carousel or Onboarding

```robotframework
*** Keywords ***
Onboarding - Swipe To Next Slide
    Swipe By Percent    80    50    20    50    500

Onboarding - Complete Onboarding
    Onboarding - Swipe To Next Slide
    Common - Wait For Element Visible    ${lbl_slide_2}
    Onboarding - Swipe To Next Slide
    Common - Wait For Element Visible    ${lbl_slide_3}
    Common - Click Element    ${btn_get_started}
```

---

## Tap Center of Element (Workaround for Click Failures)

When `Common - Click Element` fails on an element that is slightly obscured, use coordinate tap:

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
    Swipe    ${start_x}    ${start_y}    ${end_x}    ${end_y}    1000
```

---

## Collect All Items in a Scrollable List

```robotframework
*** Keywords ***
Common - Get All List Items By Scrolling
    [Arguments]    ${item_locator}    ${max_swipes}=20
    @{all_items}=    Create List
    ${prev_count}=    Set Variable    0
    FOR    ${i}    IN RANGE    ${max_swipes}
        @{visible}=    Get WebElements    ${item_locator}
        FOR    ${el}    IN    @{visible}
            ${text}=    Get Text    ${el}
            ${exists}=    Evaluate    '${text}' in ${all_items}
            IF    not ${exists}    Append To List    ${all_items}    ${text}
        END
        ${curr_count}=    Get Length    ${all_items}
        IF    ${curr_count} == ${prev_count}    BREAK
        ${prev_count}=    Set Variable    ${curr_count}
        Swipe By Percent    50    80    50    20    1000
    END
    RETURN    ${all_items}
```