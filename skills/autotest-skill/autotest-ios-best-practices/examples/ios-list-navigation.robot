*** Settings ***
# FOM Example — iOS Table List Navigation Feature
# Demonstrates: table cell selection, scroll to element, class chain locators, navigation back
# Run: robot --loglevel TRACE -d results/ -t "User_Can_Select_Item_From_List" tests/product_list.robot
Resource     ../config/imports.resource
Variables    ../data/product_list.yaml

Test Setup      Product List - Open Screen
Test Teardown   Common - Close App

*** Test Cases ***
User_Can_View_Product_List
    [Tags]    product-list    smoke    TC-001
    Product List - Verify List Visible

User_Can_Select_Item_From_List
    [Tags]    product-list    smoke    TC-002
    Product List - Select Product    ${data["${TEST_NAME}"]}

User_Can_Scroll_To_Item_Not_Visible_On_Screen
    [Tags]    product-list    regression    TC-003
    Product List - Scroll To And Select Product    ${data["${TEST_NAME}"]}

User_Can_Navigate_Back_From_Detail
    [Tags]    product-list    regression    TC-004
    Product List - Select And Return    ${data["${TEST_NAME}"]}

--- features/product_list/product_list_variables.resource ---

*** Variables ***
${lbl_list_title}       accessibility_id=productListTitle
${lbl_detail_title}     accessibility_id=productDetailTitle
${lbl_product_name}     accessibility_id=productNameLabel
${btn_add_to_cart}      accessibility_id=addToCartButton
# Table cells located by class chain with name filter — declared inline in keywords
# because name is dynamic (product name comes from test data)

--- features/product_list/product_list_keywords.resource ---

*** Settings ***
Resource    ../../config/imports.resource
Resource    product_list_variables.resource

*** Keywords ***
Product List - Open Screen
    Common - Open App
    Common - Handle Alert
    Common - Wait For Element Visible    ${lbl_list_title}

Product List - Verify List Visible
    Common - Wait For Element Visible    ${lbl_list_title}
    Page Should Contain Element    ios=**/XCUIElementTypeTable

Product List - Select Product
    [Arguments]    ${td}
    Common - Click Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${td}[product_name]'`]
    Common - Wait For Element Visible    ${lbl_detail_title}
    Page Should Contain Element    ${lbl_product_name}

Product List - Scroll To And Select Product
    [Arguments]    ${td}
    Common - Swipe Up To Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${td}[product_name]'`]
    Common - Click Element          ios=**/XCUIElementTypeCell[`name CONTAINS '${td}[product_name]'`]
    Common - Wait For Element Visible    ${lbl_detail_title}
    Page Should Contain Element    ${lbl_product_name}

Product List - Select And Return
    [Arguments]    ${td}
    Common - Click Element    ios=**/XCUIElementTypeCell[`name CONTAINS '${td}[product_name]'`]
    Common - Wait For Element Visible    ${lbl_detail_title}
    Common - Tap Navigation Back
    Common - Wait For Element Visible    ${lbl_list_title}

--- data/product_list.yaml ---

# data/product_list.yaml
data:
  User_Can_Select_Item_From_List:
    product_name: "Cà chua bi"

  User_Can_Scroll_To_Item_Not_Visible_On_Screen:
    product_name: "Bắp cải tím"

  User_Can_Navigate_Back_From_Detail:
    product_name: "Cà chua bi"
