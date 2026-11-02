*** Settings ***
# Example: Android Product List — scroll, swipe, list item selection
# Run all:  robot --loglevel TRACE -d results/ tests/product_list.robot
# Run one:  robot --loglevel TRACE -d results/ -t "User_Can_Select_Product_From_List" tests/product_list.robot
Resource     ../config/imports.resource
Variables    ../data/product_list.yaml

Test Setup      Product - Open Screen
Test Teardown   Common - Close App

*** Test Cases ***
User_Can_Select_Product_From_List
    [Tags]    product    smoke    TC-001
    Product - Select Product From List    ${data["${TEST_NAME}"]}

User_Can_Scroll_To_Load_More_Products
    [Tags]    product    regression    TC-002
    Product - Verify More Products Load On Scroll

# --- features/product/product_variables.resource ---
#
# *** Variables ***
# ${lbl_product_list_heading}     accessibility_id=product_list_title
# ${tab_products}                 accessibility_id=nav_products
# ${lbl_product_detail_title}     id=com.example.app:id/tv_product_name
# ${btn_load_more}                accessibility_id=btn_load_more
# ${icon_loading}                 id=com.example.app:id/progress_bar

# --- features/product/product_keywords.resource ---
#
# *** Settings ***
# Resource    ../../config/imports.resource
# Resource    product_variables.resource
#
# *** Keywords ***
# Product - Open Screen
#     Common - Open App
#     Common - Handle Permission Dialog
#     Login - Login With Saved Credentials         # navigate through login first
#     Common - Click Element    ${tab_products}
#     Common - Wait For Element Visible    ${lbl_product_list_heading}
#
# Product - Select Product From List
#     [Arguments]    ${td}
#     Product - Scroll To Product    ${td}[product_name]
#     Product - Tap Product Item     ${td}[product_name]
#     Product - Verify Product Detail    ${td}[product_name]
#
# Product - Scroll To Product
#     [Arguments]    ${product_name}
#     # UIAutomator2 auto-scroll — most reliable for RecyclerView
#     ${locator}=    Set Variable
#     ...    android=new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("${product_name}"))
#     Wait Until Page Contains Element    ${locator}    timeout=${TIMEOUT_DEFAULT}
#
# Product - Tap Product Item
#     [Arguments]    ${product_name}
#     ${locator}=    Set Variable    android=new UiSelector().text("${product_name}")
#     Common - Click Element    ${locator}
#
# Product - Verify Product Detail
#     [Arguments]    ${expected_name}
#     Common - Wait For Element Visible    ${lbl_product_detail_title}
#     Element Text Should Be    ${lbl_product_detail_title}    ${expected_name}
#
# Product - Verify More Products Load On Scroll
#     Common - Wait For Element Visible    ${lbl_product_list_heading}
#     Common - Swipe Up To Element    ${btn_load_more}
#     Common - Click Element    ${btn_load_more}
#     Wait Until Element Is Not Visible    ${icon_loading}    timeout=${TIMEOUT_MAX}
#     Page Should Contain Element    ${lbl_product_list_heading}

# --- data/product_list.yaml ---
#
# data:
#   User_Can_Select_Product_From_List:
#     product_name: "Cà phê sữa đá"