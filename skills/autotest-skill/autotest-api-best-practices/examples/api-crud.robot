*** Settings ***
# AOM Example — User CRUD operations
# Demonstrates: create, read, update, delete, list with pagination, cleanup
#
# Run one TC:
#   export API_USERNAME=testuser@example.com && export API_PASSWORD=Test@1234
#   robot --loglevel TRACE -d results/ -t "User_Can_Create_Account_With_Valid_Data" tests/user.robot
#
# Run full suite:
#   robot --loglevel TRACE -d results/ tests/user.robot
#
Resource    ../config/imports.resource
Variables   ../data/user.yaml

Suite Setup      User Test Suite - Setup
Suite Teardown   Delete All Sessions

*** Keywords ***
User Test Suite - Setup
    API - Create Session
    ${username}=    Get Environment Variable    API_USERNAME
    ${password}=    Get Environment Variable    API_PASSWORD
    ${token}=    API - Login    ${username}    ${password}
    Set Suite Variable    ${SUITE_TOKEN}    ${token}

*** Test Cases ***
User_Can_Create_Account_With_Valid_Data
    [Tags]    user    smoke    TC-001
    [Teardown]    User - Delete If Exists    ${headers}    ${CREATED_USER_ID}
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    ${response}=    User - Create Account    ${headers}    ${data["${TEST_NAME}"]}
    Set Test Variable    ${CREATED_USER_ID}    ${response.json()}[id]

User_Can_Get_User_By_ID
    [Tags]    user    smoke    TC-002
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - Get By ID And Verify    ${headers}    ${data["${TEST_NAME}"]}

User_Can_Update_User_Profile
    [Tags]    user    regression    TC-003
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - Update Profile    ${headers}    ${data["${TEST_NAME}"]}

User_Can_Delete_Own_Account
    [Tags]    user    regression    TC-004
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - Create And Delete    ${headers}    ${data["${TEST_NAME}"]}

User_Can_List_All_Users_With_Pagination
    [Tags]    user    regression    TC-005
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - List With Pagination    ${headers}    ${data["${TEST_NAME}"]}

User_Cannot_Create_Account_With_Duplicate_Email
    [Tags]    user    negative    TC-006
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - Create With Duplicate Email Should Fail    ${headers}    ${data["${TEST_NAME}"]}

User_Cannot_Create_Account_Without_Required_Fields
    [Tags]    user    negative    TC-007
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - Create Without Required Fields Should Fail    ${headers}    ${data["${TEST_NAME}"]}

User_Cannot_Get_Non_Existent_User
    [Tags]    user    negative    TC-008
    ${headers}=    API - Auth Header    ${SUITE_TOKEN}
    User - Get Non Existent User Should Return 404    ${headers}

--- api/user/user_variables.resource ---

*** Variables ***
${EP_USER_LIST}         /api/v1/users
${EP_USER_BY_ID}        /api/v1/users
${EP_USER_CREATE}       /api/v1/users
${EP_USER_UPDATE}       /api/v1/users
${EP_USER_DELETE}       /api/v1/users

${FIELD_ID}             id
${FIELD_USERNAME}       username
${FIELD_EMAIL}          email
${FIELD_STATUS}         status
${FIELD_ROLE}           role
${FIELD_CREATED_AT}     created_at

${VAL_STATUS_ACTIVE}    active
${VAL_ROLE_USER}        user
${VAL_ROLE_ADMIN}       admin

--- api/user/user_keywords.resource ---

*** Settings ***
Resource    ../../config/imports.resource
Resource    user_variables.resource

*** Keywords ***
User - Create Account
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary
    ...    username=${td}[username]    email=${td}[email]
    ...    password=${td}[password]    role=${td.get("role", "${VAL_ROLE_USER}")}
    ${response}=    API - POST    ${EP_USER_CREATE}    ${body}    ${headers}    expected_status=201
    API - Assert Field Not Empty    ${response}    ${FIELD_ID}
    Should Be Equal    ${response.json()}[${FIELD_USERNAME}]    ${td}[username]
    Should Be Equal    ${response.json()}[${FIELD_EMAIL}]    ${td}[email]
    API - Assert Response Time    ${response}
    RETURN    ${response}

User - Get By ID
    [Arguments]    ${headers}    ${user_id}
    ${response}=    API - GET    ${EP_USER_BY_ID}/${user_id}    ${headers}
    API - Assert Field Equals    ${response}    ${FIELD_ID}    ${user_id}
    API - Assert Response Time    ${response}
    RETURN    ${response}

User - Get By ID And Verify
    [Arguments]    ${headers}    ${td}
    ${response}=    User - Get By ID    ${headers}    ${td}[user_id]
    Should Be Equal    ${response.json()}[${FIELD_USERNAME}]    ${td}[expected_username]

User - Update Profile
    [Arguments]    ${headers}    ${td}
    # Create user first
    &{create_body}=    Create Dictionary    username=${td}[username]    email=${td}[email]    password=${td}[password]
    ${created}=    API - POST    ${EP_USER_CREATE}    ${create_body}    ${headers}    expected_status=201
    ${user_id}=    Set Variable    ${created.json()}[id]
    # Update
    &{update_body}=    Create Dictionary    username=${td}[new_username]
    ${response}=    API - PUT    ${EP_USER_UPDATE}/${user_id}    ${update_body}    ${headers}
    API - Assert Field Equals    ${response}    ${FIELD_USERNAME}    ${td}[new_username]
    API - Assert Response Time    ${response}
    # Cleanup
    API - DELETE    ${EP_USER_DELETE}/${user_id}    ${headers}    expected_status=204

User - Create And Delete
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary    username=${td}[username]    email=${td}[email]    password=${td}[password]
    ${created}=    API - POST    ${EP_USER_CREATE}    ${body}    ${headers}    expected_status=201
    ${user_id}=    Set Variable    ${created.json()}[id]
    API - DELETE    ${EP_USER_DELETE}/${user_id}    ${headers}    expected_status=204
    API - GET    ${EP_USER_BY_ID}/${user_id}    ${headers}    expected_status=404

User - List With Pagination
    [Arguments]    ${headers}    ${td}
    &{params}=    Create Dictionary    page=1    per_page=${td}[per_page]
    ${response}=    API - GET    ${EP_USER_LIST}    ${headers}    params=${params}
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    data
    Dictionary Should Contain Key    ${json}    total
    API - Assert Response Time    ${response}

User - Create With Duplicate Email Should Fail
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary    username=first_user    email=${td}[email]    password=${td}[password]
    API - POST    ${EP_USER_CREATE}    ${body}    ${headers}    expected_status=201
    &{dup_body}=    Create Dictionary    username=${td}[username]    email=${td}[email]    password=${td}[password]
    ${response}=    API - POST    ${EP_USER_CREATE}    ${dup_body}    ${headers}    expected_status=409
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    error
    Should Contain    ${json}[error]    ${td}[expected_error]

User - Create Without Required Fields Should Fail
    [Arguments]    ${headers}    ${td}
    &{body}=    Create Dictionary    username=${td}[username]
    ${response}=    API - POST    ${EP_USER_CREATE}    ${body}    ${headers}    expected_status=400
    Dictionary Should Contain Key    ${response.json()}    error

User - Get Non Existent User Should Return 404
    [Arguments]    ${headers}
    ${response}=    API - GET    ${EP_USER_BY_ID}/00000000-0000-0000-0000-000000000000    ${headers}    expected_status=404
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    message
    Should Contain    ${json}[message]    not found    ignore_case=True

User - Delete If Exists
    [Arguments]    ${headers}    ${user_id}
    ${exists}=    Run Keyword And Return Status
    ...    API - GET    ${EP_USER_BY_ID}/${user_id}    ${headers}    expected_status=200
    IF    ${exists}
        API - DELETE    ${EP_USER_DELETE}/${user_id}    ${headers}    expected_status=204
    END

--- data/user.yaml ---

data:
  User_Can_Create_Account_With_Valid_Data:
    username: "testuser_create_001"
    email: "testuser_create_001@example.com"
    password: "Test@1234"
    role: "user"

  User_Can_Get_User_By_ID:
    user_id: "existing-user-uuid"         # pre-existing user in staging environment
    expected_username: "existing_user"

  User_Can_Update_User_Profile:
    username: "testuser_update_003"
    email: "testuser_update_003@example.com"
    password: "Test@1234"
    new_username: "testuser_updated_003"

  User_Can_Delete_Own_Account:
    username: "testuser_delete_004"
    email: "testuser_delete_004@example.com"
    password: "Test@1234"

  User_Can_List_All_Users_With_Pagination:
    per_page: 10

  User_Cannot_Create_Account_With_Duplicate_Email:
    username: "testuser_dup_006"
    email: "testuser_dup_006@example.com"
    password: "Test@1234"
    expected_error: "Email already exists"

  User_Cannot_Create_Account_Without_Required_Fields:
    username: "testuser_nofields_007"
