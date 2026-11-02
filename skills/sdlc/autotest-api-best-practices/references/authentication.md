# Authentication Patterns

## Bearer Token (JWT) — Standard Pattern

Most REST APIs use Bearer token authentication. Tokens are obtained via login and attached to every request via the `Authorization` header.

```robotframework
# Suite Setup obtains token once, stores in suite variable
API Test Suite - Suite Setup
    API - Create Session
    ${username}=    Get Environment Variable    API_USERNAME
    ${password}=    Get Environment Variable    API_PASSWORD
    ${token}=    API - Login    ${username}    ${password}
    Set Suite Variable    ${SUITE_TOKEN}    ${token}

# Per test — build auth header, pass to feature keyword
*** Test Cases ***
User_Can_View_Profile
    [Tags]    user    smoke    TC-001
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - Get Profile    ${headers}

# API - Auth Header builds the header dict (from common_keywords.resource)
API - Auth Header
    [Arguments]    ${token}
    &{headers}=    Create Dictionary
    ...    Authorization=Bearer ${token}
    ...    Content-Type=application/json
    ...    Accept=application/json
    RETURN    ${headers}
```

## Token Expiry During Long Test Runs

If token expires mid-run (short-lived tokens), refresh in a keyword:

```robotframework
API - Get Valid Token
    [Arguments]    ${alias}=${SUITE_NAME}
    ${username}=    Get Environment Variable    API_USERNAME
    ${password}=    Get Environment Variable    API_PASSWORD
    ${token}=    API - Login    ${username}    ${password}    alias=${alias}
    RETURN    ${token}
```

Call `API - Get Valid Token` at test start if token TTL < suite duration.

## Basic Authentication

Some APIs (older or internal) use HTTP Basic auth:

```robotframework
# Pass credentials to Create Session
API - Create Session With Basic Auth
    [Arguments]    ${alias}=${SUITE_NAME}
    ${username}=    Get Environment Variable    API_USERNAME
    ${password}=    Get Environment Variable    API_PASSWORD
    Create Session    ${alias}    ${BASE_URL}
    ...    auth=(${username}, ${password})
    ...    verify=${True}    timeout=${TIMEOUT}
    RETURN    ${alias}

# No Authorization header needed per request — session handles it
${response}=    GET On Session    ${alias}    ${path}    expected_status=200
```

## API Key Authentication

### API Key in Header

```robotframework
API - Auth Header With API Key
    [Arguments]    ${api_key}
    &{headers}=    Create Dictionary
    ...    X-API-Key=${api_key}
    ...    Content-Type=application/json
    ...    Accept=application/json
    RETURN    ${headers}

# In Suite Setup
API Test Suite - Suite Setup
    API - Create Session
    ${api_key}=    Get Environment Variable    API_KEY
    Set Suite Variable    ${SUITE_API_KEY}    ${api_key}

# Per test
User_Can_List_Orders
    ${headers}=    API - Auth Header With API Key    ${SUITE_API_KEY}
    Order - Get List    ${headers}
```

### API Key in Query Parameter

```robotframework
# Pass via params
&{params}=    Create Dictionary    api_key=${SUITE_API_KEY}    page=1
${response}=    GET On Session    ${SUITE_NAME}    ${path}
...    params=${params}    expected_status=200
```

## OAuth 2.0 Client Credentials

For service-to-service APIs:

```robotframework
API - Get OAuth Token
    [Arguments]    ${alias}=${SUITE_NAME}
    ${client_id}=    Get Environment Variable    OAUTH_CLIENT_ID
    ${client_secret}=    Get Environment Variable    OAUTH_CLIENT_SECRET
    &{body}=    Create Dictionary
    ...    grant_type=client_credentials
    ...    client_id=${client_id}
    ...    client_secret=${client_secret}
    &{headers}=    Create Dictionary    Content-Type=application/x-www-form-urlencoded
    ${response}=    POST On Session    ${alias}    /oauth/token
    ...    data=${body}    headers=${headers}    expected_status=200
    RETURN    ${response.json()}[access_token]
```

## Testing Auth Errors

Always test both unauthorized and forbidden cases:

```robotframework
Auth - Access Without Token
    [Arguments]    ${path}
    &{headers}=    Create Dictionary    Content-Type=application/json
    ${response}=    API - GET    ${path}    ${headers}    expected_status=401
    Dictionary Should Contain Key    ${response.json()}    error

Auth - Access With Invalid Token
    [Arguments]    ${path}
    &{headers}=    Create Dictionary
    ...    Authorization=Bearer invalid_token_string
    ...    Content-Type=application/json
    ${response}=    API - GET    ${path}    ${headers}    expected_status=401

Auth - Access With Insufficient Permissions
    [Arguments]    ${path}    ${headers}
    ${response}=    API - GET    ${path}    ${headers}    expected_status=403
    Dictionary Should Contain Key    ${response.json()}    error
```

## Multiple Auth Roles in One Suite

If a suite needs both admin and user tokens:

```robotframework
Suite Setup
    API - Create Session
    # Admin token
    ${admin_user}=    Get Environment Variable    ADMIN_USERNAME
    ${admin_pass}=    Get Environment Variable    ADMIN_PASSWORD
    ${admin_token}=    API - Login    ${admin_user}    ${admin_pass}
    Set Suite Variable    ${ADMIN_TOKEN}    ${admin_token}
    # Regular user token
    ${user_name}=    Get Environment Variable    API_USERNAME
    ${user_pass}=    Get Environment Variable    API_PASSWORD
    ${user_token}=    API - Login    ${user_name}    ${user_pass}
    Set Suite Variable    ${USER_TOKEN}    ${user_token}

*** Test Cases ***
Admin_Can_Delete_Any_User
    ${headers}=    API - Auth Header    ${ADMIN_TOKEN}
    User - Delete    ${headers}    ${target_user_id}

User_Cannot_Delete_Other_User
    ${headers}=    API - Auth Header    ${USER_TOKEN}
    ${response}=    API - DELETE    ${EP_USER_DELETE}/${other_user_id}    ${headers}    expected_status=403
```

## Environment Variables Reference

| Variable | Purpose |
|---|---|
| `API_USERNAME` | Login username for test user |
| `API_PASSWORD` | Login password for test user |
| `ADMIN_USERNAME` | Login username for admin user |
| `ADMIN_PASSWORD` | Login password for admin user |
| `API_KEY` | API key (when using key-based auth) |
| `OAUTH_CLIENT_ID` | OAuth 2.0 client ID |
| `OAUTH_CLIENT_SECRET` | OAuth 2.0 client secret |

Set before running:
```bash
export API_USERNAME=testuser@example.com
export API_PASSWORD=Test@1234
robot --loglevel TRACE -d results/ tests/user.robot
```

**NEVER store credentials in YAML files, .robot files, or any committed code.**
