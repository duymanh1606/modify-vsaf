*** Settings ***
# AOM Example — API error case testing
# Demonstrates: 400, 401, 403, 404, 409, 422 scenarios; input validation; field-level errors
#
# Run one TC:
#   export API_USERNAME=testuser@example.com && export API_PASSWORD=Test@1234
#   robot --loglevel TRACE -d results/ -t "API_Returns_400_For_Missing_Required_Field" tests/errors.robot
#
Resource    ../config/imports.resource
Variables   ../data/errors.yaml

Suite Setup      Error Test Suite - Setup
Suite Teardown   Delete All Sessions

*** Keywords ***
Error Test Suite - Setup
    API - Create Session
    ${username}=    Get Environment Variable    API_USERNAME
    ${password}=    Get Environment Variable    API_PASSWORD
    ${token}=    API - Login    ${username}    ${password}
    Set Suite Variable    ${SUITE_TOKEN}    ${token}

*** Test Cases ***
API_Returns_400_For_Missing_Required_Field
    [Tags]    errors    negative    TC-001
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    Error - Create User Missing Email Should Return 400    ${headers}    ${data["${TEST_NAME}"]}

API_Returns_400_For_Invalid_Email_Format
    [Tags]    errors    negative    TC-002
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    Error - Create User Invalid Email Format Should Return 400    ${headers}    ${data["${TEST_NAME}"]}

API_Returns_401_When_Token_Not_Provided
    [Tags]    errors    negative    TC-003
    Error - Access Without Auth Should Return 401

API_Returns_401_When_Token_Expired_Or_Invalid
    [Tags]    errors    negative    TC-004
    Error - Access With Invalid Token Should Return 401

API_Returns_403_When_User_Lacks_Permission
    [Tags]    errors    negative    TC-005
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    Error - Access Admin Endpoint As User Should Return 403    ${headers}    ${data["${TEST_NAME}"]}

API_Returns_404_For_Non_Existent_Resource
    [Tags]    errors    negative    TC-006
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    Error - Get Non Existent Resource Should Return 404    ${headers}    ${data["${TEST_NAME}"]}

API_Returns_409_For_Duplicate_Resource
    [Tags]    errors    negative    TC-007
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    Error - Create Duplicate Resource Should Return 409    ${headers}    ${data["${TEST_NAME}"]}

API_Returns_422_For_Business_Rule_Violation
    [Tags]    errors    negative    TC-008
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    Error - Violate Business Rule Should Return 422    ${headers}    ${data["${TEST_NAME}"]}

API_Error_Response_Has_Required_Fields
    [Tags]    errors    regression    TC-009
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    Error - All Error Responses Have Required Structure    ${headers}

--- api/errors/error_keywords.resource ---

*** Settings ***
Resource    ../../config/imports.resource

*** Keywords ***
Error - Create User Missing Email Should Return 400
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary    username=${td}[username]    password=${td}[password]
    ${response}=    API - POST    /api/v1/users    ${body}    ${headers}    expected_status=400
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    error
    Should Not Be Empty    ${json}[error]
    API - Assert Response Time    ${response}

Error - Create User Invalid Email Format Should Return 400
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary
    ...    username=${td}[username]
    ...    email=${td}[invalid_email]
    ...    password=${td}[password]
    ${response}=    API - POST    /api/v1/users    ${body}    ${headers}    expected_status=400
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    error
    Should Contain    ${json}[error]    email    ignore_case=True

Error - Access Without Auth Should Return 401
    &{headers}=    Create Dictionary    Content-Type=application/json
    ${response}=    API - GET    /api/v1/me    ${headers}    expected_status=401
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    error
    Should Contain    ${json}[error]    Unauthorized    ignore_case=True

Error - Access With Invalid Token Should Return 401
    &{headers}=    Create Dictionary
    ...    Authorization=Bearer eyJhbGciOiJIUzI1NiJ9.invalid.token
    ...    Content-Type=application/json
    ${response}=    API - GET    /api/v1/me    ${headers}    expected_status=401
    Dictionary Should Contain Key    ${response.json()}    error

Error - Access Admin Endpoint As User Should Return 403
    [Arguments]    ${headers}    ${td}
    ${response}=    API - GET    ${td}[admin_endpoint]    ${headers}    expected_status=403
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    error
    Should Contain    ${json}[error]    Forbidden    ignore_case=True

Error - Get Non Existent Resource Should Return 404
    [Arguments]    ${headers}    ${td}
    ${response}=    API - GET    ${td}[endpoint]/${td}[non_existent_id]    ${headers}    expected_status=404
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    message
    Should Contain    ${json}[message]    not found    ignore_case=True

Error - Create Duplicate Resource Should Return 409
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary    username=duplicate_user    email=${td}[email]    password=${td}[password]
    API - POST    /api/v1/users    ${body}    ${headers}    expected_status=201
    ${response}=    API - POST    /api/v1/users    ${body}    ${headers}    expected_status=409
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    error
    Should Contain    ${json}[error]    ${td}[expected_conflict_hint]    ignore_case=True

Error - Violate Business Rule Should Return 422
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary    quantity=${td}[invalid_quantity]    product_id=${td}[product_id]
    ${response}=    API - POST    /api/v1/orders    ${body}    ${headers}    expected_status=422
    ${json}=    Set Variable    ${response.json()}
    ${has_error}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${json}    error
    ${has_details}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${json}    details
    Should Be True    ${has_error} or ${has_details}

Error - All Error Responses Have Required Structure
    [Arguments]    ${headers}
    # 400
    &{bad_body}=    Create Dictionary    username=x
    ${r400}=    API - POST    /api/v1/users    ${bad_body}    ${headers}    expected_status=400
    Dictionary Should Contain Key    ${r400.json()}    error
    # 404
    ${r404}=    API - GET    /api/v1/users/00000000-0000-0000-0000-000000000000    ${headers}    expected_status=404
    Dictionary Should Contain Key    ${r404.json()}    message
    # 401 (no auth)
    &{no_auth}=    Create Dictionary    Content-Type=application/json
    ${r401}=    API - GET    /api/v1/me    ${no_auth}    expected_status=401
    Dictionary Should Contain Key    ${r401.json()}    error

--- data/errors.yaml ---

data:
  API_Returns_400_For_Missing_Required_Field:
    username: "testuser_no_email"
    password: "Test@1234"

  API_Returns_400_For_Invalid_Email_Format:
    username: "testuser_bad_email"
    invalid_email: "this-is-not-an-email"
    password: "Test@1234"

  API_Returns_403_When_User_Lacks_Permission:
    admin_endpoint: "/api/v1/admin/users"

  API_Returns_404_For_Non_Existent_Resource:
    endpoint: "/api/v1/users"
    non_existent_id: "00000000-0000-0000-0000-000000000000"

  API_Returns_409_For_Duplicate_Resource:
    email: "duplicate_test_009@example.com"
    password: "Test@1234"
    expected_conflict_hint: "already exists"

  API_Returns_422_For_Business_Rule_Violation:
    product_id: "some-product-uuid"
    invalid_quantity: 0
