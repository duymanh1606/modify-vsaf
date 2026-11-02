*** Settings ***
# Example: Android Transfer Form — multi-field input, dropdown, confirm dialog
# Run all:  robot --loglevel TRACE -d results/ tests/transfer.robot
# Run one:  robot --loglevel TRACE -d results/ -t "User_Can_Complete_Transfer" tests/transfer.robot
Resource     ../config/imports.resource
Variables    ../data/transfer.yaml

Test Setup      Transfer - Open Screen
Test Teardown   Common - Close App

*** Test Cases ***
User_Can_Complete_Transfer
    [Tags]    transfer    smoke    TC-001
    Transfer - Complete Transfer    ${data["${TEST_NAME}"]}

User_Cannot_Transfer_With_Invalid_Amount
    [Tags]    transfer    regression    TC-002
    Transfer - Transfer With Invalid Amount    ${data["${TEST_NAME}"]}

# --- features/transfer/transfer_variables.resource ---
#
# *** Variables ***
# ${tab_transfer}             accessibility_id=tab_transfer
# ${lbl_transfer_heading}     accessibility_id=transfer_screen_title
# ${inp_amount}               id=com.example.app:id/edt_amount
# ${btn_transfer_type}        id=com.example.app:id/spinner_transfer_type
# ${inp_recipient}            id=com.example.app:id/edt_recipient_account
# ${btn_continue}             id=com.example.app:id/btn_continue
# ${btn_confirm}              accessibility_id=confirm_transfer_button
# ${lbl_success}              accessibility_id=transfer_success_message
# ${lbl_amount_error}         id=com.example.app:id/tv_amount_error
# ${txt_success}              Chuyển khoản thành công

# --- features/transfer/transfer_keywords.resource ---
#
# *** Settings ***
# Resource    ../../config/imports.resource
# Resource    transfer_variables.resource
#
# *** Keywords ***
# Transfer - Open Screen
#     Common - Open App
#     Common - Handle Permission Dialog
#     Login - Login With Saved Credentials
#     Common - Click Element    ${tab_transfer}
#     Common - Wait For Element Visible    ${lbl_transfer_heading}
#
# Transfer - Complete Transfer
#     [Arguments]    ${td}
#     Transfer - Fill Transfer Form    ${td}[amount]    ${td}[type]    ${td}[recipient]
#     Transfer - Confirm Transfer
#     Transfer - Verify Transfer Success
#
# Transfer - Transfer With Invalid Amount
#     [Arguments]    ${td}
#     Transfer - Fill Amount    ${td}[amount]
#     Common - Click Element    ${btn_continue}
#     Transfer - Verify Amount Error    ${td}[expected_error]
#
# Transfer - Fill Transfer Form
#     [Arguments]    ${amount}    ${transfer_type}    ${recipient}
#     Transfer - Fill Amount    ${amount}
#     Transfer - Select Transfer Type    ${transfer_type}
#     Common - Input Text    ${inp_recipient}    ${recipient}
#     Common - Click Element    ${btn_continue}
#
# Transfer - Fill Amount
#     [Arguments]    ${amount}
#     Common - Input Text    ${inp_amount}    ${amount}
#
# Transfer - Select Transfer Type
#     [Arguments]    ${transfer_type}
#     Common - Click Element    ${btn_transfer_type}
#     # UIAutomator2 selector for dropdown option
#     ${option}=    Set Variable    android=new UiSelector().text("${transfer_type}")
#     Common - Click Element    ${option}
#
# Transfer - Confirm Transfer
#     Common - Swipe Up To Element    ${btn_confirm}
#     Common - Click Element    ${btn_confirm}
#
# Transfer - Verify Transfer Success
#     Common - Wait For Element Visible    ${lbl_success}
#     Page Should Contain Text    ${txt_success}
#
# Transfer - Verify Amount Error
#     [Arguments]    ${expected_message}
#     Common - Wait For Element Visible    ${lbl_amount_error}
#     Element Text Should Be    ${lbl_amount_error}    ${expected_message}

# --- data/transfer.yaml ---
#
# data:
#   User_Can_Complete_Transfer:
#     amount: "100000"
#     type: "Chuyển khoản nội bộ"
#     recipient: "0123456789"
#
#   User_Cannot_Transfer_With_Invalid_Amount:
#     amount: "abc"
#     expected_error: "Số tiền không hợp lệ"