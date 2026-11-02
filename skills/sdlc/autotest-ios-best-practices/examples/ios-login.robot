*** Settings ***
# FOM Example — iOS Login Feature
# Run: robot --loglevel TRACE -d results/ -t "User_Can_Login_With_Valid_Credentials" tests/login.robot
Resource     ../config/imports.resource
Variables    ../data/login.yaml

Test Setup      Login - Open Screen
Test Teardown   Common - Close App

*** Test Cases ***
User_Can_Login_With_Valid_Credentials
    [Tags]    login    smoke    TC-001
    Login - Login With Valid Credentials    ${data["${TEST_NAME}"]}

User_Cannot_Login_With_Wrong_Password
    [Tags]    login    regression    TC-002
    Login - Login With Wrong Password    ${data["${TEST_NAME}"]}

User_Cannot_Login_With_Empty_Username
    [Tags]    login    regression    TC-003
    Login - Login With Empty Username    ${data["${TEST_NAME}"]}

User_Can_Navigate_To_Forgot_Password
    [Tags]    login    regression    TC-004
    Login - Navigate To Forgot Password

--- features/login/login_variables.resource ---

*** Variables ***
${inp_username}         accessibility_id=usernameTextField
${inp_password}         accessibility_id=passwordTextField
${btn_login}            accessibility_id=loginButton
${btn_forgot_password}  accessibility_id=forgotPasswordButton
${lbl_home_title}       accessibility_id=homeScreenTitle
${lbl_error_message}    accessibility_id=loginErrorLabel
${lbl_forgot_title}     accessibility_id=forgotPasswordScreenTitle
${txt_invalid}          Tên đăng nhập hoặc mật khẩu không đúng
${txt_empty_field}      Vui lòng nhập tên đăng nhập

--- features/login/login_keywords.resource ---

*** Settings ***
Resource    ../../config/imports.resource
Resource    login_variables.resource

*** Keywords ***
Login - Open Screen
    Common - Open App
    Common - Handle Alert
    Common - Wait For Element Visible    ${inp_username}

Login - Fill Credentials
    [Arguments]    ${username}    ${password}
    Common - Input Text       ${inp_username}    ${username}
    Common - Input Text       ${inp_password}    ${password}

Login - Tap Login
    Common - Click Element    ${btn_login}
    Common - Wait For Element Visible    ${lbl_home_title}

Login - Verify Login Success
    Common - Wait For Element Visible    ${lbl_home_title}
    Page Should Contain Element    ${lbl_home_title}

Login - Login With Valid Credentials
    [Arguments]    ${td}
    Login - Fill Credentials    ${td}[username]    ${td}[password]
    Login - Tap Login
    Login - Verify Login Success

Login - Login With Wrong Password
    [Arguments]    ${td}
    Login - Fill Credentials    ${td}[username]    ${td}[password]
    Common - Click Element    ${btn_login}
    Common - Wait For Element Visible    ${lbl_error_message}
    Element Text Should Be    ${lbl_error_message}    ${txt_invalid}

Login - Login With Empty Username
    [Arguments]    ${td}
    Common - Input Text       ${inp_password}    ${td}[password]
    Common - Click Element    ${btn_login}
    Common - Wait For Element Visible    ${lbl_error_message}
    Element Should Contain Text    ${lbl_error_message}    ${txt_empty_field}

Login - Navigate To Forgot Password
    Common - Click Element    ${btn_forgot_password}
    Common - Wait For Element Visible    ${lbl_forgot_title}
    Page Should Contain Element    ${lbl_forgot_title}

--- data/login.yaml ---

# data/login.yaml
data:
  User_Can_Login_With_Valid_Credentials:
    username: "testuser@example.com"
    password: "Test@1234"

  User_Cannot_Login_With_Wrong_Password:
    username: "testuser@example.com"
    password: "wrongpassword"

  User_Cannot_Login_With_Empty_Username:
    password: "Test@1234"
