# Android Locators — Complete Reference

## Priority Order (Always Follow This)

| Priority | Strategy | When to use |
|---|---|---|
| 1 | `id` (resource-id) | `resource-id` attribute exists — absolute priority |
| 2 | `accessibility_id` | `content-desc` attribute exists — stable, cross-platform |
| 3 | `android=` UIAutomator2 | When 1 & 2 unavailable; most powerful text/class queries |
| 4 | `class` | Element is the **only** instance of its class on screen |
| 5 | `xpath` | Last resort — very slow, only relative XPath, never absolute |

**Never use:** CSS selectors, `link=`, `partial link=` — not supported on native Android.

---

## Priority 1: `id` (Resource ID) — Ưu tiên tuyệt đối

Maps to Android `resource-id`. Most uniquely identifying attribute — always prefer this when available.

```robotframework
# Full form — always unique, preferred
${btn_confirm}    id=com.example.app:id/btn_confirm
${inp_amount}     id=com.example.app:id/edt_amount

# Short form — only if unique across the whole screen
${btn_confirm}    id=btn_confirm
```

**How to find**: In view hierarchy XML, look for `resource-id` attribute.

---

## Priority 2: `accessibility_id`

Maps to Android `content-desc` attribute. Excellent cross-platform stability — works on both Android and iOS.

```robotframework
${btn_login}       accessibility_id=login_button
${inp_username}    accessibility_id=username_input
${lbl_balance}     accessibility_id=balance_label
```

**How to find**: In Appium Inspector or `Get Source`, look for `content-desc` attribute.

---

## Priority 3: `android=` UIAutomator2

Powerful native selector. Use when `accessibility_id` and `id` are not available.

### By text

```robotframework
# Exact text match
${btn_login}     android=new UiSelector().text("Login")

# Contains (partial match)
${btn_more}      android=new UiSelector().textContains("more")

# Starts with
${btn_confirm}   android=new UiSelector().textStartsWith("Confirm")

# Regex match
${btn_action}    android=new UiSelector().textMatches("(Confirm|Agree)")
```

### By resource ID

```robotframework
${btn_submit}    android=new UiSelector().resourceId("com.example.app:id/btn_submit")
${btn_partial}   android=new UiSelector().resourceIdContains("btn_submit")
```

### By class + text (disambiguation)

```robotframework
# When text alone matches multiple elements
${btn_confirm}    android=new UiSelector().className("android.widget.Button").text("Confirm")
```

### By index (nth element of type)

```robotframework
# First EditText on screen
${inp_first}    android=new UiSelector().className("android.widget.EditText").instance(0)
```

### Scrollable — AUTO-SCROLLS to find element (most powerful for lists)

```robotframework
# Scroll entire screen to find text
${item}    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("Settings"))

# Scroll within specific container (RecyclerView)
${item}    android=new UiScrollable(new UiSelector().resourceId("com.example:id/recycler_list")).scrollIntoView(new UiSelector().text("Item 50"))

# Horizontal scroll (tab bar, carousel)
${tab}    android=new UiScrollable(new UiSelector().scrollable(true).horizontal(true)).scrollIntoView(new UiSelector().text("Tab 5"))

# Scroll to beginning / end
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollToBeginning(10)
Click Element    android=new UiScrollable(new UiSelector().scrollable(true)).scrollToEnd(10)
```

---

## Priority 4: `class` — Only When Element Is Unique on Screen

Maps to Android widget class name. Use only when the element is the **only** instance of its class visible on the current screen.

```robotframework
${inp_search}    class=android.widget.EditText
${lbl_title}     class=android.widget.TextView
```

If multiple elements share the same class → use `android=` UiSelector with `.className()` combined with text or index.

---

## Priority 5: `xpath` — Last Resort (Slow)

Use only when priorities 1–4 fail. XPath evaluation is significantly slower than UiAutomator2 on Android — avoid in performance-sensitive test suites. Always relative (`//`), never absolute.

```robotframework
# By text content
${btn_back}        xpath=//android.widget.ImageButton[@content-desc='Navigate up']
${lbl_total}       xpath=//android.widget.TextView[contains(@text,'Tổng cộng')]

# Relative to parent — useful for list items
${btn_item_action}    xpath=//android.widget.TextView[@text='Item Name']/following-sibling::android.widget.ImageButton

# NEVER — absolute xpath (breaks on any layout change)
# xpath=/hierarchy/android.widget.FrameLayout/...   ← FORBIDDEN
```

---

## Android Element Class Names

| Element | Class Name |
|---|---|
| Button | `android.widget.Button` |
| ImageButton | `android.widget.ImageButton` |
| Input (EditText) | `android.widget.EditText` |
| Label (TextView) | `android.widget.TextView` |
| Image | `android.widget.ImageView` |
| Checkbox | `android.widget.CheckBox` |
| Radio button | `android.widget.RadioButton` |
| Switch / Toggle | `android.widget.Switch` |
| Dropdown (Spinner) | `android.widget.Spinner` |
| List | `android.widget.ListView` |
| RecyclerView | `androidx.recyclerview.widget.RecyclerView` |
| ScrollView | `android.widget.ScrollView` |
| ProgressBar | `android.widget.ProgressBar` |

---

## Verifying Locators

**Never hardcode a locator without verifying it exists in the view hierarchy.**

```robotframework
# 1. Dump view hierarchy to file for inspection
${source}=    Get Source
Log    ${source}    level=DEBUG
Create File    ${OUTPUT_DIR}/screen_source.xml    ${source}
```

```bash
# 2. Use Appium Inspector (GUI tool)
# Connect to running Appium session — inspect live elements

# 3. Use adb uiautomator dump
adb shell uiautomator dump /sdcard/window_dump.xml
adb pull /sdcard/window_dump.xml .
```

### What to look for in the XML

```xml
<android.widget.Button
    resource-id="com.example.app:id/btn_login"
    content-desc="login_button"
    text="Login"
    enabled="true"
    clickable="true" />
```

- `content-desc` → use `accessibility_id=login_button`
- `resource-id` → use `id=com.example.app:id/btn_login`
- `text` → use `android=new UiSelector().text("Login")` (last resort)