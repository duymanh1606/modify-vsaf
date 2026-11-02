*** Settings ***
# FOM Example — iOS Form Input Feature
# Demonstrates: text input, keyboard dismissal, picker wheel, switch toggle, alert handling
# Run: robot --loglevel TRACE -d results/ -t "User_Can_Submit_Profile_Form" tests/profile_form.robot
Resource     ../config/imports.resource
Variables    ../data/profile_form.yaml

Test Setup      Profile Form - Open Screen
Test Teardown   Common - Close App

*** Test Cases ***
User_Can_Submit_Profile_Form
    [Tags]    profile-form    smoke    TC-001
    Profile Form - Submit Valid Profile    ${data["${TEST_NAME}"]}

User_Cannot_Submit_Form_With_Empty_Name
    [Tags]    profile-form    regression    TC-002
    Profile Form - Submit With Missing Required Field    ${data["${TEST_NAME}"]}

User_Can_Toggle_Notifications_Setting
    [Tags]    profile-form    regression    TC-003
    Profile Form - Toggle Notifications

User_Can_Select_Country_From_Picker
    [Tags]    profile-form    regression    TC-004
    Profile Form - Select Country    ${data["${TEST_NAME}"]}

--- features/profile_form/profile_form_variables.resource ---

*** Variables ***
${inp_full_name}        accessibility_id=fullNameTextField
${inp_email}            accessibility_id=emailTextField
${inp_phone}            accessibility_id=phoneTextField
${btn_country_picker}   accessibility_id=countryPickerButton
${lbl_country_value}    accessibility_id=selectedCountryLabel
${sw_notifications}     accessibility_id=notificationsSwitch
${btn_save}             accessibility_id=saveProfileButton
${lbl_success}          accessibility_id=profileSavedLabel
${lbl_name_error}       accessibility_id=nameValidationError
${txt_required}         Vui lòng nhập họ và tên

--- features/profile_form/profile_form_keywords.resource ---

*** Settings ***
Resource    ../../config/imports.resource
Resource    profile_form_variables.resource

*** Keywords ***
Profile Form - Open Screen
    Common - Open App
    Common - Handle Alert
    Common - Click Element    ${tab_profile}
    Common - Wait For Element Visible    ${inp_full_name}

Profile Form - Fill Text Fields
    [Arguments]    ${name}    ${email}    ${phone}
    Common - Input Text    ${inp_full_name}    ${name}
    Common - Input Text    ${inp_email}        ${email}
    Common - Input Text    ${inp_phone}        ${phone}
    Profile Form - Dismiss Keyboard

Profile Form - Dismiss Keyboard
    Run Keyword And Ignore Error    Click Element    ios=**/XCUIElementTypeButton[`name == 'Done'`]
    Run Keyword And Ignore Error    Click Element    ios=**/XCUIElementTypeKey[`name == 'Done'`]

Profile Form - Select Country From Picker
    [Arguments]    ${country}
    Common - Click Element    ${btn_country_picker}
    Common - Wait For Element Visible    class=XCUIElementTypePicker
    ${wheel}=    Get WebElement    class=XCUIElementTypePickerWheel
    Input Text    ${wheel}    ${country}
    Common - Click Element    ios=**/XCUIElementTypeNavigationBar/XCUIElementTypeButton[`name == 'Done'`]
    Common - Wait For Element Visible    ${lbl_country_value}
    Element Text Should Be    ${lbl_country_value}    ${country}

Profile Form - Tap Save
    Common - Swipe Up To Element    ${btn_save}
    Common - Click Element    ${btn_save}
    Common - Wait For Element Visible    ${lbl_success}

Profile Form - Submit Valid Profile
    [Arguments]    ${td}
    Profile Form - Fill Text Fields    ${td}[full_name]    ${td}[email]    ${td}[phone]
    Profile Form - Select Country From Picker    ${td}[country]
    Profile Form - Tap Save
    Page Should Contain Element    ${lbl_success}

Profile Form - Submit With Missing Required Field
    [Arguments]    ${td}
    Common - Input Text    ${inp_email}    ${td}[email]
    Profile Form - Tap Save
    Common - Wait For Element Visible    ${lbl_name_error}
    Element Should Contain Text    ${lbl_name_error}    ${txt_required}

Profile Form - Toggle Notifications
    ${before}=    Get Element Attribute    ${sw_notifications}    value
    Common - Click Element    ${sw_notifications}
    ${after}=    Get Element Attribute    ${sw_notifications}    value
    Should Not Be Equal    ${before}    ${after}
    Common - Handle Alert     OK

Profile Form - Select Country
    [Arguments]    ${td}
    Profile Form - Select Country From Picker    ${td}[country]

--- data/profile_form.yaml ---

# data/profile_form.yaml
data:
  User_Can_Submit_Profile_Form:
    full_name: "Nguyen Van A"
    email: "nguyenvana@example.com"
    phone: "0901234567"
    country: "Viet Nam"

  User_Cannot_Submit_Form_With_Empty_Name:
    email: "test@example.com"

  User_Can_Select_Country_From_Picker:
    country: "United States"
