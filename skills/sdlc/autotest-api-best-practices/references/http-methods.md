# HTTP Methods — RequestsLibrary Reference

## Session vs Sessionless

Always use **session-based** keywords (`GET On Session`, `POST On Session`, etc.) — not bare `GET`, `POST`. Sessions share connection settings (base URL, timeout, SSL verify) and persist cookies/headers across calls within the same suite.

```robotframework
# Session-based (correct)
Create Session    my_session    https://api.example.com    verify=${True}    timeout=30
${resp}=    GET On Session    my_session    /api/v1/users

# Sessionless (never use — brittle, no reuse)
${resp}=    GET    https://api.example.com/api/v1/users
```

## Common Wrappers (required — see SKILL.md Section 3)

Never call `GET On Session`, `POST On Session`, etc. directly in feature keyword files. Always use `API - GET`, `API - POST`, etc.

## GET

```robotframework
# Simple GET
${response}=    API - GET    ${EP_USER_LIST}    ${headers}

# GET with query params
&{params}=    Create Dictionary    page=1    per_page=20    status=active
${response}=    API - GET    ${EP_USER_LIST}    ${headers}    params=${params}

# GET expecting non-200 (error test)
${response}=    API - GET    ${EP_USER_BY_ID}/99999    ${headers}    expected_status=404
```

## POST

```robotframework
# JSON body
&{body}=    Create Dictionary    username=user1    email=user1@example.com    password=Test@1234
${response}=    API - POST    ${EP_USER_CREATE}    ${body}    ${headers}    expected_status=201

# Nested body
${address}=    Create Dictionary    street=123 Main    city=Hanoi    country=VN
&{body}=    Create Dictionary    name=Test Corp    address=${address}
${response}=    API - POST    ${EP_COMPANY_CREATE}    ${body}    ${headers}    expected_status=201
```

## PUT (full replacement)

```robotframework
&{body}=    Create Dictionary    username=updated    email=updated@example.com
${response}=    API - PUT    ${EP_USER_UPDATE}/${user_id}    ${body}    ${headers}
```

## PATCH (partial update)

```robotframework
&{body}=    Create Dictionary    status=inactive
${response}=    API - PATCH    ${EP_USER_UPDATE}/${user_id}    ${body}    ${headers}
```

## DELETE

```robotframework
# Default expected status: 204 No Content
${response}=    API - DELETE    ${EP_USER_DELETE}/${user_id}    ${headers}

# Some APIs return 200 with body on delete
${response}=    API - DELETE    ${EP_ORDER_DELETE}/${order_id}    ${headers}    expected_status=200
```

## Multipart / File Upload

For file uploads, do NOT use `json=` — use `files=` or `data=`:

```robotframework
API - Upload File
    [Arguments]    ${headers}    ${file_path}    ${field_name}=file
    ${file_content}=    Get Binary File    ${file_path}
    ${file_name}=    Evaluate    os.path.basename("${file_path}")    os
    &{file}=    Create Dictionary    ${field_name}=("${file_name}", ${file_content}, "application/octet-stream")
    ${upload_headers}=    Copy Dictionary    ${headers}
    Remove From Dictionary    ${upload_headers}    Content-Type
    ${response}=    POST On Session    ${SUITE_NAME}    ${EP_FILE_UPLOAD}
    ...    files=${file}    headers=${upload_headers}    expected_status=200
    RETURN    ${response}
```

## GraphQL

```robotframework
API - GraphQL Query
    [Arguments]    ${headers}    ${query}    ${variables}=${None}
    &{body}=    Create Dictionary    query=${query}
    IF    $variables is not None
        Set To Dictionary    ${body}    variables=${variables}
    END
    ${response}=    POST On Session    ${SUITE_NAME}    /graphql
    ...    json=${body}    headers=${headers}    expected_status=200
    Dictionary Should Not Contain Key    ${response.json()}    errors
    RETURN    ${response}
```

## Chained Requests (token from one call used in next)

```robotframework
Order - Create And Get Details
    [Arguments]    ${headers}    ${td}
    &{order_body}=    Create Dictionary    product_id=${td}[product_id]    qty=${td}[qty]
    ${create_resp}=    API - POST    ${EP_ORDER_CREATE}    ${order_body}    ${headers}    expected_status=201
    ${order_id}=    Set Variable    ${create_resp.json()}[id]
    ${get_resp}=    API - GET    ${EP_ORDER_BY_ID}/${order_id}    ${headers}
    API - Assert Field Equals    ${get_resp}    id    ${order_id}
    RETURN    ${get_resp}
```

## Pagination

```robotframework
API - Get All Pages
    [Arguments]    ${headers}    ${path}    ${page_size}=50
    ${all_items}=    Create List
    ${page}=    Set Variable    1
    WHILE    True
        &{params}=    Create Dictionary    page=${page}    per_page=${page_size}
        ${response}=    API - GET    ${path}    ${headers}    params=${params}
        ${items}=    Set Variable    ${response.json()}[data]
        ${count}=    Get Length    ${items}
        IF    ${count} == 0    BREAK
        Append To List    ${all_items}    @{items}
        ${page}=    Evaluate    ${page} + 1
        IF    ${count} < ${page_size}    BREAK
    END
    RETURN    ${all_items}
```

## Common `expected_status` Defaults

| Wrapper | Default `expected_status` |
|---|---|
| `API - GET` | `200` |
| `API - POST` | `201` |
| `API - PUT` | `200` |
| `API - PATCH` | `200` |
| `API - DELETE` | `204` |

Override by passing the value explicitly: `API - POST    ${path}    ${body}    ${headers}    expected_status=400`.
