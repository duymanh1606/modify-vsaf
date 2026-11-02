# Response Validation

## Status Code Validation

`expected_status` in every HTTP call is the first line of defense. The common wrappers already accept it as a parameter with sensible defaults. Specify it explicitly for every call.

```robotframework
# Explicit expected_status on success
${response}=    API - POST    ${EP_USER_CREATE}    ${body}    ${headers}    expected_status=201

# Explicit expected_status on error test
${response}=    API - POST    ${EP_USER_CREATE}    ${dup_body}    ${headers}    expected_status=409
```

When `expected_status` doesn't match the actual status code, RequestsLibrary raises `RequestMismatchError` and the test fails immediately with the actual status.

## JSON Body Assertions

### Using Common Wrappers

```robotframework
# Assert field exists and is not empty
API - Assert Field Not Empty    ${response}    id

# Assert field equals specific value
API - Assert Field Equals    ${response}    status    active

# Assert response time
API - Assert Response Time    ${response}
API - Assert Response Time    ${response}    max_seconds=1
```

### Direct JSON Access

```robotframework
${json}=    Set Variable    ${response.json()}

# Check field exists
Dictionary Should Contain Key    ${json}    id

# Check field value
Should Be Equal As Strings    ${json}[status]    active

# Check field is not empty
Should Not Be Empty    ${json}[token]

# Nested field
Should Be Equal As Strings    ${json}[user][role]    admin

# List length
${items}=    Set Variable    ${json}[items]
Length Should Be    ${items}    5
Should Be True    len(${items}) > 0
```

### Common Helper Keywords

```robotframework
API - Assert JSON Field
    [Arguments]    ${response}    ${field_path}    ${expected}
    ${json}=    Set Variable    ${response.json()}
    ${actual}=    Evaluate    "${field_path}".split(".")
    ${current}=    Set Variable    ${json}
    FOR    ${key}    IN    @{actual}
        ${current}=    Set Variable    ${current}[${key}]
    END
    Should Be Equal As Strings    ${current}    ${expected}

# Usage:
API - Assert JSON Field    ${response}    user.profile.role    admin

API - Assert List Contains Item
    [Arguments]    ${response}    ${list_field}    ${item_id}
    ${json}=    Set Variable    ${response.json()}
    ${items}=    Set Variable    ${json}[${list_field}]
    ${ids}=    Evaluate    [str(item.get("id", "")) for item in ${items}]
    Should Contain    ${ids}    ${item_id}
```

## Response Headers Validation

```robotframework
# Check specific header
${content_type}=    Set Variable    ${response.headers}[Content-Type]
Should Contain    ${content_type}    application/json

# Check header exists
Dictionary Should Contain Key    ${response.headers}    X-Request-Id

# Check pagination headers (if API uses Link header style)
Dictionary Should Contain Key    ${response.headers}    X-Total-Count
```

## Response Time Validation

```robotframework
API - Assert Response Time
    [Arguments]    ${response}    ${max_seconds}=${TIMEOUT_RESPONSE}
    ${elapsed}=    Set Variable    ${response.elapsed.total_seconds()}
    Should Be True    ${elapsed} < ${max_seconds}
    ...    Response took ${elapsed}s, expected < ${max_seconds}s

# Usage — use default threshold (2s from common_variables.resource)
API - Assert Response Time    ${response}

# Override for time-critical endpoints (500ms)
API - Assert Response Time    ${response}    max_seconds=0.5

# Looser threshold for heavy operations (search, export)
API - Assert Response Time    ${response}    max_seconds=5
```

## Schema Validation

When testing that the response structure matches a contract:

```robotframework
API - Assert Response Schema
    [Arguments]    ${response}    @{required_fields}
    ${json}=    Set Variable    ${response.json()}
    FOR    ${field}    IN    @{required_fields}
        Dictionary Should Contain Key    ${json}    ${field}
        ...    msg=${field} is missing from response
    END

# Usage
API - Assert Response Schema    ${response}    id    username    email    status    created_at
```

## Error Response Validation

For 4xx/5xx tests, always assert the error body — not just the status:

```robotframework
API - Assert Error Response
    [Arguments]    ${response}    ${expected_message_fragment}=${EMPTY}
    ${json}=    Set Variable    ${response.json()}
    # API should return some error indicator
    ${has_error}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${json}    error
    ${has_message}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${json}    message
    Should Be True    ${has_error} or ${has_message}
    ...    Response has neither 'error' nor 'message' field: ${json}
    IF    '${expected_message_fragment}' != '${EMPTY}'
        ${error_text}=    Set Variable    ${json.get("error", json.get("message", ""))}
        Should Contain    ${error_text}    ${expected_message_fragment}
        ...    ignore_case=True
    END

# Usage
${response}=    API - POST    ${EP_USER_CREATE}    ${invalid_body}    ${headers}    expected_status=400
API - Assert Error Response    ${response}    Email already exists
```

## Validation Error Details (422 Unprocessable Entity)

Many APIs return field-level validation errors:

```robotframework
API - Assert Validation Error On Field
    [Arguments]    ${response}    ${field_name}
    ${json}=    Set Variable    ${response.json()}
    # Common patterns: {errors: {field: [msg]}} or {details: [{field: ..., message: ...}]}
    ${has_errors}=    Run Keyword And Return Status
    ...    Dictionary Should Contain Key    ${json}    errors
    IF    ${has_errors}
        Should Contain    ${json}[errors]    ${field_name}
    ELSE
        ${has_details}=    Run Keyword And Return Status
        ...    Dictionary Should Contain Key    ${json}    details
        IF    ${has_details}
            ${fields}=    Evaluate    [d.get("field","") for d in ${json}[details]]
            Should Contain    ${fields}    ${field_name}
        END
    END
```

## List Response Assertions

```robotframework
API - Assert List Not Empty
    [Arguments]    ${response}    ${list_field}=data
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    ${list_field}
    ${items}=    Set Variable    ${json}[${list_field}]
    Should Not Be Empty    ${items}    msg=${list_field} list is empty

API - Assert List Length
    [Arguments]    ${response}    ${expected_length}    ${list_field}=data
    ${json}=    Set Variable    ${response.json()}
    ${items}=    Set Variable    ${json}[${list_field}]
    Length Should Be    ${items}    ${expected_length}

API - Assert Pagination Response
    [Arguments]    ${response}    ${page_field}=page    ${total_field}=total
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    ${page_field}
    Dictionary Should Contain Key    ${json}    ${total_field}
    Should Be True    ${json}[${total_field}] >= 0

# Usage
${response}=    API - GET    ${EP_USER_LIST}    ${headers}    params=${params}
API - Assert List Not Empty    ${response}
API - Assert Pagination Response    ${response}
```

## Reference: HTTP Status Codes to Test

| Code | Name | When to cover |
|---|---|---|
| 200 | OK | GET, PUT, PATCH success |
| 201 | Created | POST creates resource |
| 204 | No Content | DELETE success |
| 400 | Bad Request | Missing required field, invalid format |
| 401 | Unauthorized | Missing token, expired token, wrong credentials |
| 403 | Forbidden | Token valid but insufficient role |
| 404 | Not Found | Valid format ID, resource doesn't exist |
| 409 | Conflict | Duplicate email, unique constraint |
| 422 | Unprocessable | Business rule violation, validation failure |
| 429 | Too Many Requests | Rate limit test (if API has it) |
| 500 | Internal Server Error | Only test when intentionally breaking something |
