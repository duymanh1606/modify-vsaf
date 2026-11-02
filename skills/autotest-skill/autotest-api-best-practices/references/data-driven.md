# Data-Driven API Testing

## YAML File Structure

One YAML file per feature module. Top-level key must be `data:`. Child keys match test case names exactly.

```yaml
# data/user.yaml
data:
  User_Can_Create_Account_With_Valid_Data:
    username: "testuser_valid"
    email: "valid_user@example.com"
    password: "Test@1234"
    role: "user"
    expected_id_field: "id"

  User_Cannot_Create_Account_With_Duplicate_Email:
    username: "testuser_dup"
    email: "valid_user@example.com"    # intentional duplicate
    password: "Test@1234"
    expected_error: "Email already exists"

  User_Cannot_Create_Account_Without_Email:
    username: "testuser_noemail"
    password: "Test@1234"
    expected_status: 400
    expected_field_error: "email"

  User_Can_Update_Profile:
    new_username: "updated_user"
    new_email: "updated@example.com"

  User_Can_Delete_Own_Account:
    username: "delete_me_user"
    email: "delete_me@example.com"
    password: "Test@1234"
```

## Importing YAML in Test Suite

```robotframework
*** Settings ***
Resource    ../config/imports.resource
Variables   ../data/user.yaml
```

The `Variables` file is imported at the suite level. All YAML data is available as `${data}` dict.

## Accessing Test Data

```robotframework
*** Test Cases ***
User_Can_Create_Account_With_Valid_Data
    [Tags]    user    smoke    TC-001
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - Create Account With Valid Data    ${headers}    ${data["${TEST_NAME}"]}
```

`${TEST_NAME}` is a built-in RF variable that resolves to the current test case name at runtime — exactly matching the YAML key.

## Never Repeat Data in Keywords

```robotframework
# Wrong — hardcoded in keyword
User - Create Test Account
    &{body}=    Create Dictionary    username=testuser    email=test@example.com    password=Test@1234
    
# Correct — data comes from YAML via argument
User - Create Account With Valid Data
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary
    ...    username=${td}[username]    email=${td}[email]    password=${td}[password]
    ${response}=    API - POST    ${EP_USER_CREATE}    ${body}    ${headers}    expected_status=201
    API - Assert Field Not Empty    ${response}    id
    Should Be Equal    ${response.json()}[username]    ${td}[username]
    API - Assert Response Time    ${response}
    RETURN    ${response}
```

## Parametrized Tests with Template

For testing the same endpoint with many input variations:

```robotframework
*** Settings ***
Resource    ../config/imports.resource
Variables   ../data/auth.yaml

*** Test Cases ***
Auth_Login_Invalid_Credentials_${case}
    [Tags]    auth    negative
    [Template]    Auth - Login Should Fail
    ...    FOR    ${case}    IN    @{data[login_failures]}
    ${case}[username]    ${case}[password]    ${case}[expected_status]    ${case}[expected_error]

*** Keywords ***
Auth - Login Should Fail
    [Arguments]    ${username}    ${password}    ${expected_status}    ${expected_error}
    &{body}=    Create Dictionary    username=${username}    password=${password}
    ${response}=    API - POST    ${EP_LOGIN}    ${body}    ${headers}    expected_status=${expected_status}
    API - Assert Error Response    ${response}    ${expected_error}
```

```yaml
# data/auth.yaml
data:
  login_failures:
    - username: "nobody@example.com"
      password: "wrongpassword"
      expected_status: 401
      expected_error: "Invalid credentials"
    - username: ""
      password: "Test@1234"
      expected_status: 400
      expected_error: "Username is required"
    - username: "not-an-email"
      password: "Test@1234"
      expected_status: 400
      expected_error: "Invalid email format"
```

## Dynamic Data Generation

When tests need unique values each run (to avoid conflicts), generate dynamically:

```robotframework
User - Generate Unique Email
    ${timestamp}=    Evaluate    int(time.time())    time
    RETURN    testuser_${timestamp}@example.com

User - Generate Test Payload
    [Arguments]    ${td}
    ${email}=    User - Generate Unique Email
    &{body}=    Create Dictionary
    ...    username=${td}[username]_${timestamp}
    ...    email=${email}
    ...    password=${td}[password]
    RETURN    ${body}
```

Prefer using timestamp or random suffix to make username/email unique per run.

## Chained Data — Using IDs Across Keyword Calls

When a test chains create → get → update → delete, carry the ID between steps:

```robotframework
Order - Create And Fulfill Lifecycle
    [Arguments]    ${headers}    ${td}
    # 1. Create order
    &{body}=    Create Dictionary    product_id=${td}[product_id]    quantity=${td}[quantity]
    ${created}=    API - POST    ${EP_ORDER_CREATE}    ${body}    ${headers}    expected_status=201
    ${order_id}=    Set Variable    ${created.json()}[id]
    # 2. Confirm payment
    &{payment}=    Create Dictionary    method=credit_card    amount=${td}[amount]
    API - POST    ${EP_ORDER_PAYMENT}/${order_id}/pay    ${payment}    ${headers}    expected_status=200
    # 3. Get order — verify status updated
    ${order}=    API - GET    ${EP_ORDER_BY_ID}/${order_id}    ${headers}
    API - Assert Field Equals    ${order}    status    paid
    RETURN    ${order_id}
```

## Test Data for Error Cases

Structure negative test data with explicit expectation fields:

```yaml
data:
  User_Cannot_Access_Without_Token:
    endpoint: "/api/v1/users/me"
    expected_status: 401
    expected_error: "Unauthorized"

  User_Cannot_Access_Other_User_Profile:
    target_user_id: "other-user-uuid-here"   # pre-created in env, not created by the test
    expected_status: 403
    expected_error: "Forbidden"

  Order_Cannot_Be_Created_With_Zero_Quantity:
    product_id: "some-product-uuid"
    quantity: 0
    expected_status: 422
    expected_error: "quantity"    # field name that should appear in validation error
```

## Parameterised Data Tips

- Use string type for IDs in YAML — Python may interpret numeric strings as int.
- If a YAML value starts with `{`, wrap it in quotes or use block style to avoid being parsed as a dict.
- Use `${EMPTY}` in Robot Framework for empty string; in YAML use `""` or `~` (null).
- Never store tokens, real passwords, or PII in YAML.

## Test Isolation — Cleanup Patterns

If a test creates data that persists, clean up in teardown:

```robotframework
*** Test Cases ***
User_Can_Create_Account_With_Valid_Data
    [Tags]    user    smoke    TC-001
    [Setup]    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    [Teardown]    User - Delete If Exists    ${headers}    ${CREATED_USER_ID}
    User - Create Account With Valid Data    ${headers}    ${data["${TEST_NAME}"]}

*** Keywords ***
User - Delete If Exists
    [Arguments]    ${headers}    ${user_id}
    ${exists}=    Run Keyword And Return Status
    ...    API - GET    ${EP_USER_BY_ID}/${user_id}    ${headers}    expected_status=200
    IF    ${exists}
        API - DELETE    ${EP_USER_DELETE}/${user_id}    ${headers}    expected_status=204
    END
```

Or prefer a setUp that creates a fresh user and stores ID in a test variable, then teardown deletes it.
