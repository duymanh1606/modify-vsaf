# iOS Locator Strategies Reference

## Priority Table

| Priority | Strategy | Prefix | Stability | Use when |
|---|---|---|---|---|
| 1 | `accessibility_id` | `accessibility_id=` | Highest | `accessibilityIdentifier` set by dev |
| 2 | `name` | `name=` | High | `accessibilityLabel` (displayed text) |
| 3 | iOS Predicate String | `ios=` | Medium-High | No accessibility attributes; need type filter |
| 4 | iOS Class Chain | `ios=**/` | Medium | Structural queries, index-based access |
| 5 | `xpath` | `xpath=` | Low | Last resort — never absolute |

**NEVER on iOS:** `id=` (Android resource-id), `android=` UiSelector, CSS selectors (native app only), absolute xpath.

---

## Priority 1: `accessibility_id`

Maps to iOS `accessibilityIdentifier`. Most stable — set by developers, survives UI redesigns.

```robotframework
${btn_login}        accessibility_id=loginButton
${inp_username}     accessibility_id=usernameTextField
${lbl_home}         accessibility_id=homeScreenTitle
${sw_notifications} accessibility_id=notificationsSwitch
${tab_profile}      accessibility_id=profileTabBar
```

Ask iOS developers to add `accessibilityIdentifier` to all interactive elements.

---

## Priority 2: `name`

Maps to iOS `accessibilityLabel` (typically the visible text or developer-set label).

```robotframework
${btn_submit}    name=Submit
${lbl_welcome}   name=Welcome to the App
${btn_ok}        name=OK
```

Differs from `accessibility_id` — `name` is the human-readable label, `accessibility_id` is the programmatic identifier.

---

## Priority 3: iOS Predicate String (`ios=`)

XCUITest native predicate query. Fast, powerful, no XPath overhead.

```robotframework
# By type + name (exact match)
${btn_login}     ios=type == 'XCUIElementTypeButton' AND name == 'Login'

# By label (displayed text)
${lbl_error}     ios=label == 'Invalid username or password'

# Contains match (partial text)
${cell_item}     ios=type == 'XCUIElementTypeCell' AND name CONTAINS 'Settings'

# Begins with
${lbl_greeting}  ios=type == 'XCUIElementTypeStaticText' AND value BEGINSWITH 'Hello'

# Visibility filter
${btn_active}    ios=type == 'XCUIElementTypeButton' AND name == 'Done' AND visible == 1

# Enabled filter
${btn_submit}    ios=type == 'XCUIElementTypeButton' AND name == 'Submit' AND enabled == 1

# NOT operator
${btn_cancel}    ios=type == 'XCUIElementTypeButton' AND NOT name == 'OK'

# Combined OR
${alert_btn}     ios=name == 'Allow' OR name == 'OK'
```

### Predicate Operators

| Operator | Meaning |
|---|---|
| `==` | Exact equals |
| `!=` | Not equals |
| `CONTAINS` | Substring match |
| `BEGINSWITH` | Starts with |
| `ENDSWITH` | Ends with |
| `MATCHES` | Regex match |
| `AND` | Logical AND |
| `OR` | Logical OR |
| `NOT` | Logical NOT |

### Predicate Attributes

| Attribute | Maps to |
|---|---|
| `name` | accessibilityLabel |
| `label` | accessibilityLabel (alias) |
| `value` | accessibilityValue |
| `type` | XCUIElement type string |
| `visible` | 1 if visible, 0 if not |
| `enabled` | 1 if enabled, 0 if disabled |

---

## Priority 4: iOS Class Chain (`ios=**/`)

Structural path queries — faster than xpath. Use backtick expressions for filtering.

```robotframework
# Button by name
${btn_back}          ios=**/XCUIElementTypeButton[`name == 'Back'`]

# Any button with name containing
${btn_allow}         ios=**/XCUIElementTypeButton[`name CONTAINS 'Allow'`]

# By index in table
${cell_first}        ios=**/XCUIElementTypeTable/XCUIElementTypeCell[1]
${cell_third}        ios=**/XCUIElementTypeTable/XCUIElementTypeCell[3]

# Navigation bar back button (always first button in nav bar)
${nav_btn_back}      ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[1]

# Named navigation bar button
${nav_btn_done}      ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[`name == 'Done'`]

# Alert button
${alert_allow}       ios=**/XCUIElementTypeAlert/XCUIElementTypeButton[`name == 'Allow'`]

# Tab bar item
${tab_home}          ios=**/XCUIElementTypeTabBar/XCUIElementTypeButton[`name == 'Home'`]

# Cell containing specific static text
${cell_name}         ios=**/XCUIElementTypeCell[`name CONTAINS '${item_name}'`]

# Keyboard key
${key_return}        ios=**/XCUIElementTypeKey[`name == 'Return'`]
${key_done}          ios=**/XCUIElementTypeKey[`name == 'Done'`]
```

---

## Priority 5: `xpath` — Last Resort

Relative xpath only. Never absolute (starting with full XCUIElementTypeApplication path).

```robotframework
# Acceptable — relative with meaningful attribute
${btn_ok}     xpath=//XCUIElementTypeButton[@name='OK']
${lbl_total}  xpath=//XCUIElementTypeStaticText[contains(@name,'Total')]
${inp_email}  xpath=//XCUIElementTypeTextField[@value='Enter email']

# NEVER — absolute xpath
xpath=//XCUIElementTypeApplication/XCUIElementTypeWindow/XCUIElementTypeOther/...   # FORBIDDEN
```

---

## iOS Element Types

| Element | XCUIElementType | Common locator |
|---|---|---|
| Button | `XCUIElementTypeButton` | `accessibility_id=` |
| Text input | `XCUIElementTypeTextField` | `accessibility_id=` |
| Password input | `XCUIElementTypeSecureTextField` | `accessibility_id=` |
| Label / static text | `XCUIElementTypeStaticText` | `name=` or predicate |
| Image | `XCUIElementTypeImage` | `accessibility_id=` |
| Switch | `XCUIElementTypeSwitch` | `accessibility_id=` |
| Table | `XCUIElementTypeTable` | class chain |
| Table cell | `XCUIElementTypeCell` | class chain with name filter |
| Collection view | `XCUIElementTypeCollectionView` | class chain |
| Picker | `XCUIElementTypePicker` | `accessibility_id=` |
| Picker wheel | `XCUIElementTypePickerWheel` | `class=XCUIElementTypePickerWheel` |
| Alert | `XCUIElementTypeAlert` | `class=XCUIElementTypeAlert` |
| Action sheet | `XCUIElementTypeSheet` | `class=XCUIElementTypeSheet` |
| Navigation bar | `XCUIElementTypeNavigationBar` | class chain |
| Tab bar | `XCUIElementTypeTabBar` | class chain |
| Scroll view | `XCUIElementTypeScrollView` | `accessibility_id=` |
| Keyboard | `XCUIElementTypeKeyboard` | `class=XCUIElementTypeKeyboard` |
| Key | `XCUIElementTypeKey` | class chain by name |

---

## Dump View Hierarchy

When a locator doesn't work, dump the source to find the correct attributes:

```robotframework
${source}=    Get Source
Log    ${source}    level=DEBUG
Create File    ${OUTPUT_DIR}/ios_source.xml    ${source}
```

Then search the XML for the element. Key attributes to look for:
- `name` → use with `accessibility_id=` or `name=`
- `label` → use with `name=` or predicate `label ==`
- `type` → use for predicate `type == 'XCUIElementType...'`
- `value` → use for predicate `value CONTAINS`

Also use **Appium Inspector** connected to the live simulator/device for interactive locator building.
