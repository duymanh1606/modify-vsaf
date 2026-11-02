*** Settings ***
# Example: Android Login Feature — FOM pattern
# Run all:  robot --loglevel TRACE -d results/ tests/login.robot
# Run one:  robot --loglevel TRACE -d results/ -t "User_Can_Login_With_Valid_Credentials" tests/login.robot
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

User_Cannot_Login_With_Empty_Fields
    [Tags]    login    regression    TC-003
    Login - Login With Empty Fields

# --- features/login/login_variables.resource ---
#
# *** Variables ***
# ${inp_username}     accessibility_id=username_input
# ${inp_password}     accessibility_id=password_input
# ${btn_login}        id=com.example.app:id/btn_login
# ${lbl_home}         accessibility_id=home_screen_title
# ${lbl_error}        id=com.example.app:id/tv_error_message
# ${txt_empty_error}  Vui lòng nhập thông tin đăng nhập

# --- features/login/login_keywords.resource ---
#
# *** Settings ***
# Resource    ../../config/imports.resource
# Resource    login_variables.resource
#
# *** Keywords ***
# Login - Open Screen
#     Common - Open App
#     Common - Handle Permission Dialog
#     Common - Wait For Element Visible    ${inp_username}
#
# Login - Login With Valid Credentials
#     [Arguments]    ${td}
#     Login - Fill Credentials    ${td}[username]    ${td}[password]
#     Login - Verify Login Success
#
# Login - Login With Wrong Password
#     [Arguments]    ${td}
#     Login - Fill Credentials    ${td}[username]    ${td}[password]
#     Login - Verify Login Error    ${td}[expected_error]
#
# Login - Login With Empty Fields
#     Common - Click Element    ${btn_login}
#     Login - Verify Login Error    ${txt_empty_error}
#
# Login - Fill Credentials
#     [Arguments]    ${username}    ${password}
#     Common - Input Text       ${inp_username}    ${username}
#     Common - Input Text       ${inp_password}    ${password}
#     Common - Click Element    ${btn_login}
#
# Login - Verify Login Success
#     Common - Wait For Element Visible    ${lbl_home}
#     Page Should Contain Element    ${lbl_home}
#
# Login - Verify Login Error
#     [Arguments]    ${expected_message}
#     Common - Wait For Element Visible    ${lbl_error}
#     Element Text Should Be    ${lbl_error}    ${expected_message}

# --- data/login.yaml ---
#
# data:
#   User_Can_Login_With_Valid_Credentials:
#     username: "testuser@example.com"
#     password: "Test@1234"
#
#   User_Cannot_Login_With_Wrong_Password:
#     username: "testuser@example.com"
#     password: "wrongpass"
#     expected_error: "Tên đăng nhập hoặc mật khẩu không đúng"