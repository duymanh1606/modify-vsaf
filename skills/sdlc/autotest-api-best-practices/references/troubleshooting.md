# Troubleshooting — RF API Tests

## Error Reference Table

| Error | Likely Cause | Fix |
|---|---|---|
| `RequestConnectionError: HTTPSConnectionPool... Max retries exceeded` | API server down, wrong BASE_URL, network issue | Check `${BASE_URL}` in `common_variables.resource` and whether server is reachable: `curl ${BASE_URL}/health` |
| `HTTPError: 401 Unauthorized` in test (not expected) | Token expired or not set in Suite Setup | Verify Suite Setup ran; check `SUITE_TOKEN` variable is set |
| `HTTPError: 403 Forbidden` | Test user lacks permissions for the endpoint | Check test user role; use admin credentials env var for admin-only endpoints |
| `HTTPError: 404 Not Found` for valid resource | Resource deleted between tests / wrong ID | Test must create its own data; never rely on pre-existing resources |
| `JSONDecodeError` | API returned HTML error page (proxy, WAF, gateway) or plain text | `Log    ${response.text}` to see raw body; investigate server-side |
| `KeyError: 'access_token'` in `API - Login` | Login failed (wrong credentials, wrong endpoint) | Verify `EP_LOGIN` path; `Log    ${response.text}` to see actual response |
| `RequestMismatchError: Expected 200 but got 400` | Wrong `expected_status` OR test data triggers server-side validation | Log response body to see validation errors |
| `SSLError: CERTIFICATE_VERIFY_FAILED` | Self-signed cert in staging, wrong `verify=` setting | Check `create_session` has `verify=${True}` with correct CA bundle, or `verify=/path/to/ca.pem` |
| Session not found: `alias` | Feature keyword called before `API - Create Session` | Ensure `Suite Setup` is defined and calls `API - Create Session` |
| `KeyError` on response field | Field not in response (API version mismatch) | `Log    ${response.json()}` to inspect; check API documentation |
| Test passes but wrong data asserted | Using stale variable from prior step | Check variable scope; always use `RETURN` value from request, not a suite variable |
| `ConnectionResetError` / timeout | Request timeout too short or API slow | Increase `${TIMEOUT}` in `common_variables.resource`; check API performance |
| `UnicodeDecodeError` | Response body is binary (file download) | Use `.content` not `.json()` for binary responses |

## Debugging Techniques

### Log the Full Response

Add temporary logging to see what the server actually returned:

```robotframework
${response}=    API - POST    ${EP_USER_CREATE}    ${body}    ${headers}    expected_status=201
Log    Status: ${response.status_code}
Log    Headers: ${response.headers}
Log    Body: ${response.text}
```

### Check Session Exists

```robotframework
# In console or test
${sessions}=    Get Sessions
Log    ${sessions}
```

### Inspect the Request Being Sent

```robotframework
Log    Request URL: ${response.request.url}
Log    Request Method: ${response.request.method}
Log    Request Headers: ${response.request.headers}
Log    Request Body: ${response.request.body}
```

### Print Python Object

```robotframework
${json}=    Set Variable    ${response.json()}
Log    ${json}    formatter=repr
```

## Common Setup Issues

### Missing Environment Variables

```bash
# Check that env vars are set
echo $API_USERNAME
echo $API_PASSWORD

# Run with explicit values
API_USERNAME=testuser@example.com API_PASSWORD=Test@1234 robot tests/user.robot
```

### Session Not Deleted Between Runs

If a previous run crashed and left sessions open, the next run may get "Session already exists". Ensure `Suite Teardown` has `Delete All Sessions`.

### SSL Certificate Issues

```robotframework
# If your staging environment uses a custom CA bundle
Create Session    ${alias}    ${BASE_URL}    verify=/path/to/ca-bundle.pem    timeout=${TIMEOUT}

# NEVER do this — disables SSL verification
Create Session    ${alias}    ${BASE_URL}    verify=${False}    timeout=${TIMEOUT}  # FORBIDDEN
```

### Base URL Trailing Slash

```robotframework
# common_variables.resource — no trailing slash
${BASE_URL}    https://api-staging.example.com

# Endpoint path — starts with /
${EP_USER_LIST}    /api/v1/users
```

If `BASE_URL` ends with `/` and path starts with `/`, you get double-slash. Remove trailing slash from `BASE_URL`.

## RequestsLibrary Version Checks

```bash
pip show robotframework-requests
# Should be 0.9.x or later for Python 3.10+
```

If using older version, keywords may differ slightly. Current recommended version: `>=0.9.3`.

## Running a Single Test Case

```bash
# Run just one TC — fastest feedback loop
robot --loglevel TRACE -d results/ -t "User_Can_Create_Account_With_Valid_Data" tests/user.robot

# Run all TCs tagged smoke
robot --loglevel TRACE -d results/ -i smoke tests/user.robot

# Run all negative tests
robot --loglevel TRACE -d results/ -i negative tests/

# Run against production (override BASE_URL)
robot --loglevel TRACE -d results/ \
  -v ENV:production \
  -v BASE_URL:https://api.example.com \
  -t "User_Can_Create_Account_With_Valid_Data" tests/user.robot
```

## Reading Results

```bash
# Quick summary
python .claude/skills/autotest-results/scripts/rf_results.py \
  --output results/output.xml --sections summary --pretty

# Detailed failure info
python .claude/skills/autotest-results/scripts/rf_results.py \
  --output results/output.xml --sections errors --pretty

# Open full trace in browser
open results/log.html
```

## Authentication Troubleshooting

### Token Not Being Sent

Check the auth header is being built correctly:

```robotframework
${headers}=    API - Auth Header    ${SUITE_TOKEN}
Log    Headers: ${headers}
# Should show: {'Authorization': 'Bearer eyJ...', 'Content-Type': 'application/json', ...}
```

### Login Returns 200 But Token Field Missing

```robotframework
${response}=    POST On Session    ${SUITE_NAME}    ${EP_LOGIN}    json=${body}    expected_status=200
Log    ${response.json()}    formatter=repr
# Check what field actually contains the token: token vs access_token vs jwt vs data.token
```

### Token Expires Too Fast

If `SUITE_TOKEN` expires during a long suite run, add per-test token refresh:

```robotframework
*** Test Cases ***
Very_Long_Test
    [Tags]    user    regression
    ${token}=    API - Get Valid Token    # refresh every test
    ${headers}=    API - Auth Header    ${token}
    User - Do Work    ${headers}
```
