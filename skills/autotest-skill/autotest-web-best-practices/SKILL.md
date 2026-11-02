---
name: autotest-web-best-practices
description: Robot Framework web (SeleniumLibrary) test automation standards — locator strategy, assertion patterns, FOM structure, wait strategies, custom wrappers, and anti-patterns. Use when writing, reviewing, or debugging RF web tests.
user-invocable: false
---

# Robot Framework Web Test Automation Best Practices

## Overview
This document defines the testing standards, patterns, and best practices for writing E2E tests using Robot Framework (with SeleniumLibrary). All test automation agents and code reviewers MUST follow these guidelines.

## When to Load Additional References

For deep troubleshooting or edge cases, read the relevant reference file in `.claude/skills/autotest-web-best-practices/references/`:

| Situation | Reference file |
|---|---|
| ChromeDriver setup / version mismatch | `webdriver-setup.md` |
| Element not found, stale element, click intercepted | `troubleshooting.md` |
| Complex wait patterns (AJAX, spinner, count) | `waiting-strategies.md` |
| Locator edge cases (dynamic IDs, tables, multi-element) | `locators.md` |
| JavaScript execution patterns | `javascript-execution.md` |
| iframe / multi-window handling | `frames-windows.md` |
| Screenshots and log configuration | `screenshots-logs.md` |
| Full SeleniumLibrary keyword reference | `keywords-reference.md` |

Example files for common patterns are in `.claude/skills/autotest-web-best-practices/examples/`.

---

## 1. Project Test Setup

### Documentation & Commenting Standards

The Agent MUST keep all documentation and comments extremely concise, punchy, and direct. Avoid narrative prose or stating the obvious.

#### Suite & Keyword Documentation (`[Documentation]`)
- **Max 1-2 Sentences:** Keep the documentation block to a maximum of 2 lines.
- **Focus on "What & Why", Not "How":** Do NOT describe the step-by-step code execution. Focus on the business goal or the specific edge case.
- **Bad:** `[Documentation]    This keyword will first check if the login button is visible, then it will click on it, and then it will wait for the dashboard page to load.`
- **Good:** `[Documentation]    Authenticates the user and verifies successful redirection to the main dashboard.`

#### Inline Comments (`#`)
- **The "Why Only" Rule:** Use inline comments ONLY to explain *why* a non-obvious workaround, a complex XPath traversal, or a specific business logic was used.
- **Strictly Prohibited:** Do NOT write comments for self-explanatory actions (e.g., `# Click submit button` before a `Click Element` call).
- **Format:** Keep inline comments under **10 words** and on a single line.

### Config Reference
- **Test directory**: `./tests` — test suites (`.robot` files only)
- **Features directory**: `./features` — keywords & variables per feature/domain
- **Common directory**: `./common` — shared wrappers and global variables
- **Config directory**: `./config` — `imports.resource` (libraries + keyword files only)
- **Data directory**: `./data` — YAML test data, one file per feature
- **Results directory**: `./results` — robot output (gitignored)
- **Base URL**: defined in the project's `global-data.md`
- **Default Timeout**: set globally via `Library SeleniumLibrary timeout=30s` in `imports.resource`. **Never** use `Set Selenium Timeout` or `Set Selenium Implicit Wait` elsewhere.
- **Browser Mode (CRITICAL)**: MUST run in HEADED mode at all times. Never use `headlesschrome` or `--headless`. Headless mode hides rendering issues and makes failure screenshots useless.
- **Reporter**: `log.html` and `report.html` in `./results`
- **Screenshots**: Auto-captured on any keyword failure by `SeleniumLibrary run_on_failure=Capture Page Screenshot` (default). Do NOT add screenshot calls in `Test Teardown` or normal test steps — it creates duplicate screenshots.

### Naming Conventions

#### File Naming — `underscore_case` Only
All `.robot` and `.resource` files MUST use lowercase `underscore_case`. Never use spaces, hyphens, or camelCase.

| File type | Convention | Examples |
|---|---|---|
| Test suite | `<feature>_<scenario>.robot` | `auth_login.robot`, `transfer_deposit.robot` |
| Keyword resource | `<feature>_keywords.resource` | `auth_keywords.resource` |
| Variables resource | `<feature>_variables.resource` | `auth_variables.resource` |
| Common | `common_keywords.resource` | `common_keywords.resource` |
| Imports | `imports.resource` | `imports.resource` |
| Test data | `<feature>.yaml` | `auth.yaml`, `transfer.yaml` |

#### Test Case Names
`Snake_Case_With_Capitalization` — e.g., `User_Can_Login_With_Valid_Credentials`

#### Keyword Names — `<Noun> - <Verb> <Object>`
**The prefix MUST be a noun** — it represents the module/feature name (e.g., `Auth`, `Transfer`, `Common`). Think of it as the "class name" of the keyword.

```
Auth - Login With Credentials       ✅  noun prefix
Transfer - Select Money Source      ✅  noun prefix
Common - Click Element              ✅  noun prefix
Do Transfer - Select Source         ❌  verb prefix — wrong
Handle Auth - Login                 ❌  verb prefix — wrong
```

The entire keyword name uses **spaces only** — never underscores in any part (prefix or action):

```
Product Listing Page By Category - Dismiss Welcome Modal   ✅  spaces throughout
Product Listing Page By Category - Dismiss_Welcome_Modal   ❌  underscore in action — wrong
Auth - Login_With_Credentials                              ❌  underscore in action — wrong
```

Recommended verbs for the action part:

| Verb | When to use |
|---|---|
| `Open` | Navigate to a screen/page |
| `Close` | Close a screen/dialog/app |
| `Click` | Tap/click an element |
| `Input` | Enter text into a field |
| `Select` | Choose from a list/dropdown |
| `Verify` | Assert that something is true |
| `Get` | Retrieve a value |
| `Wait` | Wait for a condition |
| `Handle` | Deal with a popup/dialog |
| `Navigate` | Move between screens |

#### Variable Names (Locators) — Type Prefix Required
All locator and UI-related variables MUST include a type prefix.

| Prefix | Element type | Example |
|---|---|---|
| `btn_` | Button | `${btn_confirm}`, `${btn_login}` |
| `inp_` | Input field | `${inp_amount}`, `${inp_username}` |
| `lbl_` | Label / static text | `${lbl_balance}`, `${lbl_error}` |
| `txt_` | Expected text value | `${txt_success}`, `${txt_welcome}` |
| `icon_` | Icon element | `${icon_loading}`, `${icon_back}` |
| `sw_` | Switch / toggle | `${sw_notification}`, `${sw_dark_mode}` |
| `tab_` | Tab element | `${tab_transfer}`, `${tab_history}` |
| `menu_` | Menu item | `${menu_settings}`, `${menu_transfer}` |

```robotframework
# Wrong — type unclear
${confirm}         id=btn_confirm
${amount}          id=edt_amount
${success_text}    Transaction successful

# Correct — type is clear from prefix
${btn_confirm}     id=btn_confirm
${inp_amount}      id=edt_amount
${txt_success}     Transaction successful
```

### Formatting — `robotframework-tidy`

**Always format `.robot` and `.resource` files with `robotframework-tidy` after every write, before running tests and before committing.**

```bash
pip install robotframework-tidy    # one-time install

python -m robotidy automation_test/features/auth/auth_keywords.resource    # if robottidy is not on PATH
python -m robotidy automation_test/tests/login.robot
python -m robotidy automation_test/features/          # format entire directory
```

`robotframework-tidy` enforces 4-space indentation, consistent column alignment, and standard section ordering automatically.

---

## 2. Locator Strategy (Priority Order)

Always choose locators in this priority order:

### Priority 1: Custom Test IDs (Most Preferred)
```robotframework
${btn_book_now}    css=[data-testid='book-now-btn']
# Shorthand syntax (equivalent):
${btn_book_now}    data=testid:book-now-btn
```
Ask developers to add `data-testid` attributes for stable test hooks.

### Priority 2: IDs
```robotframework
${btn_login}       id=login-btn
```

### Priority 3: Name
```robotframework
${inp_email}     name=email
${inp_phone}     name=phone
```

### Priority 4: Class Name
```robotframework
${btn_submit}    class=submit-btn
${lbl_error}     class=error-message
```
Use only when a single, stable CSS class identifies the element uniquely. `class=` matches one class name — for multiple classes use CSS (Priority 5).

### Angular Component Tags vs Rendered DOM

Angular component tags in source code (`<app-product-card>`) may NOT match the rendered HTML. The browser renders them as `<article>`, `<div>`, `<li>`, etc. with custom CSS classes. Always inspect the **rendered** DOM — not the Angular template.

```robotframework
# BAD — assumes component tag is the CSS selector
${lbl_product_item}    css=app-product-card    # may render as <article class="card3">

# GOOD — use the actual rendered element's selector from DevTools
${lbl_product_item}    css=article.card3

# When uncertain, mark for verification after first run
${lbl_product_item}    css=app-product-card    # TODO: verify rendered tag in log.html
```

### Priority 4.5: Link Text (for `<a>` anchor elements only)
```robotframework
# Exact link text — simpler than XPath text-match for real anchor links
${lnk_home}        link=Home
${lnk_more}        partial link=View more
```

> ⚠️ **SPA caveat — verify element tag before using `link=`.**
> `link=` and `partial link=` **only match `<a>` elements**. Modern SPAs (Angular, React, Vue) frequently render navigation controls as `<span role="button">`, `<button>`, or `<div>` — none of which `link=` can find, and it will fail silently or raise `ElementNotFound`.
>
> **Always check the element's HTML tag in DevTools (F12) before choosing `link=`.**
> If the element is NOT an `<a>`, use XPath text-match or CSS:
> ```robotframework
> # When "Home" is a <span role="button"> (common in Angular SPAs)
> ${btn_breadcrumb_home}    xpath=//nav[contains(@class,'breadcrumb')]//span[normalize-space()='Home']
> # Or by role attribute:
> ${btn_nav_home}           css=nav [role="button"]
> ```

### Priority 5: CSS Selectors
```robotframework
${btn_confirm}     css=.confirm-booking-btn
# Attribute matching:
${btn_submit}      css=button[type="submit"]
${item_first}      css=[id^="item_"]          # starts with
${item_active}     css=[class~="active"]      # word in class list
${row_nth}         css=table tbody tr:nth-child(2)
${li_not_disabled} css=li:not(.disabled)
```
Use when class name alone (Priority 4) is not unique enough, or when combining multiple attributes.

### Priority 6: XPath (Last Resort)
```robotframework
${btn_submit}      //div[@class='card']//button[contains(text(), 'Submit')]
${inp_user}        //label[text()='Username']/following-sibling::input
${card_item}       //span[text()='${title}']/ancestor::div[@data-testid='event-card']
```
Use for complex DOM traversals that CSS cannot express. Always use **relative** paths (`//`), keep them as short as possible.

**Absolute XPath is forbidden** except in special circumstances where no other strategy works (e.g., deeply nested shadow DOM, third-party widgets with no stable attributes). When absolutely necessary, add a comment explaining why:
```robotframework
${btn_widget}    xpath=/html/body/div[2]/iframe/body/button    # third-party chat widget — no accessible attributes, no testid
```

### Avoid
- Index-only selectors without filtering: `css=ul li:nth-child(3)` (fragile to list reordering)

### Verify Locators Before Using

**Write best-effort locators using the priority order, then validate by running the test.** The test run (Step 3) is the locator validation step — `log.html` screenshots show exactly what the browser rendered at each failing step.

How to write initial locators:
- Follow the priority order strictly: `data-testid` > `id` > `name` > `class` > CSS > XPath
- Derive from domain docs and `detail-design.md` when available
- For unknown elements, use semantic patterns (`css=.breadcrumb`, `id=btn-login`) as candidates
- Mark uncertain locators `# TODO: verify in log.html` as a signal to check after first run

How to validate after a failure:
- Open `automation_test/results/log.html` — the failure screenshot shows exactly what was rendered
- Use browser DevTools (F12) to test the selector against the live DOM
- Confirm the locator returns exactly 1 element with `Get Element Count` if needed

```robotframework
# Confirm a CSS selector uniquely matches
${count}=    Get Element Count    css=button.submit
Should Be Equal As Integers    ${count}    1
```

A broad `contains(text(), ...)`/`contains(@class, ...)` XPath can also match persistent chrome that's on every page — header, nav, footer, cookie banner — not just the content area under test. Matching *something* (confirmed live via DOM inspection, or via RobotMCP's `get_session_state` in `.claude/skills/autotest-mcp-assist/SKILL.md`) is not the same as matching the *right* thing — a test can PASS while asserting against a decoy element outside the actual result/content container. `Get Element Count` catches "matches more than one," but not "matches the wrong one" — for text-based assertions, scope the XPath to the specific content container, not the whole page.

If DOM contradicts the spec → report a potential app bug. Do NOT silently adapt the test to buggy behavior.

---

## 3. Filtering and Scoping Patterns

### Scope actions to a parent
```robotframework
Click Element    css=[data-testid='event-card']:has-text('${title}') [data-testid='book-now-btn']
```

### Iterate through elements (strictly when necessary)
```robotframework
${cards}=    Get WebElements    css=[data-testid='event-card']
FOR    ${card}    IN    @{cards}
    ${text}=    Get Text    ${card}
    Run Keyword If    '${title}' in '${text}'    Click Element    ${card}
END
```

---

## 4. Assertion Patterns

### Visibility Checks
```robotframework
Wait Until Element Is Visible    ${txt_success}    timeout=${TIMEOUT_MIN}
Page Should Not Contain Element  ${alert_banner}
```

### URL Assertions
```robotframework
Location Should Be                   ${BASE_URL}/dashboard
Location Should Contain              /events/
Wait Until Location Contains         /dashboard             timeout=${TIMEOUT_DEFAULT}
Wait Until Location Is               ${BASE_URL}/success    timeout=${TIMEOUT_DEFAULT}    # exact match

# Negative URL assertion — "Location Should Not Contain" does NOT exist in SeleniumLibrary.
# Use this pattern instead:
${location}=    Get Location
Should Not Contain    ${location}    /old-path/
```

### Content Assertions
```robotframework
Element Text Should Be    ${lbl_status}    Eligible for refund
Element Should Contain    ${card_booking}    ${event_title}
Page Should Contain       ${txt_welcome}
Page Should Not Contain   ${txt_error_msg}
Title Should Be           Freso - Home
Title Should Contain      Freso
```

### Always Assert After Every Important Action
A test without assertions always passes but proves nothing. Every significant action MUST be followed by at least one verification step.

```robotframework
# Wrong — no assertion
Auth - Click Login Button

# Correct — assert the outcome
Auth - Click Login Button
Common - Wait For Element Visible    ${lbl_dashboard}
```

---

## 5. Project Structure & Feature Object Model

The framework uses a **Feature Object Model (FOM)** — organized by feature/domain with strict separation of locators and actions.

### Project Layout

```
automation_test/tests/                              # .robot test suites only
automation_test/features/                           # keywords & variables per feature
  auth/
    auth_keywords.resource
    auth_variables.resource
  product/
    product_keywords.resource
    product_variables.resource
automation_test/common/
  common_keywords.resource          # 9 standard wrappers + app-level flows
  common_variables.resource         # ${TIMEOUT_MIN}, ${TIMEOUT_DEFAULT}, ${TIMEOUT_MAX}, ${BROWSER}
automation_test/config/
  imports.resource                  # Libraries + keyword files ONLY
automation_test/data/                               # YAML test data, one file per feature
  auth.yaml
  product.yaml
automation_test/results/                            # gitignored
automation_test/python_lib/                         # custom Python libraries (optional)
```

> For large projects with many features, group under category folders:
> `automation_test/features/account_services/login/`, `automation_test/features/transfer_services/deposit/`

### File Size Limits

Keep files small and focused. If a file exceeds the limit, split by sub-feature.

| File type | Limit | Action when exceeded |
|---|---|---|
| `*_keywords.resource` | ≤ 300 lines | Split into sub-feature folders |
| `*_variables.resource` | ≤ 150 lines | Move shared vars to `common_variables.resource` |
| `*.robot` | ≤ 200 lines | Split into separate files by scenario group |

### Centralized Imports

`automation_test/config/imports.resource` declares **Libraries + all keyword files** (common + every feature). Test files import only this one file plus their YAML data.

```robotframework
# automation_test/config/imports.resource — Libraries + ALL keyword files
*** Settings ***
Library     SeleniumLibrary    timeout=30s
Library     OperatingSystem
Library     Collections
Library     yaml

Resource    ../common/common_keywords.resource
Resource    ../features/auth/auth_keywords.resource
Resource    ../features/product/product_keywords.resource
# Add a new Resource line here whenever a new feature is created
```

Each keyword file imports `automation_test/config/imports.resource` back (for libraries) and its own variables file. RF ignores duplicate imports — circular references are safe.

```robotframework
# automation_test/common/common_keywords.resource
*** Settings ***
Resource    ../config/imports.resource
Resource    common_variables.resource
```

```robotframework
# automation_test/features/auth/auth_keywords.resource
*** Settings ***
Resource    ../../config/imports.resource
Resource    auth_variables.resource

*** Keywords ***
Auth - Login With Credentials
    [Arguments]    ${username}    ${password}
    Common - Input Text       ${inp_username}    ${username}
    Common - Input Text       ${inp_password}    ${password}
    Common - Click Element    ${btn_login}
```

Test files are minimal — one Resource + one Variables:

```robotframework
# automation_test/tests/auth.robot
*** Settings ***
Resource     ../config/imports.resource
Variables    ../data/auth.yaml
```

Variable files (`_variables.resource`) are the only files with no imports — they declare locators only.

### Feature Object Model (Strict Separation)

Each feature has exactly two files in its own folder under `automation_test/features/`:

**1. Variables File — Locators only (no imports needed)**
```robotframework
# automation_test/features/auth/auth_variables.resource
*** Variables ***
${inp_username}    id=username
${inp_password}    id=password
${btn_login}       css=button[type='submit']
${lbl_dashboard}   css=.dashboard-title
```

**2. Keywords File — Actions only, using Common wrappers**
```robotframework
# automation_test/features/auth/auth_keywords.resource
*** Settings ***
Resource    ../../config/imports.resource    # libraries
Resource    auth_variables.resource          # locators

*** Keywords ***
Auth - Login With Credentials
    [Arguments]    ${username}    ${password}
    Common - Input Text       ${inp_username}    ${username}
    Common - Input Text       ${inp_password}    ${password}
    Common - Click Element    ${btn_login}

Auth - Verify Login Success
    Common - Wait For Element Visible    ${lbl_dashboard}
```

### Cross-Feature Composite Keywords
When a keyword aggregates actions across multiple features, place it in the `_keywords.resource` of the **final destination feature**.

```robotframework
# Correct — login + navigate to product lands on product page → place in product_keywords.resource
Product - Login And Go To Product Listing
    Auth - Login With Credentials    ${USER}    ${PASS}
    Common - Wait For Element Visible    ${lbl_product_page}
```

### The "Common" Boundary Rule (STRICT)
- `common_variables.resource` — ONLY global config (`${TIMEOUT_MIN}`, `${TIMEOUT_DEFAULT}`, `${TIMEOUT_MAX}`, `${BROWSER}`) or system-wide elements (global spinner, toast). **NEVER** feature-specific locators.
- `common_keywords.resource` — ONLY the 9 standard wrappers and universal setup/teardown. **NEVER** feature-specific flows or navigations.

### Keyword Size Limit — ≤ 20 Lines
A keyword must not exceed 20 lines of steps. If it does, split into focused sub-keywords.

```robotframework
# Wrong — 25+ lines, too many responsibilities
Auth - Complete Registration Flow
    ...20+ lines...

# Correct — split into focused sub-keywords
Auth - Fill Registration Form
    [Arguments]    ${name}    ${email}    ${password}
    Common - Input Text    ${inp_name}      ${name}
    Common - Input Text    ${inp_email}     ${email}
    Common - Input Text    ${inp_password}  ${password}

Auth - Submit And Verify Registration
    Common - Click Element               ${btn_register}
    Common - Wait For Element Visible    ${lbl_success}
```

### Keyword Name Must Match Implementation
**If the implementation changes, rename the keyword immediately.** A mismatch between name and behavior causes bugs.

```robotframework
# Wrong — name says "Login" but also navigates to product page
Auth - Login
    ...login steps...
    Common - Click Element    ${mnu_product}    # does more than login

# Correct — rename to reflect full action
Auth - Login And Go To Product
    ...login steps...
    Common - Click Element    ${mnu_product}
```

### Unused Variable / Keyword / Argument Rule
**Delete everything that is not used.** If a variable, keyword, or argument is declared but never referenced, remove it.

### Clean Up Temporary Files
Delete all draft files, debug keywords, temp variables, and commented-out code once the implementation is complete.

### Strict DRY Principle
Zero duplication. If a sequence of steps is identical or nearly identical in more than one place, extract it into a shared keyword immediately.

### Meaningful Keyword Abstraction (Two-Step Minimum Rule)
A custom keyword MUST contain at least two underlying keyword calls. Do NOT create thin wrappers that execute only a single built-in keyword.

---

## 6. Common Wrappers — 9 Standard Keywords

**NEVER** use raw SeleniumLibrary keywords (`Click Element`, `Input Text`, `Mouse Over`) directly inside feature keyword files. Always use the Common wrappers.

`common_keywords.resource` MUST contain at minimum these 9 keywords:

```robotframework
# Import common_variables.resource directly — NOT automation_test/config/imports.resource (circular)
*** Settings ***
Resource    common_variables.resource

*** Keywords ***
Common - Open Web
    [Arguments]    ${url}    ${browser}=${BROWSER}
    Open Browser    ${url}    ${browser}
    Maximize Browser Window

Common - Close Web
    Close All Browsers

Common - Wait For Element Visible
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_DEFAULT}
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}

Common - Input Text
    [Arguments]    ${locator}    ${text}    ${timeout}=${TIMEOUT_DEFAULT}
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Clear Element Text    ${locator}
    Input Text    ${locator}    ${text}

Common - Click Element
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_DEFAULT}
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Click Element    ${locator}

Common - Click Element If Exists
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_MIN}
    ${visible}=    Run Keyword And Return Status
    ...    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    IF    ${visible}    Click Element    ${locator}

Common - Get Text
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_DEFAULT}
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    ${text}=    Get Text    ${locator}
    RETURN    ${text}

Common - Mouse Over
    [Arguments]    ${locator}    ${timeout}=${TIMEOUT_DEFAULT}
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Mouse Over    ${locator}

Common - Scroll Into View
    [Arguments]    ${locator}
    ${element}=    Get WebElement    ${locator}
    Execute JavaScript    arguments[0].scrollIntoView({block: 'center'})    ARGUMENTS    ${element}
```

**Usage in feature keywords:**
```robotframework
# DO — use Common wrappers
Auth - Login With Credentials
    [Arguments]    ${username}    ${password}
    Common - Input Text       ${inp_username}    ${username}
    Common - Input Text       ${inp_password}    ${password}
    Common - Click Element    ${btn_login}

# DON'T — raw Selenium bypasses wait handling
Auth - Login With Credentials
    Input Text      ${inp_username}    ${username}   # BAD
    Click Element   ${btn_login}                      # BAD
```

---

## 7. Timeout Variable Rule

**Never hardcode timeout values directly in keyword calls.** Declare the three standard timeout variables in `common_variables.resource` and reference them everywhere.

```robotframework
# Wrong — hardcoded timeout values
Wait Until Element Is Visible    ${btn_submit}    timeout=10s
Wait Until Page Contains         ${txt_welcome}   timeout=30s

# Correct — use named timeout variables
*** Variables ***
${TIMEOUT_MIN}        3s
${TIMEOUT_DEFAULT}    10s
${TIMEOUT_MAX}        30s

*** Keywords ***
Auth - Login With Credentials
    Common - Click Element               ${btn_login}                           # uses ${TIMEOUT_DEFAULT}
    Common - Wait For Element Visible    ${lbl_dashboard}    ${TIMEOUT_MAX}    # slow page load
    Common - Click Element If Exists     ${btn_popup_close}  ${TIMEOUT_MIN}    # fast optional check
```

| Variable | Value | When to use |
|---|---|---|
| `${TIMEOUT_MIN}` | 3s | Optional elements, quick checks |
| `${TIMEOUT_DEFAULT}` | 10s | Standard elements (default) |
| `${TIMEOUT_MAX}` | 30s | Slow pages, file uploads, heavy operations |

---

## 8. Locator and Text Variable Rule

**Never hardcode locators or UI text strings directly in keyword calls.** All locators and text values MUST be declared as variables in `*** Variables ***` before use.

```robotframework
# Wrong — inline hardcoded locator and text
Click Element       xpath=//button[@type='submit']
Wait Until Page Contains    Transaction successful

# Correct — declared as variables
*** Variables ***
${btn_submit}        xpath=//button[@type='submit']
${txt_success}       Transaction successful

*** Keywords ***
Auth - Submit And Verify
    Common - Click Element               ${btn_submit}
    Common - Wait For Element Visible    ${txt_success}
```

This rule applies to ALL strings used as locators or expected text — XPath, CSS, text content, and attribute values.

---

## 9. Screenshot Rule

SeleniumLibrary's default `run_on_failure=Capture Page Screenshot` **automatically captures a screenshot the moment any keyword fails** — no code needed. Do NOT add `Capture Page Screenshot` to `Test Teardown`; it creates a redundant second screenshot.

```robotframework
# Correct — teardown only closes the browser; run_on_failure handles screenshots
Test Teardown    Common - Close Web

# Correct — explicit debug capture with a meaningful filename
Capture Page Screenshot    ${OUTPUT_DIR}/debug_${TEST_NAME}.png

# Wrong — redundant with run_on_failure (creates a duplicate screenshot)
Test Teardown    Run Keywords
...    Run Keyword If Test Failed    Capture Page Screenshot    # REMOVE THIS LINE
...    AND    Common - Close Web

# Wrong — screenshot after every action (slow, noisy)
Common - Click Element    ${btn_submit}
Capture Page Screenshot    # remove this
```

Screenshots land in `automation_test/results/` as `selenium-screenshot-N.png`. **The AI can read these PNG files directly** — this is faster than opening `log.html` when diagnosing failures.

---

## 10. Coordinate Click Rule

**Avoid clicking by coordinates.** Priority order:

1. **Locator-based** (always preferred) — `id`, `css`, `data-testid`, `xpath`
2. **Percentage-based** — use when no locator is available; calculate relative to viewport size
3. **Absolute x/y** — last resort only; MUST add a comment explaining why

```robotframework
# Best — locator-based
Common - Click Element    ${btn_confirm}

# Acceptable when no locator exists — percentage-based
${width}=     Execute JavaScript    return window.innerWidth
${height}=    Execute JavaScript    return window.innerHeight
${x}=         Evaluate    int(${width} * 0.5)
${y}=         Evaluate    int(${height} * 0.9)
Click Element At Coordinates    ${x}    ${y}

# Last resort — absolute coordinates (must add comment)
# Canvas element, no DOM locator available for this drawing tool
Click Element At Coordinates    640    480
```

---

## 11. Wait Strategies

### DO: Use Common wrappers and explicit waits
```robotframework
Common - Click Element               ${btn_submit}
Common - Wait For Element Visible    ${txt_success}
Wait Until Element Is Not Visible    ${spinner}    timeout=${TIMEOUT_MAX}
```

### DO: Custom timeout for slow elements
```robotframework
Common - Wait For Element Visible    ${btn_confirm}    ${TIMEOUT_MAX}
```

### DO: Wait for DOM presence (element in DOM but not Selenium-visible)

Some elements — PrimeNG/Angular Material dialog close buttons, CSS-hidden tooltips, off-screen drawers — exist in the DOM but have `visible=False` in Selenium. `Wait Until Element Is Visible` will time out even though the element is there.

Use `Wait Until Page Contains Element` (DOM presence check) and interact via JavaScript:

```robotframework
# Pattern: modal close button that is in DOM but CSS-hidden
${present}=    Run Keyword And Return Status
...    Wait Until Page Contains Element    css=button.p-dialog-close-button    timeout=${TIMEOUT_DEFAULT}
IF    ${present}
    Execute JavaScript    document.querySelector('button.p-dialog-close-button').click()
    Wait Until Element Is Not Visible    css=div.p-dialog-mask    timeout=${TIMEOUT_DEFAULT}
END
```

| Keyword | Checks |
|---|---|
| `Wait Until Element Is Visible` | DOM + computed CSS (display, visibility, opacity, size) |
| `Wait Until Page Contains Element` | DOM only — passes even if element is CSS-hidden |

Use DOM-presence check when you know the element exists but its style is `display:none` or `visibility:hidden`.

### DO: Wait for loading spinner / AJAX
```robotframework
Click Element    ${btn_load_data}
Wait Until Element Is Not Visible    css=.loading-spinner    timeout=${TIMEOUT_MAX}
Wait Until Element Is Visible        ${tbl_results}          timeout=${TIMEOUT_DEFAULT}
```

### DO: Wait for element count (list/table results)
```robotframework
# Wait for at least 1 item to appear
Wait Until Element Count Is Greater Than    css=.product-card    0    timeout=${TIMEOUT_DEFAULT}

# Wait for exact count
Wait Until Element Count Is    css=table tbody tr    5    timeout=${TIMEOUT_DEFAULT}

# Wait for count to drop (after delete)
Wait Until Element Count Is Less Than    css=.item    10    timeout=${TIMEOUT_DEFAULT}
```

### DO: Wait for text within element
```robotframework
Wait Until Element Contains        ${lbl_status}    Completed    timeout=${TIMEOUT_MAX}
Wait Until Element Does Not Contain    ${lbl_status}    Processing    timeout=${TIMEOUT_MAX}
```

### DO: Wait for exact URL
```robotframework
Wait Until Location Is         ${BASE_URL}/dashboard    timeout=${TIMEOUT_DEFAULT}
Wait Until Location Contains   /buyer/                  timeout=${TIMEOUT_DEFAULT}
```

### DO: Wait for URL to leave the current path (negative URL wait)

SeleniumLibrary has no `Wait Until Location Does Not Contain`. Use `Wait Until Keyword Succeeds` with a helper keyword:

```robotframework
# In the keyword file — wait until we're no longer on the category page
Product - Verify Left Category Page
    Wait Until Keyword Succeeds    ${TIMEOUT_DEFAULT}    500ms    URL Left Category Page

URL Left Category Page
    ${loc}=    Get Location
    Should Not Contain    ${loc}    /category/
```

> ⚠️ **Trivially-true assertion trap:** `Wait Until Location Contains /fragment/` passes **instantly** if the starting URL already contains `/fragment/`. This is a silent logic bug — the test always passes regardless of whether navigation happened.
>
> **Rule:** Only use `Wait Until Location Contains X` if `X` is NOT present in the URL before the action. When in doubt, use the negative wait pattern above, or wait for a landmark element on the destination page instead.

```robotframework
# BAD — starting URL http://example.com/app/products/list already contains /app/
Wait Until Location Contains    /app/    timeout=${TIMEOUT_DEFAULT}    # passes immediately — proves nothing

# GOOD — /dashboard/ is NOT in the starting URL
Wait Until Location Contains    /dashboard/    timeout=${TIMEOUT_DEFAULT}

# GOOD — negative wait: confirm URL left the products page
Wait Until Keyword Succeeds    ${TIMEOUT_DEFAULT}    500ms    Left Products Page

Left Products Page
    ${loc}=    Get Location
    Should Not Contain    ${loc}    /products/
```

### DO: `Wait Until Keyword Succeeds` for custom conditions
```robotframework
Wait Until Keyword Succeeds    5x    1s    Element Should Be Visible    ${lbl_loaded}
Wait Until Keyword Succeeds    30s    2s    Element Text Should Be    ${lbl_status}    Complete
```

### DON'T: Use Sleep
```robotframework
Sleep    5s    # BAD — flaky, wastes time
```

### DON'T: Override global timeout
```robotframework
Set Selenium Timeout         10s    # BAD
Set Selenium Implicit Wait   5s     # BAD
```

### Exception: Testing timed UI
```robotframework
# OK when verifying a loading state appears then disappears
Wait Until Element Is Visible      ${spinner}
Wait Until Element Is Not Visible  ${spinner}    timeout=${TIMEOUT_MAX}
```

---

## 12. Test Case Standards

### Suite / Test Lifecycle — Browser Per Test

Browser lifecycle is managed **per test**, not per suite. Each test opens a fresh browser in `Test Setup` and closes it in `Test Teardown`. This guarantees full isolation — no shared state between tests.

```robotframework
*** Settings ***
Resource     ../config/imports.resource    # all libraries + all keyword files
Variables    ../data/auth.yaml             # loads ${data} dict at parse time — no Suite Setup needed

Test Setup        Auth - Open Login Page   # opens fresh browser per test
Test Teardown     Common - Close Web
```

Feature keyword called from `Test Setup` always uses `Common - Open Web`:

```robotframework
Auth - Open Login Page
    Common - Open Web    ${URL_LOGIN}
    Common - Wait For Element Visible    ${inp_username}
```

| Hook | Runs | Purpose |
|---|---|---|
| `Suite Setup` | Once before all tests | Non-browser only: load YAML data, prepare API state |
| `Suite Teardown` | Once after all tests | Non-browser cleanup; omit if nothing to do |
| `Test Setup` | Before each test | Open fresh browser + navigate to the feature page |
| `Test Teardown` | After each test | Close browser (`run_on_failure` handles screenshots automatically) |

**Rules:**
- `Common - Open Web` is called inside the feature's `Open Page` keyword, which is called from `Test Setup`.
- `Common - Close Web` is always called in `Test Teardown` — even when the test passes.
- `Suite Setup` and `Suite Teardown` are for non-browser operations only (YAML load, API calls, variables). Never open or close a browser there.

### Tags — Required on Every Test Case
```robotframework
*** Test Cases ***
User_Can_Login_With_Valid_Credentials
    [Tags]    auth    login    smoke
    [Documentation]    Verify successful login redirects to dashboard.
    Auth - Login With Credentials    ${USER}    ${PASS}
    Auth - Verify Login Success
```

**Recommended tag conventions:**

| Tag | Purpose |
|---|---|
| `smoke` | Critical path — run on every build |
| `regression` | Full regression suite |
| `<feature>` | Feature name: `auth`, `product`, `order` |
| `wip` | Work in progress — skip in CI |

### One Keyword Per Test Case

Each test case body contains **exactly one keyword call**, which receives the test-specific data dict. All steps live inside the called keyword.

```robotframework
# automation_test/tests/auth.robot
*** Test Cases ***
User_Can_Login_With_Valid_Credentials
    [Tags]    auth    smoke
    Auth - Login With Valid Credentials    ${data["${TEST_NAME}"]}

User_Cannot_Login_With_Wrong_Password
    [Tags]    auth    regression
    Auth - Login With Wrong Password    ${data["${TEST_NAME}"]}
```

```robotframework
# automation_test/features/auth/auth_keywords.resource — scenario keywords (one per TC)
Auth - Login With Valid Credentials
    [Arguments]    ${td}
    Auth - Fill Login Form    ${td}[username]    ${td}[password]
    Auth - Verify Login Success

Auth - Login With Wrong Password
    [Arguments]    ${td}
    Auth - Fill Login Form    ${td}[username]    ${td}[password]
    Auth - Verify Error Message    ${td}[expected_error]
```

The test case name resolves at runtime into `${data["${TEST_NAME}"]}`, returning the per-test dict from the YAML.

### Tests Must Be Self-Contained
Every test sets up its own state from scratch. Never rely on state left by a previous test.

### Control Flow (`FOR`, `IF`) Belongs in Keywords
Do NOT put control flow structures directly in test cases. Move them into a keyword.

```robotframework
# Wrong — IF in test case
User_Can_Select_Category
    IF    ${category} == 'food'    Product - Click Food Tab
    ELSE    Product - Click Other Tab

# Correct — move to keyword
User_Can_Select_Category
    Product - Select Category Tab    ${category}
```

---

## 13. YAML Test Data

Store test data in `automation_test/data/<feature>.yaml` — one file per feature. The YAML must have a top-level `data:` key; each child key is the exact test case name.

```yaml
# automation_test/data/auth.yaml
data:
  User_Can_Login_With_Valid_Credentials:
    username: "testuser@example.com"
    password: "Test@1234"

  User_Cannot_Login_With_Wrong_Password:
    username: "testuser@example.com"
    password: "wrongpass"
    expected_error: "Invalid credentials"
```

Import via `Variables` in the test file — no `Suite Setup` needed. RF parses the YAML at load time and creates `${data}` as a dict.

```robotframework
# automation_test/tests/auth.robot
*** Settings ***
Resource     ../config/imports.resource    # all libraries + all keyword files
Variables    ../data/auth.yaml             # creates ${data} dict

Test Setup        Auth - Open Login Page
Test Teardown     Common - Close Web

*** Test Cases ***
User_Can_Login_With_Valid_Credentials
    [Tags]    auth    smoke
    Auth - Login With Valid Credentials    ${data["${TEST_NAME}"]}

User_Cannot_Login_With_Wrong_Password
    [Tags]    auth    regression
    Auth - Login With Wrong Password    ${data["${TEST_NAME}"]}
```

`${data["${TEST_NAME}"]}` resolves at runtime: `${TEST_NAME}` expands first, then the dict lookup returns the per-test sub-dict.

```robotframework
# Scenario keyword receives the data dict
Auth - Login With Valid Credentials
    [Arguments]    ${td}
    Auth - Fill Login Form    ${td}[username]    ${td}[password]
    Auth - Verify Login Success
```

**Rules:**
- Top-level key MUST be `data:` — RF imports this as `${data}`
- Child keys must match test case names **exactly** (spaces and case-sensitive)
- One YAML file per feature
- Never store passwords/tokens in YAML — use environment variables

---

## 14. Advanced Patterns

### `Run Keyword And Return Status` vs `Run Keyword And Ignore Error`

| | `Run Keyword And Return Status` | `Run Keyword And Ignore Error` |
|---|---|---|
| Returns | `${True}` / `${False}` | Tuple: `('PASS'/'FAIL', value)` |
| Use when | You need to branch on pass/fail | Step is optional, result doesn't matter |

```robotframework
# Return Status — use when you need to branch
${is_visible}=    Run Keyword And Return Status
...    Wait Until Element Is Visible    ${btn_popup_close}    timeout=${TIMEOUT_MIN}
IF    ${is_visible}    Common - Click Element    ${btn_popup_close}

# Ignore Error — use when step is optional
Run Keyword And Ignore Error    Common - Click Element    ${btn_skip_tutorial}
```

**Rule:** If you write `Run Keyword And Ignore Error` followed by code that depends on the outcome → switch to `Run Keyword And Return Status` with an `IF` block.

### Verifying Active / Selected State

Active state varies by UI library — **never assume `aria-selected`**. Always inspect the actual DOM attribute.

| Library | Common active state |
|---|---|
| PrimeNG (Angular) | `class*="active"` or custom class |
| Angular Material | `aria-selected="true"` on `mat-tab-label` |
| Tailwind / custom | `class*="active"`, `class*="selected"`, or `data-*` attribute |

```robotframework
# BAD — assumes aria-selected (wrong for many Angular/PrimeNG apps)
Common - Wait For Element Visible
...    xpath=//button[@aria-selected='true' and normalize-space()='${tab_name}']

# GOOD — use actual active class confirmed from DOM inspection
Common - Wait For Element Visible
...    xpath=//button[contains(@class,'filter-button') and normalize-space()='${tab_name}' and contains(@class,'active')]
```

When writing a new `Verify Tab Active` keyword, mark the active attribute `# TODO: verify active class/attr` and confirm from the screenshot after the first run.

### Hover / Mouse Over
Use `Common - Mouse Over` for elements that only appear on hover (dropdown menus, tooltips, hover cards).
```robotframework
Product - Hover Over Card And Click Action
    Common - Mouse Over    ${card_product}
    Common - Wait For Element Visible    ${btn_quick_view}    ${TIMEOUT_MIN}
    Common - Click Element    ${btn_quick_view}
```

### Scroll Into View
Use `Common - Scroll Into View` when an element is off-screen and click/interaction fails with `ElementNotInteractableException` or `MoveTargetOutOfBoundsException`.
```robotframework
Product - Click Out Of Viewport Button
    Common - Scroll Into View    ${btn_load_more}
    Common - Click Element       ${btn_load_more}
```

### Stale Element Reference
When an element reference goes stale after a page update, use the locator directly rather than storing a `Get WebElement` reference across page changes.
```robotframework
# BAD — stale after page re-render
${el}=    Get WebElement    ${btn_save}
Click Element    ${btn_trigger_refresh}
Click Element    ${el}    # StaleElementReferenceException

# GOOD — re-fetch with locator after page change
Click Element    ${btn_trigger_refresh}
Wait Until Element Is Visible    ${btn_save}
Click Element    ${btn_save}    # fresh lookup
```

### `ElementClickInterceptedException` — Element obscured
```robotframework
# Pattern: scroll into view, wait for overlay to close, then click
Wait Until Element Is Not Visible    css=.modal-overlay    timeout=${TIMEOUT_DEFAULT}
Common - Scroll Into View    ${btn_confirm}
Common - Click Element       ${btn_confirm}
```

### Frames / iframes
```robotframework
# Enter frame, interact, always exit
Select Frame      id=payment-frame
Common - Input Text    ${inp_card_number}    ${card}
Unselect Frame    # always return to main document

# Safe frame operation using TRY/FINALLY
TRY
    Select Frame    ${frame_locator}
    Common - Click Element    ${btn_confirm}
FINALLY
    Unselect Frame
END
```

### JavaScript Execution (Last Resort)
Only use JavaScript when SeleniumLibrary keywords are insufficient.

```robotframework
# Scroll element into view (use Common - Scroll Into View wrapper instead)
Execute JavaScript    arguments[0].scrollIntoView({block: 'center'})    ARGUMENTS    ${element}

# Click hidden/overlapped element
${el}=    Get WebElement    ${btn_hidden}
Execute JavaScript    arguments[0].click()    ARGUMENTS    ${el}

# Set input value when Input Text fails (SPA frameworks)
Execute JavaScript    arguments[0].value = arguments[1]    ARGUMENTS    ${el}    ${value}

# Read localStorage (e.g., auth token for API calls in Suite Setup)
${token}=    Execute JavaScript    return localStorage.getItem('auth_token')
```

---

## 15. Environment & Dynamic Data

**CRITICAL: Never hardcode URLs or credentials.** Read from the project's `global-data.md`.

```robotframework
*** Keywords ***
Common - Generate Unique Name
    ${timestamp}=    Get Current Date    result_format=%Y%m%d%H%M%S
    RETURN    Test_${timestamp}
```

---

## 16. Debugging Tips

```robotframework
# Console logging
Log    Created: "${item_name}"    console=True

# Check element state (add this as a debug keyword in the suite when needed)
Log Element State
    [Arguments]    ${locator}
    ${count}=    Get Element Count    ${locator}
    Log    Element count for ${locator}: ${count}    console=True
    IF    ${count} > 0
        ${visible}=    Run Keyword And Return Status    Element Should Be Visible    ${locator}
        ${enabled}=    Run Keyword And Return Status    Element Should Be Enabled    ${locator}
        ${text}=    Get Text    ${locator}
        Log Many    Visible: ${visible}    Enabled: ${enabled}    Text: ${text}    console=True
    END

# Log current URL + title for navigation debugging
${url}=      Get Location
${title}=    Get Title
Log    URL: ${url}, Title: ${title}    console=True
```

```bash
robot -d automation_test/results/ automation_test/tests/auth_login.robot
robot -d automation_test/results/ -t "User_Can_Login_With_Valid_Credentials" automation_test/tests/auth_login.robot
python -c "import webbrowser, os; webbrowser.open('file://' + os.path.abspath('automation_test/results/log.html'))"
```

### ChromeDriver Version Mismatch Fix

If you see `SessionNotCreatedException: ChromeDriver X only supports Chrome Y`:

```bash
# Step 1: Check versions
chromedriver --version
# macOS:   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
# Windows: "C:\Program Files\Google\Chrome\Application\chrome.exe" --version
# Linux:   google-chrome --version

# Step 2: SeleniumLibrary ≥ 6.1 bundles Selenium Manager which auto-downloads the right driver.
# Upgrade first — this often resolves the mismatch automatically:
pip install --upgrade robotframework-seleniumlibrary

# Step 3: If still mismatched, install the matching chromedriver manually:
# Download from: https://googlechromelabs.github.io/chrome-for-testing/
# Match to your Chrome major version (check chrome://version/ in browser)
#
# macOS (Homebrew):   brew install --cask chromedriver
# Windows (choco):    choco install chromedriver
# Linux (apt):        sudo apt-get install -y chromium-chromedriver

# Step 4 (macOS only): Remove Gatekeeper quarantine flag if chromedriver is blocked:
# xattr -d com.apple.quarantine $(which chromedriver)
```

The test will not run until Chrome and ChromeDriver versions match. Fix this before debugging test logic.

---

## 17. Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Do Instead |
|---|---|---|
| Raw Selenium in feature keywords | Bypasses wait handling | Use `Common - Click Element` / `Common - Input Text` |
| `Sleep 5s` | Flaky, wastes time | Use explicit wait keywords |
| Absolute XPath `xpath=/html/body/...` | Breaks on any DOM change | Use relative XPath or `data-testid`. Exception: allowed only when no other strategy works — must add a comment explaining why |
| Hardcoded locator/text inline in steps | Hard to maintain, can't reuse | Declare as `*** Variables ***` |
| Hardcoded timeout values (e.g., `timeout=10s`) | Inconsistent waits | Use `${TIMEOUT_DEFAULT}` etc. |
| Screenshot after every action | Slow, noisy | Only on failure via `Test Teardown` |
| Click by absolute coordinates | Breaks on screen resize | Use locator first; coordinates only as last resort |
| Long procedural test cases (no keywords) | Hard to read and maintain | Abstract into feature keywords |
| Shared state between tests | Order-dependent failures | Each test self-contained with Setup/Teardown |
| Headless browser mode | Hides rendering issues; failure screenshots are blank | Always use headed Chrome |
| Browser open/close in `Suite Setup`/`Suite Teardown` | Tests share browser state → failures cascade | Use `Test Setup`/`Test Teardown` for browser lifecycle |
| Feature keyword imports `automation_test/config/imports.resource` | Creates circular import | Import only the feature's own `_variables.resource` |
| Thin 1-line keyword wrappers | Zero value, clutters framework | Two-step minimum rule |
| `Set Selenium Timeout` / `Set Selenium Implicit Wait` | Overrides centralized config | Use per-keyword `timeout=` param |
| `FOR` / `IF` directly in test cases | Logic belongs in keywords | Move control flow to keyword |
| No `[Tags]` on test cases | Can't filter or group in CI | Tag every test case |
| No assertion after action | Test always passes, proves nothing | Always assert the outcome |
| Unused variables / keywords / arguments | Dead code, confusing | Delete what is not used |
| Draft code left after implementation | Clutters project | Clean up temp files when done |
| Hardcoded test data in test steps | Breaks across environments | Use YAML data files |
| Keyword prefix is a verb (`Do`, `Handle`) | Unclear ownership | Prefix must be a noun (module name) |
| `Location Should Not Contain` | This keyword does NOT exist in SeleniumLibrary | Use `${loc}= Get Location` then `Should Not Contain ${loc} /path/` |
| `Wait Until Location Contains /x/` when starting URL already has `/x/` | Trivially true — passes instantly, proves nothing about navigation | Only wait for a fragment absent from the starting URL; or use negative wait with `Wait Until Keyword Succeeds` |
| `link=Text` on a `<span>` or `<button>` | `link=` only matches `<a>` elements — raises `ElementNotFound` on non-anchors | Check element tag in DevTools; use XPath text-match or CSS `[role="button"]` for SPAs |
| `Run Keyword If Test Failed    Capture Page Screenshot` in teardown | `run_on_failure` already captures on failure — this creates a duplicate screenshot | Remove; keep teardown as just `Common - Close Web` |
| `Mouse Over` directly in feature keywords | Bypasses wait handling | Use `Common - Mouse Over` wrapper |
| Storing `Get WebElement` across page changes | Element goes stale → `StaleElementReferenceException` | Use locator string for re-lookup; only store element reference for immediate use |
| `Wait For Page To Load` | Removed in Selenium 3+; does nothing | Use `Wait Until Element Is Visible` on a page landmark |
| Duplicate wait for element that `Open Page` already waits for | Wastes time, no value | `Open Page` already waits for key element — don't repeat in test body |
| `Wait Until Element Is Visible` for a CSS-hidden element | Element in DOM but `visible=False` (e.g., PrimeNG dialog close button) — keyword always times out | Use `Wait Until Page Contains Element` for DOM presence, then JS click |
| `css=app-product-card` or any Angular component tag without verifying | Angular renders component tags as native HTML (`<article>`, `<div>`) — tag may not match DOM | Inspect the **rendered** HTML in DevTools or screenshot; use the actual element's tag and class |
| `@aria-selected='true'` for active tab locator without checking DOM | Active state varies by library — PrimeNG often uses CSS class `active`, not `aria-selected` | Inspect active element in DOM; use `contains(@class,'active')` or the confirmed attribute |
